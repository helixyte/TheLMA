-- Cleanup after reorganization of molecule designs.

select assert('(select version from db_version) = 209.00021');

--Accelerate lookup of molecule design set members.
create index molecule_design_set_member_molecule_design_id_idx
    on molecule_design_set_member(molecule_design_id);

--With the duplicates removed, we can now create a unique index which 
--ensures that we do not create duplicate design sets (sharing the same
--members) and accelerates lookup of member hash values.
create unique index stock_sample_molecule_design_set_member_hash_idx
    on stock_sample_molecule_design_set(member_hash);

--The stock_sample_molecule_design_set table also needs the molecule_type
--so that we can report the molecule type for design sets we do not have in 
--stock without having to pull up the first design in the set.
alter table stock_sample_molecule_design_set
    add column molecule_type varchar
    references molecule_type(molecule_type_id);

--Make sure we only have *one* molecule type per design set.
select assert('(select distinct count(tmp.molecule_design_set_id) '
              ' from (select mdsm.molecule_design_set_id'
              '       from molecule_design_set_member mdsm'
              '           inner join molecule_design md'
              '               on md.molecule_design_id=mdsm.molecule_design_id'
              '       group by mdsm.molecule_design_set_id,md.molecule_type)'
              ' as tmp group by tmp.molecule_design_set_id) = 1');
--Perform the update.
update stock_sample_molecule_design_set ssmds
    set molecule_type=tmp.molecule_type
    from (select mdsm.molecule_design_set_id, md.molecule_type
          from molecule_design_set_member mdsm
          inner join molecule_design md 
            on md.molecule_design_id=mdsm.molecule_design_id
            group by mdsm.molecule_design_set_id,md.molecule_type
          ) as tmp
    where tmp.molecule_design_set_id = ssmds.molecule_design_set_id;
--Set the not null constraint.
alter table stock_sample_molecule_design_set
    alter column molecule_type set not null;

--Now we can replace the stock info view (which relies on the molecule_type
--being available in the stock_sample_molecule_design_set table).
    
drop view stock_info_view;
create view stock_info_view as
select (('ssmds'::text || ssmds.molecule_design_set_id) || 'c'::text) || 
        coalesce(ss.concentration * 1e6::double precision, 
                 0::double precision) as stock_info_id, 
        ssmds.molecule_design_set_id, 
        ssmds.molecule_type as molecule_type_id, 
        coalesce(ss.concentration, 0::double precision) as concentration, 
        coalesce(count(c.container_id), 0::bigint) as total_tubes, 
        coalesce(sum(s.volume), 0::double precision) as total_volume, 
        coalesce(min(s.volume), 0::double precision) as minimum_volume, 
        coalesce(max(s.volume), 0::double precision) as maximum_volume
    from stock_sample_molecule_design_set ssmds
    left join stock_sample ss
        on ss.molecule_design_set_id = ssmds.molecule_design_set_id
        left join sample s 
            on s.sample_id = ss.sample_id
            left join container c 
                on c.container_id = s.container_id
                where c.item_status='MANAGED'
    group by ssmds.molecule_design_set_id, ss.concentration, ss.molecule_type_id;        

--The new molecule_design_set_gene view.
create view molecule_design_set_gene_view as
select distinct ssmds.molecule_design_set_id, mdg.gene_id 
    from stock_sample_molecule_design_set ssmds
        inner join molecule_design_set_member mdsm
            on mdsm.molecule_design_set_id = ssmds.molecule_design_set_id
            inner join molecule_design_gene mdg
                on mdg.molecule_design_id = mdsm.molecule_design_id;

create table molecule_design_set_gene
(
    molecule_design_set_id integer not null
        references stock_sample_molecule_design_set(molecule_design_set_id),
    gene_id integer not null
        references gene(gene_id),
    primary key (molecule_design_set_id, gene_id)
   
);

create index molecule_design_set_gene_molecule_design_set_idx
    on molecule_design_set_gene(molecule_design_set_id);

create index molecule_design_set_gene_gene_idx
    on molecule_design_set_gene(gene_id);

comment on table molecule_design_set_gene is
    'Materialized view for molecule design set gene targets.';

create or replace function
    refresh_table_molecule_design_gene() returns trigger as $$
begin
	delete from molecule_design_gene;
	delete from molecule_design_set_gene;
	insert into molecule_design_gene select * from molecule_design_gene_view;
	insert into molecule_design_set_gene select * from molecule_design_set_gene_view;
	return null;
end 
$$ language 'plpgsql';

--Accelerate lookup of stock_samples by molecule_type_id
create index stock_sample_molecule_type_id_idx
    on stock_sample(molecule_type_id);
    
--Rename stock_sample.molecule_type_id to molecule_type for consistency.
alter table stock_sample
    rename column molecule_type_id to molecule_type;
    
--Create new stock sample molecule design sets for all designs that we 
--currently do not have in stock.
select md.molecule_design_id,
       md.molecule_type,
       nextval('molecule_design_set_molecule_design_set_id_seq')
            as molecule_design_set_id
    into tmp_designs_not_in_stock
    from molecule_design md
    where md.molecule_type in 
            (select distinct molecule_type from stock_sample)
        and not exists
        (select ssmds.molecule_design_set_id 
            from stock_sample_molecule_design_set ssmds
            inner join molecule_design_set_member mdsm
                on mdsm.molecule_design_set_id = ssmds.molecule_design_set_id
                where mdsm.molecule_design_id=md.molecule_design_id);

insert into molecule_design_set
    select molecule_design_set_id,
           'STOCK_SAMPLE' as set_type
    from tmp_designs_not_in_stock;

insert into stock_sample_molecule_design_set
    select molecule_design_set_id,
           md5(cast(molecule_design_id as text)) as member_hash,
           1 as number_designs,
           molecule_type
    from tmp_designs_not_in_stock;
    
insert into molecule_design_set_member
    select molecule_design_set_id,
           molecule_design_id
    from tmp_designs_not_in_stock;

drop table tmp_designs_not_in_stock;

--Rebuild molecule and molecule set gene materialized views.
delete from molecule_design_gene;
delete from molecule_design_set_gene;
insert into molecule_design_gene select * from molecule_design_gene_view;
insert into molecule_design_set_gene select * from molecule_design_set_gene_view;

create or replace view db_version as select 209.0002 as version;