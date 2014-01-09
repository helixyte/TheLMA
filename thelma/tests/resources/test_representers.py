"""
Unit tests for representers.

FOG
"""
from pkg_resources import resource_stream # pylint: disable=E0611

from everest.mime import XmlMime
from everest.representers.atom import AtomResourceRepresenter
from everest.representers.utils import as_representer
from everest.resources.attributes import get_resource_class_attribute_names
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_root_collection
from thelma.interfaces import IGene
from thelma.interfaces import IItemStatus
from thelma.interfaces import IProject
from thelma.interfaces import IRack
from thelma.interfaces import IRackSpecs
from thelma.interfaces import IStockInfo
from thelma.interfaces import ITube
from thelma.resources.organization import OrganizationMember
from thelma.testing import ThelmaResourceTestCase


__docformat__ = 'reStructuredText en'

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2013-03-20 14:02:27 +0100 (Wed, 20 Mar 2013) $'
__revision__ = '$Rev: 13230 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/resources/tes#$'

__all__ = ['RepresentersTestCase',
           ]


class RepresentersTestCase(ThelmaResourceTestCase):
    test_path = 'thelma:tests/resources'

    def test_barcode_representer(self):
        barc_in = self._create_barcode_print_job_member()
        attrs = ('barcodes', 'labels', 'printer')
        self.__test_rpr_for_member(barc_in, (XmlMime,), attrs)

    def test_rack_collection_representer(self):
        coll = create_staging_collection(IRack)
        coll.add(self._create_plate_member())
        coll.add(self._create_tube_rack_member())
        self.__test_rpr_for_collection(coll, (XmlMime,), 'barcode')

    def test_rackspecs_collection_representer(self):
        coll = create_staging_collection(IRackSpecs)
        coll.add(self._create_plate_specs_member())
        coll.add(self._create_tube_rack_specs_member())
        # Cannot reload tube rack specs because of nested tube_specs attr.
        str_rpr = self._to_string(coll, XmlMime)
        self.assert_true(len(str_rpr) > 0)

    def test_rackshape_representer(self):
        member = self._create_rack_shape_member()
        attrs = ('number_rows', 'number_columns', 'name', 'label')
        self.__test_rpr_for_member(member, (XmlMime,), attrs)

    def test_rackposition_representer(self):
        member = self._get_rack_position_member()
        attrs = ('row_index', 'column_index')
        self.__test_rpr_for_member(member, (XmlMime,), attrs)

    def test_device_representer(self):
        dev_in = self._create_device_member()
        attrs = ('label', 'model', 'manufacturer.name')
        self.__test_rpr_for_member(dev_in, (XmlMime,), attrs)

    def test_devicetype_representer(self):
        dt_in = self._create_devicetype_member()
        attrs = ('label',)
        self.__test_rpr_for_member(dt_in, (XmlMime,), attrs)

    def test_gene_representer(self):
        ge_in = self._get_member(IGene, '641434')
        attrs = ('accession', 'locus_name')
        self.__test_rpr_for_member(ge_in, (XmlMime,), attrs)

    def test_itemstatus_representer(self):
        is_in = self._get_member(IItemStatus, 'future')
        attrs = ('name', 'description')
        self.__test_rpr_for_member(is_in, (XmlMime,), attrs)

    def test_container_representer(self):
        coll = create_staging_collection(ITube)
        tube_mb = self._create_tube_member()
        tube = tube_mb.get_entity()
        sample = self._create_sample(container=tube)
        sample.sample_molecules.append(self._create_sample_molecule())
        coll.add(tube_mb)
        str_rpr = self._to_string(coll, XmlMime)
        self.assert_true(len(str_rpr) > 0)
#        self.__test_rpr_for_collection(coll, (XmlMime,),
#                                       'sample_volume')

#    def test_job_representer(self):
#        j_in = self._create_job_member()
#        attrs = ('label', 'user')
#        self.__test_rpr_for_member(j_in, (XmlMime,), attrs)

    def test_location_representer(self):
        loc_in = self._create_location_member()
        str_rpr = self._to_string(loc_in, XmlMime)
        self.assert_true(len(str_rpr) > 0)

#    def test_experiment(self):
#        exp = self._create_experiment_member()
#        attrs = ('label', )
#        self.__test_rpr_for_member(exp, (XmlMime,), attrs)

#    def test_experimentdesign_representer(self):
#        design_in = self._create_experimentdesign_member()
#        attrs = ('label', )
#        self.__test_rpr_for_member(design_in, (XmlMime,), attrs)

#    def test_moleculedesign_representer(self):
#        md_in = self._get_member(IMoleculeDesignCollection, '11')
#        attrs = ('id','modification')
#        self.__test_rpr_for_member(md_in, (XmlMime,), attrs)

    #FIXME: not working #pylint: disable=W0511
#    def test_moleculetype_representer(self):
#        loc_in = self._create_moleculetype_member()
#        attrs = ('name', )
#        self.__test_rpr_for_member(loc_in, (XmlMime,), attrs)

    def test_organization_representer(self):
        dev_in = self._create_organization_member()
        attrs = get_resource_class_attribute_names(OrganizationMember)
        self.__test_rpr_for_member(dev_in, (XmlMime,), attrs)

    def test_project_representer(self):
        prj_in = self._create_project_member()
        self.assert_equal(len(prj_in.subprojects), 0)
        sprj = self._create_subproject_member()
        prj_in.subprojects.add(sprj)
        self.assert_equal(len(prj_in.subprojects), 1)
        # We need to add the new project to the root collection so that the
        # link of the subproject back to the project can be resolved.
        get_root_collection(prj_in).add(prj_in)
        attrs = ('label', 'leader.username', 'customer.name')
        self.__test_rpr_for_member(prj_in, (XmlMime,), attrs)

    def test_species_representer(self):
        sc_in = self._create_species_member()
        attrs = ('genus_name', 'species_name', 'common_name',
                 'acronym', 'ncbi_tax_id')
        self.__test_rpr_for_member(sc_in, (XmlMime,), attrs)

    def test_stock_info_representer(self):
        si_in = self._get_member(IStockInfo)
        str_rpr = self._to_string(si_in, XmlMime)
        self.assert_true(len(str_rpr) > 0)
        self.assert_not_equal(str_rpr.find('id="ssmds'), -1)

#    def test_target_representer(self):
#        tr = self._create_transcript_member().get_entity()
##        md = self._create_moleculedesign_member().get_entity()
#        ta_in = TargetMember.create_from_data(dict(transcript=tr,
#                                                   molecule_design=md))
#        attrs = ('transcript','molecule_design')
#        self.__test_rpr_for_member(ta_in, (XmlMime,), attrs, False)

#    def test_transcript_representer(self):
#        tr_in = self._create_transcript_member()
#        attrs = ('accession', 'gene', 'species')
#        self.__test_rpr_for_member(tr_in, (XmlMime,), attrs, False)

    def test_atom_project_member_representer(self):
        prj_mb = self._create_project_member()
        rpr_out = AtomResourceRepresenter.create_from_resource_class(prj_mb)
        str_rpr = rpr_out.to_string(prj_mb)
        self.assert_true(str_rpr.find('<title>TestProject</title>') != -1)

    def test_atom_project_collection_representer(self):
        prj_coll = self._get_collection(IProject)
        rpr_out = AtomResourceRepresenter.create_from_resource_class(prj_coll)
        str_rpr = rpr_out.to_string(prj_coll)
        self.assert_true(str_rpr.find('<title>Projects</title>') != -1)

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
                self.assert_equal(self.__getattr(member, attribute),
                                  self.__getattr(mb_reloaded, attribute))

    def __test_rpr_for_member(self, member, content_types, attributes):
        for cnt_type in content_types:
            str_rpr = self._to_string(member, cnt_type)
            mb_reloaded = self._to_resource(str_rpr, type(member), cnt_type)
            for attr in attributes:
                value_in = self.__getattr(member, attr)
                value_reloaded = self.__getattr(mb_reloaded, attr)
                self.assert_equal(value_in, value_reloaded)

    def __read_pkg_stream(self, pkg_res_name):
        return resource_stream(*pkg_res_name.split(':'))

    def __getattr(self, resource, attr):
        # Recursive attribute access with dotted attribute specifiers.
        value = resource
        for token in attr.split('.'):
            value = getattr(value, token)
        return value
