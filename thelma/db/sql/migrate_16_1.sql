select assert('(select version from db_version) = 209.0016');

create or replace view stock_info_view as 
  select (('ssmds'::text || ssmds.molecule_design_set_id) || 'c'::text) || coalesce(ss.concentration * 1000000::numeric::double precision, 0::double precision) as stock_info_id, 
    ssmds.molecule_design_set_id, ssmds.molecule_type AS molecule_type_id, 
    coalesce(ss.concentration, 0::double precision) AS concentration, 
    coalesce(count(c.container_id), 0::bigint) AS total_tubes, 
    coalesce(sum(s.volume), 0::double precision) AS total_volume, 
    coalesce(min(s.volume), 0::double precision) AS minimum_volume, 
    coalesce(max(s.volume), 0::double precision) AS maximum_volume
   from molecule_design_pool ssmds
   left join stock_sample ss ON ss.molecule_design_set_id = ssmds.molecule_design_set_id
   left join sample s ON s.sample_id = ss.sample_id
   left join container c ON c.container_id = s.container_id
  where (c.item_status is null or c.item_status::text = 'MANAGED'::text)
  group by ssmds.molecule_design_set_id, ss.concentration;

create or REPLACE view db_version as select 16.1 as version;