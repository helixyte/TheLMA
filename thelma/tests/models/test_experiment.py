"""
Created on May 26, 2011

@author: berger
"""

from everest.testing import RdbContextManager
from everest.testing import check_attributes
from everest.testing import persist
from pyramid.testing import DummyRequest
from thelma.interfaces import IPlate
from thelma.interfaces import IPlateSpecs
from thelma.interfaces import IRackShape
from thelma.interfaces import ISubproject
from thelma.interfaces import ITubeRack
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.experiment import ExperimentMetadata
from thelma.models.experiment import ExperimentRack
from thelma.models.job import ExperimentJob
from thelma.models.rack import Rack
from thelma.models.rack import RackShape
from thelma.models.rack import RackSpecs
from thelma.models.rack import rack_shape_from_rows_columns
from thelma.models.racklayout import RackLayout
from thelma.testing import ThelmaModelTestCase
from thelma.testing import create_extra_environ


class ExperimentModelTestCase(ThelmaModelTestCase):

    def set_up(self):
        super(ExperimentModelTestCase, self).set_up()
        self.init_data = \
            dict(label='my experiment',
                 destination_rack_specs=self._get_entity(IPlateSpecs),
                 source_rack=self._get_entity(ITubeRack),
                 )

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.init_data

    def _custom_configure(self):
        #
        request = DummyRequest(registry=self.config.registry,
                               environ=create_extra_environ())
        self.config.begin(request=request)

    def test_load_2_experiments(self):
        with RdbContextManager() as session:
            query = session.query(Experiment)
            experiments = query.limit(2).all()
            self.assert_equal(len(experiments), 2)

    def test_create_experiment(self):
        with RdbContextManager() as session:
            specs = \
                session.query(RackSpecs).filter_by(name='STD96').one()
            source_rack = \
                session.query(Rack).filter_by(barcode='02367784').one()
            design = \
                session.query(ExperimentDesign).filter_by(id='2').one()
            job = \
                session.query(ExperimentJob).filter_by(id='1550').one()
            attrs = dict(label='test experiment',
                         destination_rack_specs=specs,
                         source_rack=source_rack,
                         job=job,
                         experiment_design=design)
            persist(session, Experiment, attrs)
            attrs['label'] = 'test experiment 2'
            persist(session, Experiment, attrs)

    def test_init(self):
        exp = self._create_experiment(**self.init_data)
        self.assert_false(exp is None)
        check_attributes(exp, self.init_data)
        self.assert_false(exp.experiment_design is None)
        self.assert_equal(len(exp.experiment_racks), 1)

    def test_equality(self):
        exp1 = self._create_experiment(**self.init_data)
        self.init_data['source_rack'] = self._get_entity(IPlate)
        exp2 = self._create_experiment(**self.init_data)
        self.init_data['experiment_design'] = exp1.experiment_design
        self.init_data['source_rack'] = exp1.source_rack
        exp3 = self._create_experiment(**self.init_data)
        self.assert_not_equal(exp1, exp2)
        self.assert_equal(exp1, exp3)


class ExperimentRackTestCase(ThelmaModelTestCase):

    model_class = ExperimentRack

    def set_up(self):
        super(ExperimentRackTestCase, self).set_up()
        self.init_data = \
            dict(experiment=self._create_experiment(),
                 design_rack=self._create_experiment_design_rack(),
                 rack=self._create_tube_rack(),
                 )

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.init_data

    def test_load_10_experiment_racks(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            experiment_racks = query.limit(10).all()
            self.assert_equal(len(experiment_racks), 10)

    def test_init(self):
        exp_rack = self._create_experiment_rack(**self.init_data)
        self.assert_false(exp_rack is None)
        check_attributes(exp_rack, self.init_data)

    def test_equality(self):
        exp_rack1 = self._create_experiment_rack(id= -1)
        exp_rack2 = self._create_experiment_rack(id= -2)
        exp_rack3 = self._create_experiment_rack(**self.init_data)
        exp_rack3.id = exp_rack2.id
        self.assert_not_equal(exp_rack1, exp_rack2)
        self.assert_equal(exp_rack2, exp_rack3)


class ExperimentDesignModelTest(ThelmaModelTestCase):

    model_class = ExperimentDesign

    def set_up(self):
        super(ExperimentDesignModelTest, self).set_up()
        self.init_data = \
            dict(rack_shape=rack_shape_from_rows_columns(8, 12),
                 experiment_design_racks=
                            [self._create_experiment_design_rack()])

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.init_data

    def test_load_2_experiment_designs(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            experiment_designs = query.limit(2).all()
            self.assert_equal(len(experiment_designs), 2)

    def test_experiment_design_values(self):
        with RdbContextManager() as session:
            ed = session.query(self.model_class).filter_by(id=1).one()
            rs = session.query(RackShape).filter_by(name='16x24').one()
            edr1 = session.query(ExperimentDesignRack).filter_by(id=111).one()
            edr2 = session.query(ExperimentDesignRack).filter_by(id=113).one()
            edr3 = session.query(ExperimentDesignRack).filter_by(id=112).one()
            edrs = [edr1, edr2, edr3]
            attrs = dict(id=1, rack_shape=rs, design_racks=edrs)
            check_attributes(ed, attrs)

    def test_init(self):
        ed = self._create_experiment_design(**self.init_data)
        self.assert_false(ed is None)
        self.init_data['design_racks'] = self.init_data['experiment_design_racks']
        del self.init_data['experiment_design_racks']
        check_attributes(ed, self.init_data)
        self.assert_true(ed.slug is None)
        self.assert_equal(len(ed.design_racks), 1)

    def test_experiment_design_equality(self):
        ed1 = self._create_experiment_design(id= -1)
        ed2 = self._create_experiment_design(id= -2)
        ed3 = self._create_experiment_design(**self.init_data)
        ed3.id = ed2.id
        self.assert_not_equal(ed1, ed2)
        self.assert_equal(ed2, ed3)


class ExperimentDesignRackModelTest(ThelmaModelTestCase):

    model_class = ExperimentDesignRack

    def set_up(self):
        super(ExperimentDesignRackModelTest, self).set_up()
        self.init_data = dict(label='design_rack_label',
                              rack_layout=self._create_rack_layout(),
                              )

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.init_data

    def test_load_2_experiment_design_racks(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            experiment_design_racks = query.limit(2).all()
            self.assert_equal(len(experiment_design_racks), 2)

    def test_experiment_design_rack_values(self):
        with RdbContextManager() as session:
            edr = session.query(self.model_class).filter_by(id=111).one()
            rl = session.query(RackLayout).filter_by(id=419).one()
            attrs = dict(id=111, label='1', layout=rl)
            check_attributes(edr, attrs)

    def test_init(self):
        edr = self._create_experiment_design_rack(**self.init_data)
        self.assert_false(edr is None)
        self.init_data['layout'] = self.init_data['rack_layout']
        del self.init_data['rack_layout']
        check_attributes(edr, self.init_data)

    def test_equality(self):
        rl1 = self._create_rack_layout(id= -1)
        rl2 = self._create_rack_layout(id= -2)
        edr1 = self._create_experiment_design_rack(id= -3,
                                                   rack_layout=rl1)
        edr2 = self._create_experiment_design_rack(id= -4,
                                                   rack_layout=rl2)
        edr3 = self._create_experiment_design_rack(**self.init_data)
        edr3.id = edr2.id
        self.assert_not_equal(edr1, edr2)
        self.assert_equal(edr2, edr3)


class ExperimentMetadataModelTest(ThelmaModelTestCase):

    model_class = ExperimentMetadata

    def set_up(self):
        super(ExperimentMetadataModelTest, self).set_up()
        self.init_data = \
            dict(label='My Experiment Metadata',
                 ticket_number=9999,
                 subproject=self._get_entity(ISubproject),
                 number_replicates=3,
                 experiment_design=self._create_experiment_design(
                                    rack_shape=self._get_entity(IRackShape)))

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.init_data

    def test_load_2_experiment_metadatas(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            experiment_metadatas = query.limit(2).all()
            self.assert_equal(len(experiment_metadatas), 2)

    def test_experiment_metadata_init(self):
        em = self._create_experiment_metadata(**self.init_data)
        self.assert_is_not_none(em)
        check_attributes(em, self.init_data)

    def test_experiment_metadata_equality(self):
        subproject1 = self._create_subproject(label='sp1')
        subproject2 = self._create_subproject(label='sp2')
        label1 = 'label1'
        label2 = 'label2'
        em1 = self._create_experiment_metadata(subproject=subproject1,
                                               label=label1)
        em2 = self._create_experiment_metadata(subproject=subproject1,
                                               label=label1)
        em3 = self._create_experiment_metadata(subproject=subproject2,
                                               label=label1)
        em4 = self._create_experiment_metadata(subproject=subproject1,
                                               label=label2)
        self.assert_equal(em1, em2)
        self.assert_not_equal(em1, em3)
        self.assert_not_equal(em1, em4)
        self.assert_not_equal(em1, subproject1)
