"""
Experiment model classes.

FOG Nov 26, 2010
"""
from everest.entities.base import Entity
from everest.entities.utils import get_root_aggregate
from everest.entities.utils import slug_from_string
from thelma.interfaces import IRackShape
from thelma.utils import get_utc_time

__docformat__ = "reStructuredText en"

__all__ = ['EXPERIMENT_METADATA_TYPES',
           'ExperimentMetadataType',
           'Experiment',
           'ExperimentDesign',
           'ExperimentDesignRack',
           'ExperimentRack',
           'ExperimentMetadata',
           ]


class EXPERIMENT_METADATA_TYPES(object):
    OPTI = 'OPTI'
    SCREEN = 'SCREEN'
    MANUAL = 'MANUAL'
    ISO_LESS = 'ISO-LESS'
    LIBRARY = 'LIBRARY'
    RTPCR = 'RTPCR'


class ExperimentMetadataType(Entity):
    """
    Comprises the types for experiment metadata. They define the properties
    to expect (experiment design, ISO request, etc.) and the assumptions
    for processing.
    The definitions themselves are not stored in the DB, however.

    **Equality Condition:** equal :attr:`id`
    """
    #: The display name is prettier and more descriptive than the :attr:`id`.
    display_name = None

    def __init__(self, display_name, **kw):
        Entity.__init__(self, **kw)
        self.display_name = display_name

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s display name: %s>'
        params = (self.__class__.__name__, self.id, self.display_name)
        return str_format % params


class Experiment(Entity):
    """
    The cell plate racks of an experiment are all derived from the
    same source rack. Also, they are treated in the same way
    (meaning their layouts is defined by the same
    :class:`ExperimentDesignRack`).

    **Equality Condition**: not implemented yet
            Anna:eqaul :attr:`design` and :attr:`source_rack`
    """
    #: The label of the experiment.
    label = None
    #: The properties (:class:`thelma.models.rack.RackSpecs`) of the
    #: cell plates.
    destination_rack_specs = None
    #: The source rack (:class:`thelma.models.rack.Rack`)
    #: used for this experiment.
    source_rack = None
    #: The :class:`ExperimentDesign` containing
    #: the layout information.
    experiment_design = None
    #: List of the experiment racks
    #: (:class:`ExperimentRack`; cell plate racks).
    experiment_racks = None
    #: The experiment job (:class:`thelma.models.job.ExperimentJob`) this
    #: experiment belongs to.
    job = None

    def __init__(self, label, destination_rack_specs,
                 experiment_design, source_rack=None, job=None,
                 experiment_racks=None, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.destination_rack_specs = destination_rack_specs
        self.source_rack = source_rack
        self.experiment_design = experiment_design
        self.job = job
        if experiment_racks is None:
            experiment_racks = []
        self.experiment_racks = experiment_racks

    def __eq__(self, other):
        return (isinstance(other, Experiment) \
                and other.experiment_design == self.experiment_design \
                and other.source_rack == self.source_rack)

    def __str__(self):
        return '%s' % (self.id)

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, design: %s, source rack: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.experiment_design, self.source_rack)
        return str_format % params


class ExperimentRack(Entity):
    """
    An experiment rack is a physical cell plate rack
    (:class:`thelma.models.rack.Rack`) used in an
    experiment (:class:`Experiment`).

    **Equality Condition**: not implemented yet
            Anna: equal :attr:`id`
    """
    #: The experiment (:class:`Experiment`)
    #: this rack belongs to.
    experiment = None
    #: The experiment design rack
    #: (:class:`ExperimentDesignRack`) defining the
    #: layout for this rack.
    design_rack = None
    #: The physical rack (:class:`thelma.models.rack.Rack`) being this
    #: experimental rack.
    rack = None

    def __init__(self, design_rack, rack, experiment=None, **kw):
        Entity.__init__(self, **kw)
        if experiment:
            self.experiment = experiment
        self.design_rack = design_rack
        self.rack = rack

    @classmethod
    def create_from_data(cls, data):
        # FIXME: Remove when ignore on read is available. #pylint:disable=W0511
        data.pop('source_rack', None)
        return cls(**data) # ** spylint: disable=W0142

    def __eq__(self, other):
        return (isinstance(other, ExperimentRack) \
                and other.id == self.id)

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        str_format = '<%s id: %s, rack: %s, experiment: %s, design rack: %s>'
        params = (self.__class__.__name__, self.id, self.rack, self.experiment,
                  self.design_rack.label)
        return str_format % params

    @property
    def source_rack(self):
        """
        Returns the source rack (:class:`thelma.models.rack.Rack`)
        rack is derived from.
        """
        return self.experiment.source_rack


class ExperimentDesign(Entity):
    """
    An experiment design defines all parameters for a group of
    experiments (:class:`Experiment`) belonging
    to the same subproject.

    **Equality Condition**: equal :attr:`id`
    """
    #: The domain for experiment design tags.
    DOMAIN = 'experiment_design'

    #: The shape (:class:`thelma.models.rack.RackShape`) of all
    #: experiment racks (:class:`ExperimentRack`)
    #: covered by this experiment design.
    rack_shape = None
    #: A list of the design racks (:class:`ExperimentDesignRack`)
    #: defined by this design.
    design_racks = []
    #: The experiment metadata (:class:`ExperimentMetadata`) this experiment
    #: design belongs to.
    experiment_metadata = None
    #: The worklist series containing worklists for the mastermix
    #: preparation and other non-design-rack-specific tasks
    #: (:class:`thelma.models.liquidtransfer.WorklistSeries`).
    worklist_series = None
    #: The experiments schedule for this design (:class:`Experiment`).
    experiments = []

    def __init__(self, rack_shape=None, experiment_design_racks=None,
                 worklist_series=None, **kw):
        Entity.__init__(self, **kw)
        if experiment_design_racks is None:
            experiment_design_racks = []
        self.design_racks = experiment_design_racks
        self.rack_shape = rack_shape
        self.worklist_series = worklist_series

    @property
    def experiment_metadata_type(self):
        """
        The experiment type of the experiment metadata.
        """
        return self.experiment_metadata.experiment_metadata_type

    @property
    def experiment_jobs(self):
        """
        The experiment jobs schedule for this experiment design.
        """
        experiment_jobs = set()
        for experiment in self.experiments:
            if experiment.job is None: continue
            experiment_jobs.add(experiment.job)

        return experiment_jobs

    def __eq__(self, other):
        return (isinstance(other, ExperimentDesign) \
                and other.id == self.id)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, rack shape: %s>'
        params = (self.__class__.__name__, self.id, self.rack_shape)
        return str_format % params


class ExperimentDesignRack(Entity):
    """
    An experiment design rack defines a all tag and position data
    (:class:`thelma.models.tagging.TaggedRackPositionSet`)
    instances of a cell plate rack (:class:`ExperimentRack`).
    Design racks are virtual, they do *not* exist as physical racks.

    **Equality Condition**: Anna: equal :attr:`id`
    """
    #: The ID of the object in the DB.
    id = None
    #: A label of this experiment design rack.
    label = None
    #: The layout (:class:`thelma.models.racklayout.RackLayout`),
    #: i.e. the tag-and-positions information.
    layout = None
    #: The experiment design (:class:`ExperimentDesign`) this design rack
    #: is defined by.
    experiment_design = None
    #: The worklist series containing design rack specific worklists
    #: (ISO to experiment plate transfer and cell suspension addition
    #: for non-screening cases,
    #: :class:`thelma.models.liquidtransfer.WorklistSeries`).
    worklist_series = None

    def __init__(self, label, rack_layout, experiment_design=None,
                 worklist_series=None,
                 **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.layout = rack_layout
        self.experiment_design = experiment_design
        self.worklist_series = worklist_series

    @property
    def tags(self):
        tags_dict = {}
        for tp in self.layout.tagged_rack_position_sets:
            for tag in tp.tags:
                tags_dict[tag.slug] = tag
#        tag_coll = create_staging_collection(ITag)
#        for tag in tags_dict.values():
#            tag_coll.add(tag)
        return tags_dict.values()

    def __eq__(self, other):
        return (isinstance(other, ExperimentDesignRack) \
                and other.id == self.id)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, design: %s, layout: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.experiment_design, self.layout)
        return str_format % params


class ExperimentMetadata(Entity):
    """
    The experiment metadata comprises all data required for an experiment,
    i.e. the internal sample order (:class:`thelma.models.iso.IsoRequest`), the
    experiment design (:class:`thelma.models.experiment.ExperimentDesign`),
    the target set (:class:`thelma.models.gene.TargetSet`), the molecule
    design set (:class:`thelma.models.moleculedesign.MoleculeDesign`) and
    the subproject (:class:`thelma.models.subproject.Subproject`) all this
    is related to.

    **Equality Condition**: equal :attr:`subproject` and :attr:`name`
    """

    #: The (human-readable) name of the experiment metadata.
    label = None
    #: The subproject (:class:`thelma.models.subproject.Subproject`)
    #: this experiment metadata belongs to.
    subproject = None
    #: The experiment design containing the meta data for the
    #: experiments (:class:`thelma.models.experiment.ExperimentDesign`)
    experiment_design = None
    #: The sample plan (:class:`thelma.models.iso.IsoRequest`) storing
    #: the ISO layouts.
    iso_request = None
    #: The number of replicate plates (cell plates).
    number_replicates = None
    #: The date the experiment metadata was created in the database.
    creation_date = None
    #: The number of the Trac ticket used for ISO processing.
    ticket_number = None
    #: Type of experiments to be performed with this metadata
    #: (see :class:`ExperimentMetadataType`).
    experiment_metadata_type = None
    #: The molecule design pool used to test the targets
    #: (:class:`thelma.models.moleculedesign.MoleculeDesignPoolSet`)
    molecule_design_pool_set = None

    def __init__(self, label, subproject, experiment_design,
                 number_replicates, experiment_metadata_type,
                 ticket_number=None, iso_request=None,
                 molecule_design_pool_set=None, creation_date=None,
                 **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.subproject = subproject
        self.experiment_design = experiment_design
        self.iso_request = iso_request
        self.number_replicates = number_replicates
        self.ticket_number = ticket_number
        self.molecule_design_pool_set = molecule_design_pool_set
        if creation_date is None:
            creation_date = get_utc_time()
        self.creation_date = creation_date
        self.experiment_metadata_type = experiment_metadata_type

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.label)

    @classmethod
    def create_from_data(cls, data):
        if not 'iso_request' in data:
            # We need to initialize an empty ExperimentMetadata record.
            rack_shapes_agg = get_root_aggregate(IRackShape)
            rack_shape = rack_shapes_agg.get_by_slug('8x12')
            experiment_design = ExperimentDesign(rack_shape=rack_shape)
            data['experiment_design'] = experiment_design
        return cls(**data) # ** pylint: disable=W0142

    def is_type(self, experiment_metadata_type):
        """
        Convenience method is equal to the given :class:`ExperimentMetadataType`
        or type id.

        :param experiment_metadata_type: a experiment metadata type or its id
        :type experiment_metadata_type: :class:`ExperimentMetadataType` or
            :class:`str`
        :raises TypeError: If the experiment_metadata_type is an unexpected type
        :return: :class:`bool`
        """
        if isinstance(experiment_metadata_type, ExperimentMetadataType):
            type_id = experiment_metadata_type.id
        elif isinstance(experiment_metadata_type, basestring):
            type_id = experiment_metadata_type
        else:
            msg = 'Unexpected experiment metadata type. The type must be a ' \
                  '%s or a string (obtained %s).' \
                  % (ExperimentMetadataType.__name__,
                     experiment_metadata_type.__class__.__name__)
            raise TypeError(msg)

        return (self.experiment_metadata_type.id == type_id)

    def __eq__(self, other):
        return (isinstance(other, ExperimentMetadata) \
                and self.subproject == other.subproject \
                and self.label == other.label)

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id %s, type: %s, name: %s, ticket: %s, ' \
                     'subproject: %s>'
        params = (self.__class__.__name__, self.id,
                  self.experiment_metadata_type, self.label,
                  self.ticket_number, self.subproject)
        return str_format % params
