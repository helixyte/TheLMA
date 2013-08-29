"""
Short cuts for tools involved in ISO processing.
"""
from thelma.automation.tools.iso.lab.jobcreator import LabIsoJobCreator
from thelma.automation.tools.iso.poolcreation.jobcreator import \
    StockSampleCreationIsoJobCreator
from thelma.models.iso import ISO_TYPES



__docformat__ = 'reStructuredText en'

__all__ = ['get_job_creator']


def get_job_creator(iso_request, job_owner, number_isos,
                    excluded_racks=None, requested_tubes=None,
                    logging_level=None, add_default_handlers=None):
    """
    Factory method returning an :class:`IsoJobCreator` for the passed ISO
    request.

    :param iso_request: The ISO request that will take up the ISOs.
    :type iso_request: :class:`thelma.models.iso.IsoRequest` subclass

    :param job_owner: The job owner will be set as user for the ISO job.
    :type job_owner: :class:`thelma.models.user.User`

    :param number_isos: The number of ISOs ordered.
    :type number_isos: :class:`int`

    :param excluded_racks: A list of barcodes from stock racks that shall
        not be used for stock sample picking.
    :type excluded_racks: A list of rack barcodes

    :param requested_tubes: A list of barcodes from stock tubes that are
        supposed to be used.
    :type requested_tubes: A list of tube barcodes.

    :param logging_level: the desired minimum log level
    :type log_level: :class:`int` (or logging_level as
                     imported from :mod:`logging`)
    :default logging_level: *None*

    :param add_default_handlers: If *True* the log will automatically add
        the default handler upon instantiation.
    :type add_default_handlers: :class:`boolean`
    :default add_default_handlers: *None*
    """
    kw = dict(iso_request=iso_request, job_owner=job_owner,
              number_isos=number_isos, requested_tubes=requested_tubes,
              excluded_racks=excluded_racks, logging_level=logging_level,
              add_default_handlers=add_default_handlers)
    if iso_request.iso_type == ISO_TYPES.LAB:
        creator_cls = LabIsoJobCreator
    elif iso_request.iso_type == ISO_TYPES.STOCK_SAMPLE_GENERATION:
        creator_cls = StockSampleCreationIsoJobCreator
    else:
        msg = 'The ISO request has an unexpected ISO type: %s' \
               % (iso_request.iso_type)
        raise TypeError(msg)

    return creator_cls(**kw)



