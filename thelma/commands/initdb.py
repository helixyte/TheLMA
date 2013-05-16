"""
TheLMA database initialization commands

NP
"""

from everest.repositories.rdb import Session
from paste.deploy import appconfig # pylint: disable=E0611,F0401
from paste.script.command import Command # pylint: disable=E0611,F0401
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import IntegrityError
from thelma.data import initialize_data
from thelma.data.demo import initialize_demo_data
import logging
import os
import transaction
from thelma.db import create_metadata

__docformat__ = "reStructuredText en"

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-01-28 10:35:54 +0100 (Mon, 28 Jan 2013) $'
__revision__ = '$Rev: 13112 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/commands/initdb.py  $'

__all__ = ['InitializeDatabase']

class InitializeDatabase(Command): # pylint: disable=W0232
    """Create tables and optionally store data

    Example::

        $ paster initdb --include-data --include-demo-data TheLMA.ini thelma
    """
    summary = __doc__.splitlines()[0]
    usage = '\n'.join(__doc__.splitlines()[1:])
    group_name = "thelma"
    min_args = 2
    max_args = 2

    parser = Command.standard_parser(simulate=True)

    parser.add_option('--include-data',
                      action='store_true',
                      dest='data',
                      help="Store required data in the database")
    parser.add_option('--include-demo-data',
                      action='store_true',
                      dest='demo',
                      help="Store demo data in the database")

    def command(self):
        here_dir = os.getcwd()
        config_file, section_name = self.args # pylint: disable=E1101
        config_uri = 'config:%s' % config_file
        self.logging_file_config(config_file) # pylint: disable=E1101
        settings = appconfig(config_uri, section_name, relative_to=here_dir)
        db_string = settings.get('db_string') # pylint: disable=W0142
        engine = create_engine(db_string)
        data = demo = {}
        objects = []
        if self.options.data or self.options.demo: # pylint: disable=E1101
            data = initialize_data()
            objects.extend(self.__get_objects(data))
        if self.options.demo: # pylint: disable=E1101
            demo = initialize_demo_data(data)
            objects.extend(self.__get_objects(demo))
        # Initialize DB.
        metadata = create_metadata(engine)
        # Run metadata on engine.
        metadata.create_all(engine)
        if objects:
            try:
                session = Session()
                session.add_all(objects)
                transaction.commit()
            except IntegrityError, err:
                logger = logging.getLogger('sqlalchemy.engine')
                logger.error("Transaction aborted due to an integrity error")
                transaction.abort()
                raise err
        return engine

    def __get_objects(self, data_dict):
        objects = []
        for data in data_dict.values():
            for object_list in data.values():
                objects.extend(object_list)
        return objects
