"""
Project entity classes.

FOG 11.2010, AAB
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_string
from thelma.utils import get_utc_time

__docformat__ = "reStructuredText en"

__all__ = ['Project']


class Project(Entity):
    """
    This class is for the representation of projects.

    **Equality Condition**: equal :attr:`id`
    """

    #: The (human-readable) label of this project.
    label = None
    #: Equals the :attr:`label`. Titles are required for atom templates.
    title = None
    #: The customer who ordered the project
    #: (:class:`thelma.entities.organization.Organization`).
    customer = None
    #: The date the project was created in the database.
    creation_date = None
    #: The official project leader at Cenix (:class:`thelma.entities.user.User`).
    leader = None
    #: Subprojects (:class:`thelma.entities.subproject.Subproject`) belonging
    #: to this project.
    subprojects = None

    def __init__(self, label, leader,
                 customer=None, creation_date=None, subprojects=None, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.title = label
        self.customer = customer
        self.leader = leader
        if creation_date is None:
            creation_date = get_utc_time()
        self.creation_date = creation_date
        if subprojects is None:
            subprojects = []
        self.subprojects = subprojects

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`label`.
        return slug_from_string(self.label)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, leader: %s, creation date: %s, ' \
                 'subprojects: %s>'
        subprj = ', '.join([str(m) for m in self.subprojects])
        params = (self.__class__.__name__, self.id, self.label, self.leader,
                  self.creation_date, subprj)
        return str_format % params
