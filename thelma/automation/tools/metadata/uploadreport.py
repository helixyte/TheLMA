"""
Tools generating reports for experiment metadata uploads.
"""
from thelma import ThelmaLog
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.metadata.base import TransfectionLayout
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGenerator
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGeneratorLibrary
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketDescriptionBuilder
from thelma.automation.tools.worklists.base import DEAD_VOLUME_COEFFICIENT
from thelma.automation.tools.worklists.base import LIMIT_TARGET_WELLS
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.tracbase import BaseTracTool
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.base import sort_rack_positions
from thelma.models.liquidtransfer import ReservoirSpecs
from tractor import AttachmentWrapper
from tractor import create_wrapper_for_ticket_update
from xmlrpclib import Fault
from xmlrpclib import ProtocolError
import logging


__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentMetadataReportUploader',
           'ExperimentMetadataAssignmentWriter',
           'ExperimentMetadataIsoPlateWriter',
           'ExperimentMetadataInfoWriter',
           'ExperimentMetadataInfoWriterLibrary']


class ExperimentMetadataAssignmentWriter(CsvWriter):
    """
    This tool generates a report presenting the concentration and volumes
    calculated for an experiment metadata ISO to experiment rack translation.
    """

    NAME = 'EM Assignment Report Writer'

    #: The header for the design rack column.
    DESIGN_RACK_HEADER = 'Design Rack Label'
    #: The header for the source well column.
    SOURCE_WELL_HEADER = 'Source Well in ISO Plate'
    #: The header for the target well column.
    TARGET_WELL_HEADER = 'Target Well in Cell Plate'
    #: The header for the final concentration column.
    FINAL_CONCENTRATION_HEADER = 'Final Concentration in nM'
    #: The header for the ISO concentration column.
    ISO_CONCENTRATION_HEADER = 'ISO Concentration in nM'
    #: The header for the ISO volume column.
    ISO_VOLUME_HEADER = 'ISO Volume in ul'

    #: The index for the design rack column.
    DESIGN_RACK_INDEX = 0
    #: The index for the source well column.
    SOURCE_WELL_INDEX = 1
    #: The index for the target well column.
    TARGET_WELL_INDEX = 2
    #: The index for the final concentration column.
    FINAL_CONCENTRATION_INDEX = 3
    #: The index for the ISO concentration column.
    ISO_CONCENTRATION_INDEX = 4
    #: The index for the ISO volume column.
    ISO_VOLUME_INDEX = 5

    def __init__(self, generator, log):
        """
        Constructor:

        :param generator: The generator that has conducted the upload.
        :type generator: :class:`ExperimentMetadataGenerator`
        :param log: The ThelmaLog you want to write into. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """

        CsvWriter.__init__(self, log)

        #: The generator that has conducted the upload.
        self.generator = generator

        #: The completed ISO source layout.
        self.source_layout = None
        #: The transfection layouts containing the association data for
        #: each design rack.
        self.association_layouts = None
        #: A map containing the final concentrations for each design rack.
        self.final_concentrations = None

        #: Intermediate storage for the column values.
        self.__source_well_values = None
        self.__design_rack_values = None
        self.__target_well_values = None
        self.__iso_volume_values = None
        self.__iso_concentration_values = None
        self.__final_concentration_values = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        CsvWriter.reset(self)
        self.source_layout = None
        self.association_layouts = None
        self.final_concentrations = None
        self.__source_well_values = []
        self.__design_rack_values = []
        self.__target_well_values = []
        self.__iso_volume_values = []
        self.__iso_concentration_values = []
        self.__final_concentration_values = []

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list`
        """
        self.__check_input()
        if not self.has_errors(): self.__fetch_report_data()
        if not self.has_errors(): self.__generate_column_values()
        if not self.has_errors(): self.__generate_columns()

    def __check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input values ...')
        self._check_input_class('experiment metadata generator',
                                self.generator, ExperimentMetadataGenerator)

    def __fetch_report_data(self):
        """
        Retrieves the data required from the generator.
        """
        self.add_debug('Fetch report data ...')

        self.source_layout = self.generator.get_source_layout()
        self.association_layouts = self.generator.get_association_layouts()
        self.final_concentrations = self.generator.get_final_concentrations()

        if self.source_layout is None \
                            or self.association_layouts is None \
                            or self.final_concentrations is None:
            msg = 'Error when trying to fetch report data.'
            self.add_error(msg)

    def __generate_column_values(self):
        """
        Generates the values for the CSV columns.
        """
        self.add_debug('Generate column value lists ...')

        labels = self.association_layouts.keys()
        labels.sort()
        for label in labels: self.__store_design_rack_value(label)

    def __store_design_rack_value(self, label):
        """
        Stores the values for a particular design rack.
        """
        self.add_debug('Store values for design rack %s ...' % (label))

        tf_layout = self.association_layouts[label]
        concentrations = self.final_concentrations[label]

        missing_final_concentration = []
        for tf_pos in tf_layout.get_sorted_working_positions():
            cell_plate_positions = tf_pos.cell_plate_positions
            cell_plate_positions = sort_rack_positions(cell_plate_positions)
            # design rack position might lack ISO volume and conc
            src_pos = self.source_layout.get_working_position(
                                                    tf_pos.rack_position)
            for trg_pos in cell_plate_positions:
                self.__source_well_values.append(tf_pos.rack_position.label)
                self.__design_rack_values.append(label)
                self.__target_well_values.append(trg_pos.label)
                self.__iso_volume_values.append(src_pos.iso_volume)
                self.__iso_concentration_values.append(
                                                    src_pos.iso_concentration)

                if not concentrations.has_key(trg_pos):
                    missing_final_concentration.append(trg_pos.label)
                    continue
                final_conc = concentrations[trg_pos]
                self.__final_concentration_values.append(final_conc)

        if len(missing_final_concentration) > 0:
            msg = 'There are final concentrations missing for the following ' \
                  'rack positions of design rack %s: %s' \
                  % (label, missing_final_concentration)
            self.add_error(msg)

    def __generate_columns(self):
        """
        Generates the columns for the report.
        """
        self.add_debug('Generate columns ...')

        source_well_column = CsvColumnParameters.create_csv_parameter_map(
                    self.SOURCE_WELL_INDEX, self.SOURCE_WELL_HEADER,
                    self.__source_well_values)
        design_rack_column = CsvColumnParameters.create_csv_parameter_map(
                    self.DESIGN_RACK_INDEX, self.DESIGN_RACK_HEADER,
                    self.__design_rack_values)
        target_well_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TARGET_WELL_INDEX, self.TARGET_WELL_HEADER,
                    self.__target_well_values)
        iso_volume_column = CsvColumnParameters.create_csv_parameter_map(
                    self.ISO_VOLUME_INDEX, self.ISO_VOLUME_HEADER,
                    self.__iso_volume_values)
        iso_concentration_column = CsvColumnParameters.create_csv_parameter_map(
                    self.ISO_CONCENTRATION_INDEX, self.ISO_CONCENTRATION_HEADER,
                    self.__iso_concentration_values)
        final_conc_column = CsvColumnParameters.create_csv_parameter_map(
                    self.FINAL_CONCENTRATION_INDEX,
                    self.FINAL_CONCENTRATION_HEADER,
                    self.__final_concentration_values)

        self._column_map_list = [source_well_column, design_rack_column,
                                 target_well_column, iso_volume_column,
                                 iso_concentration_column,
                                 final_conc_column]
        self.add_info('Column generation completed.')


class ExperimentMetadataIsoPlateWriter(CsvWriter):
    """
    This tool generates a report presenting the concentrations and volumes
    and molecule designs of the ISO plate.
    """

    NAME = 'EM ISO Plate Writer'

    #: The header for the source well column.
    POSITION_HEADER = 'Rack Position'
    #: The header for the molecule design pool ID column.
    MDP_HEADER = 'Molecule Design Pool ID'
    #: The header for the ISO concentration column.
    ISO_CONCENTRATION_HEADER = 'ISO Concentration in nM'
    #: The header for the ISO volume column.
    ISO_VOLUME_HEADER = 'ISO Volume in ul'

    #: The index for the position column.
    POSITION_INDEX = 0
    #: The index for the molecule design pool ID.
    MDP_INDEX = 1
    #: The index for the ISO concentration column.
    ISO_CONCENTRATION_INDEX = 2
    #: The index for the ISO volume column.
    ISO_VOLUME_INDEX = 3

    def __init__(self, generator, log):
        """
        Constructor:

        :param generator: The generator that has conducted the upload.
        :type generator: :class:`ExperimentMetadataGenerator`

        :param log: The ThelmaLog you want to write into. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """

        CsvWriter.__init__(self, log)

        #: The generator that has conducted the upload.
        self.generator = generator

        #: The completed ISO source layout.
        self.source_layout = None

        #: Intermediate storage for the column values.
        self.__position_values = None
        self.__md_pool_values = None
        self.__iso_concentration_values = None
        self.__iso_volume_values = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        CsvWriter.reset(self)
        self.source_layout = None
        self.__position_values = []
        self.__md_pool_values = []
        self.__iso_concentration_values = []
        self.__iso_volume_values = []

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list`
        """
        self.__check_input()
        if not self.has_errors(): self.__fetch_report_data()
        if not self.has_errors(): self.__generate_column_values()
        if not self.has_errors(): self.__generate_columns()

    def __check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input values ...')
        self._check_input_class('experiment metadata generator',
                                self.generator, ExperimentMetadataGenerator)

    def __fetch_report_data(self):
        """
        Retrieves the data required from the generator.
        """
        self.add_debug('Fetch report data ...')

        self.source_layout = self.generator.get_source_layout()
        if self.source_layout is None:
            msg = 'The generator has errors. Abort file stream generation.'
            self.add_error(msg)
        else:
            self._check_input_class('source layout', self.source_layout,
                                    TransfectionLayout)

    def __generate_column_values(self):
        """
        Generates the values for the CSV columns.
        """
        self.add_debug('Generate column value lists ...')

        for tf_pos in self.source_layout.get_sorted_working_positions():
            if tf_pos.is_empty: continue
            self.__position_values.append(tf_pos.rack_position.label)
            md_pool = str(tf_pos.molecule_design_pool)
            self.__md_pool_values.append(md_pool)
            self.__iso_concentration_values.append(tf_pos.iso_concentration)
            self.__iso_volume_values.append(tf_pos.iso_volume)

    def __generate_columns(self):
        """
        Generates the columns for the report.
        """
        position_column = CsvColumnParameters.create_csv_parameter_map(
                          self.POSITION_INDEX, self.POSITION_HEADER,
                          self.__position_values)
        md_pool_column = CsvColumnParameters.create_csv_parameter_map(
                          self.MDP_INDEX, self.MDP_HEADER,
                          self.__md_pool_values)
        iso_conc_column = CsvColumnParameters.create_csv_parameter_map(
                          self.ISO_CONCENTRATION_INDEX,
                          self.ISO_CONCENTRATION_HEADER,
                          self.__iso_concentration_values)
        iso_volume_column = CsvColumnParameters.create_csv_parameter_map(
                          self.ISO_VOLUME_INDEX, self.ISO_VOLUME_HEADER,
                          self.__iso_volume_values)
        self._column_map_list = [position_column, md_pool_column,
                                 iso_conc_column, iso_volume_column]
        self.add_info('Column generation completed.')


class ExperimentMetadataInfoWriter(TxtWriter):
    """
    Generates a stream containing the warnings and applied equation for an
    experiment metadata upload.
    """

    NAME = 'EM Upload Info Writer'

    FORMULA_TITLE = 'FORMULAS'
    FORMULA_BASE = \
'''
ISO volume and ISO concentration have been calculated by the system.\n
'''

    ISO_VOLUME_FORMULA = \
'''
The minimum ISO volume is determined using the following formula:\n
    isoVolume = ( (No(tw) * nr * transferVolume) + deadVolume) / (2 * ODF)\n
    where\n
    isoVolume - is the determined ISO volume
    No(tw) - is the total number of target wells in all cell plates (without replicates)
    nr - is the number of (interplate) replicates (here: %s)
    transferVolume - is the mastermix volume transfer into each cell plate well (%s ul)
    deadVolume* - is the deadVolume of a ISO plate well (see below)
    ODF - is the OptiMem dilution factor (3 or 4 depending on the molecule type).\n
    If the isoVolume is smaller than the allowed minimum ISO volume (%s ul)
    it is replaced by the minimum volume. The isoVolume is rounded to
    one decimal place.\n

    * The dead volume is calculated dynamically depending on the number
    of cell plate wells that obtain volumes from an ISO position. It is
    at least %s ul. For each well above %s target wells an additional
    amount of %s ul is added to the dead volume, up to a maximum dead
    volume of %s ul.\n\n
'''

    ISO_CONCENTRATION_FORMULA = \
'''
The ISO concentration is determined using the following formula:\n
    isoConcentration = finalConcentration * (RDF * CDF * ODF)\n
    where\n
    isoConcentration - the concentration ordered from the stock (in nM)
    finalConcentration - is the final concentration in the cell plate (in nM)
    RDF - is the transfection reagent dilution factor (%s)
    CDF - is the cell suspension dilution factor (%s)
    ODF - is the OptiMem dilution factor (3 or 4 depending on the molecule type).\n
    The isoConcentration is rounded to one decimal place.
'''

    MANUAL_INPUT_LINE = \
'''
There is no mastermix support for this experiment.
The ISO volumes and ISO concentrations for this metadata have been set manually.
'''


    def __init__(self, em_log, number_replicates, supports_mastermix,
                 reservoir_specs, log):
        """
        Constructor:

        :param em_log: The log of the experiment metadata generator.
        :type em_log: :class:`thelma.ThelmaLog`

        :param number_replicates: The number of replicates planned for this
            experiment design.
        :type number_replicates: :class:`int`

        :param supports_mastermix: Do the values support mastermix preparation?
        :type supports_mastermix: :class:`bool`

        :param reservoir_specs: The reservoir specs of the ISO plate.
        :type reservoir_specs:
            :class:`thelma.models.liquidtransfer.ReservoirSpecs`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        TxtWriter.__init__(self, log)

        #: The log of the experiment metadata generator.
        self.em_log = em_log
        #: The planned number of replicates.
        self.number_replicates = number_replicates

        #: Do the values support mastermix preparation?
        self.supports_mastermix = supports_mastermix

        #: The reservoir specs of the ISO plate.
        self.reservoir_specs = reservoir_specs

    def _check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self._check_input_class('log', self.em_log, ThelmaLog)
        self._check_input_class('number of replicates', self.number_replicates,
                                int)
        self._check_input_class('"supports mastermix" flag',
                                self.supports_mastermix, bool)
        self._check_input_class('ISO plate reservoir specs',
                                self.reservoir_specs, ReservoirSpecs)

        if not self.has_errors():
            errors = self.em_log.get_messages(logging.ERROR)
            if len(errors) > 0:
                msg = 'The experiment metadata generator did not complete ' \
                      'its run. Abort file stream generation.'
                self.add_error(msg)

    def _write_stream_content(self):
        """
        Writes into the streams.
        """
        if not self.has_errors():
            if self.supports_mastermix:
                self.__write_formulas()
            else:
                self._stream.write(self.MANUAL_INPUT_LINE)
            self.__write_warnings()

    def __write_formulas(self):
        """
        Write the formula explanations in the stream.
        """

        self._write_headline(self.FORMULA_TITLE, preceding_blank_lines=0,
                             trailing_blank_lines=0)
        self._stream.write(self.FORMULA_BASE)

        min_dead_volume = self.reservoir_specs.min_dead_volume \
                          * VOLUME_CONVERSION_FACTOR
        max_dead_volume = self.reservoir_specs.max_dead_volume \
                          * VOLUME_CONVERSION_FACTOR

        self._stream.write(self.ISO_VOLUME_FORMULA % (
                            self.number_replicates,
                            TransfectionParameters.TRANSFER_VOLUME,
                            TransfectionParameters.MINIMUM_ISO_VOLUME,
                            get_trimmed_string(min_dead_volume),
                            LIMIT_TARGET_WELLS, DEAD_VOLUME_COEFFICIENT,
                            get_trimmed_string(max_dead_volume)
                            ))
        self._stream.write(self.ISO_CONCENTRATION_FORMULA %
                            (TransfectionParameters.REAGENT_MM_DILUTION_FACTOR,
                             TransfectionParameters.CELL_DILUTION_FACTOR))

    def __write_warnings(self):
        """
        Writes the warnings recorded during the upload.
        """
        self._write_headline('WARNINGS')

        warnings = self.em_log.get_messages(logging.WARNING)
        if len(warnings) < 1:
            self._stream.write('no warnings')
        else:
            for msg in warnings:
                self._stream.write('%s\n' % msg)


class ExperimentMetadataInfoWriterWarningOnly(TxtWriter):
    """
    For some experiment types there are no formulas, but only warnings.

    **Return Value:** stream (TXT)
    """
    NAME = 'EM Upload Info Writer ISO-less'

    #: The header of the warning section. It also contains the metadata name.
    WARNING_TITLE = '%s - Warnings'
    #: This line is printed if there are not warnings.
    NO_WARNINGS_LINE = 'no warnings'

    def __init__(self, em_log, em_label, log):
        """
        Constructor:

        :param em_log: The log of the experiment metadata generator.
        :type em_log: :class:`thelma.ThelmaLog`

        :param em_label: The label of the experiment metadata.
        :type em_label: :class:`basestring`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        TxtWriter.__init__(self, log=log)

        #: The log of the experiment metadata generator.
        self.em_log = em_log
        #: The label of the experiment metadata.
        self.em_label = em_label

    def _check_input(self):
        self._check_input_class('log', self.em_log, ThelmaLog)
        self._check_input_class('experiment metadata label', self.em_label,
                                basestring)

    def _write_stream_content(self):
        """
        For this scenario we must only record warning (if there are any).
        """
        self._write_headline(self.WARNING_TITLE % (self.em_label),
                             preceding_blank_lines=0)

        warnings = self.em_log.get_messages(logging.WARNING)
        if len(warnings) < 1:
            self._stream.write(self.NO_WARNINGS_LINE)
        else:
            for msg in warnings:
                self._stream.write('%s\n' % msg)


class ExperimentMetadataInfoWriterLibrary(TxtWriter):
    """
    Infos for library experiments are a little different, because we
    have different formulas.

    **Return Value:** stream (TXT)
    """
    NAME = 'EM Upload Info Writer Library'

    #: The title for the general section (contains the name of the metadata).
    GENERAL_TITLE = '%s Values'
    #: Presents the robot support flag value.
    SUPPORTS_MASTERMIX_LINE = 'Robot support available: %s'
    #: Presents the name of the used library.
    LIBRARY_LINE = 'Used library: %s'
    #: Present the ISO volume of the plate (defined by the library).
    ISO_VOLUME_LINE = 'ISO volume: %s ul'
    #: Present the ISO concentration of the plate (defined by the library).
    ISO_CONCENTRATION_LINE = 'ISO concentration: %s nM'
    #: Present the final concentration of the plate.
    FINAL_CONCENTRATION_LINE = 'Final concentration: %s nM'
    #: Presents the OptiMem dilution factor of the plate (depends on the
    #: final concentration).
    ODF_LINE = 'OptiMem dilution factor: %s'
    #: Presents the reagent name for the plate.
    REAGENT_NAME_LINE = 'Tranfection reagent: %s'
    #: Presents the reagent dilution factor for the plate.
    REAGENT_DF_LINE = 'Final dilution factor of the transfection reagent: %s'

    #: The header of the warning section.
    WARNING_TITLE = 'Warnings'
    #: This line is printed if there are not warnings.
    NO_WARNINGS_LINE = 'no warnings'

    #: The header for the OptiMem dilution factor section.
    ODF_TITLE = 'Determination of the OptiMem Dilution Factor'

    ODF_FORMULA = '''
ODF = (isoConcentration / finalConcentration) / (RDF * CDF)\n
where\n
    ODF - is the OptiMem dilution factor
    isoConcentration - the concentration ordered from the stock (here: %s nM)
    finalConcentration - is the final concentration in the cell plate (here: %s nM)
    RDF - is the transfection reagent dilution factor (%i)
    CDF - is the cell suspension dilution factor (%i).\n
    The OptiMem dilution factors is rounded to one decimal place.
'''

    def __init__(self, generator, log):
        """
        Constructor:

        :param generator: The experiment metadata generator used for the
            upload.
        :type generator: :class:`ExperimentMetadataGeneratorLibrary`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        TxtWriter.__init__(self, log=log)

        #: The experiment metadata generator used for the upload.
        self.generator = generator

        #: Do the values support mastermix preparation?
        self.__support_mastermix = None
        #: The library to be screened.
        self.__library = None
        #: The parameter values (there must only be one for each parameter).
        self.__parameter_values = None

        self.__iso_conc = None
        self.__final_conc = None

    def reset(self):
        TxtWriter.reset(self)
        self.__support_mastermix = None
        self.__library = None
        self.__parameter_values = None
        self.__iso_conc = None
        self.__final_conc = None

    def _check_input(self):
        if self._check_input_class('experiment metadata generator',
                        self.generator, ExperimentMetadataGeneratorLibrary):
            if self.generator.has_errors():
                msg = 'The generator has errors!'
                self.add_error(msg)
            elif self.generator.return_value is None:
                msg = 'The generator has not run!'
                self.add_error(msg)

    def _write_stream_content(self):
        """
        We have 3 sections: general, warnings and ODF formula.
        """
        self.add_debug('Write stream content ...')

        self.__set_report_values()
        if not self.has_errors():
            self.__write_general_section()
            self.__write_warning_section()
            self.__write_formula_section()

    def __set_report_values(self):
        """
        Fetches the values from the reporter and makes sure there are not None.
        """
        msg = 'Error when trying to fetch %s from the generator (the value ' \
              'is None)! This is a programming error, please contact the ' \
              'IT department.'

        self.__library = self.generator.get_library()
        if self.__library is None:
            self.add_error(msg % ('library'))

        self.__support_mastermix = self.generator.supports_mastermix
        if self.__support_mastermix is None:
            self.add_error(msg % ('"support mastermix" flag'))

        self.__parameter_values = self.generator.get_parameter_values()
        if self.__parameter_values is None:
            self.add_error(msg % ('parameter values'))

    def __write_general_section(self):
        """
        Volume, concentration, dilution factors, etc.
        """
        header = self.GENERAL_TITLE % (self.generator.return_value.label)
        self._write_headline(header, preceding_blank_lines=0,
                             trailing_blank_lines=1)

        general_lines = []

        if self.__support_mastermix:
            robot_support = 'yes'
        else:
            robot_support = 'no'
        general_lines.append(self.SUPPORTS_MASTERMIX_LINE % robot_support)

        general_lines.append(self.LIBRARY_LINE % (self.__library.label))

        iso_vol = self.__library.final_volume * VOLUME_CONVERSION_FACTOR
        general_lines.append(self.ISO_VOLUME_LINE % (get_trimmed_string(
                                                                iso_vol)))
        self.__iso_conc = self.__library.final_concentration \
                          * CONCENTRATION_CONVERSION_FACTOR
        general_lines.append(self.ISO_CONCENTRATION_LINE \
                             % get_trimmed_string(self.__iso_conc))

        parameters = TransfectionParameters
        self.__final_conc = self.__parameter_values[
                                                parameters.FINAL_CONCENTRATION]
        general_lines.append(self.FINAL_CONCENTRATION_LINE % (
                                        get_trimmed_string(self.__final_conc)))
        odf = self.__parameter_values[parameters.OPTIMEM_DIL_FACTOR]
        general_lines.append(self.ODF_LINE % (get_trimmed_string(odf)))
        reagent_name = self.__parameter_values[parameters.REAGENT_NAME]
        general_lines.append(self.REAGENT_NAME_LINE % (reagent_name))
        reagent_df = self.__parameter_values[parameters.REAGENT_DIL_FACTOR]
        general_lines.append(self.REAGENT_DF_LINE % (
                                                get_trimmed_string(reagent_df)))

        self._write_body_lines(general_lines)

    def __write_warning_section(self):
        """
        Writes the warnings recorded during the upload.
        """
        self._write_headline(self.WARNING_TITLE)

        generator_log = self.generator.log
        warnings = generator_log.get_messages(logging.WARNING)
        if len(warnings) < 1:
            self._stream.write(self.NO_WARNINGS_LINE)
        else:
            for msg in warnings:
                self._stream.write('%s\n' % msg)

    def __write_formula_section(self):
        """
        Writes the formula for the determination of the OptiMem dilution
        factor.
        """
        self._write_headline(self.ODF_TITLE)

        formula = self.ODF_FORMULA % (get_trimmed_string(self.__iso_conc),
                            get_trimmed_string(self.__final_conc),
                            TransfectionParameters.REAGENT_MM_DILUTION_FACTOR,
                            TransfectionParameters.CELL_DILUTION_FACTOR)
        self._stream.write(formula)


class ExperimentMetadataReportUploader(BaseTracTool):
    """
    A tool that uploads the experiment metadata file, the upload info
    file and the calculation report file to the trac ticket assigned
    to the experiment metadata.

    Currently there are 4 files available to be uploaded:

        1. The uploaded excel file containing the Experiment Metadata (all
            experiment scenarios).
        2. An file containing the warnings that have been recorded during
           the uploaded and the formulas for some calculations.
        3. A CSV table giving an overview about the well assignments
           and volumes and concentrations.
        4. A CSV table presenting the data of the ISO plate.
    """

    NAME = 'Experiment Metadata Upload Reporter'

    #: The base comment for the upload.
    BASE_COMMENT = 'Experiment metadata file upload. %s'

    #: The comment addition for experiments without ISO.
    ISO_LESS_COMMENT = 'There is no ISO request for this experiment set.'

    #: The comment addition for experiments with ISO.
    ISO_COMMENT = 'The ISO volumes and concentrations have been %s'
    #: Comment addition if robot support is not available.
    ROBOT_OPTION_YES = 'You can download !BioMek worklists for the ' \
                       'transfer from the ISO into cell plates.'
    #: Comment addition if robot support is not possible.
    ROBOT_OPTION_NO = 'The system cannot generate !BioMek worklists.'
    #: Base comment completion if ISO values have been calculated.
    AUTO_OPTION = 'determined by the system or are compliant to system ' \
                  'values. %s' % (ROBOT_OPTION_YES)
    #: Base comment completion if ISO values have been inserted manually.
    MANUAL_OPTION = 'defined in the experiment metadata file. %s' \
                     % (ROBOT_OPTION_NO)
    #: Base comment completion for library experiments.
    LIBRARY_OPTION = 'set by the system according to the library values. '

    #: The description for the Excel file.
    EXCEL_DESCRIPTION = 'Experiment metadata excel file.'
    #: The description for the info file.
    INFO_DESCRIPTION = 'Experiment metadata warnings and formulas.'
    #: The description for the csv fle.
    ASSIGNMENT_DESCRIPTION = 'Experiment metadata well assignments, volumes ' \
                      'and concentrations.'
    #: The description for the ISO plate data file.
    ISO_DESCRIPTION = 'ISO Plate Overview.'
    #: The descrition for the volume file.
    VOLUME_DESCRIPTION = 'Required stock volumes.'

    #: The file name for the Excel file.
    EXCEL_FILE_NAME = '%s.xls'
    #: The file name for the info file.
    INFO_FILE_NAME = '%s_info.txt'
    #: The file name for the csv fle.
    ASSIGNMENT_FILE_NAME = '%s_assignments.csv'
    #: The file name for the ISO plate overview file.
    ISO_FILE_NAME = '%s_ISO_data.csv'

    #: The info writer class for each scenario.
    INFO_WRITER_CLS = {
        EXPERIMENT_SCENARIOS.OPTIMISATION : ExperimentMetadataInfoWriter,
        EXPERIMENT_SCENARIOS.SCREENING : ExperimentMetadataInfoWriter,
        EXPERIMENT_SCENARIOS.LIBRARY : ExperimentMetadataInfoWriterLibrary,
        EXPERIMENT_SCENARIOS.MANUAL : ExperimentMetadataInfoWriter,
        EXPERIMENT_SCENARIOS.ISO_LESS : ExperimentMetadataInfoWriterWarningOnly,
        EXPERIMENT_SCENARIOS.ORDER_ONLY :
                                        ExperimentMetadataInfoWriterWarningOnly}

    #: Experiment scenarios that get assignment files.
    ASSIGNMENT_FILE_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION]

    #: Experiment scenario that get ISO overview files.
    ISO_OVERVIEW_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION,
                              EXPERIMENT_SCENARIOS.SCREENING,
                              EXPERIMENT_SCENARIOS.MANUAL,
                              EXPERIMENT_SCENARIOS.ORDER_ONLY]

    #: Shall existing replacements with the same name be overwritten?
    REPLACE_EXISTING_ATTACHMENTS = True

    def __init__(self, generator, experiment_metadata_link, iso_request_link):
        """
        Constructor:

        :param generator: The generator that has conducted the upload.
        :type generator: :class:`ExperimentMetadataGenerator`
        :param experiment_metadata_link: Link to the experiment metadata in
            TheLMA.
        :type experiment_metadata_link: :class:`str`
        :param iso_request_link: Link to the ISO request in TheLMA.
        :type iso_request_link: :class:`str`

        """
        BaseTracTool.__init__(self, log=None, depending=False)
        #: The generator that has conducted the upload.
        self.generator = generator
        #: Link to the experiment metadata in TheLMA.
        self.experiment_metadata_link = experiment_metadata_link
        #: Link to the ISO request in TheLMA.
        self.iso_request_link = iso_request_link
        #: The ID of the :class:`ExperimentMetadataType` for the uploaded
        #: metadata.
        self.__experiment_type_id = None
        #: The comment to be sent along with the files.
        self.__comment = None
        #: A dictionary containing the requested changes (key: attribute name,
        #: value: attribute value).
        self.__description = None
        #: The file stream of the uploaded excel data.
        self.__excel_stream = None
        #: The file stream for Info TXT file.
        self.__info_stream = None
        #: The file stream for the assignment file.
        self.__assign_stream = None
        #: The file stream for ISO plate overview file.
        self.__iso_stream = None

        #: The attachment to be uploaded.
        self.__attachments = None

    def reset(self):
        """
        Resets all values except for the instantiation values.
        """
        BaseTracTool.reset(self)
        self.__experiment_type_id = None
        self.__comment = None
        self.__description = dict()
        self.__excel_stream = None
        self.__info_stream = None
        self.__assign_stream = None
        self.__attachments = []

    def send_request(self):
        """
        Runs the tool.
        """
        self.add_info('Start upload report generation ...')
        self.reset()
        self.__check_input()
        if not self.has_errors(): self.__get_streams()
        if not self.has_errors(): self.__create_description()
        if not self.has_errors(): self.__generate_comment()
        if not self.has_errors(): self.__generate_attachment_data()
        if not self.has_errors(): self.__send_attachments_and_comment()

    def __check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input values ...')
        if self._check_input_class('experiment metadata generator',
                                   self.generator,
                                   ExperimentMetadataGenerator):
            if self.generator.has_errors():
                errors = self.generator.get_messages(logging.ERROR)
                if len(errors) > 0:
                    msg = 'The experiment metadata generator did not ' \
                          'complete its run. Abort file stream generation.'
                    self.add_error(msg)

        self._check_input_class('experiment metadata link',
                                self.experiment_metadata_link, basestring)
        if not self.iso_request_link is None:
            self._check_input_class('ISO request link', self.iso_request_link,
                                    basestring)

    def __get_streams(self):
        """
        Retrieves the file streams for the report.
        """
        self.add_debug('Get file streams ...')

        self.__experiment_type_id = self.generator.SUPPORTED_EXPERIMENT_TYPE
        self.__excel_stream = self.generator.stream

        self.__write_info_stream()
        self.__write_assignment_stream()
        self.__write_iso_plate_stream()

    def __write_info_stream(self):
        """
        This files contains potential warnings and formulas.
        """
        writer_cls = self.INFO_WRITER_CLS[self.__experiment_type_id]

        if writer_cls == ExperimentMetadataInfoWriterLibrary:
            info_writer = ExperimentMetadataInfoWriterLibrary(log=self.log,
                                                    generator=self.generator)
        elif writer_cls == ExperimentMetadataInfoWriterWarningOnly:
            info_writer = ExperimentMetadataInfoWriterWarningOnly(log=self.log,
                                    em_log=self.generator.log,
                                    em_label=self.generator.return_value.label)
        else:
            iso_rs = self.generator.return_value.lab_iso_request.\
                     iso_plate_reservoir_specs
            number_replicates = self.generator.return_value.number_replicates
            info_writer = ExperimentMetadataInfoWriter(self.generator.log,
                        number_replicates=number_replicates,
                        supports_mastermix=self.generator.supports_mastermix,
                        reservoir_specs=iso_rs, log=self.log)

        self.__info_stream = info_writer.get_result()
        if self.__info_stream is None:
            msg = 'Error when trying to write info file stream!'
            self.add_error(msg)

    def __write_assignment_stream(self):
        """
        What are the ISO plate source wells for each experiment cell plate well?
        """
        if self.__experiment_type_id in self.ASSIGNMENT_FILE_SCENARIOS:
            table_writer = ExperimentMetadataAssignmentWriter(log=self.log,
                                                  generator=self.generator)
            self.__assign_stream = table_writer.get_result()
            if self.__assign_stream is None:
                msg = 'Error when trying to write assignment stream!'
                self.add_error(msg)

    def __write_iso_plate_stream(self):
        """
        The most important ISO layout parameters as CSV.
        """
        if self.__experiment_type_id in self.ISO_OVERVIEW_SCENARIOS:
            iso_writer = ExperimentMetadataIsoPlateWriter(self.generator,
                                                          self.log)
            self.__iso_stream = iso_writer.get_result()
            if self.__iso_stream is None:
                msg = 'Error when trying to write ISO plate overview!'
                self.add_error(msg)

    def __create_description(self):
        """
        Builds the :attr:`__changes` dictionary (this method assumes validated
        values).
        """
        self.add_debug('Generate ticket changes dictionary ...')

        description_builder = IsoRequestTicketDescriptionBuilder(
                    experiment_metadata=self.generator.return_value,
                    experiment_metadata_link=self.experiment_metadata_link,
                    iso_request_link=self.iso_request_link,
                    log=self.log)
        self.__description = description_builder.get_result()

        if self.__description is None:
            msg = 'Error when trying to generate ticket description.'
            self.add_error(msg)

    def __generate_comment(self):
        """
        Generates the comment to be sent along with the files.
        """
        self.add_debug('Generate comment ...')

        if self.__experiment_type_id == EXPERIMENT_SCENARIOS.ISO_LESS:
            iso_option = self.ISO_LESS_COMMENT

        else:
            if self.__experiment_type_id == EXPERIMENT_SCENARIOS.LIBRARY:
                calc_option = self.LIBRARY_OPTION
                if self.generator.supports_mastermix:
                    calc_option = calc_option + self.ROBOT_OPTION_YES
                else:
                    calc_option = calc_option + self.ROBOT_OPTION_NO
            if self.generator.supports_mastermix:
                calc_option = self.AUTO_OPTION
            else:
                calc_option = self.MANUAL_OPTION

            iso_option = self.ISO_COMMENT % (calc_option)

        self.__comment = self.BASE_COMMENT % (iso_option)

    def __generate_attachment_data(self):
        """
        Generates the AttachmentData objects for the TracAttachmentAdder.
        """
        file_data = (
            [self.__excel_stream, self.EXCEL_FILE_NAME, self.EXCEL_DESCRIPTION],
            [self.__info_stream, self.INFO_FILE_NAME, self.INFO_DESCRIPTION],
            [self.__assign_stream, self.ASSIGNMENT_FILE_NAME,
             self.ASSIGNMENT_DESCRIPTION],
            [self.__iso_stream, self.ISO_FILE_NAME, self.ISO_DESCRIPTION])

        em_label = self.generator.return_value.label
        for stream_data in file_data:
            if stream_data[0] is None: continue
            attachment = AttachmentWrapper(content=stream_data[0],
                            file_name=stream_data[1] % (em_label),
                            description=stream_data[2])
            self.__attachments.append(attachment)

    def __send_attachments_and_comment(self):
        """
        Uploads the attachments to the Trac ticket.
        """

        self.add_info('Preparations completed. Update ticket ...')

        ticket_id = self.generator.return_value.ticket_number
        self.__update_description(ticket_id)
        if not self.has_errors(): self.__send_attachments(ticket_id)

    def __update_description(self, ticket_id):
        """
        Updates the ticket description.
        """
        try:
            project_leader = self.generator.return_value.subproject.project.\
                             leader.directory_user_id
            update_wrapper = create_wrapper_for_ticket_update(
                                            ticket_id=ticket_id,
                                            description=self.__description,
                                            cc=project_leader)
            self.tractor_api.update_ticket(ticket_wrapper=update_wrapper,
                                           comment=self.__comment,
                                           notify=self.NOTIFY)
        except ProtocolError, err:
            self.add_error(err.errmsg)
        except Fault, fault:
            msg = 'Fault %s: %s' % (fault.faultCode, fault.faultString)
            self.add_error(msg)

    def __send_attachments(self, ticket_id):
        """
        Adds the ticket attachments.
        """

        file_names = []
        for attachment_wrapper in self.__attachments:
            try:
                fn = self.tractor_api.add_attachment(ticket_id=ticket_id,
                        attachment=attachment_wrapper,
                        replace_existing=self.REPLACE_EXISTING_ATTACHMENTS)
            except ProtocolError, err:
                self.add_error(err.errmsg)
                break
            except Fault, fault:
                msg = 'Fault %s: %s' % (fault.faultCode, fault.faultString)
                self.add_error(msg)
                break
            else:
                file_names.append(fn)

        if not self.has_errors():
            self.return_value = file_names
            msg = 'The experiment metadata report has been uploaded ' \
                  'successfully.'
            self.add_info(msg)
            self.was_successful = True
