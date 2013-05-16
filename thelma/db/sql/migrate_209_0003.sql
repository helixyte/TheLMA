-- extracts some columns from the experiment metadata (molecule design set,
-- target set and ISO request) and from the ISO table (molecule design set)
-- and removes the some columns that are not needed anymore (all related
-- to experiment metadata and ISO request)


select assert('(select version from db_version) = 209.0002');

-- create association tables

CREATE TABLE experiment_metadata_iso_request (
  experiment_metadata_id INTEGER NOT NULL
    REFERENCES experiment_metadata (experiment_metadata_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  iso_request_id INTEGER NOT NULL
    REFERENCES iso_request (iso_request_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT experiment_metadata_iso_request_pkey
    PRIMARY KEY (experiment_metadata_id)
);

CREATE TABLE experiment_metadata_molecule_design_set (
  experiment_metadata_id INTEGER NOT NULL
    REFERENCES experiment_metadata (experiment_metadata_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  molecule_design_set_id INTEGER NOT NULL
    REFERENCES molecule_design_set (molecule_design_set_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT experiment_metadata_molecule_design_set_pkey
    PRIMARY KEY (experiment_metadata_id)
);

CREATE TABLE experiment_metadata_target_set (
  experiment_metadata_id INTEGER NOT NULL
    REFERENCES experiment_metadata (experiment_metadata_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  target_set_id INTEGER NOT NULL
    REFERENCES target_set (target_set_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT experiment_metadata_target_set_pkey
    PRIMARY KEY (experiment_metadata_id)
);

CREATE TABLE iso_molecule_design_set (
  iso_id INTEGER NOT NULL
    REFERENCES iso (iso_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  molecule_design_set_id INTEGER NOT NULL
    REFERENCES molecule_design_set (molecule_design_set_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT iso_molecule_design_set_pkey
    PRIMARY KEY (iso_id)
);


-- migrate data

INSERT INTO experiment_metadata_iso_request(
            experiment_metadata_id, iso_request_id)
  SELECT experiment_metadata_id, iso_request_id
  FROM experiment_metadata;

INSERT INTO experiment_metadata_molecule_design_set(
            experiment_metadata_id, molecule_design_set_id)
  SELECT experiment_metadata_id, molecule_design_set_id
  FROM experiment_metadata;

INSERT INTO experiment_metadata_target_set(
            experiment_metadata_id, target_set_id)
  SELECT experiment_metadata_id, target_set_id
  FROM experiment_metadata;

INSERT INTO iso_molecule_design_set(iso_id, molecule_design_set_id)
  SELECT iso_id, molecule_design_set_id
  FROM iso;


-- the ticket ID needs to be shifted to the experiment metadata because
-- not all experiment designs will have a ticket anymore

ALTER TABLE experiment_metadata
  ADD COLUMN ticket_number INTEGER;

UPDATE experiment_metadata
SET ticket_number = iso_request.ticket_number
FROM iso_request
WHERE iso_request.iso_request_id = experiment_metadata.iso_request_id;

ALTER TABLE experiment_metadata ALTER COLUMN ticket_number SET NOT NULL;
ALTER TABLE experiment_metadata ADD UNIQUE (ticket_number);

-- remove columns

ALTER TABLE experiment_metadata DROP COLUMN iso_request_id;
ALTER TABLE experiment_metadata DROP COLUMN molecule_design_set_id;
ALTER TABLE experiment_metadata DROP COLUMN target_set_id;
ALTER TABLE iso DROP COLUMN molecule_design_set_id;

ALTER TABLE experiment_design DROP COLUMN description;
ALTER TABLE experiment_design DROP COLUMN label;

ALTER TABLE iso_request DROP COLUMN ticket_number;
ALTER TABLE iso_request DROP COLUMN molecule_type_id;

-- remove empty molecule design and target sets

DELETE FROM molecule_design_set
WHERE molecule_design_set.molecule_design_set_id IN
  (SELECT mds.molecule_design_set_id
   FROM molecule_design_set mds LEFT OUTER JOIN molecule_design_set_member mdsm
     USING (molecule_design_set_id)
   WHERE NOT mds.set_type = 'STOCK_SAMPLE'
   GROUP BY mds.molecule_design_set_id, mds.set_type
   HAVING COUNT(mdsm.molecule_design_id) = 0);

DELETE FROM target_set
WHERE target_set.target_set_id IN
  (SELECT ts.target_set_id
   FROM target_set ts LEFT OUTER JOIN target_set_member tsm
     USING (target_set_id)
   GROUP BY ts.target_set_id
   HAVING COUNT(tsm.target_id) = 0);


-- add new experiment type for seeding experiments

ALTER TABLE experiment_metadata DROP CONSTRAINT valid_experiment_metadata;
ALTER TABLE experiment_metadata ADD CONSTRAINT valid_experiment_metadata
  CHECK (experiment_type IN ('OPTI', 'SCREEN', 'MANUAL', 'RTPCR', 'ISO-LESS'));


CREATE OR REPLACE VIEW db_version AS SELECT 209.0003 AS version;