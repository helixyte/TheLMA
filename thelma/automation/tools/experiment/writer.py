"""
These tools create the BioMek robot woklist for the ISO to experiment (cell)
plate translation.

AAB
"""
from StringIO import StringIO
from thelma.automation.tools.experiment.base import ExperimentOptimisationTool
from thelma.automation.tools.experiment.base import ExperimentScreeningTool
from thelma.automation.tools.experiment.base import ExperimentTool
from thelma.automation.tools.metadata.transfection_utils \
        import TransfectionParameters
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.worklists.base import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import get_reservoir_spec
from thelma.automation.tools.worklists.biomek \
        import ContainerDilutionWorklistWriter
from thelma.automation.tools.worklists.biomek import BiomekWorklistWriter
from thelma.automation.tools.worklists.series import SeriesWorklistWriter
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.tools.writers import create_zip_archive
from thelma.automation.tools.writers import merge_csv_streams
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentWorklistWriters',
           'ExperimentWorklistWriterOptimisation',
           'ExperimentWorklistWriterScreening',
           'ReagentPreparationWriter']


class ExperimentWorklistWriters(object):
    """
    A helper class providing variables for the experiment writer classes
    and functions for the creation of reagent preparation streams.
    """

    #: The suffix for the file name of the first CSV worklist (which deals with
    #: addition of OptiMem solutions into the ISO plate). The first part of the
    #: file name will be the experiment metadata label.
    OPTI_FILE_SUFFIX = '_biomek_optimem.csv'
    #: The suffix for the file name of the first CSV worklist (which deals with
    #: addition of complex solutions into the ISO plate). The first part of the
    #: file name will be the experiment metadata label.
    REAGENT_FILE_SUFFIX = '_biomek_reagent.csv'

    #: The suffix for the file name of the reagent solution preparation file.
    #: The first part of the file name will be the experiment metadata label.
    PREPARATION_FILE_SUFFIX = '_reagent_instructions.csv'

    #: The index of the optimem worklist in the experiment design series.
    OPTIMEM_WORKLIST_INDEX = ExperimentTool.OPTIMEM_WORKLIST_INDEX
    #: The index of the optimem worklist in the experiment design series.
    REAGENT_WORKLIST_INDEX = ExperimentTool.REAGENT_WORKLIST_INDEX

    def __init__(self):
        """
        Constructor
        """
        #: The stream for the RNAi reagent preparation file.
        self._preparation_stream = None

    def _write_preparations_file(self, stream_map, log):
        """
        Writes the stream for reagent solution preparation file.
        """
        reagent_stream = stream_map[self.REAGENT_WORKLIST_INDEX]
        reagent_content = reagent_stream.read()
        reagent_stream.seek(0)

        preparation_writer = ReagentPreparationWriter(
                                    reagent_stream_content=reagent_content,
                                    log=log)
        self._preparation_stream = preparation_writer.get_result()
        if self._preparation_stream is None:
            msg = 'ExperimentWorklistWriters - Error when trying to write ' \
                  'preparation file.'
            log.add_warning(msg)

    def _create_common_zip_map(self, stream_map, experiment_label):
        """
        Creates the common part of the zip map for the zip archive (optimem,
        reagent and reagent preparation file).
        """
        zip_map = dict()

        optimem_stream = stream_map[self.OPTIMEM_WORKLIST_INDEX]
        optimem_fn = '%s%s' % (experiment_label, self.OPTI_FILE_SUFFIX)
        zip_map[optimem_fn] = optimem_stream

        reagent_stream = stream_map[self.REAGENT_WORKLIST_INDEX]
        reagent_fn = '%s%s' % (experiment_label, self.REAGENT_FILE_SUFFIX)
        zip_map[reagent_fn] = reagent_stream

        if not self._preparation_stream is None:
            prep_fn = '%s%s' % (experiment_label, self.PREPARATION_FILE_SUFFIX)
            zip_map[prep_fn] = self._preparation_stream

        return zip_map


class ExperimentWorklistWriterOptimisation(ExperimentOptimisationTool,
                                           ExperimentWorklistWriters):
    """
    Generates a zip archive containing the worklists for the preparation
    of an RNAi experiment (mastermix preparation and transfer from ISO
    to cell plate - addition of cell suspension is *not* covered).

    **Return value:** zip archive as stream
    """

    NAME = 'Experiment Biomek Worklist Writer'

    #: The suffix for the file name of the second CSV worklist (which deals with
    #: transfer of mastermix solution from ISO plate to experiment plates).
    #: The first part of the file name will be the experiment metadata label.
    TRANSFER_FILE_SUFFIX = '_biomek_transfer.csv'


    def __init__(self, experiment, log=None,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param experiment: The experiment for which to generate the BioMek
                worklists.
        :type experiment: :class:`thelma.models.experiment.Experiment`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*

        :param log: The ThelmaLog to write into (if used as part of a batch).
        :type log: :class:`thelma.ThelmaLog`
        """
        ExperimentWorklistWriters.__init__(self)
        ExperimentOptimisationTool.__init__(self, experiment=experiment,
                                logging_level=logging_level, log=log,
                                add_default_handlers=add_default_handlers)

        #: The final stream for the transfer file.
        self.__final_transfer_stream = None

        #: The transfer job for transfer part (experiment rack prepartion) -
        #: used by a series worlist writer.
        self.__transfer_jobs = None
        #: Store the worklist streams for the mastermix preparation worklists
        #: (mapped onto job indices).
        self.__stream_map = None

        #: The zip archive including content.
        self.__zip_archive = None
        #: The stream for the :attr:`__zip_archive`.
        self.__zip_stream = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        ExperimentOptimisationTool.reset(self)
        self.__transfer_jobs = []
        self.__stream_map = None
        self.__final_transfer_stream = None
        self._preparation_stream = None
        self.__zip_archive = None
        self.__zip_stream = None

    def _execute_task(self):
        """
        Executes the processes the tool is design for.
        """
        self.add_info('Preparation complete. Start BioMek worklist ' \
                      'generation ...')

        if not self.has_errors(): self._check_mastermix_compatibility()
        if not self.has_errors(): self._sort_experiment_racks()
        if not self.has_errors(): self.__write_streams()
        if not self.has_errors(): self.__create_archive()
        if not self.has_errors():
            self.return_value = self.__zip_stream
            self.add_info('BioMek worklist generation completed.')

    def _sort_experiment_racks(self):
        """
        Sorts the experiment racks for the worklists (improves the
        readability of the generated transfer worklist file).
        """
        self.add_debug('Sort experiment racks ...')

        for label, exp_rack_list in self._experiment_racks.iteritems():
            barcode_map = dict()
            for exp_rack in exp_rack_list:
                barcode_map[exp_rack.rack.barcode] = exp_rack
            barcodes = barcode_map.keys()
            barcodes.sort()
            sorted_list = []
            for barcode in barcodes: sorted_list.append(barcode_map[barcode])
            self._experiment_racks[label] = sorted_list

    def __write_streams(self):
        """
        Writes the streams for the design rack specific worklists
        (ISO to experiment plate transfer).
        """
        self.add_debug('Generate worklist files ...')

        self._create_all_transfer_jobs()
        all_transfer_streams = dict()

        if not self.has_errors():
            writer = SeriesWorklistWriter(transfer_jobs=self._transfer_jobs,
                                          log=self.log)
            self.__stream_map = writer.get_result()

        if self.__stream_map is None:
            msg = 'Error when trying to generate worklist files.'
            self.add_error(msg)
        else:
            for job_index, stream in self.__stream_map.iteritems():
                if job_index < 2: continue
                all_transfer_streams[job_index] = stream
            self.__final_transfer_stream = merge_csv_streams(
                                                        all_transfer_streams)
            self._write_preparations_file(self.__stream_map, self.log)

    def __create_archive(self):
        """
        Creates the actual zip file.
        """
        self.add_debug('Create zip archive ...')

        experiment_label = self.experiment.label.replace(' ', '_')

        self.__zip_stream = StringIO()
        zip_map = self._create_common_zip_map(self.__stream_map,
                                              experiment_label)

        transfer_fn = '%s%s' % (experiment_label, self.TRANSFER_FILE_SUFFIX)
        zip_map[transfer_fn] = self.__final_transfer_stream

        self.__zip_archive = create_zip_archive(zip_stream=self.__zip_stream,
                                                stream_map=zip_map)


class ExperimentWorklistWriterScreening(ExperimentScreeningTool,
                                        ExperimentWorklistWriters):
    """
    Generates a zip archive containing the worklists for the preparation
    of an RNAi experiment (transfer from ISO
    to cell plate - addition of cell suspension is *not* covered).

    **Return value:** zip archive as stream
    """

    NAME = 'Experiment Cybio Worklist Writer'

    #: The suffix for the file name of the second CSV worklist (which deals with
    #: transfer of mastermix solution from ISO plate to experiment plates).
    #: The first part of the file name will be the experiment metadata label.
    TRANSFER_FILE_SUFFIX = '_cybio_transfers.csv'

    def __init__(self, experiment, log=None,
                 logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param experiment: The experiment for which to generate the BioMek
                worklists.
        :type experiment: :class:`thelma.models.experiment.Experiment`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*

        :param log: The ThelmaLog to write into (if used as part of a batch).
        :type log: :class:`thelma.ThelmaLog`
        """
        ExperimentWorklistWriters.__init__(self)
        ExperimentScreeningTool.__init__(self, experiment=experiment,
                                     logging_level=logging_level, log=log,
                                     add_default_handlers=add_default_handlers)

        #: Store the worklist streams for the mastermix preparation worklists
        #: (mapped onto job indices).
        self.__stream_map = None
        #: The stream of the Cybio file.
        self.__cybio_stream = None

        #: The stream for the RNAi reagent preparation file.
        self.__preparation_stream = None

        #: The zip archive including content.
        self.__zip_archive = None
        #: The stream for the :attr:`__zip_archive`.
        self.__zip_stream = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        ExperimentScreeningTool.reset(self)
        self.__stream_map = None
        self.__cybio_stream = None
        self.__zip_archive = None
        self.__zip_stream = None
        self._preparation_stream = None

    def _execute_task(self):
        """
        Executes the processes the tool is design for.
        """
        self.add_info('Preparation complete. Start CyBio worklist ' \
                      'generation ...')

        self._check_mastermix_compatibility()
        transfer_worklist = self._get_rack_transfer_worklist()
        if not self.has_errors():
            self._create_all_transfer_jobs(transfer_worklist)
        if not self.has_errors(): self.__write_streams()
        if not self.has_errors(): self.__create_archive()
        if not self.has_errors():
            self.return_value = self.__zip_stream
            self.add_info('Worklist generation completed.')

    def __write_streams(self):
        """
        Writes the streams.
        """
        self.add_debug('Write streams ...')

        writer = SeriesWorklistWriter(log=self.log,
                                      transfer_jobs=self._transfer_jobs)
        self.__stream_map = writer.get_result()

        if self.__stream_map is None:
            msg = 'Error when trying to generate Cybio file!'
            self.add_error(msg)
        else:
            self.__cybio_stream = self.__stream_map[
                                                self._transfer_worklist_index]
            self._write_preparations_file(self.__stream_map, self.log)

    def __create_archive(self):
        """
        Creates the actual zip file.
        """
        self.add_debug('Create zip archive ...')

        self.__zip_stream = StringIO()
        experiment_label = self.experiment.label.replace(' ', '_')
        zip_map = self._create_common_zip_map(self.__stream_map,
                                              experiment_label)

        cybio_fn = '%s%s' % (experiment_label, self.TRANSFER_FILE_SUFFIX)
        zip_map[cybio_fn] = self.__cybio_stream
        self.__zip_archive = create_zip_archive(zip_stream=self.__zip_stream,
                                                stream_map=zip_map)


class ReagentPreparationWriter(CsvWriter):
    """
    This writer generates a CSV file providing a instructions about how
    to prepare the RNAi dilutions used for the second worklist (dilution
    with RNAi reagent).

    **Return Value:** file stream (CSV)
    """

    NAME = 'Reagent Preparation Writer'

    #: The header for the position column.
    POSITION_HEADER = 'Rack Position'
    #: The header for the reagent name column.
    REAGENT_NAME_HEADER = 'Reagent Name'
    #: The header for the final dilution factor column.
    FINAL_DIL_FACTOR_HEADER = 'Final Dilution Factor'
    #: The header for the initial dilution factor column.
    PREPAR_DIL_FACTOR_HEADER = 'Preparation Dilution Factor'
    #: The header for the total volume column.
    TOTAL_VOLUME_HEADER = 'Total Volume'
    #: The header for the reagent volume column.
    REAGENT_VOL_HEADER = 'Reagent Volume'
    #: The header for the diluent volume column.
    DILUENT_VOL_HEADER = 'Diluent Volume'

    #: The index for the position column.
    POSITION_INDEX = 0
    #: The index for the reagent name column.
    REAGENT_NAME_INDEX = 1
    #: The index for the final dilution factor column.
    FINAL_DIL_FACTOR_INDEX = 2
    #: The header for the initial dilution factor column.
    PREPAR_DIL_FACTOR_INDEX = 3
    #: The index for the total volume column.
    TOTAL_VOLUME_INDEX = 4
    #: The index for the reagent volume column.
    REAGENT_VOL_INDEX = 5
    #: The index for the diluent volume column.
    DILUENT_VOL_INDEX = 6

    def __init__(self, reagent_stream_content, log):
        """
        Constructor:

        :param reagent_stream_content: The content of the reagent dilution
            worklist stream.
        :type reagent_stream_content: :class:`str`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        CsvWriter.__init__(self, log=log)

        #: The content of the reagent dilution worklist stream.
        self.reagent_stream_content = reagent_stream_content

        #: The relevant data of the worklist (key: line index, values:
        #: tuple (source pos, dilution volume, diluent info) .
        self.__worklist_data = None

        #: The estimated dead volume in ul.
        self.__dead_volume = get_reservoir_spec(RESERVOIR_SPECS_NAMES.TUBE_24).\
                             max_dead_volume * VOLUME_CONVERSION_FACTOR

        #: Intermediate storage for the column values.
        self.__position_values = None
        self.__name_values = None
        self.__final_dil_factor_values = None
        self.__ini_dil_factor_values = None
        self.__total_volume_values = None
        self.__reagent_volume_values = None
        self.__diluent_volume_values = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        CsvWriter.reset(self)
        self.__worklist_data = dict()
        self.__position_values = []
        self.__name_values = []
        self.__final_dil_factor_values = []
        self.__ini_dil_factor_values = []
        self.__total_volume_values = []
        self.__reagent_volume_values = []
        self.__diluent_volume_values = []

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list`
        """
        self.__check_input()
        if not self.has_errors(): self.__get_worklist_lines()
        if not self.has_errors(): self.__generate_column_values()
        if not self.has_errors(): self.__generate_columns()

    def __check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input values ...')
        self._check_input_class('reagent dilution worklist stream',
                                self.reagent_stream_content, str)

    def __get_worklist_lines(self):
        """
        Fetches the dilution layout from the rack layout of the plan.
        """
        self.add_debug('Get worklist lines ...')

        line_counter = 0
        for wl_line in self.reagent_stream_content.split('\n'):
            line_counter += 1
            if line_counter == 1: continue # header
            wl_line.strip()
            if len(wl_line) < 1: continue
            tokens = []
            if ',' in wl_line: tokens = wl_line.split(',')
            if ';' in wl_line: tokens = wl_line.split(';')

            position = self.__extract_data_from_line_tokens(tokens,
                        BiomekWorklistWriter.SOURCE_POS_INDEX)
            volume = self.__extract_data_from_line_tokens(tokens,
                        BiomekWorklistWriter.TRANSFER_VOLUME_INDEX)
            volume = float(volume)
            dil_info = self.__extract_data_from_line_tokens(tokens,
                        ContainerDilutionWorklistWriter.DILUENT_INFO_INDEX)
            data_tuple = (position, volume, dil_info)
            self.__worklist_data[line_counter] = data_tuple

    def __extract_data_from_line_tokens(self, tokens, data_index):
        """
        Extracts a certain information from a line token.
        """
        token = tokens[data_index]
        if token.startswith('"'): token = token[1:]
        if token.endswith('"'): token = token[:-1]
        return token

    def __generate_column_values(self):
        """
        Generates the values for the CSV columns.
        """
        self.add_debug('Generate column value lists ...')

        dil_data_map = self.__get_distinct_reagent_infos()
        line_numbers = self.__worklist_data.keys()
        line_numbers.sort()
        used_dil_infos = []
        for line_number in line_numbers:
            data_tuple = self.__worklist_data[line_number]
            dil_info = data_tuple[2]
            if dil_info in used_dil_infos: continue
            used_dil_infos.append(dil_info)
            pos_label = data_tuple[0]
            total_vol = dil_data_map[dil_info]
            self.__store_line_value(dil_info, total_vol, pos_label)

    def __get_distinct_reagent_infos(self):
        """
        Gets the dilution positions for each distinct reagent name and dilution
        factor combination.
        """

        dil_data_map = dict()
        for data_tuple in self.__worklist_data.values():
            dil_info = data_tuple[2]
            volume = data_tuple[1]
            if not dil_data_map.has_key(dil_info):
                dil_data_map[dil_info] = self.__dead_volume
            dil_data_map[dil_info] += volume
        return dil_data_map

    def __store_line_value(self, dil_info, total_vol, pos_label):
        """
        Stores the values for one line.
        """

        dil_info = dil_info.strip()
        info_tokens = dil_info.split('(')
        final_dil_factor = float(info_tokens[1][:-1])
        initial_dil_factor = TransfectionParameters.\
                            calculate_initial_reagent_dilution(final_dil_factor)

        reagent_vol = round_up((total_vol / initial_dil_factor))
        total_vol = reagent_vol * initial_dil_factor
        total_vol = round(total_vol, 1)
        diluent_vol = total_vol - reagent_vol
        initial_dil_factor = round(initial_dil_factor, 1)

        self.__position_values.append(pos_label)
        self.__name_values.append(info_tokens[0])
        self.__final_dil_factor_values.append(final_dil_factor)
        self.__ini_dil_factor_values.append(initial_dil_factor)
        self.__total_volume_values.append(total_vol)
        self.__reagent_volume_values.append(reagent_vol)
        self.__diluent_volume_values.append(diluent_vol)

    def __generate_columns(self):
        """
        Generates the columns for the report.
        """
        position_column = CsvColumnParameters.create_csv_parameter_map(
                          self.POSITION_INDEX, self.POSITION_HEADER,
                          self.__position_values)
        name_column = CsvColumnParameters.create_csv_parameter_map(
                          self.REAGENT_NAME_INDEX, self.REAGENT_NAME_HEADER,
                          self.__name_values)
        final_df_column = CsvColumnParameters.create_csv_parameter_map(
                          self.FINAL_DIL_FACTOR_INDEX,
                          self.FINAL_DIL_FACTOR_HEADER,
                          self.__final_dil_factor_values)
        ini_df_column = CsvColumnParameters.create_csv_parameter_map(
                          self.PREPAR_DIL_FACTOR_INDEX,
                          self.PREPAR_DIL_FACTOR_HEADER,
                          self.__ini_dil_factor_values)
        total_vol_column = CsvColumnParameters.create_csv_parameter_map(
                          self.TOTAL_VOLUME_INDEX, self.TOTAL_VOLUME_HEADER,
                          self.__total_volume_values)
        reagent_vol_column = CsvColumnParameters.create_csv_parameter_map(
                          self.REAGENT_VOL_INDEX, self.REAGENT_VOL_HEADER,
                          self.__reagent_volume_values)
        diluent_vol_column = CsvColumnParameters.create_csv_parameter_map(
                          self.DILUENT_VOL_INDEX, self.DILUENT_VOL_HEADER,
                          self.__diluent_volume_values)
        self._column_map_list = [position_column, name_column, final_df_column,
                                 ini_df_column, total_vol_column,
                                 reagent_vol_column, diluent_vol_column]
