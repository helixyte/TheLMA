-- Migration to alembic.

SELECT assert('(select version from db_version) = 19.1');

CREATE TABLE alembic_version
(version_num VARCHAR(32) primary key);

-- This is the base line version which is equivalent to the empty test
-- database that the populate_test_db script creates (it still contains lots
-- of extra tables and other objects that were created for CeLMA; this needs
-- to be cleaned up after CeLMA is finally retired).
INSERT INTO alembic_version (version_num) VALUES ('227c832e89fb');

-- Drop the now obsolete db_version table.
DROP VIEW db_version;