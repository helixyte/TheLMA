from thelma.db.mappers import amplicondesign
from thelma.db.mappers import antimirdesign
from thelma.db.mappers import barcodedlocation
from thelma.db.mappers import barcodedlocationtype
from thelma.db.mappers import chemicalstructure
from thelma.db.mappers import cloneddsdnadesign
from thelma.db.mappers import compoundchemicalstructure
from thelma.db.mappers import compounddesign
from thelma.db.mappers import container
from thelma.db.mappers import containerlocation
from thelma.db.mappers import containerspecs
from thelma.db.mappers import device
from thelma.db.mappers import devicetype
from thelma.db.mappers import esirnadesign
from thelma.db.mappers import executedcontainerdilution
from thelma.db.mappers import executedcontainertransfer
from thelma.db.mappers import executedracktransfer
from thelma.db.mappers import executedtransfer
from thelma.db.mappers import executedworklist
from thelma.db.mappers import experiment
from thelma.db.mappers import experimentdesign
from thelma.db.mappers import experimentdesignrack
from thelma.db.mappers import experimentjob
from thelma.db.mappers import experimentmetadata
from thelma.db.mappers import experimentmetadatatype
from thelma.db.mappers import experimentrack
from thelma.db.mappers import gene
from thelma.db.mappers import iso
from thelma.db.mappers import isoaliquotplate
from thelma.db.mappers import isocontrolstockrack
from thelma.db.mappers import isojob
from thelma.db.mappers import isopreparationplate
from thelma.db.mappers import isorequest
from thelma.db.mappers import isosamplestockrack
from thelma.db.mappers import itemstatus
from thelma.db.mappers import job
from thelma.db.mappers import jobtype
from thelma.db.mappers import librarycreationiso
from thelma.db.mappers import librarysourceplate
from thelma.db.mappers import longdsrnadesign
from thelma.db.mappers import mirnainhibitordesign
from thelma.db.mappers import mirnamimicdesign
from thelma.db.mappers import modificationchemicalstructure
from thelma.db.mappers import molecule
from thelma.db.mappers import moleculedesign
from thelma.db.mappers import moleculedesignlibrary
from thelma.db.mappers import moleculedesignpool
from thelma.db.mappers import moleculedesignpoolset
from thelma.db.mappers import moleculedesignset
from thelma.db.mappers import moleculetype
from thelma.db.mappers import nucleicacidchemicalstructure
from thelma.db.mappers import organization
from thelma.db.mappers import otherjob
from thelma.db.mappers import pipettingspecs
from thelma.db.mappers import plannedcontainerdilution
from thelma.db.mappers import plannedcontainertransfer
from thelma.db.mappers import plannedracktransfer
from thelma.db.mappers import plannedtransfer
from thelma.db.mappers import plannedworklist
from thelma.db.mappers import plate
from thelma.db.mappers import platespecs
from thelma.db.mappers import primerdesign
from thelma.db.mappers import project
from thelma.db.mappers import rack
from thelma.db.mappers import racklayout
from thelma.db.mappers import rackposition
from thelma.db.mappers import rackpositionset
from thelma.db.mappers import rackshape
from thelma.db.mappers import rackspecs
from thelma.db.mappers import reservoirspecs
from thelma.db.mappers import sample
from thelma.db.mappers import samplemolecule
from thelma.db.mappers import sampleregistration
from thelma.db.mappers import sirnadesign
from thelma.db.mappers import species
from thelma.db.mappers import standardmoleculedesignset
from thelma.db.mappers import stockinfo
from thelma.db.mappers import stocksample
from thelma.db.mappers import subproject
from thelma.db.mappers import suppliermoleculedesign
from thelma.db.mappers import supplierstructureannotation
from thelma.db.mappers import tag
from thelma.db.mappers import tagged
from thelma.db.mappers import taggedrackpositionset
from thelma.db.mappers import tagging
from thelma.db.mappers import tube
from thelma.db.mappers import tuberack
from thelma.db.mappers import tuberackspecs
from thelma.db.mappers import tubespecs
from thelma.db.mappers import tubetransfer
from thelma.db.mappers import tubetransferworklist
from thelma.db.mappers import unknownchemicalstructure
from thelma.db.mappers import user
from thelma.db.mappers import userpreferences
from thelma.db.mappers import well
from thelma.db.mappers import wellspecs
from thelma.db.mappers import worklistseries
from thelma.db.mappers import worklistseriesmember


def initialize_mappers(tables, views):
    organization.create_mapper(tables['organization'])
    itemstatus.create_mapper(tables['item_status'])
    containerspecs_mapper = \
        containerspecs.create_mapper(tables['container_specs'])
    tubespecs.create_mapper(containerspecs_mapper,
                            tables['rack_specs_container_specs'])
    wellspecs.create_mapper(containerspecs_mapper,
                            tables['rack_specs_container_specs'])
    container_mapper = container.create_mapper(tables['container'])
    tube.create_mapper(container_mapper,
                       tables['container'], tables['container_barcode'])
    well.create_mapper(container_mapper)
    rack_mapper = rack.create_mapper(tables['rack'],
                                     tables['rack_barcoded_location'],
                                     tables['container'],
                                     tables['containment'])
    tuberack.create_mapper(rack_mapper)
    plate.create_mapper(rack_mapper)
    containerlocation.create_mapper(tables['containment'])
    rackshape.create_mapper(tables['rack_shape'])
    rackspecs_mapper = rackspecs.create_mapper(tables['rack_specs'])
    tuberackspecs.create_mapper(rackspecs_mapper,
                                tables['rack_specs_container_specs'])
    platespecs.create_mapper(rackspecs_mapper,
                             tables['rack_specs_container_specs'])
    devicetype.create_mapper(tables['device_type'])
    device.create_mapper(tables['device'])
    barcodedlocation.create_mapper(tables['barcoded_location'],
                                   tables['rack_barcoded_location'])
    barcodedlocationtype.create_mapper(tables['barcoded_location'])
    moleculetype.create_mapper(tables['molecule_type'],
                               views['molecule_type_modification_view'],
                               tables['chemical_structure'])
    samplemolecule.create_mapper(tables['sample_molecule'])
    molecule.create_mapper(tables['molecule'],
                           tables['single_supplier_molecule_design'],
                           tables['supplier_molecule_design'])
    sample_mapper = \
        sample.create_mapper(tables['sample'],
                             tables['sample_molecule'],
                             tables['molecule'],
                             tables['molecule_design_pool'])
    sampleregistration.create_mapper(tables['sample_registration'])
    gene.create_mapper(tables['refseq_gene'],
                       tables['molecule_design_gene'],
                       tables['molecule_design_set_gene'],
                       tables['molecule_design'],
                       tables['molecule_design_pool'])
    species.create_mapper(tables['species'])
    stockinfo.create_mapper(views['stock_info_view'],
                            tables['molecule_design_set'],
                            tables['molecule_design_set_gene'],
                            tables['refseq_gene'])
    chemical_structure_mapper = \
        chemicalstructure.create_mapper(tables['chemical_structure'],
                                        tables['molecule_design_structure'])
    compoundchemicalstructure.create_mapper(chemical_structure_mapper,
                                            tables['chemical_structure'])
    nucleicacidchemicalstructure.create_mapper(chemical_structure_mapper,
                                               tables['chemical_structure'])
    modificationchemicalstructure.create_mapper(chemical_structure_mapper,
                                                tables['chemical_structure'])
    unknownchemicalstructure.create_mapper(chemical_structure_mapper,
                                           tables['chemical_structure'])
    molecule_design_mapper = \
       moleculedesign.create_mapper(tables['molecule_design'],
                                    tables['molecule_design_structure'],
                                    tables['single_supplier_molecule_design'],
                                    tables['molecule_design_gene'],
                                    tables['refseq_gene'])

    molecule_design_set_mapper = \
        moleculedesignset.create_mapper(tables['molecule_design_set'],
                                        tables['molecule_design_set_member'])

    moleculedesignlibrary.create_mapper(tables['molecule_design_library'],
                                tables['iso_request'],
                                tables['molecule_design_library_iso_request'])
    standardmoleculedesignset.create_mapper(
                                molecule_design_set_mapper)
    moleculedesignpool.create_mapper(
                                molecule_design_set_mapper,
                                tables['molecule_design_pool'],
                                tables['pooled_supplier_molecule_design'],
                                tables['supplier_molecule_design'],
                                tables['molecule_design_set_gene'])
    stocksample.create_mapper(sample_mapper, tables['stock_sample'])
    moleculedesignpoolset.create_mapper(
                        tables['molecule_design_pool_set'],
                        tables['molecule_design_pool_set_member'],
                        )
    compounddesign.create_mapper(molecule_design_mapper,
                                 tables['molecule_design'])
    antimirdesign.create_mapper(molecule_design_mapper,
                                tables['molecule_design'])
    cloneddsdnadesign.create_mapper(molecule_design_mapper,
                                    tables['molecule_design'])
    esirnadesign.create_mapper(molecule_design_mapper,
                               tables['molecule_design'])
    longdsrnadesign.create_mapper(molecule_design_mapper,
                                  tables['molecule_design'])
    primerdesign.create_mapper(molecule_design_mapper,
                               tables['molecule_design'])
    amplicondesign.create_mapper(molecule_design_mapper,
                                 tables['molecule_design'])
    sirnadesign.create_mapper(molecule_design_mapper,
                              tables['molecule_design'])
    mirnainhibitordesign.create_mapper(molecule_design_mapper,
                                       tables['molecule_design'])
    mirnamimicdesign.create_mapper(molecule_design_mapper,
                                   tables['molecule_design'])
    suppliermoleculedesign.create_mapper(
                                    tables['supplier_molecule_design'],
                                    tables['single_supplier_molecule_design'],
                                    tables['pooled_supplier_molecule_design'])
    supplierstructureannotation.create_mapper(
                                    tables['supplier_structure_annotation'])
    tagging.create_mapper(tables['tagging'])
    tag.create_mapper(tables['tag'], tables['tag_domain'],
                      tables['tag_predicate'], tables['tag_value'],
                      tables['tagging'])
    tagged_mapper = tagged.create_mapper(tables['tagged'], tables['tagging'])
    taggedrackpositionset.create_mapper(tagged_mapper,
                                        tables['tagged_rack_position_set'])
    rackpositionset.create_mapper(tables['rack_position_set'],
                                        tables['rack_position_set_member'])
    rackposition.create_mapper(tables['rack_position'])
    racklayout.create_mapper(tables['rack_layout'])

    jobtype.create_mapper(tables['job_type'])
    job_mapper = job.create_mapper(tables['job'])
    otherjob.create_mapper(job_mapper, tables['job'])

    # FIXME: pylint: disable=W0511
    #        Need to get rid of the "new_" prefix.
    experiment.create_mapper(tables['new_experiment'],
                             tables['experiment_source_rack'])
    experimentdesignrack.create_mapper(tables['experiment_design_rack'],
                        tables['worklist_series_experiment_design_rack'])
    experimentdesign.create_mapper(tables['experiment_design'],
                        tables['worklist_series_experiment_design'])
    experimentrack.create_mapper(tables['new_experiment_rack'])
    experimentmetadatatype.create_mapper(tables['experiment_metadata_type'])
    experimentmetadata.create_mapper(tables['experiment_metadata'],
                        tables['experiment_metadata_iso_request'],
                        tables['experiment_metadata_pool_set'])
    experimentjob.create_mapper(job_mapper, tables['job'],
                                tables['new_experiment'])


    project.create_mapper(tables['project'])
    subproject.create_mapper(tables['subproject'])
    user.create_mapper(tables['db_user'])
    userpreferences.create_mapper(tables['user_preferences'])


    iso_mapper = iso.create_mapper(tables['iso'], tables['iso_job'],
                      tables['iso_job_member'],
                      tables['iso_pool_set'])
    librarycreationiso.create_mapper(iso_mapper, tables['library_creation_iso'])
    librarysourceplate.create_mapper(tables['library_source_plate'])

    isorequest.create_mapper(tables['iso_request'],
                             tables['worklist_series_iso_request'],
                             tables['experiment_metadata_iso_request'])
    isojob.create_mapper(job_mapper, tables['iso_job'], tables['iso'],
                         tables['iso_job_member'])
    isocontrolstockrack.create_mapper(tables['iso_control_stock_rack'])
    isosamplestockrack.create_mapper(tables['iso_sample_stock_rack'])
    isoaliquotplate.create_mapper(tables['iso_aliquot_plate'])
    isopreparationplate.create_mapper(tables['iso_preparation_plate'])

    pipettingspecs.create_mapper(tables['pipetting_specs'])
    reservoirspecs.create_mapper(tables['reservoir_specs'])
    planned_transfer_mapper = plannedtransfer.create_mapper(
                    tables['planned_transfer'], tables['planned_worklist'],
                    tables['planned_worklist_member'])
    plannedcontainerdilution.create_mapper(planned_transfer_mapper,
                            tables['planned_container_dilution'],
                            tables['rack_position'])
    plannedcontainertransfer.create_mapper(planned_transfer_mapper,
                            tables['planned_container_transfer'],
                            tables['rack_position'])
    plannedracktransfer.create_mapper(planned_transfer_mapper,
                            tables['planned_rack_transfer'])
    plannedworklist.create_mapper(tables['planned_worklist'],
                                  tables['planned_transfer'],
                                  tables['planned_worklist_member'])
    worklistseries.create_mapper(tables['worklist_series'])
    worklistseriesmember.create_mapper(tables['worklist_series_member'])
    executed_transfer_mapper = executedtransfer.create_mapper(
                                                tables['executed_transfer'])
    executedcontainerdilution.create_mapper(executed_transfer_mapper,
                            tables['executed_container_dilution'],
                            tables['container'])
    executedcontainertransfer.create_mapper(executed_transfer_mapper,
                            tables['executed_container_transfer'],
                            tables['container'])
    executedracktransfer.create_mapper(executed_transfer_mapper,
                            tables['executed_rack_transfer'],
                            tables['rack'])
    executedworklist.create_mapper(tables['executed_worklist'],
                                   tables['executed_transfer'],
                                   tables['executed_worklist_member'])

    tubetransfer.create_mapper(tables['tube_transfer'], tables['rack'],
                               tables['rack_position'])
    tubetransferworklist.create_mapper(tables['tube_transfer_worklist'],
                                       tables['tube_transfer'],
                                       tables['tube_transfer_worklist_member'],
                                       tables['db_user'])
