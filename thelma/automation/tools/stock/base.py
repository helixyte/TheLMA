"""
Base constants and functions for stock-=related tasks.

AAB
"""
from thelma.automation.tools.utils.base import create_in_term_for_db_queries
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType


__docformat__ = 'reStructuredText en'

__all__ = ['STOCK_DEAD_VOLUME',
           'STOCK_MIN_TRANSFER_VOLUME',
           'STOCK_ITEM_STATUS',
           'STOCK_TUBE_SPECS',
           'STOCK_CONCENTRATIONS',
           'STOCK_RACK_SIZE',
           'STOCKMANAGEMENT_USER',
           'get_default_stock_concentration',
           'RackLocationQuery']


#: The dead volume of a stock tube in ul.
STOCK_DEAD_VOLUME = 5
#: The minimum volume that can be taken out of the stock in ul.
STOCK_MIN_TRANSFER_VOLUME = 1
#: Default item status for a stock tube.
STOCK_ITEM_STATUS = 'MANAGED'
#: The tube specs a stock tube can have.
STOCK_TUBE_SPECS = ('MATRIX0500', 'MATRIX1400')
#: The number of positions in a stock rack.
STOCK_RACK_SIZE = 96

#: The trac name for the stock management user.
STOCKMANAGEMENT_USER = 'stockmanagement'


def get_stock_tube_specs_db_term():
    """
    Returns a term that can be inserted into IN-clauses of DB queries
    (containing all valid specs for stock tubes).
    """
    return create_in_term_for_db_queries(STOCK_TUBE_SPECS, as_string=True)


class STOCK_CONCENTRATIONS(object):
    """
    Stores the stock concentrations for the different molecule types.
    """

    #: The concentration of stock solutions in nM.
    _STANDARD_STOCK_CONCENTRATION = 50000 # 50 uM
    #: The stock concentration for esiRNAs in nM.
    _ESI_RNA_STOCK_CONCENTRATION = 3800 # 3.8 uM
    #: The stock concentration for siRNA pools with more than 1 design in nM.
    _SIRNA_POOL_CONCENTRATION = 10000 # 10 uM
    #: The stock concentration for microRNAs in nM.
    _MICRO_RNA_STOCK_CONCENTRATION = 10000 # 10 uM
    #: The stock concentration for (most) compounds in nM.
    COMPOUND_STOCK_CONCENTRATION = 5000000 # 5 mM = 5000 uM

    @classmethod
    def from_molecule_type(cls, molecule_type, number_designs=1):
        """
        Returns the stock concentration for the given molecule type.

        :param molecule_type: The molecule types whose stock concentration
            you want to know.
        :type molecule_type: :class:`thelma.models.moleculetype.MoleculeType`
            or :class:`str` (molecule type ID)

        :param number_designs: The number of designs in a pool (at the moment
            this is only makes a difference for siRNA pools).
        :type number_designs: positive integer
        :default number_designs: 1

        :raises TypeError: For molecule types of the wrong class.
        :raises ValueError: If the molecule type is unknown.
        :return: The stock concentration for that molecule type in nM.
        """

        if isinstance(molecule_type, MoleculeType):
            mt_id = molecule_type.id
        elif isinstance(molecule_type, basestring):
            if MOLECULE_TYPE_IDS.is_known_type(molecule_type):
                mt_id = molecule_type
            else:
                msg = 'Unknown molecule type name "%s".' % (molecule_type)
                raise ValueError(msg)
        else:
            msg = 'The molecule types must be a %s object or a string ' \
                  '(obtained: %s).' % (MoleculeType.__class__.__name__,
                   molecule_type.__class__.__name__)
            raise TypeError(msg)

        if mt_id == MOLECULE_TYPE_IDS.MIRNA_INHI or \
                                     mt_id == MOLECULE_TYPE_IDS.MIRNA_MIMI:
            return cls._MICRO_RNA_STOCK_CONCENTRATION
        elif mt_id == MOLECULE_TYPE_IDS.ESI_RNA:
            return cls._ESI_RNA_STOCK_CONCENTRATION
        elif mt_id == MOLECULE_TYPE_IDS.COMPOUND:
            return cls.COMPOUND_STOCK_CONCENTRATION
        elif mt_id == MOLECULE_TYPE_IDS.SIRNA and number_designs > 1:
            return  cls._SIRNA_POOL_CONCENTRATION
        else:
            return cls._STANDARD_STOCK_CONCENTRATION

#: An alias for :func:`STOCK_CONCENTRATIONS.from_molecule_type`
get_default_stock_concentration = STOCK_CONCENTRATIONS.from_molecule_type


class RackLocationQuery(object):
    """
    This query determines the barcoded locations of the passed racks.
    """

    # The query statement.
    QUERY = 'SELECT r.barcode AS rack_barcode, bl.name AS location_name, ' \
                'bl.index AS location_index ' \
            'FROM rack r, barcoded_location bl, rack_barcoded_location rbl ' \
            'WHERE r.barcode IN %s' \
            'AND rbl.rack_id = r.rack_id ' \
            'AND rbl.barcoded_location_id = bl.barcoded_location_id'

    #: The query result column (required to parse the query results).
    QUERY_RESULTS = ('rack_barcode', 'location_name', 'location_index')

    #: The index of the rack barcode within the query result.
    RACK_BARCODE_INDEX = 0
    #: The index of the location name within the query result.
    LOCATION_NAME_INDEX = 1
    #: The index of the location index within the query result.
    LOCATION_INDEX_INDEX = 2

    def __init__(self, rack_barcodes):
        """
        Constructor:

        :param rack_barcodes: The rack barcodes as list.
        :type rack_barcodes: :class:`list` (or iterable)
        """
        #: Stores the location name for each rack barcode.
        self.location_names = dict()
        #: Stores the location index for each rack barcode.
        self.location_indices = dict()

        for rack_barcode in rack_barcodes:
            self.location_names[rack_barcode] = None
            self.location_indices[rack_barcode] = None

    def run(self, session):
        """
        Runs the query using the provided session.
        """
        rack_term = create_in_term_for_db_queries(self.location_names.keys(),
                                                  as_string=True)
        statement = self.QUERY % (rack_term)

        #pylint: disable=W0142
        results = session.query(*self.QUERY_RESULTS).\
                  from_statement(statement).all()
        #pylint: enable=W0142

        for record in results:
            rack_barcode = record[self.RACK_BARCODE_INDEX]
            self.location_names[rack_barcode] = record[self.LOCATION_NAME_INDEX]
            self.location_indices[rack_barcode] = \
                                               record[self.LOCATION_INDEX_INDEX]

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        str_format = '<%s number of barcodes: %s>'
        params = (self.__class__.__name__, len(self.location_names))
        return str_format % params

