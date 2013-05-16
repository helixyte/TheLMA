from everest.repositories.rdb import Session
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import joinedload
from thelma.db import create_metadata
from thelma.models.moleculedesign import MoleculeDesignPool
import os
import sys


COMMIT = False
WARNINGS = []

db_server = 'raven'
db_port = '5432'
db_user = 'thelma'
db_password = 'roo8Adei'
db_name = 'unidb'
db_string = "postgresql+psycopg2://%(db_user)s:%(db_password)s" \
            "@%(db_server)s:%(db_port)s/%(db_name)s" % locals()
engine = create_engine(db_string)
metadata = create_metadata(engine)

sess = Session()

sss_query = sess.query(MoleculeDesignPool)

hash_map = {}
total_cnt = sss_query.count()

sss_query = sss_query.options(
                    joinedload(MoleculeDesignPool.stock_samples))

dup_cnt = 1
# Go through all stock sample sets and remove duplicates.
print 'Loading stock sample molecule design sets.'
for cnt, stock_spl_set in enumerate(sss_query.all()):
    sys.stdout.write('Processing %d of %d.' % (cnt + 1, total_cnt))
    if not stock_spl_set.member_hash in hash_map:
        hash_map[stock_spl_set.member_hash] = stock_spl_set
    else:
        sys.stdout.write(' Duplicate %d.' % dup_cnt)
        dup_cnt += 1
        ref_stock_spl_set = hash_map[stock_spl_set.member_hash]
        for stock_spl in stock_spl_set.stock_samples:
            stock_spl.molecule_design_set = ref_stock_spl_set
        sess.delete(stock_spl_set)
    sys.stdout.write(os.linesep)
print 'Done processing.'

if COMMIT and len(WARNINGS) == 0:
    print 'Committing transaction.'
    sess.commit()
else:
    if WARNINGS:
        print 'Warnings occurred - rolling back transaction.'
        print 'Warning messages:'
        print '\n'.join(WARNINGS)
    print 'Rolling back transaction.'
    sess.rollback()

