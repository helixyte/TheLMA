"""
Short cuts for tools involved in lab ISO processing.
"""
from thelma.automation.tools.iso.poolcreation.execution \
    import StockSampleCreationIsoExecutor
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationIsoGenerator
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationIsoRequestGenerator
from thelma.automation.tools.iso.poolcreation.execution \
    import StockSampleCreationStockTransferReporter
from thelma.automation.tools.iso.poolcreation.writer \
    import StockSampleCreationTicketWorklistUploader
from thelma.automation.tools.iso.poolcreation.writer \
    import StockSampleCreationIsoWorklistWriter


__docformat__ = 'reStructuredText en'

__all__ = ['get_iso_request_generator',
           'get_iso_generator',
           'get_worklist_writer',
           'get_worklist_uploader',
           'get_executor',
           'get_stock_transfer_reporter']

def get_iso_request_generator(iso_request_label, stream, requester,
                              target_volume, target_concentration, **kw):
    """
    Factory method creating an :class:`StockSampleCreationIsoRequestGenerator`.

    :param iso_request_label: Will be used as label of the
        ISO request and be part of worklist name.
    :type iso_request_label: :class:`str`

    :param stream: Excel file stream containing a sheet with the
        molecule design data.

    :param requester: This user will be the reporter and owner of the ISO
        trac tickets and requester for the ISO request. The owner of the
        request however, will be the stock management.
    :type requester: :class:`thelma.entities.user.User`

    :param target_volume: The final volume for the new pool stock tubes
        in ul.
    :type target_volume: positive integer

    :param target_concentration: The final pool concentration for the new
        pool stock tubes in nM.
    :type target_concentration: positive integer
    """
    kw.update(dict(iso_request_label=iso_request_label, stream=stream,
                   requester=requester, target_volume=target_volume,
                   target_concentration=target_concentration))
    return StockSampleCreationIsoRequestGenerator(**kw)


def get_iso_generator(iso_request, ticket_numbers=None, reporter=None, **kw):
    """
    Factory method creating a :class:`StockSampleCreationIsoGenerator` that
    generates ISOs for the passed ISO request.

    IMPORTANT: This tool must not launch warnings or be interrupted, otherwise
        some or all tickets will be created multiple times.

    :param iso_request: The ISO request for which to generate the ISOs.
    :type iso_request:
        :class:`thelma.entities.iso.StockSampleGenerationIsoRequest`

    :param ticket_numbers: The user might specify ticket numbers for the
        ISO tickets. The number of ticket number must either be 1 (in
        which case all ISOs get the same ticket number) or equal to the
        number of ISOs. If there is no ticket number specified, the
        tool will generate new tickets for each ISO.
        Attention: It is not checked whether these given tickets exist!
    :type ticket_numbers: :class:`list` of `int`
    :default ticket_numbers: *None*

    :param reporter: This user will become reporter of the tickets (if
        new tickets are created). If you do not want to create tickets,
        the user might be *None*.
    :type reporter: :class:`thelma.entities.user.User`
    :default reporter: *None*
    """
    kw.update(dict(iso_request=iso_request, ticket_numbers=ticket_numbers,
                   reporter=reporter))
    return StockSampleCreationIsoGenerator(**kw)

def get_worklist_writer(iso, single_stock_racks, pool_stock_rack_barcode,
                        use_single_source_rack=False, **kw):
    """
    Factor method creating an :class:`StockSampleCreationIsoWorklistWriter` for
    a stock sample creation ISO. The worklists can be uploaded to the
    corresponding ticket using a
    :class:`StockSampleCreationTicketWorklistUploader`. However, this needs
    to be done externally (use :func:`get_worklist_uploader` to fetch the tool).

    :param iso: The pool stock sample creation ISO for which to generate
        the worklist files.
    :type iso: :class:`thelma.entities.iso.StockSampleCreationIso`

    :param single_stock_racks: The barcodes for the destination
        racks for the single molecule design tubes (these racks have to be
        empty).
    :type single_stock_racks: list of barcodes (:class:`basestring`)

    :param pool_stock_rack_barcode: The barcodes for the new pool stock rack
        (this rack has to have empty tubes in defined positions).
    :type pool_stock_rack_barcode: :class:`basestring`

    :param use_single_source_rack: If there are only dew pools to be
        created the user might want to use a single stock rack.
    :type use_single_source_rack: :class:`bool`
    :default use_single_source_rack: *False*
    """
    kw.update(dict(iso=iso, single_stock_racks=single_stock_racks,
                   pool_stock_rack_barcode=pool_stock_rack_barcode,
                   use_single_source_rack=use_single_source_rack))
    return StockSampleCreationIsoWorklistWriter(**kw)

def get_worklist_uploader(writer, **kw):
    """
    Factory method creating a :class:`StockSampleCreationTicketWorklistUploader`.
    This tool uploads the worklists generated by a
    :class:`StockSampleCreationIsoWorklistWriter` (see :func:`get_worklist_writer`)
    to the trac ticket of the ISO.

    :param writer: The writer that has generated the files.
    :type writer: :class:`StockSampleCreationIsoWorklistWriter`
    """
    kw.update(writer=writer)
    return StockSampleCreationTicketWorklistUploader(**kw)

def get_executor(iso, user, **kw):
    """
    Factory method creating an :class:`StockSampleCreationIsoExecutor` that
    conducts the DB updates for an stock sample creation ISO. The stock transfer
    reporting tool that log the stock transfers at the trac ticket can be
    fetched with :func:`get_stock_transfer_reporter`.

    :param iso: The stock sample creation ISO for which to execute the
        worklists.
    :type iso: :class:`thelma.entities.iso.StockSampleCreationIso`

    :param user: The user conducting the execution.
    :type user: :class:`thelma.entities.user.User`
    """
    kw.update(iso=iso, user=user)
    return StockSampleCreationIsoExecutor(**kw)

def get_stock_transfer_reporter(executor, **kw):
    """
    Factory method generating a
    :class:`StockSampleCreationStockTransferReporter`. This tool logs a
    stock transfers in the Trac ticket.

    :param executor: The executor tool (after run has been completed).
    :type executor: :class:`StockSampleCreationIsoExecutor`
    """
    kw.update(executor=executor)
    return StockSampleCreationStockTransferReporter(**kw)
