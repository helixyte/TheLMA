select assert('(select version from db_version) = 209.0001');

--Delete the subproject molecule infrastructure.
drop view subproject_molecule_with_status;
drop view subproject_available_molecule;
drop view subproject_rearrayed_molecule;
drop table subproject_molecule_designs_and_targets;
drop table subproject_finalized_molecule;
drop table subproject_gene_transcript;
drop table subproject_gene;
drop table subproject_molecule_transcript_target;
drop table subproject_transcript;
drop table subproject_molecule;


--Throw out old Long dsRNA (fly) production data.
--The following tables were all exclusively used during the production of 
-- Long dsRNAs (involving molecule types SSRNA, SSDNA, AMPLICON, LONG_DSRNA).
drop view oligo_molecule_productions;
drop table external_order_queue;
drop table long_dsrna_production;
drop table dsrna_production;
drop table production_container;
drop table molecule_molecule_production;
drop table molecule_production_queue;
drop table transcribed_dsrna;
drop table annealing_reaction_ssrna;
drop table chromosome_amplicon;
drop table ssrna;
drop table transcription_template;
drop table transcribable_ssdna;
drop table dsdna;
drop table annealing_reaction;
drop table pcr_reaction_oligo;
drop table pcr_reaction_template_chromosome;
drop table predicted_amplicon_transcript_target;
drop table predicted_pcr_chromosome_amplicon;
drop table pcr_reaction;
drop table transcription_reaction;
drop table rna_polymerase;
drop table predicted_gel_band;
drop table observed_gel_band;
drop table reaction_queue;
drop table reaction_type_molecule_type;
drop table reaction_type;

select sample_set_id
    into tmp_rna_prod_sample_set
    from rna_production_sample_set;
drop table rna_production_sample_set;
delete from sample_set_sample 
    where sample_set_id in
        (select sample_set_id from tmp_rna_prod_sample_set);
delete from sample_set 
    where sample_set_id in 
        (select sample_set_id from tmp_rna_prod_sample_set);
drop table tmp_rna_prod_sample_set;

delete from molecule where molecule_id in 
    (select m.molecule_id from molecule m 
        inner join molecule_design md 
        on md.molecule_design_id=m.molecule_design_id 
        where md.molecule_type='SSRNA');
delete from molecule_design where molecule_type = 'SSRNA';
delete from molecule_type where molecule_type_id = 'SSRNA';

--Deleting the SSDNA samples, sample_molecules, molecules and molecule designs
--used for the fly library production. We define the fly SSDNA designs as 
--all SSDNA designs that are not part of a primer design.
--FIXME: We need proper cascading rules here.
select md.molecule_design_id
    into tmp_fly_ssdna_designs
    from molecule_design md
    left join primer_pair pp1 on pp1.primer_1_id=md.molecule_design_id 
    left join primer_pair pp2 on pp2.primer_2_id=md.molecule_design_id 
    where molecule_type='SSDNA' 
    and (pp1.primer_1_id is null and pp2.primer_2_id is null);

select m.molecule_id, sm.sample_id
    into tmp_fly_ssdnas
    from molecule m
        left join sample_molecule sm on sm.molecule_id=m.molecule_id
    where m.molecule_design_id in 
        (select molecule_design_id from tmp_fly_ssdna_designs);
    
delete from sample_molecule
    where molecule_id in 
        (select molecule_id from tmp_fly_ssdnas);

delete from molecule
    where molecule_id in 
        (select molecule_id from tmp_fly_ssdnas);
         
--FIXME: We should also delete the sample_sets here. However, because the
--samples were involved in rearraying jobs, there are references to the sample
--sets from rearrayed_containers and task_item which shold be cleaned up
--some other time.
delete from sample_set_sample
    where sample_id in (select sample_id from tmp_fly_ssdnas
                            where not sample_id is null);

delete from sample 
    where sample_id in (select sample_id from tmp_fly_ssdnas
                            where not sample_id is null); 
    
delete from  molecule_design_structure
    where molecule_design_id in 
        (select molecule_design_id from tmp_fly_ssdna_designs);

delete from molecule_design 
    where molecule_design_id in 
        (select molecule_design_id from tmp_fly_ssdna_designs);
        
drop table tmp_fly_ssdnas;
drop table tmp_fly_ssdna_designs;

--This does not contain anything and is not used anywhere.
drop table molecule_mapping_registry;

--Throw out old GOLD and TITAN molecule designs and molecule types (making
--sure we do not have any molecules with designs of those types). 
select assert('(select count(*) from molecule m '
              ' inner join molecule_design md '
              ' on md.molecule_design_id = m.molecule_design_id '
              ' where md.molecule_type=''TITAN'') = 0');
select assert('(select count(*) from molecule m '
              ' inner join molecule_design md '
              ' on md.molecule_design_id = m.molecule_design_id '
              ' where md.molecule_type=''GOLD'') = 0');
delete from molecule_design where molecule_type = 'TITAN';
delete from molecule_design where molecule_type = 'GOLD';
delete from molecule_type where molecule_type_id = 'TITAN';
delete from molecule_type where molecule_type_id = 'GOLD';

-- Transfer the primer pairs into the new structure.
-- For the primer pools, we create new supplier molecule designs using
-- Metabion as supplier.
-- We need to use a temporary table as intermediate step.
select
    nextval('supplier_molecule_design_supplier_molecule_design_id_seq') 
        as supplier_molecule_design_id,
     nextval('molecule_design_set_molecule_design_set_id_seq')
        as molecule_design_set_id,
    (select organization_id from organization where name='Metabion') as supplier_id,
    cast(primer_pair_id as text)  as product_id,
    cast('POOL' as text) as design_type,
    primer_1_id,
    primer_2_id
     into tmp_primer_supplier_molecule_design
    from primer_pair;

insert into molecule_design_set
    select molecule_design_set_id,
           'STOCK_SAMPLE' as set_type
    from tmp_primer_supplier_molecule_design;
           
insert into molecule_design_set_member
    select molecule_design_set_id,
           primer_1_id as molecule_design_id
    from tmp_primer_supplier_molecule_design;
           
insert into molecule_design_set_member
    select molecule_design_set_id,
           primer_2_id as molecule_design_id
    from tmp_primer_supplier_molecule_design;
    
insert into stock_sample_molecule_design_set
    select molecule_design_set_id,
           md5(cast(primer_1_id as text) || ',' || cast(primer_2_id as text)) as member_hash,
           2 as number_designs
    from tmp_primer_supplier_molecule_design;

insert into supplier_molecule_design
    select supplier_id,
           product_id,
           'unknown',
           now() as time_stamp,
           true as is_current,
           false as is_deleted,
           supplier_molecule_design_id,
           design_type
    from tmp_primer_supplier_molecule_design;

insert into pooled_supplier_molecule_design
    select supplier_molecule_design_id,
           molecule_design_set_id
    from tmp_primer_supplier_molecule_design;
           
drop table tmp_primer_supplier_molecule_design;


-- Populate the stock_sample table from the samples held by all existing
-- MATRIX tubes.

-- First, create a temporary table holding all necessary data.
-- Primer samples require special treatment as we do not need to create
-- molecule design sets for them.
-- Note: This approach creates a lot of duplicate molecule design sets which 
-- we address later.
select distinct on (sample_id)
    s.sample_id,
    m.molecule_design_id,
    case when (md.molecule_type = 'SSDNA' and mdsm.molecule_design_set_id is not null)
        then mdsm.molecule_design_set_id
        when (md.molecule_type != 'SSDNA')
        then -1
        else null
    end as molecule_design_set_id,
    sm.concentration,
    md.molecule_type as molecule_type_id,
    m.supplier_id
    into tmp_stock_sample
    from (select container_id
             from container c
                 where 
                    c.item_status != 'DESTROYED'
                    and
                    (
                    c.container_specs_id = (select container_specs_id
                                            from container_specs
                                            where name = 'MATRIX0500'
                                           )
                    or
                    c.container_specs_id = (select container_specs_id
                                            from container_specs
                                            where name = 'MATRIX1400'
                                            )
                    )
                ) cts 
        inner join sample s 
	       on s.container_id = cts.container_id
	           inner join sample_molecule sm 
	               on sm.sample_id = s.sample_id 
	               inner join molecule m 
	                    on m.molecule_id = sm.molecule_id
	                    inner join molecule_design md
	                       on md.molecule_design_id = m.molecule_design_id
	                       left outer join molecule_design_set_member mdsm
	                           on mdsm.molecule_design_id = md.molecule_design_id;

select assert('(select count(*) from tmp_stock_sample where molecule_design_set_id is null) = 0');

update tmp_stock_sample 
    set molecule_design_set_id = nextval('molecule_design_set_molecule_design_set_id_seq') 
    where molecule_design_set_id=-1;

-- Create new molecule design sets and their members for all non-primer stock 
-- samples.
insert into molecule_design_set
    select molecule_design_set_id,
           'STOCK_SAMPLE' as set_type
    from tmp_stock_sample
    where molecule_type_id != 'SSDNA';
    
insert into stock_sample_molecule_design_set
    select molecule_design_set_id,
           md5(cast(molecule_design_id as text)) as member_hash,
           1 as number_designs
    from tmp_stock_sample
    where molecule_type_id != 'SSDNA';

insert into molecule_design_set_member
    select molecule_design_set_id,
           molecule_design_id
    from tmp_stock_sample
    where molecule_type_id != 'SSDNA';
            
-- Copy over the stock sample data from the temporary table.
insert into stock_sample
    select sample_id,
           molecule_design_set_id,
           supplier_id,
           molecule_type_id,
           concentration
    from tmp_stock_sample;

-- Drop the temporary table.
drop table tmp_stock_sample;


-- Update sample type for the new stock samples.
update sample
    set sample_type = 'STOCK'
    where sample_id in (select sample_id from stock_sample);


-- Create a hash for quick lookup of molecule designs given its chemical
-- structures.

-- First, we have to make sure we have structure records for *all* designs,
-- even for those for which we do not actually have structure information.
-- This is preferable to allowing NULL values in the new structure_hash field;
-- also, clients can always rely on the presence of unique structure
-- information for each molecule_design. The following statements build
-- representation strings for all designs without structure information
-- (MIRNA_MIMI, a few CLND_DSDNA) plus all designs that only have (ambiguous)
-- modification information (MIRNA_INHI) and insert the appropriate records
-- into the chemical_structure and molecule_design_structure tables.
select new_structs.*
    into tmp_new_structs
    from (select o.name || '-' || smd.product_id as representation, 
          md.molecule_design_id
          from molecule_design md
          inner join single_supplier_molecule_design ssmd
              on ssmd.molecule_design_id = md.molecule_design_id
              inner join supplier_molecule_design smd
                  on smd.supplier_molecule_design_id = ssmd.supplier_molecule_design_id
                  inner join organization o
                      on o.organization_id = smd.supplier_id
          where (not exists (select * from molecule_design_structure mds
                              where mds.molecule_design_id=md.molecule_design_id))
                 or md.molecule_type = 'MIRNA_INHI')
          as new_structs;
    
insert into chemical_structure
    select nextval('chemical_structure_chemical_structure_id_seq'),
           'UNKNOWN',
           representation
    from tmp_new_structs;

insert into molecule_design_structure
    select tmp.molecule_design_id, cs.chemical_structure_id
    from tmp_new_structs tmp
        inner join chemical_structure cs 
            on cs.representation = tmp.representation;

-- Now, create the structure_hash column and populate it with appropriate
-- hash values. These are built from all available chemical structure records
-- for a design as '|' <structure type> '|' <representation> '|', concatenated
-- with the '|' character.
alter table molecule_design
    add column structure_hash varchar;
    
select designs.molecule_design_id,
       md5(string_agg(
              designs.structure_type || '|' || designs.representation, '||'
              order by (designs.structure_type, designs.representation))) 
           as structure_hash,
       string_agg(
              designs.structure_type || '|' || designs.representation, '||'
              order by (designs.structure_type, designs.representation))
           as structure_hash_string
    into tmp_molecule_design_structure_hashes 
    from (select md.molecule_design_id, cs.chemical_structure_id,
                 cs.structure_type, cs.representation
            from molecule_design md 
		        inner join molecule_design_structure mds 
		            on mds.molecule_design_id=md.molecule_design_id 
		            inner join chemical_structure cs 
		                on cs.chemical_structure_id = mds.chemical_structure_id 
          order by md.molecule_design_id) as designs
    group by designs.molecule_design_id;
    
update molecule_design md
    set structure_hash=tmp.structure_hash
    from (select molecule_design_id, structure_hash 
                from tmp_molecule_design_structure_hashes) as tmp
    where tmp.molecule_design_id = md.molecule_design_id;

-- We now have unique structure hashes for all records; therefore, we can
-- add the appropriate constraints and drop the temporary tables.
alter table molecule_design
    alter column structure_hash set not null;

alter table molecule_design 
    add constraint structure_hash_unique unique(structure_hash);

drop table tmp_new_structs;

drop table tmp_molecule_design_structure_hashes;

create or replace view db_version as select 209.00021 as version;