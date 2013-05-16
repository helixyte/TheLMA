"""
Run tool command.
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import eq
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.rdb import Session
from everest.utils import classproperty
from paste.deploy import appconfig # pylint: disable=E0611,F0401
from paste.script.command import Command # pylint: disable=E0611,F0401
from pyramid.path import DottedNameResolver
from pyramid.registry import Registry
from thelma.interfaces import ILibraryCreationIso
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import ITube
from thelma.interfaces import ITubeTransferWorklist
from thelma.interfaces import IUser
from thelma.run import create_config
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401
import logging
import os
import sys
import transaction
#from thelma.interfaces import ITubeTransfer
#from thelma.automation.tools.libcreation.ticket \
#    import LibraryCreationStockTransferReporter
#from thelma.automation.tools.libcreation.ticket \
#    import LibraryCreationTicketWorklistUploader
from pyramid.testing import DummyRequest
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection_class
from thelma.automation.tools.stock.sampleregistration import ISampleRegistrationItem
from everest.representers.utils import as_representer
from everest.mime import JsonMime

__docformat__ = 'reStructuredText en'
__all__ = ['EmptyTubeRegistrarToolCommand',
           'LibraryCreationExecutorToolCommand',
           'LibraryCreationWorklistWriterToolCommand',
           'LibraryGeneratorToolCommand',
           'LibraryIsoGeneratorToolCommand',
           'LibraryIsoPopulatorToolCommand',
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
        if name != 'ToolCommand': # Ignore the base class.
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
            if not 'option_defs' in class_dict:
                raise ValueError('You need to define a list of option '
                                 'definitions as "option_defs" attribute '
                                 'in the class namespace of your tool (%s).'
                                 % name)
            for opt_name, attr_name, opt_kw in class_dict['option_defs']:
                if 'dest' in opt_kw:
                    raise ValueError('Cannot use the "dest" parameter for '
                                     'tool command options.')
                opt_kw['dest'] = attr_name
                parser.add_option(opt_name, **opt_kw)
            summary = class_dict.__doc__.strip()
            class_dict['summary'] = summary
            usage = bases[-1].__dict__['_usage_template'] \
                                  % class_dict['name']
            class_dict['usage'] = usage
            class_dict['parser'] = parser
        cls = type.__new__(mcs, name, bases, class_dict)
        # This is the magic: If this is the command we are running,
        # set the new class as the target class of the ToolCommand.
        if class_dict['name'] == sys.argv[-2]:
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

    def initialize(self):
        return self.__value_callback(self.__option_value)


class ToolCommand(Command): # no __init__ pylint: disable=W0232
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

    @classmethod
    def make_standard_parser(verbose=True,
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
    def finalize(cls, tool):
        """
        Override this method in derived classes to perform actions after the
        tool has run.
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
        for arg_name in arg_names:
            arg_value = getattr(self.options, arg_name) # pylint: disable=E1101
            if isinstance(arg_value, LazyOption):
                arg_value = arg_value.initialize()
            kw[arg_name] = arg_value
        tool = tool_cls(**kw)
        try:
            tool.run()
        except: # catch all pylint: disable=W0702
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
                self.__target_class.finalize(tool)
                # All good - check if we should commit.
                if not self.options.simulate: # pylint: disable=E1101
                    transaction.commit()
                else:
                    transaction.abort()
            except: # catch all pylint: disable=W0702
                transaction.abort()
                raise
        config.end()

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
        #
        srvc.start()
        # Make sure RDB sessions join the Zope transaction.
        Session.configure(extension=ZopeTransactionExtension())
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
    def finalize(cls, tool):
        if not tool.has_errors():
            tube_agg = get_root_aggregate(ITube)
            for tube in tool.return_value:
                tube_agg.add(tube)


class DeliveryRegistrarCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the delivery registrar.
    """
    name = 'deliveryregistrar'
    tool = \
        'thelma.automation.tools.stock.sampleregistration.DeliveryRegistrar'
    option_defs = [('--delivery-file',
                    'delivery_file',
                    dict(help='File containing JSON delivery registration '
                              'data.',
                         type='string')
                    ),
                   ('--report-directory',
                    'report_directory',
                    dict(help='Directory where report files will be written. '
                              'Defaults to current directory.',
                         type='string')
                    ),
                   ('--validation-files',
                    'validation_files',
                    dict(help='Directory containing or comma-separated list '
                               'secifying rack scanning files for validation '
                               'of tube positions.',
                         type='string')
                    ),
                   ]


class SampleRegistrarCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the sample registrar (for internal registration of new samples).
    """
    @classmethod
    def _sample_data_callback(cls, value):
        coll_cls = get_collection_class(ISampleRegistrationItem)
        rpr = as_representer(object.__new__(coll_cls), JsonMime)
        return [rc.get_entity() for rc in rpr.from_stream(open(value, 'rU'))]

    name = 'sampleregistrar'
    tool = \
        'thelma.automation.tools.stock.sampleregistration.SampleRegistrar'
    option_defs = \
        [('--sample-data-file',
          'sample_registration_items',
          dict(help='File containing JSON sample registration data.',
               action='callback',
               type='string',
               callback=LazyOption(lambda value: # pylint: disable=W0108
                          SampleRegistrarCommand._sample_data_callback(value))
               ),
          ),
         ('--validation-files',
          'validation_files',
          dict(help='Comma-separated list of rack scanning files '
                    'for validation of tube positions.',
               type='string')
          ),
         ]


class XL20ExecutorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the XL20 executor that executes tube transfers on DB level.
    """
    _user_callback = LazyOption(lambda value: # pylint: disable=W0108
                                get_root_aggregate(IUser).get_by_slug(value))
    _output_file_callback = LazyOption(lambda value: open(value, 'rb').read())

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
    def finalize(cls, tool):
        if not tool.has_errors():
            tube_transfer_worklist_agg = get_root_aggregate(
                                                    ITubeTransferWorklist)
            tube_transfer_worklist_agg.add(tool.return_value)


class RackScanningAdjusterToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Compares the content of rack scanning files to the DB state and might
    perform DB update (depending on the adjust_database flag).
    """
    @classmethod
    def parse_boolean(cls, value):
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        else:
            raise ValueError('Invalid boolean option: %s' % value)

    _stream_callback = LazyOption(lambda value: open(value, 'rb'))
    _user_callback = LazyOption(lambda value: # pylint: disable=W0108
                                get_root_aggregate(IUser).get_by_slug(value))
    _bool_callback = LazyOption(lambda value: # pylint: disable=W0108
                        RackScanningAdjusterToolCommand.parse_boolean(value))

    name = 'rackscanningadjuster'
    tool = 'thelma.automation.tools.stock.rackscanning:RackScanningAdjuster'

    option_defs = [('--scanfiles',
                    'rack_scanning_stream',
                    dict(help='Stream of either a single file or several ' \
                              'files as zip archives.',
                         action='callback',
                         type='string',
                         callback=_stream_callback)
                    ),
                    ('--adjust-db',
                    'adjust_database',
                    dict(help='Shall the DB be adjusted (True) or do you ' \
                              'only want to have a report (False)?',
                         action='callback',
                         type='string',
                         callback=_bool_callback)
                    ),
                    ('--user',
                    'user',
                    dict(help='User name for the DB update tracking.',
                         action='callback',
                         type='string',
                         callback=_user_callback),
                   )]

    # TODO: think about how to make this prettier
    @classmethod
    def finalize(cls, tool):
        if not tool.has_errors():
            output_file = tool.get_overview_stream()
            fn = '/Users/berger/Desktop/rack_scanning_overview.txt'
            o = open(fn, 'w')
            output_file.seek(0)
            o.write(output_file.read())
            o.close()
#            if tool.adjust_database:
#                ttw_agg = get_root_aggregate(ITubeTransferWorklist)
#                ttw = tool.get_tube_transfer_worklist()
#                ttw_agg.add(ttw)


class StockCondenserToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the tool condenser.
    """
    @classmethod
    def split_string(cls, value):
        return value.split(',')

    _excluded_racks_callback = LazyOption(lambda value: # pylint: disable=W0108
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
#    def finalize(cls, tool):
#        if not tool.has_errors():
#            zip_stream = tool.return_value
#            file_map = read_zip_archive(zip_stream)
#            for fn, stream in file_map.iteritems():
#                loc = '/Users/berger/Desktop/%s' % (fn)
#                o = open(loc, 'w')
#                o.write(stream.read())
#                o.close()


class LibraryGeneratorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the library ISO creator tool.
    """
    _excel_file_callback = LazyOption(lambda value:
                                      open(value, 'rb').read())
    _user_callback = LazyOption(lambda value: # pylint: disable=W0108
                                get_root_aggregate(IUser).get_by_slug(value))
    name = 'librarygenerator'
    tool = 'thelma.automation.tools.libcreation.generation:LibraryGenerator'
    option_defs = [('--library-name',
                    'library_name',
                    dict(help='Name of the molecule design library to create.'
                         )
                    ),
                   ('--excel-file',
                    'stream',
                    dict(help='Path for the Excel file to load.',
                         action='callback',
                         type='string',
                         callback=_excel_file_callback)
                    ),
                   ('--requester',
                    'requester',
                    dict(help='User name to use as the owner of the Trac '
                              'ticket.',
                         action='callback',
                         type='string',
                         callback=_user_callback),
                   )
                   ]

    @classmethod
    def finalize(cls, tool):
        if not tool.has_errors():
            lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
            lib_agg.add(tool.return_value)


class LibraryIsoGeneratorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Creates ISOs for a library creation ISO request.
    """

    @classmethod
    def get_library(cls, value):
        agg = get_root_aggregate(IMoleculeDesignLibrary)
        agg.filter = eq(label=value)
        return list(agg.iterator())[0]

    _library_callback = LazyOption(lambda value: # pylint: disable=W0108
                            LibraryIsoGeneratorToolCommand.get_library(value))

    name = 'librarycreationisogenerator'
    tool = 'thelma.automation.tools.libcreation.ticket:LibraryCreationIsoCreator'
    option_defs = [('--library-name',
                    'molecule_design_library',
                    dict(help='Name of the molecule design library whose ' \
                              'ISOs to create.',
                        action='callback',
                        type='string',
                        callback=_library_callback),
                    )
                   ]

class LibraryIsoPopulatorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232

    @classmethod
    def get_library(cls, value):
        agg = get_root_aggregate(IMoleculeDesignLibrary)
        agg.filter = eq(label=value)
        return list(agg.iterator())[0]

    @classmethod
    def split_string(cls, value):
        return value.split(',')

    _library_callback = LazyOption(lambda value: # pylint: disable=W0108
                            LibraryIsoPopulatorToolCommand.get_library(value))

    _excluded_racks_callback = LazyOption(lambda value: # pylint: disable=W0108
                            LibraryIsoPopulatorToolCommand.split_string(value))

    _requested_tube_callback = LazyOption(lambda value: # pylint: disable=W0108
                            LibraryIsoPopulatorToolCommand.split_string(value))

    name = 'librarycreationisopopulator'
    tool = 'thelma.automation.tools.libcreation.iso:LibraryCreationIsoPopulator'
    option_defs = [('--library-name',
                    'molecule_design_library',
                    dict(help='Name of the molecule design library whose ' \
                         'ISOs to populate.',
                        action='callback',
                        type='string',
                        callback=_library_callback),
                    ),
                   ('--number-isos',
                    'number_isos',
                    dict(help='The number of ISOs you want to populate ' \
                              '(includes an optimization step).',
                         type='int')
                    ),
                   ('--excluded-racks',
                    'excluded_racks',
                    dict(help='Racks from you do not want to pick tubes ' \
                              '(comma-separated, no white spaces).',
                         action='callback',
                         type='string',
                         callback=_excluded_racks_callback)
                    ),
                   ('--requested-tubes',
                    'requested_tubes',
                    dict(help='Tubes you prefer to be used ' \
                              '(comma-separated, no white spaces).',
                         action='callback',
                         type='string',
                         callback=_requested_tube_callback),
                   )
                   ]

    @classmethod
    def finalize(cls, tool):
        if not tool.has_errors():
            labels = []
            for lci in tool.return_value:
                labels.append(lci.label)
            msg = '%i ISO(s) have been created: %s' % (
                                            len(labels), ', '.join(labels))
            print msg


class LibraryCreationLayoutWriterToolCommand(ToolCommand): # no __init__ pylint: disable=W0232

    @classmethod
    def get_iso(cls, value):
        agg = get_root_aggregate(ILibraryCreationIso)
        agg.filter = eq(label=value)
        return list(agg.iterator())[0]

    _iso_callback = LazyOption(lambda value: # pylint: disable=W0108
                    LibraryCreationLayoutWriterToolCommand.get_iso(value))

    name = 'librarycreationisolayoutwriter'
    tool = 'thelma.automation.tools.libcreation.iso:LibraryCreationIsoLayoutWriter'
    option_defs = [('--iso',
                    'library_creation_iso',
                    dict(help='Label of the library creation ISO whose ' \
                              'layout you want to print.',
                        action='callback',
                        type='string',
                        callback=_iso_callback),
                    )]

    # TODO: think about how to make this prettier
    @classmethod
    def finalize(cls, tool):
        if not tool.has_errors():
            iso_label = tool.library_creation_iso.label
            fn = '/Users/berger/Desktop/%s.csv' % (iso_label)
            o = open(fn, 'w')
            stream = tool.return_value
            stream.seek(0)
            o.write(stream.read())
            o.close()


class LibraryCreationWorklistWriterToolCommand(ToolCommand): # no __init__ pylint: disable=W0232

    @classmethod
    def get_iso(cls, value):
        agg = get_root_aggregate(ILibraryCreationIso)
        agg.filter = eq(label=value)
        return list(agg.iterator())[0]

    @classmethod
    def get_tube_destination_map(cls, value):
        barcodes = value.split(',')
        # TODO: make configurable
        tube_racks = dict()
        number_quadrants = 4
        number_mds = 3
        for sector_index in range(number_quadrants):
            quadrant_barcodes = []
            i = 0
            while i < number_mds:
                barcode = barcodes.pop(0)
                quadrant_barcodes.append(barcode)
                i += 1
            tube_racks[sector_index] = quadrant_barcodes
        return tube_racks

    @classmethod
    def get_pool_stock_rack_barcodes(cls, value):
        barcodes = value.split(',')
        pool_racks = dict()
        number_quadrants = 4
        for sector_index in range(number_quadrants):
            barcode = barcodes[sector_index]
            pool_racks[sector_index] = barcode
        return pool_racks

    _iso_callback = LazyOption(lambda value: # pylint: disable=W0108
                    LibraryCreationWorklistWriterToolCommand.get_iso(value))

    _tube_destination_racks_callback = LazyOption(
                                lambda value: # pylint: disable=W0108
                    LibraryCreationWorklistWriterToolCommand.\
                                            get_tube_destination_map(value))


    _pool_stock_rack_callback = LazyOption(lambda value: # pylint: disable=W0108
                    LibraryCreationWorklistWriterToolCommand.\
                                            get_pool_stock_rack_barcodes(value))

    name = 'librarycreationworklistwriter'
    tool = 'thelma.automation.tools.libcreation.writer:LibraryCreationWorklistWriter'
    option_defs = [('--iso',
                    'library_creation_iso',
                    dict(help='Label of the library creation ISO for which ' \
                              'you want to get worklist files.',
                        action='callback',
                        type='string',
                        callback=_iso_callback),
                    ),
                   ('--tube-destination-racks',
                    'tube_destination_racks',
                    dict(help='The barcodes for the tube handler destination ' \
                              'racks (for the single molecule design tubes - ' \
                              'these racks have to be empty). Pass the ' \
                              'barcodes comma-separated and without white ' \
                              'spaces).',
                        action='callback',
                        type='string',
                        callback=_tube_destination_racks_callback)
                    ),
                   ('--pool-stock-racks',
                    'pool_stock_racks',
                    dict(help='Barcodes for the racks that will contain ' \
                              'the pool stock tubes. These racks have to ' \
                              'have empty tubes in defined positions. Pass ' \
                              'ordered by sector, comma-separated and ' \
                              'without white spaces).',
                         action='callback',
                         type='string',
                         callback=_pool_stock_rack_callback)
                    ),
                   ]

#    @classmethod
#    def finalize(cls, tool):
#        if not tool.has_errors():
#            uploader = LibraryCreationTicketWorklistUploader(
#                        library_creation_iso=tool.library_creation_iso,
#                        file_map=tool.return_value)
#            uploader.send_request()
#            if not uploader.transaction_completed():
#                msg = 'Error during transmission to Trac!'
#                print msg


class LibraryCreationExecutorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232

    @classmethod
    def get_iso(cls, value):
        agg = get_root_aggregate(ILibraryCreationIso)
        agg.filter = eq(label=value)
        return list(agg.iterator())[0]

    _iso_callback = \
        LazyOption(lambda value: # pylint: disable=W0108
                   LibraryCreationExecutorToolCommand.get_iso(value))
    _user_callback = \
        LazyOption(lambda value: # pylint: disable=W0108
                   get_root_aggregate(IUser).get_by_slug(value))

    name = 'librarycreationexecutor'
    tool = 'thelma.automation.tools.libcreation.execution:LibraryCreationExecutor'
    option_defs = [('--iso',
                    'library_creation_iso',
                    dict(help='Label of the library creation ISO which you ' \
                              'want to update.',
                        action='callback',
                        type='string',
                        callback=_iso_callback),
                    ),
                   ('--user',
                    'user',
                    dict(help='User name of the user who performs the update.',
                         action='callback',
                         type='string',
                         callback=_user_callback),
                   )
                   ]

#    @classmethod
#    def finalize(cls, tool):
#        if not tool.has_errors():
#            reporter = LibraryCreationStockTransferReporter(
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


class XL20DummyToolCommand(ToolCommand): # no __init__ pylint: disable=W0232

    _wl_file_callback = LazyOption(lambda value: open(value, 'rb'))

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
    def finalize(cls, tool):
        if not tool.has_errors():
            fn = '/Users/berger/Desktop/xl20out.txt'
            o = open(fn, 'w')
            stream = tool.return_value
            stream.seek(0)
            o.write(stream.read())
            o.close()
