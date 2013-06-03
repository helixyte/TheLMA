"""
ISO request mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from thelma.db.mappers.utils import CaseInsensitiveComparator
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import Iso
from thelma.models.iso import IsoRequest
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.racklayout import RackLayout
from thelma.models.user import User

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


#FIXME: no name on DB level #pylint: disable=W0511
def create_mapper(iso_request_tbl, worklist_series_iso_request_tbl,
                  experiment_metadata_iso_request_tbl):
    "Mapper factory."

    wsir = worklist_series_iso_request_tbl
    emir = experiment_metadata_iso_request_tbl

    m = mapper(IsoRequest, iso_request_tbl,
               id_attribute='iso_request_id',
               properties=
                    dict(requester=relationship(User, uselist=False),
                         iso_layout=relationship(RackLayout, uselist=False,
                                cascade='all,delete,delete-orphan',
                                single_parent=True),
                         owner=column_property(iso_request_tbl.c.owner,
                                comparator_factory=CaseInsensitiveComparator
                                ),
                         experiment_metadata=relationship(ExperimentMetadata,
                                                    secondary=emir,
                                                    uselist=False),
                         isos=relationship(Iso, back_populates='iso_request'),
                         worklist_series=relationship(WorklistSeries,
                                uselist=False, secondary=wsir,
                                cascade='all,delete,delete-orphan',
                                single_parent=True),
                    ),
               ),
    return m
