"""
Aggregate implementations.

FOG Sep 25, 2011
"""
from everest.querying.base import EXPRESSION_KINDS
from everest.repositories.rdb import Aggregate
from everest.utils import get_filter_specification_visitor
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import over
from thelma.models.container import Tube
from thelma.models.location import BarcodedLocation
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.rack import Plate
from thelma.models.rack import Rack
from thelma.models.rack import TubeRack
from thelma.models.sample import Sample
from thelma.models.sample import StockSample
from thelma.models.suppliermoleculedesign import SupplierMoleculeDesign

__docformat__ = 'reStructuredText en'
__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2013-01-28 10:35:54 +0100 (Mon, 28 Jan 2013) $'
__revision__ = '$Rev: 13112 $'
__source__ = '$URL::                                                        #$'

__all__ = ['ThelmaRdbAggregate',
           ]


class CountingQuery(Query):
    def __init__(self, *args, **kw):
        Query.__init__(self, *args, **kw)
        self.count = None
        self.data = None

    def load(self):
        query = self.add_columns(over(func.count(1)).label('_count'))
        res = [tup[0] for tup in Query.__iter__(query)]
        if len(res) > 0:
            self.count = tup._count # pylint:disable-msg=W0212,W0631
        else:
            self.count = 0
        self.data = res


class ThelmaRdbAggregate(Aggregate):
    """
    TheLMA implementation for aggregates (using SQLAlchemy).

    This specializes the everest RDB aggregate implementation to use
    TheLMA-specific query, filter, and order information.
    """
    __count = None
    __data = None

    def _query_generator(self, query, key):
        gen_query = _QueryGenerators.get(self.entity_class, query, key)
        if gen_query is None:
            gen_query = super(ThelmaRdbAggregate, # pylint: disable=W0212
                              self)._query_generator(query, key)
        return gen_query

    def _filter_visitor_factory(self):
        fac = _FilterVisitorFactories.get(self.entity_class, self._session)
        if fac is None:
            fac = super(ThelmaRdbAggregate, # pylint: disable=W0212
                        self)._filter_visitor_factory()
        return fac

    def _order_visitor_factory(self):
        fac = _OrderVisitorFactories.get(self.entity_class)
        if fac is None:
            fac = super(ThelmaRdbAggregate, # pylint: disable=W0212
                        self)._order_visitor_factory()
        return fac

    def _apply_filter(self):
        self.__count = None
        self.__data = None

    def _apply_order(self):
        self.__data = None

    def _apply_slice(self):
        self.__count = None
        self.__data = None

#    def count(self):
#        if self.__count is None:
#            self._session._query_cls = CountingQuery # pylint: disable=W0212
#            try:
#                query = self._get_data_query()
#                query.load()
#                self.__data = query.data
#                self.__count = query.count
#            finally:
#                self._session._query_cls = Query # pylint: disable=W0212
#        return self.__count
#
#    def iterator(self):
#        if self.__data is None:
#            self._session._query_cls = CountingQuery # pylint: disable=W0212
#            try:
#                query = self._get_data_query()
#                query.load()
#                self.__data = query.data
#                self.__count = query.count
#            finally:
#                self._session._query_cls = Query # pylint: disable=W0212
#        return iter(self.__data)


class _QueryGenerators(object):
    @classmethod
    def _rack_query_generator(cls, query, key):
        if key is None: # iteration over full collection
            opt_query = query.options(joinedload(Rack.location),
                                      joinedload(Rack.specs),
                                      joinedload(Rack.status))
        else:
            opt_query = query
        return opt_query

    __map = {Rack:'_rack_query_generator',
             }

    @classmethod
    def get(cls, entity_class, query, key):
        gen_attr = _QueryGenerators.__map.get(entity_class)
        if not gen_attr is None:
            res = getattr(cls, gen_attr)(query, key)
        else:
            res = None
        return res


class _FilterVisitorFactories(object):
    @classmethod
    def _location_filter_visitor_factory(cls, session): # disregard session pylint: disable=W0613
        def location_type_expr(location_type_member):
            return BarcodedLocation.type == location_type_member.name
        custom_clause_factories = {
                            ('type', 'equal_to'): location_type_expr,
                            }
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.SQL)
        return visitor_cls(BarcodedLocation, custom_clause_factories)

    @classmethod
    def _rack_filter_visitor_factory(cls, session): # disregard session pylint: disable=W0613
        def one_location_type_expr(location_type_member):
            value = location_type_member.name
            return Rack.location.has(
                       BarcodedLocation.type == value # pylint: disable=E1101
                       )
        custom_clause_factories = {
            ('location.type', 'equal_to'): one_location_type_expr,
            }
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.SQL)
        return visitor_cls(Rack, custom_clause_factories)

    @classmethod
    def _tube_filter_visitor_factory(cls, session): # disregard session pylint: disable=W0613
        # FIXME: This is necessary because we build our query expressions
        #        from the instrumented attributes of the entity class -
        #        which is Sample, not StockSample.
        def sample_product_id_expr(product_id):
            # Using hidden instrumented attributes pylint: disable=E1101
            return Tube.sample.has(
                and_(StockSample.sample_id == Sample.sample_id,
                     StockSample.molecule_design_pool.has(
                         MoleculeDesignPool.supplier_molecule_designs.any(
                             and_(SupplierMoleculeDesign.product_id == product_id,
                                  SupplierMoleculeDesign.supplier_id == StockSample.supplier_id,
                                  SupplierMoleculeDesign.is_current)
                                                                   ))))
            # pylint: enable=E1101

        custom_clause_factories = {
            ('sample.product_id', 'equal_to') : sample_product_id_expr,
            }
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.SQL)
        return visitor_cls(Tube, custom_clause_factories)

    __map = {BarcodedLocation:'_location_filter_visitor_factory',
             Rack:'_rack_filter_visitor_factory',
             TubeRack:'_rack_filter_visitor_factory',
             Plate:'_rack_filter_visitor_factory',
             Tube:'_tube_filter_visitor_factory',
             }

    @classmethod
    def get(cls, entity_class, session):
        fac_attr = _FilterVisitorFactories.__map.get(entity_class)
        if not fac_attr is None:
            res = getattr(cls, fac_attr)(session)
        else:
            res = None
        return res


class _OrderVisitorFactories(object):

    __map = {}

    @classmethod
    def get(cls, entity_class):
        fac_attr = _OrderVisitorFactories.__map.get(entity_class)
        if not fac_attr is None:
            res = getattr(cls, fac_attr)()
        else:
            res = None
        return res
