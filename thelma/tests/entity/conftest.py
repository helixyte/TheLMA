"""
pytest fixtures for the entity test suite.
"""
from pytest import fixture # pylint: disable=E0611
from pytest import yield_fixture # pylint: disable=E0611
import pytest

from everest.entities.utils import get_root_aggregate
from everest.entities.utils import slug_from_string
from everest.repositories.rdb import Session
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.iso.lab.base import DILUENT_INFO
from thelma.interfaces import IChemicalStructureType
from thelma.interfaces import IExperimentMetadataType
from thelma.interfaces import IItemStatus
from thelma.interfaces import IMoleculeType
from thelma.interfaces import IOrganization
from thelma.interfaces import IPipettingSpecs
from thelma.interfaces import IPlateSpecs
from thelma.interfaces import IRackShape
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import ISpecies
from thelma.interfaces import ITubeSpecs
from thelma.interfaces import IUser
from thelma.models.chemicalstructure import CHEMICAL_STRUCTURE_TYPE_IDS
from thelma.models.chemicalstructure import CompoundChemicalStructure
from thelma.models.chemicalstructure import NucleicAcidChemicalStructure
from thelma.models.container import ContainerLocation
from thelma.models.container import Tube
from thelma.models.container import TubeSpecs
from thelma.models.container import WellSpecs
from thelma.models.device import Device
from thelma.models.device import DeviceType
from thelma.models.experiment import EXPERIMENT_METADATA_TYPES
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.experiment import ExperimentMetadata
from thelma.models.experiment import ExperimentRack
from thelma.models.gene import Gene
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoJobPreparationPlate
from thelma.models.iso import IsoJobStockRack
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoSectorPreparationPlate
from thelma.models.iso import IsoSectorStockRack
from thelma.models.iso import IsoStockRack
from thelma.models.iso import LabIso
from thelma.models.iso import LabIsoRequest
from thelma.models.iso import StockSampleCreationIso
from thelma.models.iso import StockSampleCreationIsoRequest
from thelma.models.job import ExperimentJob
from thelma.models.job import IsoJob
from thelma.models.library import LibraryPlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.liquidtransfer import ExecutedRackSampleTransfer
from thelma.models.liquidtransfer import ExecutedSampleDilution
from thelma.models.liquidtransfer import ExecutedSampleTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PipettingSpecs
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember
from thelma.models.location import BarcodedLocation
from thelma.models.location import BarcodedLocationType
from thelma.models.moleculedesign import CompoundDesign
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculedesign import SiRnaDesign
from thelma.models.organization import Organization
from thelma.models.project import Project
from thelma.models.rack import Plate
from thelma.models.rack import PlateSpecs
from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet
from thelma.models.rack import TubeRack
from thelma.models.rack import TubeRackSpecs
from thelma.models.rack import rack_shape_from_rows_columns
from thelma.models.racklayout import RackLayout
from thelma.models.subproject import Subproject
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.moleculedesign import MoleculeDesignSet
from thelma.models.moleculetype import MoleculeType
from thelma.interfaces import ITubeRackSpecs
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.sample import StockSample
from thelma.models.sample import SampleMolecule
from thelma.models.species import Species
from thelma.models.status import ItemStatus
from thelma.models.stockinfo import StockInfo
from thelma.models.tagging import Tagged
from thelma.models.tubetransfer import TubeTransfer
from thelma.models.user import User
from thelma.models.tubetransfer import TubeTransferWorklist
from thelma.models.user import UserPreferences


__docformat__ = 'reStructuredText en'
__all__ = []

# By design, we have to use fixtures defined in the module scope as
# parameters in other fixture function declarations.
# pylint: disable=W0621


@fixture
def barcoded_location_fac(test_object_fac, barcoded_location_type_fac,
                          device_fac):
    kw = dict(name='test barcoded location',
              label='Test Barcoded Location',
              type=barcoded_location_type_fac(),
              barcode='09999999',
              device=device_fac())
    return test_object_fac(BarcodedLocation, kw=kw)


@fixture
def barcoded_location_type_fac(test_object_fac):
    kw = dict(name='testbcloctp',
              )
    return test_object_fac(BarcodedLocationType, kw=kw)


@fixture
def compound_chemical_structure_fac(test_object_fac):
    kw = dict(representation='COMPOUND')
    return test_object_fac(CompoundChemicalStructure, kw=kw)


@fixture
def compound_molecule_design_fac(test_object_fac, molecule_type_compound,
                                 compound_chemical_structure_fac):
    kw = dict(molecule_type=molecule_type_compound,
              chemical_structures=[compound_chemical_structure_fac()]
              )
    return test_object_fac(CompoundDesign, kw=kw)


@fixture
def container_location_fac(test_object_fac, tube_fac, tube_rack_fac,
                           rack_position_fac):
    kw = dict(rack=tube_rack_fac(),
              position=rack_position_fac(),
              container=tube_fac())
    return test_object_fac(ContainerLocation, kw=kw)



@fixture
def device_fac(test_object_fac, device_type_fac, organization_fac):
    kw = dict(name='TEST_DEVICE',
              label='test device',
              type=device_type_fac(),
              model='test device model',
              manufacturer=organization_fac())
    return test_object_fac(Device, kw=kw)


@fixture
def device_type_fac(test_object_fac):
    kw = dict(name='TEST_DEVICE_TYPE',
              label='test device type')
    return test_object_fac(DeviceType, kw=kw)


@fixture
def executed_rack_sample_transfer_fac(test_object_fac, plate_fac,
                                      planned_rack_sample_transfer_fac,
                                      user_cenixadm):
    kw = dict(source_rack=plate_fac(),
              target_rack=plate_fac(),
              planned_rack_sample_transfer=planned_rack_sample_transfer_fac(),
              user=user_cenixadm
              )
    return test_object_fac(ExecutedRackSampleTransfer, kw=kw)


@fixture
def executed_sample_dilution_fac(test_object_fac, well_fac, rack_position_fac,
                                 reservoir_specs_fac,
                                 planned_sample_dilution_fac, user_cenixadm):
    tgt_position = rack_position_fac(row_index=7, column_index=11)
    kw = dict(target_container=well_fac(position=tgt_position),
              reservoir_specs=reservoir_specs_fac(),
              planned_sample_dilution=planned_sample_dilution_fac(),
              user=user_cenixadm
              )
    return test_object_fac(ExecutedSampleDilution, kw=kw)


@fixture
def executed_sample_transfer_fac(test_object_fac, well_fac, rack_position_fac,
                                 planned_sample_transfer_fac, user_cenixadm):
    tgt_position = rack_position_fac(row_index=7, column_index=10)
    kw = dict(source_container=well_fac(),
              target_container=well_fac.new(position=tgt_position),
              planned_sample_transfer=planned_sample_transfer_fac(),
              user=user_cenixadm
              )
    return test_object_fac(ExecutedSampleTransfer, kw=kw)


@fixture
def executed_worklist_fac(test_object_fac, planned_worklist_fac):
    kw = dict(planned_worklist=planned_worklist_fac())
    return test_object_fac(ExecutedWorklist, kw=kw)


@fixture
def experiment_fac(test_object_fac, experiment_design_fac):
    kw = dict(label='test experiment',
              experiment_design=experiment_design_fac())
    return test_object_fac(Experiment, kw=kw)


@fixture
def experiment_design_fac(test_object_fac, rack_shape_8x12,
                          experiment_metadata_fac, experiment_design_rack_fac):
    kw = dict(rack_shape=rack_shape_8x12,
              experiment_metadata=experiment_metadata_fac(),
              experiment_design_racks=[experiment_design_rack_fac()])
    return test_object_fac(ExperimentDesign, kw=kw)


@fixture
def experiment_design_rack_fac(test_object_fac, rack_layout_fac):
    kw = dict(label='test experiment design rack',
              rack_layout=rack_layout_fac())
    return test_object_fac(ExperimentDesignRack, kw=kw)


@fixture
def experiment_job_fac(test_object_fac, experiment_fac, user_cenixadm):
    kw = dict(label='test experiment job',
              user=user_cenixadm,
              experiments=[experiment_fac()])
    return test_object_fac(ExperimentJob, kw=kw)


@fixture
def experiment_metadata_fac(test_object_fac, subproject_fac,
                            experiment_metadata_type_manual):
    kw = dict(label='test experiment metadata',
              subproject=subproject_fac(),
              number_replicates=1,
              experiment_metadata_type=experiment_metadata_type_manual,
              ticket_number=9999)
    return test_object_fac(ExperimentMetadata, kw=kw)


@fixture
def experiment_rack_fac(test_object_fac, experiment_design_rack_fac,
                        plate_fac, experiment_fac):
    kw = dict(design_rack=experiment_design_rack_fac(),
              rack=plate_fac(),
              experiment=experiment_fac())
    return test_object_fac(ExperimentRack, kw=kw)


@fixture
def gene_fac(test_object_fac, species_human):
    kw = dict(accession='99999',
              locus_name='XXXXX',
              species=species_human)
    return test_object_fac(Gene, kw=kw)


@fixture
def iso_aliquot_plate_fac(test_object_fac, lab_iso_fac, plate_fac):
    kw = dict(iso=lab_iso_fac(),
              rack=plate_fac())
    return test_object_fac(IsoAliquotPlate, kw=kw)


@fixture
def iso_job_fac(test_object_fac, user_cenixadm, lab_iso_fac):
    kw = dict(label='test iso job',
              user=user_cenixadm,
              isos=[lab_iso_fac()],
              number_stock_racks=0
              )
    return test_object_fac(IsoJob, kw=kw)


@fixture
def iso_job_preparation_plate_fac(test_object_fac, iso_job_fac, plate_fac,
                                  rack_layout_fac):
    kw = dict(iso_job=iso_job_fac(),
              rack=plate_fac(),
              rack_layout=rack_layout_fac())
    return test_object_fac(IsoJobPreparationPlate, kw=kw)


@fixture
def iso_job_stock_rack_fac(test_object_fac, iso_job_fac, plate_fac,
                           rack_layout_fac, worklist_series_fac):
    kw = dict(iso_job=iso_job_fac(),
              label='testiso#j0',
              rack=plate_fac(),
              rack_layout=rack_layout_fac(),
              worklist_series=worklist_series_fac())
    return test_object_fac(IsoJobStockRack, kw=kw)


@fixture
def iso_preparation_plate_fac(test_object_fac, lab_iso_fac, plate_fac,
                              rack_layout_fac):
    kw = dict(iso=lab_iso_fac(),
              rack=plate_fac(),
              rack_layout=rack_layout_fac())
    return test_object_fac(IsoPreparationPlate, kw=kw)


@fixture
def iso_sector_preparation_plate_fac(test_object_fac,
                                     stock_sample_creation_iso_fac, plate_fac,
                                     rack_layout_fac):
    kw = dict(iso=stock_sample_creation_iso_fac(),
              rack=plate_fac(),
              sector_index=0,
              rack_layout=rack_layout_fac())
    return test_object_fac(IsoSectorPreparationPlate, kw=kw)


@fixture
def iso_sector_stock_rack_fac(test_object_fac, lab_iso_fac, plate_fac,
                              rack_layout_fac, worklist_series_fac):
    kw = dict(iso=lab_iso_fac(),
              sector_index=0,
              label='testiso#00',
              rack=plate_fac(),
              rack_layout=rack_layout_fac(),
              worklist_series=worklist_series_fac(),
              )
    return test_object_fac(IsoSectorStockRack, kw=kw)


@fixture
def iso_stock_rack_fac(test_object_fac, lab_iso_fac, plate_fac,
                       rack_layout_fac, worklist_series_fac):
    kw = dict(iso=lab_iso_fac(),
              label='testiso#0',
              rack=plate_fac(),
              rack_layout=rack_layout_fac(),
              worklist_series=worklist_series_fac(),
              )
    return test_object_fac(IsoStockRack, kw=kw)


@fixture
def item_status_fac(test_object_fac):
    kw = dict(id='TESTIS',
              name='test item status',
              description='test item status description')
    return test_object_fac(ItemStatus, kw=kw)


@fixture
def lab_iso_fac(test_object_fac, rack_layout_fac, lab_iso_request_fac):
    kw = dict(label='test iso',
              number_stock_racks=4,
              rack_layout=rack_layout_fac.new(),
              iso_request=lab_iso_request_fac())
    return test_object_fac(LabIso, kw=kw)


@fixture
def lab_iso_request_fac(test_object_fac, user_cenixadm, rack_layout_fac,
                        reservoir_specs_std96):
    kw = dict(label='test lab iso request',
              requester=user_cenixadm,
              rack_layout=rack_layout_fac(),
              iso_plate_reservoir_specs=reservoir_specs_std96,
              )
    return test_object_fac(LabIsoRequest, kw=kw)


@fixture
def library_plate_fac(test_object_fac, molecule_design_library_fac, plate_fac):
    kw = dict(molecule_design_library=molecule_design_library_fac(),
              rack=plate_fac(),
              layout_number=1)
    return test_object_fac(LibraryPlate, kw=kw)


@fixture
def molecule_fac(test_object_fac, sirna_molecule_design_fac,
                 organization_fac):
    kw = dict(molecule_design=sirna_molecule_design_fac(),
              supplier=organization_fac()
              )
    return test_object_fac(Molecule, kw=kw)


@fixture
def molecule_design_library_fac(test_object_fac, molecule_design_pool_set_fac,
                                rack_layout_fac):
    kw = dict(molecule_design_pool_set=molecule_design_pool_set_fac(),
              label='testlib',
              final_volume=8e-6,
              final_concentration=3e-6,
              number_layouts=10,
              rack_layout=rack_layout_fac(),
              )
    return test_object_fac(MoleculeDesignLibrary, kw=kw)


@fixture
def molecule_design_pool_fac(test_object_fac, sirna_molecule_design_fac,
                             nucleic_acid_chemical_structure_fac):
    md1 = sirna_molecule_design_fac()
    md2 = sirna_molecule_design_fac(chemical_structures=
                                [nucleic_acid_chemical_structure_fac(**kw)
                                 for kw in [dict(representation='CCCCC'),
                                            dict(representation='GGGGG')]
                                 ])
    kw = dict(molecule_designs=set([md1, md2]),
              )
    return test_object_fac(MoleculeDesignPool, kw=kw)


@fixture
def molecule_design_pool_set_fac(test_object_fac, molecule_type_sirna,
                                 molecule_design_pool_fac):
    kw = dict(molecule_type=molecule_type_sirna,
              molecule_design_pools=set([molecule_design_pool_fac()]))
    return test_object_fac(MoleculeDesignPoolSet, kw=kw)


@fixture
def molecule_design_set_fac(test_object_fac, sirna_molecule_design_fac,
                            compound_molecule_design_fac):
    md1 = sirna_molecule_design_fac()
    md2 = compound_molecule_design_fac()
    kw = dict(molecule_designs=set([md1, md2]))
    return test_object_fac(MoleculeDesignSet, kw=kw)


@fixture
def molecule_type_fac(test_object_fac):
    kw = dict(name='testmoltpe',
              default_stock_concentration=5e-5)
    return test_object_fac(MoleculeType, kw=kw)


@fixture
def nucleic_acid_chemical_structure_fac(test_object_fac):
    kw = dict(representation='CTATAUGACTAGATCGATUUT')
    return test_object_fac(NucleicAcidChemicalStructure, kw=kw)


@fixture
def organization_fac(test_object_fac):
    kw = dict(name='test organization')
    return test_object_fac(Organization, kw=kw)


@fixture
def pipetting_specs_fac(test_object_fac):
    kw = dict(name='t p specs',
              min_transfer_volume=1e-6,
              max_transfer_volume=5e-5,
              max_dilution_factor=20,
              has_dynamic_dead_volume=True,
              is_sector_bound=True)
    return test_object_fac(PipettingSpecs, kw=kw)


@fixture
def planned_rack_sample_transfer_fac(test_object_fac):
    kw = dict(volume=5e-6,
              number_sectors=4,
              source_sector_index=0,
              target_sector_index=1)
    return test_object_fac(PlannedRackSampleTransfer.get_entity, kw=kw)


@fixture
def planned_sample_dilution_fac(test_object_fac, rack_position_fac):
    kw = dict(volume=5e-6,
              diluent_info=DILUENT_INFO,
              target_position=rack_position_fac()
              )
    return test_object_fac(PlannedSampleDilution.get_entity, kw=kw)


@fixture
def planned_sample_transfer_fac(test_object_fac, rack_position_fac):
    kw = dict(volume=5e-6,
              source_position=rack_position_fac(),
              target_position=rack_position_fac()
              )
    return test_object_fac(PlannedSampleTransfer.get_entity, kw=kw)


@fixture
def planned_worklist_fac(test_object_fac, pipetting_specs_biomek,
                         planned_sample_dilution_fac):
    kw = dict(label='test planned worklist',
              transfer_type=TRANSFER_TYPES.SAMPLE_DILUTION,
              pipetting_specs=pipetting_specs_biomek,
              planned_liquid_transfers=[planned_sample_dilution_fac()]
              )
    return test_object_fac(PlannedWorklist, kw=kw)


@fixture
def plate_fac(test_object_fac, plate_specs_fac, item_status_managed):
    kw = dict(label='test tube rack',
              specs=plate_specs_fac(),
              status=item_status_managed)
    return test_object_fac(Plate, kw=kw)


@fixture
def plate_specs_fac(test_object_fac, rack_shape_8x12, well_specs_fac):
    kw = dict(label='test plate specs',
              shape=rack_shape_8x12,
              well_specs=well_specs_fac())
    return test_object_fac(PlateSpecs, kw=kw)


@fixture
def project_fac(test_object_fac, user_cenixadm, organization_cenix):
    kw = dict(label='test project',
              leader=user_cenixadm,
              customer=organization_cenix,
              )
    return test_object_fac(Project, kw=kw)


@fixture
def rack_layout_fac(test_object_fac, rack_shape_8x12,
                    tagged_rack_position_set_fac):
    kw = dict(shape=rack_shape_8x12,
              tagged_rack_position_sets=[tagged_rack_position_set_fac()])
    return test_object_fac(RackLayout, kw=kw)


@fixture
def rack_position_fac(test_object_fac):
    kw = dict(row_index=0, column_index=0)
    return test_object_fac(RackPosition.from_indices, kw=kw)


@fixture
def rack_position_set_fac(test_object_fac, rack_position_fac):
    kw = dict(positions=set([rack_position_fac(row_index=pos[0],
                                               column_index=pos[1])
                             for pos in
                             [(0, 1), (0, 2), (1, 0), (1, 1), (1, 3)]]))
    return test_object_fac(RackPositionSet.from_positions, kw=kw)


@fixture
def rack_shape_fac(test_object_fac):
    kw = dict(number_columns=12,
              number_rows=8)
    return test_object_fac(rack_shape_from_rows_columns, kw=kw)


@fixture
def reservoir_specs_fac(test_object_fac, rack_shape_8x12):
    kw = dict(name='test rsv specs',
              description='test reservoir specs description',
              rack_shape=rack_shape_8x12,
              max_volume=1e-4,
              min_dead_volume=1e-6,
              max_dead_volume=5e-6)
    return test_object_fac(ReservoirSpecs, kw=kw)


@fixture
def sample_fac(test_object_fac, tube_fac):
    kw = dict(volume=1e-4,
              container=tube_fac())
    return test_object_fac(Sample, kw=kw)


@fixture
def sample_molecule_fac(test_object_fac, molecule_fac, sample_fac):
    kw = dict(molecule=molecule_fac(),
              concentration=5e-5,
              sample=sample_fac()
              )
    return test_object_fac(SampleMolecule, kw=kw)


@fixture
def sirna_molecule_design_fac(test_object_fac, molecule_type_sirna,
                        nucleic_acid_chemical_structure_fac):
    kw = dict(molecule_type=molecule_type_sirna,
              chemical_structures=[nucleic_acid_chemical_structure_fac(**kw)
                                   for kw in [dict(representation='TTTTT'),
                                              dict(representation='AAAAA')]],
              )
    return test_object_fac(SiRnaDesign, kw=kw)


@fixture
def species_fac(test_object_fac):
    kw = dict(genus_name='Bufo',
              species_name='bufo',
              common_name='kroete',
              acronym='BB',
              ncbi_tax_id=999)
    return test_object_fac(Species, kw=kw)


@fixture
def stock_info_fac(test_object_fac, molecule_design_pool_fac,
                   molecule_type_sirna):
    kw = dict(molecule_design_pool=molecule_design_pool_fac(),
              molecule_type=molecule_type_sirna,
              concentration=5e-5,
              total_tubes=5,
              total_volume=1e-4,
              minimum_volume=1e-5,
              maximum_volume=1e-5)
    return test_object_fac(StockInfo, kw=kw)


@fixture
def stock_sample_fac(test_object_fac, tube_fac, molecule_design_pool_fac,
                     organization_fac, molecule_type_sirna):
    kw = dict(volume=1e-4,
              container=tube_fac(),
              molecule_design_pool=molecule_design_pool_fac(),
              supplier=organization_fac(),
              molecule_type=molecule_type_sirna,
              concentration=5e-5)
    return test_object_fac(StockSample, kw=kw)


@fixture
def stock_sample_creation_iso_fac(test_object_fac, rack_layout_fac,
                                  stock_sample_creation_iso_request_fac):
    kw = dict(label='test iso',
              number_stock_racks=4,
              rack_layout=rack_layout_fac.new(),
              ticket_number=99999,
              layout_number=1,
              iso_request=stock_sample_creation_iso_request_fac())
    return test_object_fac(StockSampleCreationIso, kw=kw)


@fixture
def stock_sample_creation_iso_request_fac(test_object_fac):
    kw = dict(label='test lab iso request',
              stock_volume=5e-5,
              stock_concentration=1e-4,
              preparation_plate_volume=4e-5,
              number_designs=3,
              )
    return test_object_fac(StockSampleCreationIsoRequest, kw=kw)


@fixture
def subproject_fac(test_object_fac, project_fac):
    kw = dict(label='test subproject',
              project=project_fac())
    return test_object_fac(Subproject, kw=kw)


@fixture
def tag_fac(test_object_fac):
    kw = dict(domain='test_domain',
            predicate='test_predicate',
            value='test_value')
    return test_object_fac(Tag, kw=kw)


@fixture
def tagged_fac(test_object_fac, tag_fac, user_cenixadm):
    kw = dict(tags=set([tag_fac(domain='rackshapes',
                                predicate='default',
                                value='true'),
                        tag_fac(domain='audit',
                                predicate='creator',
                                value='someone')
                        ]),
              user=user_cenixadm
              )
    return test_object_fac(Tagged, kw=kw)


@fixture
def tagged_rack_position_set_fac(test_object_fac, tag_fac,
                                 rack_position_set_fac, user_cenixadm):
    return test_object_fac(TaggedRackPositionSet,
                           kw=dict(tags=set([tag_fac(value='value%d' % cnt)
                                             for cnt in range(3)]),
                                   rack_position_set=rack_position_set_fac(),
                                   user=user_cenixadm))


@fixture
def tube_fac(test_object_fac, tube_specs_fac, item_status_managed):
    kw = dict(specs=tube_specs_fac(),
              status=item_status_managed,
              barcode='1019999999')
    return test_object_fac(Tube, kw=kw)


@fixture
def tube_rack_fac(test_object_fac, tube_rack_specs_fac, item_status_managed):
    kw = dict(label='test tube rack',
              specs=tube_rack_specs_fac(),
              status=item_status_managed)
    return test_object_fac(TubeRack, kw=kw)


@fixture
def tube_rack_specs_fac(test_object_fac, rack_shape_8x12):
    kw = dict(label='test tube rack specs',
              shape=rack_shape_8x12)
    return test_object_fac(TubeRackSpecs, kw=kw)


@fixture
def tube_specs_fac(test_object_fac, organization_fac, tube_rack_specs_fac):
    kw = dict(label='test tube specs',
              max_volume=1e-4,
              dead_volume=5e-6,
              manufacturer=organization_fac(),
              tube_rack_specs=[tube_rack_specs_fac()])
    return test_object_fac(TubeSpecs, kw=kw)


@fixture
def tube_transfer_fac(test_object_fac, tube_fac, tube_rack_fac,
                      rack_position_fac):
    kw = dict(tube=tube_fac(),
              source_rack=tube_rack_fac(),
              source_position=rack_position_fac(),
              target_rack=tube_rack_fac.new(),
              target_position=rack_position_fac())
    return test_object_fac(TubeTransfer, kw=kw)


@fixture
def tube_transfer_worklist_fac(test_object_fac, user_cenixadm,
                               tube_transfer_fac):
    kw = dict(user=user_cenixadm,
              tube_transfers=[tube_transfer_fac()],
              )
    return test_object_fac(TubeTransferWorklist, kw=kw)


@fixture
def user_fac(test_object_fac):
    kw = dict(username='test user',
              directory_user_id='testuser')
    return test_object_fac(User, kw=kw)


@fixture
def user_preferences_fac(test_object_fac, user_cenixadm):
    kw = dict(user=user_cenixadm,
              app_name='test app',
              preferences='test preferences')
    return test_object_fac(UserPreferences, kw=kw)


@fixture
def well_fac(test_object_fac, well_specs_fac, item_status_managed, plate_fac,
             rack_position_fac):
    def _fetch_well(**kw):
        pos = kw['position']
        rack = kw['rack']
        well = rack.container_locations[pos].container
        well.status = kw['status']
        return well
    # Wells are actually created in the constructor of its plate, hence we
    # have to do things a little different here.
    kw = dict(specs=well_specs_fac(),
              status=item_status_managed,
              rack=plate_fac(),
              position=rack_position_fac())
    return test_object_fac(_fetch_well, kw=kw)


@fixture
def well_specs_fac(test_object_fac, organization_fac):
    kw = dict(label='test tube specs',
              max_volume=1e-4,
              dead_volume=5e-6,
              plate_specs=None,
              manufacturer=organization_fac())
    return test_object_fac(WellSpecs, kw=kw)


@fixture
def worklist_series_fac(test_object_fac):
    kw = dict()
    return test_object_fac(WorklistSeries, kw=kw)


@fixture
def worklist_series_member_fac(test_object_fac, planned_worklist_fac,
                               worklist_series_fac):
    kw = dict(planned_worklist=planned_worklist_fac(),
              worklist_series=worklist_series_fac(),
              index=0
              )
    return test_object_fac(WorklistSeriesMember, kw=kw)


# pylint: enable=W0621


@pytest.mark.usefixtures('session_entity_repo', 'session')
class TestEntityBase(object):
    """
    Base class for classes that test entities.
    """
    package_name = 'thelma'
    ini_section_name = 'app:thelma'


# Constants fixtures.

@fixture
def chemical_structure_type_nucleic_acid():
    agg = get_root_aggregate(IChemicalStructureType)
    return agg.get_by_slug(CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID.lower())


@fixture
def experiment_metadata_type_manual():
    agg = get_root_aggregate(IExperimentMetadataType)
    return agg.get_by_slug(EXPERIMENT_METADATA_TYPES.MANUAL.lower())


@fixture
def item_status_destroyed():
    agg = get_root_aggregate(IItemStatus)
    return agg.get_by_slug(ITEM_STATUS_NAMES.MANAGED.lower())


@fixture
def item_status_managed():
    agg = get_root_aggregate(IItemStatus)
    return agg.get_by_slug(ITEM_STATUS_NAMES.MANAGED.lower())


@fixture
def molecule_type_sirna():
    agg = get_root_aggregate(IMoleculeType)
    return agg.get_by_slug('sirna')


@fixture
def molecule_type_compound():
    agg = get_root_aggregate(IMoleculeType)
    return agg.get_by_slug('compound')


@fixture
def organization_cenix():
    agg = get_root_aggregate(IOrganization)
    return agg.get_by_slug('cenix')


@fixture
def pipetting_specs_biomek():
    agg = get_root_aggregate(IPipettingSpecs)
    return agg.get_by_slug(PIPETTING_SPECS_NAMES.BIOMEK.lower())


@fixture
def plate_specs_std96():
    agg = get_root_aggregate(IPlateSpecs)
    return agg.get_by_slug('std96')


@fixture
def rack_shape_8x12():
    agg = get_root_aggregate(IRackShape)
    return agg.get_by_slug('8x12')


@fixture
def rack_shape_16x24():
    agg = get_root_aggregate(IRackShape)
    return agg.get_by_slug('16x24')


@fixture
def reservoir_specs_std96():
    agg = get_root_aggregate(IReservoirSpecs)
    return agg.get_by_slug(
                    slug_from_string(RESERVOIR_SPECS_NAMES.STANDARD_96))

@fixture
def species_human():
    agg = get_root_aggregate(ISpecies)
    return agg.get_by_slug('human')


@fixture
def tube_rack_specs_matrix():
    agg = get_root_aggregate(ITubeRackSpecs)
    return agg.get_by_slug('matrix0500')


@fixture
def tube_specs_matrix():
    agg = get_root_aggregate(ITubeSpecs)
    return agg.get_by_slug('matrix0500')


@fixture
def user_cenixadm():
    agg = get_root_aggregate(IUser)
    return agg.get_by_slug('cenixadm')


class SessionContextManager(object):
    def __enter__(self):
        Session.remove()

    def __exit__(self, ext_type, value, tb):
        Session.remove()


@yield_fixture
def session():
    with SessionContextManager():
        yield


@yield_fixture
def nested_session():
    with RdbContextManager() as sess:
        yield sess
