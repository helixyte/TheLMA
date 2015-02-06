"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Lab ISO request table.
"""
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.schema import PrimaryKeyConstraint


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_request_tbl, user_tbl, rack_layout_tbl,
                 reservoir_specs_tbl):
    "Table factory."
    tbl = Table('lab_iso_request', metadata,
                Column('iso_request_id', Integer,
                       ForeignKey(iso_request_tbl.c.iso_request_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('requester_id', Integer,
                       ForeignKey(user_tbl.c.db_user_id),
                       nullable=False),
                Column('delivery_date', Date),
                Column('comment', Text),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('iso_plate_reservoir_specs_id', Integer,
                       ForeignKey(reservoir_specs_tbl.c.reservoir_specs_id,
                                  ondelete='NO ACTION', onupdate='NO ACTION'),
                       nullable=False),
                Column('process_job_first', Boolean, nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.iso_request_id)
    return tbl
