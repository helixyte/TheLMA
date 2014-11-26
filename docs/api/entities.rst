.. _entities_package:

Entities
--------

==============
Entity Classes
==============

Entities represent entities from the database. All entity classes inherit
from the following superclass:

	.. currentmodule:: thelma.entities.base

	.. class:: Entity

		The Abstract base class for all entity entities. It implements the
		BFG marker interface :class:`IEntity`.

Furthermore, each entity class implements a particular marker interface. 
The marker interface a usually called \'I[*class name*]\'.
All entities that can  be as resources as well must have a so-called \'slug\',
that is a :class:`string` identifier that can be used in an URL.

TheLMA knows the following entities (sorted by application area):

	- `Projects and Administration`_
	- `Experiments`_
	- `Genes and Targets`_
	- `Tagging`_
	- `Locations`_
	- `Vessels and Vessel Types`_
	- `Molecule Designs and Modifications`_
	- `Marker Classes`_
	- `Others`_

All entity classes in alphabetical order:

	- BarcodedLocation_
	- BarcodedLocationType_
	- Container_
	- ContainerLocation_
	- ContainerSpecs_
	- Device_
	- DeviceType_
	- Experiment_
	- ExperimentDesign_
	- ExperimentDesignRack_
	- ExperimentMetaData_
	- ExperimentRack_
	- Gene_
	- Iso_
	- IsoPosition_
	- IsoRackLayout_
	- IsoRequest_
	- ItemStatus_
	- Job_
	- JobType_
	- Molecule_
	- MoleculeDesign_
	- MoleculeDesignSet_
	- MoleculeModification_
	- MoleculeType_
	- Organization_
	- Plate_
	- PlateSpecs_
	- Project_
	- Rack_
	- RackLayout_
	- RackPosition_
	- RackPositionSet_
	- RackShape_
	- RackSpecs_
	- Sample_
	- SampleMolecule_
	- Sequence_
	- Species_
	- Subproject_
	- Tag_
	- Tagged_
	- Tagging_
	- TaggedRackPositionSet_
	- Target_
	- TargetSet_
	- Transcript_
	- Tube_
	- TubeRack_
	- TubeRackSpecs_
	- TubeSpecs_
	- User_
	- Well_
	- WellSpecs_


Projects and Administration
...........................

.. currentmodule:: thelma.entities.project
.. _Project:
.. autoclass:: Project

.. currentmodule:: thelma.entities.subproject
.. _Subproject:
.. autoclass:: Subproject

.. currentmodule:: thelma.entities.user
.. _User:
.. autoclass:: User

.. currentmodule:: thelma.entities.job
.. _Job:
.. autoclass:: Job

.. _JobType:
.. autoclass:: JobType

Experiments
...........

.. currentmodule:: thelma.entities.experiment
.. _ExperimentMetaData:
.. autoclass:: ExperimentMetaData

.. _ExperimentDesign:
.. autoclass:: ExperimentDesign

.. _Experiment:
.. autoclass:: Experiment

.. _ExperimentDesignRack:
.. autoclass:: ExperimentDesignRack

.. _ExperimentRack:
.. autoclass:: ExperimentRack

.. currentmodule:: thelma.entities.sample
.. _Sample:
.. autoclass:: Sample

.. _SampleMolecule:
.. autoclass:: SampleMolecule

.. currentmodule:: thelma.entities.iso
.. _IsoRequest:
.. autoclass:: IsoRequest

.. _Iso:
.. autoclass:: Iso

.. _IsoPosition:
.. autoclass:: IsoPosition

	There are also several subclasses of :class:`IsoPosition` that
	mainly serve as :ref:`marker classes <isopos>`.

.. currentmodule:: thelma.entities.stockinfo
.. _StockInfo:
.. autoclass:: StockInfo


Genes and Targets
.................

.. currentmodule:: thelma.entities.gene
.. _Gene:
.. autoclass:: Gene

.. _Transcript:
.. autoclass:: Transcript

.. _Target:
.. autoclass:: Target

.. _TargetSet:
.. autoclass:: TargetSet

.. currentmodule:: thelma.entities.species
.. _Species:
.. autoclass:: Species


Tagging
.......

.. currentmodule:: thelma.entities.tagging
.. _Tag:
.. autoclass:: Tag

.. _Tagging:
.. autoclass:: Tagging

.. _Tagged:
.. autoclass:: Tagged

.. _TaggedRackPositionSet:
.. autoclass:: TaggedRackPositionSet

Locations
.........

.. currentmodule:: thelma.entities.location
.. _BarcodedLocation:
.. autoclass:: BarcodedLocation

.. _BarcodedLocationType:
.. autoclass:: BarcodedLocationType

.. currentmodule:: thelma.entities.container
.. _ContainerLocation:
.. autoclass:: ContainerLocation

.. currentmodule:: thelma.entities.rack
.. _RackPosition:
.. autoclass:: RackPosition

.. _RackPositionSet:
.. autoclass:: RackPositionSet

.. currentmodule:: thelma.entities.racklayout
.. _RackLayout:
.. autoclass:: RackLayout

.. currentmodule:: thelma.entities.iso
.. _IsoRackLayout:
.. autoclass:: IsoRackLayout

Vessels and Vessel Types
........................

.. currentmodule:: thelma.entities.rack
.. _Rack:
.. autoclass:: Rack

.. _RackShape:
.. autoclass:: RackShape

.. _RackSpecs:
.. autoclass:: RackSpecs

.. currentmodule:: thelma.entities.container
.. _Container:
.. autoclass:: Container

.. _ContainerSpecs:
.. autoclass:: ContainerSpecs

.. currentmodule:: thelma.entities.rack
.. _Plate:
.. autoclass:: Plate

.. _PlateSpecs:
.. autoclass:: PlateSpecs

.. _TubeRack:
.. autoclass:: TubeRack

.. _TubeRackSpecs:
.. autoclass:: TubeRackSpecs

.. currentmodule:: thelma.entities.container
.. _Tube:
.. autoclass:: Tube

.. _TubeSpecs:
.. autoclass:: TubeSpecs

.. _Well:
.. autoclass:: Well

.. _WellSpecs:
.. autoclass:: WellSpecs


Molecule Designs and Modifications
..................................

.. currentmodule:: thelma.entities.sequence
.. _Sequence:
.. autoclass:: Sequence
	:members:

	There are also several subclasses of :class:`Sequence` that
	mainly serve as :ref:`marker classes <smc>`.

.. currentmodule:: thelma.entities.sample
.. _Molecule:
.. autoclass:: Molecule

.. currentmodule:: thelma.entities.moleculetype
.. _MoleculeType:
.. autoclass:: MoleculeType

.. currentmodule:: thelma.entities.moleculemodification
.. _MoleculeModification:
.. autoclass:: MoleculeModification

.. currentmodule:: thelma.entities.moleculedesign
.. _MoleculeDesign:
.. autoclass:: MoleculeDesign
	:members:

	There are also several subclasses of :class:`MoleculeDesign` that
	mainly serve as :ref:`marker classes <mdmc>`.

.. _MoleculeDesignSet:
.. autoclass:: thelma.entities.moleculedesign.MoleculeDesignSet

Marker Classes
..............

.. currentmodule:: thelma.entities.iso

.. _isopos:

Subclasses of :class:`thelma.entities.iso.IsoPosition`:

.. autoclass:: FixedIsoPosition

.. autoclass:: FloatingIsoPosition

.. autoclass:: EmptyIsoPosition


.. currentmodule:: thelma.entities.sequence

.. _smc:

Subclasses of :class:`thelma.entities.sequence.Sequence`:

.. autoclass:: DnaSequence

.. autoclass:: RnaSequence


.. currentmodule:: thelma.entities.moleculedesign

.. _mdmc:

Subclasses of :class:`thelma.entities.moleculedesign.MoleculeDesign`:

.. autoclass:: AmpliconDesign

.. autoclass:: AntiMirDesign

.. autoclass:: ClonedDsDNADesign

.. autoclass:: CompoundDesign

.. autoclass:: DoubleStrandedDesign

.. autoclass:: EsiRNADesign

.. autoclass:: GoldDesign

.. autoclass:: LongDoubleStrandedRNADesign

.. autoclass:: MiRNAInhibitorDesign

.. autoclass:: MiRNAMimicDesign

.. autoclass:: SingleStrandedDesign

.. autoclass:: SingleStrandedDNADesign

.. autoclass:: SingleStrandedRNADesign

.. autoclass:: SiRNADesign

.. autoclass:: TitanDesign


Others
......

.. currentmodule:: thelma.entities.device
.. _Device:
.. autoclass:: Device

.. _DeviceType:
.. autoclass:: DeviceType

.. currentmodule:: thelma.entities.status
.. _ItemStatus:
.. autoclass:: ItemStatus

.. currentmodule:: thelma.entities.organization
.. _Organization:
.. autoclass:: Organization


===============
Base Interfaces
===============

.. currentmodule:: thelma.entities.interfaces

.. autoclass:: IEntity


=============================
Utility Functions and Classes
=============================

.. currentmodule:: thelma.entities.utils

.. autofunction:: get_aggregate

.. autofunction:: get_related_aggregate

.. autofunction:: label_from_number

.. autofunction:: number_from_label

.. autofunction:: slug_from_string

.. autofunction:: slug_from_integer

.. currentmodule:: thelma.entities.rack
.. autofunction:: encode_rack_position_set

.. currentmodule:: thelma.entities.utils
.. autoclass:: BinaryRunLengthEncoder

.. currentmodule:: thelma.entities.rack
.. autoclass:: RackShapeFactory

.. autoclass:: RackPositionFactory


Aliases
.......

.. currentmodule:: thelma.entities.rack

.. autofunction:: rack_shape_from_rows_columns

.. function:: position_from_label(label)

	An alias for
	:func:`RackPositionFactory.position_from_label`

.. function:: position_from_row_column(row, column)

	An alias for
	:func:`RackPositionFactory.position_from_row_column`

.. function:: position_from_row_index_column_index(row_index, column_index)

	An alias for
	:func:`RackPositionFactory.position_from_row_index_column_index`