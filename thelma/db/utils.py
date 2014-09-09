"""
ORM utilities.

Created on Nov 28, 2012
"""
from StringIO import StringIO

from sqlalchemy import String
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import Sequence
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.sql.expression import _literal_as_binds
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import literal_column
from sqlalchemy.sql.visitors import Visitable


class BarcodeSequence(Sequence):
    """
    """
    def next_value(self):
        return func.lpad(func.cast(Sequence.next_value(self), String), 8, '0')


@compiles(BarcodeSequence)
def _compile_barcode_sequence(element, compiler, **kw): # pylint: disable=W0613
    buf = StringIO()
    buf.write('lpad(cast(')
    buf.write(compiler.visit_sequence(element))
    buf.write(" as text), 8, '0')")
    sql_expr = buf.getvalue()
    return sql_expr


class string_agg(ColumnElement): # __iter__ raises NotImplementedError pylint:disable=W0223
    """
    Represents a string_agg aggregation function clause with support for
    an ORDER BY expression.

    Adapted from
    https://groups.google.com/forum/?fromgroups=#!topic/sqlalchemy/cQ9e9IVOykE
    """
    __visit_name__ = 'string_agg'

    type = String

    def __init__(self, expr, separator, order_by=None): # pylint: disable=W0231
        self.expr = _literal_as_binds(expr)
        self.separator = _literal_as_binds(separator)
        if order_by is not None:
            self.order_by = _literal_as_column(order_by)
        else:
            self.order_by = None

    @property
    def table(self):
        return self.expr.table # pylint: disable=E1103


@compiles(string_agg, 'postgresql')
def _compile_string_agg_postgresql(element, compiler, **kw): # pylint: disable=W0613
    buf = StringIO()
    buf.write('string_agg(')
    buf.write(compiler.process(element.expr))
    buf.write(', %s' % compiler.process(element.separator))
    if not element.order_by is None:
        buf.write(' ORDER BY ')
        buf.write(compiler.process(element.order_by))
    buf.write(')')
    sql_expr = buf.getvalue()
    return sql_expr


# FIXME: This function was removed in SA 0.8.x; investigate the reason for
#        its removal.
def _literal_as_column(element):
    if isinstance(element, Visitable):
        return element
    elif hasattr(element, '__clause_element__'):
        return element.__clause_element__()
    else:
        return literal_column(str(element))
