"""
Stock audit - report amount and concentration for stock samples by
molecule type.
"""
from collections import OrderedDict
from csv import Dialect
from csv import DictWriter
from csv import QUOTE_NONNUMERIC
from csv import register_dialect

from everest.repositories.rdb.session import ScopedSessionMaker as Session
from thelma.tools.base import BaseTool


__docformat__ = 'reStructuredText en'
__all__ = ['StockAuditReporter',
           ]


class AuditCsvDialect(Dialect): # ignore no __init__ pylint: disable=W0232
    """
    Dialect to use when exporting audit results to CSV.
    """
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = QUOTE_NONNUMERIC
register_dialect('audit', AuditCsvDialect)


class StockAuditReporter(BaseTool):
    """
    Reporter for stock audits.

    You may need to define a "first" aggregate function in the SQL backend: ::

    -- Create a function that always returns the first non-NULL item
    CREATE OR REPLACE FUNCTION public.first_agg ( anyelement, anyelement )
    RETURNS anyelement LANGUAGE sql IMMUTABLE STRICT AS $$
            SELECT $1;
    $$;

    -- And then wrap an aggregate around it
    CREATE AGGREGATE public.first (
            sfunc    = public.first_agg,
            basetype = anyelement,
            stype    = anyelement
    );

    Taken from https://wiki.postgresql.org/wiki/First/last_(aggregate)
    """
    QUERY_TEMPLATE = """
     select first(ss.molecule_design_set_id) as cenixpoolid,
            string_agg(cast(md.molecule_design_id as text), ';' order by md.molecule_design_id) as cenixolddesignids,
            first(cb.barcode) as tubebarcode,
            round(first(sm.concentration)*count(sm.concentration)*1e6) as concentration,
            s.volume*round(first(sm.concentration)*count(sm.concentration)*1e9) as amount,
            first(o.name) as supplier,
            first(sr.volume)*round(first(sm.concentration)*first(mdp.number_designs)*1e9) as initialamount
            %s
     from container c
            inner join container_barcode cb on cb.container_id = c.container_id
            inner join container_specs cs on cs.container_specs_id = c.container_specs_id
            inner join sample s on s.container_id = c.container_id
            left join stock_sample ss on ss.sample_id = s.sample_id
            left join molecule_design_pool mdp on mdp.molecule_design_set_id = ss.molecule_design_set_id
            left join sample_registration sr on sr.sample_id=s.sample_id
            inner join sample_molecule sm on sm.sample_id = s.sample_id
            inner join molecule m on m.molecule_id = sm.molecule_id
            inner join organization o on o.organization_id = m.supplier_id
            inner join molecule_design md on md.molecule_design_id = m.molecule_design_id
            left join (select mds.molecule_design_id, chs.representation
                       from molecule_design_structure mds
                           inner join chemical_structure chs
                           on (chs.chemical_structure_id = mds.chemical_structure_id and chs.structure_type = 'MODIFICATION')) as structs
                on structs.molecule_design_id=md.molecule_design_id
     left join (select set.label, sss.sample_id from sample_set set
                    inner join sample_set_sample sss on sss.sample_set_id = set.sample_set_id
                           and set.sample_set_type='ORDER') as set on set.sample_id = s.sample_id
     where cs.name='MATRIX0500'
       and c.item_status='MANAGED'
       and md.molecule_type = '%s'
       %s
     group by s.sample_id
     order by %s first(o.name), first(sm.concentration) desc, first(ss.molecule_design_set_id)
     """
#    QUERY_TEMPLATE = """
#    select md.molecule_design_id as cenixdesignid,
#           cb.barcode as tubebarcode,
#           sm.concentration*1e6 as concentration,
#           s.volume*sm.concentration*1e9 as amount,
#           o.name as supplier,
#           sr.volume*sm.concentration*1e9 as initialamount
#           %s
#      from container c
#            inner join container_barcode cb on cb.container_id = c.container_id
#            inner join container_specs cs on cs.container_specs_id = c.container_specs_id
#            inner join sample s on s.container_id = c.container_id
#            left join sample_registration sr on sr.sample_id=s.sample_id
#            inner join sample_molecule sm on sm.sample_id = s.sample_id
#            inner join molecule m on m.molecule_id = sm.molecule_id
#            inner join organization o on o.organization_id = m.supplier_id
#            inner join molecule_design md on md.molecule_design_id = m.molecule_design_id
#            left join (select mds.molecule_design_id, chs.representation
#                       from molecule_design_structure mds
#                           inner join chemical_structure chs
#                           on (chs.chemical_structure_id = mds.chemical_structure_id and chs.structure_type = 'MODIFICATION')) as structs
#                on structs.molecule_design_id=md.molecule_design_id
#      left join (select ss.label, sss.sample_id from sample_set ss
#                    inner join sample_set_sample sss on sss.sample_set_id = ss.sample_set_id
#                           and ss.sample_set_type='ORDER') as ss on ss.sample_id = s.sample_id
#     where cs.name='MATRIX0500'
#       and c.item_status='MANAGED'
#       and md.molecule_type = '%s'
#       %s
#     order by %s o.name, sm.concentration desc, m.molecule_design_id
#    """
    CUSTOM_BITS = \
      {'SIRNA' :
         (
          """, case when (first(set.label) in ('ORD_103', 'ORD_106')) then 'old'
            when (first(set.label) in ('ORD_253')) then 'new'
            when (first(mdp.number_designs) = 3) then 'pool'
            else 'no'
            end as \"library\",
            case when (first(structs.representation) is null) then 'unmodified'
            else first(structs.representation)
            end as \"modification\",
            case when (first(structs.representation) = 'Ambion H') then 'yes'
            else 'no'
            end as \"silencerselect\"
          """,
          'SIRNA',
          '',
          """library, """),
       'COMPOUND' :
         ('',
          'COMPOUND',
          '',
    #      "and organization.name != 'Microsource Discovery Systems' ",
          ''),
        'SSDNA' :
         ('',
          'SSDNA',
          '',
          ''),
        'ESI_RNA' :
        ('',
         'ESI_RNA',
         '',
         ''),
       'MIRNA_INHI' :
         (""", case when (first(set.label) in ('ORD_357', 'ORD_361', 'ORD_364', 'ORD_367', 'ORD_402')) then 'Y'
            else 'N'
            end as \"library\"
          """,
          'MIRNA_INHI',
          '',
          """library desc, """),
       'MIRNA_MIMI' :
         (""", case when (first(set.label) in ('ORD_358', 'ORD_359', 'ORD_362', 'ORD_365')) then 'Y'
            else 'N'
            end as \"library\"
          """,
          'MIRNA_MIMI',
          '',
          """library desc, """),
        }
    COLUMN_MAP = OrderedDict(cenixpoolid='Cenix Pool ID',
                             cenixolddesignids='Cenix Old Design IDs',
                             tubebarcode='Tube Barcode',
                             concentration='Concentration',
                             amount='Amount',
                             supplier='Supplier',
                             initialamount='Initial Amount')
    def __init__(self, molecule_type, output_file, parent=None):
        BaseTool.__init__(self, parent=parent)
        self.__molecule_type = molecule_type
        self.__output_file = output_file

    def reset(self):
        self.__molecule_type = None
        self.__output_file = None

    def run(self):
        session = Session()
        query = self.QUERY_TEMPLATE % self.CUSTOM_BITS[self.__molecule_type]
        self.add_info('Running stock query for %s molecules.\n%s' %
                      (self.__molecule_type, query))
        records = session.execute(query)
        column_map = self.COLUMN_MAP.copy()
        if self.__molecule_type == 'SIRNA':
            column_map['library'] = 'Ambion Library'
            column_map['modification'] = 'Modification'
            column_map['silencerselect'] = 'Silencer Select'
        elif self.__molecule_type in ('MIRNA_INHI', 'MIRNA_MIMI'):
            column_map['library'] = 'Library Y/N'
        csv_file = open(self.__output_file, 'w')
        with csv_file:
            csv_writer = DictWriter(csv_file, column_map.values(),
                                    dialect='audit')
            self.add_info('Exporting audit report to file "%s".'
                          % self.__output_file)
            number_records = 0
            csv_writer.writeheader()
            for record in records:
                # Translate keys to labels.
                rec_map = {}
                for key, label in column_map.iteritems():
                    rec_map[label] = record[key]
                csv_writer.writerow(rec_map)
                number_records += 1
            self.add_info('Wrote %d records to file.' % number_records)
