"""
Transfer execution test cases.

AAB
"""
from everest.testing import check_attributes
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.semiconstants import get_pipetting_specs_biomek
from thelma.automation.tools.semiconstants import get_pipetting_specs_cybio
from thelma.automation.tools.semiconstants import get_pipetting_specs_manual
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base \
    import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.execution \
    import ContainerDilutionWorklistExecutor
from thelma.automation.tools.worklists.execution \
    import ContainerTransferWorklistExecutor
from thelma.automation.tools.worklists.execution \
    import RackTransferExecutor
from thelma.automation.tools.worklists.execution import SampleComponent
from thelma.automation.tools.worklists.execution import SampleData
from thelma.automation.tools.worklists.execution import SourceSample
from thelma.automation.tools.worklists.execution import TargetSample
from thelma.automation.tools.worklists.execution import TransferredSample
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IOrganization
from thelma.interfaces import IReservoirSpecs
from thelma.interfaces import ITubeSpecs
from thelma.interfaces import IUser
from thelma.models.container import ContainerLocation
from thelma.models.container import Tube
from thelma.models.container import TubeSpecs
from thelma.models.container import WellSpecs
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import Plate
from thelma.models.rack import PlateSpecs
from thelma.models.rack import TubeRackSpecs
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.sample import SampleMolecule
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class ExecutionHelperClassesTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.volume = 5 / VOLUME_CONVERSION_FACTOR
        self.concentration = 100 / CONCENTRATION_CONVERSION_FACTOR
        self.supplier = self._get_entity(IOrganization)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.volume
        del self.concentration
        del self.supplier

    def _get_sample(self, volume=None, container=None):
        if volume is None: volume = self.volume
        if container is None:
            container = self._get_tube()
        return Sample(volume, container)

    def _get_tube(self):
        # this is way is fater than aggregates
        tube_specs = self._get_entity(ITubeSpecs)
        return Tube(id=1, specs=tube_specs, status=get_item_status_future(),
                    barcode='01234')

    def _get_sample_molecule(self, molecule_design_id=11, concentration=None,
                             sample=None):
        md = self._get_entity(IMoleculeDesign, str(molecule_design_id))
        mol = Molecule(molecule_design=md, supplier=self.supplier)
        if concentration is None: concentration = self.concentration
        if sample is None: sample = self._get_sample()
        return SampleMolecule(molecule=mol, concentration=concentration,
                              sample=sample)

    def _get_sample_component(self, molecule_design_id=11, concentration=None):
        md = self._get_entity(IMoleculeDesign, str(molecule_design_id))
        mol = Molecule(molecule_design=md, supplier=self.supplier)
        if concentration is None: concentration = self.concentration
        return SampleComponent(molecule=mol, concentration=concentration)


class SampleComponentTestCase(ExecutionHelperClassesTestCase):

    def __get_init_data(self):
        md = self._get_entity(IMoleculeDesign, '11')
        molecule = Molecule(molecule_design=md, supplier=self.supplier)
        return dict(molecule=molecule, concentration=self.concentration)

    def test_init(self):
        kw = self.__get_init_data()
        sc = SampleComponent(**kw)
        self.assert_is_not_none(sc)
        kw['concentration'] = 100
        kw['molecule_design'] = kw['molecule'].molecule_design
        check_attributes(sc, kw)


class SampleDataTestCase(ExecutionHelperClassesTestCase):

    def test_init(self):
        self.assert_raises(TypeError, SampleData, self.volume)


class TransferredSampleTestCase(ExecutionHelperClassesTestCase):

    def __get_transferred_sample(self):
        return TransferredSample(volume=self.volume)

    def test_init(self):
        ts = self.__get_transferred_sample()
        self.assert_is_not_none(ts)
        self.assert_equal(ts.volume, 5)
        self.assert_equal(len(ts.sample_components), 0)

    def test_from_sample(self):
        sample = self._get_sample()
        self.assert_raises(NotImplementedError, TransferredSample.from_sample,
                           sample)

    def test_update_container_sample(self):
        tube = self._get_tube()
        ts = self.__get_transferred_sample()
        self.assert_raises(NotImplementedError, ts.update_container_sample,
                           tube)

    def test_add_sample_component(self):
        ts = self.__get_transferred_sample()
        self.assert_equal(len(ts.sample_components), 0)
        sm = self._get_sample_molecule(molecule_design_id=11,
                            concentration=100 / CONCENTRATION_CONVERSION_FACTOR)
        ts.add_sample_component(sm)
        self.assert_equal(len(ts.sample_components), 1)
        for md_id, sc in ts.sample_components.iteritems():
            self.assert_equal(sc.__class__, SampleComponent)
            self.assert_equal(md_id, sc.molecule_design.id)
            self.assert_equal(md_id, 11)
            self.assert_equal(sc.concentration, 100)

    def test_add_source_sample_components(self):
        sc11 = self._get_sample_component(molecule_design_id=11)
        ts = self.__get_transferred_sample()
        ts.add_sample_component(sc11)
        self.assert_equal(len(ts.sample_components), 1)
        self.assert_equal(ts.sample_components.keys(), [11])
        sc12 = self._get_sample_component(molecule_design_id=12)
        ssc = {12 : sc12}
        ts.add_source_sample_components(ssc)
        self.assert_equal(len(ts.sample_components), 1)
        self.assert_equal(ts.sample_components.keys(), [12])


class SourceSampleTestCase(ExecutionHelperClassesTestCase):

    def __get_source_sample(self):
        ss = SourceSample(volume=self.volume)
        sm = self._get_sample_molecule()
        ss.add_sample_component(sm)
        return ss

    def test_init(self):
        ss = SourceSample(volume=self.volume)
        self.assert_is_not_none(ss)
        self.assert_equal(ss.volume, 5)
        self.assert_equal(ss.total_transfer_volume, 0)

    def test_from_sample(self):
        sample = self._get_sample()
        ss = SourceSample.from_sample(sample)
        self.assert_is_not_none(ss)
        self.assert_equal(ss.volume, 5)
        self.assert_equal(ss.total_transfer_volume, 0)

    def test_create_and_add_transfer(self):
        ss = self.__get_source_sample()
        self.assert_equal(ss.total_transfer_volume, 0)
        rack_pos = get_rack_position_from_label('A1')
        # planned container dilutions are not allowed
        pcd = PlannedContainerDilution(volume=1 / VOLUME_CONVERSION_FACTOR,
                                       target_position=rack_pos,
                                       diluent_info='diluent')
        self.assert_raises(TypeError, ss.create_and_add_transfer, pcd)
        # planned container transfer
        pct = PlannedContainerTransfer(volume=1 / VOLUME_CONVERSION_FACTOR,
                                       source_position=rack_pos,
                                       target_position=rack_pos)
        ts1 = ss.create_and_add_transfer(pct)
        self.assert_is_not_none(ts1)
        self.assert_equal(ts1.volume, 1)
        self.assert_equal(len(ts1.sample_components), 1)
        self.assert_equal(ss.total_transfer_volume, 1)
        # planned rack transfer
        prt = PlannedRackTransfer(volume=2 / VOLUME_CONVERSION_FACTOR,
                                  source_sector_index=0, target_sector_index=0,
                                  sector_number=1)
        ts2 = ss.create_and_add_transfer(prt)
        self.assert_is_not_none(ts2)
        self.assert_equal(ts2.volume, 2)
        self.assert_equal(len(ts2.sample_components), 1)
        self.assert_equal(ss.total_transfer_volume, 3)
        self.assert_equal(ts1.sample_components.keys(),
                          ts2.sample_components.keys())

    def test_update_container_sample(self):
        tube = self._get_tube()
        sample = self._get_sample(container=tube)
        sm = self._get_sample_molecule(sample=sample)
        ss = SourceSample.from_sample(sample)
        # check tube sample
        self.assert_equal(sample.volume * VOLUME_CONVERSION_FACTOR, 5)
        self.assert_equal(len(sample.sample_molecules), 1)
        sm = sample.sample_molecules[0]
        self.assert_equal(sm.concentration * CONCENTRATION_CONVERSION_FACTOR,
                          100)
        self.assert_equal(sm.molecule.molecule_design.id, 11)
        # add planned container transfer
        rack_pos = get_rack_position_from_label('A1')
        pct = PlannedContainerTransfer(volume=1 / VOLUME_CONVERSION_FACTOR,
                                       source_position=rack_pos,
                                       target_position=rack_pos)
        ts1 = ss.create_and_add_transfer(pct)
        self.assert_is_not_none(ts1)
        self.assert_equal(ts1.volume, 1)
        self.assert_equal(len(ts1.sample_components), 1)
        self.assert_equal(ss.total_transfer_volume, 1)
        # update tube
        updated_sample = ss.update_container_sample(tube)
        self.assert_is_not_none(updated_sample)
        self.assert_equal(updated_sample.volume * VOLUME_CONVERSION_FACTOR, 4)
        self.assert_equal(len(updated_sample.sample_molecules), 1)
        updated_sm = updated_sample.sample_molecules[0]
        self.assert_equal(sm, updated_sm)


class TargetSampleTestCase(ExecutionHelperClassesTestCase):

    def __get_target_sample(self):
        ts = TargetSample(volume=self.volume)
        sm = self._get_sample_molecule()
        ts.add_sample_component(sm)
        return ts

    def test_init(self):
        ts = TargetSample(volume=self.volume)
        self.assert_is_not_none(ts)
        self.assert_equal(ts.volume, 5)
        self.assert_equal(ts.final_volume, 5)

    def test_from_sample(self):
        sample = self._get_sample()
        ts = TargetSample.from_sample(sample)
        self.assert_is_not_none(ts)
        self.assert_equal(ts.volume, 5)
        self.assert_equal(ts.final_volume, 5)

    def test_add_tramsfer(self):
        ts = self.__get_target_sample()
        self.assert_equal(ts.final_volume, 5)
        transfer = TransferredSample(volume=self.volume)
        ts.add_transfer(transfer)
        self.assert_equal(ts.final_volume, 10)
        self.assert_raises(AttributeError, ts.add_transfer, transfer)

    def test_create_and_add_transfer(self):
        ts = self.__get_target_sample()
        self.assert_equal(ts.final_volume, 5)
        # planned container transfers are not allowed
        rack_pos = get_rack_position_from_label('A1')
        pct = PlannedContainerTransfer(volume=5 / VOLUME_CONVERSION_FACTOR,
                        source_position=rack_pos, target_position=rack_pos)
        self.assert_raises(TypeError, ts.create_and_add_transfer, pct)
        # planned rack transfers are not allowed
        prt = PlannedRackTransfer(volume=5 / VOLUME_CONVERSION_FACTOR,
                source_sector_index=0, target_sector_index=0, sector_number=1)
        self.assert_raises(TypeError, ts.create_and_add_transfer, prt)
        # planned container dilution
        pcd = PlannedContainerDilution(volume=5 / VOLUME_CONVERSION_FACTOR,
                                target_position=rack_pos, diluent_info='some')
        transfer = ts.create_and_add_transfer(pcd)
        self.assert_is_not_none(transfer)
        self.assert_equal(transfer.volume, 5)
        self.assert_equal(len(transfer.sample_components), 0)
        self.assert_equal(ts.final_volume, 10)
        # two transfers are not allowed
        self.assert_raises(AttributeError, ts.create_and_add_transfer, pcd)

    def test_update_container(self):
        # prepare sample
        volume = 10 / VOLUME_CONVERSION_FACTOR
        sample = self._get_sample(volume)
        self._get_sample_molecule(molecule_design_id=11, sample=sample,
                            concentration=12 / CONCENTRATION_CONVERSION_FACTOR)
        self._get_sample_molecule(molecule_design_id=12, sample=sample,
                            concentration=12 / CONCENTRATION_CONVERSION_FACTOR)
        # prepare transferred sample
        transfer = TransferredSample(volume=20 / VOLUME_CONVERSION_FACTOR)
        sm3 = self._get_sample_molecule(molecule_design_id=11,
                            concentration=6 / CONCENTRATION_CONVERSION_FACTOR)
        sm4 = self._get_sample_molecule(molecule_design_id=13,
                            concentration=9 / CONCENTRATION_CONVERSION_FACTOR)
        transfer.add_sample_component(sm3)
        transfer.add_sample_component(sm4)
        # test with sample and transfer
        expected_concentrations = {11 : 8, 12 : 4, 13 : 6}
        self.__check_tube_update(sample, transfer, 30, expected_concentrations)
        # test with transfer only
        empty_sample = self._get_sample(volume=0)
        expected_concentrations = {11 : 6, 13 : 9}
        self.__check_tube_update(empty_sample, transfer, 20,
                                 expected_concentrations)
        # test with target sample only
        sample = self._get_sample(volume) # need new sample
        self._get_sample_molecule(molecule_design_id=11, sample=sample,
                            concentration=12 / CONCENTRATION_CONVERSION_FACTOR)
        self._get_sample_molecule(molecule_design_id=12, sample=sample,
                            concentration=12 / CONCENTRATION_CONVERSION_FACTOR)
        expected_concentrations = {11 : 12, 12 : 12}
        self.__check_tube_update(sample, None, 10, expected_concentrations)
        # test neither transfer nor target
        empty_sample = self._get_sample(volume=0) # need new sample
        expected_concentrations = dict()
        self.__check_tube_update(empty_sample, None, 0, expected_concentrations)

    def __check_tube_update(self, target_sample_entity, transfer,
                            expected_final_volume, expected_concentrations):
        # prepare
        ts = TargetSample.from_sample(target_sample_entity)
        if not transfer is None: ts.add_transfer(transfer)
        tube = self._get_tube()
        tube.sample = target_sample_entity
        # check result
        tube_sample = ts.update_container_sample(tube)
        self.assert_equal(ts.final_volume, expected_final_volume)
        if expected_final_volume == 0:
            self.assert_is_none(tube_sample)
        else:
            self.assert_is_not_none(tube_sample)
            self.assert_equal(tube_sample.volume * VOLUME_CONVERSION_FACTOR,
                              expected_final_volume)
            self.assert_equal(len(tube_sample.sample_molecules),
                              len(expected_concentrations))
            found_mds = []
            for sm in tube_sample.sample_molecules:
                md_id = sm.molecule.molecule_design.id
                found_mds.append(md_id)
                expected_conc = expected_concentrations[md_id]
                sample_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                self.assert_equal(expected_conc, sample_conc)
            found_mds.sort()
            expected_mds = expected_concentrations.keys()
            expected_mds.sort()
            self.assert_equal(found_mds, expected_mds)


class LiquidTransferExecutorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.executor_user = self._get_entity(IUser, 'it')
        self.target_rack = None
        self.target_plate = None
        self.target_tube_rack = None
        self.source_rack = None
        self.source_plate = None
        self.source_tube_rack = None
        # values for racks and reservoirs
        self.shape = get_96_rack_shape()
        self.supplier = self._get_entity(IOrganization, key='ambion')
        self.plate_specs = None
        self.well_specs = None
        self.tube_rack_specs = None
        self.tube_specs = None
        self.tube_counter = 0
        self.container_max_volume = 0.000200 # 200 ul
        self.container_dead_volume = 0.000010 # 10 ul
        self.starting_volume_target = 0.000010 # 10 ul
        self.starting_conc_target = 0.000000120 # 120 nM
        self.molecule_design_source = self._get_entity(IMoleculeDesign,
                                                       '10001')
        self.molecule_design_target = self._get_entity(IMoleculeDesign,
                                                       '10002')
        self.pipetting_specs = get_pipetting_specs_biomek()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.target_rack
        del self.target_plate
        del self.target_tube_rack
        del self.source_rack
        del self.source_plate
        del self.source_tube_rack
        del self.shape
        del self.supplier
        del self.plate_specs
        del self.well_specs
        del self.tube_rack_specs
        del self.tube_specs
        del self.tube_counter
        del self.container_max_volume
        del self.container_dead_volume
        del self.starting_volume_target
        del self.starting_conc_target
        del self.molecule_design_source
        del self.molecule_design_target
        del self.pipetting_specs

    def _continue_setup(self, create_sample_molecules_src=True,
                              create_sample_molecules_trg=True):
        self._create_worklist()
        self._create_rack_specs()
        self._create_source_rack()
        self._create_target_rack()
        self._fill_source_rack(create_sample_molecules_src)
        self._fill_target_rack(create_sample_molecules_trg)
        if not self.target_plate is None:
            self.target_rack = self.target_plate
            self.source_rack = self.source_plate
        self._create_tool()

    def _create_rack_specs(self):
        if self.well_specs is None:
            self.well_specs = WellSpecs(label='execution_test_well_specs',
                                        max_volume=self.container_max_volume,
                                        dead_volume=self.container_dead_volume,
                                        plate_specs=None)
        if self.plate_specs is None:
            self.plate_specs = PlateSpecs(label='execution_test_plate_specs',
                                          shape=self.shape,
                                          well_specs=self.well_specs)
        if self.tube_specs is None:
            self.tube_specs = TubeSpecs(label='excution_test_tube_specs',
                                        max_volume=self.container_max_volume,
                                        dead_volume=self.container_dead_volume,
                                        tube_rack_specs=None)
        if self.tube_rack_specs is None:
            self.tube_rack_specs = TubeRackSpecs(shape=self.shape,
                                        label='execution_test_tube_rack_specs',
                                        tube_specs=[self.tube_specs])

    def _create_worklist(self):
        raise NotImplementedError('Abstract method.')

    def _create_source_rack(self):
        self.source_plate = self.plate_specs.create_rack(
                                        label='source_plate',
                                        status=get_item_status_managed())
        self.source_tube_rack = self.tube_rack_specs.create_rack(
                                        label='source_tube_rack',
                                        status=get_item_status_managed())

    def _create_target_rack(self):
        self.target_plate = self.plate_specs.create_rack(
                                            label='target plate',
                                            status=get_item_status_future())
        self.target_tube_rack = self.tube_rack_specs.create_rack(
                                            label='target_tube_rack',
                                            status=get_item_status_future())

    def _fill_source_rack(self, create_sample_molecules_src):
        raise NotImplementedError('Abstract method.')

    def _fill_target_rack(self, create_sample_molecules_trg):
        raise NotImplementedError('Abstract method.')

    def _get_alternative_rack(self, container_positions, volume):
        rack = self.tube_rack_specs.create_rack(label='invalid rack',
                                               status=get_item_status_managed())
        for pos_label in container_positions:
            rack_pos = get_rack_position_from_label(pos_label)
            self.tube_counter += 1
            barcode = '%04i' % (self.tube_counter)
            tube = Tube.create_from_rack_and_position(specs=self.tube_specs,
                                        status=get_item_status_managed(),
                                        position=rack_pos,
                                        barcode=barcode, rack=rack)
            tube.make_sample(volume)
            rack.containers.append(tube)

        return rack

    def _create_test_sample(self, volume, container, md, conc):
        sample = Sample(volume, container)
        if not md is None:
            mol = Molecule(molecule_design=md, supplier=self.supplier)
            sample.make_sample_molecule(mol, conc)
        return sample

    def _create_test_tube(self, pos_label, rack, item_status):
        rack_pos = get_rack_position_from_label(pos_label)
        self.tube_counter += 1
        barcode = '%04i' % (self.tube_counter)
        tube = self.tube_specs.create_tube(item_status=item_status,
                                           barcode=barcode, location=None)
        ContainerLocation(container=tube, rack=rack, position=rack_pos)
        rack.containers.append(tube)
        return  tube

    def _test_invalid_user(self):
        eu = self.executor_user
        self.executor_user = self.executor_user.username
        self._test_and_expect_errors('The user must be a User object')
        self.executor_user = eu

    def _test_invalid_target_rack(self):
        trg_rack = self.target_rack
        self.target_rack = None
        self._test_and_expect_errors('The target rack must be a Rack object')
        self.target_rack = trg_rack

    def _test_invalid_pipetting_specs(self):
        ps = self.pipetting_specs
        self.pipetting_specs = 3
        self._test_and_expect_errors('The pipetting specs must be a ' \
                                     'PipettingSpecs object')
        self.pipetting_specs = ps

    def _test_missing_target_container(self, container_positions):
        self._continue_setup()
        self.target_rack = self._get_alternative_rack(container_positions,
                                                self.starting_volume_target)
        self._test_and_expect_errors('Could not find containers for ' \
                                     'the following target positions')

    def _test_target_volume_too_large(self):
        self.container_max_volume = (self.container_max_volume / 5.)
        self._continue_setup()
        self._test_and_expect_errors('Some target container cannot take up ' \
                                     'the transfer volume')


class WorklistExecutorTestCase(LiquidTransferExecutorTestCase): #pylint: disable=W0223

    def set_up(self):
        LiquidTransferExecutorTestCase.set_up(self)
        self.worklist = None
        self.ignored_positions = []

    def tear_down(self):
        LiquidTransferExecutorTestCase.tear_down(self)
        del self.worklist
        del self.ignored_positions

    def _test_invalid_planned_worklist(self):
        self._continue_setup()
        self.worklist = self.worklist.planned_transfers
        self._test_and_expect_errors('The planned worklist must be a ' \
                                     'PlannedWorklist object')

    def _test_invalid_ignored_positions(self):
        self._continue_setup()
        self.ignored_positions = dict()
        self._test_and_expect_errors('The ignored position list must be a ' \
                                     'list object')
        self.ignored_positions = ['A1', 'B2']
        self._test_and_expect_errors('The ignored rack position must be a ' \
                                     'RackPosition object')


class ContainerDilutionWorklistExecutorTestCase(WorklistExecutorTestCase):

    def set_up(self):
        WorklistExecutorTestCase.set_up(self)
        self.reservoir_specs = self._get_entity(IReservoirSpecs)
        # result data
        # position label, transfer volume, result volume, result conc
        self.result_data = dict(A1=[10, 20, 60],
                                B2=[20, 30, 40],
                                C3=[30, 40, 30],
                                D4=[50, 60, 20],
                                E5=[110, 120, 10])
        # other setup values
        self.rack_setup_pos_target = self.result_data.keys()
        self.diluent_info = 'buffer'

    def tear_down(self):
        WorklistExecutorTestCase.tear_down(self)
        del self.reservoir_specs
        del self.result_data
        del self.rack_setup_pos_target
        del self.diluent_info

    def _create_tool(self):
        self.tool = ContainerDilutionWorklistExecutor(
                      planned_worklist=self.worklist,
                      target_rack=self.target_rack,
                      user=self.executor_user,
                      reservoir_specs=self.reservoir_specs,
                      pipetting_specs=self.pipetting_specs,
                      log=self.log,
                      ignored_positions=self.ignored_positions)

    def _create_worklist(self):
        self.worklist = PlannedWorklist(label='container dilution worklist')
        for pos_label, transfer_data in self.result_data.iteritems():
            volume = transfer_data[0] / VOLUME_CONVERSION_FACTOR
            rack_pos = get_rack_position_from_label(pos_label)
            pcd = PlannedContainerDilution(volume=volume,
                                    target_position=rack_pos,
                                    diluent_info=self.diluent_info)
            self.worklist.planned_transfers.append(pcd)

    def _fill_target_rack(self, create_sample_molecules=True):
        md = self.molecule_design_target
        conc = self.starting_conc_target
        if not create_sample_molecules:
            md = None
            conc = None
        # fill plate
        for container in self.target_plate.containers:
            pos_label = container.location.position.label
            if not pos_label in self.rack_setup_pos_target: continue
            sample = self._create_test_sample(self.starting_volume_target,
                                              container, md, conc)
        # fill tube rack
        for pos_label in self.rack_setup_pos_target:
            tube = self._create_test_tube(pos_label, self.target_tube_rack,
                                          item_status=get_item_status_future())
            sample = self._create_test_sample(self.starting_volume_target,
                                              tube, md, conc)
            tube.sample = sample

    def _fill_source_rack(self, create_sample_molecules_src):
        pass

    def __check_result(self, check_sample_molecules=True,
                       number_executed_transfers=None):
        self._create_tool()
        ew = self.tool.get_result()
        self.assert_is_not_none(ew)
        self.assert_equal(ew.planned_worklist, self.worklist)
        # check executed transfers
        if number_executed_transfers is None:
            number_executed_transfers = len(self.result_data)
        self.assert_equal(len(ew.executed_transfers), number_executed_transfers)
        container_map = dict()
        timestamp = None
        for et in ew.executed_transfers:
            self._check_executed_transfer(et, TRANSFER_TYPES.CONTAINER_DILUTION)
            pt = et.planned_transfer
            pos_label = pt.target_position.label
            container_map[pos_label] = et.target_container
            self.assert_equal(et.reservoir_specs, self.reservoir_specs)
            if timestamp is None:
                timestamp = et.timestamp
            else:
                self.assert_equal(et.timestamp, timestamp)
        # check target rack
        self.assert_equal(self.target_rack.status.name,
                          ITEM_STATUS_NAMES.MANAGED)
        if isinstance(self.target_rack, Plate):
            expected_empty_status = ITEM_STATUS_NAMES.MANAGED
        else:
            expected_empty_status = ITEM_STATUS_NAMES.FUTURE
        for container in self.target_rack.containers:
            rack_pos = container.location.position
            if rack_pos in self.ignored_positions: continue
            pos_label = rack_pos.label
            sample = container.sample
            if not pos_label in self.rack_setup_pos_target:
                self.assert_is_none(sample)
                self.assert_equal(container.status.name, expected_empty_status)
                continue
            self.assert_equal(container.status.name, ITEM_STATUS_NAMES.MANAGED)
            self.assert_equal(container_map[pos_label].location,
                              container.location)
            result_data = self.result_data[pos_label]
            expected_volume = result_data[1]
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(sample_volume, expected_volume)
            if not check_sample_molecules:
                self.assert_equal(len(sample.sample_molecules), 0)
                continue
            expected_conc = result_data[2]
            self.assert_equal(len(sample.sample_molecules), 1)
            sm = sample.sample_molecules[0]
            sample_concentration = round(sm.concentration \
                                   * CONCENTRATION_CONVERSION_FACTOR, 1)
            self.assert_almost_equal(sample_concentration, expected_conc)
            self.assert_equal(sm.molecule.molecule_design,
                              self.molecule_design_target)

    def test_result(self):
        self._continue_setup()
        self.target_rack = self.target_plate
        self.__check_result()
        self.target_rack = self.target_tube_rack
        self.__check_result()

    def test_result_ignore_positions_plate(self):
        self.ignored_positions = [get_rack_position_from_label('A1'),
                                  get_rack_position_from_label('B2'),
                                  get_rack_position_from_label('H8')]
        self.result_data['A1'] = (10, 10, 120)
        self.result_data['B2'] = (10, 10, 120)
        self._continue_setup()
        self.target_rack = self.target_plate
        self.__check_result(number_executed_transfers=3)
        self.target_rack = self.target_tube_rack
        self.__check_result(number_executed_transfers=3)

    def test_result_tube_rack_status_update(self):
        self._continue_setup()
        self._create_test_tube('G8', rack=self.target_tube_rack,
                               item_status=get_item_status_future())
        self.target_rack = self.target_tube_rack
        self.__check_result()

    def test_no_sample_molecules(self):
        self._continue_setup(create_sample_molecules_trg=False)
        self.target_rack = self.target_plate
        self.__check_result(check_sample_molecules=False)
        self.target_rack = self.target_tube_rack
        self.__check_result(check_sample_molecules=False)

    def test_pipetting_specs(self):
        self.result_data['A1'] = [1, 11, round(((120 * 10) / 11.), 1)]
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are smaller ' \
                     'than the allowed minimum transfer volume of 2 ul: ' \
                     'A1 (1.0 ul).')
        self.pipetting_specs = get_pipetting_specs_manual()
        self._create_tool()
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_user()
        self._test_invalid_target_rack()
        self._test_invalid_planned_worklist()
        self._test_invalid_ignored_positions()
        self._test_invalid_pipetting_specs()

    def test_invalid_transfer_type(self):
        self._continue_setup()
        prt = PlannedRackTransfer(volume=self.starting_volume_target,
                                  source_sector_index=0,
                                  target_sector_index=0,
                                  sector_number=1)
        self.worklist = PlannedWorklist(label='invalid worklist',
                                        planned_transfers=[prt])
        self._create_tool()
        self._test_and_expect_errors('Some transfers planned in the worklist ' \
                                     'are not supported')

    def test_transfer_volume_too_large(self):
        self.container_max_volume = 0.001000 # 300 ul
        self.result_data['A1'] = (590, 600, 2)
        self._continue_setup()
        self.__check_result()
        # volume for dilutions can be split, thus: no error

    def test_transfer_volume_too_small(self):
        self.pipetting_specs = get_pipetting_specs_manual()
        self.result_data['A1'] = (1, 11, round((120 / (11 / 10.0)), 1))
        self._continue_setup()
        self.__check_result()
        self.pipetting_specs = get_pipetting_specs_biomek()
        self._create_tool()
        self._test_and_expect_errors('Some transfer volumes are smaller ' \
                                     'than the allowed minimum transfer volume')

    def test_missing_target_container(self):
        positions = ['C3', 'D4', 'E5']
        self._test_missing_target_container(positions)

    def test_target_volume_too_large(self):
        self._test_target_volume_too_large()

    def test_position_beyond_rack_shape(self):
        self.result_data['M2'] = (10, 20, 60)
        self._continue_setup()
        self._test_and_expect_errors('Could not find containers for the ' \
                                     'following target positions')


class ContainerTransferWorklistExecutorTestCase(WorklistExecutorTestCase):

    def set_up(self):
        WorklistExecutorTestCase.set_up(self)
        # result data
        # source volume, source conc, final volume, target labels
        self.source_data = dict(A1=(100, 120, 40, ['A2', 'A3']),
                                B1=(100, 240, 40, ['B2', 'B3']))
        # value = transfer vol, res vol, res src conc, res target conc,
        # number of sample molecules)
        self.target_data = dict(A2=(10, 20, 60, 60, 2),
                                A3=(50, 60, 100, 20, 2),
                                B2=(10, 20, 120, 60, 2),
                                B3=(50, 60, 200, 20, 2))

    def tear_down(self):
        WorklistExecutorTestCase.tear_down(self)
        del self.source_data
        del self.target_data

    def _create_tool(self):
        self.log = TestingLog()
        self.tool = ContainerTransferWorklistExecutor(log=self.log,
                            planned_worklist=self.worklist,
                            target_rack=self.target_rack,
                            user=self.executor_user,
                            source_rack=self.source_rack,
                            ignored_positions=self.ignored_positions,
                            pipetting_specs=self.pipetting_specs)

    def _create_worklist(self):
        self.worklist = PlannedWorklist(label='container transfer worklist')
        for src_label, src_data in self.source_data.iteritems():
            src_pos = get_rack_position_from_label(src_label)
            tgt_labels = src_data[3]
            for tgt_label in tgt_labels:
                trg_pos = get_rack_position_from_label(tgt_label)
                trg_data = self.target_data[tgt_label]
                volume = trg_data[0] / VOLUME_CONVERSION_FACTOR
                pct = PlannedContainerTransfer(volume=volume,
                                source_position=src_pos,
                                target_position=trg_pos)
                self.worklist.planned_transfers.append(pct)

    def _fill_source_rack(self, create_sample_molecules=True):
        md = self.molecule_design_source
        if not create_sample_molecules: md = None
        # fill plate
        for container in self.source_plate.containers:
            pos_label = container.location.position.label
            if not self.source_data.has_key(pos_label): continue
            src_data = self.source_data[pos_label]
            volume = src_data[0] / VOLUME_CONVERSION_FACTOR
            conc = src_data[1] / CONCENTRATION_CONVERSION_FACTOR
            if not create_sample_molecules: conc = None
            self._create_test_sample(volume, container, md, conc)
        # fill tube rack
        for pos_label, src_data in self.source_data.iteritems():
            tube = self._create_test_tube(pos_label, rack=self.source_tube_rack,
                                    item_status=get_item_status_managed())
            volume = src_data[0] / VOLUME_CONVERSION_FACTOR
            conc = src_data[1] / CONCENTRATION_CONVERSION_FACTOR
            if not create_sample_molecules: conc = None
            self._create_test_sample(volume, tube, md, conc)

    def _fill_target_rack(self, create_sample_molecules=True):
        md = self.molecule_design_target
        conc = self.starting_conc_target
        if not create_sample_molecules:
            md = None
            conc = None
        # create plate
        for container in self.target_plate.containers:
            pos_label = container.location.position.label
            if not self.target_data.has_key(pos_label): continue
            self._create_test_sample(self.starting_volume_target, container,
                                     md, conc)
        for pos_label in self.target_data.keys():
            tube = self._create_test_tube(pos_label, self.target_tube_rack,
                                          item_status=get_item_status_future())
            self._create_test_sample(self.starting_volume_target, tube, md,
                                     conc)

    def __check_result(self, check_sample_molecules_src=True,
                       number_executed_transfers=None, create_tool=True):
        if create_tool: self._create_tool()
        ew = self.tool.get_result()
        self.assert_is_not_none(ew)
        # check executed transfers
        if number_executed_transfers is None:
            number_executed_transfers = len(self.target_data)
        self.assert_equal(len(ew.executed_transfers), number_executed_transfers)
        src_container_map = dict()
        trg_container_map = dict()
        timestamp = None
        for et in ew.executed_transfers:
            self._check_executed_transfer(et, TRANSFER_TYPES.CONTAINER_TRANSFER)
            pt = et.planned_transfer
            src_label = pt.source_position.label
            trg_label = pt.target_position.label
            src_container_map[src_label] = et.source_container
            trg_container_map[trg_label] = et.target_container
            if timestamp is None:
                timestamp = et.timestamp
            else:
                self.assert_equal(et.timestamp, timestamp)
        # check source rack
        for container in self.source_rack.containers:
            rack_pos = container.location.position
            if rack_pos in self.ignored_positions: continue
            pos_label = rack_pos.label
            if not self.source_data.has_key(pos_label): continue
            self.assert_equal(src_container_map[pos_label].location,
                              container.location)
            sample = container.sample
            # source volume, source conc, final volume, target labels
            src_data = self.source_data[pos_label]
            expected_volume = src_data[2]
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_almost_equal(sample_volume, expected_volume)
            if check_sample_molecules_src:
                self.assert_equal(len(sample.sample_molecules), 1)
                sm = sample.sample_molecules[0]
                self.assert_equal(sm.molecule.molecule_design,
                                  self.molecule_design_source)
                expected_conc = src_data[1]
                sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                self.assert_almost_equal(sm_conc, expected_conc)
        # check target rack
        missing_positions = []
        #pylint: disable=E1103
        for rack_pos in self.ignored_positions:
            if self.source_data.has_key(rack_pos.label):
                src_data = self.source_data[rack_pos.label]
                for label in src_data[3]: missing_positions.append(label)
        #pylint: enable=E1103

        self.assert_equal(self.target_rack.status.name,
                          ITEM_STATUS_NAMES.MANAGED)
        if isinstance(self.target_rack, Plate):
            expected_empty_status = ITEM_STATUS_NAMES.MANAGED
        else:
            expected_empty_status = ITEM_STATUS_NAMES.FUTURE
        for container in self.target_rack.containers:
            pos_label = container.location.position.label
            sample = container.sample
            if not self.target_data.has_key(pos_label):
                self.assert_is_none(sample)
                self.assert_equal(container.status.name, expected_empty_status)
                continue
            if pos_label in missing_positions:
                self.assert_equal(sample.volume, self.starting_volume_target)
                continue
            self.assert_equal(trg_container_map[pos_label].location,
                              container.location)
            self.assert_equal(container.status.name, ITEM_STATUS_NAMES.MANAGED)
            # value = transfer vol, res vol, res src conc, res target conc,
            # number of sample molecules)
            trg_data = self.target_data[pos_label]
            expected_volume = trg_data[1]
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(sample_volume, expected_volume)
            number_sm = trg_data[4]
            self.assert_equal(len(sample.sample_molecules), number_sm)
            for sm in sample.sample_molecules:
                sample_concentration = round(sm.concentration \
                                       * CONCENTRATION_CONVERSION_FACTOR, 1)
                md = sm.molecule.molecule_design
                if md == self.molecule_design_target:
                    expected_conc = trg_data[3]
                else:
                    expected_conc = trg_data[2]
                self.assert_almost_equal(sample_concentration, expected_conc)

    def test_result_source_plate(self):
        self._continue_setup()
        self.target_rack = self.target_plate
        self.source_rack = self.source_plate
        self.__check_result()
        self.target_rack = self.target_tube_rack
        self.source_rack = self.source_tube_rack
        self.__check_result()

    def test_result_ignore_positions(self):
        self._continue_setup()
        self.source_data['A1'] = (100, 120, 100, ['A2', 'A3'])
        self.target_data['A2'] = (0, 10, 0, 120, 1)
        self.target_data['A3'] = (0, 10, 0, 120, 1)
        self.ignored_positions = [get_rack_position_from_label('A1'),
                                  get_rack_position_from_label('H8')]
        self.target_rack = self.target_plate
        self.source_rack = self.source_plate
        self.__check_result(number_executed_transfers=2)
        self.target_rack = self.target_tube_rack
        self.source_rack = self.source_tube_rack
        self.__check_result(number_executed_transfers=2)

    def test_no_sample_molecules_source(self):
        # value = transfer vol, res vol, res src conc, res target conc,
        # number of sample molecules)
        self.target_data = dict(A2=(10, 20, 0, 60, 1),
                                A3=(50, 60, 0, 20, 1),
                                B2=(10, 20, 0, 60, 1),
                                B3=(50, 60, 0, 20, 1))
        self._continue_setup(create_sample_molecules_src=False)
        self.target_rack = self.target_plate
        self.source_rack = self.source_plate
        self.__check_result(check_sample_molecules_src=False)
        self.target_rack = self.target_tube_rack
        self.source_rack = self.source_tube_rack
        self.__check_result(check_sample_molecules_src=False)

    def test_no_sample_molecules_target(self):
        # value = transfer vol, res vol, res src conc, res target conc,
        # number of sample molecules)
        self.target_data = dict(A2=(10, 20, 60, 0, 1),
                                A3=(50, 60, 100, 0, 1),
                                B2=(10, 20, 120, 0, 1),
                                B3=(50, 60, 200, 0, 1))
        self._continue_setup(create_sample_molecules_trg=False)
        self.target_rack = self.target_plate
        self.source_rack = self.source_plate
        self.__check_result()
        self.target_rack = self.target_tube_rack
        self.source_rack = self.source_tube_rack
        self.__check_result()

    def test_valid_range_overwritten(self):
        self.target_data['A2'] = (1, 11, round((120 / 11.), 1),
                                  round((120 / 1.1), 1), 2)
        self.source_data['A1'] = (100, 120, 49, ['A2', 'A3'])
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are smaller than ' \
                                     'the allowed minimum transfer volume')
        self.tool.reset()
        self.tool.set_minimum_transfer_volume(1)
        self.target_rack = self.target_plate
        self.source_rack = self.source_plate
        self.__check_result(create_tool=False)
        # check errors
        self._create_tool()
        self.tool.set_minimum_transfer_volume('-1')
        result = self.tool.get_result()
        self.assert_is_none(result)
        self._check_error_messages('The minimum transfer volume must be a ' \
                                   'positive number. Obtained: -1.')
        self._create_tool()
        self.tool.set_maximum_transfer_volume('4,3')
        result = self.tool.get_result()
        self.assert_is_none(result)
        self._check_error_messages('The maximum transfer volume must be a ' \
                                   'positive number. Obtained: 4,3.')

    def test_pipetting_specs(self):
        self.target_data['A2'] = (1, 11, round((120 / 11.), 1),
                                  round((120 / 1.1), 1), 2)
        self.source_data['A1'] = (100, 120, 49, ['A2', 'A3'])
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are smaller than ' \
                                     'the allowed minimum transfer volume')
        self.pipetting_specs = get_pipetting_specs_manual()
        self._create_tool()
        self.__check_result()

    def test_result_tube_rack_status_update(self):
        self._continue_setup()
        self._create_test_tube('G8', rack=self.target_tube_rack,
                               item_status=get_item_status_future())
        self.target_rack = self.target_tube_rack
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_user()
        self._test_invalid_target_rack()
        self._test_invalid_planned_worklist()
        self._test_invalid_ignored_positions()
        self._test_invalid_pipetting_specs()

    def test_invalid_transfer_type(self):
        self._continue_setup()
        prt = PlannedRackTransfer(volume=self.starting_volume_target,
                                  source_sector_index=0,
                                  target_sector_index=0,
                                  sector_number=1)
        self.worklist = PlannedWorklist(label='invalid worklist',
                                        planned_transfers=[prt])
        self._create_tool()
        self._test_and_expect_errors('Some transfers planned in the worklist ' \
                                     'are not supported')

    def test_transfer_volume_too_large(self):
        self.container_max_volume = 0.000500 # 300 ul
        self.source_data['A1'] = (400, 120, 100, ['A2', 'A3'])
        self.target_data['A3'] = (290, 300, round((120 / (300 / 290.0)), 1),
                                  4, 2)
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are larger than ' \
                                     'the allowed maximum transfer volume')
        self.pipetting_specs = get_pipetting_specs_manual()
        self._create_tool()
        self.__check_result()

    def test_transfer_volume_too_small(self):
        self.source_data['A1'] = (100, 120, 89, ['A2', 'A3'])
        self.target_data['A3'] = (1, 11, 10.9, round((120 / (11 / 10.0)), 1), 2)
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are smaller ' \
                                     'than the allowed minimum transfer volume')
        self.pipetting_specs = get_pipetting_specs_manual()
        self._create_tool()
        self.__check_result()

    def test_missing_target_container(self):
        positions = ['A2', 'B2']
        self._test_missing_target_container(positions)

    def test_target_volume_too_large(self):
        self._test_target_volume_too_large()

    def test_missing_source_container(self):
        self._continue_setup()
        self.shape = get_384_rack_shape()
        container_positions = ['B1']
        self.source_rack = self._get_alternative_rack(container_positions,
                                                      0.000100)
        self._test_and_expect_errors('Could not find containers for ' \
                                     'the following source positions')

    def test_source_volume_too_small(self):
        self.container_dead_volume = 0.000050 # 50 ul
        self._continue_setup()
        self._test_and_expect_errors()

    def test_position_beyond_rack_shape(self):
        self._continue_setup()
        m2_pos = get_rack_position_from_label('M2')
        g1_pos = get_rack_position_from_label('G1')
        pct = PlannedContainerTransfer(volume=self.starting_volume_target,
                    source_position=m2_pos, target_position=g1_pos)
        self.worklist.planned_transfers.append(pct)
        self._test_and_expect_errors('Could not find containers for the ' \
                                     'following source positions')
        self.source_data['G1'] = (100, 120, 90, ['M2'])
        self.target_data['M2'] = (10, 20, 60, 60, 2)
        self._continue_setup()
        self._test_and_expect_errors('Could not find containers for the ' \
                                     'following target positions')


class RackTransferExecutorTestCase(LiquidTransferExecutorTestCase):

    def set_up(self):
        LiquidTransferExecutorTestCase.set_up(self)
        self.pipetting_specs = get_pipetting_specs_cybio()
        self.planned_rack_transfer = None
        # result data
        self.transfer_volume = 0.000010 # 10 ul
        # source volume, source conc, source final volume
        self.source_data = dict(A1=(40, 120, 30),
                                A2=(35, 120, 25),
                                B1=(40, 240, 30),
                                B2=(35, 240, 25))
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(B2=(10, 120, 20, 60, 60, 'A1', 2),
                                B4=(30, 120, 40, 30, 90, 'A2', 2),
                                D2=(10, 120, 20, 120, 60, 'B1', 2),
                                D4=(30, 120, 40, 60, 90, 'B2', 2))

        # other setup values
        self.sector_number = 4
        self.source_sector_index = 0
        self.target_sector_index = 3
        self.source_rack_barcode = '09999991'
        self.target_rack_barcode = '09999992'
        self.rack_shape_src = get_96_rack_shape()
        self.rack_shape_trg = get_384_rack_shape()
        self.source_rack_specs = None
        self.target_rack_specs = None
        self.use_plates = False

    def tear_down(self):
        LiquidTransferExecutorTestCase.tear_down(self)
        del self.planned_rack_transfer
        del self.transfer_volume
        del self.source_data
        del self.target_data
        del self.sector_number
        del self.source_sector_index
        del self.target_sector_index
        del self.source_rack_barcode
        del self.target_rack_barcode
        del self.rack_shape_src
        del self.rack_shape_trg
        del self.source_rack_specs
        del self.target_rack_specs
        del self.use_plates

    def _create_tool(self):
        self.tool = RackTransferExecutor(log=self.log,
                    planned_rack_transfer=self.planned_rack_transfer,
                    target_rack=self.target_rack,
                    source_rack=self.source_rack,
                    user=self.executor_user,
                    pipetting_specs=self.pipetting_specs)

    def _create_rack_specs(self):
        if self.well_specs is None:
            self.well_specs = WellSpecs(label='execution_test_well_specs',
                                        max_volume=self.container_max_volume,
                                        dead_volume=self.container_dead_volume,
                                        plate_specs=None)
        if self.tube_specs is None:
            self.tube_specs = TubeSpecs(label='excution_test_tube_specs',
                                        max_volume=self.container_max_volume,
                                        dead_volume=self.container_dead_volume,
                                        tube_rack_specs=None)
        if self.use_plates:
            self.source_rack_specs = PlateSpecs(label='source_plate_specs',
                                                shape=self.rack_shape_src,
                                                well_specs=self.well_specs)
            self.target_rack_specs = PlateSpecs(label='target_plate_specs',
                                                shape=self.rack_shape_trg,
                                                well_specs=self.well_specs)
        else:
            self.source_rack_specs = TubeRackSpecs(label='src_tube_rack_specs',
                                                   shape=self.rack_shape_src,
                                                   tube_specs=[self.tube_specs])
            self.target_rack_specs = TubeRackSpecs(label='trg_tube_rack_specs',
                                                   shape=self.rack_shape_trg,
                                                   tube_specs=[self.tube_specs])
            self.tube_rack_specs = self.target_rack_specs

    def _create_worklist(self):
        self.planned_rack_transfer = PlannedRackTransfer(
                                volume=self.transfer_volume,
                                source_sector_index=self.source_sector_index,
                                target_sector_index=self.target_sector_index,
                                sector_number=self.sector_number)

    def _create_source_rack(self):
        self.source_rack = self.source_rack_specs.create_rack(
                                        label='source_rack',
                                        status=get_item_status_managed())
        self.source_rack.barcode = self.source_rack_barcode

    def _create_target_rack(self):
        self.target_rack = self.target_rack_specs.create_rack(
                                            label='target_rack',
                                            status=get_item_status_future())
        self.target_rack.barcode = self.target_rack_barcode

    def _fill_source_rack(self, create_sample_molecules=True):
        md = self.molecule_design_source
        if not create_sample_molecules: md = None
        if self.use_plates:
            for container in self.source_rack.containers:
                pos_label = container.location.position.label
                if not self.source_data.has_key(pos_label): continue
                # source volume, source conc, source final volume
                src_data = self.source_data[pos_label]
                volume = src_data[0] / VOLUME_CONVERSION_FACTOR
                conc = src_data[1] / CONCENTRATION_CONVERSION_FACTOR
                if not create_sample_molecules: conc = None
                self._create_test_sample(volume, container, md, conc)
        else:
            for src_label, src_data in self.source_data.iteritems():
                tube = self._create_test_tube(src_label, rack=self.source_rack,
                                        item_status=get_item_status_managed())
                volume = src_data[0] / VOLUME_CONVERSION_FACTOR
                conc = src_data[1] / CONCENTRATION_CONVERSION_FACTOR
                if not create_sample_molecules: conc = None
                self._create_test_sample(volume, tube, md, conc)

    def _fill_target_rack(self, create_sample_molecules=True):
        md = self.molecule_design_target
        if not create_sample_molecules: md = None
        if self.use_plates:
            for container in self.target_rack.containers:
                pos_label = container.location.position.label
                if not self.target_data.has_key(pos_label): continue
                # target vol (start), target conc (start), target final vol,
                # source final conc, target final conc, source well label
                trg_data = self.target_data[pos_label]
                volume = trg_data[0] / VOLUME_CONVERSION_FACTOR
                conc = trg_data[1] / CONCENTRATION_CONVERSION_FACTOR
                if not create_sample_molecules: conc = None
                self._create_test_sample(volume, container, md, conc)
        else:
            for trg_label, trg_data in self.target_data.iteritems():
                tube = self._create_test_tube(trg_label, rack=self.target_rack,
                                        item_status=get_item_status_future())
                volume = trg_data[0] / VOLUME_CONVERSION_FACTOR
                conc = trg_data[1] / CONCENTRATION_CONVERSION_FACTOR
                if not create_sample_molecules: conc = None
                self._create_test_sample(volume, tube, md, conc)

    def __check_result(self, check_sample_molecules_src=True):
        ert = self.tool.get_result()
        self.assert_is_not_none(ert)
        # check executed transfer
        self.assert_equal(ert.planned_transfer, self.planned_rack_transfer)
        self.assert_equal(ert.source_rack.barcode, self.source_rack_barcode)
        self.assert_equal(ert.target_rack.barcode, self.target_rack_barcode)
        self.assert_equal(ert.user, self.executor_user)
        self.assert_is_not_none(ert.timestamp)
        # check source rack
        for container in self.source_rack.containers:
            pos_label = container.location.position.label
            if not self.source_data.has_key(pos_label): continue
            sample = container.sample
            # source volume, source conc, source final volume
            src_data = self.source_data[pos_label]
            expected_volume = src_data[2]
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_almost_equal(sample_volume, expected_volume)
            if check_sample_molecules_src:
                self.assert_equal(len(sample.sample_molecules), 1)
                sm = sample.sample_molecules[0]
                self.assert_equal(sm.molecule.molecule_design,
                                  self.molecule_design_source)
                expected_conc = src_data[1]
                sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                self.assert_almost_equal(sm_conc, expected_conc)
        # check target rack
        self.assert_equal(self.target_rack.status.name,
                          ITEM_STATUS_NAMES.MANAGED)
        if isinstance(self.target_rack, Plate):
            expected_empty_status = ITEM_STATUS_NAMES.MANAGED
        else:
            expected_empty_status = ITEM_STATUS_NAMES.FUTURE
        for container in self.target_rack.containers:
            pos_label = container.location.position.label
            sample = container.sample
            if not self.target_data.has_key(pos_label):
                self.assert_is_none(sample)
                self.assert_equal(container.status.name, expected_empty_status)
                continue
            # target vol (start), target conc (start), target final vol,
            # source final conc, target final conc, source well label
            # number of sample molecules
            if not container.status.name == ITEM_STATUS_NAMES.MANAGED:
                raise ValueError(pos_label)

            self.assert_equal(container.status.name, ITEM_STATUS_NAMES.MANAGED)
            trg_data = self.target_data[pos_label]
            expected_volume = trg_data[2]
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(sample_volume, expected_volume)
            number_sm = trg_data[6]
            self.assert_equal(len(sample.sample_molecules), number_sm)
            for sm in sample.sample_molecules:
                sample_concentration = sm.concentration \
                                       * CONCENTRATION_CONVERSION_FACTOR
                md = sm.molecule.molecule_design
                if md == self.molecule_design_target:
                    expected_conc = trg_data[4]
                else:
                    expected_conc = trg_data[3]
                self.assert_almost_equal(sample_concentration, expected_conc)

    def test_result_small_to_large_plate(self):
        self.use_plates = True
        self._continue_setup()
        self.__check_result()

    def test_result_small_to_large_tube_rack(self):
        self._continue_setup()
        self.__check_result()

    def test_result_one_to_one_plate(self):
        self.use_plates = True
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(A1=(10, 120, 20, 60, 60, 'A1', 2),
                                A2=(30, 120, 40, 30, 90, 'A2', 2),
                                B1=(10, 120, 20, 120, 60, 'B1', 2),
                                B2=(30, 120, 40, 60, 90, 'B2', 2))
        self.rack_shape_trg = self.rack_shape_src
        # one to one requires one sector
        self.sector_number = 1
        self._continue_setup()
        self.__check_result()

    def test_result_one_to_one_tube_rack(self):
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(A1=(10, 120, 20, 60, 60, 'A1', 2),
                                A2=(30, 120, 40, 30, 90, 'A2', 2),
                                B1=(10, 120, 20, 120, 60, 'B1', 2),
                                B2=(30, 120, 40, 60, 90, 'B2', 2))
        self.rack_shape_trg = self.rack_shape_src
        # one to one requires one sector
        self.sector_number = 1
        self._continue_setup()
        self.__check_result()

    def test_result_large_to_small_plate(self):
        self.use_plates = True
        self.source_sector_index = 3
        self.target_sector_index = 0
        self.rack_shape_src = get_384_rack_shape()
        self.rack_shape_trg = get_96_rack_shape()
        # source volume, source conc, source final volume
        self.source_data = dict(B2=(40, 120, 30),
                                B4=(35, 120, 25),
                                D2=(40, 240, 30),
                                D4=(35, 240, 25))
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(A1=(10, 120, 20, 60, 60, 'B2', 2),
                                A2=(30, 120, 40, 30, 90, 'B4', 2),
                                B1=(10, 120, 20, 120, 60, 'D2', 2),
                                B2=(30, 120, 40, 60, 90, 'D4', 2))
        self._continue_setup()
        self.__check_result()

    def test_result_large_to_small_tube_rack(self):
        self.source_sector_index = 3
        self.target_sector_index = 0
        self.rack_shape_src = get_384_rack_shape()
        self.rack_shape_trg = get_96_rack_shape()
        # source volume, source conc, source final volume
        self.source_data = dict(B2=(40, 120, 30),
                                B4=(35, 120, 25),
                                D2=(40, 240, 30),
                                D4=(35, 240, 25))
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(A1=(10, 120, 20, 60, 60, 'B2', 2),
                                A2=(30, 120, 40, 30, 90, 'B4', 2),
                                B1=(10, 120, 20, 120, 60, 'D2', 2),
                                B2=(30, 120, 40, 60, 90, 'D4', 2))
        self._continue_setup()
        self.__check_result()

    def test_result_non_zero_sectors(self):
        self.source_sector_index = 1
        self.target_sector_index = 3
        self.rack_shape_trg = self.rack_shape_src
        # source volume, source conc, source final volume
        self.source_data = dict(A2=(40, 120, 30),
                                A4=(35, 120, 25),
                                C2=(40, 240, 30),
                                C4=(35, 240, 25))
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(B2=(10, 120, 20, 60, 60, 'A2', 2),
                                B4=(30, 120, 40, 30, 90, 'A4', 2),
                                D2=(10, 120, 20, 120, 60, 'C2', 2),
                                D4=(30, 120, 40, 60, 90, 'C4', 2))
        self._continue_setup()
        self.__check_result()

    def test_no_sample_molecules_source(self):
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(B2=(10, 120, 20, 0, 60, 'A1', 1),
                                B4=(30, 120, 40, 0, 90, 'A2', 1),
                                D2=(10, 120, 20, 0, 60, 'B1', 1),
                                D4=(30, 120, 40, 0, 90, 'B2', 1))
        self._continue_setup(create_sample_molecules_src=False)
        self.__check_result(check_sample_molecules_src=False)

    def test_no_sample_molecules_target(self):
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data = dict(B2=(10, 120, 20, 60, 0, 'A1', 1),
                                B4=(30, 120, 40, 30, 0, 'A2', 1),
                                D2=(10, 120, 20, 120, 0, 'B1', 1),
                                D4=(30, 120, 40, 60, 0, 'B2', 1))
        self._continue_setup(create_sample_molecules_trg=False)
        self.__check_result()

    def test_pipetting_specs(self):
        self.transfer_volume = 1 / VOLUME_CONVERSION_FACTOR
        self.pipetting_specs = get_pipetting_specs_biomek()
        self._continue_setup()
        self._test_and_expect_errors('Some transfer volumes are smaller than ' \
                         'the allowed minimum transfer volume of 2 ul: 1.0 ul')

    def test_invalid_input_users(self):
        self._continue_setup()
        self._test_invalid_user()
        self._test_invalid_target_rack()
        self._test_invalid_pipetting_specs()
        a1_pos = get_rack_position_from_label('A1')
        self.planned_rack_transfer = PlannedContainerTransfer(
                        volume=0.000050, source_position=a1_pos,
                        target_position=a1_pos)
        self._test_and_expect_errors('The planned rack transfer must be a ' \
                                     'PlannedRackTransfer object')

    def test_translator_init_failure(self):
        self.sector_number = 3
        self.source_sector_index = 1
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to initialise rack ' \
                                     'sector translator')

    def test_rack_shape_mismatch(self):
        self.sector_number = 1
        self.target_sector_index = 0
        self.source_sector_index = 0
        self._continue_setup()
        self._test_and_expect_errors('The shapes of the rack sectors do not ' \
                                     'match the planned rack transfer')

    def test_invalid_source_sector(self):
        self.source_sector_index = 3
        self.target_sector_index = 0
        self._continue_setup()
        self._test_and_expect_errors('The source sector index for many to ' \
                                     'one translations must be 0')

    def test_invalid_target_sector(self):
        self.rack_shape_src = get_384_rack_shape()
        self.rack_shape_trg = get_96_rack_shape()
        self._continue_setup()
        self._test_and_expect_errors('The target sector index for one to ' \
                                     'many translations must be 0')

    def test_invalid_source_position(self):
        self.target_sector_index = 0
        self.source_sector_index = 3
        self.rack_shape_src = get_384_rack_shape()
        self.rack_shape_trg = get_96_rack_shape()
        # source volume, source conc, source final volume
        self.source_data = dict(B1=(40, 120, 30),
                                B4=(35, 120, 25),
                                D2=(40, 240, 30),
                                D4=(35, 240, 25))
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to find target ' \
                                     'position for rack position')

    def test_missing_target_container(self):
        positions = ['A2', 'B2']
        self.shape = self.rack_shape_trg
        self._test_missing_target_container(positions)

    def test_target_volume_too_large(self):
        self.container_max_volume = 0.000100 # 100 ul
        # target vol (start), target conc (start), target final vol,
        # source final conc, target final conc, source well label,
        # number of sample molecules
        self.target_data['B2'] = (95, 120, 110, 0, 0, 'A1', 2)
        self._continue_setup()
        self._test_and_expect_errors('Some target container cannot take up ' \
                                     'the transfer volume')

    def test_source_volume_too_small(self):
        self.container_dead_volume = 0.000050 # 50 ul
        self._continue_setup()
        self._test_and_expect_errors()

    def test_equal_plates(self):
        self._continue_setup()
        self.target_rack = self.source_rack
        self._create_tool()
        ert = self.tool.get_result()
        self.assert_is_not_none(ert)
