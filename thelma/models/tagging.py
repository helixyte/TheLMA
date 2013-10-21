"""
Tagging model classes.

FOG Nov 25, 2010, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = "reStructuredText en"

__all__ = ['Tag',
           'Tagging',
           'Tagged',
           'TaggedRackPositionSet']


class Tag(Entity):
    """
    Objecs of this class represents machine tags. Machine tags have a
    domain (namespace), a predicate, and a value.
    See http://tagaholic.me/2009/03/26/what-are-machine-tags.html

    **Equality Condition**: equal :attr:`domain`, :attr:`predicate` and
    :attr:`value`
    """

    #: The domain in which the predicate-value combination is unique.
    domain = None
    #: A sort of parameter, e.g. *cell line*.
    predicate = None
    #: The value the parameter, e.g. *SKMC-33*.
    value = None

    def __init__(self, domain, predicate, value, **kw):
        Entity.__init__(self, **kw)
        self.domain = domain
        self.predicate = predicate
        self.value = self.__strip_value(value)

    def is_similar(self, other):
        """
        Checks whether two tags are equal but neglects the tag domain.
        """
        return isinstance(other, Tag) \
               and other.predicate == self.predicate \
               and other.value == self.value

    @property
    def slug(self):
        #: For instance of this class the slug is composed as follows:
        #: [:attr:`domain` \: :attr:`predicate` \= :attr:`value`\]
        #: (without white space around the special characters).
        return slug_from_string("%s:%s=%s" %
                                (self.domain, self.predicate, self.value))

    def __eq__(self, other):
        return isinstance(other, Tag) \
               and other.domain == self.domain \
               and other.predicate == self.predicate \
               and other.value == self.value

    def __hash__(self):
        return hash((self.domain, self.predicate, self.value))

    def __str__(self):
        return '%s:%s=%s' % (self.domain, self.predicate, self.value)

    def __repr__(self):
        str_format = '<%s domain: %s, predicate: %s, value: %s>'
        params = (self.__class__.__name__, self.domain, self.predicate,
                  self.value)
        return str_format % params

    def __strip_value(self, value):
        # Remove the '.0' from numeric values.
        # FIXME: This looks VERY much like a hack. # pylint:disable=W0511
        value = str(value)
        if value.endswith('.0'):
            value = value[:-2]
        return value


class Tagging(Entity):
    """
    This class records by whom a tag has been added to an object.
    Taggings are ususally created upon instatiation of
    :class:`Tagged` objects.

    **Equality Condition**: Not implemented so far
    """

    #: The associated tag (:class:`Tag`)
    tag = None
    #: The object to which the tag has been attached
    #: (:class:`Tagged`)
    tagged = None
    #: The user (:class:`thelma.models.user.User`) who has attached the tag
    user = None

    def __init__(self, tag, tagged, user, **kw):
        Entity.__init__(self, **kw)
        self.tag = tag
        self.tagged = tagged
        self.user = user


class Tagged(Entity):
    """
    This represents an object associated with a set of tags.
    It contains all attributes of the parent entity plus a tag set
    (:attr:`tags`).

    **Equality Condition**: Not implemented so far
    """

    #: A set of tags (:class:`Tag`).
    tags = set()
    #: A list of taggings (:class:`Tagging`).
    taggings = None

    def __init__(self, tags, user):
        Entity.__init__(self)
        if len(tags) < 1:
            raise ValueError('The tag list is empty!')
        self.taggings = [Tagging(tag, self, user) for tag in tags]
        self.tags = tags

    def add_tag(self, tag, user):
        """
        Adds a tag to the tag list (including generation of new
        :class:`Tagging` objects).
        """
        self.taggings.append(Tagging(tag, self, user))
        self.tags.add(tag)

    def __iter__(self):
        return iter(tg for tg in self.taggings)


class TaggedRackPositionSet(Tagged):
    """
    This class associated a set of rack positions within a layout
    with a set of tags. The :attr:`tags` set is initialized by the
    :class:`Tagged` constructor.

    **Equality Condition**: equal :attr:`tags` and :attr:`hash_value` of
    the rack position set (:class:`thelma.models.rack.RackPositionSet`)

    """

    #: The associated rack position set
    #: (:class:`thelma.models.rack.RackPositionSet`).
    rack_position_set = None

    def __init__(self, tags, rack_position_set, user=None):
        """
        :param tags: A set of tags associated to the rack positions.
        :type tags: set of :class:`Tag`

        :param rack_position_set: A rack position set.
        :type rack_position_set: class:`thelma.models.rack.RackPositionSet`

        :param user: The user who has created the object.
        :type user: class:`thelma.models.user.User`
        """
        Tagged.__init__(self, set(tags), user)
        self.rack_position_set = rack_position_set

    def __eq__(self, other):
        return isinstance(other, TaggedRackPositionSet) \
               and self.tags == other.tags \
               and self.rack_position_set.hash_value \
                                        == other.rack_position_set.hash_value

    def __repr__(self):
        str_format = '<%s id: %s rack position set: %s>'
        param = (self.__class__.__name__, self.id, self.rack_position_set)
        return str_format % param
