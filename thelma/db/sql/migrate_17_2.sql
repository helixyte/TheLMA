-- In the course of the ISO processing revision we need get rid of some
-- job restriction (pool stock sample creation ISOs for instance do not need
-- a subproject) and thus added a little refactoring of the job handling.
-- The old Celma jobs are maintained (including the DB infrastructure), however,
-- TheLMA jobs are migrated to the new table and removed from the old one.

SELECT assert('(select version from db_version) = 17.1');

CREATE TABLE new_job (
  job_id SERIAL PRIMARY KEY,
  job_type VARCHAR(10) NOT NULL,
  label VARCHAR(40) NOT NULL,
  user_id INTEGER NOT NULL
	REFERENCES db_user (db_user_id)
	ON DELETE RESTRICT ON UPDATE RESTRICT,
  creation_time TIMESTAMP WITH TIME ZONE NOT NULL,
  old_job_id INTEGER NOT NULL REFERENCES job (job_id),
  CONSTRAINT job_valid_type
    CHECK (job_type IN ('ISO', 'EXPERIMENT', 'BASE'))
);


-- migrate ISO jobs

INSERT INTO new_job (job_type, old_job_id, label, user_id, creation_time)
  SELECT 'ISO' AS job_type, oj.job_id, oj.label, oj.db_user_id, oj.start_time
  FROM job oj
  WHERE oj.type = 'ISO_PROCESSING';

ALTER TABLE iso_job_member RENAME COLUMN job_id TO old_job_id;
ALTER TABLE iso_job_member ADD COLUMN job_id INTEGER
  REFERENCES new_job (job_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE iso_job_stock_rack RENAME COLUMN job_id TO old_job_id;
ALTER TABLE iso_job_stock_rack ADD COLUMN job_id INTEGER
  REFERENCES new_job (job_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

UPDATE iso_job_member
  SET job_id =
    (SELECT nj.job_id FROM new_job nj
    WHERE nj.old_job_id = iso_job_member.old_job_id);

UPDATE iso_job_stock_rack
  SET job_id =
    (SELECT nj.job_id FROM new_job nj
     WHERE nj.old_job_id = iso_job_stock_rack.old_job_id);

ALTER TABLE iso_job_member DROP COLUMN old_job_id;
ALTER TABLE iso_job_member ALTER COLUMN job_id SET NOT NULL;
ALTER TABLE iso_job_stock_rack DROP COLUMN old_job_id;
ALTER TABLE iso_job_stock_rack ALTER COLUMN job_id SET NOT NULL;

-- migrate experiment jobs

INSERT INTO new_job (job_type, old_job_id, label, user_id, creation_time)
  SELECT 'EXPERIMENT' as job_type, oj.job_id, oj.label, oj.db_user_id,
  	oj.start_time
  FROM job oj
  WHERE oj.type = 'RNAI_EXPERIMENT'
  AND EXISTS (SELECT * from new_experiment ne WHERE oj.job_id = ne.job_id);

ALTER TABLE new_experiment RENAME COLUMN job_id TO old_job_id;
ALTER TABLE new_experiment ADD COLUMN job_id INTEGER
  REFERENCES new_job (job_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

UPDATE new_experiment
  SET job_id =
    (SELECT nj.job_id FROM new_job nj
    WHERE nj.old_job_id = new_experiment.old_job_id);

ALTER TABLE new_experiment DROP COLUMN old_job_id;
ALTER TABLE new_experiment ALTER COLUMN job_id SET NOT NULL;

-- remove migrated job records from old table and remove
-- tables not required anymore

CREATE TABLE tmp_jobs_to_delete (old_job_id INTEGER);
INSERT INTO tmp_jobs_to_delete (old_job_id) SELECT old_job_id from new_job;
ALTER TABLE new_job DROP COLUMN old_job_id;
DELETE FROM job oj
  WHERE oj.job_id IN (SELECT old_job_id FROM tmp_jobs_to_delete);
DROP TABLE tmp_jobs_to_delete;

DROP TABLE iso_job;


-- ISO job plates are new, there is nothing to be migrated

CREATE TABLE iso_job_preparation_plate (
  iso_job_preparation_plate_id SERIAL PRIMARY KEY,
  rack_id INTEGER NOT NULL REFERENCES rack (rack_id),
  rack_layout_id INTEGER NOT NULL
    REFERENCES rack_layout (rack_layout_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  job_id INTEGER NOT NULL
    REFERENCES job (job_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT iso_job_unique_preparation_plate UNIQUE (rack_id)
);


CREATE OR REPLACE VIEW db_version AS SELECT 17.2 AS version;