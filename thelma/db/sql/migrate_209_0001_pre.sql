-- Reorganization of molecule design related tables.
-- Support for molecule design pools.

select assert('(select version from db_version) = 208.0067');

-- Missing data.
update job_type set xml='' where name='OTHER';
update job_type set xml='' where name='ISO_PROCESSING';

-- =====================================
-- MOLECULE DESIGN TABLES REORGANIZATION
-- =====================================

create table chemical_structure (
    chemical_structure_id serial primary key,
    structure_type varchar not null,
    representation varchar not null
);

-- Using an md5 index for fast lookup.
create unique index chemical_structure_md5_rpr 
    on chemical_structure(structure_type, md5(representation)); 

comment on table chemical_structure is 
    'Chemical structures associated with molecule designs. We currently '
    'distinguish two structure types: COMPOUND and NUCLEIC_ACID.';

create table molecule_design_structure (
    molecule_design_id integer not null
        references molecule_design(molecule_design_id)
        on update cascade on delete cascade,
    chemical_structure_id integer not null
        references chemical_structure(chemical_structure_id)
        on update cascade on delete cascade,
    unique (molecule_design_id, chemical_structure_id)
);

create index molecule_design_structure_chemical_structure_id_idx 
    on molecule_design_structure(chemical_structure_id);
create index molecule_design_structure_molecule_design_id_idx 
    on molecule_design_structure(molecule_design_id);
create index molecule_design_molecule_type_idx 
    on molecule_design(molecule_type);

comment on table molecule_design_structure is 
    'Maps molecule designs to their chemical structures.';

-- Get rid of compound primary key in supplier_molecule_design and add new
-- one based on a sequence.
alter table supplier_molecule_design
    drop constraint supplier_molecule_design_pkey;
alter table supplier_molecule_design
    rename column supplier_molecule_design_id to product_id;
create sequence supplier_molecule_design_supplier_molecule_design_id_seq;
alter table supplier_molecule_design
    add column supplier_molecule_design_id integer
        default nextval('supplier_molecule_design_supplier_molecule_design_id_seq'::regclass);
alter table supplier_molecule_design
    add constraint supplier_molecule_design_pkey
        primary key (supplier_molecule_design_id);


create table supplier_structure_annotation (
    supplier_molecule_design_id integer not null
        references supplier_molecule_design(supplier_molecule_design_id),
    chemical_structure_id integer not null
        references chemical_structure(chemical_structure_id),
    annotation varchar not null
);

comment on table supplier_structure_annotation is 
    'Holds the supplier-specific annotation of a chemical structure '
    'that belongs to a supplier molecule design (e.g., specifying the sense '
    'strand in a double-stranded design).';
   

-- This new stock info view definition directly pulls in the modification
-- through the new chemical_structure table. This does not seem to have 
-- noticeable effects on performance.
drop view stock_info_view;
create or replace view stock_info_view as
select
        (
            'md' || md.molecule_design_id ||
            'c' || COALESCE(ssi.concentration * 1000000, 0)
        ) as stock_info_id,
        md.molecule_design_id,
        md.molecule_type,
        case when chsi.representation is NULL
            then 'unmodified'
            else chsi.representation
        end as modification,
        COALESCE(ssi.concentration, 0) as concentration,
        COALESCE(ssi.total_tubes, 0) as total_tubes,
        COALESCE(ssi.total_volume, 0) as total_volume,
        COALESCE(ssi.minimum_volume, 0) as minimum_volume,
        COALESCE(ssi.maximum_volume, 0) as maximum_volume
    from
        molecule_design md 
        left join
        (
            select
                m.molecule_design_id,
                sm.concentration,
                sum(s.volume) as total_volume,
                min(s.volume) as minimum_volume,
                max(s.volume) as maximum_volume,
                count(cts.container_id) as total_tubes
            from
                (
                select container_id
                from container c
                where
                    c.item_status = 'MANAGED' 
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
                    on s.sample_id = sm.sample_id 
                    inner join molecule m 
                        on sm.molecule_id = m.molecule_id
            group by
                m.molecule_design_id,
                sm.concentration
        ) ssi on md.molecule_design_id = ssi.molecule_design_id
        left join 
        (
            select mds.molecule_design_id,
                   chs.representation
            from molecule_design_structure mds
            left join chemical_structure chs
                on chs.chemical_structure_id = mds.chemical_structure_id
            where chs.structure_type = 'MODIFICATION'
        ) chsi on chsi.molecule_design_id = ssi.molecule_design_id
;


-- The molecule modification view should be dropped in the future since
-- modifications are now modeled as an optional part of the chemical 
-- structure of a molecule design. In the meantime, we can use this
-- replacement (now called "molecule_type_modification_view").
drop view molecule_modification_view;
create or replace view molecule_type_modification_view as
select
    distinct 
        md.molecule_type as molecule_type_id,
        chs.representation as name,
        chs.chemical_structure_id 
from
    molecule_design md
    inner join molecule_design_structure mds
    on mds.molecule_design_id = md.molecule_design_id
        inner join chemical_structure chs
        on chs.chemical_structure_id = mds.chemical_structure_id
            and chs.structure_type = 'MODIFICATION'
;

-- ============
-- POOL SUPPORT
-- ============

-- Delete old pools.
-- The molecule design pool table was (ab)used for a meta study on the results
-- on a number of genome-wide screens a long time ago. The various tables 
-- created for this study have to be dropped in order to get rid of the 
-- now obsolete design pool tables.
drop table experiment_sample_cell_line;
drop table experiment_sample_treatment;
drop table sample_experiment_sample;
drop table deviation;
drop table datum;
drop table datum_type;
drop table datum_normalization;
drop table experiment_sample;
drop table treatment_type;
drop table image_object_datum;
drop table image_object;
drop table image_object_level;
drop table image_object_class;
drop table image_summary_datum;
drop table feature_relationship;
drop table feature;

-- Now drop the design pool tables. We use the more general molecule design
-- set table to model design pools.
drop table molecule_design_pool_molecule_design;
drop table molecule_design_pool;

-- Make the supplier_design_molecule table polymorphic to support "single"
-- and "pooled" designs.
alter table supplier_molecule_design
    add column design_type varchar(10) default 'SINGLE' not null;

create table single_supplier_molecule_design (
    supplier_molecule_design_id integer primary key
        references supplier_molecule_design(supplier_molecule_design_id),
    molecule_design_id integer not null
        references molecule_design(molecule_design_id)
);

create index single_supplier_molecule_design_molecule_design_id_idx
    on single_supplier_molecule_design(molecule_design_id);
    
comment on table single_supplier_molecule_design is
    'A "normal" supplier molecule design referencing a single internal '
    'molecule design.';

create table pooled_supplier_molecule_design (
    supplier_molecule_design_id integer primary key
        references supplier_molecule_design(supplier_molecule_design_id),
    molecule_design_set_id integer not null
        references molecule_design_set(molecule_design_set_id)
);

create index pooled_supplier_molecule_design_molecule_design_set_id_idx
    on pooled_supplier_molecule_design(molecule_design_set_id);
    

comment on table single_supplier_molecule_design is
    'A pooled supplier molecule design referencing one or more internal '
    'molecule designs.';

    
-- Populate the single_supplier_molecule_design table with the molecule
-- design IDs from all current supplier molecule designs and then drop
-- the molecule_design_id column. 
insert into single_supplier_molecule_design
    select supplier_molecule_design_id, 
           molecule_design_id
    from supplier_molecule_design;

-- Drop the (unused) supplier_molecule_design_view view referencing the
-- (now obsolete) molecule_design_id column in supplier_molecule_design.
drop view supplier_molecule_design_view;
    
alter table supplier_molecule_design
    drop column molecule_design_id;


-- Stock sample table.

create table stock_sample(
    sample_id integer primary key
        references sample(sample_id),
    molecule_design_set_id integer not null
        references molecule_design_set(molecule_design_set_id),
    supplier_id integer not null
        references organization(organization_id),
    molecule_type_id varchar not null
        references molecule_type(molecule_type_id),
    concentration float not null check (concentration>0.0)
);

comment on table stock_sample is
    'A stock sample is a special case of a sample which contains molecules '
    'of one or more designs of the same molecule type from the same supplier '
    'in the same concentration. The container holding a stock sample is '
    'always a 2D barcoded MATRIX tube.';


-- Make the sample table polymorphic.
alter table sample
    add column sample_type varchar(10) not null default 'BASIC';
    

-- Rename the type column in the molecule_design_set table ("type" is a 
-- reserved word in SQL).
alter table molecule_design_set 
    rename column type to set_type;

-- The label makes only sense for library design sets which we will add as
-- a polymorphic type in the future. Drop the label for now.
alter table molecule_design_set
    drop column label;
    

-- Stock sample molecule design set table.
create table stock_sample_molecule_design_set(
    molecule_design_set_id integer primary key
        references molecule_design_set(molecule_design_set_id),
    member_hash varchar not null,
    number_designs integer not null check (number_designs>0)
);


-- Fine tune supplier molecule design view.
create or replace view supplier_molecule_design_view as
select supplier_molecule_design_id,
       supplier_id,
       product_id,
       time_stamp,
       design_type
from supplier_molecule_design
where is_current;
    

-- Rename the sample_creation table.
alter table sample_creation rename to sample_registration;
alter table sample_registration
    rename column time to time_stamp;
    

create or replace view db_version as select 209.00011 as version;