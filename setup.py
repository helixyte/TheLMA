from distribute_setup import use_setuptools
use_setuptools()

from setuptools import find_packages
from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

setup_requirements = []

install_requirements = \
    [line
     for line in open('requirements.txt', 'rU').readlines()
     if not line.startswith('-e')]
install_requirements.append('everest')
install_requirements.append('tractor')

tests_requirements = install_requirements + [
    'nose>=1.1.2,<=1.1.99',
    'nosexcover>=1.0.4,<=1.0.99',
    'coverage==3.4',
    'webtest>=1.3.1,<=1.3.99',
    ]

setup(name='TheLMA',
      version='1.3.x',
      description='TheLMA',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: BFG",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Cenix Bioscience GmbH',
      author_email='dev@cenix.com',
      url='http://www.cenix.com',
      keywords='web wsgi bfg',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      setup_requires=setup_requirements,
      install_requires=install_requirements,
      tests_require=tests_requirements,
      test_suite="thelma",
      dependency_links=['https://github.com/cenix/everest/tarball/master#egg=everest',
                        'https://github.com/cenix/tractor/tarball/master#egg=tractor'],
      entry_points="""\
      [paste.app_factory]
      app = thelma.run:app

      [paste.paster_command]
      runtool = thelma.commands.tools:ToolCommand

      [paste.filter_app_factory]
      flexfilter = everest.flexfilter:FlexFilter.paste_deploy_middleware
      """,
      )
