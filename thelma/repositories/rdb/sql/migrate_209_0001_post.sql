-- Cleanup after reorganization of molecule designs.

select assert('(select version from db_version) = 209.00011');

drop view molecule_design_info_view;

drop table mirna_inhibitor_design;
drop table mirna_inhibitor_modification;
drop table mirna_mimic_design;
drop table compound;

drop view single_stranded_design_view;
drop table single_stranded_design;
drop table single_stranded_modification;

alter table double_stranded_intended_target
    drop constraint molecule_design_id;
alter table double_stranded_intended_target
    add constraint molecule_design_id 
        foreign key (molecule_design_id)
        references molecule_design(molecule_design_id);
drop view double_stranded_design_view;
drop table double_stranded_design;
drop table double_stranded_modification;

create or replace view db_version as select 209.0001 as version;