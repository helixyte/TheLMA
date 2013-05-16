-- Replaces the old rack position table with a new one that contains 1536
-- positions (incl. labels) and does not accept duplicate positions (unlike
-- the current one). At this, we also have to replace the foreign keys in the
-- tube transfer, rack position set member and planned transfer tables.
-- The PRE script renames the old table and columns in the referencing tables
-- and creates the new structures.
--
-- The new tables and columns will be populated by a python script.
-- The POST script then removes the old columns and tables.
-- see #426
--
-- We create, populate and drop the temporary table for each table separately
-- do speed up things (the update takes much longer if there are many
-- records in the temporary table).


select assert('(select version from db_version) = 209.00111');


-- setting up an intermediate table for rack position storage

CREATE TABLE tmp_position_map (
	old_rack_position_id INTEGER NOT NULL
	  REFERENCES old_rack_position (old_rack_position_id),
	rack_position_id INTEGER NOT NULL
	  REFERENCES rack_position (rack_position_id)
);

-- populate intermediate table, collect old rack positions from the
-- referencing tables and find the corresponding new rack positions

INSERT INTO tmp_position_map (old_rack_position_id, rack_position_id)
	SELECT pos.old_rack_position_id, pos.rack_position_id
	FROM (SELECT tt.old_target_position_id AS old_rack_position_id,
	  rp.rack_position_id AS rack_position_id
	 FROM tube_transfer tt, old_rack_position orp, rack_position rp
	 WHERE tt.old_target_position_id = orp.old_rack_position_id
	 AND orp.row_index = rp.row_index
	 AND orp.column_index = rp.column_index) as pos;

INSERT INTO tmp_position_map (old_rack_position_id, rack_position_id)
	SELECT pos.old_rack_position_id, pos.rack_position_id
	FROM (SELECT tt.old_source_position_id AS old_rack_position_id,
	  rp.rack_position_id AS rack_position_id
	 FROM tube_transfer tt, old_rack_position orp, rack_position rp
	 WHERE tt.old_source_position_id = orp.old_rack_position_id
	 AND orp.row_index = rp.row_index
	 AND orp.column_index = rp.column_index) as pos;

-- update data in the referencing tables

UPDATE tube_transfer
SET target_position_id = (
    SELECT DISTINCT tmp.rack_position_id
    FROM tube_transfer tt INNER JOIN tmp_position_map tmp
    ON tt.old_target_position_id = tmp.old_rack_position_id
    WHERE tube_transfer.tube_transfer_id = tt.tube_transfer_id);

UPDATE tube_transfer
SET source_position_id = (
    SELECT DISTINCT tmp.rack_position_id
    FROM tube_transfer tt INNER JOIN tmp_position_map tmp
    ON tt.old_source_position_id = tmp.old_rack_position_id
    WHERE tube_transfer.tube_transfer_id = tt.tube_transfer_id);

-- drop table

DROP TABLE tmp_position_map;

-- planned container dilutions

CREATE TABLE tmp_position_map (
	old_rack_position_id INTEGER NOT NULL
	  REFERENCES old_rack_position (old_rack_position_id),
	rack_position_id INTEGER NOT NULL
	  REFERENCES rack_position (rack_position_id)
);

INSERT INTO tmp_position_map (old_rack_position_id, rack_position_id)
	SELECT pos.old_rack_position_id, pos.rack_position_id
	FROM (SELECT pcd.old_target_position_id AS old_rack_position_id,
	  rp.rack_position_id AS rack_position_id
	 FROM planned_container_dilution pcd, old_rack_position orp,
	   rack_position rp
	 WHERE pcd.old_target_position_id = orp.old_rack_position_id
	 AND orp.row_index = rp.row_index
	 AND orp.column_index = rp.column_index) as pos;

UPDATE planned_container_dilution
SET target_position_id = (
    SELECT DISTINCT tmp.rack_position_id
    FROM planned_container_dilution pcd INNER JOIN tmp_position_map tmp
    ON pcd.old_target_position_id = tmp.old_rack_position_id
    WHERE planned_container_dilution.planned_transfer_id = pcd.planned_transfer_id);

DROP TABLE tmp_position_map;

-- planned container transfers (source)

CREATE TABLE tmp_position_map (
	old_rack_position_id INTEGER NOT NULL
	  REFERENCES old_rack_position (old_rack_position_id),
	rack_position_id INTEGER NOT NULL
	  REFERENCES rack_position (rack_position_id)
);

INSERT INTO tmp_position_map (old_rack_position_id, rack_position_id)
	SELECT pos.old_rack_position_id, pos.rack_position_id
	FROM (SELECT pct.old_source_position_id AS old_rack_position_id,
	  rp.rack_position_id AS rack_position_id
	 FROM planned_container_transfer pct, old_rack_position orp,
	   rack_position rp
	 WHERE pct.old_source_position_id = orp.old_rack_position_id
	 AND orp.row_index = rp.row_index
	 AND orp.column_index = rp.column_index) as pos;

UPDATE planned_container_transfer
SET source_position_id = (
    SELECT DISTINCT tmp.rack_position_id
    FROM planned_container_transfer pct INNER JOIN tmp_position_map tmp
    ON pct.old_source_position_id = tmp.old_rack_position_id
    WHERE planned_container_transfer.planned_transfer_id = pct.planned_transfer_id);

DROP TABLE tmp_position_map;

-- planned container transfers (target)

CREATE TABLE tmp_position_map (
	old_rack_position_id INTEGER NOT NULL
	  REFERENCES old_rack_position (old_rack_position_id),
	rack_position_id INTEGER NOT NULL
	  REFERENCES rack_position (rack_position_id)
);

INSERT INTO tmp_position_map (old_rack_position_id, rack_position_id)
	SELECT pos.old_rack_position_id, pos.rack_position_id
	FROM (SELECT pct.old_target_position_id AS old_rack_position_id,
	  rp.rack_position_id AS rack_position_id
	 FROM planned_container_transfer pct, old_rack_position orp,
	   rack_position rp
	 WHERE pct.old_target_position_id = orp.old_rack_position_id
	 AND orp.row_index = rp.row_index
	 AND orp.column_index = rp.column_index) as pos;

UPDATE planned_container_transfer
SET target_position_id = (
    SELECT DISTINCT tmp.rack_position_id
    FROM planned_container_transfer pct INNER JOIN tmp_position_map tmp
    ON pct.old_target_position_id = tmp.old_rack_position_id
    WHERE planned_container_transfer.planned_transfer_id = pct.planned_transfer_id);

DROP TABLE tmp_position_map;


-- rack position set member

CREATE TABLE tmp_position_map (
	old_rack_position_id INTEGER NOT NULL
	  REFERENCES old_rack_position (old_rack_position_id),
	rack_position_id INTEGER NOT NULL
	  REFERENCES rack_position (rack_position_id)
);

INSERT INTO tmp_position_map (old_rack_position_id, rack_position_id)
	SELECT pos.old_rack_position_id, pos.rack_position_id
	FROM (SELECT rpsm.old_rack_position_id AS old_rack_position_id,
	  rp.rack_position_id AS rack_position_id
	 FROM rack_position_set_member rpsm, old_rack_position orp, rack_position rp
	 WHERE rpsm.old_rack_position_id = orp.old_rack_position_id
	 AND orp.row_index = rp.row_index
	 AND orp.column_index = rp.column_index) as pos;

UPDATE rack_position_set_member
SET rack_position_id = (
    SELECT DISTINCT tmp.rack_position_id
    FROM rack_position_set_member rpsm INNER JOIN tmp_position_map tmp
    ON rpsm.old_rack_position_id = tmp.old_rack_position_id
    WHERE rack_position_set_member.rack_position_set_id = rpsm.rack_position_set_id
    AND rack_position_set_member.old_rack_position_id = rpsm.old_rack_position_id);

DROP TABLE tmp_position_map;

-- sets positions to null, drops old columns and table

ALTER TABLE tube_transfer DROP COLUMN old_source_position_id;
ALTER TABLE tube_transfer DROP COLUMN old_target_position_id;
ALTER TABLE tube_transfer ALTER COLUMN
  source_position_id SET NOT NULL;
ALTER TABLE tube_transfer ALTER COLUMN
  target_position_id SET NOT NULL;

ALTER TABLE planned_container_dilution DROP COLUMN old_target_position_id;
ALTER TABLE planned_container_dilution ALTER COLUMN
  target_position_id SET NOT NULL;

ALTER TABLE planned_container_transfer DROP COLUMN old_source_position_id;
ALTER TABLE planned_container_transfer DROP COLUMN old_target_position_id;
ALTER TABLE planned_container_transfer ALTER COLUMN
  source_position_id SET NOT NULL;
ALTER TABLE planned_container_transfer ALTER COLUMN
  target_position_id SET NOT NULL;

ALTER TABLE rack_position_set_member DROP COLUMN old_rack_position_id;
ALTER TABLE rack_position_set_member ALTER COLUMN
  rack_position_id SET NOT NULL;
ALTER TABLE rack_position_set_member
  ADD CONSTRAINT rack_position_set_member_pkey
  PRIMARY KEY (rack_position_set_id, rack_position_id);

DROP TABLE old_rack_position;


-- restrict to read-only
-- This is not as easy since some proposed ways I have found did not work
-- (e.g. ALTER TABLE rack_position SET READ ONLY)

GRANT SELECT ON TABLE rack_position TO knime, thelma, reader_role, writer_role;
REVOKE INSERT, UPDATE, DELETE ON TABLE rack_position FROM knime, thelma;


CREATE OR REPLACE VIEW db_version AS SELECT 209.0011 AS version;