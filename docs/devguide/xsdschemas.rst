.. _schemata_package:

How to Create an XSD Schema for a Resource
------------------------------------------

The XSD schema used by TheLMA are stored in :mod:`thelma.schemata`.
XSD schemas presenting a :doc:`resource <../api/resources>` can be creating
using the :mod:`_template.xsd` file located in the same folder.

Let us assume the following :doc:`model <../api/models>` class:

*Example*: ::

   from rest_app.models.base import Entity

   class Example(Entity):

      def __init__(self, name, things):
         Entity.__init__(self)
         self.name = name # string
         self.thing = thing # 'Thing' object

A complete schema defines the following issues:

   - :ref:`namespaces <ns>`
   - :ref:`member type <single_t>`
   - :ref:`collection type <collection_t>`
   - :ref:`link type <link_t>`
   - :ref:`member element <single_e>`
   - :ref:`collection element <collection_e>`
   - :ref:`link type element <link_e>`

The complete example schema is present on the :ref:`bottom <complete>`

.. _ns:

Namespaces
..........

The XSD must import the :mod:`Shared.xsd` schema (*lines 9-13*) plus
all other foreign schema required (*lines 9-18*) whose elements it
want to reference (*here: \'things\' in lines 14-18*).
The namespace prefixes used the reference the different namespaces
(*lines 5-7*) should be kept constant within the application.
There is no reason to incite more confusion than necessary.

*Example:*

.. highlight:: xml

.. code-block:: xml
   :linenos:

   <schema
       targetNamespace="http://schemata.cenix-bioscience.com/example"
       elementFormDefault="qualified"
       xmlns="http://www.w3.org/2001/XMLSchema"
       xmlns:e="http://schemata.cenix-bioscience.com/example"
       xmlns:t="http://schemata.cenix-bioscience.com/thing"
       xmlns:sh="http://schemata.cenix-bioscience.com/shared"
   >
       <import
           schemaLocation="Shared.xsd"
           namespace="http://schemata.cenix-bioscience.com/shared"
       >
       </import>
       <import
           schemaLocation="Thing.xsd"
           namespace="http://schemata.cenix-bioscience.com/thing"
       >
       </import>

.. _single_t:

Member Type
...........

This XML element type definition is supposed to present a single
:doc:`member resource <../api/resources>`. Line 2 specifies the name
of the element type.
The you need to define child element presenting the attributes of the
underlying resource.

:Note: Unlike the :ref:`link type <link_t>` this element is not pointing onto
       an resource URL. Instead it directly presents the resources attributes.

Child elements for **atomic attributes** (*lines 9-12*) can be defined in the
schema directly. Define the tag name (*line 10*), the atomic type (*line 11*)
and constraints, if applicable.

Attributes that are in fact **other resources** should be defined in own
XSD schema and only be references here (see *lines 14-18*). Also here it
is possible to add constraints (e.g. *lines 15 and 16*).

*Example:*

.. code-block:: xml
   :linenos:

   <complexType
        name="ExampleType"
    >
        <choice>
            <element
                ref="e:link"
            >
            </element>
            <element
                name="example"
                type="string"
            >
            </element>
            <element
                ref="t:thing"
                minOccurs="1"
                maxOccurs="1"
            ></element>
        </choice>
    </complexType>

.. _collection_t:

Collection Type
...............

This XML element type presents a :doc:`collection <../api/resources>` of
resources. At this, it does not define whether the member elements are
:ref:`link type <link_t>` (*lines 9-13*)
or :ref:`data (member) type <single_t>` (*lines 14-18*) elements or mixed.

Specify the name of the element type (*line 2*) and the :attr:`ref` attributes
of the :ref:`member element <single_e>` (*line 15*) and the
:ref:`link element <link_e>` (*line 10*) reference.

*Example:*


.. code-block:: xml
   :linenos:

    <complexType
        name="ExampleCollectionType"
    >
        <sequence
            maxOccurs="unbounded"
            minOccurs="0"
        >
            <choice>
                <element
                    ref="e:link"
                    maxOccurs="1"
                    minOccurs="1"
                ></element>
                <element
                    ref="e:example"
                    maxOccurs="1"
                    minOccurs="1"
                ></element>
            </choice>
        </sequence>
    </complexType>


.. _link_t:

Link Type
.........

Links can point to both member an collection :doc:`resources <../api/resources>`.
However, the links defined by this element type always point to single member,
but unlike the :ref:`member type <single_t>`, the link type is not presenting
the actual resource data, but rather names a reference URL.

The link type inherits from the link type defined in :mod:`Shared.xsd` that
defines all required attributes except the :attr:`rel` one (*lines 8-12*).
This attribute determines the :doc:`resource class <../api/resources>` of
the referenced entity.

Modify the :attr:`fixed` attribute (*line 11*) and name the type (*line 2*).

*Example:*

.. code-block:: xml
   :linenos:

    <complexType
        name="ExampleLinkType"
    >
        <complexContent>
            <restriction
                base="sh:LinkType"
            >
                <attribute
                    name="rel"
                    type="string"
                    fixed="http://relations.cenix-bioscience.com/example"
                ></attribute>
            </restriction>
        </complexContent>
    </complexType>

.. _single_e:

Member Element
..............

Here, we define an :ref:`member type <single_t>` element that can be
referenced by other XSD schemas.

Define the tag name of the element as :attr:`name` attribute (*line 2*) and
enter the name of the :ref:`member type <single_t>` (including
:ref:`namespace prefix <ns>`) as :attr:`type` (*line 3*).


*Example:*

.. code-block:: xml
   :linenos:

    <element
        name="example"
        type="e:ExampleType"
    >
    </element>

.. _collection_e:

Collection Element
..................

Here, we define an :ref:`collection type <collection_t>` element that can be
referenced by other XSD schemas.

Define the tag name of the element as :attr:`name` attribute (*line 2*) and
enter the name of the :ref:`colllection type <collection_t>` (including
:ref:`namespace prefix <ns>`) as :attr:`type` (*line 3*).


*Example:*

.. code-block:: xml
   :linenos:

    <element
        name="examples"
        type="e:ExampleCollectionType"
    >
    </element>


.. _link_e:

Link Element
............

Here, we define an :ref:`link type <link_t>` element that can be
referenced by other XSD schemas.

Here, you just need to enter the name of the
:ref:`link type <link_t>` (including :ref:`namespace prefix <ns>`) as
:attr:`type` (*line 3*).


*Example:*

.. code-block:: xml
   :linenos:

    <element
        name="link"
        type="e:ExampleLinkType"
    >
    </element>


.. _complete:

Complete Schema
...............

The complete schema could look like this:

*Example:*

.. code-block:: xml

   <?xml version="1.0" encoding="UTF-8"?>

   <!-- Root Element and Namespaces -->

   <schema
       targetNamespace="http://schemata.cenix-bioscience.com/example"
       elementFormDefault="qualified"
       xmlns="http://www.w3.org/2001/XMLSchema"
       xmlns:e="http://schemata.cenix-bioscience.com/example"
       xmlns:t="http://schemata.cenix-bioscience.com/thing"
       xmlns:sh="http://schemata.cenix-bioscience.com/shared"
   >


      <!-- Imports -->

       <import
           schemaLocation="Shared.xsd"
           namespace="http://schemata.cenix-bioscience.com/shared"
       >
       </import>
       <import
           schemaLocation="Thing.xsd"
           namespace="http://schemata.cenix-bioscience.com/thing"
       >
       </import>


      <!-- Member Type -->

      <complexType
           name="ExampleType"
       >
           <choice>
               <element
                   ref="e:link"
               >
               </element>
               <element
                   name="example"
                   type="string"
               >
               </element>
               <element
                   ref="t:thing"
                   minOccurs="1"
                   maxOccurs="1"
               ></element>
           </choice>
       </complexType>


      <!-- Collection Type -->

       <complexType
           name="ExampleCollectionType"
       >
           <sequence
               maxOccurs="unbounded"
               minOccurs="0"
           >
               <choice>
                   <element
                       ref="e:link"
                       maxOccurs="1"
                       minOccurs="1"
                   ></element>
                   <element
                       ref="e:example"
                       maxOccurs="1"
                       minOccurs="1"
                   ></element>
               </choice>
           </sequence>
       </complexType>


      <!-- Link Type -->

       <complexType
           name="ExampleLinkType"
       >
           <complexContent>
               <restriction
                   base="sh:LinkType"
               >
                   <attribute
                       name="rel"
                       type="string"
                       fixed="http://relations.cenix-bioscience.com/example"
                   ></attribute>
               </restriction>
           </complexContent>
       </complexType>


      <!-- Member Element -->

       <element
           name="example"
           type="f:ExampleType"
       >
       </element>


      <!-- Collection Element -->

       <element
           name="examples"
           type="e:ExampleCollectionType"
       >
       </element>


      <!-- Link Element -->

       <element
           name="link"
           type="e:ExampleLinkType"
       >
       </element>

   </schema>