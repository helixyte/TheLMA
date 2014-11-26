"""
Short cuts for tools involved in lab ISO processing.
"""
from thelma.automation.tools.iso.lab.base import _LabIsoInstructionsWriter
from thelma.automation.tools.iso.lab.processing import WriterExecutorIsoJob
from thelma.automation.tools.iso.lab.processing import WriterExecutorLabIso
from thelma.automation.tools.iso.lab.tracreporting \
    import LabIsoStockTransferReporter
from thelma.automation.tools.iso.lab.stockrack.assemble \
    import StockRackAssemblerIsoJob
from thelma.automation.tools.iso.lab.stockrack.assemble \
    import StockRackAssemblerLabIso
from thelma.automation.tools.iso.lab.stockrack.recycling \
    import StockRackRecyclerIsoJob
from thelma.automation.tools.iso.lab.stockrack.recycling \
    import StockRackRecyclerLabIso
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.entities.iso import LabIso
from thelma.entities.job import IsoJob

__docformat__ = 'reStructuredText en'

__all__ = ['get_stock_rack_assembler',
           'get_stock_rack_recyler',
           'get_worklist_writer',
           'get_worklist_executor',
           'get_stock_transfer_reporter']


def get_stock_rack_assembler(entity, rack_barcodes, excluded_racks=None,
                             requested_tubes=None, include_dummy_output=False,
                             **kw):
    """
    Factory method generating a stock rack assembler (XL20 worklist generator)
    tool for the passed entity. The generator creates stock racks and file
    streams (XL20 worklists and processing summaries and instructions) that
    allow to position tubess for a valid stock rack.

    :param entity: The ISO or the ISO job for which to generate the files
        and the racks.
    :type entity: :class:`LabIso` or :class:`IsoJob`
        (see :attr:`_ENTITY_CLS).

    :param rack_barcodes: The barcodes for the racks to be assigned
        (the rack the tubes shall be transferred to).
    :type rack_barcodes: list of barcodes (:class:`basestring`)

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
    kw.update(dict(include_dummy_output=include_dummy_output,
                   excluded_racks=excluded_racks,
                   requested_tubes=requested_tubes))
    if isinstance(entity, LabIso):
        generator_cls = StockRackAssemblerLabIso
    elif isinstance(entity, IsoJob):
        generator_cls = StockRackAssemblerIsoJob
    else:
        msg = 'Unexpected entity class (%s). The entity must be a %s or a %s!' \
              % (entity.__class__.__name__, LabIso.__name__, IsoJob.__name__)
        raise TypeError(msg)
    return generator_cls(entity, rack_barcodes, **kw)


def get_stock_rack_recyler(entity, rack_barcodes, **kw):
    """
    Factory method generating a sotck rack recycler tool for the passed entity.
    The recycler checks a set of stock racks for compatibility and assigns
    them as stock racks if the checks have been passed.

    :param entity: The ISO or the ISO job to which to assign the rack.
    :type entity: :class:`LabIso` or :class:`IsoJob`
        (see :attr:`_ENTITY_CLS).

    :param rack_barcodes: The barcodes for the racks to be assigned.
    :type rack_barcodes: list of barcodes (:class:`basestring`)

    :raises TypeError: if the entity has an unexpected class.
    """
    kw.update(dict(entity=entity, rack_barcodes=rack_barcodes))
    if isinstance(entity, LabIso):
        recycler_cls = StockRackRecyclerLabIso
    elif isinstance(entity, IsoJob):
        recycler_cls = StockRackRecyclerIsoJob
    else:
        msg = 'Unexpected entity class (%s). The entity must be a %s or a %s!' \
              % (entity.__class__.__name__, LabIso.__name__, IsoJob.__name__)
        raise TypeError(msg)

    return recycler_cls(**kw)

def get_worklist_writer(entity, **kw):
    """
    Factory method generating a lab ISO worklist writer
    (:class:`_LabIsoWriterExecutorTool` in printing mode) for the passed
    lab ISO or ISO job.

    :param entity: The ISO job or ISO to process.
    :type entity: :class:`thelma.entities.job.IsoJob` or
        :class:`thelma.entities.iso.LabIso`.

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
    :type entity: :class:`thelma.entities.job.IsoJob` or
        :class:`thelma.entities.iso.LabIso`.

    :param user: The user who conducts the DB update (required for
        execution mode).
    :type user: :class:`thelma.entities.user.User`

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
        tool_cls = WriterExecutorLabIso
        kw['iso'] = entity
    elif isinstance(entity, IsoJob):
        tool_cls = WriterExecutorIsoJob
        kw['iso_job'] = entity
    else:
        msg = 'Unexpected entity class (%s). The entity must be a %s or a %s!' \
              % (entity.__class__.__name__, LabIso.__name__, IsoJob.__name__)
        raise TypeError(msg)

    kw.update(dict(mode=mode, user=user))
    return tool_cls(**kw)


def get_stock_transfer_reporter(executor, **kw):
    """
    Factory method generating a :class:`LabIsoStockTransferReporter`. This
    tool logs stock transfers in the trac ticket.

    :param executor: The executor tool (after run has been completed).
    :type executor: :class:`_LabIsoWriterExecutorTool`
    """
    kw.update(executor=executor)
    return LabIsoStockTransferReporter(**kw)
