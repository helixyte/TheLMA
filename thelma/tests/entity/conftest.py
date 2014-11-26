"""
"""
import pytest


__docformat__ = 'reStructuredText en'
__all__ = []


@pytest.mark.usefixtures('session_entity_repo', 'session')
class TestEntityBase(object):
    """
    Base class for classes that test entities.
    """
    package_name = 'thelma'
    ini_section_name = 'app:thelma'


