-- Migration script for Cell Line addition
-- BEGIN;

-- Add column address to table organization

ALTER TABLE organization 
    ADD COLUMN address VARCHAR;


-- Create new table cell_culture_ware

CREATE TABLE cell_culture_ware (
                cell_culture_ware_id SERIAL PRIMARY KEY,
                label VARCHAR(128) UNIQUE NOT NULL,
				supplier_id INTEGER NOT NULL REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                size DOUBLE PRECISION NOT NULL,
                coating VARCHAR NOT NULL
);
COMMENT ON TABLE cell_culture_ware IS 'Recommended plasticware for the cell line culture.';
COMMENT ON COLUMN cell_culture_ware.label IS 'A label to uniquely identify the type of platicware.';
COMMENT ON COLUMN cell_culture_ware.supplier_id IS 'Reference to the company that provided the plasticware.';
COMMENT ON COLUMN cell_culture_ware.size IS 'The minimum recommended size of the wells to grow the cells, in square cm.';


-- Create new table tissue

CREATE TABLE tissue (
                tissue_id SERIAL PRIMARY KEY,
				label VARCHAR(128) UNIQUE NOT NULL
);


-- Create new table cell_line

CREATE TABLE public.cell_line (
                cell_line_id SERIAL PRIMARY KEY,
                label VARCHAR(128) UNIQUE NOT NULL,
                species_id INTEGER NOT NULL REFERENCES species(species_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                origin TEXT NOT NULL,
                tissue_id INTEGER NOT NULL REFERENCES tissue(tissue_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                supplier_id INTEGER NOT NULL REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                image TEXT NOT NULL,
                is_type_immortal BOOLEAN NOT NULL,
                is_type_adherent BOOLEAN NOT NULL,
                safety_level SMALLINT NOT NULL,
                protocol_splitting VARCHAR NOT NULL,
                protocol_media VARCHAR NOT NULL,
                protocol_thawing VARCHAR NOT NULL,
                cell_culture_ware_id INTEGER NOT NULL REFERENCES cell_culture_ware(cell_culture_ware_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                maximum_passage INTEGER NOT NULL,
                culture_conditions_temperature DOUBLE PRECISION NOT NULL,
                culture_conditions_humidity DOUBLE PRECISION NOT NULL,
                culture_conditions_co2 DOUBLE PRECISION NOT NULL,
                comments VARCHAR,
                CONSTRAINT valid_safety_level CHECK (safety_level IN (1, 2, 3, 4))
);
COMMENT ON COLUMN public.cell_line.origin IS 'A free text explanation of the origin of the cell line (where it was bought, etc)';
COMMENT ON COLUMN public.cell_line.image IS 'An image of how the cell line should look like, in base64 format';
COMMENT ON COLUMN public.cell_line.is_type_immortal IS 'Whether the cell line is immortalized (t) or primary (f)';
COMMENT ON COLUMN public.cell_line.is_type_adherent IS 'Whether the cell line is adherent (t) or growing in suspension (f)';
COMMENT ON COLUMN public.cell_line.safety_level IS 'ENUM type with values 1, 2, 3, 4';
COMMENT ON COLUMN public.cell_line.protocol_splitting IS 'Free text description of the protocol for splitting the cells';
COMMENT ON COLUMN public.cell_line.protocol_media IS 'Free text description of the recommended growing media';
COMMENT ON COLUMN public.cell_line.protocol_thawing IS 'Free text description of the thawing protocol';
COMMENT ON COLUMN public.cell_line.cell_culture_ware_id IS 'Reference to recommended plasticware for the cells line culture';
COMMENT ON COLUMN public.cell_line.maximum_passage IS 'How many passages should be allowed for this cell line.
In the future, we might want to add a warning in the UI when the passage of the cell_line_batch is dangerousely close to maximum_passage.';
COMMENT ON COLUMN public.cell_line.culture_conditions_temperature IS 'Temperature at which the cells should be grown';
COMMENT ON COLUMN public.cell_line.culture_conditions_humidity IS 'Humidity at which the cells should be grown';
COMMENT ON COLUMN public.cell_line.culture_conditions_co2 IS 'CO2 concentration at which the cells should be grown';
COMMENT ON COLUMN public.cell_line.comments IS 'Additional comments about the cell line';


-- Create new table cell_line_batch

CREATE TABLE cell_line_batch (
                cell_line_batch_id SERIAL PRIMARY KEY,
                container_id INTEGER NOT NULL REFERENCES container(container_id) ON UPDATE CASCADE ON DELETE RESTRICT,
				cell_line_id INTEGER NOT NULL REFERENCES cell_line(cell_line_id) ON UPDATE CASCADE ON DELETE RESTRICT,
				subproject_id INTEGER NOT NULL REFERENCES subproject(subproject_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                freezing_date TIMESTAMP NOT NULL,
                defrosting_date TIMESTAMP,
                passage INTEGER NOT NULL,
                is_master_stock BOOLEAN DEFAULT true NOT NULL,
				parent_cell_line_batch_id INTEGER REFERENCES cell_line_batch(cell_line_batch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
                cell_count BIGINT NOT NULL,
                freezing_medium_dmso DOUBLE PRECISION NOT NULL,
                freezing_medium_serum DOUBLE PRECISION NOT NULL,
                freezing_medium_medium DOUBLE PRECISION NOT NULL,
                comments VARCHAR
);
COMMENT ON COLUMN public.cell_line_batch.container_id IS 'Container (TUBE) where the cells are stored.';
COMMENT ON COLUMN public.cell_line_batch.cell_line_id IS 'Cell line contained in the batch.';
COMMENT ON COLUMN public.cell_line_batch.subproject_id IS 'Surrogate primary key of the subproject.';
COMMENT ON COLUMN public.cell_line_batch.freezing_date IS 'Date when the batch was frozen. Use DATE@00:00:00 to denote the precise time is unspecified (only the date is).';
COMMENT ON COLUMN public.cell_line_batch.defrosting_date IS 'Optional date at which the cells were defrosted, if any, in the same format and convention than freezing_date. NULL if the cells are still frozen.';
COMMENT ON COLUMN public.cell_line_batch.passage IS 'Passage number when the cells were frozen. Refers to cell_line.maximum_passage';
COMMENT ON COLUMN public.cell_line_batch.is_master_stock IS 'Whether a master (t) or working (f) stock is stored.';
COMMENT ON COLUMN public.cell_line_batch.parent_cell_line_batch_id IS 'If the batch is a working stock, what is the parent?';
COMMENT ON COLUMN public.cell_line_batch.cell_count IS 'Approximate number of cells that were frozen in the tube';
COMMENT ON COLUMN public.cell_line_batch.freezing_medium_dmso IS '%DMSO in the freezing medium';
COMMENT ON COLUMN public.cell_line_batch.freezing_medium_serum IS '% serum in the freezing medium';
COMMENT ON COLUMN public.cell_line_batch.freezing_medium_medium IS '% medium in the freezing medium';
COMMENT ON COLUMN public.cell_line_batch.comments IS 'Additional comments about the batch';


-- VERSION number

DROP VIEW IF EXISTS db_version;
CREATE VIEW db_version AS
    SELECT 210.0000 AS version;


-- ROLLBACK;
