-- introduces a new metadata type table including a new type ('ORDER_ONLY' for
-- ISO requests without experiment)

SELECT assert('(select version from db_version) = 209.0013');

CREATE TABLE experiment_metadata_type (
  experiment_metadata_type_id VARCHAR(10) PRIMARY KEY,
  display_name VARCHAR NOT NULL
);

INSERT INTO experiment_metadata_type (experiment_metadata_type_id, display_name)
  VALUES ('OPTI', 'optimisation with robot-support');

INSERT INTO experiment_metadata_type (experiment_metadata_type_id, display_name)
  VALUES ('MANUAL', 'manual optimisation');

INSERT INTO experiment_metadata_type (experiment_metadata_type_id, display_name)
  VALUES ('SCREEN', 'screening');

INSERT INTO experiment_metadata_type (experiment_metadata_type_id, display_name)
  VALUES ('LIBRARY', 'library screening');

INSERT INTO experiment_metadata_type (experiment_metadata_type_id, display_name)
  VALUES ('ISO-LESS', 'seeding (without ISO)');

INSERT INTO experiment_metadata_type (experiment_metadata_type_id, display_name)
  VALUES ('QPCR', 'qPCR');

INSERT INTO experiment_metadata_type (experiment_metadata_type_id, display_name)
  VALUES ('ORDER_ONLY', 'ISO without experiment');


ALTER TABLE experiment_metadata
  ADD COLUMN experiment_metadata_type_id VARCHAR(10)
  REFERENCES experiment_metadata_type (experiment_metadata_type_id)
  ON UPDATE CASCADE ON DELETE NO ACTION;

UPDATE experiment_metadata
  SET experiment_metadata_type_id = experiment_type;

ALTER TABLE experiment_metadata
  ALTER COLUMN experiment_metadata_type_id SET NOT NULL;

ALTER TABLE experiment_metadata DROP COLUMN experiment_type;


CREATE OR REPLACE VIEW db_version AS SELECT 209.0014 AS version;