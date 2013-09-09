"""
Short cuts for tools involved in lab ISO processing.
"""
from thelma.automation.tools.iso.lab.processing import LabIsoJobWriterExecutor
from thelma.automation.tools.iso.lab.processing import LabIsoWriterExecutor
from thelma.automation.tools.iso.lab.base import _LabIsoInstructionsWriter
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.tools.iso.lab.tubehandler \
    import LabIsoJobXL20WorklistGenerator
from thelma.automation.tools.iso.lab.tubehandler \
    import LabIsoXL20WorklistGenerator
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob

__docformat__ = 'reStructuredText en'

__all__ = ['get_xl20_generator',
           'get_worklist_writer',
           'get_worklist_executor']


def get_xl20_generator(entity, destination_rack_barcodes, excluded_racks=None,
                       requested_tubes=None, include_dummy_output=False, **kw):
    """
    Factory method generating a XL20 worklist generator tool for the passed
    entity. The generator creates stock racks and file streams (XL20
    worklists and processing summaries and instructions).

    :param entity: The ISO or the ISO job for which to generate the files
        and the racks.
    :type entity: :class:`LabIso` or :class:`IsoJob`
        (see :attr:`_ENTITY_CLS).

    :param destination_rack_barcodes: The barcodes for the destination
        racks (the rack the tubes shall be transferred to).
    :type destination_rack_barcodes: list of barcodes (:class:`basestring`)

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

    :raises TypeError: if the entity has an unexpected class.
    """
    kw = dict(entity=entity, include_dummy_output=include_dummy_output,
              destination_rack_barcodes=destination_rack_barcodes,
              excluded_racks=excluded_racks, requested_tubes=requested_tubes,
              **kw)
    if isinstance(entity, LabIso):
        generator_cls = LabIsoXL20WorklistGenerator
    elif isinstance(entity, IsoJob):
        generator_cls = LabIsoJobXL20WorklistGenerator
    else:
        msg = 'Unexpected entity class (%s). The entity must be a %s or a %s!' \
              % (entity.__class__.__name__, LabIso.__name__, IsoJob.__name__)
        raise TypeError(msg)

    return generator_cls(**kw)


def get_worklist_writer(entity, **kw):
    """
    Factory method generating a lab ISO worklist writer
    (:class:`_LabIsoWriterExecutorTool` in printing mode) for the passed
    lab ISO or ISO job.

    :param entity: The ISO job or ISO to process.
    :type entity: :class:`thelma.models.job.IsoJob` or
        :class:`thelma.models.iso.LabIso`.

    :raises TypeError: if the entity has an unexpected class.
    """
    return __get_writer_executor(entity=entity,
                    mode=SerialWriterExecutorTool.MODE_PRINT_WORKLISTS, **kw)

def get_worklist_executor(entity, user, **kw):
    """
    Factory method generating a lab ISO worklist writer
    (:class:`_LabIsoWriterExecutorTool` in printing mode) for the passed
    lab ISO or ISO job.

    :param entity: The ISO job or ISO to process.
    :type entity: :class:`thelma.models.job.IsoJob` or
        :class:`thelma.models.iso.LabIso`.

    :param user: The user who conducts the DB update (required for
        execution mode).
    :type user: :class:`thelma.models.user.User`

    :raises TypeError: if the entity has an unexpected class.
    """
    return __get_writer_executor(entity=entity, user=user,
                        mode=SerialWriterExecutorTool.MODE_EXECUTE, **kw)

def __get_writer_executor(mode, entity, user=None, **kw):
    """
    Helper factory method creating an :class:`_LabIsoWriterExecutorTool`
    for the passed entity in the given mode.
    """
    if isinstance(entity, LabIso):
        tool_cls = LabIsoWriterExecutor
    elif isinstance(entity, IsoJob):
        tool_cls = LabIsoJobWriterExecutor
    else:
        msg = 'Unexpected entity class (%s). The entity must be a %s or a %s!' \
              % (entity.__class__.__name__, LabIso.__name__, IsoJob.__name__)
        raise TypeError(msg)

    kw.update(dict(mode=mode, entity=entity, user=user))
    return tool_cls(**kw)



