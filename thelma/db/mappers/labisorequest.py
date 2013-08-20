"""
Lab ISO request mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import LabIsoRequest
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.user import User

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

def create_mapper(iso_request_mapper,
                  lab_iso_request_tbl,
                  experiment_metadata_iso_request_tbl,
                  reservoir_specs_tbl):
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
                    iso_plate_reservoir_specs=relationship(ReservoirSpecs,
                           uselist=False,
                           primaryjoin=lir.c.iso_plate_reservoir_specs_id == \
                            rs.c.reservoir_specs_id)
                               ),
               polymorphic_identity=ISO_TYPES.LAB,
               )

    return m
