"""
ISO request entity classes.
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_integer
from everest.entities.utils import slug_from_string


__docformat__ = 'reStructuredText en'
__all__ = ['ISO_TYPES',
           'IsoRequest',
           'LabIsoRequest',
           'StockSampleCreationIsoRequest',
           'ISO_STATUS',
           'Iso',
           'LabIso',
           'StockSampleCreationIso',
           'STOCK_RACK_TYPES',
           'StockRack',
           'IsoJobStockRack',
           'IsoStockRack',
           'IsoSectorStockRack',
           'ISO_PLATE_TYPES',
           'IsoAliquotPlate',
           'IsoPreparationPlate',
           'IsoSectorPreparationPlate',
           'IsoJobPreparationPlate']


class ISO_TYPES(object):
    #: Base type
    BASE = 'BASE'
    #: Plates ordered by the lab (via experiment metadata).
    LAB = 'LAB'
    #: Generates new pool stock tubes (includes library generations)
    STOCK_SAMPLE_GENERATION = 'STOCK_SAMPLE_GEN'


class IsoRequest(Entity):
    """
    An ISO request is a task that requests solutions from the stock.
    The samples can be used for experiments or to generate new pooled samples.
    """
    #: The type of the associated ISOs. One of the constants defined in
    #: :class:`ISO_TYPES`.
    iso_type = None
    #: This label is also used for plate created in the course of this request.
    label = None
    #: The person owning the ISO request (in most cases the responsible
    #: stock manager).
    owner = None
    #: A list of the ISOs (:class:`Iso`) associated with this sample order.
    isos = []
    #: The number of ISOs (roughly: number of plates) required to deliver all
    #: samples if there no replicates or copies made.
    expected_number_isos = None
    #: The number of aliquot plates requested for each single ISO. Can be 0.
    number_aliquots = None
    #: The worklist series (:class:`thelma.entities.liquidtransfer.WorklistSeries`)
    #: contains the worklists for the ISO processing.
    worklist_series = None
    #: The pool set (:class:`thelma.entities.moleculedesign.MoleculeDesignPoolSet`)
    #: for the request is optional. The type of pools included depends on the
    #: derived class.
    molecule_design_pool_set = None

    def __init__(self, label, expected_number_isos=1, number_aliquots=1,
                 owner='', worklist_series=None, molecule_design_pool_set=None,
                 iso_type=None, **kw):
        if self.__class__ is IsoRequest:
            raise NotImplementedError('Abstract class')
        Entity.__init__(self, **kw)
        if iso_type is None:
            iso_type = ISO_TYPES.BASE
        self.iso_type = iso_type
        self.label = label
        self.expected_number_isos = expected_number_isos
        self.number_aliquots = number_aliquots
        self.owner = owner
        self.worklist_series = worklist_series
        self.molecule_design_pool_set = molecule_design_pool_set

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

    def __str__(self):
        return '%s' % (self.id)

    def __repr__(self):
        str_format = '<%s label: %s, owner: %s, expected number of ISOs: ' \
                     '%s, number of aliquots: %s>'
        params = (self.__class__.__name__, self.label, self.owner,
                  self.expected_number_isos, self.number_aliquots)
        return str_format % params


class LabIsoRequest(IsoRequest):
    """
    Lab ISO request are orders made by the lab to conduct experiments.

    The :attr:`molecule_design_pool_set` contains only pools for floating
    positions.
    If there is a :attr:`molecule_design_library` attached to the ISO request,
    the ISO request deals with the completion of the library plates in order
    to conduct experiments.
    """
    #: The person requesting the soultions.
    requester = None
    #: The experiment metadata
    #: (:class:`thelma.entities.experiment.ExperimentMetadata`)
    #: this lab ISO request belongs to.
    experiment_metadata = None
    #: The ISO rack layout (:class:`thelma.entities.racklayout.RackLayout`,
    #: working layout type: :class:`TransfectionLayout`) contains data about
    #: the plate positions. The data applies to all ISOs.
    rack_layout = None
    #: The data at which the ISOs shall be delivered.
    delivery_date = None
    #: A comment made by the requester (free text, optional).
    comment = None
    #: The reservoir specs for the plates to be generated
    #: (:attr:`iso_aliquot_plates` of the :class:`Iso`) define the volume
    #: properties for the plates (important for calculations,
    #: :class:`thelma.entities.liquidtransfer.ReservoirSpecs`).
    iso_plate_reservoir_specs = None
    #: Shall the ISO job be processed first (before the ISO-specific
    #: preparations?). Default: True. If there is no ISO job processing this
    #: value is ignored.
    process_job_first = None
    #: The molecule design library whose plates are used for this ISO request
    #: (:class:`thelma.entities.library.MoleculeDesignLibrary`, optional).
    molecule_design_library = None

    def __init__(self, label, requester, rack_layout, delivery_date=None,
                 comment=None, experiment_metadata=None,
                 process_job_first=True, iso_plate_reservoir_specs=None,
                 molecule_design_library=None, **kw):
        """
        Constructor.
        """
        IsoRequest.__init__(self, label=label, iso_type=ISO_TYPES.LAB, **kw)
        self.requester = requester
        self.rack_layout = rack_layout
        self.delivery_date = delivery_date
        self.comment = comment
        self.experiment_metadata = experiment_metadata
        self.iso_plate_reservoir_specs = iso_plate_reservoir_specs
        self.process_job_first = process_job_first
        self.molecule_design_library = molecule_design_library

    @property
    def experiment_metadata_type(self):
        """
        The experiment type of the experiment metadata.
        """
        return self.experiment_metadata.experiment_metadata_type

    @property
    def has_library(self):
        return not self.molecule_design_library is None


class StockSampleCreationIsoRequest(IsoRequest):
    """
    Stock sample creation ISO request serve the generation of pooled stock
    solutions from existing (single design) stock samples.

    The :attr:`molecule_design_pool_set` contains only (multi-design) pools
    whose stock samples are to be generated.
    If there is a :attr:`molecule_design_library` attached to the ISO request,
    the ISO request serves the creation of this library.
    """
    #: Volume for each new stock sample to be generated in l.
    stock_volume = None
    #: Concentration for each new stock sample to be generated in M.
    stock_concentration = None
    #: Volume of the preparation plate in l if this is a library creation
    #: ISO request.
    preparation_plate_volume = None
    #: The number of single molecule designs each new pool will consist of.
    number_designs = None
    #: The molecule design library created with this ISO request
    #: (:class:`thelma.entities.library.MoleculeDesignLibrary`, optional).
    molecule_design_library = None

    def __init__(self, label, stock_volume, stock_concentration,
                 preparation_plate_volume, number_designs,
                 molecule_design_library=None, **kw):
        IsoRequest.__init__(self, label,
                            iso_type=ISO_TYPES.STOCK_SAMPLE_GENERATION, **kw)
        self.stock_volume = stock_volume
        self.stock_concentration = stock_concentration
        self.preparation_plate_volume = preparation_plate_volume
        self.number_designs = number_designs
        self.molecule_design_library = molecule_design_library

    def __repr__(self):
        str_format = '<%s label: %s, owner: %s, number designs: %s, stock ' \
                     'volume: %s, stock concentration: %s, expected number ' \
                     'of ISOs: %s, number of aliquots: %s>'
        params = (self.__class__.__name__, self.label, self.owner,
                  self.number_designs, self.stock_volume,
                  self.stock_concentration, self.expected_number_isos,
                  self.number_aliquots)
        return str_format % params


class ISO_STATUS(object):
    """
    These status apply mainly to ISOs that also generate plates.
    """
    #: no transfers to far
    QUEUED = 'queued'
    #: DEPRECATED: contains controls
    PREPARED = 'prepared'
    #: ISO or ISO job have already been processed but the other entity has not
    IN_PROGRESS = 'in_progress'
    #: aliquot plates are completed
    DONE = 'done'
    #: aborted ISOs cannot be reopened
    CANCELLED = 'canceled'
    #: you can reopened to create further aliquots (only some cases)
    REOPENED = 'reopened'


class Iso(Entity):
    """
    Abstract base class for ISOs.

    ISO is the abbreviation for \'Internal Sample Order\'. An ISO
    always results in the generation of rack having sample with defined
    volumes and concentrations in defined positions. This can be a source
    plate for an experiment or new sample stock racks. If the resulting rack
    is a plate it is possible to deliver several aliquots.

    An ISO is always connected to an :class:`IsoRequest`. The ISO request
    contains general data that applies to all ISOs it contains. In contrast,
    an ISO focuses on the data specific for the rack to be created and on
    information required to track and facilitate the (physical) processing.
    """
    #: The type of the ISO (see :class:`ISO_TYPES` - lab or stock sample
    #: creation).
    iso_type = None
    #: A (human-readable) label, this usually contains a running number
    #: within the :class:`IsoRequest`.
    label = None
    #: The status of the ISO is used to determine which next steps are allowed.
    status = None
    #: The ISO request holding general data for this ISO (:class:`IsoRequest`).
    iso_request = None
    #: The rack layout (:class:`thelma.entities.racklayout.RackLayout`)
    #: containing specific information for the rack to be created. The structure
    #: of the layout depends on the :class:`iso_type`.
    rack_layout = None
    #: The ISO job this ISO belongs to (:class:`IsoJob`).
    iso_job = None
    #: The maximum number if ISO stock racks (all ISO types) for this ISO.
    number_stock_racks = None
    #: The ISO stocks rack for this ISO (set of :class:`IsoStockRack`) provide
    #: samples that are only used in the processing of this ISO and not by
    #: other ISOs in the same :attr:`iso_job`.
    iso_stock_racks = None
    #: The ISO stocks rack for this ISO (set of :class:`IsoSectorStockRack`)
    #: provide samples that are only used in the processing of a certain sector
    #: of this ISO and not by other ISOs in the same :attr:`iso_job`.
    iso_sector_stock_racks = None
    #: These plates are used to pre-dilute samples, they are not passed
    #: to the lab (list of :class:`IsoPreparationPlate`).
    iso_preparation_plates = None
    #: These are the actual final plates this ISO was meant to create
    #: (list of :class:`IsoAliquotPlate`).
    iso_aliquot_plates = None
    #: This set contains the molecule design pools specific to this ISO. The set
    #: is a subset of the :attr:`iso_request` pool set.
    molecule_design_pool_set = None
    #: comma separated list of stock racks id to be ignored by the optimizer
    # FIXME: The optimizer parameters should actually be part of the ISO job.
    optimizer_excluded_racks = None
    #: comma separated list of stock tube barcodes to be used by the optimizer
    optimizer_requested_tubes = None
    #: the status the ISO is set to if no other status is specified (*queued*).
    DEFAULT_STATUS = ISO_STATUS.QUEUED

    def __init__(self, label, number_stock_racks, rack_layout,
                 iso_request=None,
                 status=None, molecule_design_pool_set=None,
                 optimizer_excluded_racks=None,
                 optimizer_requested_tubes=None, iso_job=None,
                 iso_stock_racks=None, iso_sector_stock_racks=None,
                 iso_preparation_plates=None, iso_aliquot_plates=None,
                 iso_type=None, **kw):
        if self.__class__ is Iso:
            raise NotImplementedError('Abstract class')
        Entity.__init__(self, **kw)
        if iso_type is None:
            iso_type = ISO_TYPES.BASE
        self.iso_type = iso_type
        self.label = label
        self.number_stock_racks = number_stock_racks
        if status is None:
            status = self.DEFAULT_STATUS
        self.status = status
        self.iso_request = iso_request
        self.rack_layout = rack_layout
        self.iso_job = iso_job
        if iso_stock_racks is None:
            iso_stock_racks = []
        self.iso_stock_racks = iso_stock_racks
        if iso_sector_stock_racks is None:
            iso_sector_stock_racks = []
        self.iso_sector_stock_racks = iso_sector_stock_racks
        if iso_preparation_plates is None:
            iso_preparation_plates = []
        self.iso_preparation_plates = iso_preparation_plates
        if iso_aliquot_plates is None:
            iso_aliquot_plates = []
        self.iso_aliquot_plates = iso_aliquot_plates
        self.molecule_design_pool_set = molecule_design_pool_set
        self.optimizer_excluded_racks = optimizer_excluded_racks
        self.optimizer_requested_tubes = optimizer_requested_tubes

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.label)

    @property
    def iso_job_stock_rack(self):
        """
        The ISO job stock tube used for this ISO (assigned to the
        :attr:`iso_job`).
        """
        if self.iso_job is None:
            result = None
        else:
            result = self.iso_job.iso_job_stock_rack
        return result

    @property
    def stock_racks(self):
        """
        Read only access to the stock racks of this ISO. Returns a list
        of IsoStockRack or IsoSectorStockRack instances.
        """
        return self.iso_stock_racks + self.iso_sector_stock_racks

    @property
    def preparation_plates(self):
        """
        Read only access to the racks of the preparation plates in this ISO.
        """
        return [ipp.rack for ipp in self.iso_preparation_plates]

    @property
    def aliquot_plates(self):
        """
        Read only access to the racks of the aliquot plates in this ISO.
        """
        return [iaq.rack for iaq in self.iso_aliquot_plates]

    def add_aliquot_plate(self, plate):
        """
        Adds an :class:`IsoAliquotPlate`.

        :param plate: The plate to be added.
        :type plate: :class:`thelma.entities.rack.Plate`
        """
        iap = IsoAliquotPlate(None, plate)
        self.iso_aliquot_plates.append(iap)

    def add_preparation_plate(self, plate, rack_layout):
        """
        Adds an :class:`IsoPreparationPlate`.

        :param plate: The plate to be added.
        :type plate: :class:`thelma.entities.rack.Plate`
        :param rack_layout: The rack layout containing the plate data.
        :type rack_layout: :class:`thelma.entities.racklayout.RackLayout`
        """
        ipp = IsoPreparationPlate(None, plate, rack_layout)
        self.iso_preparation_plates.append(ipp)

    def __eq__(self, other):
        """
        Equality is based on the iso_request and label attributes.
        """
        return (isinstance(other, Iso) \
                and other.label == self.label \
                and other.iso_request == self.iso_request)

    def __str__(self):
        return '%s' % (self.label)

    def __repr__(self):
        str_format = '<%s, label: %s, status: %s>'
        params = (self.__class__.__name__, self.label, self.status)
        return str_format % params


class LabIso(Iso):
    """
    This special kind of :class:`Iso` generates plates for experiments in the
    lab.

    The :attr:`rack_layout` is a :class:IsoPlateLayout`,
    the :attr:`molecule_design_pool_set` is optional an only contains pools
    specific to this ISOs (floating position pools).
    """
    #: In case of library ISOs we use pre-existing library plates instead of
    #: creating aliquot plates (:class:`thelma.entities.library.LibraryPlate`).
    library_plates = None
    #: A list of requested library plate barcodes if this is a library ISO.
    # FIXME: Like the optimizer parameters, this should actually be part of
    #        the ISO job.
    requested_library_plates = None

    def __init__(self, label, number_stock_racks, rack_layout,
                 requested_library_plates=None, **kw):
        """
        Constructor
        """
        Iso.__init__(self, label, number_stock_racks, rack_layout,
                     iso_type=ISO_TYPES.LAB, **kw)
        self.library_plates = []
        self.requested_library_plates = requested_library_plates

    @property
    def final_plates(self):
        """
        Returns either the ISO aliquot or the library plates assigned to this
        ISO (depending on what sort of plates is associated with this ISO,
        library plates are tried first).
        """
        if len(self.library_plates) > 0:
            result = self.library_plates
        else:
            result = self.iso_aliquot_plates
        return result


class StockSampleCreationIso(Iso):
    """
    Specialized ISO for creating new (pooled) stock samples (in tube racks).

    The rack layout is a :class:`StockSampleCreationLayout` and contains
    the pools that are generated by this ISO.
    """
    #: The number of the Trac ticket.
    ticket_number = None
    #: The number of the layout this ISO deals with (a running number
    #: within the ISO request).
    layout_number = None
    #: The sector preparations plates for this ISO if this is a library
    #: creation ISO.
    iso_sector_preparation_plates = None

    def __init__(self, label, number_stock_racks, rack_layout, ticket_number,
                 layout_number, iso_sector_preparation_plates=None, **kw):
        Iso.__init__(self, label, number_stock_racks, rack_layout,
                     iso_type=ISO_TYPES.STOCK_SAMPLE_GENERATION, **kw)
        self.ticket_number = ticket_number
        self.layout_number = layout_number
        if iso_sector_preparation_plates is None:
            iso_sector_preparation_plates = []
        self.iso_sector_preparation_plates = iso_sector_preparation_plates

    def add_sector_preparation_plate(self, plate, sector_index, rack_layout):
        """
        Adds a :class:`IsoSectorPreparationPlate`.

        :param plate: The plate to be added.
        :type plate: :class:`thelma.entities.rack.Plate`
        :param rack_layout: The rack layout containing the plate data.
        :type rack_layout: :class:`thelma.entities.racklayout.RackLayout`
        :param int sector_index: Sector index for this sector preparation
            plate.
        """
        ispp = IsoSectorPreparationPlate(None, plate, sector_index,
                                         rack_layout)
        self.iso_sector_preparation_plates.append(ispp)

    def __eq__(self, other):
        """
        Equalithy is based on the iso_request, label, and layout_number
        attributes.
        """
        return Iso.__eq__(self, other) and \
            other.layout_number == self.layout_number

    def __repr__(self):
        str_format = '<%s, label: %s, ticket number: %i, ' \
                     'layout_number: %i, status: %s>'
        params = (self.__class__.__name__, self.label,
                  self.ticket_number, self.layout_number, self.status)
        return str_format % params


class STOCK_RACK_TYPES(object):
    #: base class
    STOCK_RACK = 'STOCK_RACK'
    #: for samples shared by all ISOs of an ISO job
    ISO_JOB = 'ISO_JOB'
    #: for samples specific to an ISO
    ISO = 'ISO'
    #: for samples specific to an a particular ISO quadrant
    SECTOR = 'SECTOR'


class StockRack(Entity):
    """
    This is a base class for stock rack used for ISO processing. Since the
    tubes in the racks can be moved the samples in the rack have to be checked
    before usage.
    """
    #: The type of the stock rack (see :class:`STOCK_RACK_TYPES`).
    stock_rack_type = None
    #: The label of the stock rack entity is not equal to the rack label.
    #: The entity label contains data that is parsed for ISO processing.
    label = None
    #: The stock rack (:class:`thelma.entities.rack.TubeRack`).
    rack = None
    #: The rack layout containing the molecule design pool and transfer data
    #: (:class:`StockRackLayout`).
    rack_layout = None
    #: The series (:class:`thelma.entities.liquidtransfer.WorklistSeries`)
    #: used to transfer volumes from the stock tubes to a target container -
    #: the worklists are always a :class:`SAMPLE TRANSFER` types even if we
    #: use a CyBio, because tubes in stock racks can move and the rack state
    #: after the transfers might change.
    worklist_series = None

    def __init__(self, label, rack, rack_layout, worklist_series,
                 stock_rack_type=None, **kw):
        if self.__class__ is StockRack:
            raise NotImplementedError('Abstract class')
        Entity.__init__(self, **kw)
        if stock_rack_type is None:
            stock_rack_type = STOCK_RACK_TYPES.STOCK_RACK
        self.stock_rack_type = stock_rack_type
        self.label = label
        self.rack = rack
        self.rack_layout = rack_layout
        self.worklist_series = worklist_series

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, rack: %s>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.rack.barcode)
        return str_format % params


class IsoJobStockRack(StockRack):
    """
    This is a special :class:`StockRack` for an :class:`IsoJob`.
    It contains samples that are passed to all ISOs of an ISO job (such
    as controls for a screening or library screening ISOs).
    """
    #: The ISO job this rack belongs to (:class:`thelma.entities.job.IsoJob`).
    iso_job = None

    def __init__(self, iso_job, label, rack, rack_layout, worklist_series,
                 **kw):
        StockRack.__init__(self, label, rack, rack_layout, worklist_series,
                           stock_rack_type=STOCK_RACK_TYPES.ISO_JOB, **kw)
        self.iso_job = iso_job

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, ISO job: %s, rack: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.iso_job,
                  self.rack.barcode)
        return str_format % params


class IsoStockRack(StockRack):
    """
    This is a special :class:`StockRack` for an :class:`Iso`.
    It contains samples that are specific to a certain ISO (as opposed to
    samples that are shared by all ISOs of an ISO job).
    There can be several ISO stock racks for an ISO.
    """
    #: The ISO this stock rack belongs to (:class:`Iso`).
    iso = None

    def __init__(self, iso, label, rack, rack_layout, worklist_series, **kw):
        StockRack.__init__(self, label, rack, rack_layout, worklist_series,
                           stock_rack_type=STOCK_RACK_TYPES.ISO, **kw)
        self.iso = iso

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, ISO: %s, rack: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.iso,
                  self.rack.barcode)
        return str_format % params


class IsoSectorStockRack(StockRack):
    """
    This is a special :class:`StockRack` (actually even ISO stock rack, but
    SQLalchemy does not support nested inheritance)for samples that a
    associated with a certain sector (quadrant) of an ISO rack. Typically,
    this is linked to the usage of the CyBio robot.
    Sector indices are 0-based.

    Sectors a listed in Z-configuration, e.g. : ::

    0 1
    2 3
    """
    #: The ISO this stock rack belongs to (:class:`Iso`).
    iso = None
    #: The sector index this stock rack is responsible for (0-based).
    sector_index = None

    def __init__(self, iso, sector_index, label, rack, rack_layout,
                 worklist_series, **kw):
        StockRack.__init__(self, label, rack, rack_layout, worklist_series,
                           stock_rack_type=STOCK_RACK_TYPES.SECTOR, **kw)
        self.iso = iso
        self.sector_index = sector_index

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, ISO: %s, rack: %s, ' \
                     'sector index: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.iso,
                  self.rack.barcode, self.sector_index)
        return str_format % params


class ISO_PLATE_TYPES(object):
    #: base class
    ISO_PLATE = 'ISO_PLATE'
    #: the plates passed to the lab (might be replicates)
    ALIQUOT = 'ALIQUOT'
    # intermediate plate for pre-dilutions (optional)
    PREPARATION = 'PREPARATION'
    #: A preparation plate for a particular sector (quadrant) used in library
    #: creation processes.
    SECTOR_PREPARATION = 'SECTOR_PREP'


class IsoPlate(Entity):
    """
    This is an abstract base class for plates that are involved in ISO
    processing.
    """
    #: The type of the ISO plate (see :class:`ISO_PLATE_TYPES`).
    iso_plate_type = None
    #: The ISO this plate belongs to.
    iso = None
    #: The actual plate (:class:`thelma.entities.rack.Plate`)
    rack = None

    def __init__(self, iso, rack, iso_plate_type=None, **kw):
        Entity.__init__(self, **kw)
        if self.__class__ is IsoPlate:
            raise NotImplementedError('Abstract class')
        if iso_plate_type is None:
            iso_plate_type = ISO_PLATE_TYPES.ISO_PLATE
        self.iso_plate_type = iso_plate_type
        self.iso = iso
        self.rack = rack

    def __eq__(self, other):
        """
        Equality is based on the iso and rack attributes
        """
        return isinstance(other, self.__class__) and \
                self.iso == other.iso and \
                self.rack == other.rack

    def __str__(self):
        return self.rack.barcode

    def __repr__(self):
        str_format = '<%s id: %s, plate: %s, iso: %s>'
        params = (self.__class__.__name__, self.id, self.rack.barcode, self.iso)
        return str_format % params


class IsoAliquotPlate(IsoPlate):
    """
    This class represents an official ISO plate, that is a plate that has
    been ordered from the stock management (via ISO request) and is passed
    to the lab or (in case of a library) a ready-to-use library plate.
    They contain samples of defined volume and concentrations in defined
    positions.
    """
    #: Marks whether a plate is still available for experiments.
    has_been_used = None

    def __init__(self, iso, rack, has_been_used=False, **kw):
        IsoPlate.__init__(self, iso, rack,
                          iso_plate_type=ISO_PLATE_TYPES.ALIQUOT, **kw)
        self.has_been_used = has_been_used


class IsoPreparationPlate(IsoPlate):
    """
    Preparation plates are used to pre-dilute samples before there are
    transferred to an :class:`IsoAliquotPlate`.
    """
    #: Contains the data to prepare the samples (pool IDs, transfer targets,
    #: volumes, concentrations, etc.).
    rack_layout = None

    def __init__(self, iso, rack, rack_layout, **kw):
        IsoPlate.__init__(self, iso, rack,
                          iso_plate_type=ISO_PLATE_TYPES.PREPARATION, **kw)
        self.rack_layout = rack_layout


class IsoSectorPreparationPlate(IsoPlate):
    """
    A special :class:`IsoPlate` (actually even ISO preparation plate, but
    SQLalchemy does not support nested inheritance) that deals with samples of
    a particular rack sector (quadrant). Typically, this is linked to the usage
    of the CyBio robot.
    Sector indices are 0-based.

    Sectors a listed in Z-configuration, e.g. : ::

    0 1
    2 3
    """
    #: Contains the data to prepare the samples (pool IDs, transfer targets,
    #: volumes, concentrations, etc.).
    rack_layout = None
    #: The final plate sector index this ISO preparation plate is responsible
    #: for (0-based). If there are several sectors with the same combination
    #: of pools this is the lowest of these sector indices.
    sector_index = None

    def __init__(self, iso, rack, sector_index, rack_layout, **kw):
        IsoPlate.__init__(self, iso, rack,
                          iso_plate_type=ISO_PLATE_TYPES.SECTOR_PREPARATION,
                          **kw)
        self.rack_layout = rack_layout
        self.sector_index = sector_index

    def __eq__(self, other):
        """
        Equality is based on the iso, rack, and sector_index attributes.
        """
        return IsoPlate.__eq__(self, other) and \
               other.sector_index == self.sector_index

    def __repr__(self):
        str_format = '<%s id: %s, ISO: %s, rack: %s, sector index: %s>'
        params = (self.__class__.__name__, self.id, self.iso, self.rack.barcode,
                  self.sector_index)
        return str_format % params


class IsoJobPreparationPlate(Entity):
    """
    Preparation plates are used to pre-dilute samples before there are
    transferred to other plates. Unlike normal :class:`IsoPreparationPlate`,
    the ISO job preparation plate is a source plate for several ISOs
    (all belonging to the same :class:`IsoJob`).
    """
    #: The ISO job this plate belongs to (:class:`thelma.entities.job.IsoJob`).
    iso_job = None
    #: The actual plate (:class:`thelma.entities.rack.Plate`)
    rack = None
    #: The rack layout containing the molecule design pool and transfer data
    #: (:class:`IsoPlateLayout`).
    rack_layout = None

    def __init__(self, iso_job, rack, rack_layout, **kw):
        Entity.__init__(self, **kw)
        self.iso_job = iso_job
        self.rack = rack
        self.rack_layout = rack_layout

    def __eq__(self, other):
        """
        Equality is based on the rack and iso_job attributes.
        """
        return isinstance(other, self.__class__) and \
                self.rack == other.rack and \
                self.iso_job == other.iso_job

    def __str__(self):
        return self.rack

    def __repr__(self):
        str_format = '<%s id: %s, rack: %s, ISO job: %s>'
        params = (self.__class__.__name__, self.id, self.rack, self.iso_job)
        return str_format % params
