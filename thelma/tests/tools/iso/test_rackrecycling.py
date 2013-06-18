"""
Tests for tools that allow recycling of stock racks for tube picking.

AAB
"""
from thelma.automation.tools.iso.rackrecycling import IsoControlRackRecycler
from thelma.automation.tools.semiconstants \
    import get_384_rack_shape
from thelma.automation.tools.semiconstants \
    import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.semiconstants\
     import get_experiment_type_robot_optimisation
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IOrganization
from thelma.models.container import ContainerLocation
from thelma.models.container import TubeSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.tests.tools.iso.test_tubehandler import IsoJobTubeHandlerTestCase


class IsoControlRackRecyclerTestCase(IsoJobTubeHandlerTestCase):

    def set_up(self):
        IsoJobTubeHandlerTestCase.set_up(self)
        self.stock_rack = None
        self.stock_rack_barcode = '09999999'
        # transfer volume 1.2 ul, take out volume 7.2 ul
        self.start_volume = 20 / VOLUME_CONVERSION_FACTOR

    def tear_down(self):
        IsoJobTubeHandlerTestCase.tear_down(self)
        del self.stock_rack
        del self.stock_rack_barcode
        del self.start_volume

    def _create_tool(self):
        self.tool = IsoControlRackRecycler(iso_job=self.iso_job,
                                           stock_rack=self.stock_rack)

    def _continue_setup(self): #pylint: disable=W0221
        IsoJobTubeHandlerTestCase._continue_setup(self)
        self.__create_stock_rack()
        self._create_tool()

    def __create_stock_rack(self):
        status = get_item_status_managed()
        supplier = self._get_entity(IOrganization)
        stock_conc = 50000 / CONCENTRATION_CONVERSION_FACTOR
        self.stock_rack = self.tube_rack_specs.create_rack(label='stock rack',
                                                           status=status)
        self.stock_rack.barcode = self.stock_rack_barcode
        tube_specs = TubeSpecs(label='test_specs',
                               max_volume=1500 * VOLUME_CONVERSION_FACTOR,
                               dead_volume=5 * VOLUME_CONVERSION_FACTOR,
                               tube_rack_specs=[self.tube_rack_specs])
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            barcode = '00%s' % (pos_label)
            tube = tube_specs.create_tube(item_status=status, barcode=barcode,
                                          location=None)
            ContainerLocation(container=tube, rack=self.stock_rack,
                              position=rack_pos)
            self.stock_rack.containers.append(tube)
            sample = Sample(self.start_volume, tube)
            pool_id = pos_data[0]
            md_pool = self._get_entity(IMoleculeDesignPool, str(pool_id))
            for md in md_pool.molecule_designs:
                mol = Molecule(molecule_design=md, supplier=supplier)
            sample.make_sample_molecule(mol, stock_conc)

    def test_result(self):
        self._continue_setup()
        iso_job = self.tool.get_result()
        self.assert_is_not_none(iso_job)
        icsr = self.iso_job.iso_control_stock_rack
        self.assert_is_not_none(icsr)
        self.assert_equal(icsr.rack.barcode, self.stock_rack_barcode)
        self.assert_is_not_none(icsr.planned_worklist)

    def test_invalid_iso_job(self):
        self._test_invalid_iso_job('ISO job')

    def test_invalid_stock_rack(self):
        self._continue_setup()
        self.stock_rack = None
        self._test_and_expect_errors('The stock rack must be a TubeRack object')

    def test_invalid_scenario(self):
        self._continue_setup()
        self.experiment_metadata.experiment_metadata_type = \
                                        get_experiment_type_robot_optimisation()
        self._test_and_expect_errors('Control stock racks are only available ' \
                'for screening cases with a 16x24-well format! This is a ' \
                'optimisation with robot-support scenario (16x24-well format)')
        self.experiment_metadata.experiment_metadata_type = \
                                        get_experiment_type_screening()
        self.iso_request.iso_layout.shape = get_96_rack_shape()
        self._test_and_expect_errors('Control stock racks are only available ' \
                'for screening cases with a 16x24-well format! This is a ' \
                'screening scenario (8x12-well format)')

    def test_finder_failure(self):
        self._continue_setup()
        for iso in self.iso_job.isos:
            iso.rack_layout = RackLayout(shape=get_384_rack_shape())
            break
        self._test_and_expect_errors('Error when trying to find layout for ' \
                                     'ISO control rack.')

    def test_no_verification(self):
        self._continue_setup()
        for tube in self.stock_rack.containers:
            tube.sample = None
            break
        self._test_and_expect_errors('The stock rack is not compatible with ' \
                                     'the ISO job!')

    def test_not_enough_volume(self):
        self.start_volume = 10 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Some tubes do not contain enough volume')
