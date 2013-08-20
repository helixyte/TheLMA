"""
Run tool command.
"""
from everest.entities.utils import get_root_aggregate
from everest.resources.interfaces import IMemberResource
from everest.mime import JsonMime
from everest.querying.specifications import eq # pylint: disable=W0611
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.rdb import Session as session_maker
from everest.representers.utils import as_representer
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection_class
from everest.utils import classproperty
from paste.deploy import appconfig # pylint: disable=E0611,F0401
from paste.script.command import Command # pylint: disable=E0611,F0401
from pyramid.path import DottedNameResolver
from pyramid.registry import Registry
from pyramid.testing import DummyRequest
from sqlalchemy import event
from sqlalchemy.orm.session import Session
from thelma.automation.tools.stock.sampleregistration import \
    IMoleculeDesignPoolRegistrationItem
from thelma.automation.tools.stock.sampleregistration import \
    IMoleculeDesignRegistrationItem
from thelma.automation.tools.stock.sampleregistration import \
    ISampleRegistrationItem
from thelma.automation.tools.stock.sampleregistration import \
    ISupplierSampleRegistrationItem
from thelma.interfaces import ITube
from thelma.interfaces import ITubeTransferWorklist
from thelma.interfaces import IUser
from thelma.run import create_config
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401
import logging
import os
import sys
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['EmptyTubeRegistrarToolCommand',
           'MetaToolCommand',
           'ToolCommand',
           'XL20ExecutorToolCommand',
           ]


class MetaToolCommand(type):
    """
    Meta class for tool commands.

    This ensures the option parser and the summary and usage doc strings are
    set up automatically for the tool to run; this is much preferable to
    having to define a new entry point for every individual tool we want to
    run.
    """
    def __new__(mcs, name, bases, class_dict):
        # Ignore base classes.
        if name != 'ToolCommand' and not name.startswith('_'):
            parser = ToolCommand.make_standard_parser(simulate=True)
            if not 'name' in class_dict:
                raise ValueError('You need to define a name for the tool '
                                 'to run as "name" attribute in the class '
                                 'namespace of your tool (%s).' % name)
            if not 'tool' in class_dict:
                raise ValueError('You need to define the pkg resource '
                                 'style dotted name (absolute) of the '
                                 'tool to run as "tool" attribute in the '
                                 'class namespace of your tool (%s).' % name)
            option_defs = \
                class_dict.get('option_defs') or bases[-1].option_defs
            if option_defs is None:
                raise ValueError('You need to define a list of option '
                                 'definitions as "option_defs" attribute '
                                 'in the class namespace of your tool (%s).'
                                 % name)
            for opt_name, attr_name, opt_kw in option_defs:
                if 'dest' in opt_kw:
                    raise ValueError('Cannot use the "dest" parameter for '
                                     'tool command options.')
                # We need a copy here in case the option defs are reused in
                # derived classes.
                copied_opt_kw = opt_kw.copy()
                copied_opt_kw['dest'] = attr_name
                parser.add_option(opt_name, **copied_opt_kw)
            summary = class_dict.__doc__.strip()
            class_dict['summary'] = summary
            usage = ToolCommand.__dict__['_usage_template'] \
                                  % class_dict['name']
            class_dict['usage'] = usage
            class_dict['parser'] = parser
        cls = type.__new__(mcs, name, bases, class_dict)
        # This is the magic: If this is the command we are running,
        # set the new class as the target class of the ToolCommand.
        if class_dict.get('name') == sys.argv[-2]:
            ToolCommand.set_target_class(cls)
        return cls


class LazyOption(object):
    """
    Simple capsule for options that can only be initialized when TheLMA has
    started up.
    """
    def __init__(self, value_callback):
        self.__value_callback = value_callback
        self.__option_value = None

    def __call__(self, option, option_name, option_value, parser): # pylint: disable=W0613
        self.__option_value = option_value
        setattr(parser.values, option.dest, self)

    def initialize(self, tool_class, options):
        return self.__value_callback(tool_class, self.__option_value, options)


class ToolCommand(Command):
    """
    Abstract base class for paste commands which run a TheLMA tool from the
    command line.
    """
    __metaclass__ = MetaToolCommand
    #: Template for usage strings in derived classes.
    _usage_template = "%s <ini file>"
    #: This is the target tool command class (set by the meta class).
    __target_class = None
    #: pkg resource style (absolute) dotted name to the tool to run.
    tool = None
    #: A sequence of the form
    #:     [<option name>,<attribute name>, <option kewyword dict>]
    #: This is used to configure the option parser in the derived command
    #: class and to extract the constructor arguments from the options.
    option_defs = None
    #: The name of the tool used on the command line.
    name = None
    #: Options group name for help messages.
    group_name = "thelma"
    #: Minimum number of command line arguments.
    min_args = 2
    #: Maximum number of command line arguments.
    max_args = 2

    def __init__(self, name):
        Command.__init__(self, name)
        self._report_callback = lambda : None

    @classmethod
    def make_standard_parser(cls,
                             verbose=True,
                             interactive=False,
                             no_interactive=False,
                             simulate=False,
                             quiet=False,
                             overwrite=False):
        parser = Command.standard_parser(verbose=verbose,
                                         interactive=interactive,
                                         no_interactive=no_interactive,
                                         simulate=simulate,
                                         quiet=quiet,
                                         overwrite=overwrite)
        parser.add_option('--ignore-warnings',
                          action='store_true',
                          dest='ignore_warnings',
                          help="If true, changes are committed even when the "
                               "tool reports warnings (unless the --simulate "
                               "flag is set).")
        return parser

    @classmethod
    def set_target_class(cls, target_class):
        cls.__target_class = target_class

    @classmethod
    def finalize(cls, tool, options):
        """
        Override this method in derived classes to perform actions after the
        tool has run.
        """
        pass

    @classmethod
    def report(cls, tool, options):
        """
        Override this method in derived classes to perform reporting actions
        after the tool has run.
        """
        pass

    @classproperty
    def summary(cls):
        if cls.__target_class is None:
            raise RuntimeError('Tool command "%s" not found!' % sys.argv[-2])
        return cls.__target_class.summary

    @classproperty
    def usage(cls):
        if cls.__target_class is None:
            raise RuntimeError('Tool command "%s" not found!' % sys.argv[-2])
        return cls.__target_class.usage

    @classproperty
    def parser(cls):
        if cls.__target_class is None:
            raise RuntimeError('Tool command "%s" not found!' % sys.argv[-2])
        return cls.__target_class.parser

    def command(self):
        ini_file = self.args[-1] # pylint: disable=E1101
        # TheLMA setup.
        config = self.__setup_thelma(ini_file)
        # Initialize the tool and run it.
        rsv = DottedNameResolver(None)
        tool_cls = rsv.resolve(self.__target_class.tool)
        arg_names = [od[1] for od in self.__target_class.option_defs]
        kw = {}
        # Initializing lazy options. We pass the target class and the
        # options so the callback has access to them.
        opts = self.options # pylint: disable=E1101
        for arg_name in arg_names:
            arg_value = getattr(opts, arg_name)
            if isinstance(arg_value, LazyOption):
                arg_value = arg_value.initialize(self.__target_class, opts)
                setattr(opts, arg_name, arg_value)
        kw = dict((arg_name, getattr(opts, arg_name))
                  for arg_name in arg_names)
        tool = tool_cls(**kw)
        try:
            tool.run()
        except:
            transaction.abort()
            raise
        else:
            if tool.has_errors():
                err_msgs = tool.log.get_messages()
                msg = 'Errors occurred during the tool run. Error messages:\n'
                raise RuntimeError(msg + os.linesep.join(err_msgs))
            warn_msgs = tool.get_messages(logging_level=logging.WARNING)
            if warn_msgs \
               and not self.options.ignore_warnings: # pylint: disable=E1101
                msg = 'Warnings occurred during the tool run. You can ' \
                      'repeat the run with the --ignore-warnings switch ' \
                      'to force changes to be committed. Warning messages:\n'
                raise RuntimeError(msg + os.linesep.join(warn_msgs))
            try:
                # This gives the tool command a chance to perform actions after
                # the tool has run.
                self.__target_class.finalize(tool, opts)
            except:
                transaction.abort()
                raise
            else:
                # Create a report of the run.
                self.__run_report(tool)
                # All good - check if we should commit.
                if not self.options.simulate: # pylint: disable=E1101
                    transaction.commit()
                else:
                    transaction.abort()
        config.end()

    def __run_report(self, tool):
        #
        self._report_callback()
        try:
            self.__target_class.report(tool, self.options) # pylint: disable=E1101
        except:
            transaction.abort()
            raise

    def __setup_thelma(self, ini_file):
        here_dir = os.getcwd()
        config_uri = 'config:%s' % ini_file
        self.logging_file_config(ini_file) # pylint: disable=E1101
        settings = appconfig(config_uri, 'thelma', relative_to=here_dir)
        reg = Registry('thelma')
        # Some tools need to resolve URLs, so we need to set up a request
        # and a service.
        url = 'http://0.0.0.0:6543'
        req = DummyRequest(application_url=url,
                           host_url=url,
                           path_url=url,
                           url=url,
                           registry=reg)
        config = create_config(settings, registry=reg)
        config.setup_registry(settings=settings)
        config.begin(request=req)
        config.load_zcml('configure.zcml')
        srvc = config.get_registered_utility(IService)
        req.root = srvc
        # Set up repositories.
        repo_mgr = config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize_all()
        # Start the everest service.
        srvc.start()
        # Configure the session maker.
        session_maker.configure(extension=ZopeTransactionExtension())
        # Set up machinery to enforce a session.flush() just before the
        # report is run so we have proper IDs in the output.
        # FIXME: This should be encapsulated better, perhaps depending on
        #        an option that selects the backend.
        def on_session_begin(session, trx, conn): # pylint: disable=W0613
            self._report_callback = lambda sess = session: sess.flush()
        event.listen(Session, 'after_begin', on_session_begin)
        return config


class EmptyTubeRegistrarToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the empty tube registrar tool.
    """
    name = 'emptytuberegistrar'
    tool = \
        'thelma.automation.tools.stock.emptytuberegistrar:EmptyTubeRegistrar'
    option_defs = [('--scanfile-dir',
                    'scanfile_directory',
                    dict(help="Directory where scanfiles are located.")
                    ),
                   ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            tube_agg = get_root_aggregate(ITube)
            for tube in tool.return_value:
                tube_agg.add(tube)


class _RegistrarCommand(ToolCommand): # no __init__ pylint: disable=W0232
    registration_resource = None

    option_defs = \
        [('--report-directory',
          'report_directory',
          dict(help='Directory where report files will be written. Defaults '
                    'to the directory the data file is in.',
               type='string'),
          ),
         ('--data-file',
          'registration_items',
          dict(help='File containing JSON registration data.',
               action='callback',
               type='string',
               callback=LazyOption(lambda cls, value, options:
                                        cls._data_callback(value, options)) # pylint: disable=W0212
               ),
          ),
         ]

    @classmethod
    def _data_callback(cls, value, options):
        # Set the default for the report directory.
        if options.report_directory is None:
            options.report_directory = os.path.dirname(value)
        coll_cls = get_collection_class(cls.registration_resource)
        rpr = as_representer(object.__new__(coll_cls), JsonMime)
        reg_items = rpr.from_stream(open(value, 'rU'))
        # FIXME: This should be treated properly in everest.
        if IMemberResource in provided_by(reg_items):
            ents = [reg_items.get_entity()]
        else:
            ents = [rc.get_entity() for rc in reg_items]
        return ents

    @classmethod
    def report(cls, tool, options):
        # Write out report files for registered items.
        tool.write_report()


class DesignPoolRegistrarCommand(_RegistrarCommand): # no __init__ pylint: disable=W0232
    """
    Runs the design registrar (for internal registration of new molecule
    designs).
    """
    name = 'designpoolregistrar'
    tool = 'thelma.automation.tools.stock.' \
           'sampleregistration.MoleculeDesignPoolRegistrar'
    registration_resource = IMoleculeDesignPoolRegistrationItem


class DesignRegistrarCommand(_RegistrarCommand): # no __init__ pylint: disable=W0232
    """
    Runs the design registrar (for internal registration of new molecule
    designs).
    """
    name = 'designregistrar'
    tool = \
    'thelma.automation.tools.stock.sampleregistration.MoleculeDesignRegistrar'
    registration_resource = IMoleculeDesignRegistrationItem


class SampleRegistrarCommand(_RegistrarCommand): # no __init__ pylint: disable=W0232
    """
    Runs the sample registrar (for internal registration of new samples).
    """
    name = 'sampleregistrar'
    tool = \
        'thelma.automation.tools.stock.sampleregistration.SampleRegistrar'
    option_defs = _RegistrarCommand.option_defs + \
        [('--validation-files',
          'validation_files',
          dict(help='Comma-separated list of rack scanning files '
                    'for validation of tube positions.',
               type='string')
           ),
          ('--rack-specs-name',
           'rack_specs_name',
           dict(help='Name of the rack specs to use for the racks to be '
                     'registered.',
                default='matrix0500',
                type='string'),
           ),
          ('--container-specs-name',
           'container_specs_name',
           dict(help='Name of the container specs to use for the containers '
                     'to be registered.',
                default='matrix0500',
                type='string'),
           ),
         ]
    registration_resource = ISampleRegistrationItem


class SupplierSampleRegistrarCommand(_RegistrarCommand): # no __init__ pylint: disable=W0232
    """
    Runs the supplier sample registrar (for registration of supplier samples).
    """
    name = 'suppliersampleregistrar'
    tool = \
    'thelma.automation.tools.stock.sampleregistration.SupplierSampleRegistrar'
    option_defs = SampleRegistrarCommand.option_defs
    registration_resource = ISupplierSampleRegistrationItem


class XL20ExecutorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the XL20 executor that executes tube transfers on DB level.
    """
    _user_callback = \
        LazyOption(lambda cls, value, options:
                                get_root_aggregate(IUser).get_by_slug(value))
    _output_file_callback = \
            LazyOption(lambda cls, value, options: open(value, 'rb').read())

    name = 'xl20executor'
    tool = 'thelma.automation.tools.worklists.tubehandler:XL20Executor'
    option_defs = [('--output-file',
                    'output_file_stream',
                    dict(help='The XL20 output file containing the ' \
                              'transfer data.',
                         action='callback',
                         type='string',
                         callback=_output_file_callback
                         )
                    ),
                   ('--user',
                    'user',
                    dict(help='User name to use as the owner of the Trac '
                              'ticket.',
                         action='callback',
                         type='string',
                         callback=_user_callback),
                   )
                   ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            tube_transfer_worklist_agg = get_root_aggregate(
                                                    ITubeTransferWorklist)
            tube_transfer_worklist_agg.add(tool.return_value)


class StockCondenserToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the tool condenser.
    """
    @classmethod
    def split_string(cls, value):
        return value.split(',')

    _excluded_racks_callback = \
        LazyOption(lambda cls, value, options:
                            StockCondenserToolCommand.split_string(value))

    name = 'stockcondenser'
    tool = 'thelma.automation.tools.stock.condense:StockCondenser'


    option_defs = [('--number-racks',
                    'racks_to_empty',
                    dict(help='Name of the molecule design library to create.',
                         type='int')
                    ),
                   ('--excluded-racks',
                    'excluded_racks',
                    dict(help='Racks from you do not want to pick tubes ' \
                              '(comma-separated, no white spaces).',
                         action='callback',
                         type='string',
                         callback=_excluded_racks_callback)
                    )]

# TODO: think about how to make this prettier
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors():
#            zip_stream = tool.return_value
#            file_map = read_zip_archive(zip_stream)
#            for fn, stream in file_map.iteritems():
#                loc = '/Users/berger/Desktop/%s' % (fn)
#                o = open(loc, 'w')
#                o.write(stream.read())
#                o.close()


#class LibraryGeneratorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#    """
#    Runs the library ISO creator tool.
#    """
#    _excel_file_callback = LazyOption(lambda cls, value, options:
#                                            open(value, 'rb').read())
#    _user_callback = \
#            LazyOption(lambda cls, value, options:
#                            get_root_aggregate(IUser).get_by_slug(value))
#    name = 'librarygenerator'
#    tool = 'thelma.automation.tools.libcreation.generation:LibraryGenerator'
#    option_defs = [('--library-name',
#                    'library_name',
#                    dict(help='Name of the molecule design library to create.'
#                         )
#                    ),
#                   ('--excel-file',
#                    'stream',
#                    dict(help='Path for the Excel file to load.',
#                         action='callback',
#                         type='string',
#                         callback=_excel_file_callback)
#                    ),
#                   ('--requester',
#                    'requester',
#                    dict(help='User name to use as the owner of the Trac '
#                              'ticket.',
#                         action='callback',
#                         type='string',
#                         callback=_user_callback),
#                   )
#                   ]
#
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors():
#            lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
#            lib_agg.add(tool.return_value)
#
#
#class LibraryIsoGeneratorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#    """
#    Creates ISOs for a library creation ISO request.
#    """
#
#    @classmethod
#    def get_library(cls, value):
#        agg = get_root_aggregate(IMoleculeDesignLibrary)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    _library_callback = \
#        LazyOption(lambda cls, value, options: cls.get_library(value))
#
#    name = 'librarycreationisogenerator'
#    tool = 'thelma.automation.tools.libcreation.ticket:LibraryCreationIsoCreator'
#    option_defs = [('--library-name',
#                    'molecule_design_library',
#                    dict(help='Name of the molecule design library whose ' \
#                              'ISOs to create.',
#                        action='callback',
#                        type='string',
#                        callback=_library_callback),
#                    )
#                   ]
#
#class LibraryIsoPopulatorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#
#    @classmethod
#    def get_library(cls, value):
#        agg = get_root_aggregate(IMoleculeDesignLibrary)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    @classmethod
#    def split_string(cls, value):
#        return value.split(',')
#
#    _library_callback = \
#        LazyOption(lambda cls, value, options: cls.get_library(value))
#
#    _excluded_racks_callback = \
#        LazyOption(lambda cls, value, options: cls.split_string(value))
#
#    _requested_tube_callback = \
#        LazyOption(lambda cls, value, options: cls.split_string(value))
#
#    name = 'librarycreationisopopulator'
#    tool = 'thelma.automation.tools.libcreation.iso:LibraryCreationIsoPopulator'
#    option_defs = [('--library-name',
#                    'molecule_design_library',
#                    dict(help='Name of the molecule design library whose ' \
#                         'ISOs to populate.',
#                        action='callback',
#                        type='string',
#                        callback=_library_callback),
#                    ),
#                   ('--number-isos',
#                    'number_isos',
#                    dict(help='The number of ISOs you want to populate ' \
#                              '(includes an optimization step).',
#                         type='int')
#                    ),
#                   ('--excluded-racks',
#                    'excluded_racks',
#                    dict(help='Racks from you do not want to pick tubes ' \
#                              '(comma-separated, no white spaces).',
#                         action='callback',
#                         type='string',
#                         callback=_excluded_racks_callback)
#                    ),
#                   ('--requested-tubes',
#                    'requested_tubes',
#                    dict(help='Tubes you prefer to be used ' \
#                              '(comma-separated, no white spaces).',
#                         action='callback',
#                         type='string',
#                         callback=_requested_tube_callback),
#                   )
#                   ]
#
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors():
#            labels = []
#            for lci in tool.return_value:
#                labels.append(lci.label)
#            msg = '%i ISO(s) have been created: %s' % (
#                                            len(labels), ', '.join(labels))
#            print msg
#
#
#class LibraryCreationLayoutWriterToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#
#    @classmethod
#    def get_iso(cls, value):
#        agg = get_root_aggregate(ILibraryCreationIso)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    _iso_callback = \
#        LazyOption(lambda cls, value, options: cls.get_iso(value))
#
#    name = 'librarycreationisolayoutwriter'
#    tool = 'thelma.automation.tools.libcreation.iso:LibraryCreationIsoLayoutWriter'
#    option_defs = [('--iso',
#                    'library_creation_iso',
#                    dict(help='Label of the library creation ISO whose ' \
#                              'layout you want to print.',
#                        action='callback',
#                        type='string',
#                        callback=_iso_callback),
#                    )]
#
#    # TODO: think about how to make this prettier
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors():
#            iso_label = tool.library_creation_iso.label
#            fn = '/Users/berger/Desktop/%s.csv' % (iso_label)
#            o = open(fn, 'w')
#            stream = tool.return_value
#            stream.seek(0)
#            o.write(stream.read())
#            o.close()
#
#
#class LibraryCreationWorklistWriterToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#
#    @classmethod
#    def get_iso(cls, value):
#        agg = get_root_aggregate(ILibraryCreationIso)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    @classmethod
#    def get_tube_destination_map(cls, value):
#        barcodes = value.split(',')
#        # TODO: make configurable
#        tube_racks = dict()
#        number_quadrants = 4
#        number_mds = 3
#        for sector_index in range(number_quadrants):
#            quadrant_barcodes = []
#            i = 0
#            while i < number_mds:
#                barcode = barcodes.pop(0)
#                quadrant_barcodes.append(barcode)
#                i += 1
#            tube_racks[sector_index] = quadrant_barcodes
#        return tube_racks
#
#    @classmethod
#    def get_pool_stock_rack_barcodes(cls, value):
#        barcodes = value.split(',')
#        pool_racks = dict()
#        number_quadrants = 4
#        for sector_index in range(number_quadrants):
#            barcode = barcodes[sector_index]
#            pool_racks[sector_index] = barcode
#        return pool_racks
#
#    _iso_callback = \
#        LazyOption(lambda cls, value, options: cls.get_iso(value))
#
#    _tube_destination_racks_callback = \
#        LazyOption(lambda cls, value, options:
#                        cls.get_tube_destination_map(value))
#
#
#    _pool_stock_rack_callback = \
#        LazyOption(lambda cls, value, options:
#                        cls.get_pool_stock_rack_barcodes(value))
#
#    name = 'librarycreationworklistwriter'
#    tool = 'thelma.automation.tools.libcreation.writer:LibraryCreationWorklistWriter'
#    option_defs = [('--iso',
#                    'library_creation_iso',
#                    dict(help='Label of the library creation ISO for which ' \
#                              'you want to get worklist files.',
#                        action='callback',
#                        type='string',
#                        callback=_iso_callback),
#                    ),
#                   ('--tube-destination-racks',
#                    'tube_destination_racks',
#                    dict(help='The barcodes for the tube handler destination ' \
#                              'racks (for the single molecule design tubes - ' \
#                              'these racks have to be empty). Pass the ' \
#                              'barcodes comma-separated and without white ' \
#                              'spaces).',
#                        action='callback',
#                        type='string',
#                        callback=_tube_destination_racks_callback)
#                    ),
#                   ('--pool-stock-racks',
#                    'pool_stock_racks',
#                    dict(help='Barcodes for the racks that will contain ' \
#                              'the pool stock tubes. These racks have to ' \
#                              'have empty tubes in defined positions. Pass ' \
#                              'ordered by sector, comma-separated and ' \
#                              'without white spaces).',
#                         action='callback',
#                         type='string',
#                         callback=_pool_stock_rack_callback)
#                    ),
#                   ]
#
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors() and not options.simulate:
#            uploader = LibraryCreationTicketWorklistUploader(
#                        library_creation_iso=tool.library_creation_iso,
#                        file_map=tool.return_value)
#            uploader.send_request()
#            if not uploader.transaction_completed():
#                msg = 'Error during transmission to Trac!'
#                print msg
#
#
#class LibraryCreationExecutorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#
#    @classmethod
#    def get_iso(cls, value):
#        agg = get_root_aggregate(ILibraryCreationIso)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    _iso_callback = \
#        LazyOption(lambda cls, value, options: cls.get_iso(value))
#    _user_callback = \
#        LazyOption(lambda cls, value, options:
#                        get_root_aggregate(IUser).get_by_slug(value))
#
#    name = 'librarycreationexecutor'
#    tool = 'thelma.automation.tools.libcreation.execution:LibraryCreationExecutor'
#    option_defs = [('--iso',
#                    'library_creation_iso',
#                    dict(help='Label of the library creation ISO which you ' \
#                              'want to update.',
#                        action='callback',
#                        type='string',
#                        callback=_iso_callback),
#                    ),
#                   ('--user',
#                    'user',
#                    dict(help='User name of the user who performs the update.',
#                         action='callback',
#                         type='string',
#                         callback=_user_callback),
#                   )
#                   ]
#
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors() and not options.simulate:
#            reporter = LibraryCreationStockTransferReporter(
#                        executor=tool)
#            reporter.send_request()
#            if not reporter.transaction_completed():
#                msg = 'Error during transmission to Trac!'
#                print msg


#class PoolGeneratorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#    """
#    Runs the pool stock sample creator tool.
#    """
#    _excel_file_callback = LazyOption(lambda cls, value, options:
#                                            open(value, 'rb').read())
#    _user_callback = \
#            LazyOption(lambda cls, value, options:
#                            get_root_aggregate(IUser).get_by_slug(value))
#    name = 'poolcreationlibrarygenerator'
#    tool = 'thelma.automation.tools.poolcreation.generation:PoolCreationLibraryGenerator'
#    option_defs = [('--iso-request-label',
#                    'iso_request_label',
#                    dict(help='Name of the molecule design and ISO request '
#                              'library to create.'
#                         )
#                    ),
#                   ('--excel-file',
#                    'stream',
#                    dict(help='Path for the Excel file to load.',
#                         action='callback',
#                         type='string',
#                         callback=_excel_file_callback)
#                    ),
#                   ('--requester',
#                    'requester',
#                    dict(help='User name to use as the owner of the Trac '
#                              'ticket.',
#                         action='callback',
#                         type='string',
#                         callback=_user_callback),
#                   ),
#                   ('--target-volume',
#                    'target_volume',
#                    dict(help='The final volume for the new pool stock '
#                              'samples in ul.',
#                         type='int'),
#                    ),
#                   ('--target-concentration',
#                    'target_concentration',
#                    dict(help='The final pool concentration for the new pool '
#                              'stock samples in nM.',
#                         type='int'),
#                    )
#                   ]
#
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors():
#            lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
#            lib_agg.add(tool.return_value)
#
#
#class PoolCreationIsoGeneratorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#    """
#    Creates ISOs for a pool stock sample creation ISO request.
#    """
#
#    @classmethod
#    def get_iso_request(cls, value):
#        agg = get_root_aggregate(IIsoRequest)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    _iso_request_callback = LazyOption(lambda cls, value, options: # pylint: disable=W0108
#                    PoolCreationIsoGeneratorToolCommand.get_iso_request(value))
#
#    name = 'poolcreationisogenerator'
#    tool = 'thelma.automation.tools.poolcreation.ticket:PoolCreationIsoCreator'
#    option_defs = [('--iso-request-label',
#                    'iso_request',
#                    dict(help='The plate set label of the ISO request whose ' \
#                              'ISOs to create.',
#                        action='callback',
#                        type='string',
#                        callback=_iso_request_callback),
#                    )
#                   ]
#
#
#class PoolCreationIsoPopulatorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#    """
#    Populates ISOs for a pool stock sample creation ISO request.
#    """
#
#    @classmethod
#    def get_library(cls, value):
#        agg = get_root_aggregate(IMoleculeDesignLibrary)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    _library_callback = LazyOption(lambda cls, value, options: # pylint: disable=W0108
#                    PoolCreationIsoPopulatorToolCommand.get_library(value))
#
#    name = 'poolcreationisopopulator'
#    tool = 'thelma.automation.tools.poolcreation.iso:PoolCreationIsoPopulator'
#    option_defs = [('--pool-creation-library',
#                    'pool_creation_library',
#                    dict(help='The label of the pool creation library whose ' \
#                              'ISOs to populate.',
#                        action='callback',
#                        type='string',
#                        callback=_library_callback),
#                    ),
#                   ('--number-isos',
#                    'number_isos',
#                    dict(help='The number of ISOs ordered.',
#                         type='int')
#                    ),
#                   ]
#
#
#class PoolCreationWorklistWriterToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#
#    @classmethod
#    def get_iso(cls, value):
#        agg = get_root_aggregate(IStockSampleCreationIso)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    _iso_callback = LazyOption(lambda cls, value, options: # pylint: disable=W0108
#                    PoolCreationWorklistWriterToolCommand.get_iso(value))
#
#    _tube_destination_racks_callback = LazyOption(lambda cls, value, options:
#                                                  value.split(','))
#
#    name = 'poolcreationworklistwriter'
#    tool = 'thelma.automation.tools.poolcreation.writer:PoolCreationWorklistWriter'
#    option_defs = [('--iso',
#                    'pool_creation_iso',
#                    dict(help='Label of the pool creation ISO for which ' \
#                              'you want to get worklist files.',
#                        action='callback',
#                        type='string',
#                        callback=_iso_callback),
#                    ),
#                   ('--tube-destination-racks',
#                    'tube_destination_racks',
#                    dict(help='The barcodes for the tube handler destination ' \
#                              'racks (for the single molecule design tubes - ' \
#                              'these racks have to be empty). Pass the ' \
#                              'barcodes comma-separated and without white ' \
#                              'spaces).',
#                        action='callback',
#                        type='string',
#                        callback=_tube_destination_racks_callback)
#                    ),
#                   ('--pool-stock-rack',
#                    'pool_stock_rack_barcode',
#                    dict(help='The barcodes for the rack that will contain ' \
#                              'the pool stock tubes. This rack has to ' \
#                              'have empty tubes in defined positions.',
#                         type='string')
#                    ),
#                   ]
#
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors() and not options.simulate:
#            uploader = PoolCreationTicketWorklistUploader(
#                        pool_creation_iso=tool.pool_creation_iso,
#                        file_map=tool.return_value)
#            uploader.send_request()
#            if not uploader.transaction_completed():
#                msg = 'Error during transmission to Trac!'
#                print msg
#
#
#class PoolCreationExecutorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
#
#    @classmethod
#    def get_iso(cls, value):
#        agg = get_root_aggregate(IStockSampleCreationIso)
#        agg.filter = eq(label=value)
#        return list(agg.iterator())[0]
#
#    _iso_callback = \
#        LazyOption(lambda cls, value, options: # pylint: disable=W0108
#                   PoolCreationExecutorToolCommand.get_iso(value))
#    _user_callback = \
#        LazyOption(lambda cls, value, options:
#                        get_root_aggregate(IUser).get_by_slug(value))
#
#    name = 'poolcreationexecutor'
#    tool = 'thelma.automation.tools.poolcreation.execution:PoolCreationExecutor'
#    option_defs = [('--iso',
#                    'pool_creation_iso',
#                    dict(help='Label of the stock sample creation ISO which ' \
#                              'you want to update.',
#                        action='callback',
#                        type='string',
#                        callback=_iso_callback),
#                    ),
#                   ('--user',
#                    'user',
#                    dict(help='User name of the user who performs the update.',
#                         action='callback',
#                         type='string',
#                         callback=_user_callback),
#                   )
#                   ]
#
#    @classmethod
#    def finalize(cls, tool, options):
#        if not tool.has_errors() and not options.simulate:
#            reporter = PoolCreationStockTransferReporter(
#                        executor=tool)
#            reporter.send_request()
#            if not reporter.transaction_completed():
#                msg = 'Error during transmission to Trac!'
#                print msg


class StockAuditToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    name = 'stockaudit'
    tool = 'thelma.automation.tools.stock.audit:StockAuditReporter'
    option_defs = [('--molecule-type',
                    'molecule_type',
                    dict(help='Molecule type to create a stock audit report '
                              'for.',
                         type='string')
                    ),
                   ('--output-file',
                    'output_file',
                    dict(help='Output file to write the stock audit report '
                              'to.')
                    )
                   ]


class RackScanningAdjusterToolCommand(ToolCommand): # no __init__ pylint: disable=W0232

    _user_callback = \
        LazyOption(lambda cls, value, options:
                                get_root_aggregate(IUser).get_by_slug(value))

    name = 'rackscanningadjuster'
    tool = 'thelma.automation.tools.stock.rackscanning:RackScanningAdjuster'

    option_defs = [('--scanfiles',
                    'rack_scanning_files',
                    dict(help='This can be a single file, a zip file or a ' \
                              'directory (in which case all *.TXT files are ' \
                              'read).',
                         type='string',
                         ),
                    ),
                   ('--adjust-db',
                    'adjust_database',
                    dict(help='Shall the DB be adjusted (specified) or do you ' \
                              'only want to have a report (not specified)?',
                         action='store_true',
                         default=False,
                         )
                    ),
                   ('--user',
                    'user',
                    dict(help='User name how executes the update ' \
                              '(if applicable).',
                         action='callback',
                         type='string',
                         callback=_user_callback),
                   )
                   ]


class XL20DummyToolCommand(ToolCommand): # no __init__ pylint: disable=W0232

    _wl_file_callback = LazyOption(lambda cls, value, options:
                                        open(value, 'rb'))

    name = 'xl20dummy'
    tool = 'thelma.automation.tools.dummies:XL20Dummy'

    option_defs = [('--worklist-file',
                    'xl20_worklist_stream',
                    dict(help='The XL20 worklist file containing the ' \
                              'planned robot operations.',
                         action='callback',
                         type='string',
                         callback=_wl_file_callback
                         )
                    ),
                   ]

    # TODO: think about how to make this prettier
    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            fn = '/Users/berger/Desktop/xl20out.txt'
            o = open(fn, 'w')
            stream = tool.return_value
            stream.seek(0)
            o.write(stream.read())
            o.close()
