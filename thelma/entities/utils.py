"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Utilities for entity classes.

NP
"""

from everest.entities.utils import get_root_aggregate
from pyramid.threadlocal import get_current_request
from pyramid.security import authenticated_userid
from thelma.interfaces import IUser

__docformat__ = 'reStructuredText en'

__all__ = ['get_current_user',
           'get_user',
           'encode_index_tuples',
           'label_from_number',
           'number_from_label',
           'BinaryRunLengthEncoder',
           'encode_index_tuples'
           ]

def get_current_user():
    """
    Gets the user entity for the currently logged in user.

    :return: The user entity (:class:`User`).
    """
    agg = get_root_aggregate(IUser)
    user_name = authenticated_userid(get_current_request())
    return agg.get_by_slug(user_name)

def get_user(username):
    """
    Gets the user entity for a given username (e.g. 'it', 'brehm' ..).

    :param username: The directory user name
    :return: The user entity (:class:`User`).
    """
    agg = get_root_aggregate(IUser)
    return agg.get_by_slug(username)

def label_from_number(number):
    """
    Converts a number into an letter label (e.g. plate row label).

    :param number: The number you want to convert
    :type number: :class:`int`
    :return: The label corresponding to that number (:class:`string`).
    :Note: The function works with numbers, not with indices. If you are
           passing an index make sure to increment it by 1.
    """
    row_label_chars = []
    while number > 0:
        modulo = (number - 1) % 26
        row_label_chars.insert(0, chr(65 + modulo))
        number = (number - modulo) / 26
    return ''.join(row_label_chars)


def number_from_label(label):
    """
    Coverts a letter label (e.g. plate row label) into a number.

    :param label: The label you want to convert.
    :type label: :class:`string`
    :return: The number corresponding to that label (:class:`int`).
    :Note: This function returns a number, not an index. If you want to
           work with indices, make sure to decrease the number by one
           before using it.
    """
    row_number = 0
    row_label_chars = list(label.upper())
    for i, c in enumerate(reversed(row_label_chars)):
        colnum = ord(c) - 64
        row_number += colnum * pow(26, i)
    return row_number


class BinaryRunLengthEncoder(object):
    """
    Encode (binary) 2D patters as 1D strings. The algorithm could in theory
    be extended to patterns with multiple (>2) states

    It is done as follows:
        * There \'positive\' and \'negative\' positions.
          The largest row_index of all positive positions defines
          the :attr:`row_number`.
          The largest column_index of all positive positions defines the
          :attr:`column_number`.
        * The algorithm now scans the rectangle of the dimension =
          row_index * column_index. It determines the length of all
          positive positions in order, counted from the top left of the 2D-array
          and stores the number in a list. It will then count the number
          of negative positions following the first positive-position-stretch,
          store the number, etc.

              **Example**: *1111001011* converts to  *[4, 2, 1, 1, 2]*

          The sum of the list elements is the number of wells.
          The algorithm will always start to look for positive (1/*True*)
          positions. Hence, if the first positions is negative, the list will
          start with *0*.
        * For database storage and use as url search term the list is converted
          in to string. The numbers are encoded by as 62-number system
          (digits *0-9*, letters *a-z*, letters *A-Z*).
          Stretches with a length of more than 61 will be displayed by
          a 2-place-number (62 system) and be marked by a \'-\' at the
          beginning.
        * At the end, the string gets a \'_r\' suffix where r is the number of
          rows encoded. It can be determined to determine the dimension of
          the scanned pattern since the sum of all numbers is the number of
          wells in the scanned area.

          **Example**: ::

                  0 1 1 0
                  1 1 0 1

          converts to *01421_2*
    """
    # pylint: disable=W0141
    #: The characters of the 62 system: digits 0-9, letters a-z, letters A-Z.
    S62_NUMBERS = range(10) + map(chr, range(97, 123)) + map(chr, range(65, 91))
    # pylint: enable=W0141
    #: Character indicating that the next length is encrypted by 2 characters.
    TWO_PLACE_MARKER = '-'

    def __init__(self, positive_positions):
        """
        Constructor - call :func:`encode_as_run_length_string` to run.

        :param positive_positions: Set of well positions
                (row_index (:class:`int`), column_index (:class:`int`))
                having one or several tags in common
        :return: run length encoded :class:`string`
        """
        #: A set of positions (row_index (:class:`int`),
        #: column_index (:class:`int`)) having a tag in common.
        self._positive_positions = positive_positions

        #: A lookup (set) storing the coordinates (row_index, column_index)
        #: for each each positive position. The lookup shall speed up
        #: the comparison.
        self._index_lookup = set()

    def encode_as_run_length_string(self):
        """
        Returns a run-length decoded string, storing the
        information of a 2D binary pattern
        (originally written for tagged wells on a plate).

        :param positive_positions: Set of well positions
                (row_index (:class:`int`), column_index (:class:`int`))
                having one or several tags in common
        :return: run length encoded :class:`string`
        """
        self._create_lookup()
        column_map = self.__get_column_map()
        row_number, column_number = self.__get_scanning_dimension(column_map)
        suffix = '_%i' % (row_number)
        run_length_list = self.__convert_1D_to_run_length_list(row_number,
                                                               column_number)
        run_length_string = self.__convert_rl_list_to_string(run_length_list)
        run_length_string += suffix
        return run_length_string

    def _create_lookup(self):
        """
        Creates the :attr:`_index_lookup` allowing for a fast comparison
        of positions.
        In the case of tuple the positions can be used directly.
        """
        for pos in self._positive_positions:
            self._index_lookup.add(pos)

    def __get_column_map(self):
        """
        All wells here are positive.
        """
        columns = {}
        for pos in self._positive_positions:
            column_index = int(self._get_column_index_from_input_set(pos))
            row_index = int(self._get_row_index_from_input_set(pos))
            if column_index in columns:
                columns[column_index].append(row_index)
            else:
                columns[column_index] = [row_index]
        return columns

    def __get_scanning_dimension(self, col_map):
        """
        Determines the largest row and column indices of all positive
        wells and derives the dimension of the scanning pattern from this.
        """
        max_row = 0
        max_column = max(col_map.keys())
        for row_list in col_map.values():
            max_row = max(max_row, max(row_list))
        return max_row + 1, max_column + 1

    def __convert_1D_to_run_length_list(self, no_rows, no_columns):
        """
        Scans the lengths of the stretches in the 1D array.
        :return: ordered list of stretch lengths
        """
        counter = 0
        counter_storage = []
        true_false_mode = True

        for col_index in range(no_columns):
            for row_index in range(no_rows):
                coords = (row_index, col_index)
                in_set = coords in self._index_lookup
                if in_set == true_false_mode:
                    counter += 1
                else:
                    counter_storage.append(counter)
                    counter = 1
                    true_false_mode = not true_false_mode
        counter_storage.append(counter)
        return counter_storage

    def __convert_rl_list_to_string(self, rl_list):
        """
        Converts the stretch length list into a string.
        """
        s62_map = {}
        for i in range(len(self.S62_NUMBERS)):
            s62_map[i] = str(self.S62_NUMBERS[i])

        rl_string = ''
        for counter in rl_list:
            if counter < 62:
                c_string = s62_map[counter]
            else:
                c2 = counter % 62
                c1 = (counter - c2) / 62
                c_string = self.TWO_PLACE_MARKER
                c_string += '%s%s' % (s62_map[c1], s62_map[c2])
            rl_string += c_string
        return rl_string

    def _get_row_index_from_input_set(self, position):
        """
        Method might be overwritten by subclasses.
        """
        return position[0]

    def _get_column_index_from_input_set(self, position):
        """
        Method might be overwritten by subclasses.
        """
        return position[1]


def encode_index_tuples(position_set):
    encoder = BinaryRunLengthEncoder(position_set)
    return encoder.encode_as_run_length_string()
