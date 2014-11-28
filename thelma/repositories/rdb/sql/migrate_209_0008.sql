-- repairing update and deletion cascades
-- at this, the experiment design metadata association is transferred to the
-- experiment metadata table

SELECT assert('(select version from db_version) = 209.0007');


-- add cascading (clean up experiment design)

ALTER TABLE experiment_design_rack
  DROP CONSTRAINT experiment_design_rack_experiment_design_id_fkey;
ALTER TABLE experiment_design_rack
  ADD CONSTRAINT experiment_design_rack_experiment_design_id_fkey
  FOREIGN KEY (experiment_design_id)
  REFERENCES experiment_design (experiment_design_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE worklist_series_experiment_design
  DROP CONSTRAINT worklist_series_experiment_design_experiment_design_id_fkey;
ALTER TABLE worklist_series_experiment_design
  ADD CONSTRAINT worklist_series_experiment_design_experiment_design_id_fkey
  FOREIGN KEY (experiment_design_id)
  REFERENCES experiment_design (experiment_design_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE worklist_series_experiment_design
  DROP CONSTRAINT worklist_series_experiment_design_worklist_series_id_fkey;
ALTER TABLE worklist_series_experiment_design
  ADD CONSTRAINT worklist_series_experiment_design_worklist_series_id_fkey
  FOREIGN KEY (worklist_series_id)
  REFERENCES worklist_series (worklist_series_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE worklist_series_experiment_design_rack
  DROP CONSTRAINT worklist_series_experiment_desig_experiment_design_rack_id_fkey;
ALTER TABLE worklist_series_experiment_design_rack
  ADD CONSTRAINT worklist_series_experiment_desig_experiment_design_rack_id_fkey
  FOREIGN KEY (experiment_design_rack_id)
  REFERENCES experiment_design_rack (experiment_design_rack_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE worklist_series_experiment_design_rack
  DROP CONSTRAINT worklist_series_experiment_design_rack_worklist_series_id_fkey;
ALTER TABLE worklist_series_experiment_design_rack
  ADD CONSTRAINT worklist_series_experiment_design_rack_worklist_series_id_fkey
  FOREIGN KEY (worklist_series_id)
  REFERENCES worklist_series (worklist_series_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE worklist_series_member
  DROP CONSTRAINT worklist_series_member_worklist_series_id_fkey;
ALTER TABLE worklist_series_member
  ADD CONSTRAINT worklist_series_member_worklist_series_id_fkey
  FOREIGN KEY (worklist_series_id)
  REFERENCES worklist_series (worklist_series_id)
  ON UPDATE CASCADE ON DELETE CASCADE;


-- delete experiment designs without reference

DELETE FROM experiment_design
  WHERE experiment_design_id IN (
    SELECT ed.experiment_design_id
    FROM experiment_design ed LEFT JOIN experiment_metadata em
    ON ed.experiment_design_id = em.experiment_design_id
    GROUP BY ed.experiment_design_id
    HAVING COUNT(em.experiment_design_id) = 0);

-- move experiment design metadata association

ALTER TABLE experiment_design
  ADD COLUMN experiment_metadata_id INTEGER
  REFERENCES experiment_metadata (experiment_metadata_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

UPDATE experiment_design
  SET experiment_metadata_id = (SELECT em.experiment_metadata_id
    FROM experiment_design ed INNER JOIN experiment_metadata em
    ON ed.experiment_design_id = em.experiment_design_id
    WHERE experiment_design.experiment_design_id = ed.experiment_design_id);

ALTER TABLE experiment_metadata DROP COLUMN experiment_design_id;
ALTER TABLE experiment_design ALTER COLUMN experiment_metadata_id SET NOT NULL;


-- add cascading (clean up rack layouts)

ALTER TABLE experiment_design_rack
  DROP CONSTRAINT experiment_design_rack_rack_layout_id_fkey;
ALTER TABLE experiment_design_rack
  ADD CONSTRAINT experiment_design_rack_rack_layout_id_fkey
  FOREIGN KEY (rack_layout_id)
  REFERENCES rack_layout (rack_layout_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE iso
  DROP CONSTRAINT iso_rack_layout_fkey;
ALTER TABLE iso
  ADD CONSTRAINT iso_rack_layout_fkey
  FOREIGN KEY (rack_layout_id)
  REFERENCES rack_layout (rack_layout_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE iso_request
  DROP CONSTRAINT iso_request_rack_layout_fkey;
ALTER TABLE iso_request
  ADD CONSTRAINT iso_request_rack_layout_fkey
  FOREIGN KEY (rack_layout_id)
  REFERENCES rack_layout (rack_layout_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE iso_control_stock_rack
  DROP CONSTRAINT iso_control_stock_rack_planned_worklist_id_fkey;
ALTER TABLE iso_control_stock_rack
  ADD CONSTRAINT iso_control_stock_rack_planned_worklist_id_fkey
  FOREIGN KEY (planned_worklist_id)
  REFERENCES planned_worklist (planned_worklist_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE iso_control_stock_rack
  DROP CONSTRAINT iso_control_stock_rack_rack_layout_id_fkey;
ALTER TABLE iso_control_stock_rack
  ADD CONSTRAINT iso_control_stock_rack_rack_layout_id_fkey
  FOREIGN KEY (rack_layout_id)
  REFERENCES rack_layout (rack_layout_id)
  ON UPDATE CASCADE ON DELETE CASCADE;


-- add cascading (clean up ISOs)

ALTER TABLE worklist_series_iso_request
  DROP CONSTRAINT worklist_series_iso_request_iso_request_id_fkey;
ALTER TABLE worklist_series_iso_request
  ADD CONSTRAINT worklist_series_iso_request_iso_request_id_fkey
  FOREIGN KEY (iso_request_id)
  REFERENCES iso_request (iso_request_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE worklist_series_iso_request
  DROP CONSTRAINT worklist_series_iso_request_worklist_series_id_fkey;
ALTER TABLE worklist_series_iso_request
  ADD CONSTRAINT worklist_series_iso_request_worklist_series_id_fkey
  FOREIGN KEY (worklist_series_id)
  REFERENCES worklist_series (worklist_series_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

-- removing unused iso_requests

CREATE TABLE tmp_exist_iso_request (
  iso_request_id INTEGER NOT NULL
  REFERENCES iso_request (iso_request_id)
);

INSERT INTO tmp_exist_iso_request
  SELECT iso_request_id
  FROM experiment_metadata_iso_request;
INSERT INTO tmp_exist_iso_request
  SELECT iso_request_id
  FROM iso_request
  WHERE iso_type = 'LIBRARY_CREATION';

DELETE FROM iso_request
  WHERE iso_request_id NOT IN (
    SELECT tmp.iso_request_id FROM tmp_exist_iso_request tmp);

DROP TABLE tmp_exist_iso_request;

-- removing unused rack layouts

ALTER TABLE tagged_rack_position_set
  DROP CONSTRAINT tagged_rack_position_set_rack_layout_id_fkey;
ALTER TABLE tagged_rack_position_set
  ADD CONSTRAINT tagged_rack_position_set_rack_layout_id_fkey
  FOREIGN KEY (rack_layout_id)
  REFERENCES rack_layout (rack_layout_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE tagging
  DROP CONSTRAINT tagging_tagged_id_fkey;
ALTER TABLE tagging
  ADD CONSTRAINT tagging_tagged_id_fkey
  FOREIGN KEY (tagged_id)
  REFERENCES tagged (tagged_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

CREATE TABLE tmp_exist_rack_layouts (
  rack_layout_id INTEGER NOT NULL
  REFERENCES rack_layout (rack_layout_id)
);

INSERT INTO tmp_exist_rack_layouts
  SELECT rack_layout_id
  FROM experiment_design_rack;
INSERT INTO tmp_exist_rack_layouts
  SELECT rack_layout_id
  FROM iso;
INSERT INTO tmp_exist_rack_layouts
  SELECT rack_layout_id
  FROM iso_request;
INSERT INTO tmp_exist_rack_layouts
  SELECT rack_layout_id
  FROM iso_control_stock_rack;

DELETE FROM rack_layout
  WHERE rack_layout_id NOT IN (
    SELECT rack_layout_id FROM tmp_exist_rack_layouts);

DROP TABLE tmp_exist_rack_layouts;

-- Add unique constraint in rack_barcoded_location to avoid duplicate checkins.
alter table rack_barcoded_location 
    add constraint rack_barcoded_location_barcoded_location_id_unique 
    unique(barcoded_location_id);
    
-- Fix member hashes for primer design pools (used a comma instead of a 
-- semicolon when creating the hashes :-S ).
update molecule_design_pool mdp
set member_hash = tmp.member_hash
from (select mdp2.molecule_design_set_id, 
             md5(string_agg(cast(mdsm.molecule_design_id as varchar), ';'
                            order by mdsm.molecule_design_id)) as member_hash
      from molecule_design_pool mdp2
        inner join molecule_design_set_member mdsm 
            on mdsm.molecule_design_set_id=mdp2.molecule_design_set_id
      group by mdp2.molecule_design_set_id
      ) as tmp
where tmp.molecule_design_set_id = mdp.molecule_design_set_id
and mdp.molecule_type='SSDNA';

-- Default stock concentrations (nM) for molecule types.
alter table molecule_type
    add column default_stock_concentration float 
    check (default_stock_concentration > 0);
update molecule_type set default_stock_concentration=50000;
update molecule_type set default_stock_concentration=10000 
    where molecule_type_id in ('MIRNA_INHI', 'MIRNA_INHI');
update molecule_type set default_stock_concentration=5000000
    where molecule_type_id = 'COMPOUND';
alter table molecule_type
    alter column default_stock_concentration set not null;
    
-- Drop the misconstrued design_type column in supplier_molecule_design; to
-- do this, we must replace the supplier_molecule_design_view.
drop view supplier_molecule_design_view;
create view supplier_molecule_design_view as
select supplier_molecule_design.supplier_molecule_design_id, 
       supplier_molecule_design.supplier_id, 
       supplier_molecule_design.product_id, 
       supplier_molecule_design.time_stamp
from supplier_molecule_design
where supplier_molecule_design.is_current;
    
alter table supplier_molecule_design
    drop column design_type;

-- Add pooled_molecule_design records for our 1 design SIRNA pools.
-- Checking assumptions: 
-- (1) For all pools with 2 designs (=primers), we already have supplier 
--     molecule design records.
select assert('(select count(*)'
              '    from molecule_design_pool mdp'
              '    where number_designs = 2'
              '    and not exists'
              '    (select smd.supplier_molecule_design_id'
              '     from molecule_design_pool mdp1'
              '     inner join pooled_supplier_molecule_design psmd'
              '         on psmd.molecule_design_set_id=mdp1.molecule_design_set_id'
              '         inner join supplier_molecule_design smd '
              '             on smd.supplier_molecule_design_id=psmd.supplier_molecule_design_id'
              '     where mdp1.molecule_design_set_id=mdp.molecule_design_set_id)) = 0');
-- (2) For for all pools with 1 design (=siRNAs) we do not have supplier
--     molecule design records.
select assert('(select count(*)'
              '    from molecule_design_pool mdp'
              '    where number_designs = 1'
              '    and not exists'
              '    (select smd.supplier_molecule_design_id'
              '     from molecule_design_pool mdp1'
              '     inner join pooled_supplier_molecule_design psmd'
              '         on psmd.molecule_design_set_id=mdp1.molecule_design_set_id'
              '         inner join supplier_molecule_design smd '
              '             on smd.supplier_molecule_design_id=psmd.supplier_molecule_design_id'
              '     where mdp1.molecule_design_set_id=mdp.molecule_design_set_id)) =' 
              '     (select count(*) from molecule_design_pool mdp2 where number_designs = 1)');
-- (3) We *really* only have 1 member in all pools where number_designs=1 
--     (a little anal perhaps).          
select assert('(select count(*) from (select count(mdsm.molecule_design_id) as count'
              ' from molecule_design_pool mdp'
              ' inner join molecule_design_set_member mdsm'
              '     on mdsm.molecule_design_set_id=mdp.molecule_design_set_id'
              ' where mdp.number_designs=1'
              ' group by mdp.molecule_design_set_id) as tmp'
              ' where tmp.count!=1) = 0');

-- Perform inserts.
insert into pooled_supplier_molecule_design
(select smd.supplier_molecule_design_id, 
        mdp.molecule_design_set_id
 from molecule_design_pool mdp 
     inner join molecule_design_set_member mdsm 
     on mdsm.molecule_design_set_id=mdp.molecule_design_set_id 
         inner join single_supplier_molecule_design ssmd 
         on ssmd.molecule_design_id=mdsm.molecule_design_id 
             inner join supplier_molecule_design smd 
             on smd.supplier_molecule_design_id=ssmd.supplier_molecule_design_id 
 where mdp.number_designs=1);


CREATE OR REPLACE VIEW db_version AS SELECT 209.0008 AS version;