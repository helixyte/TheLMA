from thelma.db.schema.tables import barcodedlocation
from thelma.db.schema.tables import chemicalstructure
from thelma.db.schema.tables import compound
from thelma.db.schema.tables import container
from thelma.db.schema.tables import containerbarcode
from thelma.db.schema.tables import containerspecs
from thelma.db.schema.tables import containment
from thelma.db.schema.tables import currentdbrelease
from thelma.db.schema.tables import dbrelease
from thelma.db.schema.tables import dbsource
from thelma.db.schema.tables import device
from thelma.db.schema.tables import devicetype
from thelma.db.schema.tables import doublestrandeddesign
from thelma.db.schema.tables import doublestrandedmodification
from thelma.db.schema.tables import executedcontainerdilution
from thelma.db.schema.tables import executedcontainertransfer
from thelma.db.schema.tables import executedracktransfer
from thelma.db.schema.tables import executedtransfer
from thelma.db.schema.tables import executedworklist
from thelma.db.schema.tables import executedworklistmember
from thelma.db.schema.tables import experiment
from thelma.db.schema.tables import experimentdesign
from thelma.db.schema.tables import experimentdesignrack
from thelma.db.schema.tables import experimentdesigntaggedrackpositionset
from thelma.db.schema.tables import experimentmetadata
from thelma.db.schema.tables import experimentmetadataisorequest
from thelma.db.schema.tables import experimentmetadatapoolset
from thelma.db.schema.tables import experimentmetadatatargetset
from thelma.db.schema.tables import experimentmetadatatype
from thelma.db.schema.tables import experimentrack
from thelma.db.schema.tables import experimentrackjob
from thelma.db.schema.tables import experimentsourcerack
from thelma.db.schema.tables import gene
from thelma.db.schema.tables import iso
from thelma.db.schema.tables import isoaliquotplate
from thelma.db.schema.tables import isocontrolstockrack
from thelma.db.schema.tables import isojob
from thelma.db.schema.tables import isojobmember
from thelma.db.schema.tables import isopoolset
from thelma.db.schema.tables import isopreparationplate
from thelma.db.schema.tables import isorequest
from thelma.db.schema.tables import isosamplestockrack
from thelma.db.schema.tables import itemstatus
from thelma.db.schema.tables import job
from thelma.db.schema.tables import jobtype
from thelma.db.schema.tables import librarycreationiso
from thelma.db.schema.tables import librarysourceplate
from thelma.db.schema.tables import mirna
from thelma.db.schema.tables import mirnainhibitordesign
from thelma.db.schema.tables import mirnainhibitormodification
from thelma.db.schema.tables import mirnamimicdesign
from thelma.db.schema.tables import molecule
from thelma.db.schema.tables import moleculedesign
from thelma.db.schema.tables import moleculedesigngene
from thelma.db.schema.tables import moleculedesignlibrary
from thelma.db.schema.tables import moleculedesignlibraryisorequest
from thelma.db.schema.tables import moleculedesignpool
from thelma.db.schema.tables import moleculedesignpoolset
from thelma.db.schema.tables import moleculedesignpoolsetmember
from thelma.db.schema.tables import moleculedesignset
from thelma.db.schema.tables import moleculedesignsetgene
from thelma.db.schema.tables import moleculedesignsetmember
from thelma.db.schema.tables import moleculedesignstructure
from thelma.db.schema.tables import moleculedesignversionedtranscripttarget
from thelma.db.schema.tables import moleculetype
from thelma.db.schema.tables import organization
from thelma.db.schema.tables import plannedcontainerdilution
from thelma.db.schema.tables import plannedcontainertransfer
from thelma.db.schema.tables import plannedracktransfer
from thelma.db.schema.tables import plannedtransfer
from thelma.db.schema.tables import plannedworklist
from thelma.db.schema.tables import plannedworklistmember
from thelma.db.schema.tables import pooledsuppliermoleculedesign
from thelma.db.schema.tables import project
from thelma.db.schema.tables import rack
from thelma.db.schema.tables import rackbarcodedlocation
from thelma.db.schema.tables import racklayout
from thelma.db.schema.tables import rackposition
from thelma.db.schema.tables import rackpositionset
from thelma.db.schema.tables import rackpositionsetmember
from thelma.db.schema.tables import rackshape
from thelma.db.schema.tables import rackspecs
from thelma.db.schema.tables import rackspecscontainerspecs
from thelma.db.schema.tables import releasegenetranscript
from thelma.db.schema.tables import releaseversionedtranscript
from thelma.db.schema.tables import reservoirspecs
from thelma.db.schema.tables import sample
from thelma.db.schema.tables import samplemolecule
from thelma.db.schema.tables import sampleregistration
from thelma.db.schema.tables import singlestrandeddesign
from thelma.db.schema.tables import singlestrandedmodification
from thelma.db.schema.tables import singlesuppliermoleculedesign
from thelma.db.schema.tables import species
from thelma.db.schema.tables import stocksample
from thelma.db.schema.tables import subproject
from thelma.db.schema.tables import suppliermoleculedesign
from thelma.db.schema.tables import supplierstructureannotation
from thelma.db.schema.tables import tag
from thelma.db.schema.tables import tagged
from thelma.db.schema.tables import taggedrackpositionset
from thelma.db.schema.tables import tagging
from thelma.db.schema.tables import target
from thelma.db.schema.tables import targetset
from thelma.db.schema.tables import targetsetmember
from thelma.db.schema.tables import transcript
from thelma.db.schema.tables import tubetransfer
from thelma.db.schema.tables import tubetransferworklist
from thelma.db.schema.tables import tubetransferworklistmember
from thelma.db.schema.tables import user
from thelma.db.schema.tables import userpreferences
from thelma.db.schema.tables import versionedtranscript
from thelma.db.schema.tables import worklistseries
from thelma.db.schema.tables import worklistseriesexperimentdesign
from thelma.db.schema.tables import worklistseriesexperimentdesignrack
from thelma.db.schema.tables import worklistseriesisorequest
from thelma.db.schema.tables import worklistseriesmember

# Not all tables are dependencies for other tables. pylint: disable=W0612
def initialize_tables(metadata):
    organization_tbl = organization.create_table(metadata)
    molecule_type_tbl = moleculetype.create_table(metadata)
    molecule_design_tbl = moleculedesign.create_table(metadata,
                                                      molecule_type_tbl)
    molecule_design_set_tbl = moleculedesignset.create_table(metadata)
    moleucle_design_pool_tbl = \
            moleculedesignpool.create_table(metadata, molecule_design_set_tbl,
                                                      molecule_type_tbl)
    molecule_design_set_member_tbl = moleculedesignsetmember.create_table(
                    metadata, molecule_design_tbl, molecule_design_set_tbl)
    chemical_structure_tbl = chemicalstructure.create_table(metadata)
    molecule_design_structure_tbl = \
            moleculedesignstructure.create_table(metadata,
                                                 molecule_design_tbl,
                                                 chemical_structure_tbl)
    item_status_tbl = itemstatus.create_table(metadata)
    rack_shape_tbl = rackshape.create_table(metadata)
    container_specs_tbl = containerspecs.create_table(metadata,
                                                      organization_tbl)
    rack_specs_tbl = rackspecs.create_table(metadata, organization_tbl,
                                            rack_shape_tbl)
    container_tbl = container.create_table(metadata, container_specs_tbl,
                                           item_status_tbl)
    containerbarcode_tbl = containerbarcode.create_table(metadata,
                                                         container_tbl)
    rack_specs_container_specs_tbl = \
        rackspecscontainerspecs.create_table(metadata, rack_specs_tbl,
                                             container_specs_tbl)
    rack_tbl = rack.create_table(metadata, item_status_tbl, rack_specs_tbl)
    device_type_tbl = devicetype.create_table(metadata)
    device_tbl = device.create_table(metadata, device_type_tbl, organization_tbl)
    barcoded_location_tbl = barcodedlocation.create_table(metadata, device_tbl)
    rack_barcoded_location_tbl = rackbarcodedlocation.create_table(
                                                        metadata,
                                                        rack_tbl,
                                                        barcoded_location_tbl)
    containment.create_table(metadata, container_tbl, rack_tbl)
    molecule_tbl = molecule.create_table(metadata, molecule_design_tbl,
                                         organization_tbl)
    sample_tbl = sample.create_table(metadata, container_tbl)
    sampleregistration.create_table(metadata, sample_tbl)
    sample_molecule_tbl = samplemolecule.create_table(metadata, sample_tbl,
                                                      molecule_tbl)
    stocksample.create_table(metadata, sample_tbl, organization_tbl,
                             molecule_design_set_tbl, molecule_type_tbl)
    single_stranded_modification_tbl = \
                               singlestrandedmodification.create_table(metadata)
    single_stranded_design_tbl = singlestrandeddesign.create_table(metadata,
                          molecule_design_tbl, single_stranded_modification_tbl)
    double_stranded_modification_tbl = \
                               doublestrandedmodification.create_table(metadata)
    double_stranded_design_tbl = \
        doublestrandeddesign.create_table(metadata, molecule_design_tbl,
                                          double_stranded_modification_tbl)
    compound_tbl = compound.create_table(metadata, molecule_design_tbl)

    species_tbl = species.create_table(metadata)
    gene_tbl = gene.create_table(metadata, species_tbl)
    molecule_design_gene_tbl = \
        moleculedesigngene.create_table(metadata, molecule_design_tbl,
                                        gene_tbl)
    molecule_design_set_gene_tbl = \
        moleculedesignsetgene.create_table(metadata, molecule_design_set_tbl,
                                           gene_tbl)

    molecule_design_pool_set_tbl = moleculedesignpoolset.create_table(metadata,
                                                        molecule_type_tbl)
    molecule_design_pool_set_member_tbl = moleculedesignpoolsetmember.\
                create_table(metadata, molecule_design_set_tbl,
                                       molecule_design_pool_set_tbl)

    db_source_tbl = dbsource.create_table(metadata)
    db_release_tbl = dbrelease.create_table(metadata, db_source_tbl)
    current_db_release_tbl = currentdbrelease.create_table(metadata,
                                                           db_source_tbl,
                                                           db_release_tbl)
    transcript_tbl = transcript.create_table(metadata, species_tbl)
    release_gene_transcript_tbl = \
        releasegenetranscript.create_table(metadata, db_release_tbl, gene_tbl,
                                           transcript_tbl)
    versioned_transcript_tbl = versionedtranscript.create_table(metadata,
                                                                transcript_tbl)
    release_versioned_transcript_tbl = \
        releaseversionedtranscript.create_table(metadata, db_release_tbl,
                                                versioned_transcript_tbl)
    molecule_design_ver_tran_target_tbl = \
        moleculedesignversionedtranscripttarget.create_table(
                                                    metadata,
                                                    molecule_design_tbl,
                                                    versioned_transcript_tbl)
    supplier_molecule_design_tbl = suppliermoleculedesign.create_table(
                                                metadata, organization_tbl)
    singlesuppliermoleculedesign.create_table(metadata,
                                              supplier_molecule_design_tbl,
                                              molecule_design_tbl)
    pooledsuppliermoleculedesign.create_table(metadata,
                                              supplier_molecule_design_tbl,
                                              molecule_design_set_tbl)
    supplierstructureannotation.create_table(metadata,
                                             supplier_molecule_design_tbl,
                                             chemical_structure_tbl)
    mirna_tbl = mirna.create_table(metadata)
    mirna_mimic_design_tbl = \
        mirnamimicdesign.create_table(metadata, molecule_design_tbl, mirna_tbl)
    mirna_inhi_modification_tbl = \
        mirnainhibitormodification.create_table(metadata)
    mirna_inhi_design_tbl = \
        mirnainhibitordesign.create_table(metadata, molecule_design_tbl,
                                          mirna_inhi_modification_tbl)

    dbuser_tbl = user.create_table(metadata)
    user_preferences_tbl = userpreferences.create_table(metadata, dbuser_tbl)

    tag_tbl = tag.create_table(metadata)
    tagged_tbl = tagged.create_table(metadata)
    tagging_tbl = tagging.create_table(metadata, tagged_tbl, tag_tbl,
                                       dbuser_tbl)
    target_tbl = target.create_table(metadata,
                            transcript_tbl, molecule_design_tbl)
    target_set_tbl = targetset.create_table(metadata)
    target_set_member_tbl = targetsetmember.create_table(metadata,
                                            target_tbl, target_set_tbl)
    rack_position_tbl = rackposition.create_table(metadata)
    rack_position_set_tbl = rackpositionset.create_table(metadata)
    rack_position_set_member_tbl = rackpositionsetmember.create_table(
                        metadata, rack_position_set_tbl, rack_position_tbl)
    rack_layout_tbl = racklayout.create_table(metadata, rack_shape_tbl)
    tagged_rack_position_set_tbl = taggedrackpositionset.create_table(
                metadata, rack_layout_tbl, tagged_tbl, rack_position_set_tbl)
    project_tbl = project.create_table(metadata, organization_tbl, dbuser_tbl)

    subproject_tbl = subproject.create_table(metadata, project_tbl)

    job_type_tbl = jobtype.create_table(metadata)
    job_tbl = job.create_table(metadata, job_type_tbl, dbuser_tbl,
                               subproject_tbl)

    reservoir_specs_tbl = reservoirspecs.create_table(metadata, rack_shape_tbl)
    planned_transfer_tbl = plannedtransfer.create_table(metadata)
    planned_container_dilution_tbl = plannedcontainerdilution.create_table(
                            metadata, planned_transfer_tbl, rack_position_tbl)
    planned_container_transfer_tbl = plannedcontainertransfer.create_table(
                            metadata, planned_transfer_tbl, rack_position_tbl)
    planned_rack_transfer_tbl = plannedracktransfer.create_table(metadata,
                            planned_transfer_tbl)
    planned_worklist_tbl = plannedworklist.create_table(metadata)
    planned_worklist_member_tbl = plannedworklistmember.create_table(metadata,
                            planned_worklist_tbl, planned_transfer_tbl)
    worklist_series_tbl = worklistseries.create_table(metadata)
    worklist_series_member_tbl = worklistseriesmember.create_table(metadata,
                            worklist_series_tbl, planned_worklist_tbl)

    executed_transfer_tbl = executedtransfer.create_table(metadata,
                            planned_transfer_tbl, dbuser_tbl)
    executed_container_dilution_tbl = executedcontainerdilution.create_table(
                            metadata, executed_transfer_tbl, container_tbl,
                            reservoir_specs_tbl)
    executed_container_transfer_tbl = executedcontainertransfer.create_table(
                            metadata, executed_transfer_tbl, container_tbl)
    executed_rack_transfer_tbl = executedracktransfer.create_table(metadata,
                            executed_transfer_tbl, rack_tbl)
    executed_worklist_tbl = executedworklist.create_table(metadata,
                                                        planned_worklist_tbl)
    executed_worklist_member_tbl = executedworklistmember.create_table(metadata,
                            executed_worklist_tbl, executed_transfer_tbl)

    tube_transfer_tbl = tubetransfer.create_table(metadata, container_tbl,
                                                  rack_tbl, rack_position_tbl)
    tube_transfer_worklist_tbl = tubetransferworklist.create_table(metadata,
                                                                   dbuser_tbl)
    tube_transfer_worklist_member_tbl = tubetransferworklistmember.create_table(
                        metadata, tube_transfer_tbl, tube_transfer_worklist_tbl)

    iso_request_tbl = isorequest.create_table(metadata, rack_layout_tbl,
                        dbuser_tbl)
    experiment_metadata_type_tbl = experimentmetadatatype.create_table(metadata)
    experiment_metadata_tbl = experimentmetadata.create_table(metadata,
                    subproject_tbl, experiment_metadata_type_tbl)
    experiment_design_tbl = experimentdesign.create_table(metadata,
                                        rack_shape_tbl, experiment_metadata_tbl)
    worklist_series_experiment_design_tbl = \
            worklistseriesexperimentdesign.create_table(metadata,
            experiment_design_tbl, worklist_series_tbl)
    experiment_tbl = experiment.create_table(
                    metadata, rack_specs_tbl, experiment_design_tbl, job_tbl)
    experiment_source_rack_tbl = experimentsourcerack.create_table(metadata,
                                                   experiment_tbl, rack_tbl)
    experiment_design_rack_tbl = experimentdesignrack.create_table(
                            metadata, experiment_design_tbl, rack_layout_tbl)
    worklist_series_experiment_design_rack_tbl = \
                    worklistseriesexperimentdesignrack.create_table(metadata,
                    experiment_design_rack_tbl, worklist_series_tbl)
    experiment_rack_tbl = experimentrack.create_table(metadata,
                        experiment_design_rack_tbl, experiment_tbl, rack_tbl)
    # FIXME: add and repair experiment racks#pylint: disable=W0511

    experiment_design_tagged_rack_position_set_tbl = \
        experimentdesigntaggedrackpositionset.create_table(metadata,
                                                tagged_rack_position_set_tbl,
                                                experiment_design_rack_tbl)

    worklist_series_iso_request_tbl = worklistseriesisorequest.create_table(
                                metadata, iso_request_tbl, worklist_series_tbl)
    experiment_metadata_iso_request_tbl = experimentmetadataisorequest.\
                    create_table(metadata, experiment_metadata_tbl,
                                 iso_request_tbl)
    experiment_metadata_pool_set_tbl = experimentmetadatapoolset.create_table(
                            metadata, experiment_metadata_tbl,
                            molecule_design_pool_set_tbl)
    experiment_metadata_target_set_tbl = experimentmetadatatargetset.\
            create_table(metadata, experiment_metadata_tbl, target_set_tbl)

    iso_tbl = iso.create_table(metadata, iso_request_tbl, rack_layout_tbl)
    library_creation_iso_tbl = librarycreationiso.create_table(metadata,
                                                               iso_tbl)
    library_source_plate_tbl = librarysourceplate.create_table(metadata,
                                    library_creation_iso_tbl, rack_tbl)
    iso_pool_set_tbl = isopoolset.create_table(metadata, iso_tbl,
                                               molecule_design_pool_set_tbl)
    iso_job_tbl = isojob.create_table(metadata, job_tbl)
    iso_job_member_tbl = isojobmember.create_table(metadata, job_tbl, iso_tbl)

    iso_control_tock_rack_tbl = isocontrolstockrack.create_table(metadata,
                iso_job_tbl, rack_layout_tbl, rack_tbl, planned_worklist_tbl)
    iso_sample_stock_rack_tbl = isosamplestockrack.create_table(metadata,
                            iso_tbl, rack_tbl, planned_worklist_tbl)
    iso_aliquot_plate_tbl = isoaliquotplate.create_table(metadata, iso_tbl,
                                                        rack_tbl)
    iso_preparation_plate_tbl = isopreparationplate.create_table(metadata,
                                                        iso_tbl, rack_tbl)

    experiment_rack_job_tbl = experimentrackjob.create_table(
                    metadata, job_tbl, experiment_rack_tbl)

    molecule_design_library_tbl = moleculedesignlibrary.create_table(metadata,
                                                molecule_design_pool_set_tbl)
    molecule_design_library_iso_request_tbl = moleculedesignlibraryisorequest.\
            create_table(metadata, molecule_design_library_tbl, iso_request_tbl)

#pylint: enable=W0612
