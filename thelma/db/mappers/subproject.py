"""
Subproject mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.project import Project
from thelma.models.subproject import Subproject

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(subproject_tbl):
    "Mapper factory."
    m = mapper(
         Subproject, subproject_tbl,
         properties=
          dict(id=synonym('subproject_id'),
               project=relationship(Project, uselist=False,
                                    back_populates='subprojects',
                                    cascade='save-update'),
#               molecule_design_set=
#                 relationship(MoleculeDesignSet,
#                              uselist=False,
#                              secondary=
#                                subproject_molecule_designs_and_targets_tbl),
#               target_set=
#                 relationship(TargetSet,
#                              uselist=False,
#                              secondary=
#                                subproject_molecule_designs_and_targets_tbl),
#               experiment_metadatas=relationship(ExperimentMetadata),
               )
          )
    if isinstance(Subproject.slug, property):
        Subproject.slug = \
            hybrid_property(Subproject.slug.fget,
                            expr=lambda cls: cast(cls.subproject_id, String))
    return m
