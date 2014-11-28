-- Adjust experiment table for new cell experiment support (extract source
-- rack column into separate table) and remove unused description column

SELECT assert('(select version from db_version) = 209.0011');


ALTER TABLE new_experiment DROP COLUMN description;

CREATE TABLE experiment_source_rack (
  experiment_id INTEGER NOT NULL
    REFERENCES new_experiment (experiment_id)
    ON UPDATE CASCADE ON DELETE NO ACTION,
  rack_id INTEGER NOT NULL
    REFERENCES rack (rack_id)
    ON UPDATE CASCADE ON DELETE NO ACTION,
  CONSTRAINT experiment_source_rack_pkey
    PRIMARY KEY (experiment_id)
);

INSERT INTO experiment_source_rack (experiment_id, rack_id)
  SELECT e.experiment_id, e.source_rack_id
  FROM new_experiment e;

ALTER TABLE new_experiment DROP COLUMN source_rack_id;


CREATE OR REPLACE VIEW db_version AS SELECT 209.0012 AS version;