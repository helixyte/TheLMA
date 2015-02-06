"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Aggregate implementations.

Created Sep 25, 2011
"""
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import and_

from everest.querying.base import EXPRESSION_KINDS
from everest.repositories.rdb.aggregate import RdbAggregate as Aggregate
from everest.utils import get_filter_specification_visitor
from thelma.entities.container import Tube
from thelma.entities.location import BarcodedLocation
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.rack import Plate
from thelma.entities.rack import Rack
from thelma.entities.rack import TubeRack
from thelma.entities.sample import Sample
from thelma.entities.sample import StockSample
from thelma.entities.suppliermoleculedesign import SupplierMoleculeDesign


__docformat__ = 'reStructuredText en'
__all__ = ['ThelmaRdbAggregate',
           ]


class ThelmaRdbAggregate(Aggregate):
    """
    TheLMA implementation for aggregates (using SQLAlchemy).

    This specializes the everest RDB aggregate implementation to use
    TheLMA-specific query, filter, and order information.
    """
    def _query_optimizer(self, query, key):
        gen_query = _QueryOptimizers.get(self.entity_class, query, key)
        if gen_query is None:
            gen_query = super(ThelmaRdbAggregate, # pylint: disable=W0212
                              self)._query_optimizer(query, key)
        return gen_query

    def _filter_visitor_factory(self):
        vst = _FilterVisitorFactories.get(self.entity_class, self._session)
        if vst is None:
            vst = super(ThelmaRdbAggregate, # pylint: disable=W0212
                        self)._filter_visitor_factory()
        return vst

    def _order_visitor_factory(self):
        vst = _OrderVisitorFactories.get(self.entity_class)
        if vst is None:
            vst = super(ThelmaRdbAggregate, # pylint: disable=W0212
                        self)._order_visitor_factory()
        return vst


class _QueryOptimizers(object):
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
        gen_attr = _QueryOptimizers.__map.get(entity_class)
        if not gen_attr is None:
            res = getattr(cls, gen_attr)(query, key)
        else:
            res = None
        return res


class _FilterVisitorFactories(object):
    @classmethod
    def _location_filter_visitor_factory(cls, session): # pylint: disable=W0613
        def location_type_expr(location_type_member):
            return BarcodedLocation.type == location_type_member.name
        custom_clause_factories = {
                            ('type', 'equal_to'): location_type_expr,
                            }
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.SQL)
        return visitor_cls(BarcodedLocation, custom_clause_factories)

    @classmethod
    def _rack_filter_visitor_factory(cls, session): # pylint: disable=W0613
        def one_location_type_expr(location_type_member):
            value = location_type_member.name
            return Rack.location.has(
                       BarcodedLocation.type == value
                       )
        custom_clause_factories = {
            ('location.type', 'equal_to'): one_location_type_expr,
            }
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.SQL)
        return visitor_cls(Rack, custom_clause_factories)

    @classmethod
    def _tube_filter_visitor_factory(cls, session): # pylint: disable=W0613
        # FIXME: This is necessary because we build our query expressions
        #        from the instrumented attributes of the entity class -
        #        which is Sample, not StockSample.
        def sample_product_id_expr(product_id):
            # Using hidden instrumented attributes pylint: disable=E1101
            return Tube.sample.has(
                and_(StockSample.sample_id == Sample.sample_id,
                     StockSample.molecule_design_pool.has(
                         MoleculeDesignPool.supplier_molecule_designs.any(
                             and_(SupplierMoleculeDesign.product_id ==
                                        product_id,
                                  SupplierMoleculeDesign.supplier_id ==
                                        StockSample.supplier_id,
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
