-- These changes stand in the course of a revision of the ISO processing
-- workflow. They serve the integration of pool stock sample creation processes
-- and some unifications and generalizations (to make ISO processing
-- independent from experiment metadata types). To this end, we also introduce
-- some more polymorphic inheritances.

 IMPORTANT: before starting assert we have only one library in the DB
 that does not belong to a stock sample pool creation iso request
 (as opposed to a proper library)! The name of the library must be 'poollib'
 In addition, make sure all ISO requests for libraries and pool creations
 are set to 'LIBRARY_CREATION'!

SELECT assert('(select version from db_version) = 16.2');


-- ISO request: create 2 subtypes, rename available types and migrate data,
-- shift rack layouts into a separate table

ALTER TABLE iso_request RENAME COLUMN number_plates TO expected_number_isos;
ALTER TABLE iso_request ADD CONSTRAINT iso_request_positive_exp_number_plates
  CHECK (expected_number_isos >= 1);
ALTER TABLE iso_request DROP CONSTRAINT number_aliquots_greater_zero;
ALTER TABLE iso_request ADD CONSTRAINT iso_request_number_aliquots_non_negative
  CHECK (number_aliquots >= 0);
ALTER TABLE iso_request ALTER COLUMN number_aliquots DROP DEFAULT;
ALTER TABLE iso_request RENAME COLUMN plate_set_label TO label;
ALTER TABLE iso_request ALTER COLUMN label SET NOT NULL;

CREATE TABLE lab_iso_request (
  iso_request_id INTEGER NOT NULL
    REFERENCES iso_request (iso_request_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  delivery_date DATE,
  comment VARCHAR,
  requester_id INTEGER NOT NULL
    REFERENCES db_user (db_user_id),
  rack_layout_id INTEGER NOT NULL
    REFERENCES rack_layout (rack_layout_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  iso_plate_reservoir_specs_id INTEGER
    REFERENCES reservoir_specs (reservoir_specs_id),
  process_job_first BOOLEAN NOT NULL,
  CONSTRAINT lab_iso_request_pkey PRIMARY KEY (iso_request_id)
);


CREATE TABLE stock_sample_creation_iso_request (
  iso_request_id INTEGER NOT NULL
    REFERENCES iso_request (iso_request_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  stock_volume FLOAT NOT NULL DEFAULT 0.000001,
  stock_concentration FLOAT NOT NULL DEFAULT 0.000010,
  number_designs INTEGER NOT NULL DEFAULT 3,
  CONSTRAINT stock_sample_creation_iso_request_pkey PRIMARY KEY (iso_request_id),
  CONSTRAINT stock_sample_creation_volume_positive
    CHECK (stock_volume > 0),
  CONSTRAINT stock_sample_creation_concentration_positive
    CHECK (stock_concentration > 0),
  CONSTRAINT stock_sample_creation_number_designs_greater_one
    CHECK (number_designs > 1)
);


ALTER TABLE iso_request DROP CONSTRAINT valid_iso_request_iso_type;
UPDATE iso_request
  SET iso_type = 'LAB' WHERE iso_type = 'STANDARD';
UPDATE iso_request
  SET iso_type = 'STOCK_SAMPLE_GEN' WHERE iso_type = 'LIBRARY_CREATION';

ALTER TABLE iso_request ADD CONSTRAINT valid_iso_request_iso_type
  CHECK (iso_type IN ('BASE', 'LAB', 'STOCK_SAMPLE_GEN'));
ALTER TABLE iso_request ALTER COLUMN iso_type DROP DEFAULT;

INSERT INTO lab_iso_request
    (iso_request_id, delivery_date, comment, rack_layout_id, requester_id,
     process_job_first)
  SELECT iso_request_id, delivery_date, comment, rack_layout_id, requester_id,
  	true AS process_job_first
  FROM iso_request
  WHERE iso_type = 'LAB';

-- use tmp table to update reservoir specs for ISO request

CREATE TABLE tmp_iso_plate_specs (
	iso_request_id INTEGER NOT NULL REFERENCES iso_request (iso_request_id),
	rack_shape_name VARCHAR NOT NULL,
	reservoir_specs_id INTEGER REFERENCES reservoir_specs (reservoir_specs_id)
);

INSERT INTO tmp_iso_plate_specs (iso_request_id, rack_shape_name)
  SELECT ir.iso_request_id, rl.rack_shape_name
  FROM iso_request ir, rack_layout rl
  WHERE ir.rack_layout_id = rl.rack_layout_id
  AND ir.iso_type = 'LAB';

UPDATE tmp_iso_plate_specs
  SET reservoir_specs_id = (
    SELECT rs.reservoir_specs_id
    FROM reservoir_specs rs
    WHERE rs.name = 'plate 96 std')
  WHERE tmp_iso_plate_specs.rack_shape_name = '8x12';

UPDATE tmp_iso_plate_specs
  SET reservoir_specs_id = (
    SELECT rs.reservoir_specs_id
    FROM reservoir_specs rs
    WHERE rs.name = 'plate 384 std')
  WHERE tmp_iso_plate_specs.rack_shape_name = '16x24';

UPDATE lab_iso_request
  SET iso_plate_reservoir_specs_id = (
  SELECT tmp.reservoir_specs_id
  FROM tmp_iso_plate_specs tmp
  WHERE tmp.iso_request_id = lab_iso_request.iso_request_id);

DROP TABLE tmp_iso_plate_specs;
ALTER TABLE lab_iso_request
  ALTER COLUMN iso_plate_reservoir_specs_id SET NOT NULL;

ALTER TABLE iso_request DROP COLUMN delivery_date;
ALTER TABLE iso_request DROP COLUMN comment;
ALTER TABLE iso_request DROP COLUMN requester_id;


INSERT INTO stock_sample_creation_iso_request (iso_request_id)
  SELECT iso_request_id
  FROM iso_request
  WHERE iso_type = 'STOCK_SAMPLE_GEN';

-- update volumes for the pool creation requests stored so far
UPDATE stock_sample_creation_iso_request
  SET stock_volume =
    (SELECT mdl.final_volume
     FROM molecule_design_library mdl, iso_request ir,
          molecule_design_library_iso_request mdlir
     WHERE mdl.molecule_design_library_id = mdlir.molecule_design_library_id
     AND ir.iso_request_id = mdlir.iso_request_id
     AND ir.iso_type = 'STOCK_SAMPLE_GEN'
     AND ir.iso_request_id = stock_sample_creation_iso_request.iso_request_id);

-- we should only have 1 in the DB at this point - unfortunately we cannot
-- get this data from the DB
UPDATE stock_sample_creation_iso_request
  SET stock_volume = 0.000045
  WHERE iso_request_id =
  	(SELECT iso_request_id FROM iso_request WHERE label = 'poollib'
  	 AND iso_type = 'STOCK_SAMPLE_GEN');

ALTER TABLE stock_sample_creation_iso_request
  ALTER COLUMN stock_volume DROP DEFAULT;
ALTER TABLE stock_sample_creation_iso_request
  ALTER COLUMN stock_concentration DROP DEFAULT;
ALTER TABLE stock_sample_creation_iso_request
  ALTER COLUMN number_designs DROP DEFAULT;


-- Delete all library that only serve pool creation (instead of libary creation)

DELETE FROM molecule_design_library
  WHERE NOT label='poollib';

-- the molecule design library gets a number of layouts and a rack layout column
-- this data may be redundant as long library are generated in-house, but as
-- soon there is no ISO request for the library anymore we cannot get this
-- number conveniently anymore

ALTER TABLE molecule_design_library ADD COLUMN number_layouts INTEGER;
ALTER TABLE molecule_design_library
  ADD CONSTRAINT positive_molecule_design_library_number_layouts
  CHECK (number_layouts > 0);

UPDATE molecule_design_library
  SET number_layouts = (
    SELECT ir.expected_number_isos
    FROM iso_request ir, molecule_design_library_iso_request mdlir
    WHERE ir.iso_request_id = mdlir.iso_request_id
    AND mdlir.molecule_design_library_id =
    	molecule_design_library.molecule_design_library_id
  );

ALTER TABLE molecule_design_library ALTER COLUMN number_layouts SET NOT NULL;

ALTER TABLE molecule_design_library ADD COLUMN rack_layout_id INTEGER
  REFERENCES rack_layout (rack_layout_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

UPDATE molecule_design_library
  SET rack_layout_id = (
    SELECT ir.rack_layout_id
    FROM iso_request ir, molecule_design_library_iso_request mdlir
    WHERE ir.iso_request_id = mdlir.iso_request_id
    AND mdlir.molecule_design_library_id =
    	molecule_design_library.molecule_design_library_id
  );

ALTER TABLE molecule_design_library ALTER COLUMN rack_layout_id SET NOT NULL;

ALTER TABLE iso_request DROP COLUMN rack_layout_id;

-- ISO requests might have pool sets now (the pool set of the experiment
-- metadata is moved here)

CREATE TABLE iso_request_pool_set (
  iso_request_id INTEGER NOT NULL
    REFERENCES iso_request (iso_request_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  molecule_design_pool_set_id INTEGER NOT NULL
    REFERENCES molecule_design_pool_set (molecule_design_pool_set_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT iso_request_pool_set_pkey PRIMARY KEY (iso_request_id),
  CONSTRAINT iso_request_unique_pool_set UNIQUE (molecule_design_pool_set_id)
);

INSERT INTO iso_request_pool_set
    (iso_request_id, molecule_design_pool_set_id)
  SELECT emir.iso_request_id, emps.molecule_design_pool_set_id
  FROM experiment_metadata_iso_request emir, experiment_metadata_pool_set emps
  WHERE emir.experiment_metadata_id = emps.experiment_metadata_id;

INSERT INTO iso_request_pool_set
    (iso_request_id, molecule_design_pool_set_id)
  SELECT mdlir.iso_request_id, mdl.molecule_design_pool_set_id
  FROM molecule_design_library mdl, molecule_design_library_iso_request mdlir
  WHERE mdl.molecule_design_library_id = mdlir.molecule_design_library_id;

DROP TABLE experiment_metadata_pool_set;

-- ISOs: adjust subtype, rename available types, add stock rack number
-- and migrate data

ALTER TABLE library_creation_iso RENAME TO stock_sample_creation_iso;
ALTER TABLE stock_sample_creation_iso
  DROP CONSTRAINT library_creation_iso_iso_id_fkey;
ALTER TABLE library_source_plate
  DROP CONSTRAINT library_source_plate_iso_id_fkey;
ALTER TABLE stock_sample_creation_iso
  DROP CONSTRAINT library_creation_iso_pkey;
ALTER TABLE stock_sample_creation_iso
  ADD CONSTRAINT stock_sample_creation_iso_id_fkey
  FOREIGN KEY (iso_id) REFERENCES iso (iso_id)
  ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE stock_sample_creation_iso
  ADD CONSTRAINT stock_sample_creation_iso_pkey PRIMARY KEY (iso_id);
ALTER TABLE library_source_plate
  ADD CONSTRAINT stock_sample_source_plate_iso_id_fkey
  FOREIGN KEY (iso_id) REFERENCES stock_sample_creation_iso (iso_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE iso DROP CONSTRAINT valid_iso_type;
UPDATE iso
  SET iso_type = 'LAB' WHERE iso_type = 'STANDARD';
UPDATE iso
  SET iso_type = 'STOCK_SAMPLE_GEN' WHERE iso_type = 'LIBRARY_CREATION';
ALTER TABLE iso ADD CONSTRAINT valid_iso_type
  CHECK (iso_type IN ('BASE', 'LAB', 'STOCK_SAMPLE_GEN'));
ALTER TABLE iso ALTER COLUMN iso_type DROP DEFAULT;

ALTER TABLE iso ADD COLUMN number_stock_racks INTEGER NOT NULL DEFAULT 1;
ALTER TABLE iso ADD CONSTRAINT iso_number_stock_racks_non_negative
  CHECK (number_stock_racks >= 0);
UPDATE iso
  SET number_stock_racks = 4
  WHERE iso_id IN (
    SELECT iso_id
    FROM iso i, experiment_metadata_iso_request emir, experiment_metadata em,
         rack_layout rl
    WHERE i.iso_request_id = emir.iso_request_id
    AND emir.experiment_metadata_id = em.experiment_metadata_id
    AND em.experiment_metadata_type_id = 'SCREEN'
    AND i.rack_layout_id = rl.rack_layout_id
    AND rl.rack_shape_name = '16x24'
    AND i.iso_type='LAB');
UPDATE iso
  SET number_stock_racks = 3
  WHERE iso_type = 'STOCK_SAMPLE_GEN';
ALTER TABLE iso ALTER COLUMN number_stock_racks DROP DEFAULT;

-- Stock racks: create base table, rename sample and controls stock racks
-- and migrate data

CREATE TABLE stock_rack (
  stock_rack_id SERIAL PRIMARY KEY,
  label VARCHAR(20) NOT NULL,
  rack_id INTEGER NOT NULL REFERENCES rack (rack_id),
  worklist_series_id INTEGER NOT NULL
    REFERENCES worklist_series (worklist_series_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  rack_layout_id INTEGER
    REFERENCES rack_layout (rack_layout_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  stock_rack_type VARCHAR(10) NOT NULL
    CHECK (stock_rack_type IN ('STOCK_RACK', 'ISO_JOB', 'ISO', 'SECTOR'))
);

CREATE TABLE iso_job_stock_rack (
  stock_rack_id INTEGER NOT NULL
    REFERENCES stock_rack (stock_rack_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  job_id INTEGER NOT NULL
    REFERENCES iso_job (job_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT iso_job_stock_rack_pkey PRIMARY KEY (stock_rack_id),
  CONSTRAINT iso_job_stock_rack_unique_job UNIQUE (job_id)
);

CREATE TABLE iso_stock_rack (
  stock_rack_id INTEGER NOT NULL
    REFERENCES stock_rack (stock_rack_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  iso_id INTEGER NOT NULL
    REFERENCES iso (iso_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT iso_stock_rack_pkey PRIMARY KEY (stock_rack_id)
);

CREATE TABLE iso_sector_stock_rack (
  stock_rack_id INTEGER NOT NULL
    REFERENCES stock_rack (stock_rack_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  iso_id INTEGER NOT NULL
    REFERENCES iso (iso_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  sector_index INTEGER NOT NULL,
  CONSTRAINT iso_sector_stock_rack_pkey PRIMARY KEY (stock_rack_id),
  CONSTRAINT iso_sector_stock_rack_sector_index_non_negative
    CHECK (sector_index >= 0)
);

ALTER TABLE worklist_series ADD COLUMN
  planned_worklist_id INTEGER UNIQUE
    REFERENCES planned_worklist (planned_worklist_id);

INSERT INTO worklist_series (planned_worklist_id)
  SELECT planned_worklist_id FROM iso_control_stock_rack;
INSERT INTO worklist_series (planned_worklist_id)
  SELECT planned_worklist_id FROM iso_sample_stock_rack;
INSERT INTO worklist_series_member
  (worklist_series_id, planned_worklist_id, index)
  SELECT worklist_series_id, planned_worklist_id, 0 AS index
  FROM worklist_series
  WHERE planned_worklist_id IS NOT NULL;

INSERT INTO stock_rack (rack_id, worklist_series_id, rack_layout_id,
      stock_rack_type, label)
  SELECT icsr.rack_id, ws.worklist_series_id, icsr.rack_layout_id,
    'ISO_JOB' AS stock_rack_type, 'default' AS label
  FROM iso_control_stock_rack icsr, worklist_series ws
  WHERE icsr.planned_worklist_id = ws.planned_worklist_id;

INSERT INTO iso_job_stock_rack (stock_rack_id, job_id)
  SELECT sr.stock_rack_id, icsr.job_id
  FROM stock_rack sr, iso_control_stock_rack icsr, worklist_series ws
  WHERE sr.worklist_series_id = ws.worklist_series_id
  AND ws.planned_worklist_id = icsr.planned_worklist_id
  AND sr.rack_layout_id = icsr.rack_layout_id;

DROP TABLE iso_control_stock_rack;

INSERT INTO stock_rack (rack_id, worklist_series_id, stock_rack_type, label)
  SELECT issr.rack_id, ws.worklist_series_id, 'SECTOR' AS stock_rack_type,
    'default' AS label
  FROM iso_sample_stock_rack issr, worklist_series ws
  WHERE issr.planned_worklist_id = ws.planned_worklist_id;

INSERT INTO iso_sector_stock_rack (stock_rack_id, iso_id, sector_index)
  SELECT sr.stock_rack_id, issr.iso_id, issr.sector_index
  FROM stock_rack sr, iso_sample_stock_rack issr, worklist_series ws
  WHERE sr.worklist_series_id = ws.worklist_series_id
  AND ws.planned_worklist_id = issr.planned_worklist_id
  AND sr.rack_id = issr.rack_id;

DROP TABLE iso_sample_stock_rack;
ALTER TABLE worklist_series DROP COLUMN planned_worklist_id;


-- the iso requests for molecule design library need to be distinguished
ALTER TABLE molecule_design_library_iso_request
  RENAME TO molecule_design_library_creation_iso_request;
ALTER TABLE molecule_design_library_creation_iso_request
  DROP CONSTRAINT molecule_design_library_iso_request_iso_request_id_fkey;
ALTER TABLE molecule_design_library_creation_iso_request
  ADD CONSTRAINT molecule_design_library_iso_request_iso_request_id_fkey
  FOREIGN KEY (iso_request_id)
  REFERENCES stock_sample_creation_iso_request (iso_request_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

CREATE TABLE molecule_design_library_lab_iso_request (
  molecule_design_library_id INTEGER NOT NULL
    REFERENCES molecule_design_library (molecule_design_library_id)
    ON UPDATE CASCADE,
  iso_request_id INTEGER NOT NULL
    REFERENCES lab_iso_request (iso_request_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT molecule_design_library_lab_iso_request_pkey
    PRIMARY KEY (iso_request_id)
);

INSERT INTO molecule_design_library_lab_iso_request
    (molecule_design_library_id, iso_request_id)
  SELECT mdl.molecule_design_library_id, emir.iso_request_id
  FROM experiment_metadata_iso_request emir, experiment_metadata em,
  	molecule_design_library mdl
  WHERE mdl.label = 'poollib'
  AND em.experiment_metadata_type_id = 'LIBRARY'
  AND emir.experiment_metadata_id = em.experiment_metadata_id;

-- Library plates - these contain the aliquot plates of the existing library

CREATE TABLE library_plate (
  library_plate_id SERIAL PRIMARY KEY,
  molecule_design_library_id INTEGER NOT NULL
    REFERENCES molecule_design_library (molecule_design_library_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  rack_id INTEGER NOT NULL
    REFERENCES rack (rack_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  layout_number INTEGER NOT NULL,
  has_been_used BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT library_plate_layout_number_greater_zero CHECK (layout_number > 0)
);

-- we should only have the poollib library in the DB at this point
INSERT INTO library_plate
  (molecule_design_library_id, rack_id, layout_number)
  SELECT mdl.molecule_design_library_id, iap.rack_id, ssci.layout_number
  FROM molecule_design_library mdl,
    molecule_design_library_creation_iso_request mdlcir,
    iso i, stock_sample_creation_iso ssci, iso_aliquot_plate iap
  WHERE mdl.label = 'poollib'
  AND mdl.molecule_design_library_id = mdlcir.molecule_design_library_id
  AND mdlcir.iso_request_id = i.iso_request_id
  AND i.iso_id = ssci.iso_id
  AND iap.iso_id = i.iso_id;


-- linking library plates to ISOs (there is no data for this table yet)

CREATE TABLE lab_iso_library_plate (
  iso_id INTEGER NOT NULL REFERENCES iso (iso_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  library_plate_id INTEGER NOT NULL REFERENCES library_plate (library_plate_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT iso_library_plate_pkey PRIMARY KEY (library_plate_id)
);

INSERT INTO lab_iso_library_plate (iso_id, library_plate_id)
  SELECT i.iso_id, lp.library_plate_id
  FROM iso i, library_plate lp, molecule_design_library_lab_iso_request mdllir,
    iso_aliquot_plate iap
  WHERE mdllir.iso_request_id = i.iso_request_id
  AND iap.iso_id = i.iso_id
  AND lp.rack_id = iap.rack_id;

UPDATE library_plate
  SET has_been_used = true
  WHERE library_plate.library_plate_id IN (
    SELECT lilp.library_plate_id FROM lab_iso_library_plate lilp);

DELETE FROM iso_aliquot_plate
  WHERE rack_id IN (
    SELECT lp.rack_id
       FROM lab_iso_library_plate lilp, library_plate lp
       WHERE lilp.library_plate_id = lp.library_plate_id)
  AND iso_id IN (SELECT iso_id FROM lab_iso_library_plate);


-- ISO plates: create base table and subtypes and migrate data

CREATE TABLE iso_plate (
  iso_plate_id SERIAL PRIMARY KEY,
  iso_id INTEGER NOT NULL REFERENCES iso (iso_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  rack_id INTEGER NOT NULL REFERENCES rack (rack_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  iso_plate_type VARCHAR(14) NOT NULL
    CHECK (iso_plate_type IN ('ISO_PLATE', 'ALIQUOT', 'PREPARATION',
    'SECTOR_PREP')),
  CONSTRAINT iso_plate_unique_rack UNIQUE (rack_id)
);

ALTER TABLE iso_aliquot_plate RENAME TO old_iso_aliquot_plate;
ALTER TABLE old_iso_aliquot_plate DROP CONSTRAINT iso_aliquot_plate_pkey;
CREATE TABLE iso_aliquot_plate (
  iso_plate_id INTEGER NOT NULL REFERENCES iso_plate (iso_plate_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  has_been_used BOOLEAN NOT NULL,
  CONSTRAINT iso_aliquot_plate_pkey PRIMARY KEY (iso_plate_id)
);

ALTER TABLE iso_preparation_plate RENAME TO old_iso_preparation_plate;
ALTER TABLE old_iso_preparation_plate
  DROP CONSTRAINT iso_preparation_plate_pkey;
CREATE TABLE iso_preparation_plate (
  iso_plate_id INTEGER NOT NULL REFERENCES iso_plate (iso_plate_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  rack_layout_id INTEGER NOT NULL REFERENCES rack_layout (rack_layout_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT iso_preparation_plate_pkey PRIMARY KEY (iso_plate_id)
);

CREATE TABLE iso_sector_preparation_plate (
  iso_plate_id INTEGER NOT NULL REFERENCES iso_plate (iso_plate_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  sector_index INTEGER NOT NULL,
  rack_layout_id INTEGER NOT NULL REFERENCES rack_layout (rack_layout_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT iso_sector_preparation_plate_pkey PRIMARY KEY (iso_plate_id),
  CONSTRAINT iso_sector_preparation_plate_index_non_negative
    CHECK (sector_index >= 0)
);

INSERT INTO iso_plate (iso_id, rack_id, iso_plate_type)
  SELECT iso_id, rack_id, 'ALIQUOT' AS iso_plate_type
  FROM old_iso_aliquot_plate;

INSERT INTO iso_aliquot_plate (iso_plate_id, has_been_used)
  SELECT iso_plate_id, false as has_been_used
  FROM iso_plate
  WHERE iso_plate_type = 'ALIQUOT';

DROP TABLE old_iso_aliquot_plate;


-- ISO job preparation plates are like preparation plates for a job
-- we recognize them by the fact that they belong to several ISOs
-- (that all belong the same ISO job)
-- we have to migrate them before the ISO preparation plate because
-- of the unique rack constraint in the iso_plates table

CREATE TABLE iso_job_preparation_plate (
  iso_job_preparation_plate_id SERIAL PRIMARY KEY,
  rack_id INTEGER NOT NULL REFERENCES rack (rack_id),
  rack_layout_id INTEGER
    REFERENCES rack_layout (rack_layout_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  job_id INTEGER
    REFERENCES job (job_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  iso_id INTEGER UNIQUE NOT NULL,
  CONSTRAINT iso_job_unique_preparation_plate UNIQUE (rack_id)
);

INSERT INTO iso_job_preparation_plate (rack_id, iso_id)
  SELECT rack_id, min(iso_id)
  FROM old_iso_preparation_plate
  GROUP BY rack_id
  HAVING count(iso_id) > 1;
UPDATE iso_job_preparation_plate
  SET job_id = (SELECT job_id FROM iso_job_member
    WHERE iso_job_member.iso_id = iso_job_preparation_plate.iso_id);
UPDATE iso_job_preparation_plate
  SET rack_layout_id = (SELECT rack_layout_id FROM iso
    WHERE iso.iso_id = iso_job_preparation_plate.iso_id);

DELETE FROM old_iso_preparation_plate
  WHERE rack_id IN (SELECT rack_id FROM iso_job_preparation_plate);
ALTER TABLE iso_job_preparation_plate DROP COLUMN iso_id;
ALTER TABLE iso_job_preparation_plate ALTER COLUMN rack_layout_id SET NOT NULL;
ALTER TABLE iso_job_preparation_plate ALTER COLUMN job_id SET NOT NULL;

-- now we can deal with ISO preparation plates

INSERT INTO iso_plate (iso_id, rack_id, iso_plate_type)
  SELECT iso_id, rack_id, 'PREPARATION' AS iso_plate_type
  FROM old_iso_preparation_plate;

INSERT INTO iso_preparation_plate (iso_plate_id, rack_layout_id)
  SELECT ip.iso_plate_id, i.rack_layout_id
  FROM old_iso_preparation_plate opp, iso i, iso_plate ip
  WHERE ip.rack_id = opp.rack_id
  AND opp.iso_id = i.iso_id;

DROP TABLE old_iso_preparation_plate;

INSERT INTO iso_plate (iso_id, rack_id, iso_plate_type)
  SELECT iso_id, rack_id, 'SECTOR_PREP' AS iso_plate_type
  FROM library_source_plate;

INSERT INTO iso_sector_preparation_plate
    (iso_plate_id, rack_layout_id, sector_index)
  SELECT ip.iso_plate_id, i.rack_layout_id, lsp.sector_index
  FROM iso_plate ip, iso i, library_source_plate lsp
  WHERE ip.iso_id = lsp.iso_id
  AND i.iso_id = ip.iso_id
  AND ip.rack_id = lsp.rack_id;

DROP TABLE library_source_plate;

CREATE OR REPLACE VIEW db_version AS SELECT 17.1 AS version;