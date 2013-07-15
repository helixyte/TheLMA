How to Implement Unit Tests
---------------------------

This documentation chapter needs to be completed.


Models
......

Unit tests for models should inherit from the
:class:`thelma.testing.ModelTestCase` superclass.
The :func:`setup` and :func:`tear_down` functions need not to be overwritten.
The unit test should check the following issues:

   - Correct instantiation or, in case of abstract superclasses, exception
     raising
   - Correct attribute instantiation (actual and expected attribute values
     can be compared using :func:`_test_attributes`).
   - The slug, if appicable.
   - Equality and inequality of objects (including inequality of object
     of different classes).
   - Additional class functions, if applicable.
   - ...