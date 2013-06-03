"""
Project mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.organization import Organization
from thelma.models.project import Project
from thelma.models.subproject import Subproject
from thelma.models.user import User

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
