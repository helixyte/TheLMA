-- Remove destination_plate_specs_id from table new_experiment.

SELECT assert('(select version from db_version) = 17.3');

alter table new_experiment drop column destination_rack_specs_id;

CREATE OR REPLACE VIEW db_version AS SELECT 17.4 AS version;