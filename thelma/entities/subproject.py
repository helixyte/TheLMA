"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Subproject entity classes.

Created 11.2010
"""
from everest.entities.base import Entity
from thelma.utils import get_utc_time


__docformat__ = "reStructuredText en"
__all__ = ['Subproject']


class Subproject(Entity):
    """
    A subproject of a project.
    """
    #: The (human-readable) label of this subproject.
    label = None
    #: The project (:class:`thelma.entities.project.Project`) this subproject
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

    def __eq__(self, other):
        """
        Equality is based on the project and label attributes.
        """
        return (isinstance(other, Subproject) \
                and other.project == self.project \
                and other.label == self.label)

    def __str__(self):
        return '%i' % (self.id)

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, project: %s>'
        params = (self.__class__.__name__, self.id, self.label, self.project)
        return str_format % params
