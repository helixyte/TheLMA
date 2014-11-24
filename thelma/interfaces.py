"""
thelma.interfaces

NP
"""

from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'

__all__ = ['IBarcodePrintJob',
           'IChemicalStructure',
           'IChemicalStructureType',
           'IContainer',
           'IContainerSpecs',
           'IDevice',
           'IDeviceType',
           'IExperiment',
           'IExperimentDesign',
           'IExperimentDesignRack',
           'IExperimentJob',
           'IExperimentMetadata',
           'IExperimentMetadataType',
           'IExperimentRack',
           'IGene',
           'IIso',
           'ILabIso',
           'IStockSampleCreationIso',
           'IIsoJob',
           'IIsoRequest',
           'ILabIsoRequest',
           'IStockSampleCreationIsoRequest',
           'IItemStatus',
           'IJob',
           'ILocation',
           'ILocationType',
           'IMolecule',
           'IMoleculeDesign',
           'IMoleculeDesignPool',
           'IMoleculeDesignSet',
           'IMoleculeType',
           'IOrganization',
           'IPipettingSpecs',
           'IPlate',
           'IPlateSpecs',
           'IProject',
           'IRack',
           'IRackLayout',
           'IRackShape',
           'IRackSpecs',
           'ISample',
           'ISampleMolecule',
           'ISeriesMember',
           'ISpecies',
           'IStockInfo',
           'IStockSample',
           'ISubproject',
           'ITag',
           'ITaggedRackPositionSet',
           'ITractor',
           'ITube',
           'ITubeRack',
           'ITubeRackSpecs',
           'ITubeSpecs',
           'IUser',
           'IUserPreferences',
           'IWell',
           'IWellSpecs',
           ]

# interfaces do not provide a constructor. pylint: disable=W0232
# interface methods do not have self pylint: disable = E0213
class IBarcodePrintJob(Interface):
    """
    Marker interface indicating participation in barcode print job resources.
    """


class IChemicalStructureType(Interface):
    """
    Marker interface indicating participation in chemical structure type
    resources.
    """


class IChemicalStructure(Interface):
    """
    Marker interface indicating participation in chemical structure resources.
    """


class IContainer(Interface):
    """
    Marker interface indicating participation in container resources.
    """


class IContainerSpecs(Interface):
    """
    Marker interface indicating participation in container specs resources.
    """


class IDevice(Interface):
    """
    Marker interface indicating participation in device resources.
    """


class IExecutedLiquidTransfer(Interface):
    """
    Marker interface indicating participation in executed transfer resources.
    """


class IExecutedSampleDilution(Interface):
    """
    Marker interface indicating participation in executed container dilution
    resources.
    """


class IExecutedSampleTransfer(Interface):
    """
    Marker interface indicating participation in executed container transfer
    resources.
    """


class IExecutedRackSampleTransfer(Interface):
    """
    Marker interface indicating participation in executed rack transfer
    resources.
    """


class IExecutedWorklist(Interface):
    """
    Marker interface indicating participation in executed worklist resources.
    """


class IDeviceType(Interface):
    """
    Marker interface indicating participation in device type resources.
    """


class IExperiment(Interface):
    """
    Marker interface indicating participation in experiment resources.
    """


class IExperimentDesign(Interface):
    """
    Marker interface indicating participation in experiment design resources.
    """


class IExperimentDesignRack(Interface):
    """
    Marker interface indicating participation in experiment design rack
    resources.
    """

class IExperimentMetadata(Interface):
    """
    Marker interface indicating participation in experiment meta data
    resources.
    """


class IExperimentMetadataType(Interface):
    """
    Marker interface indicating participation in experiment meta data type
    resources.
    """


class IExperimentRack(Interface):
    """
    Marker interface indicating participation in experiment rack resources.
    """


class IGene(Interface):
    """
    Marker interface indicating participation in gene resources.
    """


class IIso(Interface):
    """
    Marker interface indicating participation in ISO resources.
    """


class ILabIso(IIso):
    """
    Marker interface indicating participation in lab ISO resources.
    """

class IStockSampleCreationIso(IIso):
    """
    Marker interface indication participation of stock sample creation
    ISO resources.
    """


class IIsoRequest(Interface):
    """
    Marker interface indicating participation in ISO request resources.
    """


class ILabIsoRequest(IIsoRequest):
    """
    Marker interface indicating participation in lab ISO request resources.
    """


class IStockSampleCreationIsoRequest(IIsoRequest):
    """
    Marker interface indicating participation in stock sample creation ISO
    request resources.
    """


class IItemStatus(Interface):
    """
    Marker interface indicating participation in item status resources.
    """


class IJob(Interface):
    """
    Marker interface indicating participation in job resources.
    """


class IExperimentJob(Interface):
    """
    Marker interface indicating participation in experiment job
    resources.
    """


class IIsoJob(IJob):
    """
    Marker interface indicating participation in ISO job resources.
    """


class IStockRack(Interface):
    """
    Marker interface for ISO stock racks.
    """


class IIsoJobStockRack(IStockRack):
    """
    Marker interface for ISO stock racks.
    """


class IIsoStockRack(IStockRack):
    """
    Marker interface for ISO stock racks.
    """


class IIsoSectorStockRack(IStockRack):
    """
    Marker interface for ISO stock racks.
    """


class ILocation(Interface):
    """
    Marker interface indicating participation in location resources.
    """


class ILocationType(Interface):
    """
    Marker interface indicating participation in location type resources.
    """


class IMolecule(Interface):
    """
    Marker interface indicating participation in molecule resources.
    """


class IMoleculeDesign(Interface):
    """
    Marker interface indicating participation in molecule design resources.
    """


class IMoleculeDesignRegistrationItem(Interface):
    """
    Marker interface indicating participation in molecule design registration
    item resources.
    """


class IMoleculeDesignSet(Interface):
    """
    Marker interface indicating participation in the molecule design set
    resources.
    """


class IMoleculeDesignPool(IMoleculeDesignSet):
    """
    Marker interface indicating participation in molecule design pool
    resources.
    """


class IMoleculeDesignPoolRegistrationItem(Interface):
    """
    Marker interface indicating participation in molecule design pool
    registration item resources.
    """


class IMoleculeDesignPoolSet(Interface):
    """
    Marker interface indicating participation in molecule design pool set
    resources.
    """


class IMoleculeDesignLibrary(Interface):
    """
    Marker interface indicating participation in molecule design library
    resources.
    """


class ILibraryPlate(Interface):
    """
    Marker interface indicating participation in library plate resources.
    """


class IMoleculeType(Interface):
    """
    Marker interface indicating participation in molecule type resources.
    """


class IOrganization(Interface):
    """
    Marker interface indicating participation in organization resources.
    """


class IPlannedLiquidTransfer(Interface):
    """
    Marker interface indicating participation in planned transfer resources
    """


class IPlannedSampleDilution(Interface):
    """
    Marker interface indicating participation in planned container dilution
    resources
    """


class IPlannedSampleTransfer(Interface):
    """
    Marker interface indicating participation in planned container transfer
    resources
    """


class IPlannedRackSampleTransfer(Interface):
    """
    Marker interface indicating participation in planned rack transfer resources
    """


class IPlannedWorklist(Interface):
    """
    Marker interface indicating participation in planned worklist resources
    """


class IPipettingSpecs(Interface):
    """
    Marker interface indicating participation in pipetting specs resources.
    """


class IPlate(Interface):
    """
    Marker interface indicating participation in plate resources.
    """


class IPlateSpecs(Interface):
    """
    Marker interface indicating participation in plate specs resources.
    """


class IProject(Interface):
    """
    Marker interface indicating participation in project resources.
    """


class IRack(Interface):
    """
    Marker interface indicating participation in rack resources.
    """


class IRackLayout(Interface):
    """
    Marker interface indicating participation in rack layout resources.
    """


class IRackPosition(Interface):
    """
    Marker interface indicating participation in rack position resources.
    """


class IRackPositionSet(Interface):
    """
    Marker interface indicating participation in rack position set resources.
    """


class IRackShape(Interface):
    """
    Marker interface indicating participation in rack shape resources.
    """


class IRackSpecs(Interface):
    """
    Marker interface indicating participation in rack specs resources.
    """


class IReservoirSpecs(Interface):
    """
    Marker interface indicating participation in reservoir specs resources.
    """


class ISample(Interface):
    """
    Marker interface indicating participation in sample resources.
    """


class IStockSample(Interface):
    """
    Marker interface indicating participation in stock sample resources.
    """


class ISampleMolecule(Interface):
    """
    Marker interface indicating participation in sample molecule
    resources.
    """


class ISampleRegistrationItem(Interface):
    """
    Marker interface indicating participation in sample registration item
    resources.
    """


class ISupplierSampleRegistrationItem(Interface):
    """
    Marker interface indicating participation in supplier sample registration
    item resources.
    """


class ISeriesMember(Interface):
    """
    Marker interface indicating participation fo series member resources.
    """


class ISpecies(Interface):
    """
    Marker interface indicating participation in species resources.
    """


class IStockInfo(Interface):
    """
    Marker interface indicating participation in stock info resources.
    """


class ISubproject(Interface):
    """
    Marker interface indicating participation in subproject resources.
    """


class ISupplierMoleculeDesign(Interface):
    """
    Marker interface indicating participation in supplier molecule design
    resources.
    """


class ITag(Interface):
    """
    Marker interface indicating participation in tag resources.
    """


class ITaggedRackPositionSet(Interface):
    """
    Marker interface indicating participation in tagged rack position set
    resources.
    """


class ITractor(Interface):
    """
    Marker interface by which you can get the registered config file for the
    tractor API.
    """


class ITube(Interface):
    """
    Marker interface indicating participation in tube resources.
    """


class ITubeTransfer(Interface):
    """
    Marker interface indicating participation in tube transfer resources.
    """


class ITubeTransferWorklist(Interface):
    """
    Marker interface indicating participation in tube transfer worklist
    resources.
    """


class ITubeRack(Interface):
    """
    Marker interface indicating participation in tube rack resources.
    """


class ITubeRackSpecs(Interface):
    """
    Marker interface indicating participation in tube rack specs resources.
    """


class ITubeSpecs(Interface):
    """
    Marker interface indicating participation in tube specs resources.
    """


class IUser(Interface):
    """
    Marker interface indicating participation in user resources.
    """


class IUserPreferences(Interface):
    """
    Marker interface indicating participation in user resources.
    """


class IWell(Interface):
    """
    Marker interface indicating participation in well resources.
    """


class IWellSpecs(Interface):
    """
    Marker interface indicating participation in well specs resources.
    """


class IWorklistSeries(Interface):
    """
    Marker interface indicating participation in worklist series resources.
    """

# pylint: enable=W0232,E0213
