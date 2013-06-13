"""
Base classes and utils for tests involved in pool stock sample creation ISOs.

AAB
"""
from thelma.automation.tools.poolcreation.generation \
    import PoolCreationLibraryGenerator
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import FileReadingTestCase

class PoolCreationTestCase(FileReadingTestCase):

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = None
        self.VALID_FILE = None
        self.library = None
        self.requester = get_user('brehm')
        self.iso_request_label = None
        self.target_volume = None
        self.target_concentration = None

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.library
        del self.requester
        del self.iso_request_label
        del self.target_volume
        del self.target_concentration

    def _continue_setup(self, file_name=None):
        FileReadingTestCase._continue_setup(self, file_name=file_name)
        self._create_library()

    def _create_library(self):
        generator = PoolCreationLibraryGenerator(
                             iso_request_label=self.iso_request_label,
                             stream=self.stream, requester=self.requester,
                             target_volume=self.target_volume,
                             target_concentration=self.target_concentration)
        self.library = generator.get_result()
        self.assert_is_not_none(self.library)
