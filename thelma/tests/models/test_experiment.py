"""
Created on May 26, 2011

@author: berger
"""
from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import persist
from thelma.interfaces import IExperimentMetadataType
from thelma.interfaces import IPlate
from thelma.interfaces import IRackShape
from thelma.interfaces import ISubproject
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.experiment import ExperimentMetadata
from thelma.models.experiment import ExperimentRack
from thelma.testing import ThelmaEntityTestCase


class ExperimentModelTestCase(ThelmaEntityTestCase):

    model_class = Experiment

    def _get_data(self):
        return dict(label='my experiment',
                 source_rack=self._get_entity(IPlate),
                 experiment_design=self._create_experiment_design())

    def test_init(self):
        exp = self._test_init()
        self.assert_is_not_none(exp.experiment_design)
        self.assert_equal(len(exp.experiment_racks), 0)

    def test_equality(self):
        ed1 = self._create_experiment_design(id=-1)
        ed2 = self._create_experiment_design(id=-2)
        rack1 = self._create_plate(id=-3)
        rack2 = self._create_plate(id=-4)
        exp1 = self._create_experiment(experiment_design=ed1,
                                       source_rack=rack1)
        exp2 = self._create_experiment(experiment_design=ed1,
                                       source_rack=rack1)
        exp3 = self._create_experiment(experiment_design=ed2,
                                       source_rack=rack1)
        exp4 = self._create_experiment(experiment_design=ed1,
                                       source_rack=rack2)
        self.assert_equal(exp1, exp2)
        self.assert_not_equal(exp1, exp3)
        self.assert_not_equal(exp1, exp4)
        self.assert_not_equal(exp1, ed1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self._get_data()
            exp = self._create_experiment()
            attrs['job'] = self._create_experiment_job(experiments=[exp])
            persist(session, self.model_class, attrs, True)


class ExperimentRackTestCase(ThelmaEntityTestCase):

    model_class = ExperimentRack

    def _get_data(self):
        return dict(experiment=self._create_experiment(),
                 design_rack=self._create_experiment_design_rack(),
                 rack=self._create_tube_rack())

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(self._create_experiment_rack)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class ExperimentDesignModelTest(ThelmaEntityTestCase):

    model_class = ExperimentDesign

    def _get_data(self):
        return dict(rack_shape=self._get_entity(IRackShape),
                    experiment_design_racks=
                            [self._create_experiment_design_rack()],
                    experiment_metadata=self._create_experiment_metadata())

    def test_init(self):
        self._test_init()

    def test_equality(self):
        self._test_id_based_equality(self._create_experiment_design)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class ExperimentDesignRackModelTest(ThelmaEntityTestCase):

    model_class = ExperimentDesignRack

    def _get_data(self):
        return dict(label='labelTest',
                    rack_layout=self._create_rack_layout(),
                    experiment_design=self._create_experiment_design())

    def test_init(self):
        self._test_init()

    def test_equality(self):
        # do not use the super class method (rack layouts must be unique)
        rl1 = self._create_rack_layout(id=-1)
        rl2 = self._create_rack_layout(id=-2)
        rl3 = self._create_rack_layout(id=-3)
        edr1 = self._create_experiment_design_rack(rack_layout=rl1, id=-1)
        edr2 = self._create_experiment_design_rack(rack_layout=rl2, id=-2)
        edr3 = self._create_experiment_design_rack(rack_layout=rl3)
        edr3.id = edr1.id
        self.assert_not_equal(edr1, edr2)
        self.assert_equal(edr1, edr3)
        self.assert_not_equal(edr1, rl1)

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()


class ExperimentMetadataModelTest(ThelmaEntityTestCase):

    model_class = ExperimentMetadata

    def _get_data(self):
        return dict(label='My Experiment Metadata',
                 ticket_number=9999,
                 subproject=self._get_entity(ISubproject),
                 number_replicates=3,
                 experiment_metadata_type=\
                                    self._get_entity(IExperimentMetadataType))

    def test_init(self):
        self._test_init()

    def test_equality(self):
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

    def test_load(self):
        self._test_load()

    def test_persist(self):
        self._test_persist()
