"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Project mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.organization import Organization
from thelma.entities.project import Project
from thelma.entities.subproject import Subproject
from thelma.entities.user import User


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(project_tbl):
    "Mapper factory."
    m = mapper(Project, project_tbl,
               id_attribute='project_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                    customer=relationship(Organization, uselist=False),
                    subprojects=relationship(Subproject,
                                             back_populates='project',
                                             cascade='all, delete-orphan'
                                             ),
                    leader=relationship(User, uselist=False),
                    ),
               )
    return m
