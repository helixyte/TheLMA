"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Lab ISO request mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.experiment import ExperimentMetadata
from thelma.entities.iso import ISO_TYPES
from thelma.entities.iso import LabIsoRequest
from thelma.entities.library import MoleculeDesignLibrary
from thelma.entities.liquidtransfer import ReservoirSpecs
from thelma.entities.racklayout import RackLayout
from thelma.entities.user import User


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(iso_request_mapper, lab_iso_request_tbl,
                  experiment_metadata_iso_request_tbl, reservoir_specs_tbl,
                  molecule_design_library_lab_iso_request_tbl):
    "Mapper factory."
    lir = lab_iso_request_tbl
    emir = experiment_metadata_iso_request_tbl
    rs = reservoir_specs_tbl
    m = mapper(LabIsoRequest, lab_iso_request_tbl,
               inherits=iso_request_mapper,
               properties=dict(
                    requester=relationship(User, uselist=False),
                    rack_layout=relationship(RackLayout, uselist=False,
                                cascade='all,delete,delete-orphan',
                                single_parent=True),
                    experiment_metadata=relationship(ExperimentMetadata,
                                             secondary=emir, uselist=False,
                                             back_populates='lab_iso_request'),
                    molecule_design_library=relationship(
                         MoleculeDesignLibrary, uselist=False,
                         secondary=molecule_design_library_lab_iso_request_tbl),
                    iso_plate_reservoir_specs=relationship(ReservoirSpecs,
                           uselist=False,
                           primaryjoin=lir.c.iso_plate_reservoir_specs_id == \
                            rs.c.reservoir_specs_id)
                               ),
               polymorphic_identity=ISO_TYPES.LAB,
               )
    return m
