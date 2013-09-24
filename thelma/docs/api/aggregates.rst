.. _aggregates_package:

Aggregates
----------

An aggregate provides a wrapper around a set of entities (:doc:`models <models>`)
of a specific type which are held in some repository. The wrapped entity set
may be a \"root\" set of all entities in the repository or a "related" set
defined by a relationship to some other entity.

Aggregates supports filtering, sorting, counting and iteration as well as
retrieving, adding and removing entities.

The actual work is delegated to an instance of to allow for
runtime selection of :ref:`implementations <implementations>`.

.. currentmodule:: thelma.models.aggregates

Aggregates and Aggregate Interfaces
...................................

Aggregates must inherit from :class:`Aggregate`.

When implementing a new aggregate class, make sure to define the following
attributes:

   :attr:`entity_class`
      The model/entity class the aggregate class is designed for.
   :attr:`name`
      The name of the aggregate class.
   :attr:`default_implementation`
      The default aggregate mplementation (:class:`AggregateImpl`)
      for this aggregate class.

.. currentmodule: thelma.models.interfaces

Furthermore, they must implement an marker interface that inherits from
:class:`IAggregate`:

.. autoclass:: IAggregate


.. currentmodule:: thelma.models.aggregates

The following sections provides the documentation of the aggregatebase class.
However, most of its methods are actually delegated by to the aggregates
:ref:`implementation <implementations>`.

.. autoclass:: Aggregate


.. _implementations:

Aggregate Implementations
.........................

These are the aggregate implementation base classes:

   - :class:`AggregateImpl`
   - :class:`MemoryAggregateImpl`
   - :class:`OrmAggregateImpl`

.. autoclass:: AggregateImpl

.. autoclass:: MemoryAggregateImpl

.. autoclass:: OrmAggregateImpl
