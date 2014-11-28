"""
Mapper utilities.
"""
from sqlalchemy import func
from sqlalchemy.orm import ColumnProperty


__docformat__ = 'reStructuredText en'
__all__ = ['CaseInsensitiveComparator',
           'ProxyDict',
           ]

class CaseInsensitiveComparator(ColumnProperty.Comparator): # pylint: disable=W0223
    """
    Case Insensitive Comparator
    """

    def __eq__(self, other):
        other = str(other)
        return func.lower(self.__clause_element__()) == func.lower(other)

    def __ne__(self, other):
        other = str(other)
        return func.lower(self.__clause_element__()) != func.lower(other)

    def startswith(self, other, **kwargs):
        other = str(other)
        return func.lower(self.__clause_element__()
                          ).startswith(func.lower(other), **kwargs)

    def endswith(self, other, **kwargs):
        other = str(other)
        return func.lower(self.__clause_element__()
                          ).endswith(func.lower(other), **kwargs)

    def contains(self, other, **kwargs):
        other = str(other)
        return func.lower(self.__clause_element__()
                          ).contains(func.lower(other), **kwargs)


class ProxyDict(object):
    """
    Dynamic Relations as Dictionaries

    Inspired by a SQLAlchemy example found in examples/dynamic_dict/

    Places a dictionary-like facade on top of a "dynamic" relation, so that
    dictionary operations (assuming simple string keys) can operate upon a
    large collection without loading the full collection at once.
    """

    def __init__(self, parent, collection_name, child_class, child_factory,
                 key_attr_name, value_attr_name=None, key_func=None):
        self._parent = parent
        self._collection_name = collection_name
        self._child_class = child_class
        self._child_factory = child_factory
        self._key_attr_name = key_attr_name
        self._value_attr_name = value_attr_name
        self._key_func = key_func

    def __len__(self):
        return self._collection.count()

    def __getitem__(self, key):
        item = self._get_item_value(
                   self._get_collection_item(
                       self._get_item_key(key)
                       )
                   )
        if item is None:
            raise KeyError(key)
        return item

    def __setitem__(self, key, value):
        # FIXME: This method has not been tested! # pylint:disable=W0511
        raise NotImplementedError('Setting new items is not supported yet!')
#        real_key = self._get_item_key(key)
#        existing_item = self._get_collection_item(real_key)
#        if existing_item is not None:
#            self._collection.remove(existing_item)
#        self._collection.append(self._child_factory(self, real_key, value))

    def keys(self):
        return [getattr(item, self._key_attr_name) for item in self._collection]

    def values(self):
        return [self._get_item_value(item) for item in self._collection]

    @property
    def _collection(self):
        return getattr(self._parent, self._collection_name)

    def _get_collection_item(self, key):
        return self._collection.filter_by(**{self._key_attr_name:key}).first() # pylint: disable=W0142

    def _get_item_value(self, item):
        if self._value_attr_name is not None:
            return getattr(item, self._value_attr_name)
        else:
            return item

    def _get_item_key(self, key):
        if self._key_func is not None:
            return self._key_func(key)
        else:
            return key
