Unit Test Base Classes
----------------------

Unit Test Base and Helper Classes for TheLMA are found in :mod:`thelma.testing`.
The unit tests use *Nose* as plugin.

For detailed instructions of what to regard when implenting a unit test,
read the :doc:`How to Implement Unit Tests <../devguide/unittests>` section,
please.

General Base Classes
....................

.. currentmodule:: thelma.testing

.. autoclass:: ThelmaNosePlugin

.. autoclass:: Pep8CompliantTestCase

.. autoclass:: BaseTestCase

.. autoclass:: DummyModule

.. autoclass:: DummyContext

.. autofunction:: elapsed


Base Classes for Specific Tasks
...............................

.. autoclass:: DbTestCase
   :exclude-members: set_up, tear_down

   .. automethod:: set_up
   .. automethod:: tear_down
   .. automethod:: _test_model_attributes
   .. automethod:: _compare_attributes

.. autoclass:: ModelTestCase
   :exclude-members: set_up, tear_down

   .. automethod:: set_up
   .. automethod:: tear_down
   .. automethod:: _test_attributes

   Furthermore there are variuos convenience methods to create
   model objects of different classes:

   .. method:: _create_experiment(design_label='experiment_design_label')
   .. method:: _create_experiment_design_rack()
   .. method:: _create_experiment_metadata(experiment_metadata_name)
   .. method:: _create_experiment_rack()
   .. method:: _create_organization(organization_id)
   .. method:: _create_project(project_id)
   .. method:: _create_rack_layout()
   .. method:: _create_rack_position_set(additional_position=None)
   .. method:: _create_iso_request(iso_request_id)
   .. method:: _create_tag_set(additional_value=None)
   .. method:: _create_target_set()
   .. method:: _create_tprs(tags=None, user=None, positions=None)
   .. method:: _create_tube_rack(rack_id)
   .. method:: _create_transcript(accession)
   .. method:: _create_user(user_id)

.. autoclass:: ResourceTestCase

.. autoclass:: FunctionalTestCase


