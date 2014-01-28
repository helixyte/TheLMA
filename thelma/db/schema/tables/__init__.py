from thelma.db.schema.tables import barcodedlocation
from thelma.db.schema.tables import chemicalstructure
from thelma.db.schema.tables import compound
from thelma.db.schema.tables import container
from thelma.db.schema.tables import containerbarcode
from thelma.db.schema.tables import containerspecs
from thelma.db.schema.tables import containment
from thelma.db.schema.tables import device
from thelma.db.schema.tables import devicetype
from thelma.db.schema.tables import executedliquidtransfer
from thelma.db.schema.tables import executedracksampletransfer
from thelma.db.schema.tables import executedsampledilution
from thelma.db.schema.tables import executedsampletransfer
from thelma.db.schema.tables import executedworklist
from thelma.db.schema.tables import executedworklistmember
from thelma.db.schema.tables import experiment
from thelma.db.schema.tables import experimentdesign
from thelma.db.schema.tables import experimentdesignrack
from thelma.db.schema.tables import experimentdesigntaggedrackpositionset
from thelma.db.schema.tables import experimentmetadata
from thelma.db.schema.tables import experimentmetadataisorequest
from thelma.db.schema.tables import experimentmetadatatype
from thelma.db.schema.tables import experimentrack
from thelma.db.schema.tables import experimentrackjob
from thelma.db.schema.tables import experimentsourcerack
from thelma.db.schema.tables import iso
from thelma.db.schema.tables import isoaliquotplate
from thelma.db.schema.tables import isojob
from thelma.db.schema.tables import isojobmember
from thelma.db.schema.tables import isojobpreparationplate
from thelma.db.schema.tables import isojobstockrack
from thelma.db.schema.tables import isoplate
from thelma.db.schema.tables import isopoolset
from thelma.db.schema.tables import isopreparationplate
from thelma.db.schema.tables import isorequest
from thelma.db.schema.tables import isorequestpoolset
from thelma.db.schema.tables import isosectorpreparationplate
from thelma.db.schema.tables import isosectorstockrack
from thelma.db.schema.tables import isostockrack
from thelma.db.schema.tables import itemstatus
from thelma.db.schema.tables import job
from thelma.db.schema.tables import labisolibraryplate
from thelma.db.schema.tables import labisorequest
from thelma.db.schema.tables import libraryplate
from thelma.db.schema.tables import molecule
from thelma.db.schema.tables import moleculedesign
from thelma.db.schema.tables import moleculedesigngene
from thelma.db.schema.tables import moleculedesignlibrary
from thelma.db.schema.tables import moleculedesignlibrarycreationisorequest
from thelma.db.schema.tables import moleculedesignlibrarylabisorequest
from thelma.db.schema.tables import moleculedesignpool
from thelma.db.schema.tables import moleculedesignpoolset
from thelma.db.schema.tables import moleculedesignpoolsetmember
from thelma.db.schema.tables import moleculedesignset
from thelma.db.schema.tables import moleculedesignsetgene
from thelma.db.schema.tables import moleculedesignsetmember
from thelma.db.schema.tables import moleculedesignstructure
from thelma.db.schema.tables import moleculetype
from thelma.db.schema.tables import organization
from thelma.db.schema.tables import pipettingspecs
from thelma.db.schema.tables import plannedliquidtransfer
from thelma.db.schema.tables import plannedracksampletransfer
from thelma.db.schema.tables import plannedsampledilution
from thelma.db.schema.tables import plannedsampletransfer
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
from thelma.db.schema.tables import refseqgene
from thelma.db.schema.tables import reservoirspecs
from thelma.db.schema.tables import sample
from thelma.db.schema.tables import samplemolecule
from thelma.db.schema.tables import sampleregistration
from thelma.db.schema.tables import singlesuppliermoleculedesign
from thelma.db.schema.tables import species
from thelma.db.schema.tables import stockrack
from thelma.db.schema.tables import stocksample
from thelma.db.schema.tables import stocksamplecreationiso
from thelma.db.schema.tables import stocksamplecreationisorequest
from thelma.db.schema.tables import subproject
from thelma.db.schema.tables import suppliermoleculedesign
from thelma.db.schema.tables import supplierstructureannotation
from thelma.db.schema.tables import tag
from thelma.db.schema.tables import tagged
from thelma.db.schema.tables import taggedrackpositionset
from thelma.db.schema.tables import tagging
from thelma.db.schema.tables import tubetransfer
from thelma.db.schema.tables import tubetransferworklist
from thelma.db.schema.tables import tubetransferworklistmember
from thelma.db.schema.tables import user
from thelma.db.schema.tables import userpreferences
from thelma.db.schema.tables import worklistseries
from thelma.db.schema.tables import worklistseriesexperimentdesign
from thelma.db.schema.tables import worklistseriesexperimentdesignrack
from thelma.db.schema.tables import worklistseriesisojob
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
    compound_tbl = compound.create_table(metadata, molecule_design_tbl)

    species_tbl = species.create_table(metadata)
    refseq_gene_tbl = refseqgene.create_table(metadata, species_tbl)
    molecule_design_gene_tbl = \
        moleculedesigngene.create_table(metadata, molecule_design_tbl,
                                        refseq_gene_tbl)
    molecule_design_set_gene_tbl = \
        moleculedesignsetgene.create_table(metadata, molecule_design_set_tbl,
                                           refseq_gene_tbl)

    molecule_design_pool_set_tbl = moleculedesignpoolset.create_table(metadata,
                                                        molecule_type_tbl)
    molecule_design_pool_set_member_tbl = moleculedesignpoolsetmember.\
                create_table(metadata, molecule_design_set_tbl,
                                       molecule_design_pool_set_tbl)

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
    dbuser_tbl = user.create_table(metadata)
    user_preferences_tbl = userpreferences.create_table(metadata, dbuser_tbl)

    tag_tbl = tag.create_table(metadata)
    tagged_tbl = tagged.create_table(metadata)
    tagging_tbl = tagging.create_table(metadata, tagged_tbl, tag_tbl,
                                       dbuser_tbl)
    rack_position_tbl = rackposition.create_table(metadata)
    rack_position_set_tbl = rackpositionset.create_table(metadata)
    rack_position_set_member_tbl = rackpositionsetmember.create_table(
                        metadata, rack_position_set_tbl, rack_position_tbl)
    rack_layout_tbl = racklayout.create_table(metadata, rack_shape_tbl)
    tagged_rack_position_set_tbl = taggedrackpositionset.create_table(
                metadata, rack_layout_tbl, tagged_tbl, rack_position_set_tbl)
    project_tbl = project.create_table(metadata, organization_tbl, dbuser_tbl)

    subproject_tbl = subproject.create_table(metadata, project_tbl)

    job_tbl = job.create_table(metadata, dbuser_tbl)

    pipetting_specs_tbl = pipettingspecs.create_table(metadata)
    reservoir_specs_tbl = reservoirspecs.create_table(metadata, rack_shape_tbl)
    planned_liquid_transfer_tbl = plannedliquidtransfer.create_table(metadata)
    planned_sample_dilution_tbl = plannedsampledilution.create_table(metadata,
                                 planned_liquid_transfer_tbl, rack_position_tbl)
    planned_sample_transfer_tbl = plannedsampletransfer.create_table(metadata,
                                planned_liquid_transfer_tbl, rack_position_tbl)
    planned_rack_sample_transfer_tbl = plannedracksampletransfer.create_table(
                                      metadata, planned_liquid_transfer_tbl)
    planned_worklist_tbl = plannedworklist.create_table(metadata,
                                                        pipetting_specs_tbl)
    planned_worklist_member_tbl = plannedworklistmember.create_table(metadata,
                            planned_worklist_tbl, planned_liquid_transfer_tbl)
    worklist_series_tbl = worklistseries.create_table(metadata)
    worklist_series_member_tbl = worklistseriesmember.create_table(metadata,
                            worklist_series_tbl, planned_worklist_tbl)

    executed_liquid_transfer_tbl = executedliquidtransfer.create_table(metadata,
                            planned_liquid_transfer_tbl, dbuser_tbl)
    executed_sample_dilution_tbl = executedsampledilution.create_table(metadata,
                            executed_liquid_transfer_tbl, container_tbl,
                            reservoir_specs_tbl)
    executed_sample_transfer_tbl = executedsampletransfer.create_table(metadata,
                            executed_liquid_transfer_tbl, container_tbl)
    executed_rack_sample_transfer_tbl = executedracksampletransfer.create_table(
                            metadata, executed_liquid_transfer_tbl, rack_tbl)
    executed_worklist_tbl = executedworklist.create_table(metadata,
                                                        planned_worklist_tbl)
    executed_worklist_member_tbl = executedworklistmember.create_table(metadata,
                            executed_worklist_tbl, executed_liquid_transfer_tbl)

    tube_transfer_tbl = tubetransfer.create_table(metadata, container_tbl,
                                                  rack_tbl, rack_position_tbl)
    tube_transfer_worklist_tbl = tubetransferworklist.create_table(metadata,
                                                                   dbuser_tbl)
    tube_transfer_worklist_member_tbl = tubetransferworklistmember.create_table(
                        metadata, tube_transfer_tbl, tube_transfer_worklist_tbl)

    iso_request_tbl = isorequest.create_table(metadata)
    iso_request_pool_set_tbl = isorequestpoolset.create_table(metadata,
                                  iso_request_tbl, molecule_design_pool_set_tbl)
    lab_iso_request_tbl = labisorequest.create_table(metadata, iso_request_tbl,
                            dbuser_tbl, rack_layout_tbl, reservoir_specs_tbl)
    stock_sample_creation_iso_request = stocksamplecreationisorequest.\
                                        create_table(metadata, iso_request_tbl)

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
    iso_tbl = iso.create_table(metadata, iso_request_tbl, rack_layout_tbl)
    stock_sample_creation_iso_tbl = stocksamplecreationiso.create_table(
                                                            metadata, iso_tbl)
    iso_pool_set_tbl = isopoolset.create_table(metadata, iso_tbl,
                                               molecule_design_pool_set_tbl)
    iso_job_tbl = isojob.create_table(metadata, job_tbl)
    worklist_series_iso_job_tbl = worklistseriesisojob.create_table(metadata,
                                            iso_job_tbl, worklist_series_tbl)
    iso_job_member_tbl = isojobmember.create_table(metadata, job_tbl, iso_tbl)

    stock_rack_tbl = stockrack.create_table(metadata, rack_tbl, rack_layout_tbl,
                                            worklist_series_tbl)
    iso_job_stock_rack_tbl = isojobstockrack.create_table(metadata,
                                                    stock_rack_tbl, job_tbl)
    iso_stock_rack_tbl = isostockrack.create_table(metadata, stock_rack_tbl,
                                                   iso_tbl)
    iso_sector_stock_rack_tbl = isosectorstockrack.create_table(metadata,
                                                        stock_rack_tbl, iso_tbl)
    iso_plate_tbl = isoplate.create_table(metadata, iso_tbl, rack_tbl)
    iso_aliquot_plate_tbl = isoaliquotplate.create_table(metadata,
                                                         iso_plate_tbl)
    iso_preparation_plate_tbl = isopreparationplate.create_table(metadata,
                                             iso_plate_tbl, rack_layout_tbl)
    iso_sector_preparation_plate_tbl = isosectorpreparationplate.create_table(
                                      metadata, iso_plate_tbl, rack_layout_tbl)
    iso_job_preparation_plate_tbl = isojobpreparationplate.create_table(
                                metadata, rack_tbl, job_tbl, rack_layout_tbl)

    experiment_rack_job_tbl = experimentrackjob.create_table(
                    metadata, job_tbl, experiment_rack_tbl)

    molecule_design_library_tbl = moleculedesignlibrary.create_table(metadata,
                                rack_layout_tbl, molecule_design_pool_set_tbl)
    molecule_design_library_creation_iso_request_tbl = \
            moleculedesignlibrarycreationisorequest.create_table(metadata,
            molecule_design_library_tbl, stock_sample_creation_iso_request)
    molecule_design_library_lab_iso_request_tbl = \
            moleculedesignlibrarylabisorequest.create_table(metadata,
            molecule_design_library_tbl, lab_iso_request_tbl)
    library_plate_tbl = libraryplate.create_table(metadata,
                                        molecule_design_library_tbl, rack_tbl)
    iso_library_plate_tbl = labisolibraryplate.create_table(metadata, iso_tbl,
                                                            library_plate_tbl)

#pylint: enable=W0612
