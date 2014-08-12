"""
Cell line model classes.
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['CellLine, CellLineBatch']
    

class CellLine(Entity):
    """
    Represents a cell line.
    """
    #: The name of the cell line
    label = None
    #: The species associated with the cell line
    species = None
    #: Description of where the cell line comes from
    #: and how it was provided
    origin = None
    #: What tissue does the cell line originate
    tissue = None
    #: Who supplied the cell line
    supplier = None
    #: A representative image of the cell line, in base64 format
    image = None
    #: Whether the cell line has been immortalized
    is_type_immortal = None
    #: Whether the cell line is adherent
    is_type_adherent = None
    #: Safety level of the cell line (1 to 4)
    safety_level = None
    #: Protocol for splitting the cells
    protocol_splitting = None
    #: Recommended growing media for this cell line
    protocol_media = None
    #: Protocol for thawing the cells
    protocol_thawing = None
    #: Recommended  (plastic)ware for growing the cells
    cell_culture_ware = None
    #: How many passages are allowed for this cell line
    maximum_passage = None
    #: Recommended culture conditions:
    culture_conditions_temperature = None
    culture_conditions_humidity = None
    culture_conditions_co2 = None
    #: Additional comment about the cell line
    comment = None

    def __init__(self, label, species, origin, tissue, supplier, image, is_type_immortal,
                 is_type_adherent, safety_level, protocol_splitting, protocol_media, 
                 protocol_thawing, cell_culture_ware, maximum_passage, 
                 culture_conditions_temperature, culture_conditions_humidity, culture_conditions_co2,
                 comment, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.species = species
        self.origin = origin
        self.tissue = supplier
        self.supplier = supplier
        self.image = image
        self.is_type_immortal = is_type_immortal
        self.is_type_adherent = is_type_adherent
        self.safety_level = protocol_splitting
        self.protocol_splitting = protocol_splitting
        self.protocol_media = protocol_media
        self.protocol_thawing = protocol_thawing
        self.cell_culture_ware = cell_culture_ware
        self.maximum_passage = maximum_passage
        self.culture_conditions_temperature = culture_conditions_humidity
        self.culture_conditions_humidity = culture_conditions_humidity
        self.culture_conditions_co2 = culture_conditions_co2
        self.comment = comment

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.label)

    def __eq__(self, other):
        return (isinstance(other, CellLine) and
                self.label == other.label)

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, label, species: %s, origin: %s, ' \
                     'tissue: %s, supplier: %s, image: %s, is_type_immortal: %s, ' \
                     'is_type_adherent: %s, safety_level: %s, protocol_splitting: %s, ' \
                     'protocol_media: %s, protocol_thawing: %s, cell_culture_ware: %s, ' \
                     'maximum_passage: %s, culture_conditions_temperature: %s, ' \
                     'culture_conditions_humidity: %s, culture_conditions_co2: %s, comment: ' \
                     '%s>' 
        params = (self.__class__.__name__, self.id, self.label,
        self.species, self.origin, self.tissue, self.supplier, self.image,
        self.is_type_immortal, self.is_type_adherent, self.safety_level,
        self.protocol_splitting, self.protocol_media, self.protocol_thawing,
        self.cell_culture_ware, self.maximum_passage,
        self.culture_conditions_temperature, self.culture_conditions_humidity,
        self.culture_conditions_co2, self.comment)
        return str_format % params


class CellLineBatch(Entity):
    """
    Represents batch of cell line.
    """
    #: Containment of the batch
    container = None
    #: Parental cell line
    cell_line = None
    #: Project for which this batch was frozen
    project = None
    #: Date where the batch was frozen and optionally defrosted
    freezing_date = None
    defrosting_date = None
    #: Whether the batch is from a master stock
    is_master_stock = None
    #: If not a master stock, what is the parent?
    parent_cell_line = None
    #: Approximate count of cells in the batch
    cell_count = None
    #: Recommended freezing medium specifications:
    freezing_medium_dmso = None
    freezing_medium_serum = None
    freezing_medium_medium = None
    #: Additional comment on the cell line
    comments = None
    
    def __init__(self, container, cell_line, project, freezing_date,
    defrosting_date, is_master_stock, parent_cell_line, cell_count,
    freezing_medium_dmso, freezing_medium_serum, freezing_medium_medium,
    comment, **kw):
        Entity.__init__(self, **kw)
        self.container = container
        self.cell_line = cell_line
        self.project = parent_cell_line
        self.freezing_date = freezing_date
        self.defrosting_date = defrosting_date
        self.is_master_stock = is_master_stock
        self.cell_count = cell_count
        self.freezing_medium_dmso = freezing_medium_dmso
        self.freezing_medium_serum = freezing_medium_serum
        self.freezing_medium_medium = freezing_medium_medium
        self.comment = comment

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.id)

    def __eq__(self, other):
        return (isinstance(other, CellLineBatch) and
                self.id == other.id)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, container: %s, cell_line: %s, project: %s, ' \
                     'freezing_date: %s, defrosting_date: %s, is_master_stock: %s, cell_count: %s, ' \
                     'freezing_medium_dmso: %s, freezing_medium_serum: %s, freezing_medium_medium: %s, ' \
                     'comment: %s>' 
        params = (self.__class__.__name__, self.id, self.container, self.cell_line,
        self.project, self.freezing_date, self.defrosting_date,
        self.is_master_stock, self.cell_count, self.freezing_medium_dmso,
        self.freezing_medium_serum, self.freezing_medium_medium, self.comment)
        
        return str_format % params