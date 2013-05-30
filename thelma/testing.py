"""
Testing base classes.

NP
"""

from datetime import datetime
from everest.entities.utils import get_root_aggregate
from everest.mime import AtomMime
from everest.repositories.rdb import Session
from everest.representers.atom import XML_NS_ATOM
from everest.representers.atom import XML_PREFIX_ATOM
from everest.representers.utils import get_mapping_registry
from everest.testing import EntityTestCase
from everest.testing import FunctionalTestCase
from everest.testing import ResourceTestCase
from iso8601 import iso8601
from lxml import etree
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.interfaces import IContainer
from thelma.interfaces import IDeviceType
from thelma.interfaces import IExperiment
from thelma.interfaces import IExperimentDesign
from thelma.interfaces import IExperimentDesignRack
from thelma.interfaces import IExperimentMetadataType
from thelma.interfaces import IIso
from thelma.interfaces import IIsoRequest
from thelma.interfaces import IItemStatus
from thelma.interfaces import IJobType
from thelma.interfaces import ILocationType
from thelma.interfaces import IMolecule
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.interfaces import IOrganization
from thelma.interfaces import IPlate
from thelma.interfaces import IPlateSpecs
from thelma.interfaces import IRackLayout
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackPositionSet
from thelma.interfaces import IRackShape
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import ISpecies
from thelma.interfaces import ISubproject
from thelma.interfaces import ITag
from thelma.interfaces import ITractor
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.interfaces import ITubeRackSpecs
from thelma.interfaces import ITubeSpecs
from thelma.interfaces import IUser
from thelma.interfaces import IWell
from thelma.interfaces import IWellSpecs
from thelma.models.barcode import BarcodePrintJob
from thelma.models.chemicalstructure import NucleicAcidChemicalStructure
from thelma.models.container import ContainerLocation
from thelma.models.container import Tube
from thelma.models.container import TubeSpecs
from thelma.models.container import Well
from thelma.models.container import WellSpecs
from thelma.models.device import Device
from thelma.models.device import DeviceType
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.experiment import ExperimentMetadata
from thelma.models.experiment import ExperimentRack
from thelma.models.gene import Gene
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoControlStockRack
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.iso import IsoSampleStockRack
from thelma.models.job import ExperimentJob
from thelma.models.job import IsoJob
from thelma.models.job import JOB_STATUS_TYPES
from thelma.models.job import JobType
from thelma.models.job import OtherJob
from thelma.models.library import LibraryCreationIso
from thelma.models.library import LibrarySourcePlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.liquidtransfer import ExecutedContainerDilution
from thelma.models.liquidtransfer import ExecutedContainerTransfer
from thelma.models.liquidtransfer import ExecutedRackTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember
from thelma.models.location import BarcodedLocation
from thelma.models.location import BarcodedLocationType
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculedesign import MoleculeDesignSet
from thelma.models.moleculedesign import SiRnaDesign
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType
from thelma.models.organization import Organization
from thelma.models.project import Project
from thelma.models.rack import Plate
from thelma.models.rack import PlateSpecs
from thelma.models.rack import RackShape
from thelma.models.rack import TubeRack
from thelma.models.rack import TubeRackSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.sample import SampleMolecule
from thelma.models.species import Species
from thelma.models.stockinfo import StockInfo
from thelma.models.subproject import Subproject
from thelma.models.suppliermoleculedesign import SupplierMoleculeDesign
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.tubetransfer import TubeTransfer
from thelma.models.tubetransfer import TubeTransferWorklist
from thelma.models.user import UserPreferences
from thelma.resources.barcode import BarcodePrintJobMember
from thelma.resources.container import TubeMember
from thelma.resources.device import DeviceMember
from thelma.resources.devicetype import DeviceTypeMember
from thelma.resources.experiment import ExperimentDesignMember
from thelma.resources.experiment import ExperimentMember
from thelma.resources.experiment import ExperimentRackMember
from thelma.resources.gene import GeneMember
from thelma.resources.job import JobMember
from thelma.resources.jobtype import JobTypeMember
from thelma.resources.location import LocationMember
from thelma.resources.moleculetype import MoleculeTypeMember
from thelma.resources.organization import OrganizationMember
from thelma.resources.project import ProjectMember
from thelma.resources.rack import PlateMember
from thelma.resources.rack import RackPositionMember
from thelma.resources.rack import RackShapeMember
from thelma.resources.rack import TubeRackMember
from thelma.resources.rackspecs import PlateSpecsMember
from thelma.resources.rackspecs import TubeRackSpecsMember
from thelma.resources.species import SpeciesMember
from thelma.resources.stockinfo import StockInfoMember
from thelma.resources.subproject import SubprojectMember
from tractor import make_api_from_config
import pytz
import transaction

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-05-08 17:42:10 +0200 (Wed, 08 May 2013) $'
__revision__ = '$Rev: 13330 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/testing.py $'

__all__ = ['ThelmaModelTestCase',
           'ThelmaResourceTestCase',
           ]


APP_NAME = 'thelma'
REMOTE_USER = 'it'


def create_extra_environ():
    return dict(REMOTE_USER=REMOTE_USER)


class EntityCreatorMixin(object):
    def _create_barcode_print_job(self, **kw):
        if not 'barcodes' in kw:
            kw['barcodes'] = '02480532'
        if not 'labels' in kw:
            kw['labels'] = 'TestBarcode'
        if not 'printer' in kw:
            kw['printer'] = 'DUMMY'
        if not 'type' in kw:
            kw['type'] = 'UNIRACK'
        return self._create_entity(BarcodePrintJob, kw)

    def _create_container_location(self, **kw):
        if not 'rack' in kw:
            kw['rack'] = self._create_tube_rack()
        if not 'position' in kw:
            kw['position'] = self._get_entity(IRackPosition)
        if not 'container' in kw:
            kw['container'] = self._create_tube(location=None)
        return self._create_entity(ContainerLocation, kw)

    def _create_device(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'TEST_DEVICE'
        if not 'label' in kw:
            kw['label'] = 'TestDevice'
        if not 'type' in kw:
            kw['type'] = self._get_entity(IDeviceType)
        if not 'manufacturer' in kw:
            kw['manufacturer'] = self._get_entity(IOrganization)
        if not 'model' in kw:
            kw['model'] = 'Model description string.'
        return self._create_entity(Device, kw)

    def _create_device_type(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'TEST_DEVICE_TYPE'
        if not 'label' in kw:
            kw['label'] = 'TestDeviceType'
        return self._create_entity(DeviceType, kw)

    def _create_executed_container_dilution(self, **kw):
        if not 'target_container' in kw:
            kw['target_container'] = self._get_entity(ITube)
        if not 'reservoir_specs' in kw:
            kw['reservoir_specs'] = self._get_entity(IReservoirSpecs)
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, 'it')
        if not 'planned_container_dilution' in kw:
            kw['planned_container_dilution'] = \
                                self._create_planned_container_dilution()
        return self._create_entity(ExecutedContainerDilution, kw)

    def _create_executed_container_transfer(self, **kw):
        if not 'source_container' in kw:
            kw['source_container'] = self._get_entity(ITube)
        if not 'target_container' in kw:
            kw['target_container'] = self._get_entity(IWell)
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, 'it')
        if not 'planned_container_transfer' in kw:
            kw['planned_container_transfer'] = \
                                self._create_planned_container_transfer()
        return self._create_entity(ExecutedContainerTransfer, kw)

    def _create_executed_rack_transfer(self, **kw):
        if not 'source_rack' in kw:
            kw['source_rack'] = self._get_entity(ITubeRack)
        if not 'target_rack' in kw:
            kw['target_rack'] = self._get_entity(IPlate)
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, 'it')
        if not 'planned_rack_transfer' in kw:
            kw['planned_rack_transfer'] = self._create_planned_rack_transfer()
        return self._create_entity(ExecutedRackTransfer, kw)

    def _create_executed_worklist(self, **kw):
        if not 'planned_worklist' in kw:
            kw['planned_worklist'] = self._create_planned_worklist()
        if not 'executed_transfers' in kw:
            kw['executed_transfers'] = \
                                [self._create_executed_container_dilution()]
        return self._create_entity(ExecutedWorklist, kw)

    def _create_experiment(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestExperiment'
        if not 'destination_rack_specs' in kw:
            kw['destination_rack_specs'] = \
               self._get_entity(IPlateSpecs)
        if not 'source_rack' in kw:
            kw['source_rack'] = self._get_entity(ITubeRack)
        if not 'experiment_design' in kw:
            kw['experiment_design'] = self._get_entity(IExperimentDesign)
        if not 'experiment_racks' in kw:
            kw['experiment_racks'] = [self._create_experiment_rack()]
        return self._create_entity(Experiment, kw)

    def _create_experiment_design(self, **kw):
        if not 'rack_shape' in kw:
            kw['rack_shape'] = self._get_entity(IRackShape)
        return self._create_entity(ExperimentDesign, kw)

    def _create_experiment_design_rack(self, **kw):
        if not'label' in kw:
            kw['label'] = 'TestExperimentDesignRack'
        if not 'rack_layout' in kw:
            kw['rack_layout'] = self._get_entity(IRackLayout)
        return self._create_entity(ExperimentDesignRack, kw)

    def _create_experiment_job(self, **kw):
#        kw['type'] = JOB_TYPES.RNAI_EXPERIMENT
        jt_agg = get_root_aggregate(IJobType)
        kw['job_type'] = jt_agg.get_by_id('11')
        if not 'label' in kw:
            kw['label'] = 'TestExperimentJob'
        if not 'description' in kw:
            kw['description'] = 'TestDescription'
        if not 'status' in kw:
            kw['status'] = JOB_STATUS_TYPES.QUEUED
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, 'it')
        if not 'experiments' in kw:
            kw['experiments'] = [self._get_entity(IExperiment)]
        return self._create_entity(ExperimentJob, kw)

    def _create_experiment_metadata(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestExperimentMetadata'
        if not 'subproject' in kw:
            kw['subproject'] = self._get_entity(ISubproject)
        if not 'number_replicates' in kw:
            kw['number_replicates'] = 3
        if not 'experiment_metadata_type' in kw:
            kw['experiment_metadata_type'] = self._get_entity(
                                                    IExperimentMetadataType)
        return self._create_entity(ExperimentMetadata, kw)

    def _create_experiment_rack(self, **kw):
        if not 'design_rack' in kw:
            kw['design_rack'] = self._get_entity(IExperimentDesignRack)
        if not 'rack' in kw:
            kw['rack'] = self._get_entity(IPlate)
        return self._create_entity(ExperimentRack, kw)

    def _create_gene(self, **kw):
        if not 'accession' in kw:
            kw['accession'] = 'TestAccession'
        if not 'locus_name' in kw:
            kw['locus_name'] = 'TestLocusName'
        if not 'species' in kw:
            kw['species'] = self._get_entity(ISpecies)
        return self._create_entity(Gene, kw)

    def _create_iso(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestISO'
        if not 'rack_layout' in kw:
            kw['rack_layout'] = RackLayout(shape=self._get_entity(IRackShape))
        if not 'iso_request' in kw:
            kw['iso_request'] = self._get_entity(IIsoRequest)
        return self._create_entity(Iso, kw)

    def _create_iso_aliquot_plate(self, **kw):
        if not 'iso' in kw:
            kw['iso'] = self._get_entity(IIso)
        if not 'plate' in kw:
            kw['plate'] = self._get_entity(IPlate)
        return self._create_entity(IsoAliquotPlate, kw)

    def _create_iso_control_stock_rack(self, **kw):
        if not 'iso_job' in kw:
            kw['iso_job'] = self._create_iso_job()
        if not 'rack' in kw:
            kw['rack'] = self._get_entity(ITubeRack)
        if not 'rack_layout' in kw:
            kw['rack_layout'] = self._create_rack_layout()
        if not 'planned_worklist' in kw:
            kw['planned_worklist'] = self._create_planned_worklist()
        return self._create_entity(IsoControlStockRack, kw)

    def _create_iso_job(self, **kw):
        jt_agg = get_root_aggregate(IJobType)
        kw['job_type'] = jt_agg.get_by_id('15')
#        kw['type'] = JOB_TYPES.ISO_PROCESSING
        if not 'isos' in kw:
            kw['isos'] = [self._create_iso()]
        if not 'label' in kw:
            kw['label'] = 'IsoJobTestLabel'
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, 'it')
        return self._create_entity(IsoJob, kw)

    def _create_iso_preparation_plate(self, **kw):
        if not 'iso' in kw:
            kw['iso'] = self._get_entity(IIso)
        if not 'plate' in kw:
            kw['plate'] = self._get_entity(IPlate)
        return self._create_entity(IsoPreparationPlate, kw)

    def _create_iso_rack_layout(self, **kw):
        if not 'shape' in kw:
            kw['shape'] = self._get_entity(IRackShape, key='8x12')
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, key='it')
        return self._create_entity(IsoLayout, kw)

    def _create_iso_request(self, **kw):
        if not 'iso_layout' in kw:
            kw['iso_layout'] = self._create_rack_layout()
        if not 'requester' in kw:
            kw['requester'] = self._get_entity(IUser, 'it')
        if not 'plate_set_label' in kw:
            kw['plate_set_label'] = 'IsoRequest.PlateSetLabel.Test'
        return self._create_entity(IsoRequest, kw)

    def _create_iso_sample_stock_rack(self, **kw):
        if not 'iso' in kw:
            kw['iso'] = self._get_entity(IIso)
        if not 'rack' in kw:
            kw['rack'] = self._get_entity(ITubeRack)
        if not 'sector_index' in kw:
            kw['sector_index'] = 0
        if not 'planned_worklist' in kw:
            kw['planned_worklist'] = self._create_planned_worklist()
        return self._create_entity(IsoSampleStockRack, kw)

    def _create_job_type(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'TestJobTypeName'
        if not 'label' in kw:
            kw['label'] = 'TestJobTypeLabel'
        if not 'xml' in kw:
            kw['xml'] = '<xml>dummy_xml</xml>'
        return self._create_entity(JobType, kw)

    def _create_library_creation_iso(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'Lib ISO 15'
        if not 'ticket_number' in kw:
            kw['ticket_number'] = 9876
        if not 'layout_number' in kw:
            kw['layout_number'] = 15
        if not 'iso_request' in kw:
            kw['iso_request'] = self._create_iso_request()
        if not 'rack_layout' in kw:
            kw['rack_layout'] = self._create_rack_layout()
        return self._create_entity(LibraryCreationIso, kw)

    def _create_library_source_plate(self, **kw):
        if not 'iso' in kw:
            kw['iso'] = self._get_entity(IIso)
        if not 'plate' in kw:
            kw['plate'] = self._get_entity(IPlate)
        if not 'sector_index' in kw:
            kw['sector_index'] = 2
        return self._create_entity(LibrarySourcePlate, kw)

    def _create_location_type(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'TestBarcodedLocationType'
        return self._create_entity(BarcodedLocationType, kw)

    def _create_location(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'test bl 1'
        if not 'label' in kw:
            kw['label'] = 'TestBarcodedLocation'
        if not 'type' in kw:
            kw['type'] = self._get_entity(ILocationType)
        if not 'barcode' in kw:
            kw['barcode'] = '01234567'
        return self._create_entity(BarcodedLocation, kw)

    def _create_molecule(self, **kw):
        if not 'molecule_design' in kw:
            kw['molecule_design'] = self._get_entity(IMoleculeDesign, '11')
        if not 'supplier' in kw:
            kw['supplier'] = self._get_entity(IOrganization)
        return self._create_entity(Molecule, kw)

    def _create_molecule_design_library(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'MoleculeDesignLibrary.Label.Test'
        if not 'molecule_design_pool_set' in kw:
            kw['molecule_design_pool_set'] = \
                self._create_molecule_design_pool_set()
        if not 'final_volume' in kw:
            kw['final_volume'] = 0.000005
        if not 'final_concentration' in kw:
            kw['final_concentration'] = 0.000010
        return self._create_entity(MoleculeDesignLibrary, kw)

    def _create_molecule_design_set(self, **kw):
        if not 'molecue_designs' in kw:
            kw['molecule_designs'] = \
                    set([self._get_entity(IMoleculeDesign, '11')])
        return self._create_entity(MoleculeDesignSet, kw)

    def _create_molecule_type(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'TestMoleculeType'
        if not 'default_stock_concentration' in kw:
            kw['default_stock_concentration'] = 5e-4
        return self._create_entity(MoleculeType, kw)

    def _create_organization(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'TestOrganization'
        return self._create_entity(Organization, kw)

    def _create_other_job(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestOtherJob.Label'
        if not 'job_type' in kw:
            kw['job_type'] = self._get_entity(IJobType, 'DILUTION')
        if not 'subproject' in kw:
            kw['subproject'] = self._get_entity(ISubproject)
        if not 'description' in kw:
            kw['description'] = 'TestDescription'
        if not 'status' in kw:
            kw['status'] = JOB_STATUS_TYPES.QUEUED
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, 'it')
        return self._create_entity(OtherJob, kw)

    def _create_planned_container_dilution(self, **kw):
        if not 'volume' in kw:
            kw['volume'] = 0.000020
        if not 'target_position' in kw:
            kw['target_position'] = self._get_entity(IRackPosition)
        if not 'diluent_info' in kw:
            kw['diluent_info'] = 'generic_buffer'
        return self._create_entity(PlannedContainerDilution, kw)

    def _create_planned_container_transfer(self, **kw):
        if not 'volume' in kw:
            kw['volume'] = 0.000020
        if not 'source_position' in kw:
            kw['source_position'] = self._get_entity(IRackPosition, 'a1')
        if not 'target_position' in kw:
            kw['target_position'] = self._get_entity(IRackPosition, 'b2')
        return self._create_entity(PlannedContainerTransfer, kw)

    def _create_planned_rack_transfer(self, **kw):
        if not 'volume' in kw:
            kw['volume'] = 0.000020
        if not 'source_sector_index' in kw:
            kw['source_sector_index'] = 0
        if not 'target_sector_index' in kw:
            kw['target_sector_index'] = 1
        if not 'sector_number' in kw:
            kw['sector_number'] = 4
        return self._create_entity(PlannedRackTransfer, kw)

    def _create_planned_worklist(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'PlannedWorklistTestLabel'
        return self._create_entity(PlannedWorklist, kw)

    def _create_plate(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestPlate'
        if not 'specs' in kw:
            kw['specs'] = self._get_entity(IPlateSpecs)
        if not 'status' in kw:
            kw['status'] = self._get_entity(IItemStatus)
        return self._create_entity(Plate, kw)

    def _create_plate_specs(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestPlateSpecs'
        if not 'shape' in kw:
            kw['shape'] = self._get_entity(IRackShape)
        if not 'manufacturer' in kw:
            kw['manufacturer'] = self._get_entity(IOrganization)
        if not 'well_specs' in kw:
            kw['well_specs'] = self._get_entity(IWellSpecs)
        return self._create_entity(PlateSpecs, kw)

    def _create_molecule_design_pool_set(self, **kw):
        if not 'molecule_type' in kw:
            kw['molecule_type'] = self._get_entity(IMoleculeType)
        if not 'molecule_design_pools' in kw:
            kw['molecule_design_pools'] = \
                        set([self._get_entity(IMoleculeDesignPool)])
        return self._create_entity(MoleculeDesignPoolSet, kw)

    def _create_project(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestProject'
        if not 'leader' in kw:
            kw['leader'] = self._get_entity(IUser, 'it')
        if not 'customer' in kw:
            kw['customer'] = self._get_entity(IOrganization, 'cenix')
        return self._create_entity(Project, kw)

    def _create_rack_layout(self, **kw):
        if not 'shape' in kw:
            kw['shape'] = self._get_entity(IRackShape)
        return self._create_entity(RackLayout, kw)

    def _create_rack_shape(self, **kw):
        if not 'number_rows' in kw:
            kw['number_rows'] = 55
        if not 'number_columns' in kw:
            kw['number_columns'] = 110
        if not 'name' in kw:
            kw['name'] = '55x110'
        if not 'label' in kw:
            kw['label'] = '55x110'
        return self._create_entity(RackShape, kw)

    def _create_reservoir_specs(self, **kw):
        if not 'name' in kw:
            kw['name'] = 'ReservoirSpecsTestName'
        if not 'description' in kw:
            kw['description'] = 'ReservoirSpec.Test.Description'
        if not 'rack_shape' in kw:
            kw['rack_shape'] = self._get_entity(IRackShape)
        if not 'max_volume' in kw:
            kw['max_volume'] = 0.000500
        if not 'min_dead_volume' in kw:
            kw['min_dead_volume'] = 0.000010
        if not 'max_dead_volume' in kw:
            kw['max_dead_volume'] = 0.000020
        return self._create_entity(ReservoirSpecs, kw)

    def _create_rna_sequence(self, **kw):
        if not 'representation' in kw:
            kw['representation'] = 'CGAAAUAGUAGAAGAACAGTT'
        return self._create_entity(NucleicAcidChemicalStructure, kw)

    def _create_sample(self, **kw):
        if not 'volume' in kw:
            kw['volume'] = 1.0e-5
        if not 'container' in kw:
            kw['container'] = self._get_entity(IContainer)
        return self._create_entity(Sample, kw)

    def _create_sample_molecule(self, **kw):
        if not 'molecule' in kw:
            kw['molecule'] = self._get_entity(IMolecule)
        if not 'concentration' in kw:
            kw['concentration'] = 5.0e-5
        return self._create_entity(SampleMolecule, kw)

    def _create_supplier_molecule_design(self, **kw):
        if not 'product_id' in kw:
            kw['product_id'] = '11'
        if not 'supplier' in kw:
            kw['supplier'] = self._get_entity(IOrganization, 'ambion')
        return self._create_entity(SupplierMoleculeDesign, kw)

    def _create_sirna_design(self, **kw):
        if not 'molecule_type' in kw:
            kw['molecule_type'] = \
                self._get_entity(IMoleculeType,
                                 key=MOLECULE_TYPE_IDS.SIRNA.lower())
        if not 'chemical_structures' in kw:
            kw['chemical_structures'] = \
                    [self._create_rna_sequence(),
                     self._create_rna_sequence(representation=
                                                    'CUGUUCUUCUACUAUUUCGTT')]
        return self._create_entity(SiRnaDesign, kw)

    def _create_species(self, **kw):
        if not 'genus_name' in kw:
            kw['genus_name'] = 'TestGenusName'
        if not 'species_name' in kw:
            kw['species_name'] = 'TestSpeciesName'
        if not 'common_name' in kw:
            kw['common_name'] = 'TestCommonName'
        if not 'acronym' in kw:
            kw['acronym'] = 'GS'
        if not 'ncbi_tax_id' in kw:
            kw['ncbi_tax_id'] = 10
        return self._create_entity(Species, kw)

    def _create_stock_info(self, **kw):
        if not 'molecule_design' in kw:
            kw['molecule_design'] = self._get_entity(IMoleculeDesign, '11')
        if not 'molecule_type' in kw:
            kw['molecule_type'] = self._get_entity(IMoleculeType, 'sirna')
        if not 'concentration' in kw:
            kw['concentration'] = 5e-5
        if not 'total_tubes' in kw:
            kw['total_tubes'] = 5
        if not 'total_volume' in kw:
            kw['total_volume'] = 1e-3
        if not 'minimum_volume' in kw:
            kw['minimum_volume'] = 5e-5
        if not 'maximum_volume' in kw:
            kw['maximum_volume'] = 1e-4
        return self._create_entity(StockInfo, kw)

    def _create_molecule_design_pool(self, **kw):
        if not 'molecule_designs' in kw:
            kw['molecule_designs'] = set([self._create_sirna_design()])
        if not 'default_stock_concentration' in kw:
            kw['default_stock_concentration'] = 5e-05
        return self._create_entity(MoleculeDesignPool, kw)

    def _create_subproject(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestSubproject'
        if not 'creation_date' in kw:
            kw['creation_date'] = \
                    iso8601.parse_date('2005-10-25T12:01:33+02:00')
        return self._create_entity(Subproject, kw)

    def _create_tag(self, **kw):
        if not 'domain' in kw:
            kw['domain'] = 'TestTagDomain'
        if not 'predicate' in kw:
            kw['predicate'] = 'TestTagPredicate'
        if not 'value' in kw:
            kw['value'] = 'TestTag.value'
        return self._create_entity(Tag, kw)

    def _create_tagged_rack_position_set(self, **kw):
        if not 'tags' in kw:
            kw['tags'] = set([self._get_entity(ITag)])
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser, 'it')
        if not 'rack_position_set' in kw:
            kw['rack_position_set'] = self._get_entity(IRackPositionSet)
        return self._create_entity(TaggedRackPositionSet, kw)

    def _create_tube(self, **kw):
        if not 'barcode' in kw:
            kw['barcode'] = '0123456789'
        if not 'status' in kw:
            kw['status'] = self._get_entity(IItemStatus)
        if not 'specs' in kw:
            kw['specs'] = self._get_entity(ITubeSpecs)
        return self._create_entity(Tube, kw)

    def _create_tube_transfer(self, **kw):
        if not 'tube' in kw:
            kw['tube'] = self._create_tube()
        if not 'source_rack' in kw:
            kw['source_rack'] = self._create_tube_rack(label='source_rack',
                                                       barcode='09999999')
        if not 'source_position' in kw:
            kw['source_position'] = self._get_entity(IRackPosition, 'a1')
        if not 'target_rack' in kw:
            kw['target_rack'] = self._create_tube_rack(label='target_rack',
                                                       barcode='09999998')
        if not 'target_position' in kw:
            kw['target_position'] = self._get_entity(IRackPosition, 'b2')
        return self._create_entity(TubeTransfer, kw)

    def _create_tube_transfer_worklist(self, **kw):
        if not 'user' in kw:
            kw['user'] = self._get_entity(IUser)
        if not 'timestamp' in kw:
            kw['timestamp'] = datetime(2012, 8, 23, 12, 42, 1,
                                       tzinfo=pytz.UTC)
        return self._create_entity(TubeTransferWorklist, kw)

    def _create_tube_rack(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestTubeRack'
        if not'specs' in kw:
            kw['specs'] = self._get_entity(ITubeRackSpecs)
        if not 'status' in kw:
            kw['status'] = self._get_entity(IItemStatus)
        return self._create_entity(TubeRack, kw)

    def _create_tube_rack_specs(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestTubeRackSpecs'
        if not 'shape' in kw:
            kw['shape'] = self._get_entity(IRackShape)
        if not 'manufacturer' in kw:
            kw['manufacturer'] = self._get_entity(IOrganization)
        if not 'tube_specs' in kw:
            kw['tube_specs'] = [self._get_entity(ITubeSpecs)]
        return self._create_entity(TubeRackSpecs, kw)

    def _create_tube_specs(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestTubeSpecs'
        if not 'max_volume' in kw:
            kw['max_volume'] = 100e-6
        if not 'dead_volume' in kw:
            kw['dead_volume'] = 5e-6
        if not 'tube_rack_specs' in kw:
            kw['tube_rack_specs'] = [self._get_entity(ITubeRackSpecs)]
        return self._create_entity(TubeSpecs, kw)

    def _create_user_preferences(self, **kw):
        if not 'app_name' in kw:
            kw['app_name'] = 'testapp'
        if not 'preferences' in kw:
            kw['preferences'] = '{foo=bar}'
        return self._create_entity(UserPreferences, kw)

    def _create_well(self, **kw):
        if not 'status' in kw:
            kw['status'] = self._get_entity(IItemStatus)
        if not 'specs' in kw:
            kw['specs'] = self._get_entity(ITubeSpecs)
        # Well creation is special in that we have to initialize it with
        # the location set to None and then assign a proper location.
        kw['location'] = None
        rack = kw.pop('rack', self._get_entity(IPlate))
        position = kw.pop('position', self._get_entity(IRackPosition))
        well = self._create_entity(Well, kw)
        well.location = self._create_container_location(rack=rack,
                                                        position=position,
                                                        container=None)
        return well

    def _create_well_specs(self, **kw):
        if not 'label' in kw:
            kw['label'] = 'TestWellSpecs'
        if not 'max_volume' in kw:
            kw['max_volume'] = 100e-6
        if not 'dead_volume' in kw:
            kw['dead_volume'] = 5e-6
        if not 'plate_specs' in kw:
            kw['plate_specs'] = self._get_entity(IPlateSpecs)
        return self._create_entity(WellSpecs, kw)

    def _create_worklist_series(self, **kw):
        return self._create_entity(WorklistSeries, kw)

    def _create_worklist_series_member(self, **kw):
        if not 'worklist_series' in kw:
            kw['worklist_series'] = self._create_worklist_series()
        if not 'planned_worklist' in kw:
            kw['planned_worklist'] = self._create_planned_worklist()
        if not 'index' in kw:
            kw['index'] = 0
        return self._create_entity(WorklistSeriesMember, kw)


class ThelmaModelTestCase(EntityTestCase, EntityCreatorMixin):
    """
    Test class for entity classes.
    """
    package_name = 'thelma'
    ini_section_name = 'app:thelma'

    def set_up(self):
        Session.remove()
        EntityTestCase.set_up(self)
        local_settings = self.config.get_settings()
        tractor_config_file = local_settings['tractor_config_file']
        tractor_api = make_api_from_config(tractor_config_file)
        self.config.registry.registerUtility(tractor_api, ITractor) # pylint: disable=E1103

    def tear_down(self):
        Session.remove()
        EntityTestCase.tear_down(self)


class ThelmaResourceTestCase(ResourceTestCase, EntityCreatorMixin):
    """
    Test class for resources classes.
    """
    package_name = 'thelma'
    ini_section_name = 'app:thelma'

    def set_up(self):
        Session.remove()
        ResourceTestCase.set_up(self)
        #
        self.config.testing_securitypolicy("it")
        self._request.environ.update(create_extra_environ())

    def tear_down(self):
        Session.remove()
        ResourceTestCase.tear_down(self)

    def _get_entity(self, ifc, key=None):
        # This is needed by the entity creator mixin.
        mb = self._get_member(ifc, key=key)
        return mb.get_entity()

    def _create_entity(self, entity_cls, data):
        # This is needed by the entity creator mixin.
        return entity_cls.create_from_data(data)

    def _create_barcode_print_job_member(self):
        barcode = self._create_barcode_print_job()
        return self._create_member(BarcodePrintJobMember, barcode)

    def _create_tube_member(self):
        tube = self._create_tube()
        return self._create_member(TubeMember, tube)

    def _create_device_member(self):
        device = self._create_device()
        return self._create_member(DeviceMember, device)

    def _create_experiment_member(self):
        experiment = self._create_experiment()
        return self._create_member(ExperimentMember, experiment)

    def _create_experiment_rack_member(self):
        exp_rack = self._create_experiment_rack()
        return self._create_member(ExperimentRackMember, exp_rack)

    def _create_experimentdesign_member(self):
        exp_design = self._create_experiment_design()
        return self._create_member(ExperimentDesignMember, exp_design)

    def _create_devicetype_member(self):
        device_type = self._create_device_type()
        return self._create_member(DeviceTypeMember, device_type)

    def _create_gene_member(self):
        gene = self._create_gene()
        return self._create_member(GeneMember, gene)

    def _create_job_member(self):
        job = self._create_other_job()
        return self._create_member(JobMember, job)

    def _create_job_type_member(self):
        job_type = self._create_job_type()
        return self._create_member(JobTypeMember, job_type)

    def _create_moleculetype_member(self):
        molecule_type = self._create_molecule_type()
        return self._create_member(MoleculeTypeMember, molecule_type)

    def _create_location_member(self):
        location = self._create_location()
        return self._create_member(LocationMember, location)

    def _create_molecule_design_member(self):
        molecule_design = self._create_sirna_design()
        return self._create_member(LocationMember, molecule_design)

    def _create_organization_member(self):
        organization = self._create_organization()
        return self._create_member(OrganizationMember, organization)

    def _get_rack_position_member(self):
        rack_position = self._get_entity(IRackPosition)
        return self._create_member(RackPositionMember, rack_position)

    def _create_rack_shape_member(self):
        rack_shape = self._create_rack_shape()
        return self._create_member(RackShapeMember, rack_shape)

    def _create_plate_member(self):
        plate = self._create_plate()
        return self._create_member(PlateMember, plate)

    def _create_plate_specs_member(self):
        plate_specs = self._create_plate_specs()
        return self._create_member(PlateSpecsMember, plate_specs)

    def _create_species_member(self):
        species = self._create_species()
        return self._create_member(SpeciesMember, species)

    def _create_stock_info_member(self):
        stock_info = self._create_stock_info()
        return self._create_member(StockInfoMember, stock_info)

    def _create_subproject_member(self):
        subproject = self._create_subproject()
        return self._create_member(SubprojectMember, subproject)

    def _create_project_member(self):
        project = self._create_project()
        return self._create_member(ProjectMember, project)

    def _create_tube_rack_member(self):
        tube_rack = self._create_tube_rack()
        return self._create_member(TubeRackMember, tube_rack)

    def _create_tube_rack_specs_member(self):
        tube_rack_specs = self._create_tube_rack_specs()
        return self._create_member(TubeRackSpecsMember, tube_rack_specs)


class ThelmaFunctionalTestCase(FunctionalTestCase):
    """
    A basic test class for client side actions.
    """

    package_name = 'thelma'
    app_name = 'thelma'

    @property
    def find_elements(self):
        return etree.XPath('*[local-name() = $name]',
                           namespaces=self.__get_ns_map())

    @property
    def find_entry_contents(self):
        return etree.XPath('/atom:feed/atom:entry/atom:content',
                           namespaces=self.__get_ns_map())

    @property
    def count_entries(self):
        return etree.XPath('count(/atom:feed/atom:entry)',
                           namespaces=self.__get_ns_map())

    def set_up(self):
        FunctionalTestCase.set_up(self)

    def _custom_configure(self):
        self.config.testing_securitypolicy("it")

    def _create_extra_environment(self):
        return create_extra_environ()

    def tear_down(self):
        transaction.abort()
        Session.remove()
        FunctionalTestCase.tear_down(self)

    def _parse_body(self, body):
        if isinstance(body, unicode):
            body = body.encode('utf-8')
        return etree.XML(body)

    def __get_ns_map(self):
        ns_map = get_mapping_registry(AtomMime).namespace_map
        ns_map[XML_PREFIX_ATOM] = XML_NS_ATOM
        if None in ns_map:
            del ns_map[None]
        return ns_map
