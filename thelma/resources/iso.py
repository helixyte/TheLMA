"""
ISO resources.

AAB, Jun 2011
"""
from datetime import datetime

from everest.entities.interfaces import IEntity
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import DescendingOrderSpecification
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.interfaces import IDataElement
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.resources.staging import create_staging_collection
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.tools.iso import get_job_creator
from thelma.automation.tools.iso import lab
from thelma.automation.tools.iso.lab import get_stock_rack_recyler
from thelma.automation.tools.iso.lab import get_worklist_executor
from thelma.automation.tools.iso.lab.tracreporting import LabIsoStockTransferReporter
from thelma.automation.tools.metadata.ticket import IsoRequestTicketAccepter
from thelma.automation.tools.metadata.ticket import IsoRequestTicketReassigner
from thelma.automation.tools.metadata.ticket import IsoRequestTicketReopener
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.interfaces import IExperimentMetadata
from thelma.interfaces import IIsoJob
from thelma.interfaces import ILabIso
from thelma.interfaces import ILabIsoRequest
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPoolSet
from thelma.interfaces import IPlate
from thelma.interfaces import IRack
from thelma.interfaces import IRackLayout
from thelma.interfaces import IStockRack
from thelma.interfaces import IUser
from thelma.models.experiment import EXPERIMENT_METADATA_TYPES
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import Iso
from thelma.models.iso import IsoPreparationPlate
from thelma.models.job import IsoJob
from thelma.models.utils import get_current_user
from thelma.resources.base import RELATION_BASE_URL
from thelma.utils import run_tool
from thelma.utils import run_trac_tool


#from thelma.automation.tools.libcreation.iso import LibraryCreationIsoPopulator
__docformat__ = 'reStructuredText en'

__all__ = ['IsoCollection',
           'IsoMember',
           'LabIsoMember',
           'StockSampleCreationIsoMember',
           'IsoRequestCollection',
           'IsoRequestMember',
           'LabIsoRequestMember',
           'StockSampleCreationIsoRequestMember',
           'IsoStockRackMember',
           ]


class IsoMember(Member):
    relation = "%s/iso" % RELATION_BASE_URL
    title = attribute_alias('label')
    iso_type = terminal_attribute(str, 'label')
    label = terminal_attribute(str, 'label')
    status = terminal_attribute(str, 'status')
    rack_layout = member_attribute(IRackLayout, 'rack_layout')
    iso_job = member_attribute(IIsoJob, 'iso_job')
    number_stock_racks = terminal_attribute(int, 'number_stock_racks')
    molecule_design_pool_set = member_attribute(IMoleculeDesignPoolSet,
                                                'molecule_design_pool_set')
    optimizer_excluded_racks = terminal_attribute(str,
                                                  'optimizer_excluded_racks')
    optimizer_required_racks = terminal_attribute(str,
                                                  'optimizer_required_racks')
    preparation_plates = collection_attribute(IPlate,
                                              'preparation_plates')
    aliquot_plates = collection_attribute(IPlate,
                                          'aliquot_plates')
    stock_racks = collection_attribute(IStockRack, 'stock_racks')

    def update(self, data):
        if IDataElement.providedBy(data): # pylint: disable=E1101
            raise SyntaxError('Should not get here.')
        else:
            Member.update(self, data)


class LabIsoMember(IsoMember):
    relation = "%s/lab-iso" % RELATION_BASE_URL

    iso_request = member_attribute(ILabIsoRequest, 'iso_request')


class StockSampleCreationIsoMember(IsoMember):
    relation = "%s/stock-sample-creation-iso" % RELATION_BASE_URL
    ticket_number = terminal_attribute(int, 'ticket_number')
    layout_number = terminal_attribute(int, 'layout_number')


class IsoCollection(Collection):
    title = 'ISOs'
    root_name = 'isos'
    description = 'Manage ISOs'
    default_order = AscendingOrderSpecification('label')


class LabIsoCollection(IsoCollection):
    title = 'Lab ISOs'
    root_name = 'lab-isos'
    description = 'Manage Lab ISOs'


class IsoRequestMember(Member):
    relation = "%s/iso-request" % RELATION_BASE_URL
    iso_type = terminal_attribute(str, 'iso_type')
    label = terminal_attribute(str, 'label')
    owner = terminal_attribute(str, 'owner')
    expected_number_isos = terminal_attribute(int, 'expected_number_isos')
    number_aliquots = terminal_attribute(int, 'number_aliquots')
    iso_jobs = collection_attribute(IIsoJob, 'iso_jobs')

    @property
    def title(self):
        return 'Base ISO Request'


class LabIsoRequestMember(IsoRequestMember):
    relation = "%s/lab-iso-request" % RELATION_BASE_URL
    isos = collection_attribute(ILabIso, 'isos')
    delivery_date = terminal_attribute(datetime, 'delivery_date')
    requester = member_attribute(IUser, 'requester')
    experiment_metadata = member_attribute(IExperimentMetadata,
                                           'experiment_metadata')
#    experiment_metadata_type = \
#                member_attribute(IExperimentMetadataType,
#                                'experiment_metadata.experiment_metadata_type')
    rack_layout = member_attribute(IRackLayout, 'rack_layout')
    process_job_first = terminal_attribute(bool, 'process_job_first')
    ticket_number = terminal_attribute(int,
                                       'experiment_metadata.ticket_number')

    @property
    def title(self):
        return 'Lab ISO Request'

    def __getitem__(self, name):
        if name == 'completed-iso-plates':
            iso_plates = create_staging_collection(IPlate)
            if self.iso_type == ISO_TYPES.LAB \
               and self.experiment_metadata.experiment_metadata_type.id == \
                                            EXPERIMENT_METADATA_TYPES.MANUAL:
                # For standard, manual ISOs, the preparation plates are used
                # to schedule the experiment jobs.
                for iso in self.isos:
                    if iso.status == ISO_STATUS.DONE:
                        iso_plates.add(iso.iso_preparation_plate)
            else:
                # In all other cases the aliquot plates are used to schedule
                # experiment jobs.
                for iso in self.isos:
                    for plate in iso.iso_aliquot_plates:
                        if iso.status == ISO_STATUS.DONE:
                            iso_plates.add(plate)
            result = iso_plates
        else:
            result = Member.__getitem__(self, name)
        return result

    def update(self, data):
        if IEntity.providedBy(data): # pylint: disable=E1101
            raise SyntaxError('Remove this.')
#            IsoRequestMember.update(self, data)
#            self.get_entity().iso_layout = new_entity.iso_layout
#            self.delivery_date = new_entity.delivery_date
#            self.label = new_entity.label
#            self.expected_number_isos = new_entity.expected_number_isos
#            self.number_aliquots = new_entity.number_aliquots
        else:
            prx = DataElementAttributeProxy(data)
            new_owner = prx.owner
            current_owner = None if self.owner == '' else self.owner
            if new_owner != current_owner:
                self.__process_change_owner(new_owner)
            new_delivery_date = prx.delivery_date
            if new_delivery_date:
                self.delivery_date = new_delivery_date
            if not prx.jobs is None:
                self.__process_iso_jobs(prx.jobs)
            if not prx.isos is None:
                self.__process_isos(prx.isos)

    def create_xl20_worklist(self, entity, rack_barcodes,
                             optimizer_excluded_racks=None,
                             optimizer_required_racks=None,
                             include_dummy_output=False):
        assembler = lab.get_stock_rack_assembler(
                                entity=entity,
                                rack_barcodes=rack_barcodes,
                                excluded_racks=optimizer_excluded_racks,
                                requested_tubes=optimizer_required_racks,
                                include_dummy_output=include_dummy_output)
        return run_tool(assembler)

    def create_pipetting_worklist(self):
        writer = lab.get_worklist_writer(self.get_entity())
        return run_tool(writer)

    def __process_change_owner(self, new_owner):
        trac_tool = None
        if new_owner is None:
            # Reassign to requester for editing the experiment
            # metadata.
            trac_tool = IsoRequestTicketReassigner(
                                    iso_request=self.get_entity(),
                                    completed=False)
            new_owner = ''
        elif new_owner == self.requester.directory_user_id:
            # Close iso request and reassign to requester.
            trac_tool = IsoRequestTicketReassigner(
                                    iso_request=self.get_entity(),
                                    completed=True)
        elif new_owner == STOCKMANAGEMENT_USER:
            pass
        elif new_owner == 'reopen':
            user_id = get_current_user().directory_user_id
            new_owner = user_id + ", " + STOCKMANAGEMENT_USER
            trac_tool = IsoRequestTicketReopener(
                                    iso_request=self.get_entity(),
                                    username=user_id)
        else:
            # Accept iso request.
            tkt_user = new_owner.split(',')[0]
            trac_tool = IsoRequestTicketAccepter(
                                    iso_request=self.get_entity(),
                                    username=tkt_user)
        if not trac_tool is None:
            run_trac_tool(trac_tool)
        self.owner = new_owner

    def __process_iso_jobs(self, iso_jobs_prx):
        for iso_job_prx in iso_jobs_prx:
            status = iso_job_prx.status
            iso_job_id = iso_job_prx.id
            iso_job = self.__find_iso_job(iso_job_id)
            if status.startswith('UPDATE_STOCK_RACKS'):
                self.__update_stock_racks(iso_job, status)
            elif status == 'PIPETTING':
                # Transfer from job stock racks.
                self.__pipetting_iso_or_iso_job(iso_job)
            else:
                raise ValueError('Unknown ISO job status "%s".' % status)

    def __process_isos(self, isos_prx):
        number_of_new_isos = 0
        optimizer_excluded_racks = None
        optimizer_required_racks = None
        for iso_prx in isos_prx:
            status = iso_prx.status
            iso_id = iso_prx.id
            if status == 'NEW':
                number_of_new_isos += 1
                optimizer_excluded_racks = iso_prx.optimizer_excluded_racks
                optimizer_required_racks = iso_prx.optimizer_required_racks
            else:
                # Retrieve the ISO entity and perform an operation on it.
                iso = self.__find_iso(iso_id)
                if status.startswith('UPDATE_STOCK_RACKS'):
                    self.__update_stock_racks(iso, status)
                elif status == 'PIPETTING':
                    self.__pipetting_iso_or_iso_job(iso)
                elif status == 'CLOSE_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.DONE)
                elif status == 'CANCEL_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.CANCELLED)
                elif status == 'REOPEN_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.REOPENED)
                elif status == 'COPY_ISO':
                    self.__copy_iso(iso)
                else:
                    raise ValueError('Unknown ISO status "%s".' % status)
        if number_of_new_isos > 0:
            self.__generate_isos(number_of_new_isos,
                                 optimizer_excluded_racks,
                                 optimizer_required_racks)

    def __update_iso_status(self, iso, new_status):
        iso.status = new_status

    def __copy_iso(self, iso):
        future = get_item_status_future()
        new_iso = Iso(label=iso.label + '_copy',
                      iso_request=iso.iso_request,
                      molecule_design_pool_set=\
                                iso.molecule_design_pool_set,
                      optimizer_excluded_racks=
                                    iso.optimizer_excluded_racks,
                      optimizer_required_racks=
                                    iso.optimizer_required_racks,
                      rack_layout=iso.rack_layout,)
        prep_label = 'p_%s' % (new_iso.label)
        prep_plate = iso.preparation_plate.specs.create_rack(
                            label=prep_label,
                            status=future)
        IsoPreparationPlate(iso=new_iso, plate=prep_plate)
        new_isos = [new_iso]
        job_num = len(iso.iso_request.iso_jobs) + 1
        IsoJob(label='ISO Job %d' % job_num, user=get_current_user(),
               isos=new_isos)

    def __pipetting_iso_or_iso_job(self, iso_or_iso_job):
        user = get_current_user()
        executor = get_worklist_executor(iso_or_iso_job, user)
        result = run_tool(executor,
                          error_prefix='Errors during pipetting. --')
        trac_updater = LabIsoStockTransferReporter(executor=executor)
        run_trac_tool(trac_updater)
        return result

    def __update_stock_racks(self, iso_or_iso_job, status):
        stock_rack_barcodes = status[len('UPDATE_STOCK_RACKS'):].split(';')
        recycler = get_stock_rack_recyler(iso_or_iso_job, stock_rack_barcodes)
        return run_tool(recycler,
                        error_prefix='Invalid stock rack(s)! --')

    def __generate_isos(self, number_of_new_isos,
                        optimizer_excluded_racks, optimizer_requested_tubes):
        if optimizer_excluded_racks is not None:
            optimizer_excluded_racks = optimizer_excluded_racks.split(',')
        if optimizer_requested_tubes is not None:
            optimizer_requested_tubes = optimizer_requested_tubes.split(',')
        iso_request = self.get_entity()
        user = get_current_user()
        if iso_request.iso_type == ISO_TYPES.LAB:
            creator = \
                get_job_creator(iso_request,
                                user,
                                number_of_new_isos,
                                excluded_racks=optimizer_excluded_racks,
                                requested_tubes=optimizer_requested_tubes)
        else:
            raise NotImplementedError('POOL CREATION ISOs not implemented.')
        return run_tool(creator)

    def __find_iso(self, iso_id):
        # Enforce exactly one matching ISO.
        result, = [iso for iso in self.get_entity().isos if iso.id == iso_id]
        return result

    def __find_iso_job(self, iso_job_id):
        # Enforce exactly one matching ISO.
        result, = [iso_job
                   for iso_job in self.get_entity().iso_jobs
                   if iso_job.id == iso_job_id]
        return result


class StockSampleCreationIsoRequestMember(IsoRequestMember):
    relation = "%s/stock-sample-creation-iso-request" % RELATION_BASE_URL
    stock_volume = terminal_attribute(float, 'stock_volume')
    stock_concentration = terminal_attribute(float, 'stock_concentration')
    number_designs = terminal_attribute(int, 'number_designs')
    molecule_design_library = member_attribute(IMoleculeDesignLibrary,
                                               'molecule_design_library')

    @property
    def title(self):
        return 'Stock Sample Generation ISO Request'


class IsoRequestCollection(Collection):
    title = 'ISO Requests'
    root_name = 'iso-requests'
    description = 'Manage ISO Requests'


class LabIsoRequestCollection(IsoRequestCollection):
    title = 'Lab ISO Requests'
    root_name = 'lab-iso-requests'
    description = 'Manage Lab ISO Requests'
    default_order = DescendingOrderSpecification('delivery_date')


class StockSampleIsoRequestCollection(IsoRequestCollection):
    title = 'Stock Sample ISO Requests'
    root_name = 'stock-sample-iso-requests'
    description = 'Manage Stock Sample ISO Requests'


class StockRackMember(Member):
    relation = "%s/stock-rack" % RELATION_BASE_URL

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.__class__, entity.id)

    label = terminal_attribute(int, 'label')
    rack = member_attribute(IRack, 'rack')


class IsoStockRackMember(StockRackMember):
    relation = "%s/iso-stock-rack" % RELATION_BASE_URL


class IsoSectorStockRackMember(StockRackMember):
    relation = "%s/iso-sector-stock-rack" % RELATION_BASE_URL

    index = terminal_attribute(int, 'sector_index')


class StockRackCollection(Collection):
    title = 'Stock Racks'
    root_name = 'stock-racks'


class IsoStockRackCollection(StockRackCollection):
    title = 'ISO Stock Racks'
    root_name = 'iso-stock-racks'
    description = 'Manage ISO stock racks.'


class IsoSectorStockRackCollection(StockRackCollection):
    title = 'ISO Sector Stock Racks'
    root_name = 'iso-sector-stock-racks'
    description = 'Manage ISO sector stock racks.'
