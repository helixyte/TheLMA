import pytest
from sqlalchemy.exc import IntegrityError

from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestGeneEntity(TestEntityBase):
    def test_init(self, gene_fac):
        gene = gene_fac()
        assert gene.slug == slug_from_string(gene.accession)
        check_attributes(gene, gene_fac.init_kw)

    @pytest.mark.parametrize('kw1,kw2,result',
                             [(dict(id=-1), dict(id=-1, accession='foo'),
                               False),
                              (dict(id=-1), dict(id=-2), True)])
    def test_equality(self, gene_fac, kw1, kw2, result):
        g1 = gene_fac(**kw1)
        g2 = gene_fac(**kw2)
        assert (g1 == g2) is result

    def test_persist(self, nested_session, gene_fac):
        gene = gene_fac()
        # The gene table is a materialized view; we should not be able to
        # insert new records here.
        with pytest.raises(IntegrityError):
            persist(nested_session, gene, gene_fac.init_kw, True)

