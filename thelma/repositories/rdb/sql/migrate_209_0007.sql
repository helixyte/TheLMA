-- create pool set tables for ISOs and experiment metadata

select assert('(select version from db_version) = 209.0006');

alter table tube_transfer_worklist 
    alter column timestamp type timestamp with time zone;
alter table tube_transfer_worklist 
    alter column timestamp type timestamp with time zone using timestamp at time zone 'utc';
alter table executed_transfer 
    alter column timestamp type timestamp with time zone;
alter table executed_transfer 
    alter column timestamp type timestamp with time zone using timestamp at time zone 'utc';
alter table tagging 
    alter column time_stamp type timestamp with time zone;
alter table tagging 
    alter column time_stamp type timestamp with time zone using time_stamp at time zone 'utc';
alter table sample_registration 
    alter column time_stamp type timestamp with time zone;
alter table sample_registration
    alter column time_stamp type timestamp with time zone using time_stamp at time zone 'utc';
alter table rack_barcoded_location_log 
    alter column date type timestamp with time zone;
alter table rack_barcoded_location_log
    alter column date type timestamp with time zone using date at time zone 'utc';
alter table acquisition 
    alter column time_stamp type timestamp with time zone;
alter table acquisition
    alter column time_stamp type timestamp with time zone using time_stamp at time zone 'utc';
--Need to drop and recreate this view to change the column type in
--supplier_molecle_design.
drop view supplier_molecule_design_view;
alter table supplier_molecule_design 
    alter column time_stamp type timestamp with time zone;
alter table supplier_molecule_design
    alter column time_stamp type timestamp with time zone using time_stamp at time zone 'utc';
create or replace view supplier_molecule_design_view as
select supplier_molecule_design_id,
       supplier_id,
       product_id,
       time_stamp,
       design_type
from supplier_molecule_design
where is_current;

create or replace view db_version as select 209.0007 as version;