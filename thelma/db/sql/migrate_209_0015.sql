-- Changes precipitated by the creation of the schema for the DTU.

SELECT assert('(select version from db_version) = 209.0014');

-- Replace the refseq gene view with a materialized view to decouple from
-- release_gene_transcript and current_db_release tables.

-- This is the new materialized view table.
create table refseq_gene (
    gene_id integer not null references gene (gene_id),
    accession varchar(32) not null unique,
    locus_name varchar (40) not null,
    species_id integer not null references species (species_id),
    constraint refseq_gene_pkey primary key (gene_id)
);

create index refseq_gene_accession_idx on refseq_gene(accession);

-- The associated trigger.
create or replace function
    refresh_table_refseq_gene() returns trigger as $$
begin
   delete from refseq_gene;
   insert into refseq_gene
   select distinct g.gene_id, g.accession, g.locus_name, g.species_id
   from gene g
   join release_gene_transcript rgt ON rgt.gene_id = g.gene_id AND rgt.species_id = g.species_id
   join current_db_release cdr ON cdr.db_release_id = rgt.db_release_id
   join db_source ds ON ds.db_source_id = cdr.db_source_id
   where ds.db_name::text = 'RefSeq'::text;
   return null;
end 
$$ language 'plpgsql';

create trigger refresh_table_refseq_gene after update on current_db_release for each statement execute procedure refresh_table_refseq_gene();
comment on trigger refresh_table_refseq_gene on current_db_release is 'A trigger to update the refseq_gene materialized view on update operations on the current_db_release table.';

-- Now, populate the table.
insert into refseq_gene
  select distinct g.gene_id, g.accession, g.locus_name, g.species_id
  from gene g
  join release_gene_transcript rgt ON rgt.gene_id = g.gene_id AND rgt.species_id = g.species_id
  join current_db_release cdr ON cdr.db_release_id = rgt.db_release_id
  join db_source ds ON ds.db_source_id = cdr.db_source_id
  where ds.db_name::text = 'RefSeq'::text;


-- The sense strand information for the supplier molecule design is now kept in the
-- supplier_structure_annotation table.
alter table supplier_molecule_design
    drop column sense_strand;
  
    
-- One more timezone-aware timestamp (cf. migration script 209.0007).
alter table molecule 
    alter column insert_date type timestamp with time zone using timestamp at time zone 'utc';

  
CREATE OR REPLACE VIEW db_version AS SELECT 209.0015 AS version;