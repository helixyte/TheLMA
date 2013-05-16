-- Enables support for pooled library generation. We try to use the ISO
-- tables, however we need a special ISO type since the ISOs for a pooled
-- library generation shall reference own tickets each.


select assert('(select version from db_version) = 209.0003');

-- add polymorphic inheritance type column to iso table and reflect in 
-- iso_request table.

ALTER TABLE iso
  ADD COLUMN iso_type CHARACTER VARYING(20) NOT NULL
  DEFAULT 'STANDARD'
  CONSTRAINT valid_iso_type CHECK
    (iso_type IN ('STANDARD', 'LIBRARY_CREATION'));

alter table iso_request
    add column iso_type character varying(20) not null
    default 'STANDARD'
    constraint valid_iso_request_iso_type check
    (iso_type in ('STANDARD', 'LIBRARY_CREATION'));
    
-- create library creation ISO table

CREATE TABLE library_creation_iso (
  iso_id INTEGER NOT NULL
    REFERENCES iso (iso_id)
    ON DELETE CASCADE,
  ticket_number INTEGER NOT NULL,
  layout_number INTEGER NOT NULL,
  CONSTRAINT library_creation_iso_pkey PRIMARY KEY (iso_id),
  CONSTRAINT ticket_number_greater_zero CHECK (ticket_number > 0),
  CONSTRAINT layout_number_greater_zero CHECK (layout_number > 0)
);


-- Create new library table (and association table to ISO requests)

DROP TABLE molecule_design_library;

CREATE TABLE molecule_design_library(
  molecule_design_library_id SERIAL PRIMARY KEY,
  label CHARACTER VARYING(25) NOT NULL UNIQUE,
  molecule_design_set_id INTEGER NOT NULL
    REFERENCES molecule_design_set (molecule_design_set_id)
);

CREATE TABLE molecule_design_library_iso_request(
  molecule_design_library_id INTEGER NOT NULL
    REFERENCES molecule_design_library (molecule_design_library_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  iso_request_id INTEGER NOT NULL
    REFERENCES iso_request (iso_request_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT molecule_design_library_iso_request_pkey
    PRIMARY KEY (molecule_design_library_id)
);


-- Since library ISOs might have several preparation plates we need to
-- create a special association table.

CREATE TABLE library_source_plate (
  library_source_plate_id SERIAL PRIMARY KEY,
  iso_id INTEGER NOT NULL
    REFERENCES library_creation_iso (iso_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  rack_id INTEGER NOT NULL UNIQUE
    REFERENCES rack (rack_id),
  sector_index INTEGER NOT NULL
);




CREATE OR REPLACE VIEW db_version AS SELECT 209.0004 AS version;