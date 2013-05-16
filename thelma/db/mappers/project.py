"""
Project mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.organization import Organization
from thelma.models.project import Project
from thelma.models.subproject import Subproject
from thelma.models.user import User

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(project_tbl):
    "Mapper factory."
    m = mapper(Project, project_tbl,
               properties=dict(
                    id=synonym('project_id'),
                    customer=relationship(Organization, uselist=False),
                    subprojects=relationship(Subproject,
                                             back_populates='project',
                                             cascade='all, delete-orphan'
                                             ),
                    leader=relationship(User, uselist=False),
                    ),
               )
    if isinstance(Project.slug, property):
        Project.slug = \
            hybrid_property(Project.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.label))
    return m
