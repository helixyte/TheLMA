"""
Tools that report to trac tool (stock transfers).

AAB
"""
from thelma.automation.tools.iso.base import StockTransferWriterExecutor
from thelma.automation.tracbase import BaseTracTool
from thelma.models.liquidtransfer import ExecutedWorklist
from tractor import AttachmentWrapper
from tractor import create_wrapper_for_ticket_update


__docformat__ = 'reStructuredText en'

__all__ = ['IsoStockTransferReporter']


class IsoStockTransferReporter(BaseTracTool):
    """
    After each stock transfer the ticket of the referring ISO request
    is updated. This tools add a log file containing information about
    the transferred samples and their sources.

    **Return Value:** The log file as stream (arg 0) and comment (arg 1)
    """
    NAME = 'ISO Stock Transfer Reporter'

    #: The expected executor class.
    EXECUTOR_CLS = StockTransferWriterExecutor

    #: The name of the log file in the ticket.
    LOG_FILE_NAME = 'stock_transfer_%s.csv'
    #: The description of the log file.
    LOF_FILE_DESCRIPTION = 'Log file for transfer of %s from stock to ' \
                           'preparation plates.'

    #: The ticket comment for the update.
    BASE_COMMENT = 'A stock transfer has been executed by %s ' \
                   '(see file: [attachment:%s]).[[br]]' \
                   "'''Entity:''' %s[[br]]" \
                   "'''Type:''' %s[[br]]" \
                   "%s.[[br]]"

    #: Shall existing replacements with the same name be overwritten?
    REPLACE_EXISTING_ATTACHMENTS = False

    def __init__(self, executor, **kw):
        """
        Constructor:

        :param executor: The executor tool (after run has been completed).
        :type executor: :class:`StockTransferWriterExecutor` subclass
        """
        BaseTracTool.__init__(self, **kw)

        #: The tool that has conducted the execution.
        self.executor = executor

        #: The executed stock transfer worklists (for reporting).
        self._executed_stock_worklists = None

        #: The stream for the log file.
        self.__log_file_stream = None
        #: The attachment for the ticket (for the log file).
        self._log_file_attachment = None

        #: The completed ticket comment.
        self._comment = None
        #: The ticket number.
        self._ticket_number = None

    def reset(self):
        BaseTracTool.reset(self)
        self._executed_stock_worklists = None
        self.__log_file_stream = None
        self._log_file_attachment = None
        self._comment = None
        self._ticket_number = None

    def send_request(self):
        self.reset()
        self.add_info('Start report generation ...')

        self.__check_input()
        if not self.has_errors(): self._fetch_executor_data()
        if not self.has_errors(): self.__generate_log_file_stream()
        if not self.has_errors(): self.__prepare()
        if not self.has_errors(): self.__submit_request()

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('executor', self.executor,
                                   self.EXECUTOR_CLS):
            if self.executor.has_errors():
                msg = 'The executor has errors! Abort file generation.'
                self.add_error(msg)
            elif self.executor.return_value is None:
                msg = 'The executor has not run yet!'
                self.add_error(msg)
            elif not self.executor.mode == self.EXECUTOR_CLS.MODE_EXECUTE:
                msg = 'The executor is not in execution mode!'
                self.add_error(msg)

    def _fetch_executor_data(self):
        """
        Fetches the executed worklists from the generator and checks the types.
        """
        self._executed_stock_worklists = \
                                    self.executor.get_executed_stock_worklists()
        self._check_input_list_classes('executed worklist',
                      self._executed_stock_worklists, ExecutedWorklist)

    def __generate_log_file_stream(self):
        """
        Generates the log file stream.
        """
        self.add_debug('Generate log file ...')

        writer = self._get_log_file_writer()
        self.__log_file_stream = writer.get_result()

        if self.__log_file_stream is None:
            msg = 'Error when trying to generate transfer log file.'
            self.add_error(msg)

    def _get_log_file_writer(self):
        """
        By default, we use the :class:`StockTransferLogFileWriter`.
        """
        raise NotImplementedError('Abstract method.')

    def __prepare(self):
        """
        Prepares the comment and the attachment and sets the ticket number.
        """
        self.add_debug('Prepare type depending data ...')

        self._set_ticket_id()
        entity_label = self.executor.entity.label
        sample_type_str = self._get_sample_type_str()
        rack_str = self._get_rack_str()

        username = self.executor.user.username
        entity = self.executor.entity

        file_name = self.LOG_FILE_NAME % (entity.label.replace(' ', '_'))
        self._log_file_attachment = AttachmentWrapper(
                    content=self.__log_file_stream, file_name=file_name,
                    description=self.LOF_FILE_DESCRIPTION % (entity.label))

        username = self.executor.user.username
        self._comment = self.BASE_COMMENT % (username, file_name, entity_label,
                                             sample_type_str, rack_str)

    def _set_ticket_id(self):
        """
        Determines the ticket ID.
        """
        raise NotImplementedError('Abstract method.')

    def _get_sample_type_str(self):
        """
        The (position) types of the transferred samples is part of the comment.
        """
        raise NotImplementedError('Abstract method.')

    def _get_rack_str(self):
        """
        The target racks for each ISO as string. The term is part of the
        comment.
        """
        raise NotImplementedError('Abstract method.')

    def __submit_request(self):
        """
        Submits the attachment and sends a comment.
        """
        self.add_info('Preparations completed. Update ticket ...')

        update_wrapper = create_wrapper_for_ticket_update(
                                            ticket_id=self._ticket_number)
        kw_update = dict(ticket_wrapper=update_wrapper, comment=self._comment,
                         notify=self.NOTIFY)
        self._submit(self.tractor_api.update_ticket, kw_update)

        kw_att = dict(ticket_id=self._ticket_number,
                      attachment=self._log_file_attachment,
                      replace_existing=self.REPLACE_EXISTING_ATTACHMENTS)
        self._submit(self.tractor_api.add_attachment, kw_att)

        if not self.has_errors():
            self.__log_file_stream.seek(0)
            self.return_value = (self.__log_file_stream, self._comment)
            self.add_info('Reports generated and submitted.')
            self.was_successful = True


