"""
Tools for TubeHandler support.

The tools here are supposed to replace the old Celma (tube handler) worklist
generator. They produce tube handler worklists and report for an IS
or ISO job (as return value). In addition, they provide the referring
rack entities that can be requested after a successful run.

The output file of the tube handler will still be taken over by the old Celma.

AAB, Jan 2012
"""
from StringIO import StringIO
from datetime import datetime
from everest.entities.utils import get_root_aggregate
from everest.repositories.rdb import Session
from sqlalchemy.orm.exc import NoResultFound
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.dummies import XL20Dummy
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayout
from thelma.automation.tools.iso.prep_utils import IsoControlRackPosition
from thelma.automation.tools.iso.prep_utils import PrepIsoAssociationData
from thelma.automation.tools.iso.prep_utils import PrepIsoLayoutConverter
from thelma.automation.tools.iso.prep_utils import RequestedStockSample
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Controls
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Samples
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Single
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator96
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_384
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import PLATE_SPECS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.semiconstants import get_reservoir_specs_deep_96
from thelma.automation.tools.stock.base import RackLocationQuery
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.base import STOCK_ITEM_STATUS
from thelma.automation.tools.stock.base import get_stock_tube_specs_db_term
from thelma.automation.tools.utils.base import EmptyPositionManager
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.racksector import QuadrantIterator
from thelma.automation.tools.utils.racksector import RackSectorTranslator
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.tubehandler \
    import BaseXL20WorklistWriter
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.tools.writers import create_zip_archive
from thelma.interfaces import ITubeRack
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoControlStockRack
from thelma.models.iso import IsoSampleStockRack
from thelma.models.job import IsoJob
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['IsoXL20WorklistGenerator',
           'IsoXL20WorklistGenerator96',
           'IsoXL20WorklistGenerator384Samples',
           'IsoXL20WorklistGenerator384Controls',
           'TubeCandidate',
           'IsoXL20WorklistWriter',
           'IsoXL20ReportWriter',
           'IsoControlLayoutFinder']


class IsoXL20WorklistGenerator(BaseAutomationTool):
    """
    This tool generates worklists for the tube handler. At this it will also
    conduct checks on DB level. Furthermore, it produces a report that serves
    as work sheet for the stock management.

    The referring rack entities (IsoControlStockRack or IsoSampleStockRacks) are
    created too, but not added to the return value. They can be retrieved using
    the :func:`get_racks` method.

    **Return Value:** A zip archive with two files (worklist and report); if
    the :param:`include_dummy_output` flag is set, a third file containing
    the output from the XL20 dummy writer is added.
    """

    #: The suffix for the file name of the XL20 worklist file. The first
    #: part of the file name will be the ISO label.
    WORKLIST_FILE_SUFFIX = '%s_XL20_worklist.csv'
    #: The suffix for the file name of the XL20 report file. The first
    #: part of the file name will be the ISO label.
    REPORT_FILE_SUFFIX = '%s_XL20_generation_report.txt'
    #: The suffix for the file name of the XL20 dummy output writer.
    DUMMY_OUTPUT_FILE_SUFFIX = '%s_XL20_dummy_output.txt'

    #: The name of the supported rack shape.
    RACK_SHAPE_NAME = None
    #: Are the files created for an ISO job (*True*) or for a single ISO
    #: (*False*)?
    FOR_JOB = None

    def __init__(self, entity, destination_rack_barcode_map,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param entity: The ISO or the ISO job for which to generate the files
            and the racks.

        :param destination_rack_barcode_map: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcode_map: map of barcodes
            (:class:`basestring`) mapped onto sector indices.

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param include_dummy_output: Flag indicating if the
            `thelma.tools.dummies.XL20Dummy` output writer should be run
            at the end of the worklist generation. The resulting output file
            is then included in the zip file.
        :type include_dummy_output: :class:`bool`
        :default include_dummy_output: *False*

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                 add_default_handlers=add_default_handlers,
                                 depending=False)

        #: The ISO or the ISO job for which to generate the files and the racks.
        self.entity = entity
        #: The barcodes of the racks the tubes shall be transferred to.
        self.destination_rack_map = destination_rack_barcode_map

        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks
        if excluded_racks is None: self.excluded_racks = []
        #: A list of barcodes from stock tubes that are supposed to be used.
        self.requested_tubes = requested_tubes
        if requested_tubes is None: self.requested_tubes = []
        #: Flag indicating if the file from the dummy output writer should be
        #: included in the output zip file.
        self.include_dummy_output = include_dummy_output

        #: The type of the experiment metadata the ISO request belongs to.
        self._experiment_type_id = None
        #: The label used for the file names.
        self._label = None
        #: The preparation plate layout containing the position information/
        self._prep_layout = None

        #: The stock samples for which to pick tubes.
        self._requested_stock_samples = None
        #: The requested stock samples (incl. tube candidates selected by the
        #: stock tube picker) mapped onto rack sectors.
        self._sector_stock_samples = None

        #: The stream for the tube handler worklist.
        self.__worklist_stream = None
        #: The stream for the report file.
        self.__report_stream = None
        #: The (optional) stream for the dummy writer output file.
        self.__dummy_output_stream = None
        #: The zip stream wrapped around the two files.
        self.__zip_stream = None

        #: The aggreate to find the tube rack for the given barcode.
        self.__tube_rack_agg = None
        #: Maps tube racks onto barcodes (required for stock racks).
        self._barcode_map = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._label = None
        self._experiment_type_id = None
        self._prep_layout = None
        self._requested_stock_samples = []
        self._sector_stock_samples = dict()
        self.__worklist_stream = None
        self.__report_stream = None
        self.__dummy_output_stream = None
        self.__zip_stream = None
        self.__tube_rack_agg = get_root_aggregate(ITubeRack)
        self._barcode_map = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start zip content generation ...')

        self._check_input()
        if not self.has_errors() and not self.FOR_JOB:
            aliquot_plates = self.entity.iso_aliquot_plates
        if not self.has_errors(): self.__get_tube_racks()
        if not self.has_errors(): self._get_metadata()
        if not self.has_errors(): self._create_requested_stock_samples()
        if not self.has_errors(): self.__pick_tubes()
        if not self.has_errors(): self._sort_by_sector()
        if not self.has_errors(): self._create_transfer_worklists()
        if not self.has_errors(): self.__write_streams()
        if not self.has_errors() and not self.FOR_JOB and \
                    not self._experiment_type_id == EXPERIMENT_SCENARIOS.MANUAL:
            if len(aliquot_plates) == 0: self.__create_aliquot_plates()
        if not self.has_errors(): self._create_stock_racks()
        if not self.has_errors() and self.include_dummy_output:
            self.__run_output_writer()
        if not self.has_errors():
            self.__create_zip_archive()
            self.return_value = self.__zip_stream
            self.add_info('File generation completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        entity_cls = Iso
        if self.FOR_JOB: entity_cls = IsoJob
        self._check_input_class('entity', self.entity, entity_cls)

        if self._check_input_class('destination rack barcode map',
                                   self.destination_rack_map, dict):
            for sector_index, barcode in self.destination_rack_map.iteritems():
                if not self._check_input_class('sector index', sector_index,
                                               int): break
                if not self._check_input_class('rack barcode', barcode,
                                               basestring): break
            if not len(self.destination_rack_map) > 0:
                msg = 'There are no barcodes in the destination rack map!'
                self.add_error(msg)

        if self._check_input_class('excluded racks list',
                                       self.excluded_racks, list):
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break

        if self._check_input_class('requested tubes list',
                                       self.requested_tubes, list):
            for req_tube in self.requested_tubes:
                if not self._check_input_class('requested tube barcode',
                                               req_tube, basestring): break

    def __get_tube_racks(self):
        """
        Fetches the tube racks for the stock rack entities from the DB.
        """
        self.add_debug('Fetch stock racks ...')

        non_empty = []

        for barcode in self.destination_rack_map.values():
            if len(barcode) < 1: continue
            rack = self.__tube_rack_agg.get_by_slug(barcode)
            if rack is None:
                msg = 'Rack %s has not been found in the DB!' % (barcode)
                self.add_error(msg)
            elif len(rack.containers) > 0:
                non_empty.append(barcode)
            else:
                self._barcode_map[barcode] = rack

        if len(non_empty) > 0:
            non_empty.sort()
            msg = 'The following racks you have chosen are not empty: %s.' \
                  % (', '.join(non_empty))
            self.add_error(msg)

    def _get_metadata(self):
        """
        Sets the metadata required for the file creation (e.g. stock
        concentration of the molecule type, preparation layout,
        labels for the file names).
        """
        self.add_error('Abstract method: _get_metadata()')

    def _get_preparation_layout(self, rack_layout):
        """
        Obtains the preparation layout containing the position data.
        """
        if rack_layout is None:
            msg = 'Could not find preparation layout!'
            self.add_error(msg)
            return None
        elif not self.__check_rack_shape(rack_layout):
            return None

        converter = PrepIsoLayoutConverter(rack_layout=rack_layout,
                                           log=self.log)
        prep_layout = converter.get_result()
        if prep_layout is None:
            msg = 'Error when trying to convert preparation layout!'
            self.add_error(msg)

        return prep_layout

    def __check_rack_shape(self, rack_layout):
        """
        Checks the compatibility of the preparation layout rack shape.
        """
        self.add_debug('Check preparation layout rack shape ...')

        if not rack_layout.shape.name == self.RACK_SHAPE_NAME:
            msg = 'Unsupported rack shape "%s".' \
                   % (rack_layout.shape.name)
            self.add_error(msg)
            return False

        return True

    def _create_requested_stock_samples(self):
        """
        Creates a list of requested stock samples (molecule design pools for
        which  to pick stock tubes).
        """
        self.add_error('Abstract method: _create_requested_stock_samples()')

    def __pick_tubes(self):
        """
        Picks the tubes for the requested stock samples.
        """
        self.add_debug('Pick tubes ...')

        picker = StockTubePicker(log=self.log,
                         requested_stock_samples=self._requested_stock_samples,
                         excluded_racks=self.excluded_racks,
                         requested_tubes=self.requested_tubes)
        self._requested_stock_samples = picker.get_result()

        if self._requested_stock_samples is None:
            msg = 'Error when trying to pick tubes for molecule design pools.'
            self.add_error(msg)
        else:
            missing_pools = picker.get_missing_molecule_design_pools()
            if len(missing_pools) > 0:
                self._process_missing_molecule_design_pools(missing_pools)

    def _process_missing_molecule_design_pools(self, missing_pools): #pylint: disable=W0613
        """
        Deals with molecule design pools for which there was no tube picked.
        """
        self.add_error('Abstract method: ' \
                       '_process_missing_molecule_design_pools()')

    def _sort_by_sector(self):
        """
        Creates the :attr:`_sector_stock_samples` map (tube candidates for each
        sector).
        """
        self.add_error('Abstract method: _sort_by_sector()')

    def __write_streams(self):
        """
        Writes the streams for two files (worklist and report).
        """
        self.add_debug('Write files ...')

        worklist_writer = IsoXL20WorklistWriter(log=self.log,
                        sector_stock_samples=self._sector_stock_samples,
                        destination_rack_barcode_map=self.destination_rack_map)
        self.__worklist_stream = worklist_writer.get_result()

        if self.__worklist_stream is None:
            msg = 'Error when trying to write XL20 worklist!'
            self.add_error(msg)

        used_destination_racks = dict()
        for si in self._sector_stock_samples.keys():
            used_destination_racks[si] = self.destination_rack_map[si]

        report_writer = IsoXL20ReportWriter(label=self._label,
                    rack_shape_name=self.RACK_SHAPE_NAME,
                    sector_stock_samples=self._sector_stock_samples,
                    destination_rack_barcode_map=used_destination_racks,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes,
                    is_job=self.FOR_JOB, log=self.log)
        self.__report_stream = report_writer.get_result()

        if self.__report_stream is None:
            msg = 'Error when trying to write generation report!'
            self.add_error(msg)

    def _create_transfer_worklists(self):
        """
        Creates the planned worklists for the transfer from stock rack to
        preparation plate.
        """
        self.add_error('Abstract method: _create_transfer_worklists()')

    def _create_stock_racks(self):
        """
        Creates the stock rack entities for the ISO or ISO job.
        """
        self.add_error('Abstract method: _create_stock_racks()')

    def __create_aliquot_plates(self):
        """
        Creates the aliquot plates if the entity is an ISO.
        """
        # Find maximum mastermix volume
        if self.RACK_SHAPE_NAME == RACK_SHAPE_NAMES.SHAPE_384:
            aliquot_rs = get_reservoir_specs_standard_384()
        else:
            odf_map = self.__determine_optimem_dilution_factors()
            aliquot_rs = get_reservoir_specs_standard_96()
            max_mm_volume = 0
            for prep_pos in self._prep_layout.working_positions():
                optimem_df = odf_map[prep_pos.molecule_design_pool]
                for tt in prep_pos.transfer_targets:
                    volume = tt.transfer_volume * optimem_df \
                          * TransfectionParameters.REAGENT_MM_DILUTION_FACTOR
                    max_mm_volume = max(volume, max_mm_volume)
            max_rs_vol = aliquot_rs.max_volume * VOLUME_CONVERSION_FACTOR
            if max_mm_volume > max_rs_vol:
                aliquot_rs = get_reservoir_specs_deep_96()

        # Create aliquot plates
        aliquot_plate_specs = PLATE_SPECS_NAMES.from_reservoir_specs(aliquot_rs)
        for i in range(self.entity.iso_request.number_aliquots):
            label = 'a%i_%s' % ((i + 1), self.entity.label)
            aliquot_plate = aliquot_plate_specs.create_rack(label=label,
                                        status=get_item_status_future())
            IsoAliquotPlate(iso=self.entity, plate=aliquot_plate)

    def __determine_optimem_dilution_factors(self):
        """
        The ODF is required to determine the maximum volume in a 96-well
        plate (and thus whether deep well usage is required)  - library
        scenarios, that might have differing ODFs do not get here, because
        they always use 384-well plates.
        """
        odf_map = dict()
        for prep_pos in self._prep_layout.working_positions():
            if prep_pos.is_mock: continue
            pool = prep_pos.molecule_design_pool
            if odf_map.has_key(pool): continue
            odf = TransfectionParameters.get_optimem_dilution_factor(
                                                        pool.molecule_type)
            odf_map[pool] = odf

        odfs = set(odf_map.values())
        if len(odfs) == 1:
            odf_map[MOCK_POSITION_TYPE] = odf_map.values()[0]
        else:
            mock_mt = TransfectionParameters.DEFAULT_MOLECULE_TYPE
            mock_odf = TransfectionParameters.get_optimem_dilution_factor(
                                                                    mock_mt)
            odf_map[MOCK_POSITION_TYPE] = mock_odf

        return odf_map

    def __run_output_writer(self):
        """
        Runs the dummy output writer and sets the dummy output stream to its
        return value.
        """
        dummy_writer = XL20Dummy(self.__worklist_stream)
        dummy_writer.run()
        # Reset worklist stream.
        self.__worklist_stream.seek(0)
        self.__dummy_output_stream = dummy_writer.return_value

    def __create_zip_archive(self):
        """
        Creates and fills the zip archive (adds files).
        """
        self.add_info('Writes files into zip stream ...')

        self.__zip_stream = StringIO()
        zip_map = dict()

        wl_fn = self.WORKLIST_FILE_SUFFIX % (self._label)
        zip_map[wl_fn] = self.__worklist_stream
        report_fn = self.REPORT_FILE_SUFFIX % (self._label)
        zip_map[report_fn] = self.__report_stream
        if self.include_dummy_output:
            dummy_output_fn = self.DUMMY_OUTPUT_FILE_SUFFIX % self._label
            zip_map[dummy_output_fn] = self.__dummy_output_stream
        create_zip_archive(zip_stream=self.__zip_stream, stream_map=zip_map)


class IsoXL20WorklistGenerator96(IsoXL20WorklistGenerator):
    """
    This is a IsoXL20WorklistGenerator for 96-well preparation layouts.

    **Return Value:** A zip archive with two files (worklist and report)
    """

    NAME = 'XL20 96-well Worklist Generator'

    RACK_SHAPE_NAME = RACK_SHAPE_NAMES.SHAPE_96
    FOR_JOB = False


    def __init__(self, iso, destination_rack_barcode,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO for which to generate the files.
        :type iso: :class:`thelma.models.iso.Iso`

        :param destination_rack_barcode: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcodep: The barcode of the destination rack.

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param include_dummy_output: Flag indicating if the
            `thelma.tools.dummies.XL20Dummy` output writer should be run
            at the end of the worklist generation. The resulting output file
            is then included in the zip file.
        :type include_dummy_output: :class:`bool`
        :default include_dummy_output: *False*

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """

        barcode_map = {0 : destination_rack_barcode}
        IsoXL20WorklistGenerator.__init__(self, entity=iso,
                    destination_rack_barcode_map=barcode_map,
                    excluded_racks=excluded_racks,
                    requested_tubes=requested_tubes,
                    include_dummy_output=include_dummy_output,
                    logging_level=logging_level,
                    add_default_handlers=add_default_handlers)

        #: The planned worklist for the sample stock rack.
        self.__planned_worklist = None

    def _get_metadata(self):
        """
        Sets the metadata required for the file creation (e.g. stock
        concentration of the molecule type, preparation layout,
        labels for the file names).
        """
        self.add_debug('Set metadata ...')

        self._label = self.entity.label

        iso_request = self.entity.iso_request
        self._prep_layout = self._get_preparation_layout(
                                                        self.entity.rack_layout)
        self._experiment_type_id = iso_request.experiment_metadata.\
                                   experiment_metadata_type.id

    def _create_requested_stock_samples(self):
        """
        Creates a list of requested stock samples (molecule design pools for
        which to pick stock tubes).
        """
        self.add_debug('Collect requested molecules ...')

        starting_wells = self._prep_layout.get_starting_wells()
        for prep_pos in starting_wells.values():
            if prep_pos.is_mock: continue
            rss = RequestedStockSample.from_prep_pos(prep_pos)
            self._requested_stock_samples.append(rss)

    def _process_missing_molecule_design_pools(self, missing_pools):
        """
        Deals with molecule design pools for which there was no tube picked.
        Since we cannot distinguish between floating and fixed designs.
        """
        self.add_debug('Process molecule design pools without tubes ...')

        missing_pools = set(missing_pools)
        sample_pools = set()
        control_pools = set()
        for prep_pos in self._prep_layout.working_positions():
            pool_id = prep_pos.molecule_design_pool_id
            if pool_id in missing_pools:
                if prep_pos.is_floating:
                    prep_pos.inactivate()
                    sample_pools.add(pool_id)
                else:
                    control_pools.add(pool_id)

        if len(control_pools) > 0:
            controls = list(control_pools)
            controls.sort()
            msg = 'For some control molecule design pools there are no valid ' \
                  'stock tubes available: %s.' % (controls)
            self.add_error(msg)
        else:
            for pool_id in sample_pools:
                self.entity.molecule_design_pool_set.remove_pool(pool_id)

            samples = list(sample_pools)
            samples.sort()
            msg = 'The following molecule design pools are put back into the ' \
                  'queue: %s.' % (samples)
            self.add_warning(msg)
            self.entity.rack_layout = self._prep_layout.create_rack_layout()

    def _sort_by_sector(self):
        """
        Creates the :attr:`_sector_stock_samples` map (requested stock samples
        for each sector).
        """
        self._sector_stock_samples[0] = self._requested_stock_samples

    def _create_transfer_worklists(self):
        """
        Creates the planned worklists for the transfer from stock rack to
        preparation plate.
        """
        self.add_debug('Generate stock taking worklist ...')

        generator = StockTransferWorklistGenerator96(
                            working_layout=self._prep_layout,
                            label=self.entity.label, log=self.log)
        self.__planned_worklist = generator.get_result()
        if self.__planned_worklist is None:
            msg = 'Error when trying to generate stock taking worklist.'
            self.add_error(msg)

    def _create_stock_racks(self):
        """
        Creates the stock rack entities for the ISO.
        """
        self.add_debug('Create stock rack ...')

        barcode = self.destination_rack_map[0]
        if len(self.entity.iso_sample_stock_racks) > 0 and \
                self.entity.iso_sample_stock_racks[0].rack.barcode == barcode:
            return

        self.entity.iso_sample_stock_racks = []
        rack = self._barcode_map[barcode]
        IsoSampleStockRack(iso=self.entity, rack=rack, sector_index=0,
                           planned_worklist=self.__planned_worklist)


class IsoXL20WorklistGenerator384Samples(IsoXL20WorklistGenerator):
    """
    A XL20 worklist generator for the samples (floating positions) of a
    384-well plate. Samples or floating are here defined as molecule design
    pools that have *only one starting well* in the preparation layout.

    **Return Value:** A zip archive with two files (worklist and report)
    """

    NAME = 'XL20 Sample Worklist Generator'

    RACK_SHAPE_NAME = RACK_SHAPE_NAMES.SHAPE_384
    FOR_JOB = False

    def __init__(self, iso, destination_rack_barcode_map,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False,
                 enforce_cybio_compatibility=False,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO for which to generate the files.
        :type iso: :class:`thelma.models.iso.Iso`

        :param destination_rack_barcode_map: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcode_map: map of barcodes
            (:class:`basestring`) mapped onto sector indices.

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param include_dummy_output: Flag indicating if the
            `thelma.tools.dummies.XL20Dummy` output writer should be run
            at the end of the worklist generation. The resulting output file
            is then included in the zip file.
        :type include_dummy_output: :class:`bool`
        :default include_dummy_output: *False*

        :param enforce_cybio_compatibility: If *True* the samples will always be
            spread over the sample rack (according to the rack sectors)
            even if there are less than 96 samples.
        :type enforce_cybio_compatibility: :class:`bool`
        :default enforce_cybio_compatibility: *False*

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        IsoXL20WorklistGenerator.__init__(self, entity=iso,
                    destination_rack_barcode_map=destination_rack_barcode_map,
                    excluded_racks=excluded_racks,
                    requested_tubes=requested_tubes,
                    include_dummy_output=include_dummy_output,
                    logging_level=logging_level,
                    add_default_handlers=add_default_handlers)

        #: If *True* the samples will always be spread over the sample rack
        #: (according to the rack sectors) even if there are less than 96
        #: samples.
        self.enforce_cybio_compatibility = enforce_cybio_compatibility

        #: The rack sector association data for the preparation layout.
        self.__association_data = None

        #: If *True* the sample can be delivered by a single stock rack.
        self.__has_single_stock_rack = None

        #: The worklists for the transfer for the ISO sample stock racks
        #: (mapped onto source sectors).
        self.__planned_worklists = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoXL20WorklistGenerator.reset(self)
        self.__association_data = None
        self.__has_single_stock_rack = False
        self.__planned_worklists = dict()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoXL20WorklistGenerator._check_input(self)
        self._check_input_class('"enforce multiple racks" flag',
                                self.enforce_cybio_compatibility, bool)

    def _get_metadata(self):
        """
        Sets the metadata required for the file creation (e.g. stock
        concentration of the molecule type, preparation layout,
        labels for the file names).
        """
        self._label = self.entity.label
        self._prep_layout = self._get_preparation_layout(
                                                        self.entity.rack_layout)
        if not self._prep_layout is None and \
                            not self.entity.molecule_design_pool_set is None:
            for pool in self.entity.molecule_design_pool_set:
                stock_conc = pool.default_stock_concentration \
                             * CONCENTRATION_CONVERSION_FACTOR
                self._prep_layout.set_floating_stock_concentration(stock_conc)
                break

        self._experiment_type_id = self.entity.iso_request.experiment_metadata.\
                                    experiment_metadata_type.id

        if not self.has_errors() and \
                    self._experiment_type_id == EXPERIMENT_SCENARIOS.SCREENING:
            try:
                self.__association_data = PrepIsoAssociationData(
                            preparation_layout=self._prep_layout, log=self.log)
            except ValueError:
                msg = 'Error when trying to determine associations.'
                self.add_error(msg)

    def _create_requested_stock_samples(self):
        """
        Creates a list of requested stock samples (molecule design pools for
        which to pick stock tubes). In screening cases, only floatings designs
        are picked here.
        """
        self.add_debug('Create requested stock samples ...')

        pool_map = dict()
        starting_wells = self._prep_layout.get_starting_wells()
        for prep_pos in starting_wells.values():
            if prep_pos.is_mock: continue
            if self._experiment_type_id == EXPERIMENT_SCENARIOS.SCREENING and \
                            not prep_pos.is_floating: continue
            pool_id = prep_pos.molecule_design_pool_id
            pool_map[pool_id] = prep_pos # in optimisations and manual scenarios
            # each molecule design pool has only one starting position
            # if screening it can be more (1 floating + 0-n fixed)

        for pool_id, prep_pos in pool_map.iteritems():
            if prep_pos.is_mock: continue
            req_stock_sample = RequestedStockSample.from_prep_pos(prep_pos)
            self._requested_stock_samples.append(req_stock_sample)

        if len(self._requested_stock_samples) < 1:
            msg = 'Did not find any floating positions in this layout!'
            self.add_error(msg)

        elif self._experiment_type_id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            if len(self._requested_stock_samples) > 96:
                msg = 'Sorry, optimisation layouts with more than 96 ' \
                      'different molecule design pools are not supported yet ' \
                      '(number here: %i).' % (len(self._requested_stock_samples))
                self.add_error(msg)
            else:
                self.__has_single_stock_rack = True

        elif len(self._requested_stock_samples) < 96 and \
                                        not self.enforce_cybio_compatibility:
            msg = 'There is only %i molecule design pools in the stock rack. ' \
                  'The system will only prepare one stock rack. If you want ' \
                  'to to use multiple source re-run the generator with the ' \
                  '"enforce Cybio compatibility" option activated, please. ' \
                  'Do you want to proceed with only one source rack?' \
                  % (len(self._requested_stock_samples))
            self.add_warning(msg)
            self.__has_single_stock_rack = True

    def _process_missing_molecule_design_pools(self, missing_pools):
        """
        All pools here are floatings that are allowed to be missing. The
        referring layout positions are inactivated and the pool is removed
        fom the pool set.
        """
        self.add_debug('Process molecule design pools without tubes ...')

        missing_pools.sort()
        msg = 'The following molecule design pools are put back into the ' \
              'queue: %s.' % (missing_pools)
        self.add_warning(msg)

        for pool_id in missing_pools:
            self.entity.molecule_design_pool_set.remove_pool(pool_id)

        missing_pools = set(missing_pools)
        for prep_pos in self._prep_layout.working_positions():
            if prep_pos.molecule_design_pool_id in missing_pools:
                prep_pos.inactivate()

        self.entity.rack_layout = self._prep_layout.create_rack_layout()

    def _sort_by_sector(self):
        """
        Creates the :attr:`_sector_stock_samples` map (tube candidates for each
        sector).
        """
        self.add_debug('Sort requested molecules by sector ...')

        if self.__has_single_stock_rack:
            self._sector_stock_samples[0] = self._requested_stock_samples
        else:
            self.__sort_into_four_sectors()

    def __sort_into_four_sectors(self):
        """
        Sorts the requested molecules into four sectors (regardless of the
        association data).
        """

        reverse_translators = dict()
        for i in range(4):
            self._sector_stock_samples[i] = []
            translator = RackSectorTranslator(number_sectors=4,
                            source_sector_index=i,
                            target_sector_index=0,
                            enforce_type=RackSectorTranslator.ONE_TO_MANY)
            reverse_translators[i] = translator

        rack_pos_map = dict()
        for req_stock_sample in self._requested_stock_samples:
            rack_pos_map[req_stock_sample.target_position] = req_stock_sample

        quadrant_iter = QuadrantIterator(number_sectors=4)
        for quadrant_rps in quadrant_iter.get_all_quadrants(
                                            rack_shape=get_384_rack_shape()):
            for sector_index, rack_pos in quadrant_rps.iteritems():
                if not rack_pos_map.has_key(rack_pos): continue
                req_stock_sample = rack_pos_map[rack_pos]
                stock_rack_pos = reverse_translators[sector_index].translate(
                                                                    rack_pos)
                req_stock_sample.target_position = stock_rack_pos
                self._sector_stock_samples[sector_index].append(req_stock_sample)

        del_sectors = []
        for sector_index, req_stock_samples in \
                                        self._sector_stock_samples.iteritems():
            if len(req_stock_samples) < 1: del_sectors.append(sector_index)
        for sector_index in del_sectors:
            del self._sector_stock_samples[sector_index]

        if len(self._sector_stock_samples) == 1:
            msg = 'There is only one source rack because the target wells ' \
                  'for the stock transfer are all located in sector %i.' \
                  % (self._sector_stock_samples.keys()[0] + 1)
            self.add_warning(msg)

    def _create_transfer_worklists(self):
        """
        Creates the planned worklists for the transfer from stock rack to
        preparation plate.
        """
        self.add_debug('Create rack transfer worklists ...')

        msg = 'Error when trying to generate worklists for stock sample ' \
              'transfer.'

        if self.__has_single_stock_rack:
            generator = StockTransferWorklistGenerator384Single(
                    iso_label=self.entity.label, log=self.log,
                    requested_stock_samples=self._requested_stock_samples)
            worklist = generator.get_result()
            if worklist is None:
                self.add_error(msg)
            else:
                self.__planned_worklists[0] = worklist

        else:
            fl_stock_conc = self._prep_layout.floating_stock_concentration
            generator = StockTransferWorklistGenerator384Samples(
                        preparation_layout=self._prep_layout,
                        iso_label=self.entity.label,
                        sector_stock_samples=self._sector_stock_samples,
                        floating_stock_concentration=fl_stock_conc,
                        association_data=self.__association_data, log=self.log)
            self.__planned_worklists = generator.get_result()
            if self.__planned_worklists is None:
                self.add_error(msg)

    def _create_stock_racks(self):
        """
        Creates the stock rack entities for the ISO.
        """
        self.add_debug('Create stock racks ...')

        issrs = dict()
        for issr in self.entity.iso_sample_stock_racks:
            issrs[issr.rack.barcode] = issr

        new_issr = []
        for sector_index, worklist in self.__planned_worklists.iteritems():

            if not self.destination_rack_map.has_key(sector_index):
                msg = 'Please add a rack barcode for sector %i!' \
                      % (sector_index + 1)
                self.add_error(msg)
                continue
            barcode = self.destination_rack_map[sector_index]

            if issrs.has_key(barcode):
                issr = issrs[barcode]
                issr.sector_index = sector_index
                issr.planned_worklist = worklist
            else:
                rack = self._barcode_map[barcode]
                issr = IsoSampleStockRack(iso=self.entity, rack=rack,
                                sector_index=sector_index,
                                planned_worklist=worklist)
            new_issr.append(issr)

        self.entity.iso_sample_stock_racks = new_issr


class IsoXL20WorklistGenerator384Controls(IsoXL20WorklistGenerator):
    """
    This is a XL20 worklist generator for the controls of a 384-well
    screening ISO.

    The IsoControlStockRack entity is created too, but not added to the return
    value. It can be retrieved using of the :func:`get_control_racks` method.

    **Return Value:** A zip archive with two files (worklist and report)
    """
    NAME = 'XL20 Control Worklist Generator'

    RACK_SHAPE_NAME = RACK_SHAPE_NAMES.SHAPE_384
    FOR_JOB = True

    def __init__(self, iso_job, destination_rack_barcode,
                 excluded_racks=None, requested_tubes=None,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param iso_job: The ISO job for which to generate the files.
        :type iso_job: :class:`thelma.models.job.IsoJob`

        :param destination_rack_barcode: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcode: :class:`basestring`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        barcode_map = {0: destination_rack_barcode}
        IsoXL20WorklistGenerator.__init__(self, entity=iso_job,
                    destination_rack_barcode_map=barcode_map,
                    excluded_racks=excluded_racks,
                    requested_tubes=requested_tubes,
                    logging_level=logging_level,
                    add_default_handlers=add_default_handlers)

        #: The layout for the control plate (:class:`IsoControlRackLayout`)
        self.__control_layout = None
        #: The worklist for the transfer of sample from the stock tube to the
        #: prepartion plates.
        self.__planned_worklist = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        IsoXL20WorklistGenerator.reset(self)
        self.__control_layout = None
        self.__planned_worklist = None

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoXL20WorklistGenerator._check_input(self)
        if isinstance(self.entity, IsoJob):
            if len(self.entity.isos) < 1:
                msg = 'There are no ISOs in this ISO job!'
                self.add_error(msg)

    def _get_metadata(self):
        """
        Sets the metadata required for the file creation (e.g. stock
        concentration of the molecule type, preparation layout,
        labels for the file names).
        """
        self.add_debug('Set metadata ...')

        self._label = 'ISO job for %i' % (self.entity.iso_request.\
                                          experiment_metadata.ticket_number)

        em_type = self.entity.iso_request.experiment_metadata_type
        self._experiment_type_id = em_type.id
        if not self._experiment_type_id == EXPERIMENT_SCENARIOS.SCREENING:
            msg = 'You cannot create a control stock rack for %s scenarios! ' \
                  'Control stock racks are only available for %s cases!' \
                   % (em_type.display_name,
                      get_experiment_type_screening().display_name)
            self.add_error(msg)

    def _create_requested_stock_samples(self):
        """
        Creates a list of requested stock samples (molecule design pools for
        which to pick stock tubes).
        """
        self.add_debug('Create requested stock samples ...')

        finder = IsoControlLayoutFinder(iso_job=self.entity, log=self.log)
        self.__control_layout = finder.get_result()

        if self.__control_layout is None:
            msg = 'Error when trying to find control rack layout and ' \
                  'requested molecules.'
            self.add_error(msg)
        else:
            self._requested_stock_samples = finder.get_requested_stock_samples()

    def _process_missing_molecule_design_pools(self, missing_pools):
        """
        Deals with molecule design pools for which there was no tube picked.
        """
        missing_pools.sort()
        msg = 'For some control molecule design pools there are no valid ' \
              'stock tubes available: %s.' % (missing_pools)
        self.add_error(msg)

    def _sort_by_sector(self):
        """
        Creates the :attr:`_sector_stock_samples` map (requested stock samples
        for each sector).
        """
        self._sector_stock_samples[0] = self._requested_stock_samples

    def _create_transfer_worklists(self):
        """
        Creates the planned worklists for the transfer from stock rack to
        preparation plate.
        """
        generator = StockTransferWorklistGenerator384Controls(log=self.log,
                                        control_layout=self.__control_layout,
                                        job_label=self.entity.label)
        self.__planned_worklist = generator.get_result()

        if self.__planned_worklist is None:
            msg = 'Error when trying to generate control stock transfer ' \
                  'worklist.'
            self.add_error(msg)

    def _create_stock_racks(self):
        """
        Creates the stock rack entities for the ISO.
        """
        self.add_debug('Create stock rack ...')

        barcode = self.destination_rack_map[0]
        rack = self._barcode_map[barcode]
        icsr = self.entity.iso_control_stock_rack

        if icsr is None:
            IsoControlStockRack(iso_job=self.entity, rack=rack,
                        planned_worklist=self.__planned_worklist,
                        rack_layout=self.__control_layout.create_rack_layout())
        else:
            icsr.planned_worklist = self.__planned_worklist
            icsr.rack_layout = self.__control_layout.create_rack_layout()
            if not icsr.rack.barcode == barcode:
                icsr.rack = rack


class StockTubePicker(BaseAutomationTool):
    """
    Picks the stock tubes for the parent wells of a preparation layout.

    **Return Value:** The requested stock samples with the picked tubes attached
        to them.
    """

    NAME = 'Stock Tube Picker'

    def __init__(self, requested_stock_samples, log,
                 excluded_racks=None, requested_tubes=None):
        """
        Constructor:

        :param requested_stock_samples: The molecule design pools for
            which to pick tubes.
        :type requested_stock_samples: :class:`list` of
            :class:`RequestedStockSample` objects

        :param log: The log to record events.
        :type log: :class:`thelma.ThelmaLog`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The stock samples molecule design sets for which to pick tubes.
        self.requested_stock_samples = requested_stock_samples

        if excluded_racks is None: excluded_racks = []
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks

        if requested_tubes is None: requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = requested_tubes

        #: The molecule design pools of the requested tubes.
        self.requested_tube_map = None

        # The DB session used for the queries.
        self.__session = None

        #: The candidates for the tubes to be used (mapped on rack barcodes).
        self.__tube_candidates = None
        #: Molecule design pools without candidate.
        self.__missing_pools = None

        # Intermediate error storage.
        self.__no_tubes = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__session = None
        self.requested_tube_map = dict()
        self.__tube_candidates = dict()
        self.__missing_pools = []
        self.__no_tubes = []

    def get_missing_molecule_design_pools(self):
        """
        Returns a list of molecule design pools for which no suitable tubes
        have been found.
        """
        if self.return_value is None: return None
        return self.__missing_pools

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start tube picking ...')
        self.__check_input()
        if not self.has_errors():
            self.__initialize_session()
            self.__get_md_pools_for_requested_tubes()
        if not self.has_errors():
            self.__select_tubes()
        if not self.has_errors():
            self.__fetch_rack_locations()
        if not self.has_errors():
            self.return_value = self.requested_stock_samples
            self.add_info('Tube picking completed.')

    def __initialize_session(self):
        """
        Initializes a session for ORM operations.
        """
        self.__session = Session()

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input ...')

        if self._check_input_class('requested stock sample list',
                                   self.requested_stock_samples, list):
            for req_stock_sample in self.requested_stock_samples:
                if not self._check_input_class('requested stock sample',
                                    req_stock_sample, RequestedStockSample):
                    break

        if self._check_input_class('excluded racks list', self.excluded_racks,
                                   list):
            for rack_barcode in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                            rack_barcode, basestring):
                    break
        if not self.requested_tubes is None and \
                            self._check_input_class('requested tubes list',
                                                    self.requested_tubes, list):
            for tube_barcode in self.requested_tubes:
                if not self._check_input_class('requested tube barcode',
                                            tube_barcode, basestring):
                    break

    def __get_md_pools_for_requested_tubes(self):
        """
        Retrieves the molecule design pools for the requested tubes.
        """
        if len(self.requested_tubes) > len(self.requested_stock_samples):
            msg = 'There are more requested tubes (%i) than molecule design ' \
                  'pool IDs (%s)!' % (len(self.requested_tubes),
                                      len(self.requested_stock_samples))
            self.add_warning(msg)

        if len(self.requested_tubes) > 0: self.__generate_requested_tube_map()
        if not self.has_errors(): self.__check_scheduled_tube_replacement()

    def __generate_requested_tube_map(self):
        """
        Creates a map containing the molecule design pools for all
        requested tubes.
        """
        base_query = 'SELECT ss.molecule_design_set_id AS pool_id ' \
                     'FROM stock_sample ss, sample s, container_barcode cb ' \
                     'WHERE ss.sample_id = s.sample_id ' \
                     'AND s.container_id = cb.container_id ' \
                     'AND cb.barcode = \'%s\';'

        not_found = []
        pool_tube_map = dict()

        for req_tube in self.requested_tubes:
            query_statement = base_query % (req_tube)
            try:
                results = self.__session.query('pool_id').\
                                        from_statement(query_statement).all()
            except NoResultFound:
                not_found.append(req_tube)
                continue

            if len(results) < 1:
                not_found.append(req_tube)
                continue

            for record in results:
                pool_id = record[0]
                add_list_map_element(pool_tube_map, pool_id, req_tube)

        if len(not_found) > 0:
            msg = 'The following requested tubes could not be found in the ' \
                  'DB: %s.' % (not_found)
            self.add_error(msg)

        multiple_tubes = []
        for pool_id, tube_list in pool_tube_map.iteritems():
            if len(tube_list) > 1:
                info = 'MD pool: %s, tubes: %s' % (pool_id, ', '.join(tube_list))
                multiple_tubes.append(info)
            self.requested_tube_map[pool_id] = tube_list[0]

        if len(multiple_tubes) > 0:
            msg = 'You have requested multiple tubes for the same molecule ' \
                  'design pool ID! Details: %s.' % (multiple_tubes)
            self.add_warning(msg)

    def __check_scheduled_tube_replacement(self):
        """
        Checks whether there are scheduled tubes that have been replaced by
        requested ones.
        """
        replaced_tubes = []
        for req_stock_sample in self.requested_stock_samples:
            pool_id = req_stock_sample.pool.id
            if not self.requested_tube_map.has_key(pool_id): continue
            req_tube = self.requested_tube_map[pool_id]
            if not req_tube == req_stock_sample.stock_tube_barcode:
                info = 'MD pool: %s, requested: %s, scheduled: %s' \
                       % (pool_id, str(req_tube),
                          str(req_stock_sample.stock_tube_barcode))
                replaced_tubes.append(info)
                req_stock_sample.stock_tube_barcode = req_tube

        if len(replaced_tubes) > 0:
            msg = 'Some requested tubes differ from the ones scheduled ' \
                  'during ISO generation (%i molecule design pool(s)). The ' \
                  'scheduled tubes are replaced by the requested ones. ' \
                  'Details: %s.' % (len(replaced_tubes), replaced_tubes)
            self.add_warning(msg)

    def __select_tubes(self):
        """
        Checks whether the tubes preferred in the preparation layout still
        contain enough liquid.
        """
        self.add_debug('Select stock tubes ...')

        for req_stock_sample in self.requested_stock_samples:
            req_stock_volume = req_stock_sample.take_out_volume + \
                               STOCK_DEAD_VOLUME
            corr_req_stock_vol = req_stock_volume / VOLUME_CONVERSION_FACTOR

            if not self.__has_enough_stock_volume(req_stock_sample,
                                                  corr_req_stock_vol):
                self.__look_for_alternative_stock_tube(req_stock_sample,
                                                       corr_req_stock_vol)

        self.__record_errors()
        self.__check_requested_tube_usage()

        if len(self.__tube_candidates) < 1:
            msg = 'Did not find any tube!'
            self.add_error(msg)
        elif len(self.__missing_pools) > 0:
            del_indices = []
            for i in range(len(self.requested_stock_samples)):
                req_ss = self.requested_stock_samples[i]
                if req_ss.pool.id in self.__missing_pools:
                    del_indices.append(i)
            del_indices.sort(reverse=True)
            for i in del_indices: del self.requested_stock_samples[i]

    def __has_enough_stock_volume(self, req_stock_sample, req_stock_vol):
        """
        Checks whether there is still enough volume in the preferred stock tube.
        If so, the tube will be added as candidate.
        """
        if req_stock_sample.stock_rack_barcode in self.excluded_racks:
            return False

        query_statement = TubeCandidate.CONFIRMATION_QUERY \
                  % (req_stock_sample.stock_tube_barcode, req_stock_vol,
                     req_stock_sample.stock_concentration \
                                            / CONCENTRATION_CONVERSION_FACTOR,
                     STOCK_ITEM_STATUS)

        tube_candidates = []
        #pylint: disable=W0142
        results = self.__session.query(
                            *TubeCandidate.CONFIRMATION_QUERY_RESULTS). \
                            from_statement(query_statement).all()
        #pylint: enable=W0142
        for record in results:
            candidate = TubeCandidate.create_from_confirmation_query(record,
                                            req_stock_sample.stock_tube_barcode)
            tube_candidates.append(candidate)

        if len(tube_candidates) < 1:
            return False
        elif len(tube_candidates) > 1:
            msg = 'There several tube candidates for molecule design pool ' \
                  'ID %s (preferred tube %s). This is a programming error, ' \
                  'please contact the IT department!' \
                   % (req_stock_sample.pool.id,
                      req_stock_sample.stock_tube_barcode)
            self.add_error(msg)
            return False
        else:
            candidate = tube_candidates[0]
            rack_barcode = candidate.rack_barcode
            if not rack_barcode == req_stock_sample.stock_rack_barcode and \
                        not candidate.tube_barcode in self.requested_tubes:
                msg = 'The tube %s for molecule design pool %s has been ' \
                      'moved since the generation ISO!' \
                       % (req_stock_sample.stock_tube_barcode,
                          req_stock_sample.pool.id)
                self.add_warning(msg)
            self.__store_candidate(candidate, req_stock_sample, rack_barcode)
            return True

    def __look_for_alternative_stock_tube(self, req_stock_sample,
                                          req_stock_vol):
        """
        Picks an alternative stock tube if the preferred one is not
        available anymore.
        """
        tube_specs = get_stock_tube_specs_db_term()
        query_statement = TubeCandidate.SEARCH_QUERY \
                  % (req_stock_sample.pool.id,
                     req_stock_sample.stock_concentration \
                                           / CONCENTRATION_CONVERSION_FACTOR,
                     req_stock_vol, STOCK_ITEM_STATUS, tube_specs)

        tube_candidates = []
        #pylint: disable=W0142
        results = self.__session.query(*TubeCandidate.SEARCH_QUERY_RESULTS). \
                            from_statement(query_statement).all()
        #pylint: enable=W0142
        for record in results:
            candidate = TubeCandidate.create_from_searching_query(record)
            tube_candidates.append(candidate)

        if len(tube_candidates) < 1:
            info = '%s (%.1f ul, %s nM)' % (req_stock_sample.pool.id,
                                    req_stock_vol * VOLUME_CONVERSION_FACTOR,
                                    req_stock_sample.stock_concentration)
            self.__missing_pools.append(req_stock_sample.pool.id)
            self.__no_tubes.append(info)

        else:
            proposed_candidate = None
            max_vol = 0
            for candidate in tube_candidates:
                if candidate.rack_barcode in self.excluded_racks: continue
                if candidate.tube_barcode in self.requested_tubes:
                    proposed_candidate = candidate
                    break
                if candidate.stock_volume > max_vol:
                    max_vol = candidate.stock_volume
                    proposed_candidate = candidate

            if proposed_candidate is None:
                msg = 'Could not find a valid tube rack for molecule design ' \
                      'pool %s! At least one potential candidate has been ' \
                      'excluded.' % (req_stock_sample.pool.id)
                self.__missing_pools.append(req_stock_sample.pool.id)
                self.add_warning(msg)
            else:
                rack_barcode = proposed_candidate.rack_barcode
                self.__store_candidate(proposed_candidate, req_stock_sample,
                                       rack_barcode)
                if not req_stock_sample.stock_rack_barcode \
                                                        in self.excluded_racks:
                    msg = 'Tube %s for molecule design pool %s does not have ' \
                          'a sufficient volume anymore! The tube has been ' \
                          'replaced by tube %s (rack %s).' \
                           % (req_stock_sample.stock_tube_barcode,
                              req_stock_sample.pool.id,
                              proposed_candidate.tube_barcode,
                              proposed_candidate.rack_barcode)
                    self.add_warning(msg)
                else:
                    msg = 'Tube %s for molecule design pool %s has been ' \
                          'replaced by tube %s because rack %s has been ' \
                          'excluded!' % (req_stock_sample.stock_tube_barcode,
                          req_stock_sample.pool.id,
                          proposed_candidate.tube_barcode,
                          req_stock_sample.stock_rack_barcode)
                    self.add_warning(msg)

    def __store_candidate(self, candidate, requested_stock_sample,
                          rack_barcode):
        """
        Stores the picked tube candidates.
        """
        add_list_map_element(self.__tube_candidates, rack_barcode, candidate)
        requested_stock_sample.tube_candidate = candidate

    def __record_errors(self):
        """
        Records errors that have been collected during the tube picking.
        """
        if len(self.__no_tubes):
            msg = 'Could not find a valid tube rack for the following ' \
                  'molecule design pools (volumes incl. stock dead volume): ' \
                  '%s.' % (self.__no_tubes)
            self.add_warning(msg)

    def __check_requested_tube_usage(self):
        """
        Checks whether all requested tubes have been found.
        """
        used_requested_tubes = []
        for req_tube in self.requested_tubes:
            for candidate_list in self.__tube_candidates.values():
                for candidate in candidate_list:
                    if not candidate.tube_barcode == req_tube: continue
                    used_requested_tubes.append(req_tube)
        missing_requested_tubes = []
        for req_tube in self.requested_tubes:
            if not req_tube in used_requested_tubes:
                missing_requested_tubes.append(str(req_tube))

        if len(missing_requested_tubes) > 0:
            msg = 'Could not find suitable tubes for the following tube ' \
                  'barcodes you have requested: % s.' \
                   % (missing_requested_tubes)
            self.add_warning(msg)

    def __fetch_rack_locations(self):
        """
        Searchs and adds the location for the selected candidates.
        """
        self.add_debug('Fetch stock rack locations ...')

        query = RackLocationQuery(rack_barcodes=self.__tube_candidates.keys())
        query.run(self.__session)

        for rack_barcode, candidates in self.__tube_candidates.iteritems():
            location_name = query.location_names[rack_barcode]
            location_index = query.location_indices[rack_barcode]
            for candidate in candidates:
                candidate.set_location(location_name, location_index)


class TubeCandidate(object):
    """
    A stock tube candidate (storage class, immutable).
    """

    #: The index of the stock volume in the query results.
    STOCK_VOLUME_INDEX = 0
    #: The index of the rack barcode in the query results.
    RACK_BARCODE_INDEX = 1
    #: The index of the position row index in the query results.
    ROW_INDEX_INDEX = 2
    #: The index of the position column index in the query results.
    COLUMN_INDEX_INDEX = 3
    #: The index of the tube barcode in the query results.
    TUBE_BARCODE_INDEX = 4

    #: The query used when checking the volume of a schedule tube.
    CONFIRMATION_QUERY = '''
    SELECT s.volume AS stock_volume,
        r.barcode AS rack_barcode,
        rc.row AS row_index,
        rc.col AS column_index,
        cb.barcode AS tube_barcode
    FROM container c, container_barcode cb, rack r, containment rc, sample s,
        stock_sample ss
    WHERE cb.barcode = '%s'
    AND s.container_id = cb.container_id
    AND s.volume >= %s
    AND s.sample_id = ss.sample_id
    AND ss.concentration = %s
    AND c.container_id = cb.container_id
    AND c.item_status = '%s'
    AND rc.held_id = c.container_id
    AND r.rack_id = rc.holder_id;
    '''

    #: The query result column names for the confirmation query
    #: (required to parse the query results).
    CONFIRMATION_QUERY_RESULTS = ('stock_volume', 'rack_barcode',
            'row_index', 'column_index')

    #: The query used when looking for alternative tubes.
    SEARCH_QUERY = '''
    SELECT cb.barcode AS tube_barcode, s.volume AS stock_volume,
        rc.row AS row_index, rc.col AS column_index, r.barcode AS rack_barcode
    FROM stock_sample ss, sample s, container c, container_barcode cb,
        container_specs cs, containment rc, rack r
    WHERE ss.molecule_design_set_id = %s
    AND ss.sample_id = s.sample_id
    AND ss.concentration = %s
    AND s.volume >= %s
    AND s.container_id = c.container_id
    AND c.item_status = '%s'
    AND c.container_id = cb.container_id
    AND c.container_specs_id = cs.container_specs_id
    AND cs.name IN %s
    AND rc.held_id = c.container_id
    AND rc.holder_id = r.rack_id;'''

    #: The query result column names for the confirmation query
    #: (required to parse the query results).
    SEARCH_QUERY_RESULTS = CONFIRMATION_QUERY_RESULTS + ('tube_barcode',)


    def __init__(self, rack_barcode, rack_position, tube_barcode,
                 stock_volume):
        """
        Contstructor:

        :param rack_barcode: The barcode of a stock rack.
        :type rack_barcode: :class:`basestring`

        :param rack_position: The rack position in the stock tube.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param tube_barcode: The barcode of the stock tube.
        :type tube_barcode: :class:`basestring`

        :param stock_volume: The volume of the tube.
        :type stock_volume: :class:float`

        :param location_name: The name of the barcoded location the rack is
            stored at.
        :type location_name: :class:`basestring

        :param location_index: The index of of the rack in the barcoded
            location.
        :type location_index: :class:`int`
        """
        #: The barcode of a stock rack.
        self.__rack_barcode = rack_barcode
        #: The rack position in the stock tube.
        self.__rack_position = rack_position
        #: The barcode of the stock tube.
        self.__tube_barcode = tube_barcode
        #: The volume of the tube in the stock.
        self.__stock_volume = stock_volume

        #: The name of the barcoded location the rack is stored at.
        self.location_name = None
        #: The index of the rack within the barcoded location.
        self.location_index = None

    @property
    def rack_barcode(self):
        """The barcode of a stock rack."""
        return self.__rack_barcode

    @property
    def rack_position(self):
        """The rack position of the stock tube."""
        return self.__rack_position

    @property
    def tube_barcode(self):
        """The barcode of the stock tube."""
        return self.__tube_barcode

    @property
    def stock_volume(self):
        """The volume in the stock tube."""
        return self.__stock_volume

    def set_location(self, location_name, location_index):
        """
        Sets the location name and index of the candidate (using a record
        of the location query result).
        """
        self.location_name = location_name
        self.location_index = location_index

    @classmethod
    def create_from_confirmation_query(cls, record, tube_barcode):
        """
        Creates a tube candidate from a confirmation query result.
        """

        row_index = record[cls.ROW_INDEX_INDEX]
        column_index = record[cls.COLUMN_INDEX_INDEX]
        rack_pos = get_rack_position_from_indices(row_index, column_index)

        tube_candidate = TubeCandidate(tube_barcode=tube_barcode,
                            rack_position=rack_pos,
                            rack_barcode=record[cls.RACK_BARCODE_INDEX],
                            stock_volume=record[cls.STOCK_VOLUME_INDEX])

        return tube_candidate

    @classmethod
    def create_from_searching_query(cls, record):
        """
        Creates a tube candidate from a replacement search query result.
        """
        tube_barcode = record[cls.TUBE_BARCODE_INDEX]
        return cls.create_from_confirmation_query(record, tube_barcode)

    def __repr__(self):
        str_format = '<TubeCandidate: %s, rack: %s, position: %s, vol: %s>'
        params = (self.__tube_barcode, self.__rack_barcode,
                  self.__rack_position, self.__stock_volume)
        return str_format % params


class IsoXL20WorklistWriter(BaseXL20WorklistWriter):
    """
    This tool writes a worklist for the XL20 (tube handler) using the
    provided tube candidates.

    **Return Value:** the XL20 worklist as stream
    """

    NAME = 'ISO XL20 Worklist Writer'

    def __init__(self, sector_stock_samples, destination_rack_barcode_map, log):
        """
        Constructor:

        :param sector_stock_samples: The requested stock samples (incl.
            selected tube candidates) mapped onto rack sectors.
        :type sector_stock_samples: :class:`dict` of with sector indices as keys
            and lists of :class:`TubeCandidate` objects as values

        :param destination_rack_barcode_map: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcode_map: map of barcodes
            (:class:`basestring`) mapped onto sector indices.

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseXL20WorklistWriter.__init__(self, log=log)

        #: The selected tube candidates mapped onto rack sector.
        self.sector_stock_samples = sector_stock_samples
        #: The barcodes of the racks the tubes shall be transferred to.
        self.destination_rack_map = destination_rack_barcode_map

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('sector stock samples map',
                                   self.sector_stock_samples, dict):
            for si, req_stock_samples in self.sector_stock_samples.iteritems():
                if not self._check_input_class('sector index', si, int): break
                if not self._check_input_class('requested stock sample list',
                                               req_stock_samples, list): break
                for rss in req_stock_samples:
                    if not self._check_input_class('requested stock sample',
                                    rss, RequestedStockSample): break

        if self._check_input_class('destination rack barcode map',
                                   self.destination_rack_map, dict):
            for sector_index, barcode in self.destination_rack_map.iteritems():
                if not self._check_input_class('sector index', sector_index,
                                               int): break
                if not self._check_input_class('rack barcode', barcode,
                                               basestring): break

        if not self.has_errors():
            for sector_index in self.sector_stock_samples.keys():
                if not self.destination_rack_map.has_key(sector_index):
                    msg = 'The destination map misses sector index %i!' \
                          % (sector_index)
                    self.add_error(msg)

    def _store_column_values(self):
        """
        Stores the column values.
        """
        self.add_debug('Stores column values ...')

        sector_map = dict()
        src_rack_map = dict()
        for sector_index, req_samples in self.sector_stock_samples.iteritems():
            for req_stock_sample in req_samples:
                tube_candidate = req_stock_sample.tube_candidate
                rack_barcode = tube_candidate.rack_barcode
                add_list_map_element(src_rack_map, rack_barcode,
                                     req_stock_sample)
                sector_map[tube_candidate.tube_barcode] = sector_index

        racks = src_rack_map.keys()
        racks.sort()
        for src_rack in racks:
            requested_stock_samples = src_rack_map[src_rack]
            for rss in requested_stock_samples:
                tc = rss.tube_candidate
                self._source_rack_values.append('%08i' % (int(src_rack)))
                self._source_position_values.append(tc.rack_position)
                tube_barcode = tc.tube_barcode
                self._tube_barcode_values.append(tube_barcode)
                sector_index = sector_map[tube_barcode]
                dest_rack_barcode = self.destination_rack_map[sector_index]
                self._dest_rack_values.append('%08i' % int((dest_rack_barcode)))
                self._dest_position_values.append(rss.target_position)


class IsoXL20ReportWriter(TxtWriter):
    """
    This class generates the stream for a XL20 worklist generation report.

    **Return Value:** stream
    """

    NAME = 'ISO XL20 Report Writer'

    #: The main headline of the file.
    BASE_MAIN_HEADER = 'XL20 Worklist Generation Report / %s / %s'

    #: The header text for the general section.
    GENERAL_HEADER = 'General Settings'
    #: This line presents the ISO or ISO job label.
    LABEL_LINE = '%s: %s'
    #: To be filled into the :attr:`LABEL_LINE` if the report is created for
    #: an ISO.
    ISO_MARKER = 'ISO'
    #: To be filled into the :attr:`LABEL_LINE` if the report is created for
    #: an ISO job.
    ISO_JOB_MARKER = 'ISO job'

    #: This line presents the format of the preparation plate.
    PREP_SHAPE_BASE_LINE = 'Plate format: %s'
    #: This line presents the total number of stock tubes used.
    TUBE_NO_BASE_LINE = 'Total number of tubes: %i'
    #: This is title for the volumes section (part of the \'general\' section).
    VOLUME_TITLE = 'Volumes'
    #: The volume part of the general section body.
    VOLUME_BASE_LINE = '%.1f ul: %s'
    #: The body for the general section.

    #: The header text for the destination racks section.
    DESTINATION_RACKS_HEADER = 'Destination Racks'
    #: The body for the destination racks section.
    DESTINATION_RACK_BASE_LINE = 'Q%i: %s'

    #: The header text for the excluded racks section.
    EXCLUDED_RACKS_HEADER = 'Excluded Racks'
    #: The body for the excluded racks section.
    EXCLUDED_RACKS_BASE_LINE = '%s'
    #: Is used if there are no exlcuded racks.
    NO_EXCLUDED_RACKS_MARKER = 'no excluded racks'

    #: The header text for the  requested tubes section.
    REQUESTED_TUBES_HEADER = 'Requested Tubes'
    #: The body for the requested tubes section.
    REQUESTED_TUBES_BASE_LINE = '%s'
    #: Is used if no tubes have been requested.
    NO_REQUESTED_TUBES_MARKER = 'no requested tubes'

    #: The header for the source racks section.
    SOURCE_RACKS_HEADER = 'Source Racks'
    #: The body for the source racks section.
    SOURCE_RACKS_BASE_LINE = '%s (%s)'

    #: The header for the warning section.
    WARNING_HEADER = 'Warnings'
    #: The body for the warnings section.
    WARNING_BASE_LINE = '%s'
    #: Is used if no warnings have occurred.
    NO_WARNING_MARKER = 'no warnings'

    def __init__(self, label, rack_shape_name, sector_stock_samples,
                 destination_rack_barcode_map, excluded_racks, requested_tubes,
                 is_job, log):
        """
        Constructor:

        :param label: The label of the ISO or ISO job.
        :type label: :class:`basestring`

        :param rack_shape_name: The name of the preparation layout rack shape.
        :type rack_shape_name: :class:`str`

        :param sector_stock_samples: The final stock sample picked mapped onto
            rack sectors.
        :type sector_stock_samples: :class:`dict` of with sector indices as keys
            and lists of :class:`TubeCandidate` objects as values

        :param destination_rack_barcode_map: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcode_map: map of barcodes
            (:class:`basestring`) mapped onto sector indices.

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param is_job: Is the report generated for a job (*True*) or for a
            single ISO (*False*)?
        :type is_job: :class:`bool`

        :param log: The log to write into -  it also contains the warnings
            of the external tools (tube selection steps).
        :type log: :class:`thelma.ThelmaLog`
        """
        TxtWriter.__init__(self, log=log)

        #: The label of the ISO or ISO job used in the worklist generator.
        self.label = label
        #: The name of the preparation layout rack shape.
        self.rack_shape_name = rack_shape_name
        #: The :class:`RequestedStockSample` objects for the selected tubes.
        self.sector_stock_samples = sector_stock_samples
        #: The barcode of the destination rack (the rack the tubes shall
        #: be transferred to).
        self.destination_rack_map = destination_rack_barcode_map
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks
        #: A list of barcodes from stock tubes that are supposed to be used.
        self.requested_tubes = requested_tubes
        #: Is the report generated for a job (*True*) or for a single ISO
        #: s(*False*)?
        self.is_job = is_job

    def _check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('label', self.label, basestring)
        self._check_input_class('rack shape name', self.rack_shape_name, str)

        if self._check_input_class('sector stock samples map',
                                   self.sector_stock_samples, dict):
            for si, req_stock_samples in self.sector_stock_samples.iteritems():
                if not self._check_input_class('sector index', si, int): break
                if not self._check_input_class('requested stock sample list',
                                               req_stock_samples, list): break
                for req_stock_sample in req_stock_samples:
                    if not self._check_input_class('requested stock sample',
                                req_stock_sample, RequestedStockSample): break

        if self._check_input_class('destination rack barcode map',
                                   self.destination_rack_map, dict):
            for sector_index, barcode in self.destination_rack_map.iteritems():
                if not self._check_input_class('sector index', sector_index,
                                               int): break
                if not self._check_input_class('rack barcode', barcode,
                                               basestring): break

        if self._check_input_class('excluded racks list', self.excluded_racks,
                                   list):
            for rack_barcode in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                        rack_barcode, basestring): break
        if not self.requested_tubes is None and \
                            self._check_input_class('requested tubes list',
                                                    self.requested_tubes, list):
            for tube_barcode in self.requested_tubes:
                if not self._check_input_class('requested tube barcode',
                                               tube_barcode, basestring): break

        if not self.has_errors():
            for sector_index in self.sector_stock_samples.keys():
                if not self.destination_rack_map.has_key(sector_index):
                    msg = 'The destination map misses sector index %i!' \
                          % (sector_index)
                    self.add_error(msg)

    def _write_stream_content(self):
        """
        Writes into the streams.
        """
        self.add_debug('Write stream ...')

        self.__write_main_headline()
        self.__write_general_section()
        self.__write_destination_racks_section()
        self.__write_excluded_racks_section()
        self.__write_requested_tubes_section()
        self.__write_source_racks_section()
        self.__write_warning_section()

    def __write_main_headline(self):
        """
        Writes the main head line.
        """
        now = datetime.now()
        date_string = now.strftime('%d.%m.%Y')
        time_string = now.strftime('%H:%M')
        main_headline = self.BASE_MAIN_HEADER % (date_string, time_string)
        self._write_headline(main_headline, underline_char='=',
                             preceding_blank_lines=0, trailing_blank_lines=1)


    def __write_general_section(self):
        """
        Writes the GENERAL section.
        """
        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)

        volumes_part = self.__create_volumes_part()

        if self.is_job:
            marker = self.ISO_JOB_MARKER
        else:
            marker = self.ISO_MARKER
        label_line = self.LABEL_LINE % (marker, self.label)

        candidate_number = 0
        for candidates in self.sector_stock_samples.values():
            candidate_number += len(candidates)

        general_lines = [label_line,
                         self.PREP_SHAPE_BASE_LINE % (self.rack_shape_name),
                         self.TUBE_NO_BASE_LINE % (candidate_number),
                         '',
                         self.VOLUME_TITLE,
                         volumes_part]
        self._write_body_lines(line_list=general_lines)

    def __create_volumes_part(self):
        """
        Creates the volumes part for the main section.
        """
        vol_map = dict()

        for req_stock_samples in self.sector_stock_samples.values():
            for req_stock_sample in req_stock_samples:
                take_out_volume = req_stock_sample.take_out_volume
                add_list_map_element(vol_map, take_out_volume,
                                     req_stock_sample.pool.id)

        volume_lines = []
        for volume, pool_ids in vol_map.iteritems():
            pool_list_string = ', '.join(
                                [str(pool_id) for pool_id in sorted(pool_ids)])
            volume_line = self.VOLUME_BASE_LINE % (volume, pool_list_string)
            volume_lines.append(volume_line)

        return LINEBREAK_CHAR.join(volume_lines)

    def __write_destination_racks_section(self):
        """
        Writes the destination rack section.
        """
        self._write_headline(self.DESTINATION_RACKS_HEADER)
        destination_lines = []
        for sector_index, barcode in self.destination_rack_map.iteritems():
            line = self.DESTINATION_RACK_BASE_LINE % (sector_index + 1, barcode)
            destination_lines.append(line)
        self._write_body_lines(line_list=destination_lines)

    def __write_excluded_racks_section(self):
        """
        Writes the excluded racks section.
        """
        self._write_headline(self.EXCLUDED_RACKS_HEADER)

        if len(self.excluded_racks) < 1:
            lines = [self.EXCLUDED_RACKS_BASE_LINE \
                     % (self.NO_EXCLUDED_RACKS_MARKER)]
        else:
            lines = []
            for rack in self.excluded_racks:
                lines.append(self.EXCLUDED_RACKS_BASE_LINE % (rack))

        self._write_body_lines(line_list=lines)

    def __write_requested_tubes_section(self):
        """
        Writes the requested tubes section.
        """
        self._write_headline(self.REQUESTED_TUBES_HEADER)

        if self.requested_tubes is None or len(self.requested_tubes) < 1:
            lines = [self.REQUESTED_TUBES_BASE_LINE \
                     % (self.NO_REQUESTED_TUBES_MARKER)]
        else:
            lines = []
            for tube in self.requested_tubes:
                lines.append(self.REQUESTED_TUBES_BASE_LINE % (tube))

        self._write_body_lines(lines)

    def __write_source_racks_section(self):
        """
        Writes the source rack section.
        """
        self._write_headline(self.SOURCE_RACKS_HEADER)

        src_rack_map = dict()
        for req_stock_samples in self.sector_stock_samples.values():
            for req_stock_sample in req_stock_samples:
                tube_candidate = req_stock_sample.tube_candidate
                rack_barcode = tube_candidate.rack_barcode
                if src_rack_map.has_key(rack_barcode): continue
                loc_info = tube_candidate.location_name
                if loc_info is None:
                    loc_info = 'unknown location'
                elif not tube_candidate.location_index is None:
                    loc_info += ', index: %s' % (tube_candidate.location_index)
                src_rack_map[rack_barcode] = loc_info

        src_rack_lines = []
        barcodes = src_rack_map.keys()
        barcodes.sort()
        for rack_barcode in barcodes:
            loc_info = src_rack_map[rack_barcode]
            src_rack_line = self.SOURCE_RACKS_BASE_LINE % \
                            (rack_barcode, loc_info)
            src_rack_lines.append(src_rack_line)

        self._write_body_lines(src_rack_lines)

    def __write_warning_section(self):
        """
        Writes the warning section.
        """
        self._write_headline(self.WARNING_HEADER)

        warnings = self.log.get_messages()
        if len(warnings) < 1:
            lines = [self.WARNING_BASE_LINE % (self.NO_WARNING_MARKER)]
        else:
            lines = []
            for warning in warnings:
                lines.append(self.WARNING_BASE_LINE % (warning))

        self._write_body_lines(lines)


class IsoControlLayoutFinder(BaseAutomationTool):
    """
    Finds the control layout for an ISO job.

    **Return Value:** IsoControlRackLayout
    """
    NAME = 'ISO Control Layout Finder'

    def __init__(self, iso_job, log):
        """
        Constructor:

        :param iso_job: The ISO job to create the layout for.
        :type iso_job: :class:`thelma.models.job.IsoJob`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The ISO job to create the layout for.
        self.iso_job = iso_job

        #: The preparation position of one ISO mapped onto molecule design pools
        #: (must be equal for all ISOs).
        self.__control_pos_map = None

        #: The requested stock samples used to generate the layout.
        self.__requested_stock_samples = None
        #: The control layout.
        self.__control_layout = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__control_pos_map = None
        self.__control_layout = IsoControlRackLayout()
        self.__requested_stock_samples = []

    def get_requested_stock_samples(self):
        """
        Returns the requested stock samples that have been used to generate
        the control rack layout.
        """
        if self.return_value is None:
            return None
        else:
            return self.__requested_stock_samples

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start control rack layout generation ...')

        self.__check_input()
        if not self.has_errors(): self.__create_preparation_position_map()
        if not self.has_errors(): self.__generate_control_layout()
        if not self.has_errors():
            self.return_value = self.__control_layout
            self.add_info('Control rack layout generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('ISO job', self.iso_job, IsoJob):
            if len(self.iso_job.isos) < 1:
                msg = 'There are no ISOs in this ISO job!'
                self.add_error(msg)

    def __create_preparation_position_map(self):
        """
        Creates the control layout for the potential control stock rack.
        """
        self.add_debug('Create control layout ...')

        ref_iso = None
        for iso in self.iso_job.isos:
            if self.has_errors(): break
            prep_layout = self.__get_preparation_layout(iso)
            if prep_layout is None: break
            layout_controls = self.__get_control_position_map(prep_layout)
            if self.__control_pos_map is None:
                self.__control_pos_map = layout_controls
                ref_iso = iso.label
            elif not self.__is_equal_control_set(layout_controls):
                msg = 'The preparation layouts of the different ISOs are ' \
                      'inconsistent. First occurence: ISOs %s and %s.' \
                      % (iso.label, ref_iso)
                self.add_error(msg)

    def __get_preparation_layout(self, iso):
        """
        Fetches the preparation layout for a ISO.
        """
        rack_layout = iso.rack_layout
        if not rack_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            msg = 'Unsupported rack shape "%s".' \
                   % (rack_layout.shape.name)
            self.add_error(msg)

        converter = PrepIsoLayoutConverter(rack_layout=iso.rack_layout,
                                           log=self.log)
        prep_layout = converter.get_result()

        if prep_layout is None:
            msg = 'Error when trying to convert preparation layout for ISO ' \
                  '%s.' % (iso.label)
            self.add_error(msg)

        return prep_layout

    def __get_control_position_map(self, prep_layout):
        """
        Returns the control position of a preparation layout mapped onto
        their molecule design IDs.
        """
        starting_wells = prep_layout.get_starting_wells()
        pool_map = dict()
        for prep_pos in starting_wells.values():
            if prep_pos.is_mock or prep_pos.is_floating: continue
            pool = prep_pos.molecule_design_pool
            add_list_map_element(pool_map, pool, prep_pos)

        control_positions = dict()
        for pool, prep_positions in pool_map.iteritems():
            control_positions[pool] = prep_positions

        if len(control_positions) < 1:
            msg = 'Could not find control positions for this job. The ' \
                  'molecule design pools are all covered by the sample stock ' \
                  'racks.'
            self.add_error(msg)

        return control_positions

    def __is_equal_control_set(self, layout_positions):
        """
        Compares the controls sets of two ISOs.
        """
        if not len(layout_positions) == len(self.__control_pos_map):
            return False

        for pool, prep_positions in layout_positions.iteritems():
            if not self.__control_pos_map.has_key(pool): return False
            ref_preps = self.__control_pos_map[pool]
            if not len(ref_preps) == len(prep_positions): return False
            for prep_pos in prep_positions:
                if not prep_pos in ref_preps: return False

        return True

    def __generate_control_layout(self):
        """
        Generates the ISO control plate layout for this job. Also creates
        the requested molecules for the stock tube picker.
        """
        rack_shape_96 = get_96_rack_shape()
        empty_pos_manager = EmptyPositionManager(rack_shape=rack_shape_96)

        sorted_pools = sorted(self.__control_pos_map.keys(), cmp=lambda p1, p2:
                                                             cmp(p1.id, p2.id))
        for pool in sorted_pools:
            prep_positions = self.__control_pos_map[pool]
            transfer_targets = []
            for prep_pos in prep_positions:
                take_out_volume = prep_pos.get_stock_takeout_volume()
                tt = TransferTarget(rack_position=prep_pos.rack_position,
                            transfer_volume=take_out_volume)
                transfer_targets.append(tt)

            try:
                rack_pos = empty_pos_manager.get_empty_position()
            except ValueError:
                msg = 'There is no position left in the ISO control plate ' \
                      'layout.'
                self.add_error(msg)
                break

            control_pos = IsoControlRackPosition(rack_position=rack_pos,
                                  molecule_design_pool=pool,
                                  transfer_targets=transfer_targets)
            rss = RequestedStockSample.from_control_pos(control_pos,
                                    prep_positions[0], len(self.iso_job))
            self.__requested_stock_samples.append(rss)
            self.__control_layout.add_position(control_pos)
