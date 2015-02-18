"""container_rack_overhaul

Revision ID: 1d6d30bd88b6
Revises: 4cc7cebe2c0
Create Date: 2015-01-07 10:54:12.903913

"""
from thelma.entities.rack import RACK_TYPES
from thelma.entities.container import CONTAINER_TYPES

# revision identifiers, used by Alembic.
revision = '1d6d30bd88b6'
down_revision = '4cc7cebe2c0'

from alembic import op
import sqlalchemy as sa

# op module has magic attributes pylint: disable=E1101

def upgrade():
    op.create_table(
        'plate',
        sa.Column('rack_id', sa.Integer, sa.ForeignKey('rack.rack_id'),
                  primary_key=True))
    op.execute("insert into plate"
               " (select rack_id from rack where rack_type='%s')"
               % RACK_TYPES.PLATE
               )
    op.create_table(
        'tube_rack',
        sa.Column('rack_id', sa.Integer, sa.ForeignKey('rack.rack_id'),
                  primary_key=True))
    op.execute("insert into tube_rack"
               " (select rack_id from rack where rack_type='%s')"
               % RACK_TYPES.TUBE_RACK
               )
    op.create_table(
        'well',
        sa.Column('container_id', sa.Integer, primary_key=True),
        sa.Column('rack_id', sa.Integer, nullable=False),
        sa.Column('rack_position_id', sa.Integer, nullable=False)
        )
    op.execute("insert into well"
               " (select c.container_id,"
               "  cnt.holder_id as rack_id,"
               "  cnt.rack_position_id"
               "  from container c"
               "    inner join containment cnt on cnt.held_id=c.container_id"
               "  where container_type='%s')"
               % CONTAINER_TYPES.WELL)
    # Only now add the foreign key constraints to avoid triggers during
    # insert.
    op.create_foreign_key('fk_well_container_id_container',
                          'well', 'container',
                          ['container_id'], ['container_id'])
    op.create_foreign_key('fk_well_rack_id_plate',
                          'well', 'plate',
                          ['rack_id'], ['rack_id'])
    op.create_foreign_key('fk_well_rack_position_id_rack_position',
                          'well', 'rack_position',
                          ['rack_position_id'], ['rack_position_id'])
    op.create_table(
        'tube',
        sa.Column('container_id', sa.Integer, primary_key=True),
        sa.Column('barcode', sa.String, nullable=False)
        )
    op.execute("insert into tube"
               " (select c.container_id, cb.barcode"
               "  from container c inner join container_barcode cb"
               "  on cb.container_id=c.container_id"
               "  where c.container_type='%s')"
               % CONTAINER_TYPES.TUBE)
    # Only now add the foreign key constraints to avoid triggers during
    # insert.
    op.create_foreign_key('fk_tube_container_id_container',
                          'tube', 'container',
                          ['container_id'], ['container_id'])
    # Drop the foreign key on container and rack.
    op.drop_constraint('$2', 'containment')
    op.drop_constraint('holder_id', 'containment')
    # Delete all WELL records from containment (the containment information
    # was moved to the new well table).
    op.execute("delete from containment"
               "  using container"
               "  where container.container_id=containment.held_id"
               "    and container.container_type='%s'"
               % CONTAINER_TYPES.WELL)
    # Drop the spurious row and col columns; drop dependent views first.
    op.execute('drop view container_info')
    op.execute('drop view racked_molecule_sample')
    op.execute('drop view racked_sample')
    op.execute('drop view racked_tube')
    op.drop_column('containment', 'row')
    op.drop_column('containment', 'col')
    # Rename and add foreign keys to tube_rack and tube.
    op.execute("alter table containment rename to tube_location")
    op.execute('alter table tube_location'
               '  rename column held_id to container_id')
    op.execute('alter table tube_location'
               '  rename column holder_id to rack_id')
    op.create_unique_constraint('uq_tube_location_rack_id_rack_position_id',
                                'tube_location',
                                ['rack_id', 'rack_position_id'])
    op.create_foreign_key('fk_tube_location_rack_id_tube_rack',
                          'tube_location', 'tube_rack',
                          ['rack_id'], ['rack_id'],
                          onupdate='CASCADE', ondelete='CASCADE')
    op.create_foreign_key('fk_tube_location_container_id_tube',
                          'tube_location', 'tube',
                          ['container_id'], ['container_id'])
    op.drop_table('container_barcode')
    #
    op.execute("create view molecule_supplier_molecule_design_view as"
               " select m.molecule_id, smd.supplier_molecule_design_id"
               "  from molecule m"
               "   inner join single_supplier_molecule_design ssmd"
               "   on ssmd.molecule_design_id=m.molecule_design_id"
               "   inner join supplier_molecule_design smd"
               "   on smd.supplier_molecule_design_id="
               "   ssmd.supplier_molecule_design_id"
               " where smd.is_current and smd.supplier_id=m.supplier_id")
    op.execute("create table molecule_supplier_molecule_design"
               "(molecule_id integer primary key"
               " references"
               "   molecule(molecule_id),"
               " supplier_molecule_design_id integer not null"
               " references"
               "   supplier_molecule_design(supplier_molecule_design_id)"
               ")")
    op.execute("create or replace function "
               "refresh_molecule_supplier_molecule_design()"
               " returns trigger as $$"
               " begin"
               " delete from molecule_supplier_molecule_design;"
               " insert into molecule_supplier_molecule_design"
               " select * from molecule_supplier_molecule_design_view;"
               " return null;"
               " end"
               " $$ language 'plpgsql'")

def downgrade():
    raise NotImplementedError('Downgrade not implemented for this migration.')
