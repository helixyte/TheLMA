"""
Bases classes for the generation of (planned) worklists.

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.models.liquidtransfer import PlannedWorklist


__docformat__ = "reStructuredText en"

__all__ = ['PlannedWorklistGenerator'
           ]



class PlannedWorklistGenerator(BaseAutomationTool):
    """
    This is an abstract tool generating a worklist
    (:class:`thelma.models.liquidtransfer.PlannedWorklist`).

    **Return Value**: :class:`thelma.models.liquidtransfer.PlannedWorklist`
    """

    def __init__(self, log):
        """
        Constructor:

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The planned worklist to generate
        #: (:class:`thelma.models.liquidtransfer.PlannedWorklist`).
        self._planned_worklist = None
        #: The label for the worklist (:class:`str`).
        self._label = None

    def reset(self):
        """
        Resets all values except for the input values.
        """
        BaseAutomationTool.reset(self)
        self._planned_worklist = None
        self._label = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start planned worklist generation ...')

        self._check_input()
        if not self.has_errors(): self._set_label()
        if not self.has_errors():
            self._planned_worklist = PlannedWorklist(label=self._label)
            self._create_planned_transfers()
        if not self.has_errors():
            self.return_value = self._planned_worklist
            self.add_info('Planned worklist generation completed.')

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_error('Abstract method: _check_input()')

    def _set_label(self):
        """
        Use this method to set label for the planned worklist.
        """
        self.add_error('Abstract method: _set_label()')

    def _create_planned_transfers(self):
        """
        Overwrite this method to create the planned transfer belonging to
        the worklist.
        """
        self.add_error('Abstract method: _create_planned_transfers')

    def _add_planned_transfer(self, planned_transfer):
        """
        Adds a planned transfer to the worklist.
        """
        self._planned_worklist.planned_transfers.append(planned_transfer)
