from thelma.db.schema.views import doublestrandeddesign
from thelma.db.schema.views import moleculedesigngene
from thelma.db.schema.views import moleculedesignsetgene
from thelma.db.schema.views import moleculetypemodification
from thelma.db.schema.views import refseqgene
from thelma.db.schema.views import singlestrandeddesign
from thelma.db.schema.views import stockinfo
from thelma.db.schema.views import suppliermoleculedesign


def initialize_views(metadata, tables):
    moleculedesigngene.create_view(
        metadata,
        tables['molecule_design'],
        tables['gene'],
        tables['release_gene_transcript'],
        tables['versioned_transcript'],
        tables['release_versioned_transcript'],
        tables['current_db_release'],
        tables['molecule_design_versioned_transcript_target']
        )
    refseqgene.create_view(
        metadata,
        tables['gene'],
        tables['release_gene_transcript'],
        tables['current_db_release'],
        tables['db_source'])
    moleculedesignsetgene.create_view(
        metadata,
        tables['molecule_design_pool'],
        tables['molecule_design_set_member'],
        tables['molecule_design_gene'])
    stockinfo.create_view(
        metadata,
        tables['molecule_design_pool'],
        tables['stock_sample'],
        tables['sample'],
        tables['container'],
        )
    singlestrandeddesign.create_view(
        metadata,
        tables['molecule_design'],
        tables['single_stranded_design']
        )
    doublestrandeddesign.create_view(
        metadata,
        tables['molecule_design'],
        tables['double_stranded_design']
        )
    moleculetypemodification.create_view(
        metadata,
        tables['molecule_design'],
        tables['molecule_design_structure'],
        tables['chemical_structure'],
        )
    suppliermoleculedesign.create_view(
        metadata,
        tables['supplier_molecule_design'])
