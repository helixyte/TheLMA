"""
Rack layout entity classes.

Created Nov 26, 2010
"""
from everest.entities.base import Entity

__docformat__ = "reStructuredText en"
__all__ = ['RackLayout']


class RackLayout(Entity):
    """
    Rack layout.

    A rack layout is a set of tagged rack position sets for a given rack
    shape. Each rack position can have multiple tags and each tag can be
    assigned to multiple rack positions. Best conceptualized as a stack of
    tag x rack position matrices.
    """
    #: Dimension of the layout (:class:`thelma.entities.rack.RackShape`).
    shape = None
    #: List of tagged rack position sets.
    tagged_rack_position_sets = None

    __initialized = False

    def __init__(self, shape=None, tagged_rack_position_sets=None, **kw):
        Entity.__init__(self, **kw)
        self.shape = shape
        if tagged_rack_position_sets is None:
            tagged_rack_position_sets = []
        self.tagged_rack_position_sets = tagged_rack_position_sets
        self.__tag_to_positions_map = None
        self.__position_to_tags_map = None
        self.__all_tags = None
        self.__all_positions = None

    def add_tagged_rack_position_set(self, tagged_rack_position_set):
        """
        Adds the given rack position set to this rack layout.

        @param tagged_rack_position_set: Tagged rack position set to tadd.
        @type tagged_rack_position_set:
                :class:`thelma.entities.tagging.TaggedRackPositionSet`
        """
        if not self.__initialized:
            self.__initialize()
        self.tagged_rack_position_sets.append(tagged_rack_position_set)
        self.__process_tagged_rack_position_set(tagged_rack_position_set)

    def get_tags(self):
        """
        Returns all tags in this layout.

        :rtype: set of :class:`thelma.entities.tagging.Tag`
        """
        if not self.__initialized:
            self.__initialize()
        return self.__all_tags

    def get_positions(self):
        """
        Returns all rack positions in this layout.

        :rtype: set of :py:class:`thelma.entities.rack.RackPosition`
        """
        if not self.__initialized:
            self.__initialize()
        return self.__all_positions

    def get_tags_for_position(self, position):
        """
        Returns all tags for the given rack position.

        :param position: The rack position whose tags you want to get.
        :type position: :class:`thelma.entities.rack.RackPosition`
        :return: Set of all tags for the given position (empty set if there is
            no tag associated with the given position).
        :rtype: set of :py:class:`thelma.entities.tagging.Tag`
        """
        if not self.__initialized:
            self.__initialize()
        tags = self.__position_to_tags_map.get(position)
        if tags is None:
            tags = set()
        return tags

    def get_positions_for_tag(self, tag):
        """
        Returns all rack position having the given tag.

        :param tag: The tag whose positions you want to get.
        :type tag: :class:`thelma.entities.tagging.Tag`
        :return: Set of all positions for the given tag (empty set if there is
            no position associated with the given tag).
        :rtype: set of :class:`thelma.entities.rack.RackPosition`
        """
        if not self.__initialized:
            self.__initialize()
        poss = self.__tag_to_positions_map.get(tag)
        if poss is None:
            poss = set()
        return poss

    def has_positions(self):
        """
        Checks if this rack layout has any tagged positions.

        :return: Test result.
        :rtype: bool
        """
        if not self.__initialized:
            self.__initialize()
        return len(self.__all_positions) > 0

    def has_tags(self):
        """
        Checks if this rack layout has any tags.

        :return: Test result.
        :rtype: bool
        """
        if not self.__initialized:
            self.__initialize()
        return len(self.__all_tags) > 0

    def __str__(self):
        return '%s' % (self.id)

    def __repr__(self):
        str_format = '<%s id: %s, shape: %s, # tagged position sets: %i>'
        params = (self.__class__.__name__, self.id, self.shape,
                  len(self.tagged_rack_position_sets))
        return str_format % params

    def __initialize(self):
        self.__all_tags = set()
        self.__all_positions = set()
        self.__position_to_tags_map = {}
        self.__tag_to_positions_map = {}
        for trps in self.tagged_rack_position_sets:
            self.__process_tagged_rack_position_set(trps)

    def __process_tagged_rack_position_set(self, tagged_rack_position_set):
        tags = tagged_rack_position_set.tags
        poss = tagged_rack_position_set.rack_position_set
        for tag in tags:
            tposs = self.__tag_to_positions_map.get(tag)
            if tposs is None:
                self.__tag_to_positions_map[tag] = poss.positions.copy()
            else:
                tposs.update(poss)
        self.__all_positions.update(poss)
        for rack_pos in poss:
            rptags = self.__position_to_tags_map.get(rack_pos)
            if rptags is None:
                self.__position_to_tags_map[rack_pos] = tags.copy()
            else:
                rptags.update(tags)
        self.__all_tags.update(tags)
