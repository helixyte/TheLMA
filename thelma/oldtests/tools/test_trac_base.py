"""
Tests for trac base classes.

AAB Aug 15, 2011
"""
from pyramid.threadlocal import get_current_registry
from thelma.interfaces import ITractor
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase
from tractor.api import DummyTractor
from tractor.api import TractorApi


class TractorLoadTestCase(ToolsAndUtilsTestCase):

    def test_make_api(self):
        reg = get_current_registry()
        tractor_api = reg.getUtility(ITractor)
        self.assert_true(isinstance(tractor_api, TractorApi))
        self.assert_true(isinstance(tractor_api, DummyTractor))
