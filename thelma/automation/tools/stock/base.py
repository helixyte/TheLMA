"""
Base constants and functions for stock-=related tasks.

AAB
"""
from thelma.automation.utils.base import CustomQuery
from thelma.automation.utils.base import create_in_term_for_db_queries
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType
from thelma.automation.semiconstants import RACK_SHAPE_NAMES


__docformat__ = 'reStructuredText en'

__all__ = ['STOCK_DEAD_VOLUME',
           'STOCK_MIN_TRANSFER_VOLUME',
           'STOCK_ITEM_STATUS',
           'STOCK_TUBE_SPECS',
           'STOCK_CONCENTRATIONS',
           'STOCK_RACK_SHAPE_NAME'
           'get_stock_rack_shape',
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
#: The name of the :class:`RackShape` for stock racks.
STOCK_RACK_SHAPE_NAME = RACK_SHAPE_NAMES.SHAPE_96

#: The trac name for the stock management user.
STOCKMANAGEMENT_USER = 'stockmanagement'


def get_stock_rack_shape():
    """
    Returns the :class:`thelma.models.rack.RackShape` for stock racks.
    """
    return RACK_SHAPE_NAMES.from_name(STOCK_RACK_SHAPE_NAME)

def get_stock_rack_size():
    """
    Returns the number of available positions in a stock rack.
    """
    return get_stock_rack_shape().size

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


class RackLocationQuery(CustomQuery):
    """
    This query determines the barcoded locations of the passed racks.

    The query results is the
    """

    QUERY_TEMPLATE = '''
    SELECT r.barcode AS rack_barcode,
      bl.name AS location_name,
      bl.index AS location_index
    FROM rack r, barcoded_location bl, rack_barcoded_location rbl
    WHERE r.barcode IN %s
    AND rbl.rack_id = r.rack_id
    AND rbl.barcoded_location_id = bl.barcoded_location_id'''

    __RACK_BARCODE_COL_NAME = 'rack_barcode'
    __LOCATION_NAME_COL_NAME = 'location_name'
    __LOCATION_INDEX_COL_NAME = 'location_index'

    COLUMN_NAMES = [__RACK_BARCODE_COL_NAME, __LOCATION_NAME_COL_NAME,
                    __LOCATION_INDEX_COL_NAME]

    __RACK_BARCODE_INDEX = COLUMN_NAMES.index(__RACK_BARCODE_COL_NAME)
    __LOCATION_NAME_INDEX = COLUMN_NAMES.index(__LOCATION_NAME_COL_NAME)
    __LOCATION_INDEX_INDEX = COLUMN_NAMES.index(__LOCATION_INDEX_COL_NAME)

    RESULT_COLLECTION_CLS = dict

    def __init__(self, rack_barcodes):
        """
        Constructor:

        :param rack_barcodes: The rack barcodes as list.
        :type rack_barcodes: :class:`list` (or iterable)
        """
        CustomQuery.__init__(self)
        #: The rack barcodes as list.
        self.rack_barcodes = rack_barcodes

    def _get_params_for_sql_statement(self):
        return create_in_term_for_db_queries(self.rack_barcodes, as_string=True)

    def _store_result(self, result_record):
        rack_barcode = result_record[self.__RACK_BARCODE_INDEX]
        loc_name = result_record[self.__LOCATION_NAME_INDEX]
        loc_index = result_record[self.__LOCATION_INDEX_INDEX]
        if not loc_index is None:
            loc_name += ', index: %s' % (loc_index)
        self._results[rack_barcode] = loc_name

    def __repr__(self):
        str_format = '<%s number of barcodes: %s>'
        params = (self.__class__.__name__, len(self.rack_barcodes))
        return str_format % params

