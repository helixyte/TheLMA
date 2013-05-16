"""
Gene resource.

NP
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IGene
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import ISpecies
from thelma.interfaces import ITarget
from thelma.interfaces import ITranscript
from thelma.resources.base import RELATION_BASE_URL
from thelma.interfaces import IMoleculeDesignPool


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/gene.py   $'

__all__ = ['GeneCollection',
           'GeneMember',
           'TargetCollection',
           'TargetMember',
           'TargetSetCollection',
           'TargetSetMember',
           'TranscriptCollection',
           'TranscriptMember',
           ]


class GeneMember(Member):
    relation = "%s/gene" % RELATION_BASE_URL
    title = attribute_alias('locus_name')

    accession = terminal_attribute(str, 'accession')
    locus_name = terminal_attribute(str, 'locus_name')
#    nice_name = terminal_attribute('nice_name')
    species = member_attribute(ISpecies, 'species')
    molecule_designs = collection_attribute(IMoleculeDesign,
                                            'molecule_designs',
                                            is_nested=False)
    molecule_design_pools = collection_attribute(IMoleculeDesignPool,
                                                 'molecule_design_pools',
                                                 is_nested=False)


class GeneCollection(Collection):
    title = 'Genes'
    root_name = 'genes'
    description = 'Manage Genes'
    default_order = AscendingOrderSpecification('accession')


class TranscriptMember(Member):
    relation = "%s/transcript" % RELATION_BASE_URL
    accession = terminal_attribute(str, 'accession')
    gene = member_attribute(IGene, 'gene')
    species = member_attribute(ISpecies, 'species')


class TranscriptCollection(Collection):
    title = 'Transcripts'
    root_name = 'transcripts'
    description = 'Manage Transcripts'
    default_order = AscendingOrderSpecification('accession')


class TargetMember(Member):
    relation = "%s/target" % RELATION_BASE_URL
    transcript = member_attribute(ITranscript, 'transcript')
    molecule_design = member_attribute(IMoleculeDesign, 'molecule_design')


class TargetCollection(Collection):
    title = 'Targets'
    root_name = 'targets'
    description = 'Manage Targets'
    default_order = AscendingOrderSpecification('transcript')


class TargetSetMember(Member):
    relation = "%s/target-set" % RELATION_BASE_URL
    targets = collection_attribute(ITarget, 'targets')


class TargetSetCollection(Collection):
    title = 'Target Sets'
    root_name = 'target-sets'
    description = 'Manage Target Sets'
