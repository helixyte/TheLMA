-- Rename the planned transfer tables (see #384) and adjusts them in such a
-- way that planned transfers with equal values are shared (to reduce the
-- number of stored transfers). Also adds a type column to the planned worklist
-- table to simplify type determination in workflows in which the type is
-- unknown.
-- The migration for the planned transfer reduction is done individually for
-- each transfer type.

SELECT assert('(select version from db_version) = 17.2');

-- Remove unused worklists and worklist series


CREATE TABLE tmp_empty_worklists (worklist_id INTEGER NOT NULL UNIQUE);
INSERT INTO tmp_empty_worklists (worklist_id)
  SELECT ew.executed_worklist_id
  FROM executed_worklist_member ewm RIGHT JOIN executed_worklist ew
  ON ewm.executed_worklist_id = ew.executed_worklist_id
  GROUP BY ew.executed_worklist_id
  HAVING COUNT(ewm.executed_transfer_id) < 1;
DELETE FROM executed_worklist WHERE executed_worklist_id IN (
  SELECT worklist_id FROM tmp_empty_worklists);
DROP TABLE tmp_empty_worklists;

ALTER TABLE worklist_series_member DROP CONSTRAINT
  worklist_series_member_planned_worklist_id_fkey;
ALTER TABLE worklist_series_member
  ADD CONSTRAINT worklist_series_member_planned_worklist_id_fkey
  FOREIGN KEY (planned_worklist_id)
  REFERENCES planned_worklist (planned_worklist_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

CREATE TABLE tmp_empty_worklists (worklist_id INTEGER NOT NULL UNIQUE);
INSERT INTO tmp_empty_worklists (worklist_id)
  SELECT pw.planned_worklist_id
  FROM planned_worklist_member pwm RIGHT JOIN planned_worklist pw
  ON pwm.planned_worklist_id = pw.planned_worklist_id
  GROUP BY pw.planned_worklist_id
  HAVING COUNT(pwm.planned_transfer_id) < 1;
DELETE FROM planned_worklist WHERE planned_worklist_id IN (
  SELECT worklist_id FROM tmp_empty_worklists);
DROP TABLE tmp_empty_worklists;

CREATE TABLE tmp_used_worklist_series (
  worklist_series_id INTEGER NOT NULL UNIQUE);
INSERT INTO tmp_used_worklist_series (worklist_series_id)
  SELECT worklist_series_id FROM worklist_series_experiment_design_rack;
INSERT INTO tmp_used_worklist_series (worklist_series_id)
  SELECT worklist_series_id FROM worklist_series_experiment_design;
INSERT INTO tmp_used_worklist_series (worklist_series_id)
  SELECT worklist_series_id FROM worklist_series_iso_request;
INSERT INTO tmp_used_worklist_series (worklist_series_id)
  SELECT worklist_series_id FROM stock_rack;

DELETE FROM worklist_series
  WHERE worklist_series_id IN (
  SELECT ws.worklist_series_id
  FROM worklist_series ws LEFT JOIN tmp_used_worklist_series tmp
  ON ws.worklist_series_id = tmp.worklist_series_id
  GROUP BY ws.worklist_series_id
  HAVING COUNT(tmp.worklist_series_id) = 0);

DROP TABLE tmp_used_worklist_series;


ALTER TABLE planned_worklist_member
  DROP CONSTRAINT planned_worklist_member_planned_transfer_id_fkey;
ALTER TABLE planned_worklist_member
  ADD CONSTRAINT planned_worklist_member_planned_liquid_transfer_id_fkey
  FOREIGN KEY (planned_transfer_id)
  REFERENCES planned_transfer (planned_transfer_id)
  ON UPDATE CASCADE;


CREATE TABLE tmp_used_worklists (
  planned_worklist_id INTEGER NOT NULL);

INSERT INTO tmp_used_worklists (planned_worklist_id)
  SELECT DISTINCT planned_worklist_id FROM executed_worklist;
INSERT INTO tmp_used_worklists (planned_worklist_id)
  SELECT DISTINCT planned_worklist_id FROM worklist_series_member;

DELETE FROM planned_worklist
  WHERE planned_worklist_id IN (
  SELECT pw.planned_worklist_id
  FROM planned_worklist pw LEFT JOIN tmp_used_worklists tmp
  ON pw.planned_worklist_id = tmp.planned_worklist_id
  GROUP BY pw.planned_worklist_id
  HAVING COUNT(tmp.planned_worklist_id) = 0);

DROP TABLE tmp_used_worklists;


-- Create and adjust general tables

CREATE TABLE planned_liquid_transfer (
  planned_liquid_transfer_id SERIAL PRIMARY KEY,
  volume FLOAT NOT NULL,
  transfer_type VARCHAR(20)
    REFERENCES transfer_type (name)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  hash_value VARCHAR(32) NOT NULL UNIQUE,
  CONSTRAINT planned_liquid_transfer_positive_volume CHECK (volume > 0)
);

ALTER TABLE executed_transfer RENAME to executed_liquid_transfer;
ALTER TABLE executed_liquid_transfer
  ADD COLUMN planned_liquid_transfer_id INTEGER
  REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
  ON UPDATE CASCADE;
ALTER TABLE executed_liquid_transfer
  RENAME COLUMN executed_transfer_id TO executed_liquid_transfer_id;
ALTER TABLE executed_worklist_member RENAME COLUMN executed_transfer_id
  TO executed_liquid_transfer_id;


-- create new planned_worklist_member table

ALTER TABLE planned_worklist_member ADD COLUMN tmp_transfer_type
  VARCHAR(20) REFERENCES transfer_type (name);
UPDATE planned_worklist_member
  SET tmp_transfer_type = (
    SELECT pt.type
    FROM planned_transfer pt INNER JOIN planned_worklist_member pwm
    ON pt.planned_transfer_id = pwm.planned_transfer_id
    WHERE pwm.planned_transfer_id = planned_worklist_member.planned_transfer_id
    AND pwm.planned_worklist_id = planned_worklist_member.planned_worklist_id);

ALTER TABLE planned_worklist_member RENAME to old_planned_worklist_member;
CREATE TABLE planned_worklist_member (
  tmp_id SERIAL PRIMARY KEY,
  planned_worklist_id INTEGER NOT NULL
    REFERENCES planned_worklist (planned_worklist_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  planned_transfer_id INTEGER NOT NULL
    REFERENCES planned_transfer (planned_transfer_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  planned_liquid_transfer_id INTEGER
    REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  tmp_transfer_type VARCHAR(20) NOT NULL REFERENCES transfer_type (name)
);
INSERT INTO planned_worklist_member
  (planned_worklist_id, planned_transfer_id, tmp_transfer_type)
  SELECT planned_worklist_id, planned_transfer_id, tmp_transfer_type
  FROM old_planned_worklist_member;


-- migrate rack transfers

CREATE TABLE planned_rack_sample_transfer (
  planned_liquid_transfer_id INTEGER NOT NULL
    REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  sector_number INTEGER NOT NULL,
  source_sector_index INTEGER NOT NULL,
  target_sector_index INTEGER NOT NULL,
  CONSTRAINT prst_positive_number_sectors CHECK (sector_number > 0),
  CONSTRAINT prst_number_sectors_greater_than_source_sector
    CHECK (sector_number > source_sector_index),
  CONSTRAINT prst_number_sectors_greater_than_target_sector
    CHECK (sector_number > target_sector_index),
  CONSTRAINT prst_source_sector_index_non_negative
    CHECK (source_sector_index >= 0),
  CONSTRAINT prst_target_sector_index_non_negative
    CHECK (target_sector_index >= 0)
);

ALTER TABLE executed_rack_transfer RENAME to executed_rack_sample_transfer;
ALTER TABLE executed_rack_sample_transfer
  RENAME COLUMN executed_transfer_id TO executed_liquid_transfer_id;

CREATE TABLE tmp_rack_transfer_values (
  planned_transfer_id INTEGER
    REFERENCES planned_rack_transfer (planned_transfer_id),
  hash_value VARCHAR(32),
  volume FLOAT NOT NULL,
  sector_number INTEGER NOT NULL,
  source_sector_index INTEGER NOT NULL,
  target_sector_index INTEGER NOT NULL,
  CONSTRAINT tmp_rack_transfer_values_pkey PRIMARY KEY (planned_transfer_id)
);

INSERT INTO tmp_rack_transfer_values
  (planned_transfer_id, volume, sector_number, source_sector_index,
  target_sector_index, hash_value)
  SELECT pt.planned_transfer_id, pt.volume, prt.sector_number,
    prt.source_sector_index, prt.target_sector_index,
    md5(cast(volume*1e6 as text) || ';' ||
     cast(sector_number as text) || ';' ||
     cast(source_sector_index as text) || ';' ||
     cast(target_sector_index as text)) as hash_value
  FROM planned_rack_transfer prt, planned_transfer pt
  WHERE prt.planned_transfer_id = pt.planned_transfer_id;

INSERT INTO planned_liquid_transfer (volume, hash_value)
  SELECT DISTINCT volume, hash_value FROM tmp_rack_transfer_values;
UPDATE planned_liquid_transfer
  SET transfer_type = 'RACK_TRANSFER'
  WHERE transfer_type IS NULL;

CREATE TABLE tmp_old_new (
  planned_transfer_id INTEGER NOT NULL UNIQUE
    REFERENCES planned_rack_transfer (planned_transfer_id),
  hash_value VARCHAR(32) NOT NULL,
  planned_liquid_transfer_id INTEGER
    REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
);

INSERT INTO tmp_old_new
  (planned_transfer_id, hash_value)
  SELECT ton.planned_transfer_id, ton.hash_value
  FROM (SELECT tmp.planned_transfer_id AS planned_transfer_id,
               tmp.hash_value AS hash_value
       FROM tmp_rack_transfer_values tmp) AS ton;

UPDATE tmp_old_new
  SET planned_liquid_transfer_id = (
    SELECT plt.planned_liquid_transfer_id
    FROM planned_liquid_transfer plt
    WHERE plt.hash_value = tmp_old_new.hash_value);

INSERT INTO planned_rack_sample_transfer
    (planned_liquid_transfer_id, sector_number, source_sector_index,
     target_sector_index)
   SELECT DISTINCT ton.planned_liquid_transfer_id, trtv.sector_number,
     trtv.source_sector_index, trtv.target_sector_index
   FROM tmp_rack_transfer_values trtv, tmp_old_new ton
   WHERE trtv.hash_value = ton.hash_value;

UPDATE executed_liquid_transfer
  SET planned_liquid_transfer_id = (
  SELECT ton.planned_liquid_transfer_id
  FROM tmp_old_new ton INNER JOIN executed_liquid_transfer elt
  ON ton.planned_transfer_id = elt.planned_transfer_id
  WHERE executed_liquid_transfer.executed_liquid_transfer_id
    = elt.executed_liquid_transfer_id)
  WHERE executed_liquid_transfer.type = 'RACK_TRANSFER';

UPDATE planned_worklist_member
  SET planned_liquid_transfer_id = (
  SELECT DISTINCT ton.planned_liquid_transfer_id
  FROM tmp_old_new ton INNER JOIN planned_worklist_member pwm
  ON ton.planned_transfer_id = pwm.planned_transfer_id
  WHERE planned_worklist_member.planned_transfer_id
    = pwm.planned_transfer_id)
  WHERE planned_worklist_member.tmp_transfer_type = 'RACK_TRANSFER';

DROP TABLE tmp_old_new;
DROP TABLE tmp_rack_transfer_values;
ALTER TABLE planned_rack_sample_transfer
  RENAME COLUMN sector_number TO number_sectors;

-- migrate sample dilutions (conatiner dilutions)

CREATE TABLE planned_sample_dilution (
  planned_liquid_transfer_id INTEGER NOT NULL
    REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  diluent_info VARCHAR(35) NOT NULL,
  target_position_id INTEGER NOT NULL
    REFERENCES rack_position (rack_position_id)
    ON UPDATE CASCADE
);

ALTER TABLE executed_container_dilution RENAME to executed_sample_dilution;
ALTER TABLE executed_sample_dilution
  RENAME COLUMN executed_transfer_id TO executed_liquid_transfer_id;

CREATE TABLE tmp_sample_dilution_values (
  planned_transfer_id INTEGER
    REFERENCES planned_container_dilution (planned_transfer_id),
  hash_value VARCHAR,
  volume FLOAT NOT NULL,
  diluent_info VARCHAR(35) NOT NULL,
  target_position_id INTEGER NOT NULL
    REFERENCES rack_position (rack_position_id)
    ON UPDATE CASCADE,
  CONSTRAINT tmp_sample_dilution_values_pkey PRIMARY KEY (planned_transfer_id)
);

INSERT INTO tmp_sample_dilution_values
  (planned_transfer_id, volume, diluent_info, target_position_id, hash_value)
  SELECT pt.planned_transfer_id, pt.volume, pcd.diluent_info,
    pcd.target_position_id,
    md5(cast(pt.volume*1e6 as text) || ';' ||
     pcd.diluent_info || ';' ||
     cast(pcd.target_position_id as text)) as hash_value
  FROM planned_container_dilution pcd, planned_transfer pt
  WHERE pcd.planned_transfer_id = pt.planned_transfer_id;

INSERT INTO planned_liquid_transfer (volume, hash_value)
  SELECT DISTINCT volume, hash_value FROM tmp_sample_dilution_values;
UPDATE planned_liquid_transfer
  SET transfer_type = 'CONTAINER_DILUTION' WHERE transfer_type IS NULL;

CREATE TABLE tmp_old_new (
  planned_transfer_id INTEGER NOT NULL UNIQUE
    REFERENCES planned_container_dilution (planned_transfer_id),
  hash_value VARCHAR(32) NOT NULL,
  planned_liquid_transfer_id INTEGER
    REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
);

INSERT INTO tmp_old_new
  (planned_transfer_id, hash_value)
  SELECT ton.planned_transfer_id, ton.hash_value
  FROM (SELECT tmp.planned_transfer_id AS planned_transfer_id,
               tmp.hash_value AS hash_value
       FROM tmp_sample_dilution_values tmp) AS ton;

UPDATE tmp_old_new
  SET planned_liquid_transfer_id = (
    SELECT plt.planned_liquid_transfer_id
    FROM planned_liquid_transfer plt
    WHERE plt.hash_value = tmp_old_new.hash_value);

CREATE TABLE tmp_duplicates (
  hash_value VARCHAR(32) UNIQUE,
  planned_transfer_id INTEGER NOT NULL);
INSERT INTO tmp_duplicates (hash_value, planned_transfer_id)
  SELECT hash_value, min(planned_transfer_id)
  FROM tmp_sample_dilution_values
  GROUP BY hash_value;
DELETE FROM tmp_sample_dilution_values
  WHERE planned_transfer_id NOT IN (
    SELECT planned_transfer_id FROM tmp_duplicates);
DROP TABLE tmp_duplicates;
ALTER TABLE tmp_sample_dilution_values
  ADD CONSTRAINT tmp_unique_hash_value UNIQUE (hash_value);
ALTER TABLE tmp_sample_dilution_values
  ADD COLUMN planned_liquid_transfer_id INTEGER UNIQUE;
UPDATE tmp_sample_dilution_values
  SET planned_liquid_transfer_id = (
    SELECT plt.planned_liquid_transfer_id
    FROM planned_liquid_transfer plt, tmp_sample_dilution_values tmp
    WHERE plt.hash_value = tmp.hash_value
    AND tmp.hash_value = tmp_sample_dilution_values.hash_value);

INSERT INTO planned_sample_dilution
  (planned_liquid_transfer_id, diluent_info, target_position_id)
  SELECT planned_liquid_transfer_id, diluent_info, target_position_id
  FROM tmp_sample_dilution_values;

UPDATE executed_liquid_transfer
  SET planned_liquid_transfer_id = (
  SELECT ton.planned_liquid_transfer_id
  FROM tmp_old_new ton INNER JOIN executed_liquid_transfer elt
  ON ton.planned_transfer_id = elt.planned_transfer_id
  WHERE executed_liquid_transfer.executed_liquid_transfer_id
    = elt.executed_liquid_transfer_id)
  WHERE executed_liquid_transfer.type = 'CONTAINER_DILUTION';

UPDATE planned_worklist_member
  SET planned_liquid_transfer_id = (
    SELECT DISTINCT ton.planned_liquid_transfer_id
    FROM tmp_old_new ton, planned_worklist_member pw
    WHERE ton.planned_transfer_id = pw.planned_transfer_id
    AND planned_worklist_member.tmp_id = pw.tmp_id)
  WHERE planned_worklist_member.tmp_transfer_type = 'CONTAINER_DILUTION';

DROP TABLE tmp_old_new;
DROP TABLE tmp_sample_dilution_values;

-- migrate sample transfers (container transfers)

CREATE TABLE planned_sample_transfer (
  planned_liquid_transfer_id INTEGER NOT NULL
    REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  source_position_id INTEGER NOT NULL
    REFERENCES rack_position (rack_position_id)
    ON UPDATE CASCADE,
  target_position_id INTEGER NOT NULL
    REFERENCES rack_position (rack_position_id)
    ON UPDATE CASCADE);

ALTER TABLE executed_container_transfer RENAME to executed_sample_transfer;
ALTER TABLE executed_sample_transfer
  RENAME COLUMN executed_transfer_id TO executed_liquid_transfer_id;;

CREATE TABLE tmp_sample_transfer_values (
  planned_transfer_id INTEGER
    REFERENCES planned_container_transfer (planned_transfer_id),
  hash_value VARCHAR,
  volume FLOAT NOT NULL,
  source_position_id INTEGER NOT NULL
    REFERENCES rack_position (rack_position_id)
    ON UPDATE CASCADE,
  target_position_id INTEGER NOT NULL
    REFERENCES rack_position (rack_position_id)
    ON UPDATE CASCADE,
  CONSTRAINT tmp_sample_transfer_values_pkey PRIMARY KEY (planned_transfer_id)
);

INSERT INTO tmp_sample_transfer_values
  (planned_transfer_id, volume, source_position_id, target_position_id,
  hash_value)
  SELECT pt.planned_transfer_id, pt.volume, pct.source_position_id,
    pct.target_position_id,
    md5(cast(pt.volume*1e6 as text) || ';' ||
     cast(pct.source_position_id as text) || ';' ||
     cast(pct.target_position_id as text)) as hash_value
  FROM planned_container_transfer pct, planned_transfer pt
  WHERE pct.planned_transfer_id = pt.planned_transfer_id;

INSERT INTO planned_liquid_transfer (volume, hash_value)
  SELECT DISTINCT volume, hash_value FROM tmp_sample_transfer_values;
UPDATE planned_liquid_transfer
  SET transfer_type = 'CONTAINER_TRANSFER' WHERE transfer_type IS NULL;

CREATE TABLE tmp_old_new (
  planned_transfer_id INTEGER NOT NULL UNIQUE
    REFERENCES planned_container_transfer (planned_transfer_id),
  hash_value VARCHAR(32) NOT NULL,
  planned_liquid_transfer_id INTEGER
    REFERENCES planned_liquid_transfer (planned_liquid_transfer_id)
);

INSERT INTO tmp_old_new
  (planned_transfer_id, hash_value)
  SELECT ton.planned_transfer_id, ton.hash_value
  FROM (SELECT tmp.planned_transfer_id AS planned_transfer_id,
               tmp.hash_value AS hash_value
       FROM tmp_sample_transfer_values tmp) AS ton;

UPDATE tmp_old_new
  SET planned_liquid_transfer_id = (
    SELECT plt.planned_liquid_transfer_id
    FROM planned_liquid_transfer plt
    WHERE plt.hash_value = tmp_old_new.hash_value);

CREATE TABLE tmp_duplicates (
  hash_value VARCHAR(32) UNIQUE,
  planned_transfer_id INTEGER NOT NULL);
INSERT INTO tmp_duplicates (hash_value, planned_transfer_id)
  SELECT hash_value, min(planned_transfer_id)
  FROM tmp_sample_transfer_values
  GROUP BY hash_value;
DELETE FROM tmp_sample_transfer_values
  WHERE planned_transfer_id NOT IN (
    SELECT planned_transfer_id FROM tmp_duplicates);
DROP TABLE tmp_duplicates;
ALTER TABLE tmp_sample_transfer_values
  ADD CONSTRAINT tmp_unique_hash_value UNIQUE (hash_value);
ALTER TABLE tmp_sample_transfer_values
  ADD COLUMN planned_liquid_transfer_id INTEGER UNIQUE;
UPDATE tmp_sample_transfer_values
  SET planned_liquid_transfer_id = (
    SELECT plt.planned_liquid_transfer_id
    FROM planned_liquid_transfer plt, tmp_sample_transfer_values tmp
    WHERE plt.hash_value = tmp.hash_value
    AND tmp.hash_value = tmp_sample_transfer_values.hash_value);

INSERT INTO planned_sample_transfer
  (planned_liquid_transfer_id, source_position_id, target_position_id)
  SELECT planned_liquid_transfer_id, source_position_id, target_position_id
  FROM tmp_sample_transfer_values;

UPDATE executed_liquid_transfer
  SET planned_liquid_transfer_id = (
  SELECT ton.planned_liquid_transfer_id
  FROM tmp_old_new ton INNER JOIN executed_liquid_transfer elt
  ON ton.planned_transfer_id = elt.planned_transfer_id
  WHERE executed_liquid_transfer.executed_liquid_transfer_id
    = elt.executed_liquid_transfer_id)
  WHERE executed_liquid_transfer.type = 'CONTAINER_TRANSFER';

UPDATE planned_worklist_member
  SET planned_liquid_transfer_id = (
    SELECT DISTINCT ton.planned_liquid_transfer_id
    FROM tmp_old_new ton, planned_worklist_member pw
    WHERE ton.planned_transfer_id = pw.planned_transfer_id
    AND planned_worklist_member.tmp_id = pw.tmp_id)
  WHERE planned_worklist_member.tmp_transfer_type = 'CONTAINER_TRANSFER';

DROP TABLE tmp_old_new;
DROP TABLE tmp_sample_transfer_values;

-- add transfer type column to planned worklist

ALTER TABLE planned_worklist ADD COLUMN transfer_type VARCHAR(20)
    REFERENCES transfer_type (name)
    ON UPDATE CASCADE ON DELETE RESTRICT;

CREATE TABLE tmp_worklist_types (
  planned_worklist_id INTEGER NOT NULL UNIQUE,
  transfer_type VARCHAR(20));
INSERT INTO tmp_worklist_types (planned_worklist_id)
  SELECT DISTINCT planned_worklist_id FROM planned_worklist_member;
UPDATE tmp_worklist_types
  SET transfer_type = (
    SELECT DISTINCT pwm.tmp_transfer_type
    FROM planned_worklist_member pwm INNER JOIN tmp_worklist_types tmp
    ON pwm.planned_worklist_id = tmp.planned_worklist_id
    AND tmp_worklist_types.planned_worklist_id = tmp.planned_worklist_id);

UPDATE planned_worklist
  SET transfer_type = (
    SELECT DISTINCT tmp.transfer_type
    FROM planned_worklist pw INNER JOIN tmp_worklist_types tmp
    ON pw.planned_worklist_id = tmp.planned_worklist_id
    WHERE pw.planned_worklist_id = planned_worklist.planned_worklist_id);

ALTER TABLE planned_worklist ALTER COLUMN transfer_type SET NOT NULL;
DROP TABLE tmp_worklist_types;

-- add pipetting specs column to planned worklist

ALTER TABLE planned_worklist
  ADD COLUMN pipetting_specs_id INTEGER
  REFERENCES pipetting_specs (pipetting_specs_id)
  ON UPDATE CASCADE;
UPDATE planned_worklist
  SET pipetting_specs_id = (
    SELECT pipetting_specs_id FROM pipetting_specs WHERE name = 'CyBio')
  WHERE transfer_type = 'RACK_TRANSFER';
UPDATE planned_worklist
  SET pipetting_specs_id = (
    SELECT pipetting_specs_id FROM pipetting_specs WHERE name = 'BioMek')
  WHERE NOT transfer_type = 'RACK_TRANSFER';
ALTER TABLE planned_worklist ALTER COLUMN pipetting_specs_id SET NOT NULL;

ALTER TABLE pipetting_specs ALTER COLUMN name TYPE VARCHAR(11);
INSERT INTO pipetting_specs
    (name,  min_transfer_volume, max_transfer_volume, max_dilution_factor,
     has_dynamic_dead_volume, is_sector_bound)
  VALUES ('BioMekStock', 1e-06, 0.00025, 500, false, false);

UPDATE reservoir_specs
  SET name = 'microfuge rack'
  WHERE name = 'microfuge plate';

-- remove tables and columns that are not required anymore

ALTER TABLE executed_liquid_transfer
  ALTER COLUMN planned_liquid_transfer_id SET NOT NULL;
ALTER TABLE executed_liquid_transfer DROP COLUMN planned_transfer_id;

DROP TABLE old_planned_worklist_member;
ALTER TABLE planned_worklist_member
  ALTER COLUMN planned_liquid_transfer_id SET NOT NULL;
ALTER TABLE planned_worklist_member DROP COLUMN planned_transfer_id;
ALTER TABLE planned_worklist_member
  DROP CONSTRAINT planned_worklist_member_pkey1;
ALTER TABLE planned_worklist_member
  ADD CONSTRAINT planned_worklist_member_pkey
  PRIMARY KEY (planned_worklist_id, planned_liquid_transfer_id);
ALTER TABLE planned_worklist_member DROP COLUMN tmp_id;
ALTER TABLE planned_worklist_member DROP COLUMN tmp_transfer_type;

DROP TABLE planned_container_dilution;
DROP TABLE planned_rack_transfer;
DROP TABLE planned_container_transfer;
DROP TABLE planned_transfer;

-- rename transfer types

ALTER TABLE executed_liquid_transfer RENAME COLUMN type TO transfer_type;
ALTER TABLE executed_liquid_transfer
  DROP CONSTRAINT executed_transfer_type_fkey;
ALTER TABLE executed_liquid_transfer
  ADD CONSTRAINT executed_transfer_type_fkey
  FOREIGN KEY (transfer_type) REFERENCES transfer_type (name)
  ON UPDATE CASCADE;

UPDATE transfer_type SET name = 'SAMPLE_DILUTION'
 WHERE name = 'CONTAINER_DILUTION';
UPDATE transfer_type SET name = 'SAMPLE_TRANSFER'
 WHERE name = 'CONTAINER_TRANSFER';
UPDATE transfer_type SET name = 'RACK_SAMPLE_TRANSFER'
 WHERE name = 'RACK_TRANSFER';

-- alter modification permissions

REVOKE UPDATE, DELETE ON TABLE planned_liquid_transfer FROM knime, thelma;
REVOKE UPDATE, DELETE ON TABLE planned_sample_dilution FROM knime, thelma;
REVOKE UPDATE, DELETE ON TABLE planned_sample_transfer FROM knime, thelma;
REVOKE UPDATE, DELETE ON TABLE planned_rack_sample_transfer FROM knime, thelma;
REVOKE UPDATE ON TABLE planned_worklist_member FROM knime, thelma;
REVOKE UPDATE ON TABLE rack_position_set FROM knime, thelma;

CREATE OR REPLACE VIEW db_version AS SELECT 17.3 AS version;