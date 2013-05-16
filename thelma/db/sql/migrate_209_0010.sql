-- Rack position sets should be unique. We want to get rid on duplicate and
-- unused rack position sets. Duplication detected by the hash value.

-- rack positions sets should be unique in the future as well

--ALTER TABLE rack_position_set_member
--  DROP CONSTRAINT rack_position_set_member_rack_position_set_id_fkey;
--ALTER TABLE rack_position_set_member
--  ADD CONSTRAINT rack_position_set_member_rack_position_set_id_fkey
--  FOREIGN KEY (rack_position_set_id)
--  REFERENCES rack_position_set (rack_position_set_id)
--  ON UPDATE RESTRICT ON DELETE RESTRICT;

select assert('(select version from db_version) = 209.0009');


-- get and delete unused rack position sets; at this alter deletion and
-- update conditions for the rack position set member table

CREATE TABLE tmp_unused_sets (
	rack_position_set_id INTEGER NOT NULL UNIQUE
);

INSERT INTO tmp_unused_sets (rack_position_set_id)
  SELECT rps.rack_position_set_id
  FROM rack_position_set rps LEFT JOIN tagged_rack_position_set trps
  ON rps.rack_position_set_id = trps.rack_position_set_id
  GROUP BY rps.rack_position_set_id
  HAVING COUNT(trps.rack_position_set_id) = 0;

ALTER TABLE rack_position_set_member
  DROP CONSTRAINT rack_position_set_member_rack_position_set_id_fkey;
ALTER TABLE rack_position_set_member
  ADD CONSTRAINT rack_position_set_member_rack_position_set_id_fkey
  FOREIGN KEY (rack_position_set_id)
  REFERENCES rack_position_set (rack_position_set_id)
  ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE rack_position_set_member
  DROP CONSTRAINT rack_position_set_member_rack_position_id_fkey;
ALTER TABLE rack_position_set_member
  ADD CONSTRAINT rack_position_set_member_rack_position_id_fkey
  FOREIGN KEY (rack_position_id)
  REFERENCES rack_position (rack_position_id)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

DELETE FROM rack_position_set
  WHERE rack_position_set_id IN (
    SELECT rack_position_set_id FROM tmp_unused_sets);

DROP TABLE tmp_unused_sets;


-- creating a temporary table storing the minimum rack_position_set_id
-- for each rack_position_set

CREATE TABLE tmp_rps_hash_values (
	hash_value VARCHAR UNIQUE,
	new_rack_position_set_id INTEGER NOT NULL UNIQUE
);

INSERT INTO tmp_rps_hash_values (hash_value, new_rack_position_set_id)
    SELECT rps.hash_value, MIN(rps.rack_position_set_id)
    FROM rack_position_set rps
    GROUP BY rps.hash_value;


-- creating a temporary table storing the old rack_positions_set_id for each
-- minimum rack_position_set_id

CREATE TABLE tmp_rps_old_new (
  old_rack_position_set_id INTEGER NOT NULL UNIQUE,
  new_rack_position_set_id INTEGER NOT NULL
    REFERENCES tmp_rps_hash_values (new_rack_position_set_id)
);

INSERT INTO tmp_rps_old_new (old_rack_position_set_id, new_rack_position_set_id)
  SELECT ass.old_rack_position_set_id, ass.new_rack_position_set_id
  FROM (SELECT rps.rack_position_set_id AS old_rack_position_set_id,
               tmp.new_rack_position_set_id AS new_rack_position_set_id
        FROM rack_position_set rps, tmp_rps_hash_values tmp
        WHERE rps.hash_value = tmp.hash_value) as ass;

-- update referencing tagged_rack_position_set table

ALTER TABLE tagged_rack_position_set RENAME COLUMN
	rack_position_set_id TO old_rack_position_set_id;

ALTER TABLE tagged_rack_position_set ADD COLUMN
  new_rack_position_set_id INTEGER
  REFERENCES rack_position_set (rack_position_set_id);

UPDATE tagged_rack_position_set
SET new_rack_position_set_id = (
  SELECT tmp.new_rack_position_set_id
  FROM tagged_rack_position_set trps INNER JOIN tmp_rps_old_new tmp
  ON trps.old_rack_position_set_id = tmp.old_rack_position_set_id
  WHERE tagged_rack_position_set.tagged_id = trps.tagged_id);

ALTER TABLE tagged_rack_position_set
  DROP COLUMN old_rack_position_set_id;
ALTER TABLE tagged_rack_position_set RENAME COLUMN
  new_rack_position_set_id TO rack_position_set_id;

DROP TABLE tmp_rps_old_new;
DROP TABLE tmp_rps_hash_values;


-- delete now unused (duplicate) sets from the rack position set table

CREATE TABLE tmp_unused_sets (
	rack_position_set_id INTEGER NOT NULL UNIQUE
);

INSERT INTO tmp_unused_sets (rack_position_set_id)
  SELECT rps.rack_position_set_id
  FROM rack_position_set rps LEFT JOIN tagged_rack_position_set trps
  ON rps.rack_position_set_id = trps.rack_position_set_id
  GROUP BY rps.rack_position_set_id
  HAVING COUNT(trps.rack_position_set_id) = 0;

DELETE FROM rack_position_set
  WHERE rack_position_set_id IN (
    SELECT rack_position_set_id FROM tmp_unused_sets);

DROP TABLE tmp_unused_sets;

-- add unique constraints

ALTER TABLE rack_position_set
  ADD CONSTRAINT unique_rack_position_set_hash_value UNIQUE (hash_value);


CREATE OR REPLACE VIEW db_version AS SELECT 209.0010 AS version;