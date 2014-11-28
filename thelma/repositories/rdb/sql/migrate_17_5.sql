-- Remove destination_plate_specs_id from table new_experiment.
-- Create index on rack_position_set.hash_value

SELECT assert('(select version from db_version) = 17.4');

-- Making the preparation plate volume configurable for library creation
-- ISO requests.
-- FIXME: It is not clean to associate preparation plate information
--        with this table.
alter table stock_sample_creation_iso_request 
    add column preparation_plate_volume float 
        check (preparation_plate_volume>0.0);
        
-- A stock sample creation ISO request may very well consist of samples that
-- contain only a single design (e.g., single design library creation).
alter table stock_sample_creation_iso_request
    drop constraint stock_sample_creation_number_designs_greater_one;
alter table stock_sample_creation_iso_request
    add constraint stock_sample_creation_number_designs_greater_zero
        check (number_designs > 0);

    

CREATE OR REPLACE VIEW db_version AS SELECT 17.5 AS version;