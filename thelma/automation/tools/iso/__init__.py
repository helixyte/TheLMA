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
                    requested_library_plates=None, **kw):
    """
    Factory method returning an :class:`IsoJobCreator` for the passed ISO
    request.

    :param iso_request: The ISO request that will take up the ISOs.
    :type iso_request: :class:`thelma.models.iso.IsoRequest` subclass
    :param job_owner: The job owner will be set as user for the ISO job.
    :type job_owner: :class:`thelma.models.user.User`
    :param number_isos: The number of ISOs ordered.
    :type number_isos: :class:`int`
    :param excluded_racks: A list of barcodes from stock racks that should
        not be used as source racks for the ISO job to be created.
    :type excluded_racks: A list of rack barcodes
    :param requested_tubes: A list of barcodes from stock tubes to use for
        the ISO job to be created.
    :type requested_tubes: A list of tube barcodes.
    :param requested_library_plates: A list of barcodes from library plates
        to use for the ISO job to be created. This is only passed on if
        the request's ISO type is `ISO_TYPES.LAB`
    """
    kw = dict(iso_request=iso_request, job_owner=job_owner,
              number_isos=number_isos, requested_tubes=requested_tubes,
              excluded_racks=excluded_racks, **kw)
    if iso_request.iso_type == ISO_TYPES.LAB:
        kw['requested_library_plates'] = requested_library_plates
        creator_cls = LabIsoJobCreator
    elif iso_request.iso_type == ISO_TYPES.STOCK_SAMPLE_GENERATION:
        creator_cls = StockSampleCreationIsoJobCreator
    else:
        msg = 'The ISO request has an unexpected ISO type: %s' \
               % (iso_request.iso_type)
        raise TypeError(msg)
    return creator_cls(**kw)
