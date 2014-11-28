-- libraries, ISOs and experiment metadata contain pool sets instead of
-- molecule design sets

select assert('(select version from db_version) = 209.0004');


CREATE TABLE pool_set (
  pool_set_id SERIAL PRIMARY KEY
);

CREATE TABLE pool_set_member (
  pool_set_id INTEGER NOT NULL
    REFERENCES pool_set (pool_set_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  pool_id INTEGER NOT NULL
    REFERENCES stock_sample_molecule_design_set (molecule_design_set_id),
  CONSTRAINT pool_set_member_pkey PRIMARY KEY (pool_set_id, pool_id)
);

ALTER TABLE molecule_design_library DROP COLUMN molecule_design_set_id;
ALTER TABLE molecule_design_library
  ADD COLUMN pool_set_id INTEGER NOT NULL
  REFERENCES pool_set (pool_set_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE library_creation_iso
  ADD COLUMN pool_set_id INTEGER NOT NULL
  REFERENCES pool_set (pool_set_id)
  ON UPDATE CASCADE ON DELETE CASCADE;


CREATE OR REPLACE VIEW db_version AS SELECT 209.0005 AS version;