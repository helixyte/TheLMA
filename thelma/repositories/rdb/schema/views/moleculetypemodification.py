"""
Molecule modification view.
"""
from sqlalchemy.sql import and_
from sqlalchemy.sql import select

from thelma.repositories.rdb.view import view_factory
from thelma.entities.chemicalstructure import CHEMICAL_STRUCTURE_TYPE_IDS


__docformat__ = 'reStructuredText en'
__all__ = ['create_view']


VIEW_NAME = 'molecule_type_modification_view'


def create_view(metadata, molecule_design_tbl, molecule_design_structure_tbl,
                chemical_structure_tbl):
    """
    molecule_type_modification_view factory
    """
    md = molecule_design_tbl
    mds = molecule_design_structure_tbl
    chs = chemical_structure_tbl
    modification = \
      select([md.c.molecule_type_id.label('molecule_type_id'),
              chs.c.representation.label('name'),
              chs.c.chemical_structure_id],
             from_obj=md \
              .join(mds,
                    mds.c.molecule_design_id == md.c.molecule_design_id) \
              .join(chs,
                    and_(chs.c.chemical_structure_id ==
                                        mds.c.chemical_structure_id,
                         chs.c.structure_type_id ==
                                CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION))
             )
    return view_factory(VIEW_NAME, metadata, modification)
