"""
:Date: 2011-05
:Author: AAB, berger at cenix-bioscience dot com

Parser handler base classes. Handlers initializes and run parsers and transform
their results into model entities, if the parser was completed successfully.
Handlers can also access the parsing message recordings.
"""

from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.base import BaseTool
from thelma.automation.utils.layouts import MoleculeDesignPoolParameters
from thelma.interfaces import IRackShape
from thelma.models.rack import RackPositionSet
from thelma.models.tagging import Tag


__docformat__ = 'reStructuredText en'
__all__ = ['BaseParserHandler',
           'LayoutParserHandler',
           'MoleculeDesignPoolLayoutParserHandler']


class BaseParserHandler(BaseTool):
    """
    Abstract base class for all parser handlers in TheLMA.

    Handlers initializes and run parsers and transform their results into
    model entities, if the parser was completed successfully.
    """
    _PARSER_CLS = None

    def __init__(self, stream=None, parent=None):
        """
        Constructor.

        :param stream: the opened file to parse
        :type stream: a file stream
        """
        BaseTool.__init__(self, parent=parent)
        #: The stream for the parser.
        self.stream = stream
        #: The parser handled by the parser handler.
        self.parser = None
        #: The object to be passed as result.
        self.return_value = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        self.return_value = None
        self.parser = None

    def run(self):
        """
        Initializes and runs the parser; if successful, creates a result
        entity.
        """
        self.reset()
        self._initialize_parser()
        self.parser.run()
        if self.parsing_completed():
            self._convert_results_to_entity()

    def _initialize_parser(self):
        """
        Initialises the parser.
        """
        kw = dict(stream=self.stream, parent=self._root_recorder)
        self.parser = self._PARSER_CLS(**kw) #pylint: disable=E1102
        self._initialize_parser_keys()

    def _initialize_parser_keys(self):
        """
        Used to set parser values.
        """
        pass

    def parsing_completed(self):
        """
        Checks whether the parsing run has been completed without errors.

        :rtype: :class:`boolean`
        """
        if self.parser is None:
            result = False
        else:
            result = self.parser.has_run and not self.parser.has_errors()
        return result

    def _convert_results_to_entity(self):
        """
        Converts the parsing results into a model entity of the model class.
        """
        raise NotImplementedError('Abstract method.')

    def __str__(self):
        return '<Parser Handler %s, errors: %i>' % (self.NAME,
                                                    self.error_count)


class LayoutParserHandler(BaseParserHandler): #pylint: disable=W0223
    """
    Special handler for parsers that involve plate layouts (providing some
    utility functions).
    """
    #: The domain for the layout tags.
    TAG_DOMAIN = None

    def __init__(self, stream, parent=None):
        """
        Constructor.

        :param stream: The opened file to parse.
        :type stream: a file stream
        """
        BaseParserHandler.__init__(self, stream=stream, parent=parent)
        #: The rack shape of the experiment design racks.
        self._rack_shape = None

    def _determine_rack_shape(self):
        """
        Creates a Rack Shape from a RackShapeParsingContainer (using
        the RackShapeFactory).
        """
        self.add_debug('Determining rack shape ...')
        if self.parser.shape is None:
            msg = 'There were no layouts in the uploaded file!'
            self.add_error(msg)
        else:
            self._rack_shape = self._convert_to_rack_shape(self.parser.shape)

    def _convert_to_rack_shape(self, rack_shape_container):
        """
        Converts a :class:`RackShapeParsingContainer` into a
        :class:`thelma.models.rack.RackShape`.
        """
        rack_shape_aggregate = get_root_aggregate(IRackShape)
        rack_shape = \
            rack_shape_aggregate.get_by_slug(rack_shape_container.name)
        if rack_shape is None:
            msg = 'Unable to fetch rack shape for shape label "%s"!'
            self.add_error(msg)
        return rack_shape

    def _convert_to_tag(self, tag_container):
        """
        Converts lists of tag_tuples into Tag entity sets.
        """
        tag_value = tag_container.value
        if str(tag_value).endswith('.0'):
            tag_value = '.'.join(str(tag_value).split('.')[0:-1])
        return Tag(self.TAG_DOMAIN, tag_container.predicate, tag_value)

    def _convert_to_rack_position(self, pos_container):
        """
        Creates a rack position for a rack position container.
        """
        return get_rack_position_from_indices(pos_container.row_index,
                                              pos_container.column_index)

    def _convert_to_rack_position_set(self, position_containers):
        """
        Create a rack position set from a set of rack position
        parsing containers.
        """
        return RackPositionSet.from_positions(
                                    [self._convert_to_rack_position(pos)
                                     for pos in position_containers])

class MoleculeDesignPoolLayoutParserHandler(LayoutParserHandler): #pylint: disable=W0223
    """
    Abstract handler for :class:`ExcelMoleculeDesignPoolLayoutParser`s
    for Excel file having layout that potentially contain molecule design
    pools - floating positions must be treated in a special way.
    """

    def __init__(self, stream, parent=None):
        LayoutParserHandler.__init__(self, stream, parent=parent)

    def _initialize_parser_keys(self):
        """
        We need to set floating related parser values. Also the allowed
        layout dimension are the fixed (96-well or 384-well).
        """
        parameter_set = MoleculeDesignPoolParameters
        validator = parameter_set.create_validator_from_parameter(
                                          parameter_set.MOLECULE_DESIGN_POOL)
        self.parser.molecule_design_id_predicates = validator.aliases
        self.parser.no_id_indicator = parameter_set.FLOATING_INDICATOR

        shape96 = get_96_rack_shape()
        shape384 = get_384_rack_shape()
        self.parser.allowed_rack_dimensions = [
                    (shape96.number_rows, shape96.number_columns),
                    (shape384.number_rows, shape384.number_columns)]
