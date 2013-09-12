-- Add a short name column to the reservoir specs table (as new slug) to
-- simplify specification in generic sample transfer sheet.

SELECT assert('(select version from db_version) = 209.0012');

ALTER TABLE reservoir_specs RENAME COLUMN name TO description;

ALTER TABLE reservoir_specs
  ADD COLUMN name VARCHAR(15);

UPDATE reservoir_specs
  SET name = 'quarter mod'
  WHERE description = 'quarter modular reservoir';

UPDATE reservoir_specs
  SET description = 'Quarter modular reservoir'
  WHERE name = 'quarter mod';

UPDATE reservoir_specs
  SET name = 'microfuge plate'
  WHERE description = '1.5 ml tube 4x6';

UPDATE reservoir_specs
  SET description = 'Microfuge tube rack 4x6'
  WHERE name = 'microfuge plate';

UPDATE reservoir_specs
  SET name = 'plate 96 std'
  WHERE description = 'Standard 96-well plate';

UPDATE reservoir_specs
  SET name = 'plate 96 deep'
  WHERE description = 'Deepwell 96-well plate';

UPDATE reservoir_specs
  SET name = 'plate 384 std'
  WHERE description = 'Standard 384-well plate';

UPDATE reservoir_specs
  SET name = 'falcon tube'
  WHERE description = 'Falcon tube for manual preparation';

ALTER TABLE reservoir_specs ALTER COLUMN name SET NOT NULL;

INSERT INTO reservoir_specs (description, rack_shape_name, max_volume,
    min_dead_volume, max_dead_volume, name)
  VALUES ('Stock rack 96 tubes', '8x12' , '0.0005', '5e-6', '5e-6',
    'stock rack');



CREATE OR REPLACE VIEW db_version AS SELECT 209.0013 AS version;