-- introduces a table that stores the properties of the pipetting robots
-- available at Cenix (including manual pipetting)

SELECT assert('(select version from db_version) = 209.0015');

CREATE TABLE pipetting_specs (
  pipetting_specs_id SERIAL PRIMARY KEY,
  name VARCHAR(8) UNIQUE NOT NULL,
  min_transfer_volume FLOAT NOT NULL,
  max_transfer_volume FLOAT NOT NULL,
  max_dilution_factor INTEGER NOT NULL,
  has_dynamic_dead_volume BOOLEAN NOT NULL,
  is_sector_bound BOOLEAN NOT NULL,
  CONSTRAINT positive_pipetting_min_transfer_volume
    CHECK (min_transfer_volume > 0),
  CONSTRAINT positive_pipetting_max_transfer_volume
    CHECK (max_transfer_volume > 0),
  CONSTRAINT pipetting_transfer_volume_max_larger_than_min
    CHECK (max_transfer_volume > min_transfer_volume),
  CONSTRAINT positive_pipettig_max_dilution_factor
    CHECK (max_dilution_factor > 0)
);

INSERT INTO pipetting_specs
  (name, min_transfer_volume, max_transfer_volume, max_dilution_factor,
   has_dynamic_dead_volume, is_sector_bound)
  VALUES ('manual', 0.0000005, 0.1, 1000, false, false);

INSERT INTO pipetting_specs
  (name, min_transfer_volume, max_transfer_volume, max_dilution_factor,
   has_dynamic_dead_volume, is_sector_bound)
  VALUES ('BioMek', 0.000002, 0.00025, 500, true, false);

INSERT INTO pipetting_specs
  (name, min_transfer_volume, max_transfer_volume, max_dilution_factor,
   has_dynamic_dead_volume, is_sector_bound)
  VALUES ('CyBio', 0.000001, 0.0001, 100, false, true);


CREATE OR REPLACE VIEW db_version AS SELECT 209.0016 AS version;