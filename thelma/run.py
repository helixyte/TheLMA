"""
Functions to create a WSGI application

NP
"""

from everest.configuration import Configurator
from everest.root import RootFactory
from thelma.interfaces import ITractor
from tractor import make_api_from_config

__docformat__ = "reStructuredText en"

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2012-12-02 14:30:54 +0100 (Sun, 02 Dec 2012) $'
__revision__ = '$Rev: 12968 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/run.py              $'

__all__ = ['app',
           'create_config',
           ]


def create_config(settings, package='thelma', registry=None):
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
    """This function returns a WSGI application.

    It is usually called by the PasteDeploy framework during
    ``paster serve``.
    """
    config = create_config(local_settings)
    return config.make_wsgi_app()
