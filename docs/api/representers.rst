.. _representers_package:

Representers
------------

Representers perform the serialization and deserialization of
:doc:`resources <resources>`, i.e. they convert resources into representations
and vice versa.

   - `Representer Base Classes`_
   - `Representer Interfaces`_
   - `Attributes`_
   - `Utility Methods`_
   - `Configuration`_
   - `Specific Representation Type: Atom Representations`_
   - `Specific Representation Type: CSV Representations`_
   - `Specific Representation Type: XML Representations`_

Representer Base Classes
........................

.. currentmodule:: thelma.resources.representers.base

.. autoclass:: Representer

.. autoclass:: DataElementRegistry

.. autoclass:: ResourceRepresenter

.. autoclass:: DataElement

.. autoclass:: LinkedDataElement

.. autoclass:: RepresentationParser

.. autoclass:: RepresentationGenerator

.. autoclass:: MetaRepresenterConfiguration

.. autoclass:: RepresenterConfiguration

Representer Interfaces
......................

.. currentmodule:: thelma.resources.representers.interfaces

.. autoclass:: ISerializer

.. autoclass:: IDeSerializer

.. autoclass:: IRepresenter

.. autoclass:: IResourceRepresenter

.. autoclass:: IMemberResourceRepresenter

.. autoclass:: ICollectionResourceRepresenter

.. autoclass:: IDataElement

.. autoclass:: IDataElementRegistry

.. autoclass:: ILinkedDataElement

.. autoclass:: ICustomDataElement

Attributes
..........

.. currentmodule:: thelma.resources.representers.attributes

.. autoclass:: ResourceAttributeTypes

.. autoclass:: MappedAttribute

Utility Methods
...............

.. currentmodule:: thelma.resources.representers.utils

.. autofunction:: as_representer

.. autofunction:: get_data_element_registry

Configuration
.............

Explain ...

Specific Representation Type: Atom Representations
..................................................

.. currentmodule:: thelma.resources.representers.atom

.. autoclass:: AtomResourceRepresenter

.. currentmodule:: thelma.resources.representers.base

.. function:: resource_adapter

      An alias for :func:`AtomResourceRepresenter.create_from_resource` (which
      is the inherited :func:`ResourceRepresenter.create_from_resource`).

.. currentmodule:: thelma.resources.representers.xml

.. class:: AtomDataElementRegistry

      An alias for :class:`XmlDataElementRegistry`

.. class:: AtomRepresenterConfiguration

      An alias for :class:`XmlRepresenterConfiguration`

Specific Representation Type: CSV Representations
.................................................

.. currentmodule:: thelma.resources.representers.csv

.. autoclass:: CsvRepresentationParser

.. autoclass:: CsvRepresentationGenerator

.. autoclass:: CsvResourceRepresenter

.. currentmodule:: thelma.resources.representers.base

.. function:: resource_adapter

      An alias for :func:`CsvResourceRepresenter.create_from_resource`
      (which is the inherited :func:`ResourceRepresenter.create_from_resource`).

.. currentmodule:: thelma.resources.representers.csv

.. autoclass:: CsvDataElement

.. autoclass:: CsvLinkedDataElement

.. autoclass:: CsvDataElementRegistry

.. autoclass:: MetaCsvRepresenterConfiguration

.. autoclass:: CsvRepresenterConfiguration


Specific Representation Type: XML Representations
.................................................

.. currentmodule:: thelma.resources.representers.xml

.. autoclass:: IConverter

.. autoclass:: NoOpConverter

.. autoclass:: XmlRepresentationParser

.. autoclass:: XmlRepresentationGenerator

.. autoclass:: XmlResourceRepresenter
   :members: create_from_resource

.. currentmodule:: thelma.resources.representers.base

.. function:: resource_adapter

      An alias for :func:`XmlResourceRepresenter.create_from_resource`
      (which is the inherited :func:`ResourceRepresenter.create_from_resource`).

.. currentmodule:: thelma.resources.representers.xml

.. autoclass:: XmlMappedAttribute

.. autoclass:: XmlDataElement

.. autoclass:: XmlLinkedDataElement

.. autoclass:: XmlDataElementRegistry

.. autoclass:: MetaXmlRepresenterConfiguration

.. autoclass:: XmlRepresenterConfiguration
