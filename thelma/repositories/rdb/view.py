"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Utilities to create/drop views.

Based on a recipe published in:

http://www.sqlalchemy.org/trac/wiki/UsageRecipes/Views
"""
from sqlalchemy.sql import table
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement

__docformat__ = 'reStructuredText en'
__all__ = ['CreateView',
           'DropView',
           'view_factory',
           ]


class CreateView(DDLElement):
    def __init__(self, name, selectable): # pylint: disable=W0231
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name): # pylint: disable=W0231
        self.name = name


@compiler.compiles(CreateView, 'postgresql')
def create_view_compile_postgresql(element, compiler, **kw): # pylint: disable=W0621,W0613
    selection = compiler.sql_compiler.process(element.selectable)
    stmt = "CREATE OR REPLACE VIEW %s AS %s" % (element.name, selection)
    # FIXME: we should not combine the statement and params here.
    #        it is a SQLAlchemy bug... report it.
    params = {}
    for k, v in element.selectable.compile().params.iteritems():
        params[k] = ("'%s'" % v) if isinstance(v, basestring) else v
    return stmt % params


@compiler.compiles(CreateView, 'sqlite')
def create_view_compile_sqlite(element, compiler, **kw): # pylint: disable=W0621,W0613
    # FIXME: duplicate code
    # FIXME: it seems that there is a bug in SQLAlchemy and creating views
    #        this way emits an exception
    selection = compiler.sql_compiler.process(element.selectable)
    stmt = "CREATE VIEW %s AS %s" % (element.name, selection)
    # FIXME: we should not combine the statement and params here.
    #        it is a SQLAlchemy bug... report it.
    params = {}
    for k, v in element.selectable.compile().params.iteritems():
        params[k] = ("'%s'" % v) if isinstance(v, basestring) else v
    return stmt % params


@compiler.compiles(DropView)
def drop_view_compile(element, compiler, **kw): # pylint: disable=W0621,W0613
    return "DROP VIEW %s" % (element.name)


def view_factory(name, metadata, selectable):
    if not hasattr(metadata, 'views'):
        metadata.views = {}

    metadata.views[name] = table(name)

    for c in selectable.c:
        c._make_proxy(metadata.views[name]) # pylint: disable=W0212

    CreateView(name, selectable).execute_at('after-create', metadata)
    DropView(name).execute_at('before-drop', metadata)
    return metadata.views[name]
