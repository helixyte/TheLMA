from everest.repositories.rdb import Session
from sqlalchemy.engine import create_engine
from thelma.db import create_metadata
from thelma.entities.rack import RackPosition
from thelma.entities.utils import label_from_number


# If this is set to True, the changes will be committed when the script
# completes successfully (i.e., without errors and without warnings).
COMMIT = True

db_server = 'raven'
db_port = '5432'
db_user = 'thelma'
db_password = 'roo8Adei'
db_name = 'buffalo_backup'
db_string = "postgresql+psycopg2://%(db_user)s:%(db_password)s" \
            "@%(db_server)s:%(db_port)s/%(db_name)s" % locals()
engine = create_engine(db_string)
metadata = create_metadata(engine)

sess = Session()

max_row_number = 32
max_col_number = 48

pos_map = dict()

for r in range(max_row_number):

    row_letter = label_from_number(r + 1)
    for c in range(max_col_number):

        label = '%s%i' % (row_letter, c + 1)
        rack_pos = RackPosition(row_index=r, column_index=c, label=label)
        pos_map[label] = rack_pos
        sess.add(rack_pos)

print '%i rack positions have been created.' % (len(pos_map))
print 'Done processing.'


if COMMIT:
    sess.commit()
else:
    sess.rollback()
