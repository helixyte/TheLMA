"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Subproject mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.project import Project
from thelma.entities.subproject import Subproject


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(subproject_tbl):
    "Mapper factory."
    m = mapper(
         Subproject, subproject_tbl,
         id_attribute='subproject_id',
         properties=
          dict(project=relationship(Project, uselist=False,
                                    back_populates='subprojects',
                                    cascade='save-update'),
#               molecule_design_set=
#                 relationship(MoleculeDesignSet,
#                              uselist=False,
#                              secondary=
#                                subproject_molecule_designs_and_targets_tbl),
               )
          )
    return m
