"""
ISO resources.

AAB, Jun 2011
"""

from datetime import datetime
from everest.interfaces import IUserMessageNotifier
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
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.threadlocal import get_current_registry
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.tools.iso import get_job_creator
from thelma.automation.tools.iso.lab import get_stock_rack_recyler
from thelma.automation.tools.iso.lab import get_worklist_executor
from thelma.automation.tools.iso.lab.tracreporting import LabIsoStockTransferReporter
from thelma.automation.tools.metadata.ticket import IsoRequestTicketAccepter
from thelma.automation.tools.metadata.ticket import IsoRequestTicketReassigner
from thelma.automation.tools.metadata.ticket import IsoRequestTicketReopener
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.interfaces import IExperimentMetadata
from thelma.interfaces import IIso
from thelma.interfaces import IIsoJob
from thelma.interfaces import IIsoRequest
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPoolSet
from thelma.interfaces import IPlate
from thelma.interfaces import IRack
from thelma.interfaces import IRackLayout
from thelma.interfaces import IUser
from thelma.models.experiment import EXPERIMENT_METADATA_TYPES
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import Iso
from thelma.models.iso import IsoPreparationPlate
from thelma.models.job import IsoJob
from thelma.models.utils import get_current_user
from thelma.resources.base import RELATION_BASE_URL
import logging
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
    label = terminal_attribute(str, 'label')
    status = terminal_attribute(str, 'status')
    number_stock_racks = terminal_attribute(int, 'number_stock_racks')
    iso_request = member_attribute(IIsoRequest, 'iso_request')
    rack_layout = member_attribute(IRackLayout, 'rack_layout')
    molecule_design_pool_set = member_attribute(IMoleculeDesignPoolSet,
                                                'molecule_design_pool_set')
    optimizer_excluded_racks = terminal_attribute(str,
                                                  'optimizer_excluded_racks')
    optimizer_required_racks = terminal_attribute(str,
                                                  'optimizer_required_racks')
    # TODO: attach racks
#    iso_sample_stock_racks = collection_attribute(IIsoStockRack,
#                                                  'iso_stock_racks')
#    iso_preparation_plate = member_attribute(IRack,
#                                             'iso_preparation_plate.plate')
#    iso_aliquot_plates = collection_attribute(IRack,
#                                              'iso_aliquot_plates_plates')
    iso_job = member_attribute(IIsoJob, 'iso_job')

    def update(self, data):
        if IDataElement.providedBy(data): # pylint: disable=E1101
            pass
        else:
            Member.update(self, data)


class LabIsoMember(IsoMember):
    pass


class StockSampleCreationIsoMember(IsoMember):
    ticket_number = terminal_attribute(int, 'ticket_number')
    layout_number = terminal_attribute(int, 'layout_number')


class IsoCollection(Collection):
    title = 'ISOs'
    root_name = 'isos'
    description = 'Manage ISOs'
    default_order = AscendingOrderSpecification('label')


class IsoRequestMember(Member):
    relation = "%s/iso-request" % RELATION_BASE_URL
    iso_type = terminal_attribute(str, 'iso_type')
    label = terminal_attribute(str, 'label')
    owner = terminal_attribute(str, 'owner')
    expected_number_isos = terminal_attribute(int, 'expected_number_isos')
    number_aliquots = terminal_attribute(int, 'number_aliquots')
    isos = collection_attribute(IIso, 'isos')

    @property
    def title(self):
        return 'Base ISO Request'


class LabIsoRequestMember(IsoRequestMember):
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

    def update_from_entity(self, new_entity):
        self.get_entity().iso_layout = new_entity.iso_layout
        self.delivery_date = new_entity.delivery_date
        self.label = new_entity.label
        self.expected_number_isos = new_entity.expected_number_isos
        self.number_aliquots = new_entity.number_aliquots

    def update_from_data(self, data_element):
        prx = DataElementAttributeProxy(data_element)
        new_owner = prx.owner
        current_owner = self.owner
        if len(current_owner) < 1:
            current_owner = None
        if new_owner != current_owner:
            self.__process_change_owner(new_owner)
        new_delivery_date = prx.delivery_date
        if new_delivery_date:
            self.delivery_date = new_delivery_date
        if prx.isos is not None:
#        if len(prx.isos) > 0:
            self.__process_isos(prx.isos)

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
#                if status == 'TRANSFER_JOB_STOCK':
#                    self.__transfer_job_stock(iso)
                if status.startswith('UPDATE_JOB_STOCK_RACK'):
                    barcode = status[len('UPDATE_JOB_STOCK_RACK'):]
                    self.__update_job_stock_rack(iso, barcode)
                elif status == 'TRANSFER_TO_ISO':
                    self.__transfer_to_iso(iso)
                elif status == 'CLOSE_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.DONE)
                elif status == 'CANCEL_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.CANCELLED)
                elif status == 'REOPEN_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.REOPENED)
                elif status == 'COPY_ISO':
                    self.__copy_iso(iso)
                else:
                    raise ValueError('Unknwon ISO status "%s".' % status)
        if number_of_new_isos > 0:
            self.__generate_isos(number_of_new_isos,
                                 optimizer_excluded_racks,
                                 optimizer_required_racks)

    def __process_change_owner(self, new_owner):
        if new_owner is None:
            # Reassign to requester for editing the experiment
            # metadata.
            reassigner = IsoRequestTicketReassigner(
                                    iso_request=self.get_entity(),
                                    completed=False)
            reassigner.send_request()
            new_owner = ''
            if not reassigner.transaction_completed():
                errors = reassigner.get_messages(logging.ERROR)
                raise HTTPBadRequest(" -- ".join(errors)).exception
        elif new_owner == self.requester.directory_user_id:
            # Close iso request and reassign to requester.
            reassigner = IsoRequestTicketReassigner(
                        iso_request=self.get_entity(),
                        completed=True)
            reassigner.send_request()
            if not reassigner.transaction_completed():
                errors = reassigner.get_messages(logging.ERROR)
                raise HTTPBadRequest(" -- ".join(errors)).exception
        elif new_owner == STOCKMANAGEMENT_USER:
            pass
        elif new_owner == 'reopen':
            user_id = get_current_user().directory_user_id
            new_owner = user_id + ", " + STOCKMANAGEMENT_USER
            reopener = IsoRequestTicketReopener(
                                    iso_request=self.get_entity(),
                                    username=user_id)
            reopener.send_request()
        else:
            # Accept iso request.
            tkt_user = new_owner.split(',')[0]
            accepter = IsoRequestTicketAccepter(
                            iso_request=self.get_entity(),
                            username=tkt_user)
            accepter.send_request()
            if not accepter.transaction_completed():
                msg = " -- ".join(accepter.get_messages(
                                                logging.ERROR))
                raise HTTPBadRequest(msg).exception
        self.owner = new_owner

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

    def __transfer_to_iso(self, iso):
        user = get_current_user()
        executor = get_worklist_executor(iso, user)
        trac_updater = LabIsoStockTransferReporter(executor=executor)
        self.__run_tool(executor, 'Errors during transfer to ISO. --',
                        trac_tool=trac_updater)

    def __update_job_stock_rack(self, iso, stock_rack_barcode):
        recycler = get_stock_rack_recyler(iso.iso_job,
                                          [stock_rack_barcode])
        self.__run_tool(recycler, 'Control stock rack is not valid! --')

#    def __transfer_job_stock(self, iso):
#        user = get_current_user()
#        executor = IsoControlStockRackExecutor(iso_job=iso.iso_job,
#                                               user=user)
#        trac_updater = StockTransferReportUploader(executor=executor)
#        self.__run_tool(executor, 'Stock rack is not valid! --',
#                        trac_tool=trac_updater)

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
        self.__run_tool(creator, '')

    def __run_tool(self, tool, error_text, trac_tool=None):
        tool_result = tool.get_result()
        # Check for errors.
        if tool_result is None or tool_result is False:
            msg = " -- ".join(tool.get_messages(logging.ERROR))
            raise HTTPBadRequest(error_text + msg).exception
        # Now, collect warnings and notify the user message context manager.
        warnings = tool.get_messages(logging.WARNING)
        if len(warnings) > 0:
            reg = get_current_registry()
            msg_notifier = reg.getUtility(IUserMessageNotifier)
            msg_notifier.notify(" -- ".join(warnings))
        if trac_tool is not None:
            trac_tool.send_request()
            if not trac_tool.transaction_completed():
                errors = trac_tool.get_messages(logging.ERROR)
                raise HTTPBadRequest(' -- '.join(errors)).exception
        return tool_result

    def __find_iso(self, iso_id):
        # Enforce exactly one matching ISO.
        result, = [iso for iso in self.get_entity().isos if iso.id == iso_id]
        return result


class StockSampleCreationIsoRequestMember(IsoRequestMember):
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
    default_order = DescendingOrderSpecification('delivery_date')


class IsoStockRackMember(Member):
    relation = "%s/iso_stock_rack" % RELATION_BASE_URL

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.__class__, entity.id)

    rack = member_attribute(IRack, 'rack')


class IsoSectorStockRackMember(Member):
    relation = "%s/iso_sector_stock_rack" % RELATION_BASE_URL

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.__class__, entity.id)

    index = terminal_attribute(int, 'sector_index')
    rack = member_attribute(IRack, 'rack')
