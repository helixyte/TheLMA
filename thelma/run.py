"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Functions to create a WSGI application
"""
from tractor import make_api_from_config

from everest.configuration import Configurator
from everest.root import RootFactory
from thelma.interfaces import ITractor


__docformat__ = "reStructuredText en"
__all__ = ['app',
           'create_config',
           ]


def create_config(settings, package='thelma', registry=None):
    """
    Returns a configurator for TheLMA.
    """
    config = Configurator(package=package,
                          registry=registry)
    if registry is None:
        config.setup_registry(settings=settings,
                              root_factory=RootFactory())
        config.load_zcml('configure.zcml')
    # tractor registration
    tractor_config_file = settings['tractor_config_file']
    tractor_api = make_api_from_config(tractor_config_file)
    config.registry.registerUtility(tractor_api, ITractor) # pylint: disable=E1103
    return config


def app(global_settings, **local_settings): # pylint: disable=W0613
    """
    Returns a WSGI application.

    It is usually called by the PasteDeploy framework during
    ``paster serve``.
    """
    config = create_config(local_settings)
    return config.make_wsgi_app()
