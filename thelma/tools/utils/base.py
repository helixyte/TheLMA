"""
:Date: 12 Aug 2011
:Author: AAB, berger at cenix-bioscience dot com

Utility methods and classes for tools.
"""
from math import ceil
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query


__docformat__ = "reStructuredText en"
__all__ = ['MAX_PLATE_LABEL_LENGTH',
           'VOLUME_CONVERSION_FACTOR',
           'CONCENTRATION_CONVERSION_FACTOR',
           'are_equal_values',
           'is_smaller_than',
           'is_larger_than',
           'is_valid_number',
           'get_converted_number',
           'get_trimmed_string',
           'round_up',
           'create_in_term_for_db_queries',
           'add_list_map_element',
           'CustomQuery']


#: The maximum length a rack label might have to be printable.
MAX_PLATE_LABEL_LENGTH = 20

#: Volumes are stored in litres (in the DB), we work in ul.
VOLUME_CONVERSION_FACTOR = 1e6
#: Concentration are stored in molars (in the DB), we work with nM.
CONCENTRATION_CONVERSION_FACTOR = 1e9

#: This error range is used for floating point comparison.
__ERROR_RANGE = 0.001

def are_equal_values(value1, value2):
    """
    Compares 2 floating values (to circumvent python's floating point
    inaccuracy which occurs already with number with only one decimal place
    difference). Instead of comparing the values directly the method will
    check whether the difference of the values is within a certain error
    range.

    :param value1: a floating value
    :type value1: a number

    :param value2: a floating value
    :type value2: a number

    :return: :class:`bool`
    """
    diff = value1 - value2
    return (diff < __ERROR_RANGE and diff > (__ERROR_RANGE * -1))

def is_smaller_than(value1, value2):
    """
    Checks whether the first given value is smaller than the second one.

    This method serves to circumvent python's floating point
    inaccuracy which occurs already with number with only one decimal place
    difference). Instead of comparing the values directly the method will
    check whether the difference of the values is below a certain values.

    :param value1: a floating value (the one to be checked)
    :type value1: a number

    :param value2: a floating value (the reference value)
    :type value2: a number

    :return: :class:`bool`
    """
    diff = value1 - value2
    return diff < (__ERROR_RANGE * -1)

def is_larger_than(value1, value2):
    """
    Checks whether the first given value is larger than the second one.

    This method serves to circumvent python's floating point
    inaccuracy which occurs already with number with only one decimal place
    difference). Instead of comparing the values directly the method will
    check whether the difference of the values is above a certain values.

    :param value1: a floating value (the one to be checked)
    :type value1: a number

    :param value2: a floating value (the reference value)
    :type value2: a number

    :return: :class:`bool`
    """
    diff = value1 - value2
    return diff > __ERROR_RANGE

def sort_rack_positions(rack_positions):
    """
    Returns a list of rack positions sorted by row.

    :param rack_positions: The rack positions to be sorted.
    :type rack_positions: Iterable of :class:`thelma.entities.rack.RackPosition`
    :return: sorted list
    """

    rack_position_map = {}
    for rack_position in rack_positions:
        label = '%s%02i' % (rack_position.label[:1],
                            int(rack_position.label[1:]))
        rack_position_map[label] = rack_position
    labels = rack_position_map.keys()
    labels.sort()

    sorted_rack_positions = []
    for label in labels:
        rack_position = rack_position_map[label]
        sorted_rack_positions.append(rack_position)
    return sorted_rack_positions


def is_valid_number(value, positive=True, may_be_zero=False, is_integer=False):
    """
    Checks whether a passed value is a valid float
    (e.g. needed for concentrations).

    :param value: The value to be checked.

    :param positive: If *True* a value must be a positive number.
    :type positive: :class:`boolean`
    :default positive: *False*

    :param may_be_zero: If *True* a value of 0 is prohibited.
    :type may_be_zero: :class:`boolean`
    :default may_be_zero: *False*

    :param is_integer: If *True*, the method will also check if the
        value is an integer.
    :type is_integer: :class:`bool`
    :default is_integer: *False*

    :return: :class:`boolean`
    """

    meth = float
    if is_integer:
        meth = int
        if isinstance(value, (basestring, int, float)):
            value = get_trimmed_string(value)

    try:
        number_value = meth(value)
    except ValueError:
        return False
    except TypeError:
        return False

    if not may_be_zero and number_value == 0:
        return False
    if positive and not number_value >= 0:
        return False

    return True

def get_converted_number(value, is_integer=False):
    """
    Returns a number if conversion into a number is possible.

    :param value: The value to be checked.

    :param positive: If *True* a value must be a positive number.
    :type positive: :class:`boolean`
    :default positive: *False*

    :param may_be_zero: If *True* a value of 0 is prohibited.
    :type may_be_zero: :class:`boolean`
    :default may_be_zero: *False*

    :param is_integer: If *True*, the method will also check if the
        value is an integer.
    :type is_integer: :class:`bool`
    :default is_integer: *False*
    """
    if is_valid_number(value, is_integer=is_integer):
        if is_integer:
            return int(value)
        else:
            return float(value)

    return value

def get_trimmed_string(value):
    """
    Returns a string of value (stripped of \'.0\' at the end). Float values
    are limited to 1 decimal place.
    """
    if isinstance(value, float):
        value = round(value, 1)
    value_str = str(value)
    if value_str.endswith('.0'): value_str = value_str[:-2]
    return value_str

def round_up(value, decimal_places=1):
    """
    Rounds up the given value (to the decimal place specified (default: 1)).

    :param value: The number to round up.
    :type value: :class:`float`

    :param decimal_places: The decimal place to round to (1 refers to 1 place
        behind a comma).
    :type decimal_places: :class:`int`

    :return: The round value as float.
    """

    value = float(value)
    fact = float('1e%i' % (decimal_places))
    rounded_intermediate = ceil(round((value * fact), decimal_places + 1))
    rounded_value = (rounded_intermediate) / fact
    return rounded_value

def create_in_term_for_db_queries(values, as_string=False):
    """
    Utility method converting a collection of values (iterable) into a tuple
    that can be used for an IN statement in a DB query.

    :param as_string: If *True* the values of the list will be surrounded
        by quoting.
    :type as_string: :class:`bool`
    :default as_string: *False*
    """

    as_string_list = values
    if as_string:
        as_string_list = []
        for value in values:
            string_value = '\'%s\'' % (value)
            as_string_list.append(string_value)
    tuple_content = ', '.join(str(i) for i in as_string_list)
    return '(%s)' % (tuple_content)

def add_list_map_element(value_map, map_key, new_element, as_set=False):
    """
    Adds the passed element to the passed map (assuming all map value
    being lists).

    :param value_map: The map the element shall be added to.
    :type value_map: :class:`dict`

    :param map_key: The key for the map.
    :type map_key: any valid key

    :param new_element: The element to be added.
    :type new_element: any

    :param as_set: Shall the value be a set (*True*) or a list
        (*False*, default)?
    :type as_set: :class:`bool`
    :default as_set: *False* (list)
    """
    if value_map.has_key(map_key):
        values = value_map[map_key]
    else:
        if as_set:
            values = set()
        else:
            values = list()
        value_map[map_key] = values

    if as_set:
        values.add(new_element)
    else:
        values.append(new_element)


def get_nested_dict(parent_dict, map_key):
    """
    Helper function fetching dictionary from another dictionary in which it is
    referenced. If the key is not known to the parent a new dictionary
    is created and assigned.

    :param parent_dict: The map containing the other dictionary.
    :type parent_dict: :class:`dict`

    :param map_key: The key for the dict to be fetched.
    :type map_key: any suitable key
    """
    if parent_dict.has_key(map_key):
        return parent_dict[map_key]
    child_dict = dict()
    parent_dict[map_key] = child_dict
    return child_dict


class CustomQuery(object):
    """
    Creates and runs a DB query. The results are converted into candidates list.
    """
    #: The raw query without values for the variable clauses.
    QUERY_TEMPLATE = None
    #: The query result column names in the order in which there are expected.
    COLUMN_NAMES = None

    #: The type of the collection storing the query results
    #: (default: :class:`list`).
    RESULT_COLLECTION_CLS = list

    def __init__(self):
        """
        Constructor:

        :param session: The DB session to be used.
        """
        #: The completed query including search values (use
        #: :func:`create_sql_statement` to generate).
        self.sql_statement = None
        #: A dictionary or list containing the query results.
        self._results = None

    def create_sql_statement(self):
        """
        Creates the :attr:`sql_statement` by inserting the search values into
        the :attr:`QUERY_TEMPLATE`.
        """
        params = self._get_params_for_sql_statement()
        self.sql_statement = self.QUERY_TEMPLATE % params

    def _get_params_for_sql_statement(self):
        """
        Returns a tuple of parameters to be inserted into the
        :attr:`QUERY_TEMPLATE` in order to create the :attr:`sql_statement`.
        """
        raise NotImplementedError('Abstract method')

    def run(self, session):
        """
        Runs the query and converts its results to a :class:`TubeCandidate`s.
        Also generates the query if this has not been done yet.

        Attention: Candidates from former runs are removed!

        :param session: The DB session to be used.

        :raise ValueError: If there is not at least one result for the query
        """
        if self.sql_statement is None:
            self.create_sql_statement()

        self._results = self.RESULT_COLLECTION_CLS() #pylint: disable=E1102
        column_names = tuple(self.COLUMN_NAMES)
        query_options = dict(query_class=Query)
        try:
            results = session.query(*column_names, **query_options) \
                             .from_statement(self.sql_statement) \
                             .all()
        except NoResultFound:
            raise ValueError('The tube picking query did not return any ' \
                             'result!')
        else:
            for record in results:
                self._store_result(record)

    def _store_result(self, result_record):
        """
        Converts a result record into a storage object (if applicable) and
        stores it in the :attr:`_results` list.
        """
        raise NotImplementedError('Abstract method')

    def get_query_results(self):
        """
        Returns the result collection.
        """
        return self._results

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__
