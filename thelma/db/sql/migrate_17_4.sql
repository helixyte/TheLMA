-- Remove destination_plate_specs_id from table new_experiment.
-- Create index on rack_position_set.hash_value

SELECT assert('(select version from db_version) = 17.3');

alter table new_experiment drop column destination_rack_specs_id;

create index rack_position_set_hash_value_idx on rack_position_set(hash_value);

CREATE OR REPLACE VIEW db_version AS SELECT 17.4 AS version;