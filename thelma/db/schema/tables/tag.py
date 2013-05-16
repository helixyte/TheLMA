"""
Tag table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    # The tag domain, predicate and value tables are not used
    # anywhere else, so we keep them local in this module for now.
    tag_domain_tbl = \
        Table('tag_domain', metadata,
              Column('tag_domain_id', Integer, primary_key=True),
              Column('domain', String,
                     CheckConstraint('length(domain)>0'), nullable=False),
              )
    tag_predicate_tbl = \
        Table('tag_predicate', metadata,
              Column('tag_predicate_id', Integer, primary_key=True),
              Column('predicate', String,
                     CheckConstraint('length(predicate)>0'), nullable=False),
              )
    tag_value_tbl = \
        Table('tag_value', metadata,
              Column('tag_value_id', Integer, primary_key=True),
              Column('value', String,
                     CheckConstraint('length(value)>0'), nullable=False)
              )
    tag_tbl = \
        Table('tag', metadata,
              Column('tag_id', Integer, primary_key=True),
              Column('tag_domain_id', Integer,
                     ForeignKey(tag_domain_tbl.c.tag_domain_id),
                     nullable=False),
              Column('tag_predicate_id', Integer,
                     ForeignKey(tag_predicate_tbl.c.tag_predicate_id),
                     nullable=False),
              Column('tag_value_id', Integer,
                     ForeignKey(tag_value_tbl.c.tag_value_id),
                     nullable=False),
              )
    return tag_tbl
