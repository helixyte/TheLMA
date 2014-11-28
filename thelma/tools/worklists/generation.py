"""
Bases classes for the generation of (planned) worklists.

AAB
"""
from thelma.tools.semiconstants import get_pipetting_specs
from thelma.tools.base import BaseTool
from thelma.entities.liquidtransfer import PlannedWorklist


__docformat__ = "reStructuredText en"

__all__ = ['PlannedWorklistGenerator'
           ]


class PlannedWorklistGenerator(BaseTool):
    """
    This is an abstract tool generating a worklist
    (:class:`thelma.entities.liquidtransfer.PlannedWorklist`).

    **Return Value**: :class:`thelma.entities.liquidtransfer.PlannedWorklist`
    """
    #: The name of the pipetting specs assumed for the worklist.
    PIPETTING_SPECS_NAME = None

    def __init__(self, parent=None):
        BaseTool.__init__(self, parent=parent)
        #: The planned liquid transfers for the worklist.
        self._planned_liquid_transfers = None
        #: The label for the worklist (:class:`str`).
        self._label = None

    def reset(self):
        """
        Resets all values except for the input values.
        """
        BaseTool.reset(self)
        self._planned_liquid_transfers = []
        self._label = None

    def run(self):
        self.reset()
        self.add_info('Start planned worklist generation ...')
        self._check_input()
        if not self.has_errors():
            self._set_label()
        if not self.has_errors():
            self._create_planned_liquid_transfers()
        if not self.has_errors():
            transfer_type = self.__get_transfer_type()
        if not self.has_errors():
            pipetting_specs = get_pipetting_specs(self.PIPETTING_SPECS_NAME)
            planned_worklist = \
                        PlannedWorklist(self._label,
                                        transfer_type,
                                        pipetting_specs,
                                        planned_liquid_transfers=
                                            self._planned_liquid_transfers)
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
        # Also makes sure that there is only one distinct transfer type.
        transfer_types = set()
        for plt in self._planned_liquid_transfers:
            transfer_types.add(plt.transfer_type)
        result = None
        if len(transfer_types) > 1:
            msg = 'The planned transfers for this worklist "%s" have ' \
                  'different types: %s!' % (self._label,
                   ', '.join(sorted(list(transfer_types))))
            self.add_error(msg)
        elif len(transfer_types) < 1:
            msg = 'There are no transfer types scheduled for this planned ' \
                  'worklist: %s!' % (self._label)
            self.add_error(msg)
        else:
            # Success!
            result = list(transfer_types)[0]
        return result
