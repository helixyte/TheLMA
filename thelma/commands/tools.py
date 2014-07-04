"""
Run tool command.
"""
import logging
import optparse
import os
import sys

from pyramid.path import DottedNameResolver
from pyramid.registry import Registry
from pyramid.testing import DummyRequest
from sqlalchemy import event
from sqlalchemy.orm.session import Session
import transaction

from everest.entities.utils import get_root_aggregate
from everest.mime import JsonMime
from everest.querying.specifications import cntd
from everest.querying.specifications import eq # pylint: disable=W0611
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.rdb import Session as session_maker
from everest.representers.utils import as_representer
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection_class
from everest.utils import classproperty
from paste.deploy import appconfig # pylint: disable=E0611,F0401
from paste.script.command import Command # pylint: disable=E0611,F0401
from thelma.automation.tools.iso.libcreation.report import \
    LibraryCreationStockTransferReporter
from thelma.automation.tools.iso.libcreation.report import \
    LibraryCreationTicketWorklistUploader
from thelma.automation.tools.iso.poolcreation.execution import \
    StockSampleCreationStockTransferReporter
from thelma.interfaces import IMoleculeDesignPool
from thelma.automation.tools.iso.poolcreation.writer \
    import StockSampleCreationTicketWorklistUploader
from thelma.automation.tools.stock.sampleregistration import \
    IMoleculeDesignPoolRegistrationItem
from thelma.automation.tools.stock.sampleregistration import \
    IMoleculeDesignRegistrationItem
from thelma.automation.tools.stock.sampleregistration import \
    ISampleRegistrationItem
from thelma.automation.tools.stock.sampleregistration import \
    ISupplierSampleRegistrationItem
from thelma.automation.tools.writers import write_zip_archive
from thelma.interfaces import IIsoJob
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IPipettingSpecs
from thelma.interfaces import IPlannedWorklist
from thelma.interfaces import IRack
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import IStockSampleCreationIso
from thelma.interfaces import IStockSampleCreationIsoRequest
from thelma.interfaces import ITube
from thelma.interfaces import ITubeTransferWorklist
from thelma.interfaces import IUser
from thelma.run import create_config
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['EmptyTubeRegistrarToolCommand',
           'MetaToolCommand',
           'ToolCommand',
           'XL20ExecutorToolCommand',
           ]


class LazyOptionCallback(object):
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


def make_lazy_option_def(option_name, help_string, option_type,
                         parameter_name=None):
    def opt_callback(cls, value, options): # pylint: disable=W0613
        agg = get_root_aggregate(option_type)
        if not ',' in value:
            val = agg.get_by_slug(value)
        else:
            agg.filter = cntd(slug=value.split(','))
            val = [ent for ent in agg]
        return val
    if parameter_name is None:
        parameter_name = option_name.replace('-', '_')
    lazy_callback = LazyOptionCallback(opt_callback)
    return ('--%s' % option_name,
            parameter_name,
            dict(help=help_string,
                 action='callback',
                 type='string',
                 callback=lazy_callback)
            )


def make_lazy_user_option_def(option_name='user',
                              parameter_name=None,
                              help_string='User name running the tool.'):
    return make_lazy_option_def(option_name, help_string, IUser,
                                parameter_name=parameter_name)


def make_lazy_file_option_def(option_name='file',
                              parameter_name=None,
                              help_string='File to open.',
                              read_on_open=False):
    if parameter_name is None:
        parameter_name = option_name.replace('-', '_')
    if read_on_open:
        cb = lambda cls, value, options: open(value, 'rb').read()
    else:
        cb = lambda cls, value, options: open(value, 'rb')
    lazy_callback = LazyOptionCallback(cb)
    return ('--%s' % option_name,
            parameter_name,
            dict(help=help_string,
                 action='callback',
                 type='string',
                 callback=lazy_callback)
            )


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

    class ToolOption(optparse.Option):
        ATTRS = optparse.Option.ATTRS + ['pass_to_tool']

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
        parser.option_class = cls.ToolOption
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
        kw = {}
        for arg_name in arg_names:
            arg_value = getattr(opts, arg_name)
            if isinstance(arg_value, LazyOptionCallback):
                arg_value = arg_value.initialize(self.__target_class, opts)
                setattr(opts, arg_name, arg_value)
            kw[arg_name] = arg_value
        # Remove options that are for command use only.
        for opt in self.parser.option_list:
            if opt.dest in kw and opt.pass_to_tool is False:
                del kw[opt.dest]
        tool = tool_cls(**kw)
        try:
            tool.run()
        except:
            transaction.abort()
            raise
        else:
            if tool.has_errors():
                err_msgs = tool.get_messages()
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
               callback=LazyOptionCallback(
                            lambda cls, value, options:
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
    tool = 'thelma.automation.tools.stock.sampleregistration:' \
           'SampleRegistrar'
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
    tool = 'thelma.automation.tools.stock.sampleregistration:' \
           'SupplierSampleRegistrar'
    option_defs = SampleRegistrarCommand.option_defs
    registration_resource = ISupplierSampleRegistrationItem


class XL20ExecutorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the XL20 executor that executes tube transfers on DB level.
    """
    name = 'xl20executor'
    tool = 'thelma.automation.tools.worklists.tubehandler:XL20Executor'
    option_defs = \
        [make_lazy_file_option_def(option_name='output-file',
                                   parameter_name='output_file_stream',
                                   help_string='The XL20 output file ' \
                                               'containing the transfer ' \
                                               'data.'),
         make_lazy_user_option_def(help_string='User name to use as the '
                                               'owner of the Trac ticket.'),
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
    _excluded_racks_callback = \
        LazyOptionCallback(lambda cls, value, options:
                                [el.strip() for el in value.split(',')])
    name = 'stockcondenser'
    tool = 'thelma.automation.tools.stock.condense:StockCondenser'
    option_defs = [('--number-racks',
                    'racks_to_empty',
                    dict(help='Name of the molecule design library to create.',
                         type='int')
                    ),
                   ('--excluded-racks',
                    'excluded_racks',
                    dict(help='Barcodes of racks to be excluded from tube '
                              'picking (comma-separated).',
                         action='callback',
                         type='string',
                         callback=_excluded_racks_callback)
                    ),
                   ('--output-dir',
                    'output_dir',
                    dict(help='Directory to write the condense worklists to.',
                         type='string'),
                    )
                   ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            write_zip_archive(tool.return_value, options.outut_dir)


class StockSampleCreationIsoRequestGenerator(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the stock sample ISO Request Generator tool.
    """
    name = 'stocksamplecreationisorequestgenerator'
    tool = 'thelma.automation.tools.iso.poolcreation.generation:StockSampleCreationIsoRequestGenerator'
    option_defs = \
        [('--iso-request-label',
          'iso_request_label',
          dict(help='Name of stock sample ISO request to create.'
               )
          ),
         make_lazy_file_option_def(option_name='excel-file',
                                   parameter_name='stream',
                                   help_string='Excel file to load.',
                                   read_on_open=True),
         ('--target-volume',
          'target_volume',
          dict(help='The final volume for the new pool stock '
               'samples in ul.',
               type='int'),
          ),
         ('--target-concentration',
          'target_concentration',
          dict(help='The final pool concentration for the new pool '
               'stock samples in nM.',
               type='int'),
          )
         ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            ir_agg = get_root_aggregate(IStockSampleCreationIsoRequest)
            ir_agg.add(tool.return_value)



class LibraryIsoRequestGeneratorToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    """
    Runs the library ISO creator tool.
    """
    name = 'librarycreationisorequestgenerator'
    tool = 'thelma.automation.tools.iso.libcreation.requestgenerator' \
           ':LibraryCreationIsoRequestGenerator'
    option_defs = \
        [('--library-name',
          'library_name',
          dict(help='Name of the molecule design library to create.'
               )
          ),
         make_lazy_file_option_def(option_name='excel-file',
                                   parameter_name='stream',
                                   help_string='Excel file to load.',
                                   read_on_open=True),
         make_lazy_user_option_def(option_name='requester',
                                   help_string='User name to use as the ' \
                                               'owner of the Trac ticket.'
                                   ),
         ('--number-designs',
          'number_designs',
          dict(help='Number of molecule designs per library sample.',
               type='int',
               ),
          ),
         ('--number-aliquots',
          'number_aliquots',
          dict(help='Number of aliquots to generate per library layout.',
               type='int',
               ),
          ),
         ('--preparation-plate-volume',
          'preparation_plate_volume',
          dict(help='Volume for the preparation plates in ul.',
               type='float'),
          ),
         ('--create-pool-racks',
          'create_pool_racks',
          dict(help='Flag indicating that pool stock racks should be created.',
               action='store_true'),
          ),
       ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
            lib_agg.add(tool.return_value)


class _IsoRequestOperationTool(ToolCommand): # no __init__ pylint: disable=W0232
    @classmethod
    def get_iso_request(cls, value):
        ir_agg = get_root_aggregate(IStockSampleCreationIsoRequest)
        ir_agg.filter = eq(label=value)
        return ir_agg.iterator().next()

    iso_request_callback = \
        LazyOptionCallback(lambda cls, value, options: # pylint: disable=W0108
                                StockSampleCreationIsoGeneratorToolCommand \
                                    .get_iso_request(value))

    option_defs = [('--iso-request-label',
                    'iso_request',
                    dict(help='The label of the ISO request for which ISOs ' \
                               'will be created.',
                        action='callback',
                        type='string',
                        callback=iso_request_callback),
                    ),
                   ]


def _ticket_numbers_callback(option, name, value, parser): # pylint: disable=W0613
    nums = [int(num.strip()) for num in value.split(',')]
    setattr(parser.values, option.dest, nums)


class StockSampleCreationIsoGeneratorToolCommand(_IsoRequestOperationTool): # no __init__ pylint: disable=W0232
    """
    Creates ISOs for a pool stock sample creation ISO request.
    """
    name = 'stocksamplecreationisogenerator'
    tool = 'thelma.automation.tools.iso.poolcreation.generation:' \
           'StockSampleCreationIsoGenerator'
    option_defs = _IsoRequestOperationTool.option_defs + \
                  [('--ticket-numbers',
                    'ticket_numbers',
                    dict(help='The ticket numbers for the ISOs to generate',
                         action='callback',
                         type='string',
                         callback=_ticket_numbers_callback),
                    ),
                   make_lazy_user_option_def(
                                option_name='reporter',
                                help_string='Reporter of the tickets, if ' \
                                            'tickets should be created for ' \
                                            'the new ISOs.',
                                   ),
                   ]


class LibraryCreationIsoGeneratorToolCommand(
                                StockSampleCreationIsoGeneratorToolCommand): # no __init__ pylint: disable=W0232
    """
    Creates ISOs for a library creation ISO request.
    """
    name = 'librarycreationisogenerator'
    tool = 'thelma.automation.tools.iso.libcreation.isogenerator' \
           ':LibraryCreationIsoGenerator'


class StockSampleCreationIsoJobCreatorToolCommand(_IsoRequestOperationTool): # no __init__ pylint: disable=W0232
    name = 'stocksamplecreationisojobcreator'
    tool = 'thelma.automation.tools.iso.poolcreation.jobcreator' \
           ':StockSampleCreationIsoJobCreator'

    @classmethod
    def split_string(cls, value):
        return value.split(',')

    _excluded_racks_callback = \
        LazyOptionCallback(lambda cls, value, options: cls.split_string(value))

    _requested_tubes_callback = \
        LazyOptionCallback(lambda cls, value, options: cls.split_string(value))

    option_defs = _IsoRequestOperationTool.option_defs + \
        [make_lazy_user_option_def(option_name='job-owner',
                                   help_string='User name of the user the ' \
                                               'job will be assigned to.'),
         ('--number-isos',
          'number_isos',
          dict(help='The number of ISOs ordered.',
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
               callback=_requested_tubes_callback),
         )
         ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            ij_agg = get_root_aggregate(IIsoJob)
            ij_agg.add(tool.return_value)


class LibraryCreationIsoJobCreatorToolCommand(
                                StockSampleCreationIsoJobCreatorToolCommand): # no __init__ pylint: disable=W0232
    name = 'librarycreationisojobcreator'
    tool = 'thelma.automation.tools.iso.libcreation.jobcreator' \
           ':LibraryCreationIsoJobCreator'


class _IsoOperationToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    @classmethod
    def get_iso(cls, value):
        agg = get_root_aggregate(IStockSampleCreationIso)
        agg.filter = eq(label=value)
        return list(agg.iterator())[0]

    iso_callback = \
        LazyOptionCallback(lambda cls, value, options: cls.get_iso(value)) # pylint: disable=W0108

    option_defs = [('--iso',
                    'iso',
                    dict(help='Label of the pool creation ISO for which ' \
                              'you want to get worklist files.',
                        action='callback',
                        type='string',
                        callback=iso_callback),
                    ),
                   ]



def _rack_barcode_list_callback(option, name, value, parser): # pylint: disable=W0613
    bcs = value.split(',')
    setattr(parser.values, option.dest, bcs)


class StockSampleCreationIsoWorklistWriterToolCommand(_IsoOperationToolCommand): # no __init__ pylint: disable=W0232
    name = 'stocksamplecreationisoworklistwriter'
    tool = 'thelma.automation.tools.iso.poolcreation.writer:' \
           'StockSampleCreationIsoWorklistWriter'

    option_defs = _IsoOperationToolCommand.option_defs + \
                  [('--single-stock-racks',
                    'single_stock_racks',
                    dict(help='Comma-separated list of barcodes for the ' \
                              'stock racks containing the single ' \
                              'design samples that serve as sources' \
                              'for the pools to create (must be empty).',
                        action='callback',
                        type='string',
                        callback=_rack_barcode_list_callback)
                    ),
                   ('--pool-stock-rack',
                    'pool_stock_rack_barcode',
                    dict(help='Barcode of the rack that will contain ' \
                              'the pool stock tubes. This rack has to ' \
                              'have empty tubes in defined positions. '
                              'If this is not given, the pools are created ' \
                              'directly in sector preparation plates.',
                         type='string')
                    ),
                   ('--use-single-source-rack',
                    'use_single_source_rack',
                    dict(help='If there are only few pools to be created the ' \
                              'user might want to use a single stock rack.',
                         action='store_true',
                         default=False)
                   )]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors() and not options.simulate:
            uploader = StockSampleCreationTicketWorklistUploader(tool)
            uploader.run()
            if not uploader.transaction_completed():
                msg = 'Error during transmission to Trac!'
                print msg


class LibraryCreationIsoWorklistWriterToolCommand(_IsoOperationToolCommand): # no __init__ pylint: disable=W0232
    name = 'librarycreationisoworklistwriter'
    tool = 'thelma.automation.tools.iso.libcreation.writer' \
           ':LibraryCreationIsoWorklistWriter'

    option_defs = \
        StockSampleCreationIsoWorklistWriterToolCommand.option_defs[:-2] + \
        [('--pool-stock-racks',
          'pool_stock_racks',
          dict(help='Barcodes for the racks that will contain ' \
                    'the pool stock tubes. These racks have to ' \
                    'have empty tubes in defined positions. Pass ' \
                    'ordered by sector, comma-separated and ' \
                    'without white spaces).',
               action='callback',
               type='string',
               callback=_rack_barcode_list_callback)
          ),
         ('--include-dummy-output',
          'include_dummy_output',
          dict(help='Flag indicating that the output should include a dummy '
                    'tube handler output file for in silico tube handling.',
               action='store_true',
               default=False),
          ),
         ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors(): #  and not options.simulate:
            uploader = LibraryCreationTicketWorklistUploader(tool)
            uploader.run()
            if not uploader.transaction_completed():
                msg = 'Error during transmission to Trac!'
                print msg


class StockSampleCreationExecutorToolCommand(_IsoOperationToolCommand): # no __init__ pylint: disable=W0232
    name = 'stocksamplecreationexecutor'
    tool = 'thelma.automation.tools.iso.poolcreation.execution:' \
           'StockSampleCreationExecutor'

    option_defs = _IsoOperationToolCommand.option_defs + \
        [make_lazy_user_option_def(help_string='User name of the user who '
                                               'performs the update.'),
         ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors() and not options.simulate:
            reporter = StockSampleCreationStockTransferReporter(tool)
            reporter.run()
            if not reporter.transaction_completed():
                msg = 'Error during transmission to Trac!'
                print msg



class LibraryCreationIsoExecutorToolCommand(
                                StockSampleCreationExecutorToolCommand): # no __init__ pylint: disable=W0232
    name = 'librarycreationisoexecutor'
    tool = 'thelma.automation.tools.iso.libcreation.executor:' \
           'LibraryCreationIsoExecutor'

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors() and not options.simulate:
            reporter = LibraryCreationStockTransferReporter(tool)
            reporter.run()
            if not reporter.transaction_completed():
                msg = 'Error during transmission to Trac!'
                print msg


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

    name = 'rackscanningadjuster'
    tool = 'thelma.automation.tools.stock.rackscanning:RackScanningAdjuster'

    option_defs = \
        [('--scanfiles',
          'rack_scanning_files',
          dict(help='This can be a single file, a zip file or a ' \
                    'directory (in which case all *.TXT files are ' \
                    'read).',
               type='string',
               ),
          ),
         ('--adjust-db',
          'adjust_database',
          dict(help='If set, the DB will be adjusted; else, only a report ' \
                    'will be generated.',
               action='store_true',
               default=False,
               ),
          ),
         make_lazy_user_option_def(help_string='User name who runs the '
                                               'update (if applicable).'),
         ]


class XL20DummyToolCommand(ToolCommand): # no __init__ pylint: disable=W0232
    name = 'xl20dummy'
    tool = 'thelma.automation.tools.dummies:XL20Dummy'
    option_defs = \
        [make_lazy_file_option_def(option_name='worklist-file',
                                   parameter_name='xl20_worklist_stream',
                                   help_string='The XL20 worklist file '
                                               'containing the planned ' \
                                               'tube transfers.'),
         ('--output-file',
          'output_file',
          dict(help='Output file to write to.',
               type='string'),
          ),
         ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            fn = options.output_file
            stream = tool.return_value
            stream.seek(0)
            with open(fn, 'w') as out_file:
                out_file.write(stream.read())


class CustomLiquidTransferToolCommand(ToolCommand):
    name = 'customliquidtransfertool'
    tool = 'thelma.automation.tools.worklists.custom:CustomLiquidTransferTool'
    option_defs = \
        [make_lazy_file_option_def(option_name='excel-file',
                                   parameter_name='stream',
                                   help_string='Excel file to load.',
                                   read_on_open=True),
         ('--mode',
          'mode',
          dict(help='"execute" (requires user) or "print"',
               type='string')
          ),
         make_lazy_user_option_def(help_string='User name who runs the '
                                               'update (if mode is set '
                                               'to "execution").'),
         ('--output-dir',
          'output_dir',
          dict(help='Directory to write the condense worklists to.',
               type='string'),
          ),
         ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            write_zip_archive(tool.return_value, options.output_dir)


class CustomLiquidTransferWorklistExecutor(ToolCommand):

    name = 'customliquidtransferexecutor'
    tool = 'thelma.automation.tools.worklists.custom:' \
           'CustomLiquidTransferExecutor'
    option_defs = \
        [make_lazy_file_option_def(option_name='excel-file',
                                   parameter_name='stream',
                                   help_string='Excel file to load.',
                                   read_on_open=True),
         make_lazy_user_option_def(help_string='User name who runs the '
                                               'update.'),
                   ]


class SampleDilutionWorklistExecutor(ToolCommand):
    name = 'sampledilutionworklistexecutor'
    tool = 'thelma.automation.tools.worklists.execution:' \
           'SampleDilutionWorklistExecutor'

    option_defs = [make_lazy_option_def('transfer',
                                        'ID of the planned dilution worklist '
                                        'to be executed.',
                                        IPlannedWorklist,
                                        parameter_name='planned_worklist'),
                   make_lazy_option_def('target-rack',
                                        'Barcode of the target rack.',
                                        IRack),
                   make_lazy_option_def('pipetting-specs',
                                        'Specs of the pipetting device to '
                                        'use',
                                        IPipettingSpecs),
                   make_lazy_user_option_def(),
                   make_lazy_option_def('reservoir-specs',
                                        'Specs of the buffer reservoir',
                                        IReservoirSpecs),
                   ]


class RackSampleTransferExecutor(ToolCommand):
    name = 'racksampletransferexecutor'
    tool = 'thelma.automation.tools.worklists.execution:' \
           'RackSampleTransferExecutor'

    option_defs = [make_lazy_option_def('target-rack',
                                        'Barcode of the target rack.',
                                        IRack),
                   make_lazy_option_def('pipetting-specs',
                                        'Specs of the pipetting device to '
                                        'use',
                                        IPipettingSpecs),
                   make_lazy_user_option_def(),
                   make_lazy_option_def('transfer',
                                        'ID of the planned rack sample '
                                        'transfer to be executed.',
                                        IPlannedWorklist,
                                        parameter_name=
                                            'planned_rack_sample_transfer'),
                   make_lazy_option_def('source-rack',
                                        'Barcode of the source rack.',
                                        IRack),
                   ]


class StockSampleCreationTubePickerCommand(ToolCommand):
    name = 'stocksamplecreationtubepicker'
    tool = 'thelma.automation.tools.iso.poolcreation.tubepicking:' \
           'StockSampleCreationTubePicker'

    @classmethod
    def get_ids_from_file(cls, file_name):
        with open(file_name, 'rU') as input_file:
            ids = [int(line.strip()) for line in input_file]
        agg = get_root_aggregate(IMoleculeDesignPool)
        agg.filter = cntd(id=ids)
        return list(iter(agg))

    ids_callback = LazyOptionCallback(lambda cls, value, options: # pylint: disable=W0108
                                        cls.get_ids_from_file(value))

    option_defs = \
        [('--pool-id-file',
          'molecule_design_pools',
          dict(help='File with molecule design pool IDs.',
               type='string',
               action='callback',
               callback=ids_callback
               )
          ),
         ('--output-file',
          'output_file',
          dict(help='File to write the picked candidates to.',
               default='tube_picker_candidates.csv',
               type='string',
               pass_to_tool=False)
          ),
         ('--stock-concentration',
          'single_design_concentration',
          dict(help='Stock sample concentration of the tubes to pick.',
               type='float'),
          ),
         ('--stock-volume',
          'take_out_volume',
          dict(help='Requested stock volume to transfer.',
               type='float'),
          ),
         ]

    @classmethod
    def finalize(cls, tool, options):
        if not tool.has_errors():
            fn = options.output_file
            out_lines = ['pool_id,tube_barcode,rack_barcode,rack_position'
                         ',volume']
            attrs = ('pool_id', 'tube_barcode', 'rack_barcode',
                     'rack_position', 'volume')
            fmt_str = ','.join(['%%(%s)s' % attr for attr in attrs])
            for cand in tool.return_value:
                out_lines.append(fmt_str
                                 % dict([(attr, getattr(cand, attr))
                                         for attr in attrs]))
            with open(fn, 'wb') as out_file:
                out_file.write(os.linesep.join(out_lines))
