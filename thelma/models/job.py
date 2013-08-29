"""
Job model classes.

AAB, Created on Jun 22, 2011
"""

from everest.entities.base import Entity
from thelma.utils import get_utc_time
from thelma.models.iso import IsoJobPreparationPlate

__docformat__ = 'reStructuredText en'

__all__ = ['JOB_TYPES',
           'Job',
           'ExperimentJob',
           'IsoJob']


class JOB_TYPES(object):
    """
    Valid job types.
    """
    #: Base type.
    BASE = 'BASE'
    #: Experiment jobs contain :class:`Experiment`s that are handled together.
    #: All experiments in the job must belong to the same
    # :class:`ExperimentMetadata`.
    EXPERIMENT = 'EXPERIMENT'
    #: ISO job contain :class:`Iso`s that are processed together. There might
    #: share stock racks (e.g. for controls in screenings). All ISOs in the job
    #: must belong to the same :class:`IsoRequest`.
    ISO = 'ISO'


class Job(Entity):
    """
    Jobs group entities that represent (laboratory) tasks. Tasks belonging to
    the same job are typically conducted together in one run (physically).
    Items belonging to the same job might share properties such as a layout or
    a rack.

    There is no status tracking at the moment except for the storage of
    the creation time.

    **Equality Condition**: equal :attr:`id`
    """
    #: Defines the entity type group by this job (see :class:`JOB_TYPES`).
    job_type = None
    #: The (human-readable) label of this job.
    label = None
    #: The user this job is assigned to (:class:`thelma.models.user.User`)
    user = None
    #: A timestamp storing the time of creation.
    creation_time = None

    def __init__(self, label, user, creation_time=None, job_type=None, **kw):
        """
        Constructor
        """
        if self.__class__ is Job:
            raise NotImplementedError('Abstract class')
        Entity.__init__(self, **kw)
        if job_type is None:
            job_type = JOB_TYPES.BASE
        self.job_type = job_type
        self.label = label
        self.user = user
        if creation_time is None:
            creation_time = get_utc_time()
        self.creation_time = creation_time

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, user: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.user)
        return str_format % params


class ExperimentJob(Job):
    """
    A job class grouping :class:`Experiment` entities. All experiments must
    belong to the same :class:`ExperimentDesign`.

    **Equality Condition**: equal :attr:`id`
    """

    #: A list of ExperimentRack objects (:class:`ExperimentRack`)
    #: associated with this job.
    experiments = None

    def __init__(self, label, user, experiments, **kw):
        """
        Constructor:
        """
        if experiments is None or len(experiments) < 1:
            raise ValueError('An experiment job must consist of at least ' \
                             '1 experiment!')
        Job.__init__(self, label=label, user=user,
                     job_type=JOB_TYPES.EXPERIMENT, **kw)
        self.experiments = experiments

    def __len__(self):
        return len(self.experiments)

    def __iter__(self):
        return iter(self.experiments)


class IsoJob(Job):
    """
    A job class grouping :class:`Iso` entities. All ISOs must belong to the
    same :class:`IsoRequest`. They might share an :class:`IsoJobStockRack`
    and an :class:`IsoJobPreparationPlate`.

    **Equality Condition**: equal :attr:`id`
    """

    #: The ISOs belonging to this job.
    isos = []
    #: The maximum number if ISO stock racks for this ISO job.
    number_stock_racks = None

    #: The rack containing the stock tubes for the controls that are
    #: used in this job (not every ISO job needs some, list of
    #: :class:`thelma.models.iso.IsoJobStockRack`)
    iso_job_stock_racks = None
    #: The plates used to predilute controls before there are transferred
    #: to the ISO plates. The samples in this plate serve as source for all
    #: ISOs in this job (not every ISO job needs some, list of
    #: :class:`thelma.models.iso.IsoJobPreparationPlate`).
    iso_job_preparation_plates = None

    def __init__(self, label, user, isos, number_stock_racks, **kw):
        """
        Constructor
        """
        if isos is None or len(isos) < 1:
            raise ValueError('An ISO job must consist of at least 1 ISO!')
        Job.__init__(self, label=label, user=user, job_type=JOB_TYPES.ISO, **kw)
        self.isos = isos
        self.number_stock_racks = number_stock_racks

    @property
    def iso_request(self):
        """
        This ISO request this job belongs to.
        """
        iso_request = None
        for iso in self.isos:
            if iso_request is None:
                iso_request = iso.iso_request
            elif not iso_request == iso.iso_request:
                msg = 'Integrity Error: The ISOs of this ISO job belong to ' \
                      'different ISO requests (%s and %s).' \
                       % (iso.iso_request, iso_request)
                raise ValueError(msg)

        return iso_request

    def add_preparation_plate(self, plate, rack_layout):
        """
        Adds an :class:`IsoJobPreparationPlate`.

        :param plate: The plate to be added.
        :type plate: :class:`thelma.models.rack.Plate`

        :param rack_layout: The rack layout containing the plate data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`
        """
        IsoJobPreparationPlate(iso_job=self, rack=plate,
                               rack_layout=rack_layout)

    def __len__(self):
        return len(self.isos)

    def __iter__(self):
        return iter(self.isos)
