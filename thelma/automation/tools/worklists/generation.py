"""
Bases classes for the generation of (planned) worklists.

AAB
"""
from thelma.automation.semiconstants import get_pipetting_specs
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

    #: The name of the pipetting specs assumed for the worklist.
    PIPETTING_SPECS_NAME = None

    def __init__(self, log):
        """
        Constructor:

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The planned liquid transfers for the worklist.
        self._planned_liquid_transfers = None
        #: The label for the worklist (:class:`str`).
        self._label = None

    def reset(self):
        """
        Resets all values except for the input values.
        """
        BaseAutomationTool.reset(self)
        self._planned_liquid_transfers = []
        self._label = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start planned worklist generation ...')

        self._check_input()
        if not self.has_errors(): self._set_label()
        if not self.has_errors(): self._create_planned_liquid_transfers()
        if not self.has_errors(): transfer_type = self.__get_transfer_type()
        if not self.has_errors():
            planned_worklist = PlannedWorklist(label=self._label,
                 transfer_type=transfer_type,
                 planned_liquid_transfers=self._planned_liquid_transfers,
                 pipetting_specs=get_pipetting_specs(self.PIPETTING_SPECS_NAME))
            self.return_value = planned_worklist
            self.add_info('Planned worklist generation completed.')

    def _check_input(self):
        """
        Checks the input values.
        """
        raise NotImplementedError('Abstract method.')

    def _set_label(self):
        """
        Use this method to set label for the planned worklist.
        """
        raise NotImplementedError('Abstract method.')

    def _create_planned_liquid_transfers(self):
        """
        Overwrite this method to create the planned liquid transfer belonging to
        the worklist.
        """
        raise NotImplementedError('Abstract method.')

    def _add_planned_transfer(self, planned_transfer):
        """
        Adds a planned transfer to the worklist.
        """
        self._planned_liquid_transfers.append(planned_transfer)

    def __get_transfer_type(self):
        """
        Also makes sure that there is only one distinct transfer type.
        """
        transfer_types = set()
        for plt in self._planned_liquid_transfers:
            transfer_types.add(plt.transfer_type)

        if len(transfer_types) > 1:
            msg = 'The planned transfers for this worklist "%s" have ' \
                  'different types: %s!' % (self._label,
                   ', '.join(sorted(list(transfer_types))))
            self.add_error(msg)
            return None
        elif len(transfer_types) < 1:
            msg = 'There are no transfer types scheduled for this planned ' \
                  'worklist: %s!' % (self._label)
            self.add_error(msg)
        else:
            return list(transfer_types)[0]
