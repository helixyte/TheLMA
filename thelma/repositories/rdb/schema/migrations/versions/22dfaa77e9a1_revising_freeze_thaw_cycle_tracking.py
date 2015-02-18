"""Revising freeze/thaw cycle tracking.

Revision ID: 22dfaa77e9a1
Revises: 227c832e89fb
Create Date: 2014-12-19 10:10:45.284405

"""

# revision identifiers, used by Alembic.
revision = '22dfaa77e9a1'
down_revision = '227c832e89fb'

from alembic import op
import sqlalchemy as sa

# op module has magic attributes pylint: disable=E1101

def upgrade():
    op.add_column('sample',
                  sa.Column('freeze_thaw_cycles', sa.Integer))
    op.add_column('sample', sa.Column('checkout_date',
                                      sa.DateTime(timezone=True)))
    # Fill the new freeze thaw cycle field. We use the maximum of all sample
    # molecule f/t cycles.
    op.execute('select s.sample_id, max(sm.freeze_thaw_cycles) as ftc'
               ' into tmp_max_ftc'
               ' from sample s'
               ' inner join sample_molecule sm'
               ' on sm.sample_id=s.sample_id'
               ' where s.sample_id=s.sample_id group by s.sample_id')
    op.execute('alter table tmp_max_ftc'
               ' add constraint tmp_max_ftc_sample_id_uq'
               'unique (sample_id)')
    op.execute('update sample'
               ' set freeze_thaw_cycles=tmp.ftc'
               ' from tmp_max_ftc tmp'
               ' where tmp.sample_id=sample.sample_id')
    op.execute('drop table tmp_max_ftc')


def downgrade():
    op.drop_column('sample', 'freeze_thaw_cycles')
    op.drop_column('sample', 'checkout_date')

# pylint: enable=E1101
