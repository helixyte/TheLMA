select assert('(select version from db_version) = 16.1');

-- remove unique rack contraint from ISO aliquot and ISO preparation plate
-- table to enable use of library plates and sharing of job plates
-- (this will become obsolete by the ISO revision - it is only a temporary
-- hack)

ALTER TABLE iso_aliquot_plate DROP CONSTRAINT unique_rack;
ALTER TABLE iso_preparation_plate DROP CONSTRAINT unique_plate;


create or REPLACE view db_version as select 16.2 as version;