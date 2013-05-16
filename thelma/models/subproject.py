"""
Subproject model classes.

FOG 11.2010, AAB
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_integer
from thelma.utils import get_utc_time

__docformat__ = "reStructuredText en"

__all__ = ['Subproject']


class Subproject(Entity):
    """
    This class represents subproject of projects.

    **Equality Condition**: equal :attr:`project` and equal :attr:`label`
    """

    #: The (human-readable) label of this subproject.
    label = None
    #: The project (:class:`thelma.models.project.Project`) this subproject
    #: belongs to. It is backreferenced by ORM.
    project = None
    #: The date the subproject was created in the database.
    creation_date = None
    #: Indicates whether the subproject is still active or already completed.
    active = None

    def __init__(self, label,
                 creation_date=None, active=False, project=None, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        if creation_date is None:
            creation_date = get_utc_time()
        self.creation_date = creation_date
        self.active = active
        if project is not None:
            self.project = project

    @property
    def title(self):
        return self.project.label + ' - ' + self.label

    def update(self, member):
        """
        This function edits the :attr:`label` and :attr:`active` attributes
        of the object.

        :param member: A subproject (member of a collection)
        """
        self.label = member.label
        self.active = member.active

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_integer(self.id)

    def __eq__(self, other):
        return (isinstance(other, Subproject) \
                and other.project == self.project \
                and other.label == self.label)

    def __str__(self):
        return '%i' % (self.id)

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, project: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.project)
        return str_format % params