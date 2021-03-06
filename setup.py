from distribute_setup import use_setuptools
use_setuptools()

from setuptools import find_packages
from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

setup_requirements = []

install_requirements = \
    [line
     for line in open('requirements.txt', 'rU').readlines()
     if not line.startswith('-e')]
install_requirements.append('everest')
install_requirements.append('tractor')

tests_requirements = install_requirements + [
    'nose-cov',
    'webtest',
    ]

setup(name='TheLMA',
      version='1.9.x',
      description='TheLMA',
      long_description=README,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: everest",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='F. Oliver Gathmann, Nikos Papagrigoriou, Anna-Antonia ' \
             ' Berger, Tobias Rothe',
      author_email='fogathmann at gmail.com',
      keywords='web wsgi bfg',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      setup_requires=setup_requirements,
      install_requires=install_requirements,
      tests_require=tests_requirements,
      test_suite="thelma",
      dependency_links=
        ['https://github.com/cenix/everest/tarball/master#egg=everest',
         'https://github.com/cenix/tractor/tarball/master#egg=tractor'],
      entry_points="""\
      [paste.app_factory]
      app = thelma.run:app
      [paste.paster_command]
      runtool = thelma.tools.shell:ToolCommand
      [paste.filter_app_factory]
      flexfilter = everest.flexfilter:FlexFilter.paste_deploy_middleware
      """,
      )

