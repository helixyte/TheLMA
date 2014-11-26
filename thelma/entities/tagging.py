"""
Tagging entity classes.
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
    Machine tag.

    Machine tags have a domain (namespace), a predicate, and a value;
    see http://tagaholic.me/2009/03/26/what-are-machine-tags.html.

    Equality is based on domain, predicate, and value.
    """
    #: Tag domain in which the predicate-value combination is unique.
    domain = None
    #: Tag predicate (e.g., *Cell line*).
    predicate = None
    #: Tag value (e.g.. *SKMC-33*).
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
    Record for a single tagging event.
    """
    #: Tag (:class:`Tag`) to attach.
    tag = None
    #:Object to attach the tag to.
    #: (:class:`Tagged`)
    tagged = None
    #: User (:class:`thelma.entities.user.User`) performing the taggign.
    user = None

    def __init__(self, tag, tagged, user, **kw):
        """
        Constructor.

        :param tag: tag for this tagging.
        :type tag: :class:`Tag`.
        :param tagged: object to tag.
        :type tagged: :class:`Tagged`
        :param user: User performing the tagging.
        :type user: class:`thelma.entities.user.User`
        """
        Entity.__init__(self, **kw)
        self.tag = tag
        self.tagged = tagged
        self.user = user


class Tagged(Entity):
    """
    Object associated with a set of tags.
    """
    #: `set` of tags (:class:`Tag`).
    tags = set()
    #: `list` of taggings (:class:`Tagging`).
    taggings = None

    def __init__(self, tags, user):
        """
        Constructor.

        :param set tags: Set of :class:`Tag` instances associated to the rack
            positions.
        :param user: User who creates the tagged object.
        :type user: class:`thelma.entities.user.User`
        """
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
    Associates a set of rack positions with a set of tags.

    The :attr:`tags` set is initialized by the :class:`Tagged` constructor.

    Equality is determined using the tag set and the hash_value of the rack
    position set.
    """
    #: Associated rack position set
    #: (:class:`thelma.entities.rack.RackPositionSet`).
    rack_position_set = None

    def __init__(self, tags, rack_position_set, user=None):
        """
        Constructor.

        :param rack_position_set: Rack position set.
        :type rack_position_set: class:`thelma.entities.rack.RackPositionSet`
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
