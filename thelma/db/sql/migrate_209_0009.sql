-- add a default stock concentration column to the molecule design pool
-- table, adds some missing unique constraint (various tables) and adds
-- final concentration and volume to the molecule design library

SELECT assert('(select version from db_version) = 209.0008');

-- adding the default stock concentration

ALTER TABLE molecule_design_pool
  ADD COLUMN default_stock_concentration FLOAT;
ALTER TABLE molecule_design_pool
  ADD CONSTRAINT positive_default_stock_concentration
  CHECK (default_stock_concentration > 0);

-- add values

-- 10 uM for miRNAs
UPDATE molecule_design_pool
 SET default_stock_concentration = 0.00001
 WHERE molecule_type = 'MIRNA_INHI'
 OR molecule_type = 'MIRNA_MIMI';

-- 10 uM for siRNA pools with 3 designs
UPDATE molecule_design_pool
 SET default_stock_concentration = 0.00001
 WHERE number_designs = 3
 AND molecule_type = 'SIRNA';

-- 3.8 uM for esiRNA pools
UPDATE molecule_design_pool
  SET default_stock_concentration = 0.0000038
  WHERE molecule_type = 'ESI_RNA';


-- compounds have different stock concentrations (default: 5 mM)

UPDATE molecule_design_pool
  SET default_stock_concentration = (
    SELECT MIN(concentration)
  	FROM stock_sample
  	WHERE molecule_type = 'COMPOUND'
  	AND molecule_design_pool.molecule_design_set_id = stock_sample.molecule_design_set_id
	GROUP BY molecule_design_set_id)
  WHERE molecule_type = 'COMPOUND';

UPDATE molecule_design_pool
  SET default_stock_concentration = 0.005
  WHERE molecule_type = 'COMPOUND'
  AND default_stock_concentration IS NULL;

-- all other pools have a stock concentration of 50 uM
UPDATE molecule_design_pool
  SET default_stock_concentration = 0.00005
  WHERE default_stock_concentration IS NULL;

-- add NOT NULL condition

ALTER TABLE molecule_design_pool ALTER COLUMN default_stock_concentration
	SET NOT NULL;


-- adding some missing UNIQUE constraints (various tables)

ALTER TABLE experiment_design_rack
  ADD CONSTRAINT unique_label_per_experiment_design
  UNIQUE (experiment_design_id, label);

ALTER TABLE iso_job_member
  ADD CONSTRAINT unique_iso_job_iso
  UNIQUE (iso_id);

ALTER TABLE iso_pool_set
  ADD CONSTRAINT unique_iso_pool_set_iso
  UNIQUE (iso_id);

ALTER TABLE molecule_design_pool
  ADD CONSTRAINT unique_molecule_design_pool_member_hash
  UNIQUE (member_hash);

ALTER TABLE molecule_design_pool_set_member
  ADD CONSTRAINT unique_pool_per_molecule_design_pool_set
  UNIQUE (molecule_design_pool_set_id, molecule_design_pool_id);

ALTER TABLE molecule_design_set_member
  ADD CONSTRAINT unique_molecule_design_per_molecule_design_set
  UNIQUE (molecule_design_set_id, molecule_design_id);

ALTER TABLE worklist_series_experiment_design
  ADD CONSTRAINT unique_worklist_series_experiment_design
  UNIQUE (experiment_design_id);

ALTER TABLE worklist_series_experiment_design_rack
  ADD CONSTRAINT unique_worklist_series_experiment_design_rack
  UNIQUE (experiment_design_rack_id);

ALTER TABLE worklist_series_iso_request
  ADD CONSTRAINT unique_worlist_series_iso_request_id
  UNIQUE (iso_request_id);


-- final volume (4 ul) and concentration (1270 nM) for the library

ALTER TABLE molecule_design_library
  ADD COLUMN final_volume FLOAT NOT NULL DEFAULT 0.000004;
ALTER TABLE molecule_design_library
  ADD CONSTRAINT positive_molecule_design_library_volume
  CHECK (final_volume > 0);
ALTER TABLE molecule_design_library
  ALTER COLUMN final_volume DROP DEFAULT;

ALTER TABLE molecule_design_library
  ADD COLUMN final_concentration FLOAT NOT NULL DEFAULT 0.00000127;
ALTER TABLE molecule_design_library
  ADD CONSTRAINT positive_molecule_design_library_concentration
  CHECK (final_concentration > 0);
ALTER TABLE molecule_design_library
  ALTER COLUMN final_concentration DROP DEFAULT;



CREATE OR REPLACE VIEW db_version AS SELECT 209.0009 AS version;