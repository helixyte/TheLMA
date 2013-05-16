"""
Job model classes.

AAB, Created on Jun 22, 2011
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string
from everest.entities.utils import slug_from_integer
from thelma.models.utils import get_current_user

__docformat__ = 'reStructuredText en'

__all__ = ['JOB_TYPES',
           'Job',
           'OtherJob',
           'ExperimentJob',
           'IsoJob']


class JOB_TYPES(object):
    """
    Valid job types.
    """
    OTHER = 'OTHER'
    RNAI_EXPERIMENT = 'RNAI_EXPERIMENT'
    ISO_PROCESSING = 'ISO_PROCESSING'


class JobType(Entity):
    """
    This class represents a job type, such as 'Dilution', 'Replicating' a.s.o.

    **Equality Condition**: equal :attr:`name`
    """

    #: The name of the job type.
    name = None
    #: The label of the job type.
    label = None
    # The XML description of the job's workflow.
    xml = None

    def __init__(self, name, label, xml, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.label = label
        self.xml = xml

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __eq__(self, other):
        """
        Equality operator.
        Equality is based o the :attr:`name`.
        """
        return (isinstance(other, JobType) \
                and self.name == other.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s name: %s>'
        params = (self.__class__.__name__, self.name)
        return str_format % params


class JOB_STATUS_TYPES(object):
    """
    Known job statuses.
    """
    QUEUED = 'QUEUED'
    IN_PROGRESS = 'IN_PROGRESS'
    DONE = 'DONE'
    CANCELLED = 'CANCELLED'


class Job(Entity):
    """
    This class represents a job for the laboratory.

    **Equality Condition**: equal :attr:`id`
    """

    #: The type of the job (element of :class:`JOB_TYPES`).
    type = None
    #: The (human-readable) label of this job.
    label = None
    #: May contain more detailed information.
    description = None
    #: The job type (:class:`JobType`)
    job_type = None
    #: The user this job is assigned to (:class:`thelma.models.user.User`)
    user = None
    #: The subproject this job belongs to
    #:(:class:`thelma.models.subproject.Subproject`)
    subproject = None
    #: Records the progress of the job (:class:`JOB_STATUS_TYPES`)
    status = None
    #: The time the job has been started.
    start_time = None
    #: The time the job has been finished.
    end_time = None

    def __init__(self, label, subproject, job_type, user=None,
                 description=None, status=None, start_time=None, **kw):

        Entity.__init__(self, **kw)
        self.label = label
        self.job_type = job_type
        self.user = user
        self.subproject = subproject
        self.description = description
        self.start_time = start_time
        if status == None:
            status = JOB_STATUS_TYPES.QUEUED
        self.status = status

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`id`.
        return slug_from_integer(self.id)

    @classmethod
    def create_from_data(cls, data):
        if not 'user' in data:
            user = get_current_user()
            data['user'] = user
        return cls(**data)

    def  __eq__(self, other):
        """
        Equality operator.
        Equality is based o the :attr:`id`.
        """
        return (isinstance(other, Job) \
                and self.id == other.id)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, type: %s, status: %s, ' \
                     'subproject: %s, user: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.type,
                  self.status, self.subproject, self.user)
        return str_format % params


class OtherJob(Job):
    """
    A class for jobs that neither RNAi experiment nor ISO processing jobs.

    **Equality Condition**: equal :attr:`id`
    """

    def __init__(self, label, subproject, job_type=None, user=None,
                 description=None, status=None, **kw):
        """
        Constructor
        """
        Job.__init__(self, label=label,
                     subproject=subproject,
                     job_type=job_type,
                     user=user,
                     description=description,
                     status=status,
                     **kw)
        self.type = JOB_TYPES.OTHER


# TODO: create separate job type
class ExperimentJob(Job):
    """
    This is a special type for RNAi experiments.

    **Equality Condition**: equal :attr:`id`
    """

    #: A list of ExperimentRack objects (:class:`ExperimentRack`)
    #: associated with this job.
    experiments = None

    def __init__(self, label, job_type, experiments=None, subproject=None, **kw):
        """
        Constructor
        """

        if experiments is None:
            raise ValueError('An experiment job must consist of at least ' \
                             '1 experiment!')

        if subproject is None:
            subproject = experiments[0].experiment_design.experiment_metadata.\
                               subproject
        Job.__init__(self, label=label, subproject=subproject,
                     job_type=job_type,
                     **kw)
        self.type = JOB_TYPES.RNAI_EXPERIMENT
        self.experiments = experiments


class IsoJob(Job):
    """
    This is a special job class for ISO processing jobs.

    **Equality Condition**: equal :attr:`id`
    """

    #: The ISOs belonging to this job.
    isos = []
    #: The rack containing the stock tubes for the controls that are
    #: used in this job (384-well plate ISOs only)
    #: (:class:`thelma.models.iso.IsoControlStockRack`)
    iso_control_stock_rack = None

    def __init__(self, label, job_type, isos, **kw):
        """
        Constructor
        """
        if isos is None:
            raise ValueError('An ISO job must consist of at least 1 ISO!')

        iso_request = isos[0].iso_request
        Job.__init__(self, label=label,
                     subproject=iso_request.experiment_metadata.subproject,
                     job_type=job_type,
                     **kw)
        self.type = JOB_TYPES.ISO_PROCESSING
        self.isos = isos

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

    def __eq__(self, other):
        return isinstance(other, IsoJob) and self.id == other.id

    def __len__(self):
        return len(self.isos)

    def __iter__(self):
        return iter(self.isos)

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, status: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.status)
        return str_format % params
