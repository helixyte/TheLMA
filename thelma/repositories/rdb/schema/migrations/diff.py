"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Inspect differences between the entity domain model and the current DB schema.
"""
import pprint

from alembic.autogenerate import compare_metadata
from alembic.environment import EnvironmentContext
from alembic.script import ScriptDirectory

from thelma.repositories.rdb import initialize_schema
from thelma.repositories.rdb.schema.migrations.util import create_engine
from thelma.repositories.rdb.schema.migrations.util import parse_config


__docformat__ = 'reStructuredText en'
__all__ = []


alembic_cfg = parse_config()
# Parse settings.
metadata = initialize_schema()


IGNORE_OPS = dict(remove_table=set([
                    # bioinformatics tables
                    'annotation',
                    'annotation_accession',
                    'annotation_relationship',
                    'annotation_type',
                    'chromosome',
                    'chromosome_gene_feature',
                    'chromosome_transcript_feature',
                    'current_db_release',
                    'db_release',
                    'db_source',
                    'double_stranded_intended_target',
                    'evidence',
                    'gene',
                    'gene2annotation',
                    'gene_identifier',
                    'intended_mirna_target',
                    'intended_target',
                    'legacy_primer_pair',
                    'mirna',
                    'molecule_design_mirna_target',
                    'molecule_design_versioned_transcript_target',
                    'primer_pair',
                    'primer_validation',
                    'refseq_update_species',
                    'release_gene',
                    'release_gene2annotation',
                    'release_gene_transcript',
                    'release_versioned_transcript',
                    'replaced_gene',
                    'replaced_transcript',
                    'seq_identifier_type',
                    'target',
                    'transcript',
                    'transcript_identifier',
                    'transcript_gene',
                    'versioned_transcript',
                    'versioned_transcript_amplicon',
                    # legacy tables
                    'acquisition',
                    'acquisition_site',
                    'acquisition_task_item',
                    'cell_line',
                    'db_group',
                    'db_group_users',
                    'dilution_job_step',
                    'experiment',
                    'experimental_content',
                    'experimental_content_label',
                    'experimental_content_type',
                    'experimental_content_type_rack_position_block',
                    'experimental_design',
                    'experimental_design_assay',
                    'experimental_design_factor',
                    'experimental_design_factor_level',
                    'experimental_design_rack',
                    'experimental_design_rack_treatment',
                    'experimental_design_rack_treatment_rack_position_block',
                    'experiment_metadata_molecule_design_set',
                    'experiment_metadata_target_set',
                    'experiment_rack',
                    'external_primer_carrier',
                    'file',
                    'file_set',
                    'file_set_files',
                    'file_type',
                    'image_analysis_task_item',
                    'iso_molecule_design_set',
                    'iso_racks',
                    'job',
                    'job_step',
                    'job_type',
                    'file_storage_site',
                    'molecule_design_set_target_set',
                    'printer',
                    'order_sample_set',
                    'rack_barcoded_location_log',
                    'rack_mask',
                    'rack_mask_position',
                    'rack_position_block',
                    'readout_task_item',
                    'readout_type',
                    'rearrayed_containers',
                    'rnai_experiment',
                    'sample_cells',
                    'sample_set',
                    'sample_set_sample',
                    'sample_set_type',
                    'sequence_feature',
                    'status_type',
                    'supplier_barcode',
                    'target',
                    'target_set',
                    'target_set_member',
                    'task',
                    'task_item',
                    'task_report',
                    'task_type',
                    'transfection_job_step',
                    # unmapped tables
                    'liquid_type',
                    'transfer_type',
                    '_user_messages',
                    ]),
                  remove_index=set([
                    'stock_container_idx',
                    'ix_rack_barcode', # not detected properly.
                    'project_pass_file_storage_site_id_key',
                    ]),
                  add_index=set([
                    'stock_container_idx',
                    'ix_rack_barcode', # not detected properly.
                    ]),
                  add_constraint=set([]),
                  remove_constraint=set([
                    'project_pass_file_storage_site_id_key'
                    ]),
                  modify_nullable=set([
                    'rack.barcode',
                    ]),
                  remove_column=set(
                    ['subproject.file_storage_site_id'
                     ]),
                  )


def include_op(op_):
    #: Filter function for migration operations detected by the
    #: compare_metadata function.
    if isinstance(op_, tuple):
        op_name = op_[0]
        if op_name.endswith('_table'):
            op_obj = op_[1]
            op_obj_name = op_obj.name
        elif op_name.endswith('_column'):
            op_obj = op_[3]
            op_obj_name = op_[2] + '.' + op_obj.name
        else:
            op_obj = op_[1]
            op_obj_name = op_obj.name
            if op_obj_name is None:
                op_obj_name = op_obj.table.name + '.' \
                                + '_'.join(c.name for c in op_obj.columns)
    else:
        op_name = op_[0][0]
        op_obj_name = op_[0][2] + '.' + op_[0][3]
    return not op_obj_name in IGNORE_OPS.get(op_name, [])

# Set up a migration context.
alembic_cfg.set_main_option('script_location', 'thelma:db/schema/migrations')
script = ScriptDirectory.from_config(alembic_cfg)
env_ctxt = EnvironmentContext(alembic_cfg, script)
engine = create_engine(alembic_cfg)
env_ctxt.configure(engine.connect()) # , include_object=include_object)
mig_ctxt = env_ctxt.get_context()

ops = compare_metadata(mig_ctxt, metadata)
diff = [op for op in ops if include_op(op)]
pprint.pprint(diff, indent=2, width=20)
