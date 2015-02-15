How to Add a New Plugin
-----------------------

Plugin must exhibit implementations for the different layers of the pyramid
framework, i.e.:

   1. :ref:`Entities <entity>` and :ref:`aggregates <aggregate>` for the
      *entity* layer

   2. :ref:`DB schemes <schema>` and :ref:`mappers <mapper>` for
      *database access*

   3. :ref:`Resources and collections <resource>` for the *resource* layer

   4. :ref:`Representers <representer>` for the *representation* (including
      an :ref:`XSD Schema <xsd>`)

Furthermore all components must be :ref:`registered <registration>`,
:ref:`tested <test>` and :ref:`documented <documentation>`.


.. _entity:

1.) Implementing the Entity Class
.................................

The entity needs to be a subclass of :class:`thelma.entities.base.Entity`.
Furthermore, it must implement a marker interface. These interfaces
are, in the case of TheLMA, stored in a module called
:doc:`thelma.interfaces <../api/entitiess>`. They must be a subclass of
:class:`thelma.entities.interfaces.IEntity`.

*Example*: ::

   from rest_app.interfaces import IEntity

   class IExample(IEntity):
      """ No body required """

If the entity is to be represented as :ref:`resource <resource>`,
too, you have to specify an attribute called :attr:`slug`. The slug should
be a unique identifier for an objects of this class (within the namespace of all
objects of this class) that can be used as part of a URL as well.

:Note: Make sure to should overwrite the default built-in methods
       :func:`__eq__`, :func:`__ne__`, :func:`__str__` and :func:`__repr__`.

*Example*: ::

   from rest_app.interfaces import IExample

   class Example(Entity):
      implements(IExample)

      id = None
      slug = None
      name = None
      thing = None

      def __init__(self, name, things):
         Entity.__init__(self)
         self.name = name
         self.slug = self._create_slug(self.name)
         self.thing = thing

      def __eq__(self, other):
         return (isinstance(other, ItemStatus) and self.id == other.id)

      def __ne__(self, other):
         return not (self == other)

      def __str__(self):
         return self.id

      def __repr__(self):
         format = '<%s id: %s, name: %s, thing: %s>'
         params = (self.__class__.__name__, self.id, self.name, self.thing)
         return format % params

      def _create_slug(self, string):
         s = string.replace(' ', '-')
         s = s.replace('_', '-')
         s = s.lower()
         return s

.. _aggregate:


.. _schema:

2.) Implementing the DB Schema
..............................

The DB schema defines the database table associated with a class of
entities. The tables created mimic the tables of the database.

:Note: Instead of database table, you can also address a database view.

First, you have to implement a table factory function for the plugin.
Use :mod:`sqlalchemy` to specify column names, primary and foreign keys,
constraints, etc.

*Example*: ::

   from sqlalchemy import Table, Column, String, Integer, ForeignKey

   def create_table(metadata, thing_tbl):

      tbl = Table('example', metadata,
            Column('example_id', Integer, primary_key=True),
            Column('name', String(32), nullable=False),
            Column('thing_id', Integer,
                   ForeignKey(thing_tbl.c.thing_id))
            )
      return tbl

The factory function must then be called by the :func:`initialize_tables`
function in the :mod:`rest_app.db.schema.tables.__init__`, respectively,
the :mod:`rest_app.db.schema.views.__init__` module. Both functions are
indirectly by :mod:`rest_app.db.__init__` (via
:mod:`rest_app.db.schema.__init__`).

*Example*: ::

   from rest_app.db.schema.tables import thing, example

   def initialize_tables(metadata):
      thing_tbl = create_table(metadata)
      example_table = create_table(metadata, thing_tbl)

.. _mapper:

3.) Implementing the Mapper
...........................

Mappers map the columns of an :ref:`DB schema table <schema>` onto
the :ref:`entity <entity>` attributes.

Similar to the DB schema tables, you have to implement a factory function,
first. Use the module :mod:`sqlalchemy.orm` to do so.

:Note: Atomic attributes having the same name like the corresponding
       database table are mapped automatically and need not to be specified.

*Example*: ::

   from sqlalchemy.orm import mapper, relationship, synonym
   from rest_app.entities.example import Example
   from rest_app.entities.thing import Thing

   def create_mapper(example_tbl):

      m = mapper(Example, example_tbl,
         properties=
            dict(id=synonym('example_id'),
                 thing=relationship(Thing),
                 ),
         )
      return m

The factory function must then be called by the :func:`initialize_mappers`
function in the :mod:`rest_app.db.mappers.__init__` module. This method
in turn is called by application :mod:`db.__init__` module.

*Example*: ::

   from rest_app.db.mappers import example

   def initialize_mappers(tables):
      example.create_mapper(tables['example'])

.. _resource:

4.) Implementing the Resource Classes
.....................................

Resources contain the business logic required for the exposure of a
:ref:`entity <entity>`. A resource can either represent a single entity.
In this case it is called **Member**. On the other hand, it may contain several
member resources of the same type. This type of resource is called
**Collection**.

.. _mem_res:

I) Member Resources
+++++++++++++++++++

Member resources must be subclasses of :class:`thelma.resources.base.Member`.
They must implement a marker interface for BFG that inherits
from :class:`thelma.resources.interfaces.IMemberResource`. The interfaces
are, in the case of TheLMA, stored in a module called
:doc:`thelma.resources.interfaces <../api/resources>`.

*Example*: ::

   from rest_app.resources.interfaces import IMemberResource

   class IExampleMember(IMemberResource):
      """ No body required """

When implementing a member resource, make sure to specify the following two
attributes:

   :attr:`relation`
      This attributes the traversal path for resources of this class.
   :attr:`entity_class`
      The :ref:`entity class <entity>` this resource member class is
      associated with.

You then need to define the relations between the resource attributes and
the entity attributes. Use the predefined :doc:`descriptors <../api/resources>`
to do so.

Finally, you have to create an **adapter** for the BFG framework that points
to :func:`create_from_entity` method of the
:class:`thelma.resources.base.Member` superclass. This method creates
a resource from a given entity.

*Example*::

   from rest_app.resources.base import Member
   from rest_app.resources.interfaces import IExampleMember

   class ExampleMember(Member):
      implements(IExampleMember)

      relation = "%s/example" % RELATION_BASE_URL
      entity_class = Example

      name = entity_atomic_attribute('name')
      thing = entity_member_attribute('thing', collection_name='things')

   example_entity_adapter = ExampleMember.create_from_entity

.. _col_res:

II) Collection Resources
++++++++++++++++++++++++

Collection resources must be subclasses of
:class:`thelma.resources.base.Collection`.
They must implement a marker interface for BFG that inherits
from :class:`thelma.resources.interfaces.ICollectionResource`. The interfaces
are, in the case of TheLMA, stored in a module called
:doc:`thelma.resources.interfaces <../api/resources>`.

*Example*: ::

   from rest_app.resources.interfaces import ICollectionResource

   class IExampleCollection(ICollectionResource):
      """ No body required """

When implementing a collection resource, make sure to specify the following two
attributes:

   :attr:`member_resource_class`
      The class of the :ref:`member resources <mem_res>` contained
      in this collection.
   :attr:`title`
      The title with which collection objects are referenced.
   :attr:`base_collection_name`
      The name of the unfiltered \'root\' collection that contains all
      possible members of this collection class.
   :attr:`description`
      A description of the collection.
   :attr:`default_order` (optional)
      The default order of the collection\'s members.

Finally you have to create an **adapter** for the BFG framework that points
to :func:`create_from_aggregate` method of the
:class:`thelma.resources.base.Collection` superclass. This method creates
a collection from a given :ref:`aggregate <aggregate>`.

*Example*::

   from rest_app.resources.base import Collection
   from rest_app.resources.interfaces import IExampleCollection
   from rest_app.resources.example import ExampleMember
   from rest_app.sorting import SimpleOrder

   class ExampleCollection(Collection):
      implements(IExampleCollection)

      member_resource_class = ExampleMember
      title = 'Examples'
      base_collection_name = 'examples'

      description = 'Manage Example'
      default_order = SimpleOrder('name').reverse()

   examples_aggregate_adapter = ExampleCollection.create_from_aggregate

.. _xsd:

5. Defining an XSD Schema
.........................

XSD schemas define how the hiearchy and tag names of XML elements presenting
a :ref:`resource <resource>` object. The generation of XSD schemas is explained
in a :doc:`separate chapter <xsdschemas>`.

.. _representer:

6. Setting up Representers
..........................

Once you have created an :ref:`XML schema <xsd>` for the resource, you can
set up the representer. To this end, you have to add some classes in the
module :mod:`rest_app.resources.representers.config`.

First, you have to create some marker classes that migth also contain
information about attribute mapping:

*Example*::

   class _EXAMPLE(object):
       pass

   class EXAMPLE_MEMBER(_EXAMPLE):
       mapping = dict(label=dict(ignore=TRUE),)

   class EXAMPLE_COLLECTION(_EXAMPLE):
       pass

Second, we need to create class defining the namespace, the XSD schema location
and the global namespace prefix for the plugin.

*Example*::

   from rest_app.resources.representers.xml import XmlRepresenterConfiguration

   class _XML_EXAMPLE(XmlRepresenterConfiguration):
       xml_schema = 'thelma:schemata/Example.xsd'
       xml_ns = 'http://schemata.thelma.org/example'
       xml_prefix = 'e'

Finally, we need a set of classes containing the tag names for the root member
and collection type :doc:`XML elements <xsdschemas>` elements for this plugin
and (optional) further mappings.

*Example*::

   from rest_app.resources.representers.config import _XML_EXAMPLE, _XML_THING,
   from rest_app.resources.representers.config import EXAMPLE_MEMBER, EXAMPLE_COLLECTION

   class XML_EXAMPLE_MEMBER(_XML_EXAMPLE, EXAMPLE_MEMBER):
       xml_tag = 'example'
       mapping = dict(thing=dict(namespace=_XML_THING.xml_ns),)

   class XML_EXAMPLES_COLLECTION(_XML_EXAMPLE, EXAMPLE_COLLECTION):
       xml_tag = 'examples'


.. _registration:

7. Registration
...............

Finally, you have to register in the BFG framework. To this end, you have
to add the following declaration in :mod:`thelma.resources.configure.zcml`:

1. **tag name:** *member_resource*
      :attr:`resource` atrribute:
         name of the :ref:`member resource <mem_res>` class (relative path)

.. code-block:: xml

    <member_resource
        resource=".example.ExampleMember" />

2. **tag name:** *collection_resource*
      :attr:`resource` attribute:
         name of the :ref:`collection resource <col_res>` class
         (relative path)
      :attr:`aggregate` attribute:
         name of the :ref:`aggregate <aggregate>` class (absolute path)

.. code-block:: xml

    <collection_resource
        resource=".example.ExampleCollection"
        aggregate="thelma.entities.aggregates.ExampleAggregate" />

3. **tag name:** *representer*
      :attr:`for` attribute:
         name of the :ref:`member resource <mem_res>` class (relative path)
      :attr:`content_type` attribute:
         \'*thelma.mime.XmlMime*\'
      :attr:`configuration` attribute:
         name of the :ref:`member representer for XML <representer>`
         (relative path)

.. code-block:: xml

    <representer
        for=".example.ExampleMember"
        content_type="thelma.mime.XmlMime"
        configuration=".representers.config.XML_EXAMPLE_MEMBER" />

4. **tag name:** *representer*
      :attr:`for` attribute:
         name of the :ref:`collection resource <col_res>` class
         (relative path)
      :attr:`content_type` attribute:
         \'*thelma.mime.XmlMime*\'
      :attr:`configuration` attribute:
         name of the :ref:`collection representer for XML <representer>`
         (relative path)

.. code-block:: xml

    <representer
        for=".example.ExampleCollection"
        content_type="thelma.mime.XmlMime"
        configuration=".representers.config.XML_EXAMPLE_COLLECTION" />

5. **tag name:** *representer* (optional)
      :attr:`for` attribute:
         name of the :ref:`collection resource <col_res>` class
         (relative path) and
         name of the :ref:`collection resource <col_res>` class
         (relative path) separated by new line
      :attr:`content_type` attribute:
         \'*thelma.mime.CsvMime*\'

.. code-block:: xml

    <representer
        for=".example.ExampleCollection
             .example.ExampleMember"
        content_type="thelma.mime.CsvMime" />

.. _test:

8.) Unit Tests
..............

Implement :doc:`unit tests <unittests>` for the entity, resource,
the DB access and the representers.

.. _documentation:

9.) Documentation
..................

Do not forget to add a documentation for the plugin. In the case of
TheLMA you have to add a link to the reffering entity class in
*docs/api/entities.rst* (both in the alpabetical header section and
in the details section below).
