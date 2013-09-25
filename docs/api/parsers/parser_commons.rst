.. _parsers_package:

Parser Commons
--------------

This page presents common classes used by parsers in TheLMA.

===============
Parsers Classes
===============

Parser Base Classes
###################

.. currentmodule:: thelma.parsers.implementation.base

.. autoclass:: BaseParser

.. currentmodule:: thelma.parsers.implementation.excel

.. autoclass:: ExcelFileParser

.. currentmodule:: thelma.parsers.implementation.base

.. autoclass:: ParsingContainer

.. currentmodule:: thelma.parsers.implementation.excel

.. autoclass:: ExcelParsingContainer

   .. automethod:: _get_cell_value
   .. automethod:: _check_cell_value_for_residues
   .. automethod:: _create_error
   .. automethod:: _create_debug_info
   .. automethod:: _create_info

Specific Parsers
################

- :doc:`The Experimental Meta Data Excel File Parser <experimental_meta_data>`
- :doc:`The ISO Excel File Parser <iso_parser>`

=======
Logging
=======

.. automodule:: thelma.parsers.errors
	:members:

	.. autoclass:: ParsingLog
		:members:

	.. autoclass:: ParsingLogEvent
		:members:

	.. autoclass:: ExcelFileParsingLogEvent