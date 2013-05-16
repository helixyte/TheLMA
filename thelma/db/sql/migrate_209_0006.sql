-- create pool set tables for ISOs and experiment metadata

select assert('(select version from db_version) = 209.0005');

-- some table renaming

ALTER TABLE stock_sample_molecule_design_set RENAME TO molecule_design_pool;

ALTER TABLE pool_set RENAME TO molecule_design_pool_set;
ALTER TABLE pool_set_member RENAME TO molecule_design_pool_set_member;
ALTER TABLE molecule_design_pool_set
  RENAME COLUMN pool_set_id TO molecule_design_pool_set_id;
ALTER TABLE molecule_design_pool_set_member
  RENAME COLUMN pool_set_id TO molecule_design_pool_set_id;
ALTER TABLE molecule_design_pool_set_member
  RENAME COLUMN pool_id TO molecule_design_pool_id;

-- create new association tables

CREATE TABLE experiment_metadata_pool_set (
  experiment_metadata_id INTEGER NOT NULL
    REFERENCES experiment_metadata (experiment_metadata_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  molecule_design_pool_set_id INTEGER NOT NULL
    REFERENCES molecule_design_pool_set (molecule_design_pool_set_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT experiment_metadata_pool_set_pkey
    PRIMARY KEY (experiment_metadata_id)
);

CREATE TABLE iso_pool_set (
  iso_id INTEGER NOT NULL
    REFERENCES iso (iso_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  molecule_design_pool_set_id INTEGER NOT NULL
    REFERENCES molecule_design_pool_set (molecule_design_pool_set_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT iso_pool_set_pkey
    PRIMARY KEY (iso_id)
);

-- migrate data from library creation ISO table to association table

INSERT INTO iso_pool_set (iso_id, molecule_design_pool_set_id)
  SELECT iso_id, pool_set_id
  FROM library_creation_iso;

ALTER TABLE library_creation_iso DROP COLUMN pool_set_id;

-- add molecule type to pool set table

ALTER TABLE molecule_design_pool_set
  ADD COLUMN molecule_type_id VARCHAR(20) NOT NULL
  REFERENCES molecule_type (molecule_type_id)
  DEFAULT 'SIRNA';

ALTER TABLE molecule_design_pool_set
  ALTER COLUMN molecule_type_id DROP DEFAULT;

update molecule_design_set
    set set_type='POOL'
    where set_type='STOCK_SAMPLE';
    
    
alter table molecule_design_library
    rename column pool_set_id to molecule_design_pool_set_id;

CREATE OR REPLACE VIEW db_version AS SELECT 209.0006 AS version;