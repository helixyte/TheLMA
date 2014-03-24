"""
Tools for layout optimisations.

AAB
"""
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.layouts import WorkingLayout


__docformat__ = 'reStructuredText en'

__all__ = ['TransferItem',
           'BiomekLayoutOptimizer',
           'TransferSubcolumn',
           'SourceSubcolumn']


class TransferItem(object):
    """
    A container object for convenience purposes. Represents a future source
    position.
    """

    def __init__(self, working_pos):
        """
        Constructor:

        :param working_pos: An object providing a hash value and a rack position
            (usually the first occurrence of item having that hash value).
        :type working_pos: :class:`WorkingPosition` subclass
        """
        #: The transfection position storing the transfection data.
        self.working_pos = working_pos
        #: The hash value (full hash) of the :attr:`tf_pos`.
        self.hash_value = self._get_hash_value()

        #: Target row index of first occurence (used to determine, whether
        #: further transfer items can be pipetted in the same movement).
        self.target_row_index = working_pos.rack_position.row_index

    def _get_hash_value(self):
        """
        Derives the hash value from the working position this item deals with.
        """
        raise NotImplementedError('Abstract method.')

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                other.hash_value == self.hash_value

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __cmp__(self, other):
        return cmp(self.hash_value, other.hash_value)

    def __hash__(self):
        return hash(self.hash_value)

    def __str__(self):
        return self.hash_value

    def __repr__(self):
        str_format = '%s %s, row index: %i'
        params = (self.__class__.__name__, self.hash_value,
                  self.target_row_index)
        return str_format % params


class BiomekLayoutOptimizer(BaseAutomationTool):
    """
    Tries to generate an speed-otimised source plate layout for a Biomek
    transfer. The sorting is based on working position hash values.

    To this end, we try to maintain the column ordering. However, if the
    the source plate is smaller than the cell plate, the robot cannot pipet
    into to adjacent cell plate wells within one column. Thus, in this case
    the two target positions must have a minimum row distance of 1 and the
    column must be split into \'subcolumns\'.

    **Return Value:** The optimised source layout.
    """

    #: The class of the source layout (:Class:`WorkingLayout` subclass).
    SOURCE_LAYOUT_CLS = WorkingLayout
    #: The used :class:`TransferItem` subclass.
    TRANSFER_ITEM_CLASS = TransferItem

    def __init__(self, log):
        """
        Constructor:

        :param design_rack_layouts: The transfection layout for each design rack.
        :type design_rack_layouts: :class:`dict`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The source layout.
        self._source_layout = None

        #: A set of all hash values.
        self._hash_values = None
        #: The column maps for the different target layouts (working positions
        #: mapped onto column indices) - the keys of this dictionary should
        #: be suitable for sorting. Otherwise there are irrelevant.
        self._column_maps = None

        #: The rack shape of the source layout.
        self.__source_rack_shape = None

        #: The minimum distance in rows two well of a column must have for
        #: the Biomek to pipet them together. The value is 1 for 384-well
        #: plates and 0 (=no distance) for 96-well plates.
        self.__trg_min_row_distance = None
        #: The minimum distance in rows two well of a column must have for
        #: the Biomek to pipet them together. The value is 1 for 384-well
        #: plates and 0 (=no distance) for 96-well plates.
        self.__src_min_row_distance = None

        #: The transfer items that are already part of a subcolumn.
        self.__subcolumn_tids = None
        #: All :class:`TransferSubcolumn` objects mapped onto their length.
        self.__subcolumn_lengths = None

        #: Stores :class:`SourceSubcolumn` objects managing the remaining free
        #: positions for the source transfection layout.
        self.__free_positions = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._source_layout = None
        self._hash_values = set()
        self._column_maps = dict()
        self.__source_rack_shape = None
        self.__trg_min_row_distance = None
        self.__src_min_row_distance = None
        self.__subcolumn_tids = dict()
        self.__subcolumn_lengths = dict()
        self.__free_positions = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start layout optimisation ...')

        self._check_input()
        if not self.has_errors(): self._find_hash_values()
        if not self.has_errors(): self.__set_source_values()
        if not self.has_errors():
            have_equal_shape = self.__source_rack_shape \
                               == self._get_target_layout_shape()
            if have_equal_shape: self.__sort_one_to_one()
            if len(self._source_layout) < 1:
                # one to one not possible (incl. trial and failure)
                self.__split_into_subcolumns()
                self.__sort_subcolumns()
                self.__distribute_source_columns()
        if not self.has_errors():
            self.return_value = self._source_layout
            self.add_info('Layout optimisation completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        raise NotImplementedError('Abstract method.')

    def _find_hash_values(self):
        """
        Initialises :attr:`_hash_values` and :attr:`_column_maps`.
        """
        raise NotImplementedError('Abstract method.')

    def __set_source_values(self):
        """
        There are two sizes available: 96 positions and 384 positions. If
        possible (less than 97 distinct hash values), we use the smaller one.
        Also sets the source rack shape and minimum row distances.
        """
        self.add_debug('Determine rack shape ...')

        small_shape = get_96_rack_shape()
        large_shape = get_384_rack_shape()
        if len(self._hash_values) > large_shape.size:
            msg = 'The number of source positions (%i) exceeds %i! ' \
                  'Redesign your experiment or talk to the IT ' \
                  'department, please.' \
                  % (len(self._hash_values), large_shape.size)
            self.add_error(msg)
        elif len(self._hash_values) > small_shape.size:
            source_rack_shape = large_shape
        else:
            source_rack_shape = small_shape

        if not self.has_errors():
            self._source_layout = self._init_source_layout(source_rack_shape)
            self.__source_rack_shape = self._source_layout.shape
            if self.__source_rack_shape.name == RACK_SHAPE_NAMES.SHAPE_384:
                self.__src_min_row_distance = 1
            else:
                self.__src_min_row_distance = 0
            target_layout_shape = self._get_target_layout_shape()
            if target_layout_shape.name == RACK_SHAPE_NAMES.SHAPE_384:
                self.__trg_min_row_distance = 1
            else:
                self.__trg_min_row_distance = 0

    def _init_source_layout(self, source_layout_shape):
        """
        By default, we initialize a layout of the :attr:`SOURCE_LAYOUT_CLS`
        with the :attr:`__source_rack_shape`.
        """
        return self.SOURCE_LAYOUT_CLS(shape=source_layout_shape)

    def _get_target_layout_shape(self):
        """
        Returns the rack shape of the target layout.
        """
        raise NotImplementedError('Abstract method.')

    def __sort_one_to_one(self):
        """
        This is some sort sort of short cut for the very simple layouts.
        In one-to-one sorting mode we simply assign the rack position of the
        earliest occurrence of a rack position for a hash value. If the
        position is already occupied, the process is aborted and we switch
        back to the "normal" optimisation algorithm.

        One-to-one assumes equal rack shapes.
        """
        position_map = self._create_one_to_one_map()

        if not position_map is None:
            for rack_pos, working_pos in position_map.iteritems():
                self._add_source_position(rack_pos, working_pos)
            if not len(self._source_layout) == len(self._source_layout):
                msg = 'Error during 1-to-1 sorting. The length of the source ' \
                      'transfection layout (%i) does not match the number of ' \
                      'distinct hash values (%i). This should not happen. ' \
                      'Talk to IT, please.' \
                      % (len(self._source_layout), len(self._hash_values))
                self.add_error(msg)

    def _create_one_to_one_map(self):
        """
        Creates one position map for one to one sorting (with source rack
        positions as keys and template working positions as values).
        Return *None* if one-to-one sorting is not possible.
        """
        return None

    def __split_into_subcolumns(self):
        """
        We try to keep position in the same column. However, since we might
        need to observe a minimum row distance we might need subcolumns.
        """
        self.add_debug('Split into subcolumns ...')

        labels = sorted(self._column_maps.keys())
        for label in labels:
            column_map = self._column_maps[label]
            for column_index in sorted(column_map.keys()):
                working_positions = sorted(column_map[column_index],
                        cmp=lambda wp1, wp2: cmp(wp1.rack_position.row_index,
                                                 wp2.rack_position.row_index))
                subcolumns = self.__split_column(working_positions,
                                                 column_index)
                for subcolumn in subcolumns:
                    self.__store_subcolumns(subcolumn)

    def __split_column(self, sorted_working_positions, column_index):
        """
        Tries to determine subcolumn that can be pipetted together (regarding
        distance the limitations of the robot..
        """
        subcolumns = []
        used_hash_values = set()

        for working_pos in sorted_working_positions:
            tid = self.TRANSFER_ITEM_CLASS(working_pos=working_pos)
            if tid.hash_value in used_hash_values: continue
            used_hash_values.add(tid.hash_value)
            picked_subcolumn = None
            for subcolumn in subcolumns:
                if not subcolumn.allows_transfer_item(tid): continue
                picked_subcolumn = subcolumn
                subcolumn.add_transfer_item(tid)
                break
            if picked_subcolumn is None:
                subcolumn = TransferSubcolumn(target_column_index=column_index,
                                   min_row_distance=self.__trg_min_row_distance)
                subcolumn.add_transfer_item(tid)
                subcolumns.append(subcolumn)

        return subcolumns

    def __store_subcolumns(self, subcolumn):
        """
        If some of the transfer items within the subcolumn are already part
        of other subcolumns there are removed and the remaining transfer items
        are appended, too, if possible.
        """
        # Find transfer items that already stored
        used_tids = []
        for tid in subcolumn.transfer_items:
            if self.__subcolumn_tids.has_key(tid): used_tids.append(tid)
        for used_tid in used_tids: subcolumn.remove_transfer_item(used_tid)

        # Try to append the remaining transfer items to subcolumn already stored
        if not (len(subcolumn) < 1 or len(used_tids) < 1):
            while len(subcolumn) > 0:
                tid = subcolumn.transfer_items.pop(0)
                tid_appended = False
                for used_tid in sorted(used_tids):
                    stored_subcolumn = self.__subcolumn_tids[used_tid]
                    if len(stored_subcolumn) \
                                        < self.__source_rack_shape.number_rows:
                        stored_subcolumn.add_transfer_item(tid)
                        self.__subcolumn_tids[tid] = stored_subcolumn
                        tid_appended = True
                        break
                if not tid_appended:
                    subcolumn.transfer_items.insert(0, tid)
                    break

        # store remaining subcolumns
        for tid in subcolumn:
            self.__subcolumn_tids[tid] = subcolumn

    def __sort_subcolumns(self):
        """
        Sorts the subcolumns by length.
        """
        self.add_debug('Sort subcolumns ...')

        found_before = set()

        for subcolumn in self.__subcolumn_tids.values():
            if subcolumn in found_before: continue
            found_before.add(subcolumn)
            add_list_map_element(self.__subcolumn_lengths, len(subcolumn),
                                 subcolumn)

    def __distribute_source_columns(self):
        """
        We always try to find a column whose number of free positions match
        the size of the subcolumn exactly. If there is no column like this,
        we accept larger columns. Only if that fails, too, we start to
        split subcolumns into smaller units.
        """
        self.add_debug('Distribute sub columns ...')

        self.__free_positions = SourceSubcolumn.from_rack_shape(
                                rack_shape=self.__source_rack_shape,
                                min_row_distance=self.__src_min_row_distance)

        while len(self.__subcolumn_lengths) > 0:
            length = max(self.__subcolumn_lengths.keys())
            unsorted_subcolumns = self.__subcolumn_lengths[length]
            subcolumns = sorted(unsorted_subcolumns)
            transfer_subcolumn = subcolumns.pop(0)
            ssc = self.__get_column_with_equal_or_more_positions(length)
            if not ssc is None:
                self.__assign_subcolumn_positions(ssc, transfer_subcolumn)
            else:
                self.__devide_subcolumn(transfer_subcolumn)

            if len(subcolumns) < 1:
                del self.__subcolumn_lengths[length]
            else:
                self.__subcolumn_lengths[length] = subcolumns

        if not len(self._source_layout) == len(self._hash_values):
            msg = 'The number of final source positions (%i) does not match ' \
                  'the number of distinct hash values (%i). This should ' \
                  'not happen. Talk to IT, please.' \
                  % (len(self._source_layout), len(self._hash_values))
            self.add_error(msg)

    def __get_column_with_equal_or_more_positions(self, number_positions):
        """
        Returns a column having the requested number of free positions or more.
        """
        free_count = number_positions
        while free_count < self.__source_rack_shape.number_rows + 1:
            ssc = self.__get_column_with_equal_positions(free_count)
            if not ssc is None: return ssc
            free_count += 1

        return None

    def __get_column_with_less_positions(self, number_positions):
        """
        Returns a column having less than the requested number of free positions
        (but as much free positions as possible).
        """
        free_count = number_positions - 1
        while free_count > 0:
            ssc = self.__get_column_with_equal_positions(free_count)
            if not ssc is None: return ssc
            free_count -= 1

        msg = 'There is no unassigned position left in the source layout. ' \
              'This should not happen. Talk to IT, please.'
        self.add_error(msg)

    def __get_column_with_equal_positions(self, number_positions):
        """
        Returns a column having the requested number of free positions.
        """
        for ssc in self.__free_positions:
            if len(ssc) == number_positions:
                return ssc

        return None

    def __devide_subcolumn(self, subcolumn):
        """
        Devides a subcolumn into 2 parts, of which one stored and the second
        is put pack into the queue.
        """
        ssc = self.__get_column_with_less_positions(len(subcolumn))
        if not ssc is None:

            free_count = len(ssc)
            storage_subcolumn = subcolumn.split(free_count)
            self.__assign_subcolumn_positions(ssc, storage_subcolumn)

            add_list_map_element(self.__subcolumn_lengths, len(subcolumn),
                                 subcolumn)

    def __assign_subcolumn_positions(self, source_subcolumn,
                                     transfer_subcolumn):
        """
        Each transfer item in the subcolumn gets a position in the source
        layout.
        """
        for tid in transfer_subcolumn.transfer_items:
            rack_pos = source_subcolumn.get_position()
            self._add_source_position(rack_pos, tid.working_pos)

    def _add_source_position(self, rack_pos, working_pos): #pylint: disable=W0613
        """
        Creates a new source position and places it onto the given
        position of the source layout.
        """
        raise NotImplementedError('Abstract method.')


class TransferSubcolumn(object):
    """
    Represents a sub column, that is a group of transfer that can be covered
    by one Biomek movement (if two samples of column are to close to one
    another, they cannot be pipetted together)
    """

    def __init__(self, target_column_index, min_row_distance):
        """
        Constructor:

        :param min_row_distance: The minimum number of free wells that must be
            between 2 target wells for the biomek to be able to pipet them
            together.
        :type min_row_distance: :class:`int`
        """
        #: The minimum difference in row indices a potential further position
        #: must have.
        self.min_row_distance = min_row_distance
        #: The transfer items of this subcolumn.
        self.transfer_items = []
        #: The target row index of the transfer item added last.
        self.last_row_index = None
        #: The first column index of the first design rack layout this
        #: subcolumn occurs in.
        self.target_column_index = target_column_index

    def add_transfer_item(self, tid):
        """
        Adds a new transfer item and adjusts the :attr:`last_row_index`.
        """
        self.transfer_items.append(tid)
        self.last_row_index = tid.target_row_index

    def allows_transfer_item(self, tid):
        """
        Whether a transfer item can be accepted depends whether the
        :attr:`min_row_distance` to the :attr:`last_row_index` is met
        (given, both transfer item originate from the same column and
        design rack).
        """
        if self.last_row_index is None: return True
        return (tid.target_row_index - self.last_row_index) \
                                                > self.min_row_distance

    def remove_transfer_item(self, tid):
        """
        Removes a transfer item from the subcolumn.
        """
        self.transfer_items.remove(tid)

    def split(self, number_transfer_items):
        """
        Returns a new subcolumn that contains the first n elements of the
        :attr:`transfer_items` list (with n being number of tids). The
        referring transfer items are remove from the own list.

        :param number_transfer_items: The number of transfer to be passed to the
            new subcolumn.
        :type number_transfer_items: :class:`int`
        """
        new_subcolumn = TransferSubcolumn(
                                min_row_distance=self.min_row_distance,
                                target_column_index=self.target_column_index)

        while len(new_subcolumn) < number_transfer_items:
            tid = self.transfer_items.pop(0)
            new_subcolumn.add_transfer_item(tid)

        return new_subcolumn

    @property
    def hash_value(self):
        """
        The transfection hash values of all stored transfer items in the
        order of addition (to enable subcolumn sorting (required for
        reproducibility).
        """
        hash_value = '%i' % (self.target_column_index)
        for tid in self.transfer_items:
            hash_value += '-'
            hash_value += str(tid.hash_value)
        return hash_value

    def __len__(self):
        return len(self.transfer_items)

    def __cmp__(self, other):
        return cmp(self.hash_value, other.hash_value)

    def __iter__(self):
        return iter(self.transfer_items)

    def __repr__(self):
        str_format = '<%s length: %i, last row index: %i, hash: %s>'
        params = (self.__class__.__name__, len(self.transfer_items),
                  self.last_row_index, self.hash_value)
        return str_format % params


class SourceSubcolumn(object):
    """
    Helper class. Represents a sub column in the source plate. If two source  are
    wells to close together they cannot be used a source well in the same
    pipetting movement.
    """
    def __init__(self, column_index, free_row_indices):
        """
        Constructor:

        :param column_index: The column index within the source plate.
        :type column_index: :class:`int`

        :param free_row_indices: The row indices that have not been occupied
            yet.
        :type free_row_indices: :class:`list`
        """
        #: The column index within the source plate.
        self.column_index = column_index
        #: The row indices that are still available.
        self.free_row_indices = sorted(free_row_indices)

    def get_position(self):
        """
        Returns a position which is then remove from the pool.
        """
        row_index = self.free_row_indices.pop(0)
        return get_rack_position_from_indices(row_index, self.column_index)

    @classmethod
    def from_rack_shape(cls, rack_shape, min_row_distance):
        """
        Factory method returning a list with :class:`SourceSubColumn` objects
        for this rack shape. The row indices of the returned sub column will
        suitable to be pipetted in one movement (assuming the given minimum
        row distance).
        """
        source_sub_columns = []
        for c in range(rack_shape.number_columns):
            for start_row in range(min_row_distance + 1):
                row_indices = range(start_row, rack_shape.number_rows,
                                    (min_row_distance + 1))
                ssc = SourceSubcolumn(column_index=c,
                                      free_row_indices=row_indices)
                source_sub_columns.append(ssc)

        return source_sub_columns

    def __len__(self):
        return len(self.free_row_indices)

    def __str__(self):
        return '%i-%i' % (self.column_index, len(self.free_row_indices))

    def __repr__(self):
        str_format = '<%s column index: %i, free rows: %s>'
        params = (self.__class__.__name__, self.column_index,
                  self.free_row_indices)
        return str_format % params
