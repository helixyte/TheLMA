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


select assert('(select version from db_version) = 209.0010');

-- rename old table and columns

ALTER TABLE rack_position RENAME TO old_rack_position;
ALTER TABLE old_rack_position RENAME COLUMN
  rack_position_id TO old_rack_position_id;

ALTER TABLE planned_container_dilution RENAME COLUMN
  target_position_id TO old_target_position_id;
ALTER TABLE planned_container_transfer RENAME COLUMN
  source_position_id TO old_source_position_id;
ALTER TABLE planned_container_transfer RENAME COLUMN
  target_position_id TO old_target_position_id;
ALTER TABLE rack_position_set_member RENAME COLUMN
  rack_position_id TO old_rack_position_id;
ALTER TABLE tube_transfer RENAME COLUMN
  source_position_id TO old_source_position_id;
ALTER TABLE tube_transfer RENAME COLUMN
  target_position_id TO old_target_position_id;

-- create new table

CREATE TABLE rack_position (
  rack_position_id SERIAL PRIMARY KEY,
  row_index INTEGER NOT NULL,
  column_index INTEGER NOT NULL,
  label VARCHAR(4) NOT NULL,
  CONSTRAINT non_negative_rack_position_row_index CHECK (row_index >= 0),
  CONSTRAINT non_negative_rack_position_column_index CHECK (column_index >= 0),
  CONSTRAINT unique_rack_position_label UNIQUE (label),
  CONSTRAINT unique_rack_position_indices UNIQUE (row_index, column_index)
);


-- create new columns in the tables referencing rack positions
-- the default values will be removed at the end of the script

ALTER TABLE planned_container_dilution ADD COLUMN
  target_position_id INTEGER
  REFERENCES rack_position (rack_position_id);

ALTER TABLE planned_container_transfer ADD COLUMN
  source_position_id INTEGER
  REFERENCES rack_position (rack_position_id);

ALTER TABLE planned_container_transfer ADD COLUMN
  target_position_id INTEGER
  REFERENCES rack_position (rack_position_id);

ALTER TABLE rack_position_set_member ADD COLUMN
  rack_position_id INTEGER
  REFERENCES rack_position (rack_position_id);

ALTER TABLE tube_transfer ADD COLUMN
  source_position_id INTEGER
  REFERENCES rack_position (rack_position_id);

ALTER TABLE tube_transfer ADD COLUMN
  target_position_id INTEGER
  REFERENCES rack_position (rack_position_id);



CREATE OR REPLACE VIEW db_version AS SELECT 209.00111 AS version;