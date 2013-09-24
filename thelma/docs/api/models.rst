.. _models_package:

Models
------

=============
Model Classes
=============

Models represent entities from the database. All entity classes inherit
from the following superclass:

	.. currentmodule:: thelma.models.base

	.. class:: Entity

		The Abstract base class for all model entities. It implements the
		BFG marker interface :class:`IEntity`.

Furthermore, each model class implements a particular marker interface for
BFG. The marker interface a usually called \'I[*class name*]\'.
All models that can  be as resources as well must have a so-called \'slug\',
that is a :class:`string` identifier that can be used in an URL.

TheLMA knows the following models (sorted by application area):

	- `Projects and Administration`_
	- `Experiments`_
	- `Genes and Targets`_
	- `Tagging`_
	- `Locations`_
	- `Vessels and Vessel Types`_
	- `Molecule Designs and Modifications`_
	- `Marker Classes`_
	- `Others`_

All model classes in alphabetical order:

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

.. currentmodule:: thelma.models.project
.. _Project:
.. autoclass:: Project

.. currentmodule:: thelma.models.subproject
.. _Subproject:
.. autoclass:: Subproject

.. currentmodule:: thelma.models.user
.. _User:
.. autoclass:: User

.. currentmodule:: thelma.models.job
.. _Job:
.. autoclass:: Job

.. _JobType:
.. autoclass:: JobType

Experiments
...........

.. currentmodule:: thelma.models.experiment
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

.. currentmodule:: thelma.models.sample
.. _Sample:
.. autoclass:: Sample

.. _SampleMolecule:
.. autoclass:: SampleMolecule

.. currentmodule:: thelma.models.iso
.. _IsoRequest:
.. autoclass:: IsoRequest

.. _Iso:
.. autoclass:: Iso

.. _IsoPosition:
.. autoclass:: IsoPosition

	There are also several subclasses of :class:`IsoPosition` that
	mainly serve as :ref:`marker classes <isopos>`.

.. currentmodule:: thelma.models.stockinfo
.. _StockInfo:
.. autoclass:: StockInfo


Genes and Targets
.................

.. currentmodule:: thelma.models.gene
.. _Gene:
.. autoclass:: Gene

.. _Transcript:
.. autoclass:: Transcript

.. _Target:
.. autoclass:: Target

.. _TargetSet:
.. autoclass:: TargetSet

.. currentmodule:: thelma.models.species
.. _Species:
.. autoclass:: Species


Tagging
.......

.. currentmodule:: thelma.models.tagging
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

.. currentmodule:: thelma.models.location
.. _BarcodedLocation:
.. autoclass:: BarcodedLocation

.. _BarcodedLocationType:
.. autoclass:: BarcodedLocationType

.. currentmodule:: thelma.models.container
.. _ContainerLocation:
.. autoclass:: ContainerLocation

.. currentmodule:: thelma.models.rack
.. _RackPosition:
.. autoclass:: RackPosition

.. _RackPositionSet:
.. autoclass:: RackPositionSet

.. currentmodule:: thelma.models.racklayout
.. _RackLayout:
.. autoclass:: RackLayout

.. currentmodule:: thelma.models.iso
.. _IsoRackLayout:
.. autoclass:: IsoRackLayout

Vessels and Vessel Types
........................

.. currentmodule:: thelma.models.rack
.. _Rack:
.. autoclass:: Rack

.. _RackShape:
.. autoclass:: RackShape

.. _RackSpecs:
.. autoclass:: RackSpecs

.. currentmodule:: thelma.models.container
.. _Container:
.. autoclass:: Container

.. _ContainerSpecs:
.. autoclass:: ContainerSpecs

.. currentmodule:: thelma.models.rack
.. _Plate:
.. autoclass:: Plate

.. _PlateSpecs:
.. autoclass:: PlateSpecs

.. _TubeRack:
.. autoclass:: TubeRack

.. _TubeRackSpecs:
.. autoclass:: TubeRackSpecs

.. currentmodule:: thelma.models.container
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

.. currentmodule:: thelma.models.sequence
.. _Sequence:
.. autoclass:: Sequence
	:members:

	There are also several subclasses of :class:`Sequence` that
	mainly serve as :ref:`marker classes <smc>`.

.. currentmodule:: thelma.models.sample
.. _Molecule:
.. autoclass:: Molecule

.. currentmodule:: thelma.models.moleculetype
.. _MoleculeType:
.. autoclass:: MoleculeType

.. currentmodule:: thelma.models.moleculemodification
.. _MoleculeModification:
.. autoclass:: MoleculeModification

.. currentmodule:: thelma.models.moleculedesign
.. _MoleculeDesign:
.. autoclass:: MoleculeDesign
	:members:

	There are also several subclasses of :class:`MoleculeDesign` that
	mainly serve as :ref:`marker classes <mdmc>`.

.. _MoleculeDesignSet:
.. autoclass:: thelma.models.moleculedesign.MoleculeDesignSet

Marker Classes
..............

.. currentmodule:: thelma.models.iso

.. _isopos:

Subclasses of :class:`thelma.models.iso.IsoPosition`:

.. autoclass:: FixedIsoPosition

.. autoclass:: FloatingIsoPosition

.. autoclass:: EmptyIsoPosition


.. currentmodule:: thelma.models.sequence

.. _smc:

Subclasses of :class:`thelma.models.sequence.Sequence`:

.. autoclass:: DnaSequence

.. autoclass:: RnaSequence


.. currentmodule:: thelma.models.moleculedesign

.. _mdmc:

Subclasses of :class:`thelma.models.moleculedesign.MoleculeDesign`:

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

.. currentmodule:: thelma.models.device
.. _Device:
.. autoclass:: Device

.. _DeviceType:
.. autoclass:: DeviceType

.. currentmodule:: thelma.models.status
.. _ItemStatus:
.. autoclass:: ItemStatus

.. currentmodule:: thelma.models.organization
.. _Organization:
.. autoclass:: Organization


===============
Base Interfaces
===============

.. currentmodule:: thelma.models.interfaces

.. autoclass:: IEntity


=============================
Utility Functions and Classes
=============================

.. currentmodule:: thelma.models.utils

.. autofunction:: get_aggregate

.. autofunction:: get_related_aggregate

.. autofunction:: label_from_number

.. autofunction:: number_from_label

.. autofunction:: slug_from_string

.. autofunction:: slug_from_integer

.. currentmodule:: thelma.models.rack
.. autofunction:: encode_rack_position_set

.. currentmodule:: thelma.models.utils
.. autoclass:: BinaryRunLengthEncoder

.. currentmodule:: thelma.models.rack
.. autoclass:: RackShapeFactory

.. autoclass:: RackPositionFactory


Aliases
.......

.. currentmodule:: thelma.models.rack

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