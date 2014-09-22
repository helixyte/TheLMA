-- Reconciliation of differences between SQLAlchemy metadata and actual DB 
-- structure as detected by alembic.

SELECT assert('(select version from db_version) = 17.5');

-- Adding and renaming unique constraints with new unified naming scheme or
-- dropping spurious unique constraints for primary keys.
alter table barcoded_location 
    add constraint uq_barcoded_location_barcode unique(barcode);
alter table containment drop constraint "containment_held_id_key";
alter table containment 
    rename constraint "containment_holder_id_key" 
    to "uq_containment_holder_id_row_col";
alter table db_user 
    rename constraint "db_user_login_key" to "uq_db_user_login";
alter table db_user
    add constraint uq_db_user_username unique(username);
alter table db_user
    add constraint uq_db_user_email_addr unique(email_addr);
alter table db_user
    add constraint uq_directory_user_id unique(directory_user_id);
alter table molecule_design
    rename constraint "structure_hash_unique" 
    to "uq_molecule_design_structure_hash";
alter table molecule_design_pool
    rename constraint "unique_molecule_design_pool_member_hash" 
    to "uq_molecule_design_pool_member_hash";
alter table molecule_design_pool_set_member 
    drop constraint "unique_pool_per_molecule_design_pool_set";
alter table molecule_design_set_member 
    drop constraint "unique_molecule_design_per_molecule_design_set";
alter table molecule_design_structure 
    drop constraint "molecule_design_structure_molecule_design_id_chemical_struc_key";
alter table molecule_design_structure
    add constraint "molecule_design_structure_pkey" 
    primary key (molecule_design_id, chemical_structure_id);
alter table organization
    rename constraint "organization_name_key" 
    to "uq_organization_name";
alter table rack
    add constraint uq_rack_barcode unique(barcode);
alter table rack_barcoded_location
    drop constraint "rack_barcoded_location_barcoded_location_id_unique";
alter table rack_position
    rename constraint "unique_rack_position_indices" 
    to "uq_rack_position_row_index_column_index";
alter table rack_position
    rename constraint "unique_rack_position_label" 
    to "uq_rack_position_label";
alter table rack_position_set
    drop constraint "unique_rack_position_set_hash_value";
alter table rack_shape drop constraint "rack_shape_name_key" cascade;
alter table experiment_design 
    add constraint "experiment_design_rack_shape_name_fkey"
    foreign key (rack_shape_name) references rack_shape(rack_shape_name);
alter table experimental_content
    add constraint "experimental_content_rack_shape_name_fkey"
    foreign key (rack_shape_name) references rack_shape(rack_shape_name);
alter table experimental_design
    add constraint "experimental_design_rack_shape_name_fkey"
    foreign key (rack_shape_name) references rack_shape(rack_shape_name);
alter table rack_layout
    add constraint "rack_layout_rack_shape_name_fkey"
    foreign key (rack_shape_name) references rack_shape(rack_shape_name);
alter table rack_specs
    add constraint "rack_specs_rack_shape_name_fkey"
    foreign key (rack_shape_name) references rack_shape(rack_shape_name);
alter table reservoir_specs
    add constraint "reservoir_specs_rack_shape_name_fkey"
    foreign key (rack_shape_name) references rack_shape(rack_shape_name);
alter table refseq_gene drop constraint "refseq_gene_accession_key";
alter table sample drop constraint "sample_container_id_key";
alter table subproject
    rename constraint "project_pass_project_id_key" 
    to "uq_subproject_project_id_label";
alter table tag_domain
    rename constraint "tag_domain_domain_key" 
    to "uq_tag_domain_domain";
alter table tag_predicate
    rename constraint "tag_predicate_predicate_key" 
    to "uq_tag_predicate_predicate";
alter table tag_value
    rename constraint "tag_value_value_key" 
    to "uq_tag_value_value";
alter table worklist_series_experiment_design
    rename constraint "unique_worklist_series_experiment_design" 
    to "uq_worklist_series_experiment_design_experiment_design_id";
alter table worklist_series_experiment_design_rack
    rename constraint "unique_worklist_series_experiment_design_rack" 
    to "uq_worklist_series_experiment_design_rack_experiment_design_rack_id";
alter table worklist_series_iso_request
    rename constraint "unique_worlist_series_iso_request_id" 
    to "uq_worlist_series_iso_request_iso_request_id";
alter table worklist_series_member
    rename constraint "unique_planned_worklist" 
    to "uq_worlist_series_member_planned_worklist_id";

-- Unifying index names.
alter index "containment_holder_id_index"
    rename to "ix_containment_holder_id";
alter index "molecule_molecule_design_id_idx" 
    rename to "ix_molecule_molecule_design_id";
alter index "molecule_design_molecule_type_idx"
    rename to "ix_molecule_design_molecule_type";
alter index "molecule_design_set_gene_molecule_design_set_idx"
    rename to "ix_molecule_design_set_gene_molecule_design_set_id";
alter index "molecule_design_set_gene_gene_idx"
    rename to "ix_molecule_design_set_gene_gene_id";
alter index "molecule_design_set_member_molecule_design_id_idx"
    rename to "ix_molecule_design_set_member_molecule_design_id";
alter index "molecule_design_structure_chemical_structure_id_idx"
    rename to "ix_molecule_design_structure_chemical_structure_id";
alter index "molecule_design_structure_molecule_design_id_idx"
    rename to "ix_molecule_design_structure_molecule_design_id";
alter index "pooled_supplier_molecule_design_molecule_design_set_id_idx"
    rename to "ix_pooled_supplier_molecule_design_molecule_design_set_id";
alter index "rack_barcode_idx"
    rename to "ix_rack_barcode";
drop index "rack_barcoded_location_barcoded_location_id_idx";
drop index "rack_barcoded_location_rack_id_idx";
create unique index "ix_rack_barcoded_location_barcoded_location_id" 
    on rack_barcoded_location(barcoded_location_id);
drop index "rack_position_set_hash_value_idx";
create unique index "ix_rack_position_set_hash_value" 
    on rack_position_set(hash_value);
drop index "stock_sample_molecule_design_set_member_hash_idx";
drop index "refseq_gene_accession_idx";
create unique index "ix_refseq_gene_accession" 
    on refseq_gene(accession);
create index "ix_refseq_gene_locus_name"
    on refseq_gene(locus_name);
alter index "sample_container_idx"
    rename to "ix_sample_container_id";
alter index "sample_molecule_molecule_id_idx"
    rename to "ix_sample_molecule_molecule_id";
alter index "sample_molecule_sample_id_idx"
    rename to "ix_sample_molecule_sample_id";
alter index "single_supplier_molecule_design_molecule_design_id_idx"
    rename to "ix_single_supplier_molecule_design_molecule_design_id";
alter index "stock_sample_molecule_type_id_idx"
    rename to "ix_stock_sample_molecule_type";
    
    
-- Misc. other changes.
alter table experiment_metadata 
    alter column creation_date set default now();    
alter table planned_liquid_transfer 
    alter column transfer_type set not null;
alter table rack_barcoded_location
    rename constraint "$2" 
    to "barcoded_location_barcoded_location_id_fkey";
alter table tagged_rack_position_set 
    alter column rack_position_set_id set not null;

-- The refseq_gene table is just a materialized view the purpose of which is
-- to decouple the genes relevant for the LIMS from the larger gene table.
-- The foreign key constraint is hurting this purpose as it requires the 
-- gene table to be present.
alter table refseq_gene 
    drop constraint "refseq_gene_gene_id_fkey";

    
-- Dropping the old experimental_* tables.
drop table experimental_design_rack_treatment_rack_position_block;
drop table experimental_design_rack_treatment;
drop table experimental_design_rack;
drop table experimental_content_type_rack_position_block ;
drop table experimental_content_label;
drop table experimental_design_rack_treatment;
drop table experimental_design_factor_level;
drop table experimental_design_factor;
drop table experimental_design_assay ;
drop table experimental_content_type ;
drop table acquisition_site;
drop table acquisition;
drop table experiment_rack_job;
drop table experiment_rack;
drop table experiment;
drop table experimental_content;
drop table experimental_design;
    
alter sequence "executed_transfer_executed_transfer_id_seq"
    rename to "executed_liquid_transfer_executed_liquid_transfer_id_seq";
alter sequence "internal_sample_order_internal_sample_order_id_seq"
    rename to "iso_iso_id_seq";
alter sequence "sample_order_plan_sample_order_plan_id_seq"
    rename to "iso_request_iso_request_id_seq";
alter sequence "pool_set_pool_set_id_seq"
    rename to "molecule_design_pool_set_molecule_design_pool_set_id_seq";
alter sequence "rack_position_rack_position_id_seq1"
    rename to "rack_position_rack_position_id_seq";
alter sequence "tag_namespace_tag_namespace_id_seq"
    rename to "tag_domain_tag_domain_id_seq";
CREATE OR REPLACE VIEW db_version AS SELECT 19.1 AS version;