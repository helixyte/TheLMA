"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 24, 2013.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['cache_loader_registry',
           ]


class CacheLoaderRegistry(object):
    """
    Cache loader registry for static entity loaders. These are used by the
    caching entity store to populate in-memory root collections.
    """
    def __init__(self):
        self.__loaders = {}

    def register_loader(self, entity_class, loader):
        self.__loaders[entity_class] = loader

    def __call__(self, entity_class):
        loader = self.__loaders.get(entity_class)
        if not loader is None:
            ents = loader()
        else:
            ents = []
        return ents

cache_loader_registry = CacheLoaderRegistry()
