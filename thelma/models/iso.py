"""
ISO request model classes

Jun 2011, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_integer
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['ISO_STATUS',
           'ISO_TYPES',
           'Iso',
           'IsoRequest',
           'IsoControlStockRack',
           'IsoSampleStockRack',
           'IsoPreparationPlate',
           'IsoAliquotPlate']


class ISO_STATUS(object):
    QUEUED = 'queued' # no transfers to far
    PREPARED = 'prepared' # contains controls
    IN_PROGRESS = 'in_progress' # contains controls and samples
    DONE = 'done' # aliquot plates are completed
    CANCELLED = 'canceled'
    REOPENED = 'reopened'


class ISO_TYPES(object):
    STANDARD = 'STANDARD'
    LIBRARY_CREATION = 'LIBRARY_CREATION'


class Iso(Entity):
    """
    ISO is the abbreviation for \'Internal Sample Order\'. An ISO
    always corresponds to one rack (source rack in terms of experiments).
    The layout for the rack to be delivered is defined by a
    :class:`IsoRequest`, whereas the actual molecule designs to insert
    are delivered from a molecule design set
    (:class:`thelma.models.moleculedesign.MoleculeDesign`; both to be
    addressed via the experiment metadata
    :class:`thelma.models.experiment.ExperimentMetadata`)

    **Equality condition**: equal :attr:`iso_request` and equal :attr:`label`
    """

    #: A (human-readable) label.
    label = None
    #: The ISO request holding the ISO rack layout for this ISO
    #: (:class:`IsoRequest`)
    iso_request = None
    #: The status of the ISO.
    status = None
    #: comma separated list of stock racks id to be ignored by the optimizer
    optimizer_excluded_racks = None
    #: comma separated list of stock racks id to be used by the optimizer
    optimizer_required_racks = None
    #: The rack layout (:class:`thelma.models.racklayout.RackLayout`)
    #: containing the information about how to set up the preparation plate.
    rack_layout = None
    #: The ISO job this ISO belongs to (:class:`IsoJob`).
    iso_job = None
    #: The ISO sample stocks rack for this ISO
    #: (set of :class:`IsoSampleStockRack`).
    iso_sample_stock_racks = None
    #: The ISO preparation plate for this ISO (:class:`IsoPreparationPlate`).
    iso_preparation_plate = None
    #: The aliquot plates for this ISO (the plates actually ordered; set of
    #: :class:`IsoAliquotPlate`).
    iso_aliquot_plates = None
    #: This set contains the molecule design pools applied to this ISO. The set
    #: is a subset of the experiment metadata or library pool set.
    molecule_design_pool_set = None

    #: The type of the ISO (see :class:`ISO_TYPES` - standard or library
    #: creation).
    iso_type = None

    #: the status the ISO is set to if no other status is specified (*queued*).
    DEFAULT_STATUS = ISO_STATUS.QUEUED

    def __init__(self, label, iso_request=None, iso_type=None,
                 status=None, molecule_design_pool_set=None,
                 optimizer_excluded_racks=None,
                 optimizer_required_racks=None,
                 rack_layout=None, iso_job=None,
                 iso_preparation_plate=None,
                 iso_sample_stock_racks=None,
                 iso_aliquot_plates=None, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.label = label
        self.iso_request = iso_request
        self.molecule_design_pool_set = molecule_design_pool_set
        if status is None:
            status = self.DEFAULT_STATUS
        self.status = status
        if iso_type is None:
            iso_type = ISO_TYPES.STANDARD
        self.iso_type = iso_type
        self.optimizer_excluded_racks = optimizer_excluded_racks
        self.optimizer_required_racks = optimizer_required_racks
        self.rack_layout = rack_layout
        self.iso_job = iso_job
        self.iso_preparation_plate = iso_preparation_plate
        if iso_aliquot_plates is None:
            iso_aliquot_plates = []
        self.iso_aliquot_plates = iso_aliquot_plates
        if iso_sample_stock_racks is None:
            iso_sample_stock_racks = []
        self.iso_sample_stock_racks = iso_sample_stock_racks

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.label)

    @property
    def control_stock_tube(self):
        """
        The control stock tube used for this ISO (assigned to the
        :attr:`iso_job`).
        """
        return self.iso_job.iso_control_stock_rack

    @property
    def preparation_plate(self):
        """
        The preparation plate.
        """
        if self.iso_preparation_plate is None:
            return None
        else:
            return self.iso_preparation_plate.plate

    @property
    def iso_aliquot_plates_plates(self):
        if self.iso_aliquot_plates is None:
            plates = None
        else:
            plates = [iap.plate for iap in self.iso_aliquot_plates]
        return plates

    def __eq__(self, other):
        return (isinstance(other, Iso) \
                and other.label == self.label \
                and other.iso_request == self.iso_request)

    def __str__(self):
        return '%s' % (self.label)

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, status: %s, ISO request: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.status,
                  self.iso_request)
        return str_format % params


class IsoRequest(Entity):
    """
    An ISO request provides all data required for the delivery of ISO racks
    (:class:`thelma.models.rack.Rack`): Plate set label, delivery date,
    requester (:class:`thelma.models.user.User`), the experiment metadata the ISO
    request belongs to (:class:`thelma.models.experiment.ExperimentMetadata`, the
    plate layout (:class:`thelma.models.racklayout.RackLayout`)
    and a list of ISOs (:class:`Iso`).
    There is one ISO request per experiment metadata that is shared by all
    ISO belonging to it.

    **Equality Condition**: equal :attr:`plate_set_label`
    """

    #: The type of the associated ISOs. One of the constants defined in
    #: :class:`ISO_TYPES`.
    iso_type = ISO_TYPES.STANDARD
    #: The ISO rack layout defining the plate positions
    #: (:class:`thelma.models.racklayout.RackLayout`).
    iso_layout = None
    #: The person making the ISO request.
    requester = None
    #: The person owning the ISO request.
    owner = None
    #: The data at which the ISO shall be delivered.
    delivery_date = None
    #: A label for the plates created due to the ISO.
    plate_set_label = None
    #: A list of the ISOs (:class:`Iso`) associated with this sample order.
    isos = []
    #: The experiment metadata
    #: (:class:`thelma.models.experiment.ExperimentMetadata`)
    #: this ISO request belongs to.
    experiment_metadata = None
    #: Number of plates to create per ISO
    number_plates = None
    #: The number of aliquot plates request for each single ISO.
    number_aliquots = None
    #: A comment (free text).
    comment = None
    #: The worklist series (:class:`thelma.models.liquidtransfer.WorklistSeries`)
    #: contains the worklists for the ISO processing.
    worklist_series = None

    def __init__(self, iso_layout, requester, number_plates=1,
                 number_aliquots=1, delivery_date=None, owner='',
                 plate_set_label='', comment='', experiment_metadata=None,
                 worklist_series=None, iso_type=ISO_TYPES.STANDARD, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.iso_layout = iso_layout
        self.requester = requester
        self.number_plates = number_plates
        self.number_aliquots = number_aliquots
        self.delivery_date = delivery_date
        self.owner = owner
        self.plate_set_label = plate_set_label
        self.comment = comment
        self.experiment_metadata = experiment_metadata
        self.worklist_series = worklist_series
        self.iso_type = iso_type

    @property
    def slug(self):
        """
        The slug for ISO requests is derived from the :attr:`id`.
        """
        return slug_from_integer(self.id)

    @property
    def iso_jobs(self):
        """
        The ISO jobs for this ISO request.
        """
        return set([iso.iso_job for iso in self.isos \
                    if not iso.iso_job is None])

    @property
    def experiment_metadata_type(self):
        """
        The experiment type of the experiment metadata.
        """
        return self.experiment_metadata.experiment_metadata_type

    def __eq__(self, other):
        return isinstance(other, IsoRequest) and other.id == self.id

    def __str__(self):
        return '%s' % (self.id)

    def __repr__(self):
        str_format = '<%s plate set label: %s, experiment metadata: %s, ' \
                     'iso layout: %s, number plates: %s, number aliquots: %s>'
        params = (self.__class__.__name__, self.plate_set_label,
                  self.experiment_metadata, self.iso_layout,
                  self.number_plates, self.number_aliquots)
        return str_format % params


class IsoControlStockRack(Entity):
    """
    This class contains the data required to generate the control samples
    of a 384-well screening ISO. It comprises the stock rack, its expected
    layout (:class:`IsoControlRackLayout`) planned worklist for the transfer
    from stock rack to the preparation plate. There is only control molecule
    designs in an ISO control stock rack.

    The stock rack is shared ISOs that belong to the job. Its rack shape is
    always 8x12.

    :Note: ISO job for 96-well plates do not have a IsoControlStockRack.

    **Equality Condition**: equal :attr:`iso_job`
    """

    #: The ISO job this ISO control stock belongs to
    #: (:class:`thelma.models.job.IsoJob`).
    iso_job = None
    #: The stock rack (:class:`thelma.models.rack.TubeRack`).
    rack = None
    #: The rack layout containing the stock rack layout data.
    rack_layout = None
    #: The worklist used to transfer volume from the stock tubes to
    #: the preparation plate
    #: (:class:`thelma.models.liquidtransfer.PlannedWorklist`).
    planned_worklist = None

    def __init__(self, iso_job, rack, rack_layout, planned_worklist, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.iso_job = iso_job
        self.rack = rack
        self.rack_layout = rack_layout
        self.planned_worklist = planned_worklist

    def __eq__(self, other):
        return isinstance(other, IsoControlStockRack) and \
                self.iso_job == other.iso_job

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, ISO job: %s, stock rack: %s>'
        params = (self.__class__.__name__, self.id, self.iso_job,
                  self.rack.barcode)
        return str_format % params


class IsoSampleStockRack(Entity):
    """
    This class represents a rack holding the stock tubes that are required
    to generate a particular ISO. ISOs for 96-well plates do only have
    one ISO sample stock rack which contains both the molecule designs for
    controls and sample. ISOs for 384-well plates might contain up to
    four ISO sample stock racks that contain molecule designs for only the
    samples (floating positions). The molecule designs for the controls
    are provided separately by the IsoControlStockRack of the ISO job of the
    ISO.
    IsoSampleStockRacks have a rack shape of 8x12.

    **Equality Condition**: equal :attr:`iso` and equal :attr:`tube_rack`
    """

    #: The ISO this sample stock rack belongs to (:class:`ISO`).
    iso = None
    #: The stock rack (:class:`thelma.models.rack.TubeRack`).
    rack = None
    #: The sector index for reformatting (transfer from 4 96-well plates
    #: to 1 384-well plate). We use Z-configuration (the sector for 96-well
    #: ISO is always 1).
    sector_index = None
    #: The worklist that has been used to transfer volume from the stock
    #: in the rack (:class:`thelma.models.liquidtransfer.PlannedWorklist`)
    planned_worklist = None

    def __init__(self, iso, rack, sector_index, planned_worklist=None,
                 **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.iso = iso
        self.rack = rack
        self.sector_index = sector_index
        self.planned_worklist = planned_worklist

    def __eq__(self, other):
        return isinstance(other, IsoSampleStockRack) and \
                self.iso == other.iso and \
                self.rack == other.rack

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, ISO: %s, tube rack: %s, sector index: %s>'
        params = (self.__class__.__name__, self.id, self.iso, self.rack.barcode,
                  self.sector_index)
        return str_format % params


class IsoPreparationPlate(Entity):
    """
    This class represents a plate serving as source plate (and sometimes
    backup) for an ISO aliquot plate.

    **Equality Condition**: equal :attr:`iso` and equal :attr:`plate`
    """

    #: The ISO this preparation plate belongs to (:class:`Iso`).
    iso = None
    #: The plate being the preparation plate (:class:`thelma.models.rack.Plate`).
    plate = None

    def __init__(self, iso, plate, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.iso = iso
        self.plate = plate

    def __eq__(self, other):
        return isinstance(other, IsoPreparationPlate) and \
                self.iso == other.iso and \
                self.plate == other.plate

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, ISO: %s, plate: %s>'
        params = (self.__class__.__name__, self.id, self.iso, self.plate)
        return str_format % params


class IsoAliquotPlate(Entity):
    """
    This class represents an official ISO plate, that is a plate that has
    been ordered from the stock management (via ISO request).

    **Equality Condition**: equal :attr:`iso` and equal :attr:`plate`
    """

    #: Marker in the plate labels of additioal
    ADDITIONAL_PLATE_MARKER = 'add_'

    #: The ISO this preparation plate belongs to (:class:`Iso`).
    iso = None
    #: The plate being the aliquot plate (:class:`thelma.models.rack.Plate`).
    plate = None

    def __init__(self, iso, plate, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.iso = iso
        self.plate = plate

    @property
    def iso_preparation_plate(self):
        """
        The ISO preparation plate this aliquot plate has been derived from.
        """
        return self.iso.iso_preparation_plate

    def __eq__(self, other):
        return (isinstance(other, IsoAliquotPlate)) and \
                self.iso == other.iso and \
                self.plate == other.plate

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, ISO: %s, plate: %s>'
        params = (self.__class__.__name__, self.id, self.iso, self.plate)
        return str_format % params
