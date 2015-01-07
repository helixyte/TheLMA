"""rack position fkey

Revision ID: 4cc7cebe2c0
Revises: 22dfaa77e9a1
Create Date: 2015-01-05 10:16:40.762142

"""

# revision identifiers, used by Alembic.
revision = '4cc7cebe2c0'
down_revision = '22dfaa77e9a1'

from alembic import op
import sqlalchemy as sa

# op module has magic attributes pylint: disable=E1101

def upgrade():
    op.add_column('containment',
                  sa.Column('rack_position_id', sa.Integer,
                            sa.ForeignKey('rack_position.rack_position_id')))
    # Populate new rack position ID column.
    op.execute('update containment '
               'set rack_position_id=(select rp.rack_position_id from '
               '    rack_position rp '
               '        where (rp.row_index, rp.column_index) = '
               '              (containment.row, containment.col))')
    # Add NOT NULL constraint.
    op.alter_column('containment', 'rack_position_id', nullable=False)


def downgrade():
    op.drop_column('containment', 'rack_position_id')
