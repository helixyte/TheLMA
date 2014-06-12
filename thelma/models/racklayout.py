"""
Rack layout model classes.

FOG Nov 26, 2010
"""

from everest.entities.base import Entity

__docformat__ = "reStructuredText en"

__all__ = ['RackLayout']


class RackLayout(Entity):
    """
    A rack layout is a set of tagged rack position sets for a given rack
    shape. Each rack position can have multiple tags and each tag can be
    assigned to multiple rack positions. Best conceptualized as a stack of
    tag x rack position matrices.

    **Equality Condition**: not implemented yet
    """

    #: the dimension of the layout (:class:`thelma.model.rack.RackShape`).
    shape = None

    tagged_rack_position_sets = None

    def __init__(self, shape=None, tagged_rack_position_sets=None, **kw):
        Entity.__init__(self, **kw)
        self.shape = shape
        if tagged_rack_position_sets is None:
            tagged_rack_position_sets = []
        self.tagged_rack_position_sets = tagged_rack_position_sets

    def get_tags(self):
        """
        Returns all tags in this layout.

        :rtype: set of :class:`thelma.models.tagging.Tag`
        """
        tags = set()
        for tp in self.tagged_rack_position_sets:
            for tag in tp.tags:
                tags.add(tag)
        return tags

    def get_positions(self):
        """
        Returns all rack positions in this layout.

        :rtype: set of :py:class:`thelma.models.rack.RackPosition`
        """
        positions = set()
        for trps in self.tagged_rack_position_sets:
            for position in trps.rack_position_set:
                positions.add(position)
        return positions

    def get_tags_for_position(self, position):
        """
        Returns all tags for the given rack position.

        :param position: The rack position whose tags you want to get.
        :type position: :class:`thelma.models.rack.RackPosition`
        :return: All tags for the given position.
        :rtype: set of :py:class:`thelma.models.tagging.Tag`
        """
        tags = []
        for tprs in self.tagged_rack_position_sets:
            if position in tprs.rack_position_set:
                for tag in tprs.tags:
                    tags.append(tag)
        return set(tags)

    def get_positions_for_tag(self, tag):
        """
        Returns all rack position having the given tag.

        :param tag: The tag whose positions you want to get.
        :type tag: :class:`thelma.models.tagging.Tag`
        :return: All positions for the given tag.
        :rtype: set of :class:`thelma.models.rack.RackPosition`
        """
        positions = set()
        for tp in self.tagged_rack_position_sets:
            if tag in tp.tags:
                for position in tp.rack_position_set.positions:
                    positions.add(position)
        return positions

    def has_positions(self):
        """
        Checks if this rack layout has any tagged positions.

        :return: Test result.
        :rtype: bool
        """
        result = False
        for trps in self.tagged_rack_position_sets:
            if len(trps.rack_position_set) > 0:
                result = True
                break
        return result

    def __str__(self):
        return '%s' % (self.id)

    def __repr__(self):
        str_format = '<%s id: %s, shape: %s, No. of tagged positions sets: %i>'
        params = (self.__class__.__name__, self.id, self.shape,
                  len(self.tagged_rack_position_sets))
        return str_format % params
