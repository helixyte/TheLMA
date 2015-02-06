"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Unit tests for representers.
"""
from pkg_resources import resource_stream # pylint: disable=E0611
import pytest

from everest.mime import XmlMime
from everest.representers.utils import as_representer
from everest.resources.attributes import get_resource_class_attribute_names
from everest.resources.staging import create_staging_collection
from thelma.interfaces import IBarcodePrintJob
from thelma.interfaces import IDevice
from thelma.interfaces import IDeviceType
from thelma.interfaces import IItemStatus
from thelma.interfaces import ILocation
from thelma.interfaces import IOrganization
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackShape
from thelma.interfaces import ISpecies
from thelma.resources.organization import OrganizationMember


__docformat__ = 'reStructuredText en'
__all__ = ['TestResourceRepresenters',
           ]


@pytest.mark.usefixtures('resource_repo')
class TestResourceRepresenters(object):

    def test_barcode_representer(self, barcode_print_job_fac):
        bpj = barcode_print_job_fac()
        coll = create_staging_collection(IBarcodePrintJob)
        bpj_mb = coll.create_member(bpj)
        attrs = ('barcodes', 'labels', 'printer')
        self.__test_rpr_for_member(bpj_mb, (XmlMime,), attrs)

    def test_rackshape_representer(self, rack_shape_8x12):
        coll = create_staging_collection(IRackShape)
        rs_mb = coll.create_member(rack_shape_8x12)
        attrs = ('number_rows', 'number_columns', 'name', 'label')
        self.__test_rpr_for_member(rs_mb, (XmlMime,), attrs)

    def test_rackposition_representer(self, rack_position_a1):
        coll = create_staging_collection(IRackPosition)
        rp_mb = coll.create_member(rack_position_a1)
        attrs = ('row_index', 'column_index')
        self.__test_rpr_for_member(rp_mb, (XmlMime,), attrs)

    def test_device_representer(self, device_fac, device_type_printer,
                                organization_cenix):
        dev = device_fac(type=device_type_printer,
                         manufacturer=organization_cenix)
        coll = create_staging_collection(IDevice)
        dev_mb = coll.create_member(dev)
        attrs = ('label', 'model', 'manufacturer.name')
        self.__test_rpr_for_member(dev_mb, (XmlMime,), attrs)

    def test_devicetype_representer(self, device_type_fac):
        dt = device_type_fac()
        coll = create_staging_collection(IDeviceType)
        dt_mb = coll.create_member(dt)
        attrs = ('label',)
        self.__test_rpr_for_member(dt_mb, (XmlMime,), attrs)

    def test_itemstatus_representer(self, item_status_managed):
        coll = create_staging_collection(IItemStatus)
        is_mb = coll.create_member(item_status_managed)
        attrs = ('name', 'description')
        self.__test_rpr_for_member(is_mb, (XmlMime,), attrs)

    def test_location_representer(self, barcoded_location_fac):
        bcl = barcoded_location_fac()
        coll = create_staging_collection(ILocation)
        bcl_mb = coll.create_member(bcl)
        str_rpr = self._to_string(bcl_mb, XmlMime)
        assert len(str_rpr) > 0

    def test_organization_representer(self, organization_cenix):
        coll = create_staging_collection(IOrganization)
        org_mb = coll.create_member(organization_cenix)
        attrs = get_resource_class_attribute_names(OrganizationMember)
        self.__test_rpr_for_member(org_mb, (XmlMime,), attrs)

    def test_species_representer(self, species_human):
        coll = create_staging_collection(ISpecies)
        sp_mb = coll.create_member(species_human)
        attrs = ('genus_name', 'species_name', 'common_name',
                 'acronym', 'ncbi_tax_id')
        self.__test_rpr_for_member(sp_mb, (XmlMime,), attrs)

    def _to_string(self, resource, content_type):
        rpr = as_representer(resource, content_type)
        return rpr.to_string(resource)

    def _to_resource(self, string_representation, resource_type, content_type):
        rpr = as_representer(object.__new__(resource_type), content_type)
        return rpr.from_string(string_representation)

    def __test_rpr_for_collection(self, coll, content_types, attribute):
        for cnt_type in content_types:
            str_rpr = self._to_string(coll, cnt_type)
            print str_rpr
            col_reloaded = self._to_resource(str_rpr, type(coll), cnt_type)
            it = iter(col_reloaded)
            for member in coll:
                mb_reloaded = it.next()
                assert self.__getattr(member, attribute) \
                       == self.__getattr(mb_reloaded, attribute)

    def __test_rpr_for_member(self, member, content_types, attributes):
        for cnt_type in content_types:
            str_rpr = self._to_string(member, cnt_type)
            mb_reloaded = self._to_resource(str_rpr, type(member), cnt_type)
            for attr in attributes:
                value_in = self.__getattr(member, attr)
                value_reloaded = self.__getattr(mb_reloaded, attr)
                assert value_in == value_reloaded

    def __read_pkg_stream(self, pkg_res_name):
        return resource_stream(*pkg_res_name.split(':'))

    def __getattr(self, resource, attr):
        # Recursive attribute access with dotted attribute specifiers.
        value = resource
        for token in attr.split('.'):
            value = getattr(value, token)
        return value
