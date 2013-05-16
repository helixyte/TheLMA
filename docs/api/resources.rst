.. _resources_package:

Resources
---------

Resources contain the business logic required for the exposure of a
:doc:`model <models>` or an :doc:`aggregate <aggregates>` of models.
In this chapter you will find more information about:

   - `Resource Base Classes`_
   - `Base Interfaces`_
   - `Descriptors`_

A resource can either represent an single model.
In this case it is called **Member**. On the other hand, it may contain several
member resources of the same type. This type of resource is called
**Collection**.

Resource Base Classes
.....................

.. currentmodule:: thelma.resources.base

.. autoclass:: Link

.. autoclass:: Resource

.. autoclass:: Member

.. autoclass:: Collection

.. autoclass:: Service


.. _interfaces:

Base Interfaces
...............

Resources must implement a number of interfaces and marker interfaces
in order to be regocnized by the BFG framework. The following section
describes the abstract interfaces superclasses used in TheLMA.

.. currentmodule:: thelma.resources.interfaces

.. autoclass:: ILocationAware

.. autoclass:: ITraversable

.. autoclass:: IResource

.. autoclass:: IMemberResource

.. autoclass:: ICollectionResource


Descriptors
...........

Descriptors are used to associate resource attributes with
:doc:`model <models>` attributes.

.. currentmodule:: thelma.resources.descriptors

.. autoclass:: entity_attribute_base

.. autoclass:: entity_atomic_attribute

.. autoclass:: entity_member_attribute

.. autoclass:: root_entities_attribute

.. autoclass:: related_entities_attribute