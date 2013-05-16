"""
ISO resources.

AAB, Jun 2011
"""

from datetime import datetime
from everest.entities.utils import get_root_aggregate
from everest.interfaces import IUserMessageNotifier
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import DescendingOrderSpecification
from everest.representers.dataelements import DataElementAttributeProxy
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.resources.staging import create_staging_collection
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.threadlocal import get_current_registry
from thelma.automation.tools.iso.generation import IsoGenerator
from thelma.automation.tools.iso.generation import IsoRescheduler
from thelma.automation.tools.iso.seriesprocessing import IsoAliquotCreator
from thelma.automation.tools.iso.seriesprocessing import IsoAliquotExecutor
from thelma.automation.tools.iso.seriesprocessing import IsoProcessingExecutor
from thelma.automation.tools.iso.stock import IsoControlStockRackExecutor
from thelma.automation.tools.iso.stock import IsoSampleStockRackExecutor
from thelma.automation.tools.iso.tubehandler import IsoControlRackRecycler
from thelma.automation.tools.libcreation.iso import LibraryCreationIsoPopulator
from thelma.automation.tools.metadata.ticket import IsoRequestTicketAccepter
from thelma.automation.tools.metadata.ticket import IsoRequestTicketReassigner
from thelma.automation.tools.metadata.ticket import IsoRequestTicketReopener
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.interfaces import IExperimentMetadata
from thelma.interfaces import IExperimentMetadataType
from thelma.interfaces import IIso
from thelma.interfaces import IIsoJob
from thelma.interfaces import IIsoRequest
from thelma.interfaces import IIsoSampleStockRack
from thelma.interfaces import IJobType
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


__docformat__ = 'reStructuredText en'

__all__ = ['IsoCollection',
           'IsoMember',
           'IsoRequestCollection',
           'IsoRequestMember',
           'IsoSampleStockRackCollection',
           'IsoSampleStockRackMember',
           ]


class IsoMember(Member):
    relation = "%s/iso" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')
    iso_request = member_attribute(IIsoRequest, 'iso_request')
    molecule_design_pool_set = member_attribute(IMoleculeDesignPoolSet,
                                                'molecule_design_pool_set')
    status = terminal_attribute(str, 'status')
    optimizer_excluded_racks = terminal_attribute(str,
                                                  'optimizer_excluded_racks')
    optimizer_required_racks = terminal_attribute(str,
                                                  'optimizer_required_racks')
    rack_layout = member_attribute(IRackLayout, 'rack_layout')
    iso_sample_stock_racks = collection_attribute(IIsoSampleStockRack,
                                                  'iso_sample_stock_racks')
    iso_preparation_plate = member_attribute(IRack,
                                             'iso_preparation_plate.plate')
    iso_aliquot_plates = collection_attribute(IRack,
                                              'iso_aliquot_plates_plates')
    iso_job = member_attribute(IIsoJob, 'iso_job')

    def update_from_data(self, data_element):
        pass


class IsoCollection(Collection):
    title = 'ISOs'
    root_name = 'isos'
    description = 'Manage ISOs'
    default_order = AscendingOrderSpecification('label')


class IsoRequestMember(Member):
    relation = "%s/iso-request" % RELATION_BASE_URL
    iso_type = terminal_attribute(str, 'iso_type')
    plate_set_label = terminal_attribute(str, 'plate_set_label')
    rack_layout = member_attribute(IRackLayout, 'iso_layout')
    delivery_date = terminal_attribute(datetime, 'delivery_date')
    isos = collection_attribute(IIso, 'isos')
    requester = member_attribute(IUser, 'requester')
    owner = terminal_attribute(str, 'owner')
    comment = terminal_attribute(str, 'comment')
    number_plates = terminal_attribute(int, 'number_plates')
    number_aliquots = terminal_attribute(int, 'number_aliquots')
    ticket_number = terminal_attribute(int,
                                       'experiment_metadata.ticket_number')
    experiment_metadata = member_attribute(IExperimentMetadata,
                                           'experiment_metadata')
    experiment_metadata_type = \
                member_attribute(IExperimentMetadataType,
                                'experiment_metadata.experiment_metadata_type')

    @property
    def title(self):
        return '%s ISO Request' \
            % ('Standard' if self.iso_type == ISO_TYPES.STANDARD else
               'Library Creation')

    def __getitem__(self, name):
        if name == 'completed_iso_plates':
            iso_plates = create_staging_collection(IPlate)
            if self.iso_type == ISO_TYPES.STANDARD \
               and self.experiment_metadata.is_type(
                                            EXPERIMENT_METADATA_TYPES.MANUAL):
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
        self.plate_set_label = new_entity.plate_set_label
        self.number_plates = new_entity.number_plates
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
                if status == 'TRANSFER_CONTROL_STOCK':
                    self.__transfer_control_stock(iso)
                elif status.startswith('UPDATE_CONTROL_STOCK_RACK'):
                    barcode = status[len('UPDATE_CONTROL_STOCK_RACK'):]
                    self.__update_control_stock_rack(iso, barcode)
                elif status == 'TRANSFER_STOCK':
                    self.__transfer_stock(iso)
                elif status == 'TRANSFER_TO_ISO':
                    self.__transfer_to_iso(iso)
                elif status.startswith('TRANSFER_TO_ADD_ALIQUOT'):
                    barcode = status[len('TRANSFER_TO_ADD_ALIQUOT'):]
                    self.__transfer_to_add_aliquote_plate(iso, barcode)
                elif status == 'CLOSE_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.DONE)
                elif status == 'CANCEL_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.CANCELLED)
                elif status == 'REOPEN_ISO':
                    self.__update_iso_status(iso, ISO_STATUS.REOPENED)
                elif status == 'COPY_ISO_WITH_OPTIMIZATION':
                    self.__copy_iso(iso, True)
                elif status == 'COPY_ISO_WITHOUT_OPTIMIZATION':
                    self.__copy_iso(iso, False)
                elif status == 'ADD_ALIQUOT':
                    self.__add_aliquote_plate(iso)
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

    def __copy_iso(self, iso, with_optimization):
        if not with_optimization:
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
        else:
            rescheduler = IsoRescheduler(iso_request=iso.iso_request,
                                         isos_to_copy=[iso],)
            new_isos = self.__run_tool(rescheduler,
                                       'Problem during ISO rescheduling! --')
        job_num = len(iso.iso_request.iso_jobs) + 1
        job_type_aggregate = get_root_aggregate(IJobType)
        job_type = job_type_aggregate.get_by_slug('iso-batch')
        IsoJob(label='ISO Job %d' % job_num,
               job_type=job_type, isos=new_isos, user=get_current_user())

    def __add_aliquote_plate(self, iso):
        creator = IsoAliquotCreator(iso=iso)
        self.__run_tool(creator, 'Errors during adding aliquot plate. --')

    def __transfer_to_add_aliquote_plate(self, iso, barcode):
        user = get_current_user()
        executor = IsoAliquotExecutor(iso=iso,
                                      barcode=barcode, user=user)
        self.__run_tool(executor, 'Aliquot plate is not valid! --')

    def __transfer_to_iso(self, iso):
        user = get_current_user()
        executor = IsoProcessingExecutor(iso=iso, user=user)
        self.__run_tool(executor, 'Errors during transfer to ISO. --')

    def __transfer_stock(self, iso):
        user = get_current_user()
        executor = IsoSampleStockRackExecutor(iso=iso, user=user)
        self.__run_tool(executor, 'Errors during stock transfer. --')

    def __update_control_stock_rack(self, iso, stock_rack_barcode):
        rack_aggregate = get_root_aggregate(IRack)
        stock_rack = rack_aggregate.get_by_slug(stock_rack_barcode)
        recycler = IsoControlRackRecycler(iso_job=iso.iso_job,
                                          stock_rack=stock_rack)
        self.__run_tool(recycler, 'Control stock rack is not valid! --')

    def __transfer_control_stock(self, iso):
        user = get_current_user()
        executor = IsoControlStockRackExecutor(iso_job=iso.iso_job,
                                               user=user)
        self.__run_tool(executor, 'Stock rack is not valid! --')

    def __generate_isos(self, number_of_new_isos,
                        optimizer_excluded_racks, optimizer_requested_tubes):
        if optimizer_excluded_racks is not None:
            optimizer_excluded_racks = optimizer_excluded_racks.split(',')
        if optimizer_requested_tubes is not None:
            optimizer_requested_tubes = optimizer_requested_tubes.split(',')
        iso_request = self.get_entity()
        if iso_request.iso_type == ISO_TYPES.STANDARD:
            generator = \
                    IsoGenerator(iso_request,
                                 number_of_new_isos,
                                 excluded_racks=optimizer_excluded_racks,
                                 requested_tubes=optimizer_requested_tubes)
        else:
            generator = LibraryCreationIsoPopulator(
                                    iso_request.molecule_design_library,
                                    number_of_new_isos,
                                    excluded_racks=optimizer_excluded_racks,
                                    requested_tubes=optimizer_requested_tubes)
        new_isos = self.__run_tool(generator, '')
        iso_aggregate = get_root_aggregate(IIso)
        job_type_aggregate = get_root_aggregate(IJobType)
        job_type = job_type_aggregate.get_by_slug('iso-batch')
        user = get_current_user()
        iso_job = None
        job_counter = len(iso_request.iso_jobs) + 1
        for iso in new_isos:
            iso_aggregate.add(iso)
            if iso.iso_job == None:
                if iso_job == None:
                    label = 'ISO Job %i' % (job_counter)
                    iso_job = IsoJob(label=label, job_type=job_type,
                                     isos=[iso], user=user)
                iso.iso_job = iso_job

    def __run_tool(self, tool, error_text):
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
        return tool_result

    def __find_iso(self, iso_id):
        # Enforce exactly one matching ISO.
        result, = [iso for iso in self.get_entity().isos if iso.id == iso_id]
        return result


class IsoRequestCollection(Collection):
    title = 'ISO Requests'
    root_name = 'iso-requests'
    description = 'Manage ISO Requests'
    default_order = DescendingOrderSpecification('delivery_date')


class IsoSampleStockRackMember(Member):
    relation = "%s/iso_sample_stock_rack" % RELATION_BASE_URL

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.__class__, entity.id)

    index = terminal_attribute(int, 'sector_index')
    rack = member_attribute(IRack, 'rack')


class IsoSampleStockRackCollection(Collection):
    title = 'IsoSampleStockRacks'
    root_name = 'iso_sample_stock_racks'
    description = 'Manage iso_sample_stock_racks where racks are held'
    default_order = AscendingOrderSpecification('type') \
                    & AscendingOrderSpecification('label')