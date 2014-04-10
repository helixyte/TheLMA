"""
:Date: 02 aug 2011
:Author: AAB, berger at cenix-bioscience dot com
"""

from everest.repositories.rdb import Session
from thelma.automation.errors import MessageRecorder
from thelma.automation.semiconstants import clear_semiconstant_caches
from thelma.automation.semiconstants import initialize_semiconstant_caches
from thelma.automation.utils.base import get_trimmed_string


__docformat__ = 'reStructuredText en'

__all__ = ['BaseTool']


class BaseTool(MessageRecorder):
    """
    Abstract base class for all tools.

    Its main purpose is to provide message recording and parameter checking
    amenities.
    """
    def __init__(self, parent=None):
        MessageRecorder.__init__(self, parent=parent)
        if self._is_root:
            initialize_semiconstant_caches()
        #: The object to be passed as result.
        self.return_value = None

    def run(self):
        """
        Runs the tool.
        """
        raise NotImplementedError('Abstract method.')

    def get_result(self, run=True):
        """
        Returns the return value.

        :param bool run: Determines whether the tool shall call the
            :func:`run` method (it can also be called separately).
        :default run: *True*
        """
        # FIXME: Get rid of the run parameter - a "get_*" method should not
        #        have side effects!
        if run:
            try:
                self.run()
            finally:
                if self._is_root:
                    clear_semiconstant_caches()
        return self.return_value

    def reset(self):
        """
        Resets the tool's :attr:`log`, its :attr:`return_value`.
        """
        MessageRecorder.reset(self)
        self.return_value = None
        if self._is_root:
            initialize_semiconstant_caches()
        self.add_info('Reset.')

    def _get_additional_value(self, value):
        """
        This function can be used if there are additional values to be
        returned to a parent tool besides the actual return value. The
        function makes sure the value is only returned if the
        :attr:`return_value` of the tool is not None (i.e. the tool has
        run and completed without errors).
        """
        if self.return_value is None:
            result = None
        else:
            result = value
        return result

    def _check_input_class(self, name, obj, obj_class):
        """
        Checks whether an object has the expected class and records an error
        if the test fails.

        :param str name: The name to use for the checked object should an
            error be recorded.
        :param object obj: The object to check.
        :param type obj_class: The expected class.
        """
        is_valid = isinstance(obj, obj_class)
        if not is_valid:
            msg = 'The %s must be a %s object (obtained: %s).' \
                  % (name, obj_class.__name__, obj.__class__.__name__)
            self.add_error(msg)
        return is_valid

    def _check_input_list_classes(self, item_name, list_obj, item_cls,
                                  may_be_empty=False):
        """
        Checks whether a list and the objects it contains have the expected
        class and a length of at least 1 and records an error, if the test
        fails.

        :param str item_name: The name to use for the checked list items
            should an error be recorded.
        :param list list_obj: The list to be tested.
        :param type item_cls: The expected class for the list items.
        :param bool may_be_empty: May the list be empty?
        :default may_be_empty: *False*
        """
        list_name = '%s list' % (item_name)
        is_valid = self._check_input_class(list_name, list_obj, list)
        if is_valid:
            is_valid = all([self._check_input_class(item_name, item, item_cls)
                            for item in list_obj])
        if is_valid:
            is_valid = len(list_obj) > 0 or may_be_empty
            if not is_valid:
                msg = 'The %s is empty!' % (list_name)
                self.add_error(msg)
        return is_valid

    def _check_input_map_classes(self, map_obj, map_name, key_name, key_cls,
                                 value_name, value_cls, may_be_empty=False):
        """
        Checks whether a maps and the objects it contains have the expected
        class and a length of at least 1 and records an error, if applicable.

        :param map_obj: The map to be tested.
        :type map_obj: :class:`dict`

        :param map_name: The name under which the map shall be referenced
            in the error message.
        :type map_name: :class:`str

        :param key_name: The name under which a map key item be referenced
            in the error message.
        :type key_name: :class:`str

        :param value_name: The name under which a mape value shall be
            referenced in the error message.
        :type value_name: :class:`str

        :param key_cls: The expected class for the map keys.
        :type key_cls: any

        :param value_cls: The expected class for the map values.
        :type value_cls: any

        :param may_be_empty: May the list be empty?
        :type may_be_empty: :class:`bool`
        :default may_be_empty: *False*
        """
        is_valid = self._check_input_class(map_name, map_obj, dict)
        if is_valid:
            for k, v in map_obj.iteritems():
                if not self._check_input_class(key_name, k, key_cls):
                    is_valid = False
                    break
                elif not self._check_input_class(value_name, v, value_cls):
                    is_valid = False
                    break
        if is_valid:
            is_valid = len(map_obj) > 0 or may_be_empty
            if not is_valid:
                msg = 'The %s is empty!' % (map_name)
                self.add_error(msg)
        return is_valid

    def _run_and_record_error(self, meth, base_msg, error_types=None, **kw):
        """
        Convenience method that runs a method and catches errors of the
        specified types. The error messages are recorded along with the
        base msg.

        :param meth: The method to be called.

        :param base_msg: This message is put in front of the potential error
            message. If the message is *None* there is no error recorded.
        :type base_msg: :class:`str`

        :param error_types: Error classes that shall be caught.
        :type error_types: iterable
        :default error_type: *None* (catches AttributeError, ValueError and
            TypeError)

        :return: The method return value or *None* (in case of exception)
        """
        if base_msg is not None:
            filler = ': '
            if base_msg.endswith(filler):
                filler = ''
            elif base_msg.endswith(':'):
                filler = ' '
            base_msg += filler
        if error_types is None:
            error_types = {ValueError, TypeError, AttributeError}
        elif isinstance(error_types, type):
            error_types = set([error_types])
        elif isinstance(error_types, type) \
             and issubclass(error_types, StandardError):
            error_types = (error_types,)
        try:
            return_value = meth(**kw)
        except StandardError as e:
            if e.__class__ in error_types and not base_msg is None:
                self.add_error(base_msg + str(e))
            elif base_msg is None:
                return_value = None
            else:
                raise e
        else:
            return return_value

    def _get_joined_str(self, item_list, is_strs=True, sort_items=True,
                        separator=', '):
        """
        Helper method converting the passed list into a joined string, separated
        by comma (default). By default, the elements are sorted before
        conversion. This is handy i.e. when printing error messages.

        :param item_list: The recorded events in a list.
        :type item_list: :class:`list` or iterable that can be converted into
            a list.
        :param bool is_strs: If not the items must be converted first.
            Without conversion the join method will raise an error.
        :default is_strs: *True*
        :param bool sort_items: Shall the items be sorted?
        :default sort_items: *True*
        :param str separator: The string to use for the joining.
        :default separator: Comma and 1 space.
        """
        if not isinstance(item_list, list):
            item_list = list(item_list)
        if sort_items: item_list.sort()
        if is_strs:
            item_strs = item_list
        else:
            item_strs = [get_trimmed_string(item) for item in item_list]
        return separator.join(item_strs)

    def _get_joined_map_str(self, item_map, str_pattern='%s (%s)',
                            all_strs=True, sort_lists=True, separator=' - '):
        """
        Helper method converting the passed map into a string joined by the
        given separator. By default, the elements of the lists are sorted
        before conversion (map keys are always sorted).
        This is handy i.e. when printing error messages.

        If the map values are iterables, :func:`_get_joined_str` is used to
        generate a string for the list.

        :param item_map: The recorded events in a map.
        :type item_map: :class:`map` having iterables as values
        :param str str_pattern: Is used to convert key-value pairs into a string.
            The first placeholder is used by the key, the second by the joined
            string value.
        :default str_pattern: *%s (%s)*
        :param bool all_strs: Flag indicating if the value list items are
            strings (only applicable if the value is an iterable)? If not the
            items must be converted first. Without conversion the join method
            will raise an error.
        :default all_strs: *True*
        :param bool sort_lists: Flag indicating if the values items should be
            sorted (only applicable if the value is an iterable).
        :default sort_lists: *True*
        :param str separator: The string to use for the joining the key-value
            strings.
        :default separator: whitespace, dash, whitespace
        """
        details = []
        for k in sorted(item_map.keys()):
            v = item_map[k]
            if isinstance(v, (list, set, dict, tuple)):
                v_str = self._get_joined_str(v, is_strs=all_strs,
                                             sort_items=sort_lists)
            else:
                v_str = str(v)
            details_str = str_pattern % (get_trimmed_string(k), v_str)
            details.append(details_str)
        return separator.join(details)

    def __str__(self):
        return '<Tool %s, errors: %i>' % (self.NAME, self.error_count)


class SessionTool(BaseTool):
    """
    Abstract base class for tools that run queries.
    """
    def __init__(self, parent=None):
        BaseTool.__init__(self, parent=parent)
        #: The DB session used for the queries.
        self.__session = None

    def reset(self):
        BaseTool.reset(self)
        self.__session = Session()

    def _run_query(self, query, base_error_msg):
        """
        Helper method running a :class:`CustomQuery` and recording errors
        if necessary. If the message is *None* there is no error recorded.
        """
        self._run_and_record_error(query.run, base_msg=base_error_msg,
                                   error_types=ValueError,
                                   session=self.__session)

    def run(self):
        BaseTool.run(self)
        del self.__session
