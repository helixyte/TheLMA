"""
Short cuts for tools involved in lab ISO processing.
"""
from thelma.automation.tools.iso.lab.tubehandler \
    import LabIsoJobXL20WorklistGenerator
from thelma.automation.tools.iso.lab.tubehandler \
    import LabIsoXL20WorklistGenerator
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob

__docformat__ = 'reStructuredText en'

__all__ = ['get_xl20_generator']


def get_xl20_generator(entity, destination_rack_barcodes, excluded_racks=None,
                       requested_tubes=None, include_dummy_output=False,
                       logging_level=None, add_default_handlers=None):
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

    :param logging_level: the desired minimum log level
    :type logging_level: :class:`int` (or logging_level as
                     imported from :mod:`logging`)
    :default logging_level: logging.WARNING

    :param add_default_handlers: If *True* the log will automatically add
        the default handler upon instantiation.
    :type add_default_handlers: :class:`boolean`
    :default add_default_handlers: *False*
    """
    kw = dict(entity=entity, include_dummy_output=include_dummy_output,
              destination_rack_barcodes=destination_rack_barcodes,
              excluded_racks=excluded_racks, requested_tubes=requested_tubes,
              logging_level=logging_level,
              add_default_handlers=add_default_handlers)
    if isinstance(entity, LabIso):
        generator_cls = LabIsoXL20WorklistGenerator
    elif isinstance(entity, IsoJob):
        generator_cls = LabIsoJobXL20WorklistGenerator
    else:
        msg = 'The passed has an unexpected type: %s' % (entity.iso_type)
        raise TypeError(msg)

    return generator_cls(**kw)
