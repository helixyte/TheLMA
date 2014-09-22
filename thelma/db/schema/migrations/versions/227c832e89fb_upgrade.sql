--
-- PostgreSQL database dump
--

-- Dumped from database version 9.2.3
-- Dumped by pg_dump version 9.2.6
-- Started on 2014-09-12 16:16:40 CEST

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 481 (class 3079 OID 12513)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 4973 (class 0 OID 0)
-- Dependencies: 481
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- TOC entry 846 (class 1247 OID 16783283)
-- Name: aa; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN aa AS text
	CONSTRAINT aa_check CHECK ((VALUE !~ '[^A-Z]'::text));


ALTER DOMAIN public.aa OWNER TO postgres;

--
-- TOC entry 4974 (class 0 OID 0)
-- Dependencies: 846
-- Name: DOMAIN aa; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN aa IS 'Amino acid sequence.

Consider renaming to amino_acid.  It is immediately obvious what ''dna''
stands for.  The same can not be said for ''aa''';


--
-- TOC entry 848 (class 1247 OID 16783285)
-- Name: cenix_barcode; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN cenix_barcode AS character(8)
	CONSTRAINT cenix_barcode_check CHECK ((VALUE ~ similar_escape('[0-9]+'::text, NULL::text)));


ALTER DOMAIN public.cenix_barcode OWNER TO postgres;

--
-- TOC entry 850 (class 1247 OID 16783287)
-- Name: concentration; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN concentration AS double precision
	CONSTRAINT concentration_check CHECK ((VALUE > (0)::double precision));


ALTER DOMAIN public.concentration OWNER TO postgres;

--
-- TOC entry 4975 (class 0 OID 0)
-- Dependencies: 850
-- Name: DOMAIN concentration; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN concentration IS 'concentration units are moles/liter';


--
-- TOC entry 852 (class 1247 OID 16783291)
-- Name: dblink_pkey_results; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE dblink_pkey_results AS (
	"position" integer,
	colname text
);


ALTER TYPE public.dblink_pkey_results OWNER TO postgres;

--
-- TOC entry 855 (class 1247 OID 16783292)
-- Name: dna; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN dna AS text
	CONSTRAINT dna_check CHECK ((VALUE !~ '[^A|T|G|C|N|M|R|W|S|Y|K|V|H|D|B|X]'::text));


ALTER DOMAIN public.dna OWNER TO postgres;

--
-- TOC entry 4976 (class 0 OID 0)
-- Dependencies: 855
-- Name: DOMAIN dna; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN dna IS 'DNA sequence.';


--
-- TOC entry 857 (class 1247 OID 16783294)
-- Name: experiment_sample_status; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN experiment_sample_status AS text
	CONSTRAINT experiment_sample_status_check CHECK ((VALUE = ANY (ARRAY['no_sirna'::text, 'untransfected'::text, 'unspecific'::text, 'positive_control'::text, 'sample'::text])));


ALTER DOMAIN public.experiment_sample_status OWNER TO postgres;

--
-- TOC entry 4977 (class 0 OID 0)
-- Dependencies: 857
-- Name: DOMAIN experiment_sample_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN experiment_sample_status IS 'Status of experiment_sample

Allowed values:
    o no_sirna -- sample with no sirna
    o untransfected -- untransfected sample
    o unspecific -- negative control
    o positive_control -- positive control
    o sample -- sample';


--
-- TOC entry 859 (class 1247 OID 16783296)
-- Name: guid; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN guid AS character varying(36) NOT NULL
	CONSTRAINT guid_check CHECK (((VALUE)::text ~ '^[A-Za-z0-9]{8}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{12}$'::text));


ALTER DOMAIN public.guid OWNER TO postgres;

--
-- TOC entry 861 (class 1247 OID 16783298)
-- Name: name; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN name AS character varying
	CONSTRAINT "$1" CHECK (((VALUE)::text ~ similar_escape('[_A-Za-z][_A-Za-z0-9]+'::text, NULL::text)));


ALTER DOMAIN public.name OWNER TO postgres;

--
-- TOC entry 863 (class 1247 OID 16783300)
-- Name: normalization; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN normalization AS character varying(80);


ALTER DOMAIN public.normalization OWNER TO postgres;

--
-- TOC entry 4978 (class 0 OID 0)
-- Dependencies: 863
-- Name: DOMAIN normalization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN normalization IS 'Data normalization method

Allowed values:
    o plate_average
    o none
    o to_negative_control';


--
-- TOC entry 864 (class 1247 OID 16783301)
-- Name: nucleic_acid; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN nucleic_acid AS text
	CONSTRAINT nucleic_acid_check CHECK ((VALUE !~ '[^A|T|U|G|C|N|M|R|W|S|Y|K|V|H|D|B|X]'::text));


ALTER DOMAIN public.nucleic_acid OWNER TO postgres;

--
-- TOC entry 4979 (class 0 OID 0)
-- Dependencies: 864
-- Name: DOMAIN nucleic_acid; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN nucleic_acid IS 'Nucleic acid sequence (RNA, DNA or a mixture of the two).';


--
-- TOC entry 866 (class 1247 OID 16783303)
-- Name: orientation; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN orientation AS text
	CONSTRAINT orientation_check CHECK (((VALUE = 'sense'::text) OR (VALUE = 'antisense'::text)));


ALTER DOMAIN public.orientation OWNER TO postgres;

--
-- TOC entry 4980 (class 0 OID 0)
-- Dependencies: 866
-- Name: DOMAIN orientation; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN orientation IS 'Orientation for strand in double stranded nucleic acids

Allowed values:
    o sense -- strand which is to be read as 5p -> 3p
    o antisense -- strand which is to be read as 3p -> 5p';


--
-- TOC entry 868 (class 1247 OID 16783305)
-- Name: rna; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN rna AS text
	CONSTRAINT rna_check CHECK ((VALUE !~ '[^A|U|G|C|N|M|R|W|S|Y|K|V|H|D|B|X]'::text));


ALTER DOMAIN public.rna OWNER TO postgres;

--
-- TOC entry 4981 (class 0 OID 0)
-- Dependencies: 868
-- Name: DOMAIN rna; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN rna IS 'RNA sequence.';


--
-- TOC entry 870 (class 1247 OID 16783307)
-- Name: sequence_feature_type; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN sequence_feature_type AS character varying(11) NOT NULL
	CONSTRAINT sequence_feature_type_check CHECK (((VALUE)::text = ANY (ARRAY[('GENE'::character varying)::text, ('TRANSCRIPT'::character varying)::text, ('EXON'::character varying)::text, ('INTRON'::character varying)::text, ('SNP'::character varying)::text, ('REPEAT'::character varying)::text, ('AMPLICON'::character varying)::text, ('UTR_5_PRIME'::character varying)::text, ('UTR_3_PRIME'::character varying)::text])));


ALTER DOMAIN public.sequence_feature_type OWNER TO postgres;

--
-- TOC entry 4982 (class 0 OID 0)
-- Dependencies: 870
-- Name: DOMAIN sequence_feature_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN sequence_feature_type IS 'Type of sequence feature (modeled after Bioperl SeqFeatures).  These are
    located within a particular sequence (e.g. gene X is in chromosome Y
    between bps 1000 and 5000).

Valid values:
    o GENE -- gene
    o TRANSCRIPT -- transcript
    o EXON -- exon
    o INTRON -- intron
    o SNP -- snp
    o REPEAT -- sequence repeat
    o AMPLICON -- amplicon
    o UTR_5_PRIME -- 5p UTR
    o UTR_3_PRIME -- 3p UTR';


--
-- TOC entry 872 (class 1247 OID 16783309)
-- Name: status; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN status AS character varying(32);


ALTER DOMAIN public.status OWNER TO postgres;

--
-- TOC entry 4983 (class 0 OID 0)
-- Dependencies: 872
-- Name: DOMAIN status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN status IS 'Status of experiment_sample

Allowed values:
    o no_sirna -- sample with no sirna
    o untransfected -- untransfected sample
    o unspecific -- negative control
    o positive_control -- positive control
    o sample -- sample

Consider renaming to experiment_sample_status to avoid confusion with
item_status.';


--
-- TOC entry 873 (class 1247 OID 16783310)
-- Name: subproject_molecule_status; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN subproject_molecule_status AS character varying(17)
	CONSTRAINT subproject_molecule_status_check CHECK (((VALUE)::text = ANY (ARRAY[('QUEUED_ORDERING'::character varying)::text, ('QUEUED_REARRAYING'::character varying)::text, ('REARRAYED'::character varying)::text, ('FINALIZED'::character varying)::text])));


ALTER DOMAIN public.subproject_molecule_status OWNER TO postgres;

--
-- TOC entry 4984 (class 0 OID 0)
-- Dependencies: 873
-- Name: DOMAIN subproject_molecule_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN subproject_molecule_status IS 'Status of a molecule design within a subproject.

Valid values, in order of priority.  Later states take priority over earlier
states.
    o QUEUED_ORDERING -- the molecule design is not available in house and
          must be ordered.
    o QUEUED_REARRAYING -- the molecule design is available in house but has
          not yet been rearrayed into plates.
    o REARRAYED -- the molecule design has been rearrayed into plates
    o FINALIZED -- satisfactory final data has been obtained for the molecule
          design.

The following states were once allowed, but have been temporarily removed
because we do not have the tables in place to be able to determine whether
molecule designs are in those states:
    o ORDERED -- the molecule design has been ordered but has not yet been
          delivered.
    o ACQUIRED -- raw data has been acquired for the molecule design.';


--
-- TOC entry 875 (class 1247 OID 16783312)
-- Name: supplier_sense_strand; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN supplier_sense_strand AS character varying(10)
	CONSTRAINT supplier_sense_strand_check CHECK (((VALUE)::text = ANY (ARRAY[('sequence_1'::character varying)::text, ('sequence_2'::character varying)::text, ('unknown'::character varying)::text])));


ALTER DOMAIN public.supplier_sense_strand OWNER TO postgres;

--
-- TOC entry 4985 (class 0 OID 0)
-- Dependencies: 875
-- Name: DOMAIN supplier_sense_strand; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN supplier_sense_strand IS 'Tells which strand of double-stranded design has been designated by supplier as the sense strand';


--
-- TOC entry 877 (class 1247 OID 16783314)
-- Name: treatment; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN treatment AS character varying(32);


ALTER DOMAIN public.treatment OWNER TO postgres;

--
-- TOC entry 4986 (class 0 OID 0)
-- Dependencies: 877
-- Name: DOMAIN treatment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN treatment IS 'treatment applied to an experiment sample

Allowed values:
    o ZKA -- Schering cytostatic drug compound
    o DMSO -- Dimethyl Sulfoxdie';


--
-- TOC entry 878 (class 1247 OID 16783315)
-- Name: validation_result; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN validation_result AS character(6)
	CONSTRAINT validation_result CHECK (((VALUE = 'PASSED'::bpchar) OR (VALUE = 'FAILED'::bpchar)));


ALTER DOMAIN public.validation_result OWNER TO postgres;

--
-- TOC entry 4987 (class 0 OID 0)
-- Dependencies: 878
-- Name: DOMAIN validation_result; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON DOMAIN validation_result IS 'validation result of primer pair

Allowed values:
    o PASSED
    o FAILED';


--
-- TOC entry 494 (class 1255 OID 16783317)
-- Name: assert(character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION assert(character varying) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    expression alias for $1;
    r record;
begin
    for r in execute ('select (' || expression || ') as success') loop
        if not r.success then
            raise exception 'Assert failed!';
        end if;
    end loop;
    return;
end;    
$_$;


ALTER FUNCTION public.assert(character varying) OWNER TO postgres;

--
-- TOC entry 4988 (class 0 OID 0)
-- Dependencies: 494
-- Name: FUNCTION assert(character varying); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION assert(character varying) IS 'assert(expression)

Assert a boolean expression evaluates to TRUE.  If the expression is TRUE,
nothing happens.  If the expression is FALSE, the exception
''Assertion failed!'' is raised.

Use this to ensure assumptions made by migration scripts hold before attempting
operations that could produce incorrect results if the assumptions are
violated';


--
-- TOC entry 495 (class 1255 OID 16783318)
-- Name: assert_db_version(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION assert_db_version(integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
begin
    if ((select version from db_version) <> $1) then
        raise exception 'version mismatch';
    end if;
    return;
end;
$_$;


ALTER FUNCTION public.assert_db_version(integer) OWNER TO postgres;

--
-- TOC entry 4989 (class 0 OID 0)
-- Dependencies: 495
-- Name: FUNCTION assert_db_version(integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION assert_db_version(integer) IS 'assert_db_version(db_version)

DEPRECATED

Assert the current database version matches db_version.  This does not work
as intended, even for integer version numbers and should be dropped.';


--
-- TOC entry 496 (class 1255 OID 16783319)
-- Name: assertion_trigger(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION assertion_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
    perform check_assertions_for_table(tg_argv[0]);
    return null;
end;
$$;


ALTER FUNCTION public.assertion_trigger() OWNER TO postgres;

--
-- TOC entry 4990 (class 0 OID 0)
-- Dependencies: 496
-- Name: FUNCTION assertion_trigger(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION assertion_trigger() IS 'assertion_trigger() returns "trigger"

DEPRECATED

This was part of an experimental substitute for the SQL-92 CREATE ASSERTION
statement.  Performance of the scheme was unacceptable.  Should be dropped.';


--
-- TOC entry 497 (class 1255 OID 16783320)
-- Name: check_all_assertions(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION check_all_assertions() RETURNS void
    LANGUAGE plpgsql
    AS $$
declare
    r record;
begin
    for r in select assertion_name, expression
              from _assertion loop
        perform check_expression(r.expression, r.assertion_name);
    end loop;
    return;
end;
$$;


ALTER FUNCTION public.check_all_assertions() OWNER TO postgres;

--
-- TOC entry 4991 (class 0 OID 0)
-- Dependencies: 497
-- Name: FUNCTION check_all_assertions(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION check_all_assertions() IS 'check_all_assertions()

DEPRECATED

This was part of an experimental substitute for the SQL-92 CREATE ASSERTION
statement.  Performance of the scheme was unacceptable.  Should be dropped.

Check all assertions in the _assertion table are satisfied.';


--
-- TOC entry 498 (class 1255 OID 16783321)
-- Name: check_expression(character varying, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION check_expression(character varying, character varying) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    expression alias for $1;
    assertion_name alias for $2;
    r record;
begin
    for r in execute ('select (' || expression || ') as success') loop
        if not r.success then
            raise exception 'Assertion % failed!', assertion_name;
        end if;
    end loop;
    return;
end;    
$_$;


ALTER FUNCTION public.check_expression(character varying, character varying) OWNER TO postgres;

--
-- TOC entry 4992 (class 0 OID 0)
-- Dependencies: 498
-- Name: FUNCTION check_expression(character varying, character varying); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION check_expression(character varying, character varying) IS 'check_expression(expression, assertion_name)

DEPRECATED

This was part of an experimental substitute for the SQL-92 CREATE ASSERTION
statement.  Performance of the scheme was unacceptable.  Should be dropped.

Check expression evaluates to TRUE.  If the expression is TRUE,
nothing happens.  If the expression is FALSE, the exception
''Assertion <assertion_name> failed!'' is raised.';


--
-- TOC entry 499 (class 1255 OID 16783322)
-- Name: commacat(text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION commacat(acc text, instr text) RETURNS text
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF acc IS NULL OR acc = '' THEN
      RETURN instr;
    ELSE
      RETURN acc || ', ' || instr;
    END IF;
  END;
$$;


ALTER FUNCTION public.commacat(acc text, instr text) OWNER TO postgres;

--
-- TOC entry 500 (class 1255 OID 16783323)
-- Name: first_agg(anyelement, anyelement); Type: FUNCTION; Schema: public; Owner: gathmann
--

CREATE FUNCTION first_agg(anyelement, anyelement) RETURNS anyelement
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
        SELECT $1;
$_$;


ALTER FUNCTION public.first_agg(anyelement, anyelement) OWNER TO gathmann;

--
-- TOC entry 503 (class 1255 OID 16783324)
-- Name: insert_double_stranded_design_view(integer, character varying, nucleic_acid, nucleic_acid, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_double_stranded_design_view(integer, character varying, nucleic_acid, nucleic_acid, character varying) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_molecule_design_id alias for $1;
    new_molecule_type alias for $2;
    new_sequence_1 alias for $3;
    new_sequence_2 alias for $4;
    new_modification alias for $5;
    molecule_design_exists boolean;
begin
    if new_molecule_design_id is null then
        insert into molecule_design (molecule_type)
             values (new_molecule_type);
        insert into double_stranded_design (molecule_design_id,
                                            sequence_1,
                                            sequence_2,
                                            modification)
             values ((select currval('molecule_design_molecule_design_id_seq')),
                     least(new_sequence_1, new_sequence_2),
                     greatest(new_sequence_1, new_sequence_2),
                     new_modification);
    else
        select into molecule_design_exists
               (select exists (select molecule_design_id
                                 from molecule_design
                                where molecule_design_id =
                                          new_molecule_design_id));
        if not molecule_design_exists then
            insert into molecule_design (molecule_design_id, molecule_type)
                 values (new_molecule_design_id, new_molecule_type);
        end if;
        insert into double_stranded_design (molecule_design_id,
                                            sequence_1,
                                            sequence_2,
                                            modification)
             values (new_molecule_design_id,
                     least(new_sequence_1, new_sequence_2),
                     greatest(new_sequence_1, new_sequence_2),
                     new_modification);
    end if;
    return;
end;
$_$;


ALTER FUNCTION public.insert_double_stranded_design_view(integer, character varying, nucleic_acid, nucleic_acid, character varying) OWNER TO postgres;

--
-- TOC entry 4993 (class 0 OID 0)
-- Dependencies: 503
-- Name: FUNCTION insert_double_stranded_design_view(integer, character varying, nucleic_acid, nucleic_acid, character varying); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION insert_double_stranded_design_view(integer, character varying, nucleic_acid, nucleic_acid, character varying) IS 'insert_double_stranded_design_view(new_molecule_design_id,
                                    new_molecule_type,
                                    new_sequence_1,
                                    new_sequence_2,
                                    new_modification)

Support insertion into view double_stranded_design_view.

Do not call directly.  Use an insert statement on double_stranded_design_view
instead.

Parameters:
    o new_molecule_design_id (optional) -- if NULL, a new molecule_design
          record will be inserted.
    o new_molecule_type (mandatory)
    o new_sequence_1 (mandatory) -- consider changing type to nucleic_acid
    o new_sequence_2 (mandatory) -- consider changing type to nucleic_acid
    o new_modification (manadatory)

Precondition: new_sequence_1 < new_sequence_2';


--
-- TOC entry 504 (class 1255 OID 16783325)
-- Name: insert_racked_molecule_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision, integer, double precision); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_racked_molecule_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision, integer, double precision) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_container_specs_name alias for $1;
    new_item_status alias for $2;
    new_container_barcode alias for $3;
    new_rack_barcode alias for $4;
    new_row alias for $5;
    new_col alias for $6;
    new_volume alias for $7;
    new_molecule_design_id alias for $8;
    new_concentration alias for $9;
begin
    insert
      into racked_sample (container_specs_name, item_status,
                          container_barcode, rack_barcode, row, col, volume)
    values (new_container_specs_name, new_item_status,
            new_container_barcode, new_rack_barcode, new_row, new_col,
            new_volume);
    insert
      into molecule (molecule_design_id)
    values (new_molecule_design_id);
    insert
      into sample_molecule (sample_id, molecule_id, concentration)
    values (currval('sample_sample_id_seq'),
            currval('molecule_molecule_id_seq'),
            new_concentration);
    return;
end;
$_$;


ALTER FUNCTION public.insert_racked_molecule_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision, integer, double precision) OWNER TO postgres;

--
-- TOC entry 505 (class 1255 OID 16783326)
-- Name: insert_racked_sample(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer, double precision); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_racked_sample(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer, double precision) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_container_specs_name alias for $1;
    new_item_status_name alias for $2;
    new_container_barcode alias for $3;
    new_rack_barcode alias for $4;
    new_row alias for $5;
    new_col alias for $6;
    new_volume alias for $7;
begin
    insert
      into racked_tube (container_specs_name, item_status_name,
	  				    container_barcode, rack_barcode, row, col)
    values (new_container_specs_name, new_item_status_name,
			new_container_barcode, new_rack_barcode, new_row, new_col);
    insert
      into sample (container_id, volume)
    values ((select container_id
               from container_barcode
              where barcode = new_container_barcode),
            new_volume);
    return;
end;$_$;


ALTER FUNCTION public.insert_racked_sample(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer, double precision) OWNER TO postgres;

--
-- TOC entry 4994 (class 0 OID 0)
-- Dependencies: 505
-- Name: FUNCTION insert_racked_sample(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer, double precision); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION insert_racked_sample(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer, double precision) IS 'insert_racked_sample(new_container_specs_name,
                      new_item_status_name,
                      new_container_barcode,
                      new_rack_barcode,
                      new_row,
                      new_col,
                      new_volume)

DEPRECATED

This function supported insertion into an earlier version of racked_sample.
Should be dropped.';


--
-- TOC entry 506 (class 1255 OID 16783327)
-- Name: insert_racked_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_racked_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_container_specs_name alias for $1;
    new_item_status alias for $2;
    new_container_barcode alias for $3;
    new_rack_barcode alias for $4;
    new_row alias for $5;
    new_col alias for $6;
    new_volume alias for $7;
begin
    insert
      into racked_tube (container_specs_name, item_status,
                          container_barcode, rack_barcode, row, col)
    values (new_container_specs_name, new_item_status,
            new_container_barcode, new_rack_barcode, new_row, new_col);
    insert
      into sample (container_id, volume)
    values ((select container_id
               from container_barcode
              where barcode = new_container_barcode),
            new_volume);
    return;
end;
$_$;


ALTER FUNCTION public.insert_racked_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision) OWNER TO postgres;

--
-- TOC entry 4995 (class 0 OID 0)
-- Dependencies: 506
-- Name: FUNCTION insert_racked_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION insert_racked_sample(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer, double precision) IS 'insert_racked_sample(new_container_specs_name,
                      new_item_status,
                      new_container_barcode,
                      new_rack_barcode,
                      new_row,
                      new_col,
                      new_volume)

Support insertion into view racked_sample.

Do not call directly.  Use an insert statement on racked_sample instead.';


--
-- TOC entry 501 (class 1255 OID 16783328)
-- Name: insert_racked_tube(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_racked_tube(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_container_specs_name alias for $1;
    new_item_status_name alias for $2;
    new_container_barcode alias for $3;
    new_rack_barcode alias for $4;
    new_row alias for $5;
    new_col alias for $6;
begin
    insert
      into container (container_specs_id, item_status_id)
    values ((select container_specs_id
        	   from container_specs
    	      where name = new_container_specs_name),
    		(select item_status_id
    		   from item_status
    		  where name = new_item_status_name));
    insert
      into containment (holder_id, held_id, row, col)
    values ((select rack_id
               from rack
              where barcode = new_rack_barcode),
            (select currval('container_container_id_seq')),
            new_row, new_col);
    insert
      into container_barcode (container_id, barcode)
    values ((select currval('container_container_id_seq')),
            new_container_barcode);
    return;
end;$_$;


ALTER FUNCTION public.insert_racked_tube(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer) OWNER TO postgres;

--
-- TOC entry 4996 (class 0 OID 0)
-- Dependencies: 501
-- Name: FUNCTION insert_racked_tube(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION insert_racked_tube(pg_catalog.name, pg_catalog.name, character varying, integer, integer, integer) IS 'insert_racked_tube(new_container_specs_name,
                    new_item_status_name,
                    new_container_barcode,
                    new_rack_barcode,
                    new_row,
                    new_col)

DEPRECATED

This function supported insertion into an earlier version of racked_tube.
Should be dropped.';


--
-- TOC entry 502 (class 1255 OID 16783329)
-- Name: insert_racked_tube(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_racked_tube(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_container_specs_name alias for $1;
    new_item_status alias for $2;
    new_container_barcode alias for $3;
    new_rack_barcode alias for $4;
    new_row alias for $5;
    new_col alias for $6;
begin
    insert
      into container (container_specs_id, item_status)
    values ((select container_specs_id
               from container_specs
              where name = new_container_specs_name),
            new_item_status);
    insert
      into containment (holder_id, held_id, row, col)
    values ((select rack_id
               from rack
              where barcode = new_rack_barcode),
            (select currval('container_container_id_seq')),
            new_row, new_col);
    insert
      into container_barcode (container_id, barcode)
    values ((select currval('container_container_id_seq')),
            new_container_barcode);
    return;
end;
$_$;


ALTER FUNCTION public.insert_racked_tube(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer) OWNER TO postgres;

--
-- TOC entry 4997 (class 0 OID 0)
-- Dependencies: 502
-- Name: FUNCTION insert_racked_tube(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION insert_racked_tube(pg_catalog.name, character varying, character varying, cenix_barcode, integer, integer) IS 'insert_racked_tube(new_container_specs_name,
                    new_item_status,
                    new_container_barcode,
                    new_rack_barcode,
                    new_row,
                    new_col)

Support insertion into view racked_tube.

Do not call directly.  Use an insert statement on racked_tube instead.';


--
-- TOC entry 507 (class 1255 OID 16783330)
-- Name: insert_single_stranded_design_view(integer, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_single_stranded_design_view(integer, integer, integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_molecule_design_id alias for $1;
    new_molecule_type_id alias for $2;
    new_sequence_id alias for $3;
    molecule_design_exists record;
begin
    if new_molecule_design_id is null then
        insert into molecule_design (molecule_type_id)
             values (new_molecule_type_id);
        insert into single_stranded_design (molecule_design_id, sequence_id)
             values ((select currval('molecule_design_molecule_design_id_seq')),
                     new_sequence_id);
    else
        select into molecule_design_exists (exists (select molecule_design_id 
                                 from molecule_design 
                                where molecule_design_id = 
                                          new_molecule_design_id));
        if not molecule_design_exists then
            insert into molecule_design (molecule_design_id, molecule_type_id)
                 values (new_molecule_design_id, new_molecule_type_id);
        end if;
        insert into single_stranded_design (molecule_design_id, sequence_id)
             values (new_molecule_design_id, new_sequence_id);
    end if;
    return;
end;$_$;


ALTER FUNCTION public.insert_single_stranded_design_view(integer, integer, integer) OWNER TO postgres;

--
-- TOC entry 4998 (class 0 OID 0)
-- Dependencies: 507
-- Name: FUNCTION insert_single_stranded_design_view(integer, integer, integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION insert_single_stranded_design_view(integer, integer, integer) IS 'insert_single_stranded_design_view(new_molecule_design_id,
                                    new_molecule_type_id,
                                    new_sequence_id)

DEPRECATED

This function supported insertion into an earlier version of
single_stranded_design_view.  Should be dropped.';


--
-- TOC entry 508 (class 1255 OID 16783331)
-- Name: insert_single_stranded_design_view(integer, character varying, nucleic_acid, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION insert_single_stranded_design_view(integer, character varying, nucleic_acid, character varying) RETURNS void
    LANGUAGE plpgsql
    AS $_$
declare
    new_molecule_design_id alias for $1;
    new_molecule_type alias for $2;
    new_sequence alias for $3;
    new_modification alias for $4;
    molecule_design_exists record;
begin
    if new_molecule_design_id is null then
        insert into molecule_design (molecule_type)
             values (new_molecule_type);
        insert into single_stranded_design (molecule_design_id, sequence,
                                            modification)
             values ((select currval('molecule_design_molecule_design_id_seq')),
                     new_sequence, new_modification);
    else
        select into molecule_design_exists (exists (select molecule_design_id
                                 from molecule_design
                                where molecule_design_id =
                                          new_molecule_design_id));
        if not molecule_design_exists then
            insert into molecule_design (molecule_design_id, molecule_type)
                 values (new_molecule_design_id, new_molecule_type);
        end if;
        insert into single_stranded_design (molecule_design_id, sequence,
                                            modification)
             values (new_molecule_design_id, new_sequence,
                                            new_modification);
    end if;
    return;
end;
$_$;


ALTER FUNCTION public.insert_single_stranded_design_view(integer, character varying, nucleic_acid, character varying) OWNER TO postgres;

--
-- TOC entry 4999 (class 0 OID 0)
-- Dependencies: 508
-- Name: FUNCTION insert_single_stranded_design_view(integer, character varying, nucleic_acid, character varying); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION insert_single_stranded_design_view(integer, character varying, nucleic_acid, character varying) IS 'insert_single_stranded_design_view(molecule_design_id,
                                       varchar,
                                       sequence,
                                       modification)
Insert a tuple into single_stranded_design_view.  Sematics follow Date, 2004';


--
-- TOC entry 509 (class 1255 OID 16783332)
-- Name: minimum(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION minimum(integer, integer) RETURNS integer
    LANGUAGE plpgsql IMMUTABLE
    AS $_$
begin
    if $1 < $2 then
        return $1;
    else
        return $2;
    end if;
end;$_$;


ALTER FUNCTION public.minimum(integer, integer) OWNER TO postgres;

--
-- TOC entry 5000 (class 0 OID 0)
-- Dependencies: 509
-- Name: FUNCTION minimum(integer, integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION minimum(integer, integer) IS 'minimum(a, b)

DEPRECATED

This function has the same purpose as the built-in GREATEST expression, but
is less flexible.  Should be dropped.

Return the greater of a and b.';


--
-- TOC entry 510 (class 1255 OID 16783333)
-- Name: plpgsql_call_handler(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION plpgsql_call_handler() RETURNS language_handler
    LANGUAGE c
    AS '$libdir/plpgsql', 'plpgsql_call_handler';


ALTER FUNCTION public.plpgsql_call_handler() OWNER TO postgres;

--
-- TOC entry 511 (class 1255 OID 16783334)
-- Name: range(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION range(integer, integer) RETURNS SETOF integer
    LANGUAGE plpgsql
    AS $_$
declare
        s alias for $1;
        e alias for $2;
        i integer;
begin
        i := s;

        while i < e
        loop
                return next i;
                i := i + 1;
        end loop;

        return null;
end;
$_$;


ALTER FUNCTION public.range(integer, integer) OWNER TO postgres;

--
-- TOC entry 5001 (class 0 OID 0)
-- Dependencies: 511
-- Name: FUNCTION range(integer, integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION range(integer, integer) IS 'range(start, end) returns setof integer

Return a table containing all integers from greater than or equal to start and
less than end.

E.g.,

unidb=# select * from range(1, 5);
 ?column?
----------
        1
        2
        3
        4
(4 rows)

This function is very useful for discovering which values of a range are
missing when combined with an EXCEPT clause.  The implementation is currently
broken due to a syntax error and must be fixed.';


--
-- TOC entry 512 (class 1255 OID 16783335)
-- Name: refresh_table_molecule_design_gene(); Type: FUNCTION; Schema: public; Owner: cebos
--

CREATE FUNCTION refresh_table_molecule_design_gene() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
delete from molecule_design_gene;
delete from molecule_design_set_gene;
insert into molecule_design_gene select * from molecule_design_gene_view;
insert into molecule_design_set_gene select * from molecule_design_set_gene_view;
return null;
end 
$$;


ALTER FUNCTION public.refresh_table_molecule_design_gene() OWNER TO cebos;

--
-- TOC entry 5002 (class 0 OID 0)
-- Dependencies: 512
-- Name: FUNCTION refresh_table_molecule_design_gene(); Type: COMMENT; Schema: public; Owner: cebos
--

COMMENT ON FUNCTION refresh_table_molecule_design_gene() IS 'A simple function to update the molecule_design_gene materialized view';


--
-- TOC entry 513 (class 1255 OID 16783336)
-- Name: refresh_table_refseq_gene(); Type: FUNCTION; Schema: public; Owner: berger
--

CREATE FUNCTION refresh_table_refseq_gene() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
   delete from refseq_gene;
   insert into refseq_gene
   select distinct g.gene_id, g.accession, g.locus_name, g.species_id
   from gene g
   join release_gene_transcript rgt ON rgt.gene_id = g.gene_id AND rgt.species_id = g.species_id
   join current_db_release cdr ON cdr.db_release_id = rgt.db_release_id
   join db_source ds ON ds.db_source_id = cdr.db_source_id
   where ds.db_name::text = 'RefSeq'::text;
   return null;
end
$$;


ALTER FUNCTION public.refresh_table_refseq_gene() OWNER TO berger;

--
-- TOC entry 514 (class 1255 OID 16783337)
-- Name: set_container_type(); Type: FUNCTION; Schema: public; Owner: gathmann
--

CREATE FUNCTION set_container_type() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    has_bc BOOLEAN;
BEGIN
    IF NEW.container_type = 'CONTAINER' THEN
            SELECT INTO has_bc has_barcode FROM container_specs
                                           WHERE container_specs_id=NEW.container_specs_id;
            IF has_bc
                THEN NEW.container_type = 'TUBE';
                ELSE NEW.container_type = 'WELL';
            END IF;
    END IF;
    RETURN NEW;
END
$$;


ALTER FUNCTION public.set_container_type() OWNER TO gathmann;

--
-- TOC entry 5003 (class 0 OID 0)
-- Dependencies: 514
-- Name: FUNCTION set_container_type(); Type: COMMENT; Schema: public; Owner: gathmann
--

COMMENT ON FUNCTION set_container_type() IS 'Function to set the container type of newly INSERTed containers.';


--
-- TOC entry 515 (class 1255 OID 16783338)
-- Name: set_rack_type(); Type: FUNCTION; Schema: public; Owner: thelma
--

CREATE FUNCTION set_rack_type() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE rack
       SET rack_type=CASE WHEN rack_specs.has_movable_subitems THEN 'TUBERACK' ELSE 'PLATE' END
      FROM rack_specs
     WHERE rack_specs.rack_specs_id=rack.rack_specs_id
       AND rack.rack_type='RACK';
    RETURN NULL;
END
$$;


ALTER FUNCTION public.set_rack_type() OWNER TO thelma;

--
-- TOC entry 5004 (class 0 OID 0)
-- Dependencies: 515
-- Name: FUNCTION set_rack_type(); Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON FUNCTION set_rack_type() IS 'Function to set the rack type of newly INSERTed racks.';


--
-- TOC entry 1668 (class 1255 OID 16783339)
-- Name: array_accum(anyelement); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE array_accum(anyelement) (
    SFUNC = array_append,
    STYPE = anyarray,
    INITCOND = '{}'
);


ALTER AGGREGATE public.array_accum(anyelement) OWNER TO postgres;

--
-- TOC entry 5005 (class 0 OID 0)
-- Dependencies: 1668
-- Name: AGGREGATE array_accum(anyelement); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON AGGREGATE array_accum(anyelement) IS 'Return an array containing the value of each aggregated cell.';


--
-- TOC entry 1669 (class 1255 OID 16783340)
-- Name: concatenate(text); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE concatenate(text) (
    SFUNC = commacat,
    STYPE = text,
    INITCOND = ''
);


ALTER AGGREGATE public.concatenate(text) OWNER TO postgres;

--
-- TOC entry 1670 (class 1255 OID 16783341)
-- Name: first(anyelement); Type: AGGREGATE; Schema: public; Owner: gathmann
--

CREATE AGGREGATE first(anyelement) (
    SFUNC = first_agg,
    STYPE = anyelement
);


ALTER AGGREGATE public.first(anyelement) OWNER TO gathmann;

--
-- TOC entry 1671 (class 1255 OID 16783342)
-- Name: textcat_all(text); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE textcat_all(text) (
    SFUNC = textcat,
    STYPE = text,
    INITCOND = ''
);


ALTER AGGREGATE public.textcat_all(text) OWNER TO postgres;

--
-- TOC entry 169 (class 1259 OID 16783343)
-- Name: _assertion_trigger_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE _assertion_trigger_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public._assertion_trigger_seq OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 170 (class 1259 OID 16783345)
-- Name: _user_messages; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE _user_messages (
    guid character varying NOT NULL,
    text character varying NOT NULL,
    time_stamp timestamp with time zone NOT NULL
);


ALTER TABLE public._user_messages OWNER TO thelma;

--
-- TOC entry 171 (class 1259 OID 16783365)
-- Name: acquisition_task_item; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE acquisition_task_item (
    file_set_id integer NOT NULL,
    task_item_id integer NOT NULL,
    file_storage_site_id integer NOT NULL
);


ALTER TABLE public.acquisition_task_item OWNER TO postgres;

--
-- TOC entry 5008 (class 0 OID 0)
-- Dependencies: 171
-- Name: TABLE acquisition_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE acquisition_task_item IS 'Extra information for completed acquisition task items.';


--
-- TOC entry 5009 (class 0 OID 0)
-- Dependencies: 171
-- Name: COLUMN acquisition_task_item.file_set_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN acquisition_task_item.file_set_id IS 'File set to which all acquired images belong.';


--
-- TOC entry 5010 (class 0 OID 0)
-- Dependencies: 171
-- Name: COLUMN acquisition_task_item.file_storage_site_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN acquisition_task_item.file_storage_site_id IS 'File storage site where images where stored.

This information should probably be derrived from the files instead.';


--
-- TOC entry 172 (class 1259 OID 16783368)
-- Name: annotation_annotation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE annotation_annotation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.annotation_annotation_id_seq OWNER TO postgres;

--
-- TOC entry 173 (class 1259 OID 16783370)
-- Name: annotation; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE annotation (
    annotation_id integer DEFAULT nextval('annotation_annotation_id_seq'::regclass) NOT NULL,
    annotation_type_id integer NOT NULL,
    name text NOT NULL,
    CONSTRAINT annotation_name CHECK ((name <> ''::text))
);


ALTER TABLE public.annotation OWNER TO postgres;

--
-- TOC entry 5013 (class 0 OID 0)
-- Dependencies: 173
-- Name: TABLE annotation; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE annotation IS 'contains annotations for genes';


--
-- TOC entry 5014 (class 0 OID 0)
-- Dependencies: 173
-- Name: COLUMN annotation.annotation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation.annotation_id IS 'Primary key

Internal ID. Not to be made public.';


--
-- TOC entry 5015 (class 0 OID 0)
-- Dependencies: 173
-- Name: COLUMN annotation.annotation_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation.annotation_type_id IS 'ID of annotation_type';


--
-- TOC entry 5016 (class 0 OID 0)
-- Dependencies: 173
-- Name: COLUMN annotation.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation.name IS 'the actual annotation

This could be a name, a description, a reference. Suggest renaming this to
annotation';


--
-- TOC entry 174 (class 1259 OID 16783378)
-- Name: annotation_accession; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE annotation_accession (
    annotation_id integer NOT NULL,
    accession character varying(30) NOT NULL
);


ALTER TABLE public.annotation_accession OWNER TO postgres;

--
-- TOC entry 5018 (class 0 OID 0)
-- Dependencies: 174
-- Name: TABLE annotation_accession; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE annotation_accession IS 'maps an accession number to an annotation';


--
-- TOC entry 5019 (class 0 OID 0)
-- Dependencies: 174
-- Name: COLUMN annotation_accession.annotation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation_accession.annotation_id IS 'ID of annotation';


--
-- TOC entry 5020 (class 0 OID 0)
-- Dependencies: 174
-- Name: COLUMN annotation_accession.accession; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation_accession.accession IS 'accession of annotation

This could be a GO accession, Kegg accession, etc.';


--
-- TOC entry 175 (class 1259 OID 16783381)
-- Name: annotation_relationship; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE annotation_relationship (
    parent_annotation_id integer NOT NULL,
    child_annotation_id integer NOT NULL,
    CONSTRAINT parent_child_different CHECK ((parent_annotation_id <> child_annotation_id))
);


ALTER TABLE public.annotation_relationship OWNER TO postgres;

--
-- TOC entry 5022 (class 0 OID 0)
-- Dependencies: 175
-- Name: TABLE annotation_relationship; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE annotation_relationship IS 'maps parent-child relationships between annotation terms';


--
-- TOC entry 5023 (class 0 OID 0)
-- Dependencies: 175
-- Name: COLUMN annotation_relationship.parent_annotation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation_relationship.parent_annotation_id IS 'ID of annotation of the parent term';


--
-- TOC entry 5024 (class 0 OID 0)
-- Dependencies: 175
-- Name: COLUMN annotation_relationship.child_annotation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation_relationship.child_annotation_id IS 'ID of annotation of the child term';


--
-- TOC entry 176 (class 1259 OID 16783385)
-- Name: annotation_type_annotation_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE annotation_type_annotation_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.annotation_type_annotation_type_id_seq OWNER TO postgres;

--
-- TOC entry 177 (class 1259 OID 16783387)
-- Name: annotation_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE annotation_type (
    annotation_type_id integer DEFAULT nextval('annotation_type_annotation_type_id_seq'::regclass) NOT NULL,
    db_source_id integer NOT NULL,
    type character varying(200) NOT NULL,
    CONSTRAINT annotation_type_type CHECK (((type)::text <> ''::text))
);


ALTER TABLE public.annotation_type OWNER TO postgres;

--
-- TOC entry 5027 (class 0 OID 0)
-- Dependencies: 177
-- Name: TABLE annotation_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE annotation_type IS 'types of annotations and their db source';


--
-- TOC entry 5028 (class 0 OID 0)
-- Dependencies: 177
-- Name: COLUMN annotation_type.annotation_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation_type.annotation_type_id IS 'primary key

Internal ID. Not to be made public';


--
-- TOC entry 5029 (class 0 OID 0)
-- Dependencies: 177
-- Name: COLUMN annotation_type.db_source_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation_type.db_source_id IS 'ID of db_source';


--
-- TOC entry 5030 (class 0 OID 0)
-- Dependencies: 177
-- Name: COLUMN annotation_type.type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN annotation_type.type IS 'type of annotation

Should be made into a domain. Values are
    o Reactome pathway
    o Gene summary
    o GeneRIF
    o KEGG pathway
    o Official Gene Name
    o COG
    o GO Process
    o GO Function
    o GO Component';


--
-- TOC entry 178 (class 1259 OID 16783392)
-- Name: barcode_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE barcode_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.barcode_seq OWNER TO postgres;

--
-- TOC entry 179 (class 1259 OID 16783394)
-- Name: barcoded_location; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE barcoded_location (
    type character varying(12) NOT NULL,
    label character varying(128) NOT NULL,
    barcode cenix_barcode DEFAULT lpad((nextval('barcode_seq'::regclass))::text, 8, '0'::text) NOT NULL,
    barcoded_location_id integer DEFAULT nextval(('barcoded_location_barcoded_location_id_seq'::text)::regclass) NOT NULL,
    name pg_catalog.name NOT NULL,
    device_id integer,
    index integer
);


ALTER TABLE public.barcoded_location OWNER TO postgres;

--
-- TOC entry 5033 (class 0 OID 0)
-- Dependencies: 179
-- Name: TABLE barcoded_location; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE barcoded_location IS 'A place where racks can be kept

The name is silly.  We may require all locations in the system to have a
barcode, but that is no justification for the awkward name.  Consider renaming
to location.

There are a number of candidate columns to replace the current primary key,
barcoded_location_id.  See the column comments.';


--
-- TOC entry 5034 (class 0 OID 0)
-- Dependencies: 179
-- Name: COLUMN barcoded_location.type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN barcoded_location.type IS 'Type of location

This is just a name with no associated information.  Consider making this
column a foreign key to a new location_type table which can hold information
such as a description, capacity, etc.';


--
-- TOC entry 5035 (class 0 OID 0)
-- Dependencies: 179
-- Name: COLUMN barcoded_location.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN barcoded_location.label IS 'User-assigned name for the location, intended for display

Must be unique for a given device ID.';


--
-- TOC entry 5036 (class 0 OID 0)
-- Dependencies: 179
-- Name: COLUMN barcoded_location.barcode; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN barcoded_location.barcode IS 'Barcode attached to the location

Candidate primary key.';


--
-- TOC entry 5037 (class 0 OID 0)
-- Dependencies: 179
-- Name: COLUMN barcoded_location.barcoded_location_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN barcoded_location.barcoded_location_id IS 'Surrogate primary key of the location

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
one of the other candidates as the primary key.  My inclination is to use
barcode.';


--
-- TOC entry 5038 (class 0 OID 0)
-- Dependencies: 179
-- Name: COLUMN barcoded_location.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN barcoded_location.name IS 'User-assigned name for the location, intended for programatic purposes

Candidate primary key.

Programs should not rely on specific database contents and thus this column
has little value.  Probably should be dropped.';


--
-- TOC entry 5039 (class 0 OID 0)
-- Dependencies: 179
-- Name: COLUMN barcoded_location.device_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN barcoded_location.device_id IS 'Device in or on which location exists (optional)

This column allows NULLs.  You could consider moving this column and index into
a new device_location table.  However, in the current database every location
could be associated with a device, so it might be better to fix the data and
add a NOT NULL constraint.';


--
-- TOC entry 5040 (class 0 OID 0)
-- Dependencies: 179
-- Name: COLUMN barcoded_location.index; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN barcoded_location.index IS 'Index of the position in the device in or on which location exists (optional)

This column allows NULLs.  You could consider moving this column and device_id
into a new device_location table.  However, in the current database every
location could be associated with a device, so it might be better to fix the
data and add a NOT NULL constraint.';


--
-- TOC entry 180 (class 1259 OID 16783402)
-- Name: barcoded_location_barcoded_location_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE barcoded_location_barcoded_location_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.barcoded_location_barcoded_location_id_seq OWNER TO postgres;

--
-- TOC entry 181 (class 1259 OID 16783404)
-- Name: carrier_content_type_carrier_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE carrier_content_type_carrier_content_type_id_seq
    START WITH 17
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.carrier_content_type_carrier_content_type_id_seq OWNER TO postgres;

--
-- TOC entry 182 (class 1259 OID 16783406)
-- Name: carrier_origin_type_carrier_origin_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE carrier_origin_type_carrier_origin_type_id_seq
    START WITH 10
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.carrier_origin_type_carrier_origin_type_id_seq OWNER TO postgres;

--
-- TOC entry 183 (class 1259 OID 16783408)
-- Name: carrier_set_carrier_set_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE carrier_set_carrier_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.carrier_set_carrier_set_id_seq OWNER TO postgres;

--
-- TOC entry 184 (class 1259 OID 16783410)
-- Name: carrier_set_type_carrier_set_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE carrier_set_type_carrier_set_type_id_seq
    START WITH 6
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.carrier_set_type_carrier_set_type_id_seq OWNER TO postgres;

--
-- TOC entry 185 (class 1259 OID 16783412)
-- Name: cell_line; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE cell_line (
    cell_line_id integer NOT NULL,
    species_id integer NOT NULL,
    identifier character varying(64) NOT NULL
);


ALTER TABLE public.cell_line OWNER TO postgres;

--
-- TOC entry 5047 (class 0 OID 0)
-- Dependencies: 185
-- Name: TABLE cell_line; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE cell_line IS 'Cell line

We don''t store much information about cell lines now, but there have been some
vague requests for more.';


--
-- TOC entry 5048 (class 0 OID 0)
-- Dependencies: 185
-- Name: COLUMN cell_line.cell_line_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN cell_line.cell_line_id IS 'Surrogate primary key of the cell line

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
identifier as the primary key in its place.';


--
-- TOC entry 5049 (class 0 OID 0)
-- Dependencies: 185
-- Name: COLUMN cell_line.species_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN cell_line.species_id IS 'ID of originating species';


--
-- TOC entry 5050 (class 0 OID 0)
-- Dependencies: 185
-- Name: COLUMN cell_line.identifier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN cell_line.identifier IS 'Cell line name

Consider renaming to cell_line_name.

Consider making this column the primary key in place of cell_line_id.';


--
-- TOC entry 186 (class 1259 OID 16783415)
-- Name: cell_line_cell_line_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE cell_line_cell_line_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.cell_line_cell_line_id_seq OWNER TO postgres;

--
-- TOC entry 5052 (class 0 OID 0)
-- Dependencies: 186
-- Name: cell_line_cell_line_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE cell_line_cell_line_id_seq OWNED BY cell_line.cell_line_id;


--
-- TOC entry 187 (class 1259 OID 16783417)
-- Name: chemical_structure; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE chemical_structure (
    chemical_structure_id integer NOT NULL,
    structure_type character varying NOT NULL,
    representation character varying NOT NULL
);


ALTER TABLE public.chemical_structure OWNER TO gathmann;

--
-- TOC entry 5054 (class 0 OID 0)
-- Dependencies: 187
-- Name: TABLE chemical_structure; Type: COMMENT; Schema: public; Owner: gathmann
--

COMMENT ON TABLE chemical_structure IS 'Chemical structures associated with molecule designs. We currently distinguish two structure types: COMPOUND and NUCLEIC_ACID.';


--
-- TOC entry 188 (class 1259 OID 16783423)
-- Name: chemical_structure_chemical_structure_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE chemical_structure_chemical_structure_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chemical_structure_chemical_structure_id_seq OWNER TO gathmann;

--
-- TOC entry 5056 (class 0 OID 0)
-- Dependencies: 188
-- Name: chemical_structure_chemical_structure_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE chemical_structure_chemical_structure_id_seq OWNED BY chemical_structure.chemical_structure_id;


--
-- TOC entry 189 (class 1259 OID 16783425)
-- Name: chromosome; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE chromosome (
    chromosome_id integer NOT NULL,
    species_id integer NOT NULL,
    name character varying(25) NOT NULL,
    sequence text
);


ALTER TABLE public.chromosome OWNER TO postgres;

--
-- TOC entry 5057 (class 0 OID 0)
-- Dependencies: 189
-- Name: TABLE chromosome; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE chromosome IS 'A chromosome

Stores complete sequence for some of the chromosomes (from fly).';


--
-- TOC entry 5058 (class 0 OID 0)
-- Dependencies: 189
-- Name: COLUMN chromosome.sequence; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN chromosome.sequence IS 'Complete sequence for chromosome.

Allows NULLs, consider changing this.';


--
-- TOC entry 190 (class 1259 OID 16783431)
-- Name: chromosome_chromosome_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE chromosome_chromosome_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chromosome_chromosome_id_seq OWNER TO postgres;

--
-- TOC entry 5060 (class 0 OID 0)
-- Dependencies: 190
-- Name: chromosome_chromosome_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE chromosome_chromosome_id_seq OWNED BY chromosome.chromosome_id;


--
-- TOC entry 191 (class 1259 OID 16783433)
-- Name: chromosome_gene_feature; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE chromosome_gene_feature (
    gene_id integer NOT NULL,
    sequence_feature_id integer NOT NULL,
    chromosome_id integer NOT NULL
);


ALTER TABLE public.chromosome_gene_feature OWNER TO postgres;

--
-- TOC entry 192 (class 1259 OID 16783436)
-- Name: chromosome_transcript_feature; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE chromosome_transcript_feature (
    transcript_id integer NOT NULL,
    sequence_feature_id integer NOT NULL,
    chromosome_id integer NOT NULL
);


ALTER TABLE public.chromosome_transcript_feature OWNER TO postgres;

--
-- TOC entry 5063 (class 0 OID 0)
-- Dependencies: 192
-- Name: TABLE chromosome_transcript_feature; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE chromosome_transcript_feature IS 'Sequence coordinates of transcript on chromosome

Coordinates can be retrieved via sequence_feature_id';


--
-- TOC entry 480 (class 1259 OID 16859042)
-- Name: compound; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE compound (
    molecule_design_id integer NOT NULL,
    smiles character varying NOT NULL
);


ALTER TABLE public.compound OWNER TO thelma;

--
-- TOC entry 193 (class 1259 OID 16783439)
-- Name: container; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE container (
    container_id integer NOT NULL,
    container_specs_id integer NOT NULL,
    item_status character varying(9) NOT NULL,
    container_type character varying(9) DEFAULT 'CONTAINER'::character varying NOT NULL
);


ALTER TABLE public.container OWNER TO postgres;

--
-- TOC entry 5065 (class 0 OID 0)
-- Dependencies: 193
-- Name: TABLE container; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE container IS 'A container, capable of holding a sample';


--
-- TOC entry 5066 (class 0 OID 0)
-- Dependencies: 193
-- Name: COLUMN container.container_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container.container_id IS 'Surrogate primary key of the container

Internal ID.  Do not publish.';


--
-- TOC entry 5067 (class 0 OID 0)
-- Dependencies: 193
-- Name: COLUMN container.container_specs_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container.container_specs_id IS 'ID of container type';


--
-- TOC entry 5068 (class 0 OID 0)
-- Dependencies: 193
-- Name: COLUMN container.item_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container.item_status IS 'Status of container';


--
-- TOC entry 5069 (class 0 OID 0)
-- Dependencies: 193
-- Name: COLUMN container.container_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container.container_type IS 'The rack type allows the ORM to support joined inheritance for
racks.';


--
-- TOC entry 194 (class 1259 OID 16783443)
-- Name: container_barcode; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE container_barcode (
    container_id integer NOT NULL,
    barcode character varying NOT NULL,
    CONSTRAINT container_barcode_barcode CHECK (((barcode)::text <> ''::text))
);


ALTER TABLE public.container_barcode OWNER TO postgres;

--
-- TOC entry 5071 (class 0 OID 0)
-- Dependencies: 194
-- Name: TABLE container_barcode; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE container_barcode IS 'A barcode on a container

This is a separate table from container because many containers do not have
barcodes attached to them.  For example, the wells of a fixed-well microtiter
plate are not usually barcoded.';


--
-- TOC entry 195 (class 1259 OID 16783450)
-- Name: container_container_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE container_container_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.container_container_id_seq OWNER TO postgres;

--
-- TOC entry 5073 (class 0 OID 0)
-- Dependencies: 195
-- Name: container_container_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE container_container_id_seq OWNED BY container.container_id;


--
-- TOC entry 196 (class 1259 OID 16783452)
-- Name: containment; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE containment (
    holder_id integer NOT NULL,
    held_id integer NOT NULL,
    col integer NOT NULL,
    "row" integer NOT NULL,
    CONSTRAINT containment_col_non_negative CHECK ((col >= 0)),
    CONSTRAINT containment_numeric_row CHECK (("row" >= 0))
);


ALTER TABLE public.containment OWNER TO postgres;

--
-- TOC entry 5075 (class 0 OID 0)
-- Dependencies: 196
-- Name: TABLE containment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE containment IS 'Association of a container with its holding rack';


--
-- TOC entry 5076 (class 0 OID 0)
-- Dependencies: 196
-- Name: COLUMN containment.holder_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN containment.holder_id IS 'ID of holding rack

The name of this column comes from earlier ambitions for a generic inventory
management scheme, where holders and held items could be nested arbitrarily.
This has yet to happen and in the current context the name holder_id is
confusing.  Consider renaming to rack_id';


--
-- TOC entry 5077 (class 0 OID 0)
-- Dependencies: 196
-- Name: COLUMN containment.held_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN containment.held_id IS 'ID of held container

The name of this column comes from earlier ambitions for a generic inventory
management scheme, where holders and held items could be nested arbitrarily.
This has yet to happen and in the current context the name held_id is
confusing.  Consider renaming to container_id';


--
-- TOC entry 5078 (class 0 OID 0)
-- Dependencies: 196
-- Name: COLUMN containment.col; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN containment.col IS 'Zero-based column index starting from the left of the rack';


--
-- TOC entry 5079 (class 0 OID 0)
-- Dependencies: 196
-- Name: COLUMN containment."row"; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN containment."row" IS 'Zero-based row index starting from the top of the rack';


--
-- TOC entry 197 (class 1259 OID 16783457)
-- Name: rack; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack (
    barcode cenix_barcode DEFAULT lpad((nextval('barcode_seq'::regclass))::text, 8, '0'::text) NOT NULL,
    creation_date timestamp without time zone DEFAULT now() NOT NULL,
    rack_specs_id integer NOT NULL,
    label character varying(20) DEFAULT ''::character varying NOT NULL,
    rack_id integer DEFAULT nextval(('rack_rack_id_seq'::text)::regclass) NOT NULL,
    comment character varying DEFAULT ''::character varying NOT NULL,
    item_status character varying(9) NOT NULL,
    rack_type character varying(9) DEFAULT 'RACK'::character varying NOT NULL
);


ALTER TABLE public.rack OWNER TO postgres;

--
-- TOC entry 5081 (class 0 OID 0)
-- Dependencies: 197
-- Name: TABLE rack; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack IS 'A tube rack or microtiter plate';


--
-- TOC entry 5082 (class 0 OID 0)
-- Dependencies: 197
-- Name: COLUMN rack.barcode; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack.barcode IS 'Barcode of the rack.

Consider changing the type of this field to char(8) and requiring all
characters to be digits.';


--
-- TOC entry 5083 (class 0 OID 0)
-- Dependencies: 197
-- Name: COLUMN rack.creation_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack.creation_date IS 'Date the rack record was inserted, defaults to now().';


--
-- TOC entry 5084 (class 0 OID 0)
-- Dependencies: 197
-- Name: COLUMN rack.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack.label IS 'Short menemonic label.  Need not be unique.';


--
-- TOC entry 5085 (class 0 OID 0)
-- Dependencies: 197
-- Name: COLUMN rack.rack_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack.rack_id IS 'Surrogate primary key of the rack

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
barcode as the primary key in its place.';


--
-- TOC entry 5086 (class 0 OID 0)
-- Dependencies: 197
-- Name: COLUMN rack.comment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack.comment IS 'Space for comments.';


--
-- TOC entry 5087 (class 0 OID 0)
-- Dependencies: 197
-- Name: COLUMN rack.item_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack.item_status IS 'Status of rack';


--
-- TOC entry 198 (class 1259 OID 16783469)
-- Name: rack_specs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_specs (
    name character varying(32) NOT NULL,
    number_rows smallint NOT NULL,
    number_columns smallint NOT NULL,
    label character varying(128) NOT NULL,
    has_movable_subitems boolean NOT NULL,
    manufacturer_id integer,
    rack_specs_id integer DEFAULT nextval(('rack_specs_rack_specs_id_seq'::text)::regclass) NOT NULL,
    rack_shape_name character varying NOT NULL,
    CONSTRAINT nonempty_label CHECK (((label)::text <> ''::text)),
    CONSTRAINT nonempty_name CHECK (((name)::text <> ''::text)),
    CONSTRAINT number_columns CHECK ((number_columns > 0)),
    CONSTRAINT number_rows CHECK ((number_rows > 0))
);


ALTER TABLE public.rack_specs OWNER TO postgres;

--
-- TOC entry 5089 (class 0 OID 0)
-- Dependencies: 198
-- Name: TABLE rack_specs; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_specs IS 'A type of rack';


--
-- TOC entry 5090 (class 0 OID 0)
-- Dependencies: 198
-- Name: COLUMN rack_specs.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_specs.name IS 'User-assigned name for the rack type, intended for programatic purposes

Programs should not rely on specific database contents and thus this column
has little value.  Probably should be dropped.';


--
-- TOC entry 5091 (class 0 OID 0)
-- Dependencies: 198
-- Name: COLUMN rack_specs.number_rows; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_specs.number_rows IS 'Number of rows in racks of this type (Consider deleting the column when CeLMA domain/marshals become redundant)';


--
-- TOC entry 5092 (class 0 OID 0)
-- Dependencies: 198
-- Name: COLUMN rack_specs.number_columns; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_specs.number_columns IS 'Number of columns in raks of this type (Consider deleting the column when CeLMA domain/marshals become redundant)';


--
-- TOC entry 5093 (class 0 OID 0)
-- Dependencies: 198
-- Name: COLUMN rack_specs.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_specs.label IS 'User-assigned name for the rack type, intended for display';


--
-- TOC entry 5094 (class 0 OID 0)
-- Dependencies: 198
-- Name: COLUMN rack_specs.has_movable_subitems; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_specs.has_movable_subitems IS 'If TRUE, containers can be physically added to and removed from this rack.
If FALSE, containers are physically fixed to the rack.';


--
-- TOC entry 5095 (class 0 OID 0)
-- Dependencies: 198
-- Name: COLUMN rack_specs.manufacturer_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_specs.manufacturer_id IS 'Organization ID of manufacturer of this type of rack (optional)

Long ago, someone decided to create placeholder rack specs with labels like
''std. 96'' and ''std. 384''.  Since these specs were used as placeholders
for many actual rack types, no manufacturer could be associated with them.
Thus this column allows NULLs.  We now have a large number of racks associated
with these placeholder types.  It is probably impossible to determine the
actual rack type for each and every rack which is associated with one of these
placeholders.  Thus, we are probably stuck allowing NULLs in this column
forevermore.';


--
-- TOC entry 5096 (class 0 OID 0)
-- Dependencies: 198
-- Name: COLUMN rack_specs.rack_specs_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_specs.rack_specs_id IS 'Surrogate primary key of the rack type

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.

Consider adding a description column to parallel container_specs.';


--
-- TOC entry 199 (class 1259 OID 16783480)
-- Name: container_info; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW container_info AS
    SELECT DISTINCT r.rack_id, c.container_id, cb.barcode, c.item_status, c.container_specs_id, w."row", w.col, rs.number_rows, rs.number_columns FROM rack_specs rs, rack r, containment w, (container c LEFT JOIN container_barcode cb ON ((c.container_id = cb.container_id))) WHERE (((r.rack_specs_id = rs.rack_specs_id) AND (r.rack_id = w.holder_id)) AND (w.held_id = c.container_id)) ORDER BY r.rack_id, c.container_id, cb.barcode, c.item_status, c.container_specs_id, w."row", w.col, rs.number_rows, rs.number_columns;


ALTER TABLE public.container_info OWNER TO postgres;

--
-- TOC entry 5098 (class 0 OID 0)
-- Dependencies: 199
-- Name: VIEW container_info; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW container_info IS 'Summary of racked containers.';


--
-- TOC entry 200 (class 1259 OID 16783485)
-- Name: container_specs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE container_specs (
    container_specs_id integer NOT NULL,
    manufacturer_id integer,
    name pg_catalog.name NOT NULL,
    label character varying NOT NULL,
    description character varying DEFAULT ''::character varying NOT NULL,
    max_volume double precision NOT NULL,
    dead_volume double precision NOT NULL,
    has_barcode boolean DEFAULT false NOT NULL,
    CONSTRAINT container_specs_dead_volume CHECK ((dead_volume >= (0.0)::double precision)),
    CONSTRAINT container_specs_max_volume CHECK ((max_volume >= (0.0)::double precision))
);


ALTER TABLE public.container_specs OWNER TO postgres;

--
-- TOC entry 5100 (class 0 OID 0)
-- Dependencies: 200
-- Name: TABLE container_specs; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE container_specs IS 'A type of container';


--
-- TOC entry 5101 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.container_specs_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.container_specs_id IS 'Surrogate primary key of the cell line

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.';


--
-- TOC entry 5102 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.manufacturer_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.manufacturer_id IS 'Organization ID of manufacturer of this type of container (optional)

Long ago, someone decided to create placeholder container specs with labels
like ''std. 96 well'' and ''std. 384 well''.  Since these specs were used as
placeholders for many actual container types, no manufacturer could be
associated with them.  Thus this column allows NULLs.  We now have a large
number of containers associated with these placeholder types.  It is probably
impossible to determine the actual container type for each and every
container which is associated with one of these placeholders.  Thus, we are
probably stuck allowing NULLs in this column forevermore.';


--
-- TOC entry 5103 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.name IS 'User-assigned name for the container type, intended for programatic purposes

Programs should not rely on specific database contents and thus this column
has little value.  Probably should be dropped.';


--
-- TOC entry 5104 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.label IS 'User-assigned name for the container type, intended for display';


--
-- TOC entry 5105 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.description IS 'Space for comments';


--
-- TOC entry 5106 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.max_volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.max_volume IS 'Container capacity, in liters

The maximum volume Cenix has decided to use in this type of container, which is
usually less than the capacity specified by the manufacturer.';


--
-- TOC entry 5107 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.dead_volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.dead_volume IS 'Container dead volume, in liters

The amount of liquid which is left over in the container after all the maximum
achievable amount is pipetted out.

The actual dead volume depends not only on the type of container, but also on
the pipette or robot used, liquid viscosity, etc.  Thus, this column is probably
useless and should be droped.';


--
-- TOC entry 5108 (class 0 OID 0)
-- Dependencies: 200
-- Name: COLUMN container_specs.has_barcode; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN container_specs.has_barcode IS 'If TRUE, containers of this type have a barcode attached to them.';


--
-- TOC entry 201 (class 1259 OID 16783495)
-- Name: container_specs_container_specs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE container_specs_container_specs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.container_specs_container_specs_id_seq OWNER TO postgres;

--
-- TOC entry 5110 (class 0 OID 0)
-- Dependencies: 201
-- Name: container_specs_container_specs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE container_specs_container_specs_id_seq OWNED BY container_specs.container_specs_id;


--
-- TOC entry 202 (class 1259 OID 16783497)
-- Name: current_db_release; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE current_db_release (
    db_release_id integer NOT NULL,
    db_source_id integer NOT NULL
);


ALTER TABLE public.current_db_release OWNER TO postgres;

--
-- TOC entry 203 (class 1259 OID 16783500)
-- Name: db_release; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE db_release (
    db_release_id integer NOT NULL,
    version character varying(20) NOT NULL,
    db_source_id integer NOT NULL,
    release_date timestamp without time zone NOT NULL,
    download_source character varying(256) NOT NULL
);


ALTER TABLE public.db_release OWNER TO postgres;

--
-- TOC entry 5113 (class 0 OID 0)
-- Dependencies: 203
-- Name: TABLE db_release; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE db_release IS 'Versioned release of data downloaded from an annotation DB (e.g. RefSeq)';


--
-- TOC entry 5114 (class 0 OID 0)
-- Dependencies: 203
-- Name: COLUMN db_release.version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_release.version IS 'Version of DB release

Uses convention (if it exists) of the annotation DB (e.g. 1 for RefSeq
  release 1).

If annotation DB does not issue discrete, named release (e.g. NCBI Gene),
  then the version will be based on the download date.

Note that this is a char data type so if sorting, need to cast the
  data type to appropriate type.';


--
-- TOC entry 5115 (class 0 OID 0)
-- Dependencies: 203
-- Name: COLUMN db_release.db_source_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_release.db_source_id IS 'Refers to annotation DB';


--
-- TOC entry 204 (class 1259 OID 16783503)
-- Name: db_source; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE db_source (
    db_source_id integer NOT NULL,
    db_name character varying(20) NOT NULL,
    curating_organization character varying(25) NOT NULL
);


ALTER TABLE public.db_source OWNER TO postgres;

--
-- TOC entry 5117 (class 0 OID 0)
-- Dependencies: 204
-- Name: TABLE db_source; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE db_source IS 'Source of annotated data (e.g. RefSeq)';


--
-- TOC entry 5118 (class 0 OID 0)
-- Dependencies: 204
-- Name: COLUMN db_source.db_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_source.db_name IS 'Name of the annotation DB (e.g. RefSeq)';


--
-- TOC entry 5119 (class 0 OID 0)
-- Dependencies: 204
-- Name: COLUMN db_source.curating_organization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_source.curating_organization IS 'Organization which hosts or funds the DB (e.g. NCBI)';


--
-- TOC entry 205 (class 1259 OID 16783506)
-- Name: current_db_release_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW current_db_release_view AS
    SELECT ds.db_name, ds.curating_organization, dr.version, dr.release_date FROM db_source ds, db_release dr, current_db_release cdr WHERE ((ds.db_source_id = dr.db_source_id) AND (cdr.db_release_id = dr.db_release_id));


ALTER TABLE public.current_db_release_view OWNER TO postgres;

--
-- TOC entry 5121 (class 0 OID 0)
-- Dependencies: 205
-- Name: VIEW current_db_release_view; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW current_db_release_view IS 'Release info for the version of the annotation DB (e.g. RefSeq) that is current.';


--
-- TOC entry 206 (class 1259 OID 16783510)
-- Name: db_group; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE db_group (
    db_group_id integer NOT NULL,
    login character varying(13) NOT NULL,
    password character varying(13) NOT NULL
);


ALTER TABLE public.db_group OWNER TO postgres;

--
-- TOC entry 5123 (class 0 OID 0)
-- Dependencies: 206
-- Name: TABLE db_group; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE db_group IS 'A group of application users.

Users inherit their access permissions from the groups to which they belong.
However, the information about which group has which permissions is stored
external to the database.

It is a maintenance headache to keep the application groups up to
date separately from the LDAP group information.  Consider using LDAP for
application groups.';


--
-- TOC entry 5124 (class 0 OID 0)
-- Dependencies: 206
-- Name: COLUMN db_group.db_group_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_group.db_group_id IS 'Surrogate primary key of the group

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
login as the primary key in its place.';


--
-- TOC entry 5125 (class 0 OID 0)
-- Dependencies: 206
-- Name: COLUMN db_group.login; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_group.login IS 'Group name

The column name is misleading, since it is not possible to log in to a group.
Consider renaming to db_group_name.

Consider using this column instead of db_user_id as the primary key.';


--
-- TOC entry 5126 (class 0 OID 0)
-- Dependencies: 206
-- Name: COLUMN db_group.password; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_group.password IS 'Crypt-encrypted group password

Historically, it was possible to override any user belonging to a certain group
by using the group password in CeLMA.  This was a bad idea, and is no longer
supported by the application.  The column can not easily be removed because
of intricate legacy code on CeLMA which relies on this columns existance,
although nothing is actually done with its contents.

Drop at the first opportunity.';


--
-- TOC entry 207 (class 1259 OID 16783513)
-- Name: db_group_db_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE db_group_db_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.db_group_db_group_id_seq OWNER TO postgres;

--
-- TOC entry 5128 (class 0 OID 0)
-- Dependencies: 207
-- Name: db_group_db_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE db_group_db_group_id_seq OWNED BY db_group.db_group_id;


--
-- TOC entry 208 (class 1259 OID 16783515)
-- Name: db_group_users; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE db_group_users (
    db_group_id integer NOT NULL,
    db_user_id integer NOT NULL
);


ALTER TABLE public.db_group_users OWNER TO postgres;

--
-- TOC entry 5130 (class 0 OID 0)
-- Dependencies: 208
-- Name: TABLE db_group_users; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE db_group_users IS 'Many-to-many relationship of users and groups

It is a maintenance headache to keep the application group membership up to
date separately from the LDAP information.  Consider using LDAP for application
group membership.

The name of this table is inconsistent with our current naming conventions.
Consider renaming to db_group_db_user or, perhaps better, group_membership';


--
-- TOC entry 209 (class 1259 OID 16783518)
-- Name: db_release_db_release_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE db_release_db_release_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.db_release_db_release_id_seq OWNER TO postgres;

--
-- TOC entry 5132 (class 0 OID 0)
-- Dependencies: 209
-- Name: db_release_db_release_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE db_release_db_release_id_seq OWNED BY db_release.db_release_id;


--
-- TOC entry 210 (class 1259 OID 16783520)
-- Name: db_source_db_source_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE db_source_db_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.db_source_db_source_id_seq OWNER TO postgres;

--
-- TOC entry 5134 (class 0 OID 0)
-- Dependencies: 210
-- Name: db_source_db_source_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE db_source_db_source_id_seq OWNED BY db_source.db_source_id;


--
-- TOC entry 211 (class 1259 OID 16783522)
-- Name: db_user; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE db_user (
    db_user_id integer NOT NULL,
    username character varying(30) NOT NULL,
    login character varying(13) NOT NULL,
    email_addr character varying(128) NOT NULL,
    password character varying(34) NOT NULL,
    directory_user_id character varying NOT NULL
);


ALTER TABLE public.db_user OWNER TO postgres;

--
-- TOC entry 5136 (class 0 OID 0)
-- Dependencies: 211
-- Name: TABLE db_user; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE db_user IS 'A user of Cenix DB-based applications, such as CeLMA

A user belongs to zero or more groups and inherits their permissions from the
groups to which they belong.  See db_group_users.

Users must remain in this table even after they depart from the company, because
there may be references from to users from jobs they have scheduled, etc.  A
consequence is that departed users could potentially log in to Cenix
applications.  An active flag could be added to avoid this.

It is a maintenance headache to keep the application users up to
date separately from the LDAP user information.  Furthermore, users must
remember two sets of login names and passwords.  Consider using LDAP for
application users.';


--
-- TOC entry 5137 (class 0 OID 0)
-- Dependencies: 211
-- Name: COLUMN db_user.db_user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_user.db_user_id IS 'Surrogate primary key of the user

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
login as the primary key in its place.';


--
-- TOC entry 5138 (class 0 OID 0)
-- Dependencies: 211
-- Name: COLUMN db_user.username; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_user.username IS 'Full name of the user

Misleadingly named.  Consider renaming to db_user_full_name.

Consider adding a unique constraint on this column.';


--
-- TOC entry 5139 (class 0 OID 0)
-- Dependencies: 211
-- Name: COLUMN db_user.login; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_user.login IS 'Login name of the user

Consider using this column instead of db_user_id as the primary key.

Consider adding a check constraint to this column to prohibit illegal
characters.

Consider renaming to db_user_login.';


--
-- TOC entry 5140 (class 0 OID 0)
-- Dependencies: 211
-- Name: COLUMN db_user.email_addr; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_user.email_addr IS 'E-mail address of the user

Consider adding a unique constraint on this column.

Consider adding a check constraint to this column to prohibit illegal
characters and possible to enforce letters.  Do not go so far as to try to
validate e-mail addresses, however.  Validating e-mail addresses as a
practically insoluable problem.';


--
-- TOC entry 5141 (class 0 OID 0)
-- Dependencies: 211
-- Name: COLUMN db_user.password; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN db_user.password IS 'MD5-encrypted password of the user';


--
-- TOC entry 212 (class 1259 OID 16783528)
-- Name: db_user_db_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE db_user_db_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.db_user_db_user_id_seq OWNER TO postgres;

--
-- TOC entry 5143 (class 0 OID 0)
-- Dependencies: 212
-- Name: db_user_db_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE db_user_db_user_id_seq OWNED BY db_user.db_user_id;


--
-- TOC entry 213 (class 1259 OID 16783530)
-- Name: db_version; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW db_version AS
    SELECT 19.1 AS version;


ALTER TABLE public.db_version OWNER TO postgres;

--
-- TOC entry 5145 (class 0 OID 0)
-- Dependencies: 213
-- Name: VIEW db_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW db_version IS 'Version of the DB schema

This is updated as the last step in each migration script.  The single column,
version, should be of type NUMERIC(8,4) with the form <major>.<minor>.  As long
as CREATE OR REPLACE view is used to update db_version, this comment will be
preserved.

We can assert that the DB schema is at a particular version with a line like

    select assert(''(select version from db_version) = 206.0001'');

We can update the DB version with a line like

    create or replace view db_version as select 206.0002 as version;';


--
-- TOC entry 214 (class 1259 OID 16783534)
-- Name: device; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE device (
    device_id integer NOT NULL,
    device_type_id integer NOT NULL,
    label character varying(32) NOT NULL,
    model character varying(64) NOT NULL,
    name pg_catalog.name NOT NULL,
    manufacturer_id integer NOT NULL
);


ALTER TABLE public.device OWNER TO postgres;

--
-- TOC entry 5147 (class 0 OID 0)
-- Dependencies: 214
-- Name: TABLE device; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE device IS 'An external device

Devices are used for two purposes:
 * as a means for grouping related barcoded_locations (e.g. freezers)
 * for defining supported operations of machines (e.g pipetting robots)';


--
-- TOC entry 5148 (class 0 OID 0)
-- Dependencies: 214
-- Name: COLUMN device.device_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device.device_id IS 'Surrogate primary key of the device

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.';


--
-- TOC entry 5149 (class 0 OID 0)
-- Dependencies: 214
-- Name: COLUMN device.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device.label IS 'User-assigned name for the device, intended for display

Consider adding a unique constraint on this column';


--
-- TOC entry 5150 (class 0 OID 0)
-- Dependencies: 214
-- Name: COLUMN device.model; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device.model IS 'Model name for the device

This is currently not a foreign key.  Consider creating a new device_model
table so that information common to all instances of a given device model
need only be stored once';


--
-- TOC entry 5151 (class 0 OID 0)
-- Dependencies: 214
-- Name: COLUMN device.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device.name IS 'User-assigned name for the device, intended for programatic purposes

Programs should not rely on specific database contents and thus this column
has little value.  Probably should be dropped.';


--
-- TOC entry 5152 (class 0 OID 0)
-- Dependencies: 214
-- Name: COLUMN device.manufacturer_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device.manufacturer_id IS 'Organization ID of manufacturer of this device';


--
-- TOC entry 215 (class 1259 OID 16783537)
-- Name: device_device_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE device_device_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.device_device_id_seq OWNER TO postgres;

--
-- TOC entry 5154 (class 0 OID 0)
-- Dependencies: 215
-- Name: device_device_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE device_device_id_seq OWNED BY device.device_id;


--
-- TOC entry 216 (class 1259 OID 16783539)
-- Name: device_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE device_type (
    device_type_id integer NOT NULL,
    name pg_catalog.name NOT NULL,
    label character varying NOT NULL
);


ALTER TABLE public.device_type OWNER TO postgres;

--
-- TOC entry 5156 (class 0 OID 0)
-- Dependencies: 216
-- Name: TABLE device_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE device_type IS 'A general class of device

Examples of device types could be pipetting robots, freezers and barcode
printers.

If programs need to rely on the presence of particular device types in the
database, this table should be replaced by a domain.';


--
-- TOC entry 5157 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN device_type.device_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device_type.device_type_id IS 'Surrogate primary key of the device type

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.

Consider adding a description or comment column.';


--
-- TOC entry 5158 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN device_type.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device_type.name IS 'User-assigned name for the device type, intended for programatic purposes

If programs need to rely on the presence of particular device types, the
entire table should be replaced by a domain.  Otherwise, this column
has little value and should probably be dropped.';


--
-- TOC entry 5159 (class 0 OID 0)
-- Dependencies: 216
-- Name: COLUMN device_type.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN device_type.label IS 'User-assigned name for the device type, intended for display';


--
-- TOC entry 217 (class 1259 OID 16783545)
-- Name: device_type_device_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE device_type_device_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.device_type_device_type_id_seq OWNER TO postgres;

--
-- TOC entry 5161 (class 0 OID 0)
-- Dependencies: 217
-- Name: device_type_device_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE device_type_device_type_id_seq OWNED BY device_type.device_type_id;


--
-- TOC entry 218 (class 1259 OID 16783547)
-- Name: dilution_job_step; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE dilution_job_step (
    job_step_id integer NOT NULL,
    diluent_volume double precision NOT NULL,
    CONSTRAINT diluent_volume CHECK ((diluent_volume > (0.0)::double precision))
);


ALTER TABLE public.dilution_job_step OWNER TO postgres;

--
-- TOC entry 5163 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE dilution_job_step; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE dilution_job_step IS 'Extra information required for processing dilution job steps

The type of diluent is not currently specified.  We may want to track it.';


--
-- TOC entry 5164 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN dilution_job_step.diluent_volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN dilution_job_step.diluent_volume IS 'Volume of diluent to add to each sample, in liters.';


--
-- TOC entry 219 (class 1259 OID 16783551)
-- Name: double_stranded_intended_target; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE double_stranded_intended_target (
    molecule_design_id integer NOT NULL,
    sequence_1_orientation orientation NOT NULL,
    versioned_transcript_id integer NOT NULL
);


ALTER TABLE public.double_stranded_intended_target OWNER TO postgres;

--
-- TOC entry 5166 (class 0 OID 0)
-- Dependencies: 219
-- Name: TABLE double_stranded_intended_target; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE double_stranded_intended_target IS 'Transcript (with specific version) that was target for a ds design';


--
-- TOC entry 5167 (class 0 OID 0)
-- Dependencies: 219
-- Name: COLUMN double_stranded_intended_target.sequence_1_orientation; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN double_stranded_intended_target.sequence_1_orientation IS 'Orientation (sense or antisense) for the sequence in the sequence_1
column of the referenced double_stranded_design record.

If antisense, it means that sequence_1 is the reverse complement of the
target transcript sequence.';


--
-- TOC entry 220 (class 1259 OID 16783557)
-- Name: evidence; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE evidence (
    release_gene2annotation_id integer NOT NULL,
    evidence character varying(30) NOT NULL
);


ALTER TABLE public.evidence OWNER TO postgres;

--
-- TOC entry 5169 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE evidence; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE evidence IS 'evidence of an annotation

This could be renamed to annotation_evidence';


--
-- TOC entry 5170 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN evidence.release_gene2annotation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN evidence.release_gene2annotation_id IS 'ID of release_gene2annotation';


--
-- TOC entry 5171 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN evidence.evidence; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN evidence.evidence IS 'evidence codes from GeneOntology';


--
-- TOC entry 221 (class 1259 OID 16783560)
-- Name: executed_liquid_transfer; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE executed_liquid_transfer (
    executed_liquid_transfer_id integer NOT NULL,
    db_user_id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    transfer_type character varying(20) NOT NULL,
    planned_liquid_transfer_id integer NOT NULL
);


ALTER TABLE public.executed_liquid_transfer OWNER TO thelma;

--
-- TOC entry 222 (class 1259 OID 16783564)
-- Name: executed_rack_sample_transfer; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE executed_rack_sample_transfer (
    executed_liquid_transfer_id integer NOT NULL,
    target_rack_id integer NOT NULL,
    source_rack_id integer NOT NULL
);


ALTER TABLE public.executed_rack_sample_transfer OWNER TO thelma;

--
-- TOC entry 223 (class 1259 OID 16783567)
-- Name: executed_sample_dilution; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE executed_sample_dilution (
    executed_liquid_transfer_id integer NOT NULL,
    target_container_id integer NOT NULL,
    reservoir_specs_id integer NOT NULL
);


ALTER TABLE public.executed_sample_dilution OWNER TO thelma;

--
-- TOC entry 224 (class 1259 OID 16783570)
-- Name: executed_sample_transfer; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE executed_sample_transfer (
    executed_liquid_transfer_id integer NOT NULL,
    source_container_id integer NOT NULL,
    target_container_id integer NOT NULL
);


ALTER TABLE public.executed_sample_transfer OWNER TO thelma;

--
-- TOC entry 225 (class 1259 OID 16783573)
-- Name: executed_liquid_transfer_executed_liquid_transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE executed_liquid_transfer_executed_liquid_transfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.executed_liquid_transfer_executed_liquid_transfer_id_seq OWNER TO thelma;

--
-- TOC entry 5177 (class 0 OID 0)
-- Dependencies: 225
-- Name: executed_liquid_transfer_executed_liquid_transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE executed_liquid_transfer_executed_liquid_transfer_id_seq OWNED BY executed_liquid_transfer.executed_liquid_transfer_id;


--
-- TOC entry 226 (class 1259 OID 16783575)
-- Name: executed_worklist; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE executed_worklist (
    executed_worklist_id integer NOT NULL,
    planned_worklist_id integer NOT NULL
);


ALTER TABLE public.executed_worklist OWNER TO thelma;

--
-- TOC entry 227 (class 1259 OID 16783578)
-- Name: executed_worklist_executed_worklist_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE executed_worklist_executed_worklist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.executed_worklist_executed_worklist_id_seq OWNER TO thelma;

--
-- TOC entry 5179 (class 0 OID 0)
-- Dependencies: 227
-- Name: executed_worklist_executed_worklist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE executed_worklist_executed_worklist_id_seq OWNED BY executed_worklist.executed_worklist_id;


--
-- TOC entry 228 (class 1259 OID 16783580)
-- Name: executed_worklist_member; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE executed_worklist_member (
    executed_worklist_id integer NOT NULL,
    executed_liquid_transfer_id integer NOT NULL
);


ALTER TABLE public.executed_worklist_member OWNER TO thelma;

--
-- TOC entry 229 (class 1259 OID 16783593)
-- Name: experiment_design; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE experiment_design (
    experiment_design_id integer NOT NULL,
    rack_shape_name character varying NOT NULL,
    experiment_metadata_id integer NOT NULL
);


ALTER TABLE public.experiment_design OWNER TO thelma;

--
-- TOC entry 5181 (class 0 OID 0)
-- Dependencies: 229
-- Name: TABLE experiment_design; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE experiment_design IS 'Replacement for the deprecated "experimental_design" table.';


--
-- TOC entry 230 (class 1259 OID 16783599)
-- Name: experiment_design_experiment_design_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE experiment_design_experiment_design_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.experiment_design_experiment_design_id_seq OWNER TO thelma;

--
-- TOC entry 5183 (class 0 OID 0)
-- Dependencies: 230
-- Name: experiment_design_experiment_design_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE experiment_design_experiment_design_id_seq OWNED BY experiment_design.experiment_design_id;


--
-- TOC entry 231 (class 1259 OID 16783601)
-- Name: experiment_design_rack; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE experiment_design_rack (
    experiment_design_rack_id integer NOT NULL,
    label character varying NOT NULL,
    experiment_design_id integer NOT NULL,
    rack_layout_id integer NOT NULL
);


ALTER TABLE public.experiment_design_rack OWNER TO thelma;

--
-- TOC entry 5184 (class 0 OID 0)
-- Dependencies: 231
-- Name: TABLE experiment_design_rack; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE experiment_design_rack IS 'Replacement for the deprecated "experimental_design_rack" table. Holds a
rack layout for a single rack in an experiment design.';


--
-- TOC entry 232 (class 1259 OID 16783607)
-- Name: experiment_design_rack_experiment_design_rack_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE experiment_design_rack_experiment_design_rack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.experiment_design_rack_experiment_design_rack_id_seq OWNER TO thelma;

--
-- TOC entry 5186 (class 0 OID 0)
-- Dependencies: 232
-- Name: experiment_design_rack_experiment_design_rack_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE experiment_design_rack_experiment_design_rack_id_seq OWNED BY experiment_design_rack.experiment_design_rack_id;


--
-- TOC entry 233 (class 1259 OID 16783611)
-- Name: experiment_metadata; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE experiment_metadata (
    experiment_metadata_id integer NOT NULL,
    label character varying NOT NULL,
    subproject_id integer NOT NULL,
    number_replicates integer DEFAULT 1 NOT NULL,
    creation_date timestamp with time zone DEFAULT now() NOT NULL,
    ticket_number integer NOT NULL,
    experiment_metadata_type_id character varying(10) NOT NULL
);


ALTER TABLE public.experiment_metadata OWNER TO thelma;

--
-- TOC entry 5187 (class 0 OID 0)
-- Dependencies: 233
-- Name: TABLE experiment_metadata; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE experiment_metadata IS 'Metadata for a set of experiments to be conducted within the scope of a
 subproject. The experiment metadata requires a subproject, an experimental
 design and a sample order metadata upon creation; the (sample) molecule design
 set and the target set can initially be empty.';


--
-- TOC entry 234 (class 1259 OID 16783618)
-- Name: experiment_metadata_experiment_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE experiment_metadata_experiment_metadata_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.experiment_metadata_experiment_metadata_id_seq OWNER TO thelma;

--
-- TOC entry 5189 (class 0 OID 0)
-- Dependencies: 234
-- Name: experiment_metadata_experiment_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE experiment_metadata_experiment_metadata_id_seq OWNED BY experiment_metadata.experiment_metadata_id;


--
-- TOC entry 235 (class 1259 OID 16783620)
-- Name: experiment_metadata_iso_request; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE experiment_metadata_iso_request (
    experiment_metadata_id integer NOT NULL,
    iso_request_id integer NOT NULL
);


ALTER TABLE public.experiment_metadata_iso_request OWNER TO gathmann;

--
-- TOC entry 236 (class 1259 OID 16783623)
-- Name: experiment_metadata_molecule_design_set; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE experiment_metadata_molecule_design_set (
    experiment_metadata_id integer NOT NULL,
    molecule_design_set_id integer NOT NULL
);


ALTER TABLE public.experiment_metadata_molecule_design_set OWNER TO gathmann;

--
-- TOC entry 237 (class 1259 OID 16783626)
-- Name: experiment_metadata_target_set; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE experiment_metadata_target_set (
    experiment_metadata_id integer NOT NULL,
    target_set_id integer NOT NULL
);


ALTER TABLE public.experiment_metadata_target_set OWNER TO gathmann;

--
-- TOC entry 238 (class 1259 OID 16783629)
-- Name: experiment_metadata_type; Type: TABLE; Schema: public; Owner: berger; Tablespace: 
--

CREATE TABLE experiment_metadata_type (
    experiment_metadata_type_id character varying(10) NOT NULL,
    display_name character varying NOT NULL
);


ALTER TABLE public.experiment_metadata_type OWNER TO berger;

--
-- TOC entry 239 (class 1259 OID 16783643)
-- Name: experiment_sample_experiment_sample_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE experiment_sample_experiment_sample_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.experiment_sample_experiment_sample_id_seq OWNER TO postgres;

--
-- TOC entry 240 (class 1259 OID 16783645)
-- Name: experiment_source_rack; Type: TABLE; Schema: public; Owner: berger; Tablespace: 
--

CREATE TABLE experiment_source_rack (
    experiment_id integer NOT NULL,
    rack_id integer NOT NULL
);


ALTER TABLE public.experiment_source_rack OWNER TO berger;

--
-- TOC entry 241 (class 1259 OID 16783733)
-- Name: external_primer_carrier; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE external_primer_carrier (
    carrier_id integer NOT NULL,
    species_id integer NOT NULL,
    external_carrier_id integer NOT NULL
);


ALTER TABLE public.external_primer_carrier OWNER TO postgres;

--
-- TOC entry 5196 (class 0 OID 0)
-- Dependencies: 241
-- Name: TABLE external_primer_carrier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE external_primer_carrier IS 'Maps external primer carrier IDs to internal rack IDs for worm and fly
primer shipments.';


--
-- TOC entry 5197 (class 0 OID 0)
-- Dependencies: 241
-- Name: COLUMN external_primer_carrier.external_carrier_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN external_primer_carrier.external_carrier_id IS 'The sequential rack ID used to identify a rack delivered by an external
primer supplier. The term "carrier" is a precursor to our current term
"rack".';


--
-- TOC entry 242 (class 1259 OID 16783736)
-- Name: file; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE file (
    file_id integer NOT NULL,
    file_type_id integer NOT NULL,
    file_name character varying(128) NOT NULL,
    file_extension character varying(32),
    file_storage_site_id integer NOT NULL,
    CONSTRAINT file_name CHECK (((((file_name)::text ~ similar_escape('[^/]+'::text, NULL::text)) AND ((file_name)::text <> '.'::text)) AND ((file_name)::text <> '..'::text)))
);


ALTER TABLE public.file OWNER TO postgres;

--
-- TOC entry 5199 (class 0 OID 0)
-- Dependencies: 242
-- Name: TABLE file; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE file IS 'Reference to a  file stored on a file server';


--
-- TOC entry 5200 (class 0 OID 0)
-- Dependencies: 242
-- Name: COLUMN file.file_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file.file_id IS 'Surrogate primary key of the file

Internal ID.  Do not publish.

Because we only store the leaf name in file_name, this column is required to
allow single-column foreign keys to this table.  If we stored the absolute
file name in file_name, value of this column would be questionable and we
could consider dropping it and using file_name as the primary key in its
place.

WARNING: there should be a unique constraint on (file_name,
file_storage_site_id).  Add ASAP!';


--
-- TOC entry 5201 (class 0 OID 0)
-- Dependencies: 242
-- Name: COLUMN file.file_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file.file_type_id IS 'ID of file type

This is not the MIME type.  File types indicate the "purpose" of the file
in the Cenix context.';


--
-- TOC entry 5202 (class 0 OID 0)
-- Dependencies: 242
-- Name: COLUMN file.file_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file.file_name IS 'Unix leaf file name (relative to parent directory)';


--
-- TOC entry 5203 (class 0 OID 0)
-- Dependencies: 242
-- Name: COLUMN file.file_extension; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file.file_extension IS 'Filename extension (part after the last dot (''.'') in file_name.

This column''s contents are entirely redundant with file_name and no constraint
ensures that the values remain in synch.  If the intent is to give information
on the type of file, consider replacing this column with the MIME type.  If
the file extension is what is actually required, replace this column with an
indexed function to extract the extension from file_name.';


--
-- TOC entry 5204 (class 0 OID 0)
-- Dependencies: 242
-- Name: COLUMN file.file_storage_site_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file.file_storage_site_id IS 'ID of file storage site, i.e., parent directory';


--
-- TOC entry 5205 (class 0 OID 0)
-- Dependencies: 242
-- Name: CONSTRAINT file_name ON file; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT file_name ON file IS 'Ensure no directory separators or relative references appear in the file name';


--
-- TOC entry 243 (class 1259 OID 16783740)
-- Name: file_file_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE file_file_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_file_id_seq OWNER TO postgres;

--
-- TOC entry 5207 (class 0 OID 0)
-- Dependencies: 243
-- Name: file_file_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE file_file_id_seq OWNED BY file.file_id;


--
-- TOC entry 244 (class 1259 OID 16783742)
-- Name: file_set; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE file_set (
    file_set_id integer NOT NULL
);


ALTER TABLE public.file_set OWNER TO postgres;

--
-- TOC entry 5209 (class 0 OID 0)
-- Dependencies: 244
-- Name: TABLE file_set; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE file_set IS 'A set of related files

This is a mere grouping.  We store no information about the file set itself.
As such, this table doesn''t seem very useful.  However, CeLMA relies on it.';


--
-- TOC entry 5210 (class 0 OID 0)
-- Dependencies: 244
-- Name: COLUMN file_set.file_set_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file_set.file_set_id IS 'Surrogate primary key of the file set

Internal ID.  Do not publish.';


--
-- TOC entry 245 (class 1259 OID 16783745)
-- Name: file_set_file_set_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE file_set_file_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_set_file_set_id_seq OWNER TO postgres;

--
-- TOC entry 5212 (class 0 OID 0)
-- Dependencies: 245
-- Name: file_set_file_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE file_set_file_set_id_seq OWNED BY file_set.file_set_id;


--
-- TOC entry 246 (class 1259 OID 16783747)
-- Name: file_set_files; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE file_set_files (
    file_id integer NOT NULL,
    file_set_id integer NOT NULL
);


ALTER TABLE public.file_set_files OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 16783750)
-- Name: file_storage_site; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE file_storage_site (
    file_storage_site_id integer NOT NULL,
    path character varying NOT NULL,
    CONSTRAINT path CHECK ((((path)::text ~ similar_escape('/|(/[^/]+)+'::text, NULL::text)) AND ((path)::text !~ similar_escape('.*/.(/.*|$)'::text, NULL::text))))
);


ALTER TABLE public.file_storage_site OWNER TO postgres;

--
-- TOC entry 5215 (class 0 OID 0)
-- Dependencies: 247
-- Name: TABLE file_storage_site; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE file_storage_site IS 'A site where files can be stored (i.e., a directory)';


--
-- TOC entry 5216 (class 0 OID 0)
-- Dependencies: 247
-- Name: COLUMN file_storage_site.file_storage_site_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file_storage_site.file_storage_site_id IS 'Surrogate primary key of the file storage site

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
path as the primary key in its place.';


--
-- TOC entry 5217 (class 0 OID 0)
-- Dependencies: 247
-- Name: COLUMN file_storage_site.path; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file_storage_site.path IS 'Absolute Unix directory path';


--
-- TOC entry 5218 (class 0 OID 0)
-- Dependencies: 247
-- Name: CONSTRAINT path ON file_storage_site; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT path ON file_storage_site IS 'Ensure path begins with a slash, does not end with a slash and has no relative
references';


--
-- TOC entry 248 (class 1259 OID 16783757)
-- Name: file_storage_site_file_storage_site_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE file_storage_site_file_storage_site_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_storage_site_file_storage_site_id_seq OWNER TO postgres;

--
-- TOC entry 5220 (class 0 OID 0)
-- Dependencies: 248
-- Name: file_storage_site_file_storage_site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE file_storage_site_file_storage_site_id_seq OWNED BY file_storage_site.file_storage_site_id;


--
-- TOC entry 249 (class 1259 OID 16783759)
-- Name: file_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE file_type (
    file_type_id integer NOT NULL,
    name character varying(64) NOT NULL,
    pattern character varying(16),
    description character varying(256)
);


ALTER TABLE public.file_type OWNER TO postgres;

--
-- TOC entry 5222 (class 0 OID 0)
-- Dependencies: 249
-- Name: TABLE file_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE file_type IS 'A type of file

This is not the MIME type.  File types indicate the "purpose" of the file
in the Cenix context.';


--
-- TOC entry 5223 (class 0 OID 0)
-- Dependencies: 249
-- Name: COLUMN file_type.file_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file_type.file_type_id IS 'Surrogate primary key of the file type

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name as the primary key in its place.';


--
-- TOC entry 5224 (class 0 OID 0)
-- Dependencies: 249
-- Name: COLUMN file_type.pattern; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file_type.pattern IS 'Pattern that matches files of this type (optional)

The pattern is a string which may appear at any position in the file name.

There is no need to allow NULLs in this column.  Consider adding a NOT NULL
constraint and setting the default value to the empty string.';


--
-- TOC entry 5225 (class 0 OID 0)
-- Dependencies: 249
-- Name: COLUMN file_type.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN file_type.description IS 'Human-readable description of file type (optional)

There is no need to allow NULLs in this column.  Consider adding a NOT NULL
constraint and setting the default value to the empty string.';


--
-- TOC entry 250 (class 1259 OID 16783762)
-- Name: file_type_file_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE file_type_file_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.file_type_file_type_id_seq OWNER TO postgres;

--
-- TOC entry 5227 (class 0 OID 0)
-- Dependencies: 250
-- Name: file_type_file_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE file_type_file_type_id_seq OWNED BY file_type.file_type_id;


--
-- TOC entry 251 (class 1259 OID 16783764)
-- Name: gene_gene_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE gene_gene_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gene_gene_id_seq OWNER TO postgres;

--
-- TOC entry 252 (class 1259 OID 16783766)
-- Name: gene; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE gene (
    gene_id integer DEFAULT nextval('gene_gene_id_seq'::regclass) NOT NULL,
    accession character varying(32) NOT NULL,
    locus_name character varying(40) NOT NULL,
    species_id integer NOT NULL
);


ALTER TABLE public.gene OWNER TO postgres;

--
-- TOC entry 5230 (class 0 OID 0)
-- Dependencies: 252
-- Name: TABLE gene; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE gene IS 'Gene';


--
-- TOC entry 5231 (class 0 OID 0)
-- Dependencies: 252
-- Name: COLUMN gene.accession; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN gene.accession IS 'Unique accession assigned by annotation DB (e.g. NCBI Gene)';


--
-- TOC entry 253 (class 1259 OID 16783770)
-- Name: gene2annotation_gene2annotation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE gene2annotation_gene2annotation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gene2annotation_gene2annotation_id_seq OWNER TO postgres;

--
-- TOC entry 254 (class 1259 OID 16783772)
-- Name: gene2annotation; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE gene2annotation (
    gene2annotation_id integer DEFAULT nextval('gene2annotation_gene2annotation_id_seq'::regclass) NOT NULL,
    gene_id integer NOT NULL,
    annotation_id integer NOT NULL
);


ALTER TABLE public.gene2annotation OWNER TO postgres;

--
-- TOC entry 5234 (class 0 OID 0)
-- Dependencies: 254
-- Name: TABLE gene2annotation; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE gene2annotation IS 'Associates gene with annotation

To find associations based on particular annotation DB release,
use release_gene2annotation.';


--
-- TOC entry 255 (class 1259 OID 16783776)
-- Name: gene_identifier; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE gene_identifier (
    gene_identifier_id integer NOT NULL,
    name character varying(64) NOT NULL,
    seq_identifier_type_id integer NOT NULL,
    gene_id integer NOT NULL
);


ALTER TABLE public.gene_identifier OWNER TO postgres;

--
-- TOC entry 5236 (class 0 OID 0)
-- Dependencies: 255
-- Name: TABLE gene_identifier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE gene_identifier IS 'Identifier associated with gene by annotation DB';


--
-- TOC entry 256 (class 1259 OID 16783779)
-- Name: gene_identifier_gene_identifier_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE gene_identifier_gene_identifier_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gene_identifier_gene_identifier_id_seq OWNER TO postgres;

--
-- TOC entry 5238 (class 0 OID 0)
-- Dependencies: 256
-- Name: gene_identifier_gene_identifier_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE gene_identifier_gene_identifier_id_seq OWNED BY gene_identifier.gene_identifier_id;


--
-- TOC entry 257 (class 1259 OID 16783781)
-- Name: humane_rack; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW humane_rack AS
    SELECT r.barcode, rs.name AS rack_specs_name, r.item_status FROM rack r, rack_specs rs WHERE (r.rack_specs_id = rs.rack_specs_id);


ALTER TABLE public.humane_rack OWNER TO postgres;

--
-- TOC entry 5240 (class 0 OID 0)
-- Dependencies: 257
-- Name: VIEW humane_rack; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW humane_rack IS 'View of rack with only human readable data items.  Supports insert.';


--
-- TOC entry 258 (class 1259 OID 16783785)
-- Name: hybridization_hybridization_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE hybridization_hybridization_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.hybridization_hybridization_id_seq OWNER TO postgres;

--
-- TOC entry 259 (class 1259 OID 16783787)
-- Name: image_analysis_task_item; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE image_analysis_task_item (
    image_file_set_id integer NOT NULL,
    task_item_id integer NOT NULL
);


ALTER TABLE public.image_analysis_task_item OWNER TO postgres;

--
-- TOC entry 5243 (class 0 OID 0)
-- Dependencies: 259
-- Name: TABLE image_analysis_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE image_analysis_task_item IS 'Additional information for completed image analysis task items.

DEPRECATED.

This has never been used and should probably be dropped.';


--
-- TOC entry 5244 (class 0 OID 0)
-- Dependencies: 259
-- Name: COLUMN image_analysis_task_item.image_file_set_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN image_analysis_task_item.image_file_set_id IS 'ID of file set containing all images analysed for this task item.';


--
-- TOC entry 260 (class 1259 OID 16783790)
-- Name: image_object_image_object_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE image_object_image_object_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.image_object_image_object_id_seq OWNER TO postgres;

--
-- TOC entry 261 (class 1259 OID 16783792)
-- Name: intended_mirna_target; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE intended_mirna_target (
    molecule_design_id integer NOT NULL,
    accession character varying(24) NOT NULL
);


ALTER TABLE public.intended_mirna_target OWNER TO postgres;

--
-- TOC entry 5247 (class 0 OID 0)
-- Dependencies: 261
-- Name: TABLE intended_mirna_target; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE intended_mirna_target IS 'Intended microRNA target for molecule';


--
-- TOC entry 262 (class 1259 OID 16783795)
-- Name: intended_target; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE intended_target (
    molecule_design_id integer NOT NULL,
    versioned_transcript_id integer NOT NULL
);


ALTER TABLE public.intended_target OWNER TO postgres;

--
-- TOC entry 5249 (class 0 OID 0)
-- Dependencies: 262
-- Name: TABLE intended_target; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE intended_target IS 'Transcript (with specific version) that was target for a molecule design';


--
-- TOC entry 263 (class 1259 OID 16783798)
-- Name: iso; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE iso (
    iso_id integer NOT NULL,
    label character varying NOT NULL,
    status character varying NOT NULL,
    iso_request_id integer NOT NULL,
    optimizer_excluded_racks character varying,
    optimizer_requested_tubes character varying,
    rack_layout_id integer NOT NULL,
    iso_type character varying(20) NOT NULL,
    number_stock_racks integer NOT NULL,
    CONSTRAINT iso_number_stock_racks_non_negative CHECK ((number_stock_racks >= 0)),
    CONSTRAINT valid_iso_type CHECK (((iso_type)::text = ANY (ARRAY[('BASE'::character varying)::text, ('LAB'::character varying)::text, ('STOCK_SAMPLE_GEN'::character varying)::text])))
);


ALTER TABLE public.iso OWNER TO thelma;

--
-- TOC entry 5251 (class 0 OID 0)
-- Dependencies: 263
-- Name: TABLE iso; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE iso IS 'Order of a set of sample molecule designs arranged on a single physical
rack. The rack layout is specified by the sample order plan held by the
 associated experiment plan.';


--
-- TOC entry 264 (class 1259 OID 16783806)
-- Name: iso_iso_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE iso_iso_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.iso_iso_id_seq OWNER TO thelma;

--
-- TOC entry 5253 (class 0 OID 0)
-- Dependencies: 264
-- Name: iso_iso_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE iso_iso_id_seq OWNED BY iso.iso_id;


--
-- TOC entry 265 (class 1259 OID 16783808)
-- Name: iso_aliquot_plate; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_aliquot_plate (
    iso_plate_id integer NOT NULL,
    has_been_used boolean NOT NULL
);


ALTER TABLE public.iso_aliquot_plate OWNER TO gathmann;

--
-- TOC entry 266 (class 1259 OID 16783811)
-- Name: iso_job; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_job (
    job_id integer NOT NULL,
    number_stock_racks integer NOT NULL,
    CONSTRAINT job_number_stock_racks_non_negative CHECK ((number_stock_racks >= 0))
);


ALTER TABLE public.iso_job OWNER TO gathmann;

--
-- TOC entry 267 (class 1259 OID 16783815)
-- Name: iso_job_member; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE iso_job_member (
    iso_id integer NOT NULL,
    job_id integer NOT NULL
);


ALTER TABLE public.iso_job_member OWNER TO thelma;

--
-- TOC entry 268 (class 1259 OID 16783818)
-- Name: iso_job_preparation_plate; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_job_preparation_plate (
    iso_job_preparation_plate_id integer NOT NULL,
    rack_id integer NOT NULL,
    rack_layout_id integer NOT NULL,
    job_id integer NOT NULL
);


ALTER TABLE public.iso_job_preparation_plate OWNER TO gathmann;

--
-- TOC entry 269 (class 1259 OID 16783821)
-- Name: iso_job_preparation_plate_iso_job_preparation_plate_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE iso_job_preparation_plate_iso_job_preparation_plate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.iso_job_preparation_plate_iso_job_preparation_plate_id_seq OWNER TO gathmann;

--
-- TOC entry 5255 (class 0 OID 0)
-- Dependencies: 269
-- Name: iso_job_preparation_plate_iso_job_preparation_plate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE iso_job_preparation_plate_iso_job_preparation_plate_id_seq OWNED BY iso_job_preparation_plate.iso_job_preparation_plate_id;


--
-- TOC entry 270 (class 1259 OID 16783823)
-- Name: iso_job_stock_rack; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_job_stock_rack (
    stock_rack_id integer NOT NULL,
    job_id integer NOT NULL
);


ALTER TABLE public.iso_job_stock_rack OWNER TO gathmann;

--
-- TOC entry 271 (class 1259 OID 16783826)
-- Name: iso_molecule_design_set; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_molecule_design_set (
    iso_id integer NOT NULL,
    molecule_design_set_id integer NOT NULL
);


ALTER TABLE public.iso_molecule_design_set OWNER TO gathmann;

--
-- TOC entry 272 (class 1259 OID 16783829)
-- Name: iso_plate; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_plate (
    iso_plate_id integer NOT NULL,
    iso_id integer NOT NULL,
    rack_id integer NOT NULL,
    iso_plate_type character varying(14) NOT NULL,
    CONSTRAINT iso_plate_iso_plate_type_check CHECK (((iso_plate_type)::text = ANY (ARRAY[('ISO_PLATE'::character varying)::text, ('ALIQUOT'::character varying)::text, ('PREPARATION'::character varying)::text, ('SECTOR_PREP'::character varying)::text])))
);


ALTER TABLE public.iso_plate OWNER TO gathmann;

--
-- TOC entry 273 (class 1259 OID 16783833)
-- Name: iso_plate_iso_plate_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE iso_plate_iso_plate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.iso_plate_iso_plate_id_seq OWNER TO gathmann;

--
-- TOC entry 5257 (class 0 OID 0)
-- Dependencies: 273
-- Name: iso_plate_iso_plate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE iso_plate_iso_plate_id_seq OWNED BY iso_plate.iso_plate_id;


--
-- TOC entry 274 (class 1259 OID 16783835)
-- Name: iso_pool_set; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_pool_set (
    iso_id integer NOT NULL,
    molecule_design_pool_set_id integer NOT NULL
);


ALTER TABLE public.iso_pool_set OWNER TO gathmann;

--
-- TOC entry 275 (class 1259 OID 16783838)
-- Name: iso_preparation_plate; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_preparation_plate (
    iso_plate_id integer NOT NULL,
    rack_layout_id integer NOT NULL
);


ALTER TABLE public.iso_preparation_plate OWNER TO gathmann;

--
-- TOC entry 276 (class 1259 OID 16783841)
-- Name: iso_racks; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE iso_racks (
    iso_id integer NOT NULL,
    preparation_plate_id integer NOT NULL,
    iso_plate_id integer NOT NULL,
    stock_rack_id integer NOT NULL
);


ALTER TABLE public.iso_racks OWNER TO thelma;

--
-- TOC entry 277 (class 1259 OID 16783844)
-- Name: iso_request; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE iso_request (
    iso_request_id integer NOT NULL,
    label character varying NOT NULL,
    expected_number_isos integer NOT NULL,
    owner character varying DEFAULT ''::character varying NOT NULL,
    number_aliquots integer NOT NULL,
    iso_type character varying(20) NOT NULL,
    CONSTRAINT iso_request_number_aliquots_non_negative CHECK ((number_aliquots >= 0)),
    CONSTRAINT iso_request_positive_exp_number_plates CHECK ((expected_number_isos >= 1)),
    CONSTRAINT valid_iso_request_iso_type CHECK (((iso_type)::text = ANY (ARRAY[('BASE'::character varying)::text, ('LAB'::character varying)::text, ('STOCK_SAMPLE_GEN'::character varying)::text])))
);


ALTER TABLE public.iso_request OWNER TO thelma;

--
-- TOC entry 5260 (class 0 OID 0)
-- Dependencies: 277
-- Name: TABLE iso_request; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE iso_request IS 'Plan for a set of sample orders in a particular layout, volume,
 concentration and rack type.';


--
-- TOC entry 278 (class 1259 OID 16783854)
-- Name: iso_request_pool_set; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_request_pool_set (
    iso_request_id integer NOT NULL,
    molecule_design_pool_set_id integer NOT NULL
);


ALTER TABLE public.iso_request_pool_set OWNER TO gathmann;

--
-- TOC entry 279 (class 1259 OID 16783857)
-- Name: iso_sector_preparation_plate; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_sector_preparation_plate (
    iso_plate_id integer NOT NULL,
    sector_index integer NOT NULL,
    rack_layout_id integer NOT NULL,
    CONSTRAINT iso_sector_preparation_plate_index_non_negative CHECK ((sector_index >= 0))
);


ALTER TABLE public.iso_sector_preparation_plate OWNER TO gathmann;

--
-- TOC entry 280 (class 1259 OID 16783861)
-- Name: iso_sector_stock_rack; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_sector_stock_rack (
    stock_rack_id integer NOT NULL,
    iso_id integer NOT NULL,
    sector_index integer NOT NULL,
    CONSTRAINT iso_sector_stock_rack_sector_index_non_negative CHECK ((sector_index >= 0))
);


ALTER TABLE public.iso_sector_stock_rack OWNER TO gathmann;

--
-- TOC entry 281 (class 1259 OID 16783865)
-- Name: iso_stock_rack; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE iso_stock_rack (
    stock_rack_id integer NOT NULL,
    iso_id integer NOT NULL
);


ALTER TABLE public.iso_stock_rack OWNER TO gathmann;

--
-- TOC entry 282 (class 1259 OID 16783868)
-- Name: item_status; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE item_status (
    item_status_id character varying(9) NOT NULL,
    name character varying(18) NOT NULL,
    description text DEFAULT ''::text,
    CONSTRAINT item_status_item_status_id_check CHECK ((char_length((item_status_id)::text) > 0)),
    CONSTRAINT item_status_name_check CHECK ((char_length((name)::text) > 0))
);


ALTER TABLE public.item_status OWNER TO postgres;

--
-- TOC entry 5262 (class 0 OID 0)
-- Dependencies: 282
-- Name: TABLE item_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE item_status IS 'Status of inventory items';


--
-- TOC entry 283 (class 1259 OID 16783877)
-- Name: job; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE job (
    job_id integer NOT NULL,
    job_type_id integer NOT NULL,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    label character varying(64) NOT NULL,
    description text,
    db_user_id integer NOT NULL,
    subproject_id integer NOT NULL,
    status_type character varying(12) NOT NULL,
    type character varying(20) DEFAULT 'OTHER'::character varying NOT NULL,
    CONSTRAINT valid_job_type CHECK (((type)::text = ANY (ARRAY[('OTHER'::character varying)::text, ('RNAI_EXPERIMENT'::character varying)::text, ('ISO_PROCESSING'::character varying)::text])))
);


ALTER TABLE public.job OWNER TO postgres;

--
-- TOC entry 5264 (class 0 OID 0)
-- Dependencies: 283
-- Name: TABLE job; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE job IS 'A job, that is a concrete instance of a job type.';


--
-- TOC entry 5265 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.job_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.job_id IS 'Surrogate primary key of the job';


--
-- TOC entry 5266 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.start_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.start_time IS 'Time processing of the job was started (optional)

This is probably redundant with task.start_time.  Consider dropping.';


--
-- TOC entry 5267 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.end_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.end_time IS 'Time processing of the job was completed (optional)

This is probably redundant with task.end_time.  Consider dropping.';


--
-- TOC entry 5268 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.label IS 'User-assigned name for the job';


--
-- TOC entry 5269 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.description IS 'Option description of the purpose of this job or special instructions

NULLs do not need to be allowed in this column.  Consider adding a NOT NULL
constraint and setting the default value to the empty string.';


--
-- TOC entry 5270 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.db_user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.db_user_id IS 'User who had scheduled the job';


--
-- TOC entry 5271 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.subproject_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.subproject_id IS 'Subproject this job is part of.';


--
-- TOC entry 5272 (class 0 OID 0)
-- Dependencies: 283
-- Name: COLUMN job.status_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job.status_type IS 'Status of the job.';


--
-- TOC entry 284 (class 1259 OID 16783885)
-- Name: job_job_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE job_job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_job_id_seq OWNER TO postgres;

--
-- TOC entry 5274 (class 0 OID 0)
-- Dependencies: 284
-- Name: job_job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE job_job_id_seq OWNED BY job.job_id;


--
-- TOC entry 285 (class 1259 OID 16783887)
-- Name: job_step; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE job_step (
    job_id integer NOT NULL,
    xml_id character varying(64) NOT NULL,
    task_type_id integer NOT NULL,
    label character varying(64),
    instruction text,
    job_step_id integer DEFAULT nextval(('job_step_job_step_id_seq'::text)::regclass) NOT NULL
);


ALTER TABLE public.job_step OWNER TO postgres;

--
-- TOC entry 5276 (class 0 OID 0)
-- Dependencies: 285
-- Name: TABLE job_step; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE job_step IS 'A step of a job.

A job step is to a job as a task type is to a job type.

The xml_id and label columns are only needed because of the use of XML for
storing the job structure.  If we used tables to store the job structure,
xml_id, label and task_type_id could be replaced with a foreign key to a
job_type-task_type association table.';


--
-- TOC entry 5277 (class 0 OID 0)
-- Dependencies: 285
-- Name: COLUMN job_step.xml_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_step.xml_id IS 'ID from job_type XML for the job step.';


--
-- TOC entry 5278 (class 0 OID 0)
-- Dependencies: 285
-- Name: COLUMN job_step.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_step.label IS 'Label from job_type XML for the job step.';


--
-- TOC entry 5279 (class 0 OID 0)
-- Dependencies: 285
-- Name: COLUMN job_step.instruction; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_step.instruction IS 'Special instructions for the person executing the job (optional)

NULLs do not need to be allowed in this column.  Consider adding a NOT NULL
constraint and setting the default value to the empty string.';


--
-- TOC entry 5280 (class 0 OID 0)
-- Dependencies: 285
-- Name: COLUMN job_step.job_step_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_step.job_step_id IS 'Surrogate primary key of the job step

Internal ID.  Do not publish.

The surrogate key is useful because otherwise other tables would have to
use a compound foreign key of (job_id, xml_id) but it is not strictly
necessary.';


--
-- TOC entry 286 (class 1259 OID 16783894)
-- Name: job_step_job_step_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE job_step_job_step_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_step_job_step_id_seq OWNER TO postgres;

--
-- TOC entry 287 (class 1259 OID 16783896)
-- Name: job_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE job_type (
    job_type_id integer NOT NULL,
    name character varying(32) NOT NULL,
    label character varying(64) NOT NULL,
    xml text NOT NULL
);


ALTER TABLE public.job_type OWNER TO postgres;

--
-- TOC entry 5283 (class 0 OID 0)
-- Dependencies: 287
-- Name: TABLE job_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE job_type IS 'Job type.

Defines a "class" of jobs of which the job entries are "instances".';


--
-- TOC entry 5284 (class 0 OID 0)
-- Dependencies: 287
-- Name: COLUMN job_type.job_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_type.job_type_id IS 'Surrogate primary key of the job type

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.';


--
-- TOC entry 5285 (class 0 OID 0)
-- Dependencies: 287
-- Name: COLUMN job_type.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_type.name IS 'User-assigned name for the job type, intended for programatic purposes

Programs should not rely on the presence of particular job types.
Probably should be dropped.';


--
-- TOC entry 5286 (class 0 OID 0)
-- Dependencies: 287
-- Name: COLUMN job_type.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_type.label IS 'User-assigned name for the job type, intended for display';


--
-- TOC entry 5287 (class 0 OID 0)
-- Dependencies: 287
-- Name: COLUMN job_type.xml; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN job_type.xml IS 'XML specification of the job steps to appear in jobs with type job_type.

Because this information is stored as XML in a text field, we can''t
enforce constraints or use SQL to manipulate job types.  Consider creating new
tables to manage the information currently encoded in XML.

The DTD for the XML is as follows:

<!DOCTYPE JobType [
  <!-- root element -->
  <!ELEMENT JobType (Task | Link)*>
  <!-- Step within the job -->
  <!ELEMENT Task>
  <!-- ID of task within the job type, used for references from Link
    -- elements.  Also used by CeLMA for SOURCE and SINK tasks.  Don''t rename
    -- those until CeLMA is fixed to use the task type instead. -->
  <!ATTLIST Task id ID #REQUIRED>
  <!-- task_type.name -->
  <!ATTLIST Task type NMTOKEN #REQUIRED>
  <!-- Position of center of task icon expressed as a fraction of size of the
    -- panel in which the job type is displayed.  The origin is the top left
    -- corner of the panel -->
  <!ATTLIST Task pos_x CDATA #REQUIRED>
  <!ATTLIST Task pos_y CDATA #REQUIRED>
  <!-- Link between to tasks.  The each task type defines zero or more input
    -- and zero or more output connectors.  A link connects an output connector
    -- of one task to the input connect of another (loopbacks from an output
    -- of a task to an input of the same task are allowed) -->
  <!ELEMENT Link>
  <!-- All current entries have an item_type of PLATE.  I don''t know what
    -- this was intended to do -->
  <!ATTLIST Link item_type NMTOKEN #REQUIRED>
  <!-- ID of source task -->
  <!ATTLIST Link from_task NMTOKEN #REQUIRED>
  <!-- ID of destination task -->
  <!ATTLIST Link to_task NMTOKEN #REQUIRED>
  <!-- Zero-based integer index of source connector  -->
  <!ATTLIST Link from_connector NMTOKEN #REQUIRED>
  <!-- Zero-based integer index of destination connector -->
  <!ATTLIST Link to_connector NMTOKEN #REQUIRED>
]>';


--
-- TOC entry 288 (class 1259 OID 16783902)
-- Name: job_type_job_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE job_type_job_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_type_job_type_id_seq OWNER TO postgres;

--
-- TOC entry 5289 (class 0 OID 0)
-- Dependencies: 288
-- Name: job_type_job_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE job_type_job_type_id_seq OWNED BY job_type.job_type_id;


--
-- TOC entry 289 (class 1259 OID 16783904)
-- Name: lab_iso_library_plate; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE lab_iso_library_plate (
    iso_id integer NOT NULL,
    library_plate_id integer NOT NULL
);


ALTER TABLE public.lab_iso_library_plate OWNER TO gathmann;

--
-- TOC entry 290 (class 1259 OID 16783907)
-- Name: lab_iso_request; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE lab_iso_request (
    iso_request_id integer NOT NULL,
    delivery_date date,
    comment character varying,
    requester_id integer NOT NULL,
    rack_layout_id integer NOT NULL,
    iso_plate_reservoir_specs_id integer NOT NULL,
    process_job_first boolean NOT NULL
);


ALTER TABLE public.lab_iso_request OWNER TO gathmann;

--
-- TOC entry 291 (class 1259 OID 16783913)
-- Name: legacy_primer_pair; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE legacy_primer_pair (
    legacy_id integer NOT NULL,
    primer_pair_id integer NOT NULL
);


ALTER TABLE public.legacy_primer_pair OWNER TO postgres;

--
-- TOC entry 5291 (class 0 OID 0)
-- Dependencies: 291
-- Name: TABLE legacy_primer_pair; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE legacy_primer_pair IS 'Maps legacy primer_pair_id to current primer_pair_id
These legacy primer_pair_id come from the Ambion project DB';


--
-- TOC entry 292 (class 1259 OID 16783916)
-- Name: library_plate; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE library_plate (
    library_plate_id integer NOT NULL,
    molecule_design_library_id integer NOT NULL,
    rack_id integer NOT NULL,
    layout_number integer NOT NULL,
    has_been_used boolean DEFAULT false NOT NULL,
    CONSTRAINT library_plate_layout_number_greater_zero CHECK ((layout_number > 0))
);


ALTER TABLE public.library_plate OWNER TO gathmann;

--
-- TOC entry 293 (class 1259 OID 16783921)
-- Name: library_plate_library_plate_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE library_plate_library_plate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.library_plate_library_plate_id_seq OWNER TO gathmann;

--
-- TOC entry 5293 (class 0 OID 0)
-- Dependencies: 293
-- Name: library_plate_library_plate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE library_plate_library_plate_id_seq OWNED BY library_plate.library_plate_id;


--
-- TOC entry 294 (class 1259 OID 16783923)
-- Name: liquid_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE liquid_type (
    liquid_type_id integer NOT NULL,
    name character varying NOT NULL,
    density double precision NOT NULL,
    CONSTRAINT liquid_type_density CHECK ((density > (0.0)::double precision))
);


ALTER TABLE public.liquid_type OWNER TO postgres;

--
-- TOC entry 5294 (class 0 OID 0)
-- Dependencies: 294
-- Name: TABLE liquid_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE liquid_type IS 'A type of liquid

For now we only store density and use this to determine sample volume from
measured mass.  In future I could imagine tracking viscosity, etc.';


--
-- TOC entry 5295 (class 0 OID 0)
-- Dependencies: 294
-- Name: COLUMN liquid_type.liquid_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN liquid_type.liquid_type_id IS 'Surrogate primary key of the liquid type

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name as the primary key in its place.';


--
-- TOC entry 5296 (class 0 OID 0)
-- Dependencies: 294
-- Name: COLUMN liquid_type.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN liquid_type.name IS 'User-assigned name for the liquid type, intended for display';


--
-- TOC entry 5297 (class 0 OID 0)
-- Dependencies: 294
-- Name: COLUMN liquid_type.density; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN liquid_type.density IS 'density in kg/l';


--
-- TOC entry 295 (class 1259 OID 16783930)
-- Name: liquid_type_liquid_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE liquid_type_liquid_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.liquid_type_liquid_type_id_seq OWNER TO postgres;

--
-- TOC entry 5299 (class 0 OID 0)
-- Dependencies: 295
-- Name: liquid_type_liquid_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE liquid_type_liquid_type_id_seq OWNED BY liquid_type.liquid_type_id;


--
-- TOC entry 296 (class 1259 OID 16783932)
-- Name: mirna; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE mirna (
    accession character varying(24) NOT NULL,
    sequence rna NOT NULL,
    CONSTRAINT mirna_accession_check CHECK ((char_length((accession)::text) > 0))
);


ALTER TABLE public.mirna OWNER TO postgres;

--
-- TOC entry 5301 (class 0 OID 0)
-- Dependencies: 296
-- Name: TABLE mirna; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE mirna IS 'microRNA.  Star sequence IDs end with a _star';


--
-- TOC entry 297 (class 1259 OID 16783939)
-- Name: molecule; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE molecule (
    molecule_id integer NOT NULL,
    insert_date timestamp with time zone DEFAULT now(),
    molecule_design_id integer NOT NULL,
    supplier_id integer NOT NULL
);


ALTER TABLE public.molecule OWNER TO postgres;

--
-- TOC entry 5303 (class 0 OID 0)
-- Dependencies: 297
-- Name: TABLE molecule; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE molecule IS 'A concrete synthesis of a particular molecule design';


--
-- TOC entry 5304 (class 0 OID 0)
-- Dependencies: 297
-- Name: COLUMN molecule.molecule_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN molecule.molecule_id IS 'Surrogate primary key of the molecule

Internal ID.  Do not publish.';


--
-- TOC entry 5305 (class 0 OID 0)
-- Dependencies: 297
-- Name: COLUMN molecule.insert_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN molecule.insert_date IS 'Date the molecule record was inserted (optional)

All new insertions should use the default value.  The insertion date typically
roughly corresponds to the delivery date of the sample containing the molecule';


--
-- TOC entry 298 (class 1259 OID 16783943)
-- Name: molecule_design; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE molecule_design (
    molecule_design_id integer NOT NULL,
    molecule_type character varying(10) NOT NULL,
    structure_hash character varying NOT NULL
);


ALTER TABLE public.molecule_design OWNER TO postgres;

--
-- TOC entry 5307 (class 0 OID 0)
-- Dependencies: 298
-- Name: TABLE molecule_design; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE molecule_design IS 'Abstract molecule structure.

Particular kinds of molecule designs are described in subtables.

WARNING: Currently, there is no constraint to prevent entries in multiple
subtables referring to a given molecule design.';


--
-- TOC entry 5308 (class 0 OID 0)
-- Dependencies: 298
-- Name: COLUMN molecule_design.molecule_design_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN molecule_design.molecule_design_id IS 'Surrogate primary key of the molecule design

Public ID.';


--
-- TOC entry 5309 (class 0 OID 0)
-- Dependencies: 298
-- Name: COLUMN molecule_design.molecule_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN molecule_design.molecule_type IS 'Type of the molecule design.

This is more specific than the classes defined by the subtables';


--
-- TOC entry 299 (class 1259 OID 16783949)
-- Name: molecule_design_gene; Type: TABLE; Schema: public; Owner: cebos; Tablespace: 
--

CREATE TABLE molecule_design_gene (
    molecule_design_id integer NOT NULL,
    gene_id integer NOT NULL
);


ALTER TABLE public.molecule_design_gene OWNER TO cebos;

--
-- TOC entry 5311 (class 0 OID 0)
-- Dependencies: 299
-- Name: TABLE molecule_design_gene; Type: COMMENT; Schema: public; Owner: cebos
--

COMMENT ON TABLE molecule_design_gene IS 'This is a materialized view to improve the speed of retrieving target info. This table is automatically updated by a trigger.';


--
-- TOC entry 300 (class 1259 OID 16783952)
-- Name: molecule_design_versioned_transcript_target; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE molecule_design_versioned_transcript_target (
    molecule_design_id integer NOT NULL,
    versioned_transcript_id integer NOT NULL
);


ALTER TABLE public.molecule_design_versioned_transcript_target OWNER TO postgres;

--
-- TOC entry 5313 (class 0 OID 0)
-- Dependencies: 300
-- Name: TABLE molecule_design_versioned_transcript_target; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE molecule_design_versioned_transcript_target IS 'Association of molecule and targtted versioned transcript.

Requires perfect match between molecule and transcript sequences.';


--
-- TOC entry 301 (class 1259 OID 16783955)
-- Name: release_gene_transcript; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE release_gene_transcript (
    gene_id integer NOT NULL,
    transcript_id integer NOT NULL,
    db_release_id integer NOT NULL,
    species_id integer NOT NULL
);


ALTER TABLE public.release_gene_transcript OWNER TO postgres;

--
-- TOC entry 5315 (class 0 OID 0)
-- Dependencies: 301
-- Name: TABLE release_gene_transcript; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE release_gene_transcript IS 'Association between gene and transcript based on specific annotation
DB release.';


--
-- TOC entry 302 (class 1259 OID 16783958)
-- Name: release_versioned_transcript; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE release_versioned_transcript (
    db_release_id integer NOT NULL,
    versioned_transcript_id integer NOT NULL
);


ALTER TABLE public.release_versioned_transcript OWNER TO postgres;

--
-- TOC entry 5317 (class 0 OID 0)
-- Dependencies: 302
-- Name: TABLE release_versioned_transcript; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE release_versioned_transcript IS 'Association between transcript and version based on specific annotation
DB release.';


--
-- TOC entry 303 (class 1259 OID 16783961)
-- Name: versioned_transcript_versioned_transcript_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE versioned_transcript_versioned_transcript_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.versioned_transcript_versioned_transcript_id_seq OWNER TO postgres;

--
-- TOC entry 304 (class 1259 OID 16783963)
-- Name: versioned_transcript; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE versioned_transcript (
    versioned_transcript_id integer DEFAULT nextval('versioned_transcript_versioned_transcript_id_seq'::regclass) NOT NULL,
    transcript_id integer NOT NULL,
    version integer NOT NULL,
    sequence dna NOT NULL
);


ALTER TABLE public.versioned_transcript OWNER TO postgres;

--
-- TOC entry 5320 (class 0 OID 0)
-- Dependencies: 304
-- Name: TABLE versioned_transcript; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE versioned_transcript IS 'Transcript whose sequence is specified by version number.

NCBI updates version number when sequence changes.';


--
-- TOC entry 305 (class 1259 OID 16783970)
-- Name: molecule_design_gene_view; Type: VIEW; Schema: public; Owner: cebos
--

CREATE VIEW molecule_design_gene_view AS
    SELECT DISTINCT mdvtt.molecule_design_id, gene.gene_id FROM molecule_design_versioned_transcript_target mdvtt, (SELECT g.gene_id, rgt.transcript_id FROM gene g, release_gene_transcript rgt, current_db_release cdr WHERE ((cdr.db_release_id = rgt.db_release_id) AND (rgt.gene_id = g.gene_id))) gene, (SELECT vt.transcript_id, vt.versioned_transcript_id FROM versioned_transcript vt, current_db_release cdr, release_versioned_transcript rvt WHERE ((cdr.db_release_id = rvt.db_release_id) AND (rvt.versioned_transcript_id = vt.versioned_transcript_id))) transcript WHERE ((gene.transcript_id = transcript.transcript_id) AND (transcript.versioned_transcript_id = mdvtt.versioned_transcript_id));


ALTER TABLE public.molecule_design_gene_view OWNER TO cebos;

--
-- TOC entry 5322 (class 0 OID 0)
-- Dependencies: 305
-- Name: VIEW molecule_design_gene_view; Type: COMMENT; Schema: public; Owner: cebos
--

COMMENT ON VIEW molecule_design_gene_view IS 'A special query to create an association view between a molecule design ID and a gene ID. This view is used by a function to update the molecule_design_gene materialized view';


--
-- TOC entry 306 (class 1259 OID 16783974)
-- Name: molecule_design_library; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_library (
    molecule_design_library_id integer NOT NULL,
    label character varying(25) NOT NULL,
    molecule_design_pool_set_id integer NOT NULL,
    final_volume double precision NOT NULL,
    final_concentration double precision NOT NULL,
    number_layouts integer NOT NULL,
    rack_layout_id integer NOT NULL,
    CONSTRAINT positive_molecule_design_library_concentration CHECK ((final_concentration > (0)::double precision)),
    CONSTRAINT positive_molecule_design_library_number_layouts CHECK ((number_layouts > 0)),
    CONSTRAINT positive_molecule_design_library_volume CHECK ((final_volume > (0)::double precision))
);


ALTER TABLE public.molecule_design_library OWNER TO gathmann;

--
-- TOC entry 307 (class 1259 OID 16783980)
-- Name: molecule_design_library_creation_iso_request; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_library_creation_iso_request (
    molecule_design_library_id integer NOT NULL,
    iso_request_id integer NOT NULL
);


ALTER TABLE public.molecule_design_library_creation_iso_request OWNER TO gathmann;

--
-- TOC entry 308 (class 1259 OID 16783983)
-- Name: molecule_design_library_lab_iso_request; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_library_lab_iso_request (
    molecule_design_library_id integer NOT NULL,
    iso_request_id integer NOT NULL
);


ALTER TABLE public.molecule_design_library_lab_iso_request OWNER TO gathmann;

--
-- TOC entry 309 (class 1259 OID 16783986)
-- Name: molecule_design_library_molecule_design_library_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE molecule_design_library_molecule_design_library_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.molecule_design_library_molecule_design_library_id_seq OWNER TO gathmann;

--
-- TOC entry 5326 (class 0 OID 0)
-- Dependencies: 309
-- Name: molecule_design_library_molecule_design_library_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE molecule_design_library_molecule_design_library_id_seq OWNED BY molecule_design_library.molecule_design_library_id;


--
-- TOC entry 310 (class 1259 OID 16783988)
-- Name: molecule_design_mirna_target; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE molecule_design_mirna_target (
    molecule_design_id integer NOT NULL,
    accession character varying(24) NOT NULL
);


ALTER TABLE public.molecule_design_mirna_target OWNER TO postgres;

--
-- TOC entry 5327 (class 0 OID 0)
-- Dependencies: 310
-- Name: TABLE molecule_design_mirna_target; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE molecule_design_mirna_target IS 'microRNA-molecule design mapping';


--
-- TOC entry 311 (class 1259 OID 16783991)
-- Name: molecule_design_molecule_design_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE molecule_design_molecule_design_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.molecule_design_molecule_design_id_seq OWNER TO postgres;

--
-- TOC entry 5329 (class 0 OID 0)
-- Dependencies: 311
-- Name: molecule_design_molecule_design_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE molecule_design_molecule_design_id_seq OWNED BY molecule_design.molecule_design_id;


--
-- TOC entry 312 (class 1259 OID 16783993)
-- Name: molecule_design_pool; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_pool (
    molecule_design_set_id integer NOT NULL,
    member_hash character varying NOT NULL,
    number_designs integer NOT NULL,
    molecule_type character varying NOT NULL,
    default_stock_concentration double precision NOT NULL,
    CONSTRAINT positive_default_stock_concentration CHECK ((default_stock_concentration > (0)::double precision)),
    CONSTRAINT stock_sample_molecule_design_set_number_designs_check CHECK ((number_designs > 0))
);


ALTER TABLE public.molecule_design_pool OWNER TO gathmann;

--
-- TOC entry 313 (class 1259 OID 16784001)
-- Name: molecule_design_pool_molecule_design_pool_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE molecule_design_pool_molecule_design_pool_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.molecule_design_pool_molecule_design_pool_id_seq OWNER TO postgres;

--
-- TOC entry 314 (class 1259 OID 16784003)
-- Name: molecule_design_pool_set; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_pool_set (
    molecule_design_pool_set_id integer NOT NULL,
    molecule_type_id character varying(20) NOT NULL
);


ALTER TABLE public.molecule_design_pool_set OWNER TO gathmann;

--
-- TOC entry 315 (class 1259 OID 16784006)
-- Name: molecule_design_pool_set_member; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_pool_set_member (
    molecule_design_pool_set_id integer NOT NULL,
    molecule_design_pool_id integer NOT NULL
);


ALTER TABLE public.molecule_design_pool_set_member OWNER TO gathmann;

--
-- TOC entry 316 (class 1259 OID 16784009)
-- Name: molecule_design_set; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE molecule_design_set (
    molecule_design_set_id integer NOT NULL,
    set_type character varying NOT NULL
);


ALTER TABLE public.molecule_design_set OWNER TO thelma;

--
-- TOC entry 5335 (class 0 OID 0)
-- Dependencies: 316
-- Name: TABLE molecule_design_set; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE molecule_design_set IS 'Named set of molecule designs.';


--
-- TOC entry 317 (class 1259 OID 16784015)
-- Name: molecule_design_set_gene; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_set_gene (
    molecule_design_set_id integer NOT NULL,
    gene_id integer NOT NULL
);


ALTER TABLE public.molecule_design_set_gene OWNER TO gathmann;

--
-- TOC entry 5337 (class 0 OID 0)
-- Dependencies: 317
-- Name: TABLE molecule_design_set_gene; Type: COMMENT; Schema: public; Owner: gathmann
--

COMMENT ON TABLE molecule_design_set_gene IS 'Materialized view for molecule design set gene targets.';


--
-- TOC entry 318 (class 1259 OID 16784018)
-- Name: molecule_design_set_member; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE molecule_design_set_member (
    molecule_design_set_id integer NOT NULL,
    molecule_design_id integer NOT NULL
);


ALTER TABLE public.molecule_design_set_member OWNER TO thelma;

--
-- TOC entry 5339 (class 0 OID 0)
-- Dependencies: 318
-- Name: TABLE molecule_design_set_member; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE molecule_design_set_member IS 'Member of a molecule design set.';


--
-- TOC entry 319 (class 1259 OID 16784021)
-- Name: molecule_design_set_gene_view; Type: VIEW; Schema: public; Owner: gathmann
--

CREATE VIEW molecule_design_set_gene_view AS
    SELECT DISTINCT ssmds.molecule_design_set_id, mdg.gene_id FROM ((molecule_design_pool ssmds JOIN molecule_design_set_member mdsm ON ((mdsm.molecule_design_set_id = ssmds.molecule_design_set_id))) JOIN molecule_design_gene mdg ON ((mdg.molecule_design_id = mdsm.molecule_design_id)));


ALTER TABLE public.molecule_design_set_gene_view OWNER TO gathmann;

--
-- TOC entry 320 (class 1259 OID 16784025)
-- Name: molecule_design_set_molecule_design_set_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE molecule_design_set_molecule_design_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.molecule_design_set_molecule_design_set_id_seq OWNER TO thelma;

--
-- TOC entry 5342 (class 0 OID 0)
-- Dependencies: 320
-- Name: molecule_design_set_molecule_design_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE molecule_design_set_molecule_design_set_id_seq OWNED BY molecule_design_set.molecule_design_set_id;


--
-- TOC entry 321 (class 1259 OID 16784027)
-- Name: molecule_design_set_target_set; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE molecule_design_set_target_set (
    molecule_design_set_id integer NOT NULL,
    target_set_id integer NOT NULL
);


ALTER TABLE public.molecule_design_set_target_set OWNER TO thelma;

--
-- TOC entry 5343 (class 0 OID 0)
-- Dependencies: 321
-- Name: TABLE molecule_design_set_target_set; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE molecule_design_set_target_set IS 'Links a molecule design set to one or several sets of targets.';


--
-- TOC entry 322 (class 1259 OID 16784030)
-- Name: molecule_design_structure; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE molecule_design_structure (
    molecule_design_id integer NOT NULL,
    chemical_structure_id integer NOT NULL
);


ALTER TABLE public.molecule_design_structure OWNER TO gathmann;

--
-- TOC entry 5345 (class 0 OID 0)
-- Dependencies: 322
-- Name: TABLE molecule_design_structure; Type: COMMENT; Schema: public; Owner: gathmann
--

COMMENT ON TABLE molecule_design_structure IS 'Maps molecule designs to their chemical structures.';


--
-- TOC entry 323 (class 1259 OID 16784033)
-- Name: molecule_molecule_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE molecule_molecule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.molecule_molecule_id_seq OWNER TO postgres;

--
-- TOC entry 5347 (class 0 OID 0)
-- Dependencies: 323
-- Name: molecule_molecule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE molecule_molecule_id_seq OWNED BY molecule.molecule_id;


--
-- TOC entry 324 (class 1259 OID 16784035)
-- Name: molecule_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE molecule_type (
    molecule_type_id character varying(10) NOT NULL,
    name character varying(20) NOT NULL,
    description text DEFAULT ''::text,
    thaw_time integer DEFAULT 0 NOT NULL,
    default_stock_concentration double precision NOT NULL,
    CONSTRAINT molecule_type_default_stock_concentration_check CHECK ((default_stock_concentration > (0)::double precision)),
    CONSTRAINT molecule_type_molecule_type_id_check CHECK ((char_length((molecule_type_id)::text) > 0)),
    CONSTRAINT molecule_type_name_check CHECK ((char_length((name)::text) > 0)),
    CONSTRAINT molecule_type_thaw_time_check CHECK ((thaw_time >= 0))
);


ALTER TABLE public.molecule_type OWNER TO postgres;

--
-- TOC entry 5349 (class 0 OID 0)
-- Dependencies: 324
-- Name: TABLE molecule_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE molecule_type IS 'Type of molecule';


--
-- TOC entry 5350 (class 0 OID 0)
-- Dependencies: 324
-- Name: COLUMN molecule_type.thaw_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN molecule_type.thaw_time IS 'Time (in seconds) samples containing molecules of this type can be
kept at room temperature before they thaw out (triggering an increase
in the freeze/thaw cycle counter).';


--
-- TOC entry 325 (class 1259 OID 16784047)
-- Name: molecule_type_modification_view; Type: VIEW; Schema: public; Owner: gathmann
--

CREATE VIEW molecule_type_modification_view AS
    SELECT DISTINCT md.molecule_type AS molecule_type_id, chs.representation AS name, chs.chemical_structure_id FROM ((molecule_design md JOIN molecule_design_structure mds ON ((mds.molecule_design_id = md.molecule_design_id))) JOIN chemical_structure chs ON (((chs.chemical_structure_id = mds.chemical_structure_id) AND ((chs.structure_type)::text = 'MODIFICATION'::text))));


ALTER TABLE public.molecule_type_modification_view OWNER TO gathmann;

--
-- TOC entry 326 (class 1259 OID 16784051)
-- Name: new_experiment; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE new_experiment (
    experiment_id integer NOT NULL,
    label character varying NOT NULL,
    experiment_design_id integer NOT NULL,
    job_id integer NOT NULL
);


ALTER TABLE public.new_experiment OWNER TO thelma;

--
-- TOC entry 5353 (class 0 OID 0)
-- Dependencies: 326
-- Name: TABLE new_experiment; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE new_experiment IS 'Replacement for the deprecated experiment table.';


--
-- TOC entry 327 (class 1259 OID 16784057)
-- Name: new_experiment_experiment_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE new_experiment_experiment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.new_experiment_experiment_id_seq OWNER TO thelma;

--
-- TOC entry 5355 (class 0 OID 0)
-- Dependencies: 327
-- Name: new_experiment_experiment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE new_experiment_experiment_id_seq OWNED BY new_experiment.experiment_id;


--
-- TOC entry 328 (class 1259 OID 16784059)
-- Name: new_experiment_rack; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE new_experiment_rack (
    experiment_rack_id integer NOT NULL,
    experiment_design_rack_id integer NOT NULL,
    experiment_id integer NOT NULL,
    rack_id integer NOT NULL
);


ALTER TABLE public.new_experiment_rack OWNER TO thelma;

--
-- TOC entry 5356 (class 0 OID 0)
-- Dependencies: 328
-- Name: TABLE new_experiment_rack; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE new_experiment_rack IS 'Replacement for the deprecated experiment_rack table.';


--
-- TOC entry 329 (class 1259 OID 16784062)
-- Name: new_experiment_rack_experiment_rack_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE new_experiment_rack_experiment_rack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.new_experiment_rack_experiment_rack_id_seq OWNER TO thelma;

--
-- TOC entry 5358 (class 0 OID 0)
-- Dependencies: 329
-- Name: new_experiment_rack_experiment_rack_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE new_experiment_rack_experiment_rack_id_seq OWNED BY new_experiment_rack.experiment_rack_id;


--
-- TOC entry 330 (class 1259 OID 16784064)
-- Name: new_file_storage_site_file_storage_site_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE new_file_storage_site_file_storage_site_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.new_file_storage_site_file_storage_site_id_seq OWNER TO postgres;

--
-- TOC entry 331 (class 1259 OID 16784066)
-- Name: new_job; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE new_job (
    job_id integer NOT NULL,
    job_type character varying(10) NOT NULL,
    label character varying(40) NOT NULL,
    user_id integer NOT NULL,
    creation_time timestamp with time zone NOT NULL,
    CONSTRAINT job_valid_type CHECK (((job_type)::text = ANY (ARRAY[('ISO'::character varying)::text, ('EXPERIMENT'::character varying)::text, ('BASE'::character varying)::text])))
);


ALTER TABLE public.new_job OWNER TO gathmann;

--
-- TOC entry 332 (class 1259 OID 16784070)
-- Name: new_job_job_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE new_job_job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.new_job_job_id_seq OWNER TO gathmann;

--
-- TOC entry 5360 (class 0 OID 0)
-- Dependencies: 332
-- Name: new_job_job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE new_job_job_id_seq OWNED BY new_job.job_id;


--
-- TOC entry 333 (class 1259 OID 16784072)
-- Name: new_sequence_sequence_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE new_sequence_sequence_id_seq
    START WITH 822275
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.new_sequence_sequence_id_seq OWNER TO postgres;

--
-- TOC entry 334 (class 1259 OID 16784074)
-- Name: order_sample_set; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE order_sample_set (
    sample_set_id integer NOT NULL,
    synthesis_date timestamp without time zone,
    external_order_id smallint NOT NULL,
    supplier_id integer NOT NULL
);


ALTER TABLE public.order_sample_set OWNER TO postgres;

--
-- TOC entry 5362 (class 0 OID 0)
-- Dependencies: 334
-- Name: TABLE order_sample_set; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE order_sample_set IS 'Set of samples in a delivery from a supplier.';


--
-- TOC entry 5363 (class 0 OID 0)
-- Dependencies: 334
-- Name: COLUMN order_sample_set.synthesis_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN order_sample_set.synthesis_date IS 'Date the samples were synthesized (optional)

We almost never know this.  Even if we do, there is no gurantee every sample
in the delivery was synthesized on the same date.  If we want to track this
information, it should go in a table associated with the sample.  Otherwise,
this column should be dropped.';


--
-- TOC entry 5364 (class 0 OID 0)
-- Dependencies: 334
-- Name: COLUMN order_sample_set.external_order_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN order_sample_set.external_order_id IS 'Sequence number of the delivery.

This is mostly used to autogenerate a label for the sampel set.  I don''t
think it is used for anything else anymore.  Probably should be dropped.';


--
-- TOC entry 5365 (class 0 OID 0)
-- Dependencies: 334
-- Name: COLUMN order_sample_set.supplier_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN order_sample_set.supplier_id IS 'ID of supplier of delivery.';


--
-- TOC entry 335 (class 1259 OID 16784077)
-- Name: organization_organization_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE organization_organization_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.organization_organization_id_seq OWNER TO postgres;

--
-- TOC entry 336 (class 1259 OID 16784079)
-- Name: organization; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE organization (
    organization_id integer DEFAULT nextval('organization_organization_id_seq'::regclass) NOT NULL,
    name character varying NOT NULL,
    CONSTRAINT name CHECK (((name)::text <> ''::text))
);


ALTER TABLE public.organization OWNER TO postgres;

--
-- TOC entry 5368 (class 0 OID 0)
-- Dependencies: 336
-- Name: TABLE organization; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE organization IS 'An external or internal organization with which Cenix does business

Organizations can be, e.g., customers, suppliers or equipment manufacturers.

Historically, we have dealt with relatively few organizations so it has not
been important to keep information such as addresses, contacts, etc.  It
might be important to keep such information in the future, but there is still
no such requirement.';


--
-- TOC entry 5369 (class 0 OID 0)
-- Dependencies: 336
-- Name: COLUMN organization.organization_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN organization.organization_id IS 'Surrogate primary key of the organization

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name as the primary key in its place.';


--
-- TOC entry 5370 (class 0 OID 0)
-- Dependencies: 336
-- Name: COLUMN organization.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN organization.name IS 'User-assigned name for the organization, intended for display';


--
-- TOC entry 337 (class 1259 OID 16784087)
-- Name: origin_type_origin_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE origin_type_origin_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.origin_type_origin_type_id_seq OWNER TO postgres;

--
-- TOC entry 338 (class 1259 OID 16784089)
-- Name: pipetting_specs; Type: TABLE; Schema: public; Owner: berger; Tablespace: 
--

CREATE TABLE pipetting_specs (
    pipetting_specs_id integer NOT NULL,
    name character varying(11) NOT NULL,
    min_transfer_volume double precision NOT NULL,
    max_transfer_volume double precision NOT NULL,
    max_dilution_factor integer NOT NULL,
    has_dynamic_dead_volume boolean NOT NULL,
    is_sector_bound boolean NOT NULL,
    CONSTRAINT pipetting_transfer_volume_max_larger_than_min CHECK ((max_transfer_volume > min_transfer_volume)),
    CONSTRAINT positive_pipettig_max_dilution_factor CHECK ((max_dilution_factor > 0)),
    CONSTRAINT positive_pipetting_max_transfer_volume CHECK ((max_transfer_volume > (0)::double precision)),
    CONSTRAINT positive_pipetting_min_transfer_volume CHECK ((min_transfer_volume > (0)::double precision))
);


ALTER TABLE public.pipetting_specs OWNER TO berger;

--
-- TOC entry 339 (class 1259 OID 16784096)
-- Name: pipetting_specs_pipetting_specs_id_seq; Type: SEQUENCE; Schema: public; Owner: berger
--

CREATE SEQUENCE pipetting_specs_pipetting_specs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pipetting_specs_pipetting_specs_id_seq OWNER TO berger;

--
-- TOC entry 5374 (class 0 OID 0)
-- Dependencies: 339
-- Name: pipetting_specs_pipetting_specs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: berger
--

ALTER SEQUENCE pipetting_specs_pipetting_specs_id_seq OWNED BY pipetting_specs.pipetting_specs_id;


--
-- TOC entry 340 (class 1259 OID 16784098)
-- Name: planned_liquid_transfer; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE planned_liquid_transfer (
    planned_liquid_transfer_id integer NOT NULL,
    volume double precision NOT NULL,
    transfer_type character varying(20) NOT NULL,
    hash_value character varying(32) NOT NULL,
    CONSTRAINT planned_liquid_transfer_positive_volume CHECK ((volume > (0)::double precision))
);


ALTER TABLE public.planned_liquid_transfer OWNER TO gathmann;

--
-- TOC entry 341 (class 1259 OID 16784102)
-- Name: planned_liquid_transfer_planned_liquid_transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE planned_liquid_transfer_planned_liquid_transfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.planned_liquid_transfer_planned_liquid_transfer_id_seq OWNER TO gathmann;

--
-- TOC entry 5376 (class 0 OID 0)
-- Dependencies: 341
-- Name: planned_liquid_transfer_planned_liquid_transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE planned_liquid_transfer_planned_liquid_transfer_id_seq OWNED BY planned_liquid_transfer.planned_liquid_transfer_id;


--
-- TOC entry 342 (class 1259 OID 16784104)
-- Name: planned_rack_sample_transfer; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE planned_rack_sample_transfer (
    planned_liquid_transfer_id integer NOT NULL,
    number_sectors integer NOT NULL,
    source_sector_index integer NOT NULL,
    target_sector_index integer NOT NULL,
    CONSTRAINT prst_number_sectors_greater_than_source_sector CHECK ((number_sectors > source_sector_index)),
    CONSTRAINT prst_number_sectors_greater_than_target_sector CHECK ((number_sectors > target_sector_index)),
    CONSTRAINT prst_positive_number_sectors CHECK ((number_sectors > 0)),
    CONSTRAINT prst_source_sector_index_non_negative CHECK ((source_sector_index >= 0)),
    CONSTRAINT prst_target_sector_index_non_negative CHECK ((target_sector_index >= 0))
);


ALTER TABLE public.planned_rack_sample_transfer OWNER TO gathmann;

--
-- TOC entry 343 (class 1259 OID 16784112)
-- Name: planned_sample_dilution; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE planned_sample_dilution (
    planned_liquid_transfer_id integer NOT NULL,
    diluent_info character varying(35) NOT NULL,
    target_position_id integer NOT NULL
);


ALTER TABLE public.planned_sample_dilution OWNER TO gathmann;

--
-- TOC entry 344 (class 1259 OID 16784115)
-- Name: planned_sample_transfer; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE planned_sample_transfer (
    planned_liquid_transfer_id integer NOT NULL,
    source_position_id integer NOT NULL,
    target_position_id integer NOT NULL
);


ALTER TABLE public.planned_sample_transfer OWNER TO gathmann;

--
-- TOC entry 345 (class 1259 OID 16784118)
-- Name: planned_worklist; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE planned_worklist (
    planned_worklist_id integer NOT NULL,
    label character varying NOT NULL,
    transfer_type character varying(20) NOT NULL,
    pipetting_specs_id integer NOT NULL
);


ALTER TABLE public.planned_worklist OWNER TO thelma;

--
-- TOC entry 346 (class 1259 OID 16784124)
-- Name: planned_worklist_member; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE planned_worklist_member (
    planned_worklist_id integer NOT NULL,
    planned_liquid_transfer_id integer NOT NULL
);


ALTER TABLE public.planned_worklist_member OWNER TO gathmann;

--
-- TOC entry 347 (class 1259 OID 16784127)
-- Name: planned_worklist_planned_worklist_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE planned_worklist_planned_worklist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.planned_worklist_planned_worklist_id_seq OWNER TO thelma;

--
-- TOC entry 5382 (class 0 OID 0)
-- Dependencies: 347
-- Name: planned_worklist_planned_worklist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE planned_worklist_planned_worklist_id_seq OWNED BY planned_worklist.planned_worklist_id;


--
-- TOC entry 348 (class 1259 OID 16784129)
-- Name: molecule_design_pool_set_molecule_design_pool_set_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE molecule_design_pool_set_molecule_design_pool_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.molecule_design_pool_set_molecule_design_pool_set_id_seq OWNER TO gathmann;

--
-- TOC entry 5383 (class 0 OID 0)
-- Dependencies: 348
-- Name: molecule_design_pool_set_molecule_design_pool_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE molecule_design_pool_set_molecule_design_pool_set_id_seq OWNED BY molecule_design_pool_set.molecule_design_pool_set_id;


--
-- TOC entry 349 (class 1259 OID 16784131)
-- Name: pooled_supplier_molecule_design; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE pooled_supplier_molecule_design (
    supplier_molecule_design_id integer NOT NULL,
    molecule_design_set_id integer NOT NULL
);


ALTER TABLE public.pooled_supplier_molecule_design OWNER TO gathmann;

--
-- TOC entry 350 (class 1259 OID 16784134)
-- Name: primer_pair_primer_pair_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE primer_pair_primer_pair_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.primer_pair_primer_pair_id_seq OWNER TO postgres;

--
-- TOC entry 351 (class 1259 OID 16784136)
-- Name: primer_pair; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE primer_pair (
    primer_pair_id integer DEFAULT nextval('primer_pair_primer_pair_id_seq'::regclass) NOT NULL,
    primer_1_id integer NOT NULL,
    primer_2_id integer NOT NULL,
    CONSTRAINT less_than CHECK ((primer_1_id <= primer_2_id))
);


ALTER TABLE public.primer_pair OWNER TO postgres;

--
-- TOC entry 5386 (class 0 OID 0)
-- Dependencies: 351
-- Name: TABLE primer_pair; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE primer_pair IS 'Pair of DNA oligos for PCR reaction.';


--
-- TOC entry 352 (class 1259 OID 16784141)
-- Name: species; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE species (
    species_id integer NOT NULL,
    genus_name character varying(25) NOT NULL,
    species_name character varying(25) NOT NULL,
    common_name character varying(25) NOT NULL,
    acronym character varying(2) NOT NULL,
    ncbi_tax_id smallint NOT NULL
);


ALTER TABLE public.species OWNER TO postgres;

--
-- TOC entry 5388 (class 0 OID 0)
-- Dependencies: 352
-- Name: TABLE species; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE species IS 'Species';


--
-- TOC entry 5389 (class 0 OID 0)
-- Dependencies: 352
-- Name: COLUMN species.ncbi_tax_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN species.ncbi_tax_id IS 'NCBI Taxonomy ID';


--
-- TOC entry 353 (class 1259 OID 16784144)
-- Name: transcript_transcript_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE transcript_transcript_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transcript_transcript_id_seq OWNER TO postgres;

--
-- TOC entry 354 (class 1259 OID 16784146)
-- Name: transcript; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE transcript (
    transcript_id integer DEFAULT nextval('transcript_transcript_id_seq'::regclass) NOT NULL,
    accession character varying(30) NOT NULL,
    species_id integer NOT NULL
);


ALTER TABLE public.transcript OWNER TO postgres;

--
-- TOC entry 5392 (class 0 OID 0)
-- Dependencies: 354
-- Name: TABLE transcript; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE transcript IS 'Transcript

Not necessarily mRNA, we store non-coding RNAs too.';


--
-- TOC entry 5393 (class 0 OID 0)
-- Dependencies: 354
-- Name: COLUMN transcript.accession; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN transcript.accession IS 'Unique accession assigned by annotation DB (e.g. NCBI Gene)';


--
-- TOC entry 355 (class 1259 OID 16784150)
-- Name: versioned_transcript_amplicon; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE versioned_transcript_amplicon (
    versioned_transcript_id integer NOT NULL,
    primer_pair_id integer NOT NULL,
    left_primer_start integer NOT NULL,
    right_primer_start integer NOT NULL
);


ALTER TABLE public.versioned_transcript_amplicon OWNER TO postgres;

--
-- TOC entry 5395 (class 0 OID 0)
-- Dependencies: 355
-- Name: TABLE versioned_transcript_amplicon; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE versioned_transcript_amplicon IS 'Stores PCR amplification product for primer pair using transcript as template.';


--
-- TOC entry 5396 (class 0 OID 0)
-- Dependencies: 355
-- Name: COLUMN versioned_transcript_amplicon.left_primer_start; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN versioned_transcript_amplicon.left_primer_start IS 'Position in transcript where 5p bp of left primer will hybidize to the negative strand of double-stranded template.';


--
-- TOC entry 5397 (class 0 OID 0)
-- Dependencies: 355
-- Name: COLUMN versioned_transcript_amplicon.right_primer_start; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN versioned_transcript_amplicon.right_primer_start IS 'Position in transcript where 5p bp of right primer will hybidize to the positive strand of double-stranded template.';


--
-- TOC entry 356 (class 1259 OID 16784153)
-- Name: primer_pair_target_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW primer_pair_target_view AS
    SELECT DISTINCT pp.primer_pair_id, svt.accession AS transcript_accession, srgt.species, srgt.gene_name, srgt.gene_accession FROM ((primer_pair pp LEFT JOIN (SELECT vta.primer_pair_id, t.accession, t.transcript_id FROM versioned_transcript_amplicon vta, versioned_transcript vt, transcript t WHERE ((vta.versioned_transcript_id = vt.versioned_transcript_id) AND (vt.transcript_id = t.transcript_id))) svt ON ((pp.primer_pair_id = svt.primer_pair_id))) LEFT JOIN (SELECT DISTINCT rgt.transcript_id, s.common_name AS species, g.locus_name AS gene_name, g.accession AS gene_accession FROM current_db_release cdr, release_gene_transcript rgt, (gene g LEFT JOIN species s ON ((s.species_id = g.species_id))) WHERE ((cdr.db_release_id = rgt.db_release_id) AND (rgt.gene_id = g.gene_id)) ORDER BY rgt.transcript_id, s.common_name, g.locus_name, g.accession) srgt ON ((svt.transcript_id = srgt.transcript_id))) ORDER BY pp.primer_pair_id, svt.accession, srgt.species, srgt.gene_name, srgt.gene_accession;


ALTER TABLE public.primer_pair_target_view OWNER TO postgres;

--
-- TOC entry 5399 (class 0 OID 0)
-- Dependencies: 356
-- Name: VIEW primer_pair_target_view; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW primer_pair_target_view IS 'Displays target info of primer pairs';


--
-- TOC entry 357 (class 1259 OID 16784158)
-- Name: primer_validation; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE primer_validation (
    primer_pair_id integer NOT NULL,
    cell_line_id integer NOT NULL,
    result validation_result NOT NULL,
    db_user_id integer NOT NULL,
    project_id integer NOT NULL
);


ALTER TABLE public.primer_validation OWNER TO postgres;

--
-- TOC entry 5401 (class 0 OID 0)
-- Dependencies: 357
-- Name: TABLE primer_validation; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE primer_validation IS 'validation data for primer pairs';


--
-- TOC entry 5402 (class 0 OID 0)
-- Dependencies: 357
-- Name: COLUMN primer_validation.primer_pair_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN primer_validation.primer_pair_id IS 'tested primer pair';


--
-- TOC entry 5403 (class 0 OID 0)
-- Dependencies: 357
-- Name: COLUMN primer_validation.cell_line_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN primer_validation.cell_line_id IS 'ID of cell_line

This is the cell_line the validation experiment was conducted on';


--
-- TOC entry 5404 (class 0 OID 0)
-- Dependencies: 357
-- Name: COLUMN primer_validation.result; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN primer_validation.result IS 'result of validation test';


--
-- TOC entry 5405 (class 0 OID 0)
-- Dependencies: 357
-- Name: COLUMN primer_validation.db_user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN primer_validation.db_user_id IS 'user who submitted the validation data';


--
-- TOC entry 5406 (class 0 OID 0)
-- Dependencies: 357
-- Name: COLUMN primer_validation.project_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN primer_validation.project_id IS 'The sequential project_id used to identify a given project in the project
table';


--
-- TOC entry 358 (class 1259 OID 16784164)
-- Name: printer; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE printer (
    device_id integer NOT NULL,
    queue_name character varying NOT NULL,
    CONSTRAINT queue_name CHECK ((((queue_name)::text ~ similar_escape('[a-z0-9\_-]+'::text, NULL::text)) AND (char_length((queue_name)::text) <= 127)))
);


ALTER TABLE public.printer OWNER TO postgres;

--
-- TOC entry 5408 (class 0 OID 0)
-- Dependencies: 358
-- Name: TABLE printer; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE printer IS 'Additional information needed for devices that are printers.';


--
-- TOC entry 5409 (class 0 OID 0)
-- Dependencies: 358
-- Name: COLUMN printer.queue_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN printer.queue_name IS 'Name of Unix lpr printer queue';


--
-- TOC entry 359 (class 1259 OID 16784171)
-- Name: project; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE project (
    project_id integer NOT NULL,
    customer_id integer NOT NULL,
    label character varying(64) NOT NULL,
    creation_date timestamp with time zone NOT NULL,
    project_leader_id integer NOT NULL
);


ALTER TABLE public.project OWNER TO postgres;

--
-- TOC entry 5411 (class 0 OID 0)
-- Dependencies: 359
-- Name: TABLE project; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE project IS 'A scientific project';


--
-- TOC entry 5412 (class 0 OID 0)
-- Dependencies: 359
-- Name: COLUMN project.project_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN project.project_id IS 'Surrogate primary key of the project

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
label as the primary key in its place.';


--
-- TOC entry 5413 (class 0 OID 0)
-- Dependencies: 359
-- Name: COLUMN project.customer_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN project.customer_id IS 'ID of organization who comissioned the project.';


--
-- TOC entry 5414 (class 0 OID 0)
-- Dependencies: 359
-- Name: COLUMN project.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN project.label IS 'User-assigned name for the project, intended for display';


--
-- TOC entry 5415 (class 0 OID 0)
-- Dependencies: 359
-- Name: COLUMN project.creation_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN project.creation_date IS 'Date the project was created.

New insertions should use the default value.';


--
-- TOC entry 5416 (class 0 OID 0)
-- Dependencies: 359
-- Name: COLUMN project.project_leader_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN project.project_leader_id IS 'ID of user who is responsible for the project as a whole.';


--
-- TOC entry 360 (class 1259 OID 16784174)
-- Name: project_project_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE project_project_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.project_project_id_seq OWNER TO postgres;

--
-- TOC entry 5418 (class 0 OID 0)
-- Dependencies: 360
-- Name: project_project_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE project_project_id_seq OWNED BY project.project_id;


--
-- TOC entry 361 (class 1259 OID 16784176)
-- Name: rack_barcoded_location; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_barcoded_location (
    rack_id integer NOT NULL,
    barcoded_location_id integer NOT NULL,
    checkin_date timestamp without time zone NOT NULL
);


ALTER TABLE public.rack_barcoded_location OWNER TO postgres;

--
-- TOC entry 5420 (class 0 OID 0)
-- Dependencies: 361
-- Name: TABLE rack_barcoded_location; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_barcoded_location IS 'Association of a rack with its holding location';


--
-- TOC entry 5421 (class 0 OID 0)
-- Dependencies: 361
-- Name: COLUMN rack_barcoded_location.checkin_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_barcoded_location.checkin_date IS 'Time the rack was checked in to the location';


--
-- TOC entry 362 (class 1259 OID 16784179)
-- Name: rack_barcoded_location_log; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_barcoded_location_log (
    rack_id integer NOT NULL,
    barcoded_location_id integer,
    date timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.rack_barcoded_location_log OWNER TO postgres;

--
-- TOC entry 5423 (class 0 OID 0)
-- Dependencies: 362
-- Name: TABLE rack_barcoded_location_log; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_barcoded_location_log IS 'The barcoded location log table records all barcoded location changes for
all racks (i.e., each individual check-in and check-out event).
This table is going to grow over time; while it is unlikely that this will
ever cause performance problems, we could consider cutting off the log
in certain intervals.';


--
-- TOC entry 363 (class 1259 OID 16784183)
-- Name: rack_info; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW rack_info AS
    SELECT r.rack_id, r.rack_specs_id, r.item_status, r.barcode, r.creation_date, rbl.barcoded_location_id, rbl.checkin_date, r.label, r.comment FROM (rack r LEFT JOIN rack_barcoded_location rbl ON ((r.rack_id = rbl.rack_id)));


ALTER TABLE public.rack_info OWNER TO postgres;

--
-- TOC entry 5425 (class 0 OID 0)
-- Dependencies: 363
-- Name: VIEW rack_info; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW rack_info IS 'Convenient access to information for checked in racks.

DEPRECATED

This is no longer used by CeLMA and should probably be dropped.';


--
-- TOC entry 364 (class 1259 OID 16784187)
-- Name: rack_layout; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE rack_layout (
    rack_layout_id integer NOT NULL,
    rack_shape_name character varying NOT NULL
);


ALTER TABLE public.rack_layout OWNER TO thelma;

--
-- TOC entry 5427 (class 0 OID 0)
-- Dependencies: 364
-- Name: TABLE rack_layout; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE rack_layout IS 'One or more tagged position sets on a rack of a given shape.';


--
-- TOC entry 365 (class 1259 OID 16784193)
-- Name: rack_layout_rack_layout_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE rack_layout_rack_layout_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rack_layout_rack_layout_id_seq OWNER TO thelma;

--
-- TOC entry 5429 (class 0 OID 0)
-- Dependencies: 365
-- Name: rack_layout_rack_layout_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE rack_layout_rack_layout_id_seq OWNED BY rack_layout.rack_layout_id;


--
-- TOC entry 366 (class 1259 OID 16784195)
-- Name: rack_mask; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_mask (
    number_rows integer NOT NULL,
    number_columns integer NOT NULL,
    name pg_catalog.name NOT NULL,
    label character varying NOT NULL,
    description character varying DEFAULT ''::character varying NOT NULL,
    rack_mask_id integer DEFAULT nextval(('rack_mask_rack_mask_id_seq'::text)::regclass) NOT NULL,
    CONSTRAINT carrier_mask_number_columns CHECK ((number_columns > 0)),
    CONSTRAINT carrier_mask_number_rows CHECK ((number_rows > 0))
);


ALTER TABLE public.rack_mask OWNER TO postgres;

--
-- TOC entry 5430 (class 0 OID 0)
-- Dependencies: 366
-- Name: TABLE rack_mask; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_mask IS 'Rack mask

A rack mask indicates which containers may be accessed for some purpose.  For
example, an internal sample order may fill only positions which are in the
mask.';


--
-- TOC entry 5431 (class 0 OID 0)
-- Dependencies: 366
-- Name: COLUMN rack_mask.number_rows; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask.number_rows IS 'Number of rows in the mask';


--
-- TOC entry 5432 (class 0 OID 0)
-- Dependencies: 366
-- Name: COLUMN rack_mask.number_columns; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask.number_columns IS 'Number of columns in the mask';


--
-- TOC entry 5433 (class 0 OID 0)
-- Dependencies: 366
-- Name: COLUMN rack_mask.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask.name IS 'User-assigned name for the rack mask, intended for programatic purposes

Programs should not rely on specific database contents and thus this column
has little value.  Probably should be dropped.';


--
-- TOC entry 5434 (class 0 OID 0)
-- Dependencies: 366
-- Name: COLUMN rack_mask.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask.label IS 'User-assigned name for the rack mask, intended for display';


--
-- TOC entry 5435 (class 0 OID 0)
-- Dependencies: 366
-- Name: COLUMN rack_mask.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask.description IS 'Space for comments.';


--
-- TOC entry 5436 (class 0 OID 0)
-- Dependencies: 366
-- Name: COLUMN rack_mask.rack_mask_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask.rack_mask_id IS 'Surrogate primary key of the rack mask

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.

WARNING: there is no constraint to ensure that row and col are in range for
number_rows and number_columns of the parent rack_mask.';


--
-- TOC entry 367 (class 1259 OID 16784205)
-- Name: rack_mask_position; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_mask_position (
    rack_mask_id integer NOT NULL,
    col integer NOT NULL,
    "row" integer NOT NULL,
    CONSTRAINT carrier_mask_position_col CHECK ((col >= 0)),
    CONSTRAINT carrier_mask_position_numeric_row CHECK (("row" >= 0))
);


ALTER TABLE public.rack_mask_position OWNER TO postgres;

--
-- TOC entry 5438 (class 0 OID 0)
-- Dependencies: 367
-- Name: TABLE rack_mask_position; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_mask_position IS 'Position in a rack mask

Positions appearing in this table are considered permitted by the mask.';


--
-- TOC entry 5439 (class 0 OID 0)
-- Dependencies: 367
-- Name: COLUMN rack_mask_position.col; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask_position.col IS 'Zero-based column index starting from the left of the rack mask';


--
-- TOC entry 5440 (class 0 OID 0)
-- Dependencies: 367
-- Name: COLUMN rack_mask_position."row"; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rack_mask_position."row" IS 'Zero-based row index starting from the top of the rack mask';


--
-- TOC entry 368 (class 1259 OID 16784210)
-- Name: rack_mask_rack_mask_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE rack_mask_rack_mask_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rack_mask_rack_mask_id_seq OWNER TO postgres;

--
-- TOC entry 369 (class 1259 OID 16784212)
-- Name: rack_position; Type: TABLE; Schema: public; Owner: berger; Tablespace: 
--

CREATE TABLE rack_position (
    rack_position_id integer NOT NULL,
    row_index integer NOT NULL,
    column_index integer NOT NULL,
    label character varying(4) NOT NULL,
    CONSTRAINT non_negative_rack_position_column_index CHECK ((column_index >= 0)),
    CONSTRAINT non_negative_rack_position_row_index CHECK ((row_index >= 0))
);


ALTER TABLE public.rack_position OWNER TO berger;

--
-- TOC entry 370 (class 1259 OID 16784217)
-- Name: rack_position_block; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_position_block (
    rack_position_block_id integer NOT NULL,
    row_begin integer NOT NULL,
    row_end integer NOT NULL,
    column_begin integer NOT NULL,
    column_end integer NOT NULL,
    CONSTRAINT rack_position_block_check CHECK ((row_end >= row_begin)),
    CONSTRAINT rack_position_block_check1 CHECK ((column_end >= column_begin)),
    CONSTRAINT rack_position_block_column_begin_check CHECK ((column_begin >= 0)),
    CONSTRAINT rack_position_block_row_begin_check CHECK ((row_begin >= 0))
);


ALTER TABLE public.rack_position_block OWNER TO postgres;

--
-- TOC entry 5444 (class 0 OID 0)
-- Dependencies: 370
-- Name: TABLE rack_position_block; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_position_block IS 'A rack position block represents a rectangular block of positions on a rack.
The block is specified by its top left and the bottom right corner position
(very much like a block of cells in Excel). A single cell is represented as a
block starting and ending in itself. Each block is kept in the table only once.';


--
-- TOC entry 371 (class 1259 OID 16784224)
-- Name: rack_position_block_rack_position_block_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE rack_position_block_rack_position_block_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rack_position_block_rack_position_block_id_seq OWNER TO postgres;

--
-- TOC entry 5446 (class 0 OID 0)
-- Dependencies: 371
-- Name: rack_position_block_rack_position_block_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE rack_position_block_rack_position_block_id_seq OWNED BY rack_position_block.rack_position_block_id;


--
-- TOC entry 372 (class 1259 OID 16784226)
-- Name: rack_position_rack_position_id_seq; Type: SEQUENCE; Schema: public; Owner: berger
--

CREATE SEQUENCE rack_position_rack_position_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rack_position_rack_position_id_seq OWNER TO berger;

--
-- TOC entry 5448 (class 0 OID 0)
-- Dependencies: 372
-- Name: rack_position_rack_position_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: berger
--

ALTER SEQUENCE rack_position_rack_position_id_seq OWNED BY rack_position.rack_position_id;


--
-- TOC entry 373 (class 1259 OID 16784228)
-- Name: rack_position_set; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE rack_position_set (
    rack_position_set_id integer NOT NULL,
    hash_value character varying NOT NULL
);


ALTER TABLE public.rack_position_set OWNER TO thelma;

--
-- TOC entry 5449 (class 0 OID 0)
-- Dependencies: 373
-- Name: TABLE rack_position_set; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE rack_position_set IS 'Set of grid positions.';


--
-- TOC entry 374 (class 1259 OID 16784234)
-- Name: rack_position_set_member; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE rack_position_set_member (
    rack_position_set_id integer NOT NULL,
    rack_position_id integer NOT NULL
);


ALTER TABLE public.rack_position_set_member OWNER TO thelma;

--
-- TOC entry 5451 (class 0 OID 0)
-- Dependencies: 374
-- Name: TABLE rack_position_set_member; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE rack_position_set_member IS 'Member of a grid position set.';


--
-- TOC entry 375 (class 1259 OID 16784237)
-- Name: rack_position_set_rack_position_set_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE rack_position_set_rack_position_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rack_position_set_rack_position_set_id_seq OWNER TO thelma;

--
-- TOC entry 5453 (class 0 OID 0)
-- Dependencies: 375
-- Name: rack_position_set_rack_position_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE rack_position_set_rack_position_set_id_seq OWNED BY rack_position_set.rack_position_set_id;


--
-- TOC entry 376 (class 1259 OID 16784239)
-- Name: rack_rack_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE rack_rack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rack_rack_id_seq OWNER TO postgres;

--
-- TOC entry 377 (class 1259 OID 16784241)
-- Name: rack_shape; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_shape (
    rack_shape_name character varying NOT NULL,
    number_rows integer NOT NULL,
    number_columns integer NOT NULL,
    label character varying NOT NULL,
    CONSTRAINT rack_shape_number_columns_check CHECK ((number_columns > 0)),
    CONSTRAINT rack_shape_number_rows_check CHECK ((number_rows > 0))
);


ALTER TABLE public.rack_shape OWNER TO postgres;

--
-- TOC entry 5455 (class 0 OID 0)
-- Dependencies: 377
-- Name: TABLE rack_shape; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_shape IS 'A rack shape has a name and represents the rectangular grid of
rows and columns in a rack.

Each rack shape is kept in the table only once.';


--
-- TOC entry 378 (class 1259 OID 16784249)
-- Name: rack_specs_container_specs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rack_specs_container_specs (
    rack_specs_id integer NOT NULL,
    container_specs_id integer NOT NULL
);


ALTER TABLE public.rack_specs_container_specs OWNER TO postgres;

--
-- TOC entry 5457 (class 0 OID 0)
-- Dependencies: 378
-- Name: TABLE rack_specs_container_specs; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rack_specs_container_specs IS 'Compatibility of rack type and container type

If a pair of rack_specs_id and container_specs_id appears in this table, than
the given types are compatibile.  No container should appear in a rack which
is not marked as compatible through this table.

WARNING: there is no constraint to enforce that this rule is observed.';


--
-- TOC entry 379 (class 1259 OID 16784252)
-- Name: rack_specs_rack_specs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE rack_specs_rack_specs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rack_specs_rack_specs_id_seq OWNER TO postgres;

--
-- TOC entry 380 (class 1259 OID 16784254)
-- Name: racked_tube; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW racked_tube AS
    SELECT cs.name AS container_specs_name, c.item_status, cb.barcode AS container_barcode, r.barcode AS rack_barcode, cm."row", cm.col FROM rack r, containment cm, container c, container_barcode cb, container_specs cs WHERE ((((r.rack_id = cm.holder_id) AND (cm.held_id = c.container_id)) AND (c.container_id = cb.container_id)) AND (c.container_specs_id = cs.container_specs_id));


ALTER TABLE public.racked_tube OWNER TO postgres;

--
-- TOC entry 5460 (class 0 OID 0)
-- Dependencies: 380
-- Name: VIEW racked_tube; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW racked_tube IS 'View of tubes held in racks.  Supports insert.';


--
-- TOC entry 381 (class 1259 OID 16784258)
-- Name: sample; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sample (
    sample_id integer NOT NULL,
    container_id integer NOT NULL,
    volume double precision,
    sample_type character varying(10) DEFAULT 'BASIC'::character varying NOT NULL,
    CONSTRAINT sample_volume_non_negative CHECK ((volume >= (0.0)::double precision))
);


ALTER TABLE public.sample OWNER TO postgres;

--
-- TOC entry 5462 (class 0 OID 0)
-- Dependencies: 381
-- Name: TABLE sample; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE sample IS 'A sample of liquid in a container';


--
-- TOC entry 5463 (class 0 OID 0)
-- Dependencies: 381
-- Name: COLUMN sample.sample_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample.sample_id IS 'Surrogate primary key of the sample

Internal ID.  Do not publish.

Currently a sample is always held by a container.  As such, this column is
strictly redundant because the container_id is a candidate key.  I chose to
add this surrogate key so that tables which are associated with samples would
not be affected if samples were no longer required to be in containers.  Such
a change was under consideration at the time.  I''m not sure the distinction
is of useful anymore.  Certainly, the existance of this column adds an extra
join to some queries.';


--
-- TOC entry 5464 (class 0 OID 0)
-- Dependencies: 381
-- Name: COLUMN sample.container_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample.container_id IS 'Container holding the sample';


--
-- TOC entry 5465 (class 0 OID 0)
-- Dependencies: 381
-- Name: COLUMN sample.volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample.volume IS 'Volume of liquid, in liters (optional)

A NULL in this column indicates that the volume is unknown.

NULLs are allowed because we have not always tracked volumes and legacy data
had to be accomodated.  New inserts should never use NULLs here.';


--
-- TOC entry 382 (class 1259 OID 16784263)
-- Name: racked_sample; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW racked_sample AS
    SELECT rt.container_specs_name, rt.item_status, rt.container_barcode, rt.rack_barcode, rt."row", rt.col, s.volume FROM racked_tube rt, container_barcode cb, sample s WHERE (((rt.container_barcode)::text = (cb.barcode)::text) AND (cb.container_id = s.container_id));


ALTER TABLE public.racked_sample OWNER TO postgres;

--
-- TOC entry 5467 (class 0 OID 0)
-- Dependencies: 382
-- Name: VIEW racked_sample; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW racked_sample IS 'View of samples held in racked tubes.  Supports insert.';


--
-- TOC entry 383 (class 1259 OID 16784267)
-- Name: sample_molecule; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sample_molecule (
    sample_id integer NOT NULL,
    molecule_id integer NOT NULL,
    concentration double precision,
    freeze_thaw_cycles integer,
    checkout_date timestamp without time zone,
    CONSTRAINT sample_molecule_concentration CHECK ((concentration >= (0.0)::double precision)),
    CONSTRAINT sample_molecule_freeze_thaw_cycles_check CHECK (((freeze_thaw_cycles IS NULL) OR (freeze_thaw_cycles >= 0)))
);


ALTER TABLE public.sample_molecule OWNER TO postgres;

--
-- TOC entry 5469 (class 0 OID 0)
-- Dependencies: 383
-- Name: TABLE sample_molecule; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE sample_molecule IS 'Molecules in a sample';


--
-- TOC entry 5470 (class 0 OID 0)
-- Dependencies: 383
-- Name: COLUMN sample_molecule.concentration; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample_molecule.concentration IS 'concentration (moles per liter)';


--
-- TOC entry 5471 (class 0 OID 0)
-- Dependencies: 383
-- Name: COLUMN sample_molecule.freeze_thaw_cycles; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample_molecule.freeze_thaw_cycles IS 'The freeze/thaw cycles of a sample molecule indicate how often it has been
thawed out and frozen again. The number of freeze/thaw cycles can
affect the stability of a molecule dramatically. A value of NULL indicates
that freeze/thaw cycles are not being tracked for the give sample molecule.';


--
-- TOC entry 5472 (class 0 OID 0)
-- Dependencies: 383
-- Name: COLUMN sample_molecule.checkout_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample_molecule.checkout_date IS 'Records the time this sample molecule was last checked out of the stock.
Will be NULL if the sample molecule is currently in a rack that is checked
into the stock';


--
-- TOC entry 5473 (class 0 OID 0)
-- Dependencies: 383
-- Name: CONSTRAINT sample_molecule_concentration ON sample_molecule; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT sample_molecule_concentration ON sample_molecule IS 'Currently a concentration of 0.0 is permitted.  This seems wrong.  If
the concentration is zero there should not be any record.';


--
-- TOC entry 384 (class 1259 OID 16784272)
-- Name: racked_molecule_sample; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW racked_molecule_sample AS
    SELECT rs.container_specs_name, rs.item_status, rs.container_barcode, rs.rack_barcode, rs."row", rs.col, rs.volume, m.molecule_design_id, sm.concentration FROM racked_sample rs, container_barcode cb, sample s, sample_molecule sm, molecule m, molecule_design md WHERE ((((((rs.container_barcode)::text = (cb.barcode)::text) AND (cb.container_id = s.container_id)) AND (s.sample_id = sm.sample_id)) AND (sm.molecule_id = m.molecule_id)) AND (m.molecule_design_id = md.molecule_design_id));


ALTER TABLE public.racked_molecule_sample OWNER TO postgres;

--
-- TOC entry 5475 (class 0 OID 0)
-- Dependencies: 384
-- Name: VIEW racked_molecule_sample; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW racked_molecule_sample IS 'View of samples held in racked tubes containing molecules.  Supports insert.';


--
-- TOC entry 385 (class 1259 OID 16784276)
-- Name: readout_task_item; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE readout_task_item (
    file_set_id integer NOT NULL,
    task_item_id integer NOT NULL
);


ALTER TABLE public.readout_task_item OWNER TO postgres;

--
-- TOC entry 5477 (class 0 OID 0)
-- Dependencies: 385
-- Name: TABLE readout_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE readout_task_item IS 'Additional information for completed readout task items.

DEPRECATED.

This has never been used and should probably be dropped.';


--
-- TOC entry 5478 (class 0 OID 0)
-- Dependencies: 385
-- Name: COLUMN readout_task_item.file_set_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN readout_task_item.file_set_id IS 'ID of file set containing all images analysed for this task item.';


--
-- TOC entry 386 (class 1259 OID 16784279)
-- Name: readout_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE readout_type (
    readout_type_id integer NOT NULL,
    name pg_catalog.name NOT NULL,
    label character varying NOT NULL
);


ALTER TABLE public.readout_type OWNER TO postgres;

--
-- TOC entry 5480 (class 0 OID 0)
-- Dependencies: 386
-- Name: TABLE readout_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE readout_type IS 'Type of readout.

DEPRECATED.

Not referenced from any tables and no longer used by CeLMA.
Probably should be dropped.';


--
-- TOC entry 5481 (class 0 OID 0)
-- Dependencies: 386
-- Name: COLUMN readout_type.readout_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN readout_type.readout_type_id IS 'Surrogate primary key of the readout type

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.';


--
-- TOC entry 5482 (class 0 OID 0)
-- Dependencies: 386
-- Name: COLUMN readout_type.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN readout_type.name IS 'User-assigned name for the readout type, intended for programatic purposes

Programs should not rely on the presence of particular job types.  If programs
must rely on this, replace the table with a domain.  Otherwise this column
should probably be dropped.';


--
-- TOC entry 5483 (class 0 OID 0)
-- Dependencies: 386
-- Name: COLUMN readout_type.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN readout_type.label IS 'User-assigned name for the readout type, intended for display';


--
-- TOC entry 387 (class 1259 OID 16784285)
-- Name: readout_type_readout_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE readout_type_readout_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.readout_type_readout_type_id_seq OWNER TO postgres;

--
-- TOC entry 5485 (class 0 OID 0)
-- Dependencies: 387
-- Name: readout_type_readout_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE readout_type_readout_type_id_seq OWNED BY readout_type.readout_type_id;


--
-- TOC entry 388 (class 1259 OID 16784287)
-- Name: rearrayed_containers; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rearrayed_containers (
    source_container_id integer NOT NULL,
    destination_container_id integer NOT NULL,
    destination_sample_set_id integer NOT NULL,
    transfer_volume double precision,
    CONSTRAINT rearrayed_containers_transfer_volume_positive CHECK ((transfer_volume > (0.0)::double precision))
);


ALTER TABLE public.rearrayed_containers OWNER TO postgres;

--
-- TOC entry 5487 (class 0 OID 0)
-- Dependencies: 388
-- Name: TABLE rearrayed_containers; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rearrayed_containers IS 'Record a transfer of liquid from one container to another.

The use of a sample set to indirectly associate this table to a job is
highly problematic.  These records should be associated with a task item
instead, but it is probably impossible to reconstruct such associations for
legacy data.';


--
-- TOC entry 5488 (class 0 OID 0)
-- Dependencies: 388
-- Name: COLUMN rearrayed_containers.source_container_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rearrayed_containers.source_container_id IS 'ID of container from which liquid was aspirated';


--
-- TOC entry 5489 (class 0 OID 0)
-- Dependencies: 388
-- Name: COLUMN rearrayed_containers.destination_container_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rearrayed_containers.destination_container_id IS 'ID of contaienr into which liquid was dispensed';


--
-- TOC entry 5490 (class 0 OID 0)
-- Dependencies: 388
-- Name: COLUMN rearrayed_containers.destination_sample_set_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rearrayed_containers.destination_sample_set_id IS 'ID of sample set associated with the job in which this liquid transfer
occured.';


--
-- TOC entry 5491 (class 0 OID 0)
-- Dependencies: 388
-- Name: COLUMN rearrayed_containers.transfer_volume; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rearrayed_containers.transfer_volume IS 'Volume of liquid transferred, in liters';


--
-- TOC entry 389 (class 1259 OID 16784291)
-- Name: refseq_gene; Type: TABLE; Schema: public; Owner: berger; Tablespace: 
--

CREATE TABLE refseq_gene (
    gene_id integer NOT NULL,
    accession character varying(32) NOT NULL,
    locus_name character varying(40) NOT NULL,
    species_id integer NOT NULL
);


ALTER TABLE public.refseq_gene OWNER TO berger;

--
-- TOC entry 390 (class 1259 OID 16784294)
-- Name: refseq_gene_view; Type: VIEW; Schema: public; Owner: thelma
--

CREATE VIEW refseq_gene_view AS
    SELECT DISTINCT g.gene_id, g.accession, g.locus_name, g.species_id FROM (((gene g JOIN release_gene_transcript rgt ON (((rgt.gene_id = g.gene_id) AND (rgt.species_id = g.species_id)))) JOIN current_db_release cdr ON ((cdr.db_release_id = rgt.db_release_id))) JOIN db_source ds ON ((ds.db_source_id = cdr.db_source_id))) WHERE ((ds.db_name)::text = 'RefSeq'::text);


ALTER TABLE public.refseq_gene_view OWNER TO thelma;

--
-- TOC entry 391 (class 1259 OID 16784299)
-- Name: refseq_update_species; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE refseq_update_species (
    species_id integer NOT NULL
);


ALTER TABLE public.refseq_update_species OWNER TO postgres;

--
-- TOC entry 5495 (class 0 OID 0)
-- Dependencies: 391
-- Name: TABLE refseq_update_species; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE refseq_update_species IS 'Species which are to be part of regular RefSeq updates.';


--
-- TOC entry 392 (class 1259 OID 16784302)
-- Name: release_gene; Type: TABLE; Schema: public; Owner: walsh; Tablespace: 
--

CREATE TABLE release_gene (
    release_gene_id integer NOT NULL,
    db_release_id integer NOT NULL,
    gene_id integer NOT NULL
);


ALTER TABLE public.release_gene OWNER TO walsh;

--
-- TOC entry 5497 (class 0 OID 0)
-- Dependencies: 392
-- Name: TABLE release_gene; Type: COMMENT; Schema: public; Owner: walsh
--

COMMENT ON TABLE release_gene IS 'Association between gene and annotation DB release.';


--
-- TOC entry 393 (class 1259 OID 16784305)
-- Name: release_gene2annotation_release_gene2annotation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE release_gene2annotation_release_gene2annotation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.release_gene2annotation_release_gene2annotation_id_seq OWNER TO postgres;

--
-- TOC entry 394 (class 1259 OID 16784307)
-- Name: release_gene2annotation; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE release_gene2annotation (
    release_gene2annotation_id integer DEFAULT nextval('release_gene2annotation_release_gene2annotation_id_seq'::regclass) NOT NULL,
    db_release_id integer NOT NULL,
    gene2annotation_id integer NOT NULL
);


ALTER TABLE public.release_gene2annotation OWNER TO postgres;

--
-- TOC entry 5500 (class 0 OID 0)
-- Dependencies: 394
-- Name: TABLE release_gene2annotation; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE release_gene2annotation IS 'Association between gene and annotation based on specific annotation
DB release.';


--
-- TOC entry 395 (class 1259 OID 16784311)
-- Name: release_gene_release_gene_id_seq; Type: SEQUENCE; Schema: public; Owner: walsh
--

CREATE SEQUENCE release_gene_release_gene_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.release_gene_release_gene_id_seq OWNER TO walsh;

--
-- TOC entry 5502 (class 0 OID 0)
-- Dependencies: 395
-- Name: release_gene_release_gene_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: walsh
--

ALTER SEQUENCE release_gene_release_gene_id_seq OWNED BY release_gene.release_gene_id;


--
-- TOC entry 396 (class 1259 OID 16784313)
-- Name: release_sirna_transcript_target_release_sirna_transcript_target; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE release_sirna_transcript_target_release_sirna_transcript_target
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.release_sirna_transcript_target_release_sirna_transcript_target OWNER TO postgres;

--
-- TOC entry 397 (class 1259 OID 16784315)
-- Name: replaced_gene; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE replaced_gene (
    replaced_gene_id integer NOT NULL,
    replacement_gene_id integer NOT NULL,
    db_release_id integer NOT NULL
);


ALTER TABLE public.replaced_gene OWNER TO postgres;

--
-- TOC entry 5505 (class 0 OID 0)
-- Dependencies: 397
-- Name: TABLE replaced_gene; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE replaced_gene IS 'Association between an obsolete gene and its replacement based on
specific annotation DB release.

NCBI often collapses genes or replaces predicted genes with annotated.';


--
-- TOC entry 398 (class 1259 OID 16784318)
-- Name: replaced_transcript; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE replaced_transcript (
    replaced_transcript_id integer NOT NULL,
    replacement_transcript_id integer NOT NULL,
    db_release_id integer NOT NULL
);


ALTER TABLE public.replaced_transcript OWNER TO postgres;

--
-- TOC entry 5507 (class 0 OID 0)
-- Dependencies: 398
-- Name: TABLE replaced_transcript; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE replaced_transcript IS 'Association between an obsolete transcript and its replacement based on
specific annotation DB release.

NCBI often replaces predicted transcripts (XM) with annotated (NM).';


--
-- TOC entry 399 (class 1259 OID 16784321)
-- Name: reservoir_specs; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE reservoir_specs (
    reservoir_specs_id integer NOT NULL,
    description character varying NOT NULL,
    rack_shape_name character varying(5) NOT NULL,
    max_volume double precision NOT NULL,
    min_dead_volume double precision NOT NULL,
    max_dead_volume double precision NOT NULL,
    name character varying(15) NOT NULL,
    CONSTRAINT max_dead_volume_greater_or_equal_min_dead_volume CHECK ((max_dead_volume >= min_dead_volume)),
    CONSTRAINT max_dead_volume_greater_zero CHECK ((max_dead_volume > (0)::double precision)),
    CONSTRAINT max_volume_greater_max_dead_volume CHECK ((max_volume > max_dead_volume)),
    CONSTRAINT max_volume_greater_zero CHECK ((max_volume > (0)::double precision)),
    CONSTRAINT min_dead_volume_greater_zero CHECK ((min_dead_volume > (0)::double precision))
);


ALTER TABLE public.reservoir_specs OWNER TO thelma;

--
-- TOC entry 400 (class 1259 OID 16784332)
-- Name: reservoir_specs_reservoir_specs_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE reservoir_specs_reservoir_specs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reservoir_specs_reservoir_specs_id_seq OWNER TO thelma;

--
-- TOC entry 5510 (class 0 OID 0)
-- Dependencies: 400
-- Name: reservoir_specs_reservoir_specs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE reservoir_specs_reservoir_specs_id_seq OWNED BY reservoir_specs.reservoir_specs_id;


--
-- TOC entry 401 (class 1259 OID 16784334)
-- Name: rnai_experiment; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE rnai_experiment (
    job_id integer NOT NULL,
    number_replicates integer NOT NULL
);


ALTER TABLE public.rnai_experiment OWNER TO postgres;

--
-- TOC entry 5511 (class 0 OID 0)
-- Dependencies: 401
-- Name: TABLE rnai_experiment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE rnai_experiment IS 'Extra information for RNAi experiment jobs.

Once upon a time, it probably made sense to store the number of replicates
for RNAi experiment jobs.  Now RNAi experiment jobs work just like replicating
jobs, which also allow a number of replicates to be specified and which don''t
need to store this explicitly anywhere.  The table can probably be dropped.';


--
-- TOC entry 5512 (class 0 OID 0)
-- Dependencies: 401
-- Name: COLUMN rnai_experiment.number_replicates; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN rnai_experiment.number_replicates IS 'Number of replicates to make of each source rack';


--
-- TOC entry 402 (class 1259 OID 16784337)
-- Name: rnai_experiment_job_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE rnai_experiment_job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rnai_experiment_job_id_seq OWNER TO postgres;

--
-- TOC entry 5514 (class 0 OID 0)
-- Dependencies: 402
-- Name: rnai_experiment_job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE rnai_experiment_job_id_seq OWNED BY rnai_experiment.job_id;


--
-- TOC entry 403 (class 1259 OID 16784339)
-- Name: rnai_experiment_rnai_experiment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE rnai_experiment_rnai_experiment_id_seq
    START WITH 307
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rnai_experiment_rnai_experiment_id_seq OWNER TO postgres;

--
-- TOC entry 404 (class 1259 OID 16784341)
-- Name: sample_cells; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sample_cells (
    sample_id integer NOT NULL,
    cell_line_id integer NOT NULL
);


ALTER TABLE public.sample_cells OWNER TO postgres;

--
-- TOC entry 5517 (class 0 OID 0)
-- Dependencies: 404
-- Name: TABLE sample_cells; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE sample_cells IS 'Cells in a sample';


--
-- TOC entry 405 (class 1259 OID 16784344)
-- Name: iso_request_iso_request_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE iso_request_iso_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.iso_request_iso_request_id_seq OWNER TO thelma;

--
-- TOC entry 5519 (class 0 OID 0)
-- Dependencies: 405
-- Name: iso_request_iso_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE iso_request_iso_request_id_seq OWNED BY iso_request.iso_request_id;


--
-- TOC entry 406 (class 1259 OID 16784346)
-- Name: sample_registration; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sample_registration (
    sample_id integer NOT NULL,
    volume double precision NOT NULL,
    time_stamp timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.sample_registration OWNER TO postgres;

--
-- TOC entry 407 (class 1259 OID 16784350)
-- Name: sample_sample_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sample_sample_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sample_sample_id_seq OWNER TO postgres;

--
-- TOC entry 5521 (class 0 OID 0)
-- Dependencies: 407
-- Name: sample_sample_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE sample_sample_id_seq OWNED BY sample.sample_id;


--
-- TOC entry 408 (class 1259 OID 16784352)
-- Name: sample_set_auto_label_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sample_set_auto_label_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sample_set_auto_label_seq OWNER TO postgres;

--
-- TOC entry 409 (class 1259 OID 16784354)
-- Name: sample_set; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sample_set (
    creation_time timestamp without time zone DEFAULT now(),
    label character varying(32) DEFAULT (('AUTO<'::text || (nextval('sample_set_auto_label_seq'::regclass))::text) || '>'::text) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    sample_set_id integer DEFAULT nextval(('sample_set_sample_set_id_seq'::text)::regclass) NOT NULL,
    sample_set_type character varying(14) NOT NULL
);


ALTER TABLE public.sample_set OWNER TO postgres;

--
-- TOC entry 5524 (class 0 OID 0)
-- Dependencies: 409
-- Name: TABLE sample_set; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE sample_set IS 'A collection of samples, related for some purpose.

If this table were only used for user-defined sets of samples it might be
useful.  As it is, it is an integral part of the job-processing system.  As
such, the user can''t take good advantage of the sample sets, because the
collection of sample sets gets cluttered with autogenerated sets.';


--
-- TOC entry 5525 (class 0 OID 0)
-- Dependencies: 409
-- Name: COLUMN sample_set.creation_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample_set.creation_time IS 'The the sample set was created (optional)

All insert statements should use the default value.';


--
-- TOC entry 5526 (class 0 OID 0)
-- Dependencies: 409
-- Name: COLUMN sample_set.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample_set.label IS 'User-defined label of the sample set.

If this were optional, we would avoid all the useless autogenerated names.
Consider splitting out to a sample_set_label table and only moving entries
across that have useful names.';


--
-- TOC entry 5527 (class 0 OID 0)
-- Dependencies: 409
-- Name: COLUMN sample_set.sample_set_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample_set.sample_set_id IS 'Surrogate primary key of the sample set

Internal ID.  Do not publish.

If we choose to make labels optional, this would become a public ID.';


--
-- TOC entry 5528 (class 0 OID 0)
-- Dependencies: 409
-- Name: COLUMN sample_set.sample_set_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sample_set.sample_set_type IS 'Type of sample set.

WARNING: no constraint ensures correct subtables are in place for the given
sample set type.';


--
-- TOC entry 410 (class 1259 OID 16784364)
-- Name: sample_set_sample; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sample_set_sample (
    sample_set_id integer NOT NULL,
    sample_id integer NOT NULL
);


ALTER TABLE public.sample_set_sample OWNER TO postgres;

--
-- TOC entry 5530 (class 0 OID 0)
-- Dependencies: 410
-- Name: TABLE sample_set_sample; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE sample_set_sample IS 'Many-to-many relationship between samples and sample sets.';


--
-- TOC entry 411 (class 1259 OID 16784367)
-- Name: sample_set_sample_set_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sample_set_sample_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sample_set_sample_set_id_seq OWNER TO postgres;

--
-- TOC entry 412 (class 1259 OID 16784369)
-- Name: sample_set_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sample_set_type (
    sample_set_type_id character varying(14) NOT NULL,
    name character varying(28) NOT NULL,
    description text DEFAULT ''::text,
    CONSTRAINT sample_set_type_name_check CHECK ((char_length((name)::text) > 0)),
    CONSTRAINT sample_set_type_sample_set_type_id_check CHECK ((char_length((sample_set_type_id)::text) > 0))
);


ALTER TABLE public.sample_set_type OWNER TO postgres;

--
-- TOC entry 5533 (class 0 OID 0)
-- Dependencies: 412
-- Name: TABLE sample_set_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE sample_set_type IS 'Type of sample set';


--
-- TOC entry 413 (class 1259 OID 16784378)
-- Name: sample_set_type_sample_set_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sample_set_type_sample_set_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sample_set_type_sample_set_type_id_seq OWNER TO postgres;

--
-- TOC entry 414 (class 1259 OID 16784380)
-- Name: sample_type_sample_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sample_type_sample_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sample_type_sample_type_id_seq OWNER TO postgres;

--
-- TOC entry 415 (class 1259 OID 16784382)
-- Name: seq_identifier_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE seq_identifier_type (
    seq_identifier_type_id integer NOT NULL,
    db_source_id integer NOT NULL,
    name character varying(20) NOT NULL
);


ALTER TABLE public.seq_identifier_type OWNER TO postgres;

--
-- TOC entry 5537 (class 0 OID 0)
-- Dependencies: 415
-- Name: TABLE seq_identifier_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE seq_identifier_type IS 'Type of identifier associated with sequence entity by annotation DB';


--
-- TOC entry 416 (class 1259 OID 16784385)
-- Name: seq_identifier_type_seq_identifier_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE seq_identifier_type_seq_identifier_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_identifier_type_seq_identifier_type_id_seq OWNER TO postgres;

--
-- TOC entry 5539 (class 0 OID 0)
-- Dependencies: 416
-- Name: seq_identifier_type_seq_identifier_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE seq_identifier_type_seq_identifier_type_id_seq OWNED BY seq_identifier_type.seq_identifier_type_id;


--
-- TOC entry 417 (class 1259 OID 16784387)
-- Name: sequence_feature; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE sequence_feature (
    sequence_feature_id integer NOT NULL,
    start integer NOT NULL,
    stop integer NOT NULL,
    strand character(1) NOT NULL,
    sequence_feature_type sequence_feature_type NOT NULL,
    CONSTRAINT start CHECK ((0 < start)),
    CONSTRAINT stop CHECK ((start < stop)),
    CONSTRAINT strand CHECK ((((strand = '-'::bpchar) OR (strand = '.'::bpchar)) OR (strand = '+'::bpchar)))
);


ALTER TABLE public.sequence_feature OWNER TO postgres;

--
-- TOC entry 5541 (class 0 OID 0)
-- Dependencies: 417
-- Name: TABLE sequence_feature; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE sequence_feature IS 'Sequence annotation described by (stranded) sequence coordinates.

Based on Bioperl Bio::SeqFeature.

Follows some strand designation convetion from GFF.';


--
-- TOC entry 5542 (class 0 OID 0)
-- Dependencies: 417
-- Name: COLUMN sequence_feature.sequence_feature_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sequence_feature.sequence_feature_id IS 'Surrogate key of the sequence feature';


--
-- TOC entry 5543 (class 0 OID 0)
-- Dependencies: 417
-- Name: COLUMN sequence_feature.start; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sequence_feature.start IS 'One-based offset from start of sequence to first base in feature';


--
-- TOC entry 5544 (class 0 OID 0)
-- Dependencies: 417
-- Name: COLUMN sequence_feature.stop; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sequence_feature.stop IS 'One-based offset from start of sequence to last base in feature';


--
-- TOC entry 5545 (class 0 OID 0)
-- Dependencies: 417
-- Name: COLUMN sequence_feature.strand; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN sequence_feature.strand IS 'Strand on which feature is located.

Follows GFF convention.

 "+" indicates top strand
 "-" indicates bottom strand
 "." indicates no strandedness';


--
-- TOC entry 418 (class 1259 OID 16784396)
-- Name: sequence_feature_sequence_feature_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sequence_feature_sequence_feature_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sequence_feature_sequence_feature_id_seq OWNER TO postgres;

--
-- TOC entry 5547 (class 0 OID 0)
-- Dependencies: 418
-- Name: sequence_feature_sequence_feature_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE sequence_feature_sequence_feature_id_seq OWNED BY sequence_feature.sequence_feature_id;


--
-- TOC entry 419 (class 1259 OID 16784398)
-- Name: sequence_hybridization_sequence_hybridization_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sequence_hybridization_sequence_hybridization_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sequence_hybridization_sequence_hybridization_id_seq OWNER TO postgres;

--
-- TOC entry 420 (class 1259 OID 16784400)
-- Name: sequence_transcript_target_sequence_transcript_target_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE sequence_transcript_target_sequence_transcript_target_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sequence_transcript_target_sequence_transcript_target_id_seq OWNER TO postgres;

--
-- TOC entry 421 (class 1259 OID 16784402)
-- Name: single_supplier_molecule_design; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE single_supplier_molecule_design (
    supplier_molecule_design_id integer NOT NULL,
    molecule_design_id integer NOT NULL
);


ALTER TABLE public.single_supplier_molecule_design OWNER TO gathmann;

--
-- TOC entry 5551 (class 0 OID 0)
-- Dependencies: 421
-- Name: TABLE single_supplier_molecule_design; Type: COMMENT; Schema: public; Owner: gathmann
--

COMMENT ON TABLE single_supplier_molecule_design IS 'A pooled supplier molecule design referencing one or more internal molecule designs.';


--
-- TOC entry 422 (class 1259 OID 16784405)
-- Name: species_species_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE species_species_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.species_species_id_seq OWNER TO postgres;

--
-- TOC entry 5553 (class 0 OID 0)
-- Dependencies: 422
-- Name: species_species_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE species_species_id_seq OWNED BY species.species_id;


--
-- TOC entry 423 (class 1259 OID 16784407)
-- Name: status_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE status_type (
    status_type_id character varying(12) NOT NULL,
    name character varying(24) NOT NULL,
    description text DEFAULT ''::text,
    CONSTRAINT status_type_name_check CHECK ((char_length((name)::text) > 0)),
    CONSTRAINT status_type_status_type_id_check CHECK ((char_length((status_type_id)::text) > 0))
);


ALTER TABLE public.status_type OWNER TO postgres;

--
-- TOC entry 424 (class 1259 OID 16784416)
-- Name: stock_info_view; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE stock_info_view (
    stock_info_id text,
    molecule_design_set_id integer,
    molecule_type_id character varying,
    concentration double precision,
    total_tubes bigint,
    total_volume double precision,
    minimum_volume double precision,
    maximum_volume double precision
);


ALTER TABLE public.stock_info_view OWNER TO gathmann;

--
-- TOC entry 425 (class 1259 OID 16784422)
-- Name: stock_rack; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE stock_rack (
    stock_rack_id integer NOT NULL,
    label character varying(20) NOT NULL,
    rack_id integer NOT NULL,
    worklist_series_id integer NOT NULL,
    rack_layout_id integer,
    stock_rack_type character varying(10) NOT NULL,
    CONSTRAINT stock_rack_stock_rack_type_check CHECK (((stock_rack_type)::text = ANY (ARRAY[('STOCK_RACK'::character varying)::text, ('ISO_JOB'::character varying)::text, ('ISO'::character varying)::text, ('SECTOR'::character varying)::text])))
);


ALTER TABLE public.stock_rack OWNER TO gathmann;

--
-- TOC entry 426 (class 1259 OID 16784426)
-- Name: stock_rack_stock_rack_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE stock_rack_stock_rack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stock_rack_stock_rack_id_seq OWNER TO gathmann;

--
-- TOC entry 5557 (class 0 OID 0)
-- Dependencies: 426
-- Name: stock_rack_stock_rack_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gathmann
--

ALTER SEQUENCE stock_rack_stock_rack_id_seq OWNED BY stock_rack.stock_rack_id;


--
-- TOC entry 427 (class 1259 OID 16784428)
-- Name: stock_sample; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE stock_sample (
    sample_id integer NOT NULL,
    molecule_design_set_id integer NOT NULL,
    supplier_id integer NOT NULL,
    molecule_type character varying NOT NULL,
    concentration double precision NOT NULL,
    CONSTRAINT stock_sample_concentration_check CHECK ((concentration > (0.0)::double precision))
);


ALTER TABLE public.stock_sample OWNER TO gathmann;

--
-- TOC entry 5558 (class 0 OID 0)
-- Dependencies: 427
-- Name: TABLE stock_sample; Type: COMMENT; Schema: public; Owner: gathmann
--

COMMENT ON TABLE stock_sample IS 'A stock sample is a special case of a sample which contains molecules of one or more designs of the same molecule type from the same supplier in the same concentration. The container holding a stock sample is always a 2D barcoded MATRIX tube.';


--
-- TOC entry 428 (class 1259 OID 16784435)
-- Name: stock_sample_creation_iso; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE stock_sample_creation_iso (
    iso_id integer NOT NULL,
    ticket_number integer NOT NULL,
    layout_number integer NOT NULL,
    CONSTRAINT layout_number_greater_zero CHECK ((layout_number > 0)),
    CONSTRAINT ticket_number_greater_zero CHECK ((ticket_number > 0))
);


ALTER TABLE public.stock_sample_creation_iso OWNER TO gathmann;

--
-- TOC entry 429 (class 1259 OID 16784440)
-- Name: stock_sample_creation_iso_request; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE stock_sample_creation_iso_request (
    iso_request_id integer NOT NULL,
    stock_volume double precision NOT NULL,
    stock_concentration double precision NOT NULL,
    number_designs integer NOT NULL,
    preparation_plate_volume double precision,
    CONSTRAINT stock_sample_creation_concentration_positive CHECK ((stock_concentration > (0)::double precision)),
    CONSTRAINT stock_sample_creation_iso_reques_preparation_plate_volume_check CHECK ((preparation_plate_volume > (0.0)::double precision)),
    CONSTRAINT stock_sample_creation_number_designs_greater_zero CHECK ((number_designs > 0)),
    CONSTRAINT stock_sample_creation_volume_positive CHECK ((stock_volume > (0)::double precision))
);


ALTER TABLE public.stock_sample_creation_iso_request OWNER TO gathmann;

--
-- TOC entry 430 (class 1259 OID 16784447)
-- Name: subproject_subproject_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE subproject_subproject_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subproject_subproject_id_seq OWNER TO postgres;

--
-- TOC entry 431 (class 1259 OID 16784449)
-- Name: subproject; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE subproject (
    project_id integer NOT NULL,
    label character varying NOT NULL,
    creation_date timestamp with time zone NOT NULL,
    file_storage_site_id integer,
    active boolean DEFAULT true NOT NULL,
    subproject_id integer DEFAULT nextval('subproject_subproject_id_seq'::regclass) NOT NULL
);


ALTER TABLE public.subproject OWNER TO postgres;

--
-- TOC entry 5562 (class 0 OID 0)
-- Dependencies: 431
-- Name: TABLE subproject; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE subproject IS 'A part of phase of a project.

All jobs must be associated with a subproject.';


--
-- TOC entry 5563 (class 0 OID 0)
-- Dependencies: 431
-- Name: COLUMN subproject.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN subproject.label IS 'User-assigned name for the subproject, intended for display.

Must be unique for a given project.';


--
-- TOC entry 5564 (class 0 OID 0)
-- Dependencies: 431
-- Name: COLUMN subproject.creation_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN subproject.creation_date IS 'Date the subproject was created.';


--
-- TOC entry 5565 (class 0 OID 0)
-- Dependencies: 431
-- Name: COLUMN subproject.file_storage_site_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN subproject.file_storage_site_id IS 'Directory where subproject files are kept.';


--
-- TOC entry 5566 (class 0 OID 0)
-- Dependencies: 431
-- Name: COLUMN subproject.active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN subproject.active IS 'TRUE if subproject is currently in progress.';


--
-- TOC entry 5567 (class 0 OID 0)
-- Dependencies: 431
-- Name: COLUMN subproject.subproject_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN subproject.subproject_id IS 'Surrogate primary key of the subproject

Internal ID.  Do not publish.

The value of this column is questionable.  It may be useful in that it allows
single-column foreign keys.  Consider using (project_id, label) as the primary
key instead.';


--
-- TOC entry 432 (class 1259 OID 16784457)
-- Name: supplier_barcode; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE supplier_barcode (
    supplier_barcode character varying(30) NOT NULL,
    rack_id integer NOT NULL,
    supplier_id integer NOT NULL
);


ALTER TABLE public.supplier_barcode OWNER TO postgres;

--
-- TOC entry 5569 (class 0 OID 0)
-- Dependencies: 432
-- Name: TABLE supplier_barcode; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE supplier_barcode IS 'Supplier-assigned barcode of a rack.

WARNING: no primary key defined.  Consider defining a primary key on (rack_id)';


--
-- TOC entry 5570 (class 0 OID 0)
-- Dependencies: 432
-- Name: COLUMN supplier_barcode.supplier_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN supplier_barcode.supplier_id IS 'ID of supplier organization

WARNING: no foreign key constraint!';


--
-- TOC entry 433 (class 1259 OID 16784460)
-- Name: supplier_molecule_design_supplier_molecule_design_id_seq; Type: SEQUENCE; Schema: public; Owner: gathmann
--

CREATE SEQUENCE supplier_molecule_design_supplier_molecule_design_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.supplier_molecule_design_supplier_molecule_design_id_seq OWNER TO gathmann;

--
-- TOC entry 434 (class 1259 OID 16784462)
-- Name: supplier_molecule_design; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE supplier_molecule_design (
    supplier_id integer NOT NULL,
    product_id character varying NOT NULL,
    time_stamp timestamp with time zone DEFAULT now() NOT NULL,
    is_current boolean DEFAULT false NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    supplier_molecule_design_id integer DEFAULT nextval('supplier_molecule_design_supplier_molecule_design_id_seq'::regclass) NOT NULL,
    CONSTRAINT supplier_molecule_design_id CHECK (((product_id)::text <> ''::text))
);


ALTER TABLE public.supplier_molecule_design OWNER TO postgres;

--
-- TOC entry 5572 (class 0 OID 0)
-- Dependencies: 434
-- Name: TABLE supplier_molecule_design; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE supplier_molecule_design IS 'Supplier-issued IDs for molecule designs';


--
-- TOC entry 5573 (class 0 OID 0)
-- Dependencies: 434
-- Name: COLUMN supplier_molecule_design.supplier_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN supplier_molecule_design.supplier_id IS 'ID of supplier organization';


--
-- TOC entry 5574 (class 0 OID 0)
-- Dependencies: 434
-- Name: COLUMN supplier_molecule_design.product_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN supplier_molecule_design.product_id IS 'Supplier-issued molecule design ID';


--
-- TOC entry 435 (class 1259 OID 16784473)
-- Name: supplier_molecule_design_view; Type: VIEW; Schema: public; Owner: gathmann
--

CREATE VIEW supplier_molecule_design_view AS
    SELECT supplier_molecule_design.supplier_molecule_design_id, supplier_molecule_design.supplier_id, supplier_molecule_design.product_id, supplier_molecule_design.time_stamp FROM supplier_molecule_design WHERE supplier_molecule_design.is_current;


ALTER TABLE public.supplier_molecule_design_view OWNER TO gathmann;

--
-- TOC entry 436 (class 1259 OID 16784477)
-- Name: supplier_structure_annotation; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE supplier_structure_annotation (
    supplier_molecule_design_id integer NOT NULL,
    chemical_structure_id integer NOT NULL,
    annotation character varying NOT NULL
);


ALTER TABLE public.supplier_structure_annotation OWNER TO gathmann;

--
-- TOC entry 5577 (class 0 OID 0)
-- Dependencies: 436
-- Name: TABLE supplier_structure_annotation; Type: COMMENT; Schema: public; Owner: gathmann
--

COMMENT ON TABLE supplier_structure_annotation IS 'Holds the supplier-specific annotation of a chemical structure that belongs to a supplier molecule design (e.g., specifying the sense strand in a double-stranded design).';


--
-- TOC entry 437 (class 1259 OID 16784483)
-- Name: tag; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tag (
    tag_id integer NOT NULL,
    tag_domain_id integer NOT NULL,
    tag_predicate_id integer NOT NULL,
    tag_value_id integer NOT NULL
);


ALTER TABLE public.tag OWNER TO thelma;

--
-- TOC entry 5579 (class 0 OID 0)
-- Dependencies: 437
-- Name: TABLE tag; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE tag IS 'Machine tag consisting of a namespace, a predicate and a value.';


--
-- TOC entry 438 (class 1259 OID 16784486)
-- Name: tag_domain; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tag_domain (
    tag_domain_id integer NOT NULL,
    domain character varying NOT NULL
);


ALTER TABLE public.tag_domain OWNER TO thelma;

--
-- TOC entry 5581 (class 0 OID 0)
-- Dependencies: 438
-- Name: TABLE tag_domain; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE tag_domain IS 'Namespace for a machine tag (unique).';


--
-- TOC entry 439 (class 1259 OID 16784492)
-- Name: tag_domain_tag_domain_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE tag_domain_tag_domain_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tag_domain_tag_domain_id_seq OWNER TO thelma;

--
-- TOC entry 5583 (class 0 OID 0)
-- Dependencies: 439
-- Name: tag_domain_tag_domain_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE tag_domain_tag_domain_id_seq OWNED BY tag_domain.tag_domain_id;


--
-- TOC entry 440 (class 1259 OID 16784494)
-- Name: tag_predicate; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tag_predicate (
    tag_predicate_id integer NOT NULL,
    predicate character varying NOT NULL
);


ALTER TABLE public.tag_predicate OWNER TO thelma;

--
-- TOC entry 5584 (class 0 OID 0)
-- Dependencies: 440
-- Name: TABLE tag_predicate; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE tag_predicate IS 'Predicate for a machine tag (unique).';


--
-- TOC entry 441 (class 1259 OID 16784500)
-- Name: tag_predicate_tag_predicate_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE tag_predicate_tag_predicate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tag_predicate_tag_predicate_id_seq OWNER TO thelma;

--
-- TOC entry 5586 (class 0 OID 0)
-- Dependencies: 441
-- Name: tag_predicate_tag_predicate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE tag_predicate_tag_predicate_id_seq OWNED BY tag_predicate.tag_predicate_id;


--
-- TOC entry 442 (class 1259 OID 16784502)
-- Name: tag_tag_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE tag_tag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tag_tag_id_seq OWNER TO thelma;

--
-- TOC entry 5587 (class 0 OID 0)
-- Dependencies: 442
-- Name: tag_tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE tag_tag_id_seq OWNED BY tag.tag_id;


--
-- TOC entry 443 (class 1259 OID 16784504)
-- Name: tag_value; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tag_value (
    tag_value_id integer NOT NULL,
    value character varying NOT NULL
);


ALTER TABLE public.tag_value OWNER TO thelma;

--
-- TOC entry 5588 (class 0 OID 0)
-- Dependencies: 443
-- Name: TABLE tag_value; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE tag_value IS 'Value for a machine tag (unique).';


--
-- TOC entry 444 (class 1259 OID 16784510)
-- Name: tag_value_tag_value_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE tag_value_tag_value_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tag_value_tag_value_id_seq OWNER TO thelma;

--
-- TOC entry 5590 (class 0 OID 0)
-- Dependencies: 444
-- Name: tag_value_tag_value_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE tag_value_tag_value_id_seq OWNED BY tag_value.tag_value_id;


--
-- TOC entry 445 (class 1259 OID 16784512)
-- Name: tagged; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tagged (
    tagged_id integer NOT NULL,
    type character varying NOT NULL
);


ALTER TABLE public.tagged OWNER TO thelma;

--
-- TOC entry 5591 (class 0 OID 0)
-- Dependencies: 445
-- Name: TABLE tagged; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE tagged IS 'Tagged object.';


--
-- TOC entry 446 (class 1259 OID 16784518)
-- Name: tagged_rack_position_set; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tagged_rack_position_set (
    rack_layout_id integer NOT NULL,
    tagged_id integer NOT NULL,
    rack_position_set_id integer NOT NULL
);


ALTER TABLE public.tagged_rack_position_set OWNER TO thelma;

--
-- TOC entry 5593 (class 0 OID 0)
-- Dependencies: 446
-- Name: TABLE tagged_rack_position_set; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE tagged_rack_position_set IS 'Tagged position set within a rack layout. A given rack layout may reference
 one to many tagged rack position sets.';


--
-- TOC entry 447 (class 1259 OID 16784521)
-- Name: tagged_tagged_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE tagged_tagged_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tagged_tagged_id_seq OWNER TO thelma;

--
-- TOC entry 5595 (class 0 OID 0)
-- Dependencies: 447
-- Name: tagged_tagged_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE tagged_tagged_id_seq OWNED BY tagged.tagged_id;


--
-- TOC entry 448 (class 1259 OID 16784523)
-- Name: tagging; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tagging (
    tagged_id integer NOT NULL,
    tag_id integer NOT NULL,
    user_id character varying NOT NULL,
    time_stamp timestamp with time zone NOT NULL
);


ALTER TABLE public.tagging OWNER TO thelma;

--
-- TOC entry 5596 (class 0 OID 0)
-- Dependencies: 448
-- Name: TABLE tagging; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE tagging IS 'Tagging event performed by a user at a specific time, linking a tagged
 object with a tag.';


--
-- TOC entry 449 (class 1259 OID 16784529)
-- Name: target; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE target (
    target_id integer NOT NULL,
    molecule_design_id integer NOT NULL,
    transcript_id integer NOT NULL
);


ALTER TABLE public.target OWNER TO thelma;

--
-- TOC entry 5598 (class 0 OID 0)
-- Dependencies: 449
-- Name: TABLE target; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE target IS 'Maps a molecule design to one or several transcripts it targets.';


--
-- TOC entry 450 (class 1259 OID 16784532)
-- Name: target_set; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE target_set (
    target_set_id integer NOT NULL,
    label character varying NOT NULL
);


ALTER TABLE public.target_set OWNER TO thelma;

--
-- TOC entry 5600 (class 0 OID 0)
-- Dependencies: 450
-- Name: TABLE target_set; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE target_set IS 'A named set of targets.';


--
-- TOC entry 451 (class 1259 OID 16784538)
-- Name: target_set_member; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE target_set_member (
    target_set_id integer NOT NULL,
    target_id integer NOT NULL
);


ALTER TABLE public.target_set_member OWNER TO thelma;

--
-- TOC entry 5602 (class 0 OID 0)
-- Dependencies: 451
-- Name: TABLE target_set_member; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE target_set_member IS 'Member of a target set.';


--
-- TOC entry 452 (class 1259 OID 16784541)
-- Name: target_set_target_set_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE target_set_target_set_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.target_set_target_set_id_seq OWNER TO thelma;

--
-- TOC entry 5604 (class 0 OID 0)
-- Dependencies: 452
-- Name: target_set_target_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE target_set_target_set_id_seq OWNED BY target_set.target_set_id;


--
-- TOC entry 453 (class 1259 OID 16784543)
-- Name: target_target_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE target_target_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.target_target_id_seq OWNER TO thelma;

--
-- TOC entry 5605 (class 0 OID 0)
-- Dependencies: 453
-- Name: target_target_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE target_target_id_seq OWNED BY target.target_id;


--
-- TOC entry 454 (class 1259 OID 16784545)
-- Name: task; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE task (
    task_id integer NOT NULL,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    instruction text,
    comment text,
    db_user_id integer,
    job_step_id integer NOT NULL,
    status_type character varying(12) NOT NULL
);


ALTER TABLE public.task OWNER TO postgres;

--
-- TOC entry 5606 (class 0 OID 0)
-- Dependencies: 454
-- Name: TABLE task; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE task IS 'Atomic unit of work within a job step.

Consider splitting start_time, end_time and db_user_id into a
task_processed table.';


--
-- TOC entry 5607 (class 0 OID 0)
-- Dependencies: 454
-- Name: COLUMN task.start_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task.start_time IS 'Time task processing was started (optional)';


--
-- TOC entry 5608 (class 0 OID 0)
-- Dependencies: 454
-- Name: COLUMN task.end_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task.end_time IS 'Time task was completed (optional)';


--
-- TOC entry 5609 (class 0 OID 0)
-- Dependencies: 454
-- Name: COLUMN task.instruction; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task.instruction IS 'Instructions to the operator from the scheduler.

DEPRECATED.

The content of this column was migrated to the job_step table.  Dropping
this column was probably forgotten.  Should be dropped now.';


--
-- TOC entry 5610 (class 0 OID 0)
-- Dependencies: 454
-- Name: COLUMN task.comment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task.comment IS 'Space for observations from operator.';


--
-- TOC entry 5611 (class 0 OID 0)
-- Dependencies: 454
-- Name: COLUMN task.db_user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task.db_user_id IS 'ID of operator who performed the task';


--
-- TOC entry 5612 (class 0 OID 0)
-- Dependencies: 454
-- Name: COLUMN task.status_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task.status_type IS 'Status of task';


--
-- TOC entry 455 (class 1259 OID 16784551)
-- Name: task_item; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE task_item (
    rack_id integer NOT NULL,
    task_id integer NOT NULL,
    comment text,
    item_set_id integer NOT NULL,
    task_item_id integer DEFAULT nextval(('task_item_task_item_id_seq'::text)::regclass) NOT NULL
);


ALTER TABLE public.task_item OWNER TO postgres;

--
-- TOC entry 5614 (class 0 OID 0)
-- Dependencies: 455
-- Name: TABLE task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE task_item IS 'Association of a rack with a task.';


--
-- TOC entry 5615 (class 0 OID 0)
-- Dependencies: 455
-- Name: COLUMN task_item.comment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_item.comment IS 'Space for operator observations.';


--
-- TOC entry 5616 (class 0 OID 0)
-- Dependencies: 455
-- Name: COLUMN task_item.item_set_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_item.item_set_id IS 'ID of sample set all output samples belong to.  This is a poor way of
associating samples with task items.  See rearrayed_containers for more
details.';


--
-- TOC entry 5617 (class 0 OID 0)
-- Dependencies: 455
-- Name: COLUMN task_item.task_item_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_item.task_item_id IS 'Surrogate primary key for task item.

Not strictly necessary, but allows us to use single-column foreign keys to
refer to this table.  Otherwise we would have to use (rack_id, task_id) as
in foreign keys.';


--
-- TOC entry 456 (class 1259 OID 16784558)
-- Name: task_item_task_item_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE task_item_task_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.task_item_task_item_id_seq OWNER TO postgres;

--
-- TOC entry 457 (class 1259 OID 16784560)
-- Name: task_report; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE task_report (
    subproject_id integer NOT NULL,
    task_type_id integer NOT NULL,
    report_type character varying NOT NULL
);


ALTER TABLE public.task_report OWNER TO postgres;

--
-- TOC entry 5620 (class 0 OID 0)
-- Dependencies: 457
-- Name: TABLE task_report; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE task_report IS 'Reports for specific task type and project';


--
-- TOC entry 5621 (class 0 OID 0)
-- Dependencies: 457
-- Name: COLUMN task_report.report_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_report.report_type IS 'Name of report type';


--
-- TOC entry 458 (class 1259 OID 16784566)
-- Name: task_task_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE task_task_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.task_task_id_seq OWNER TO postgres;

--
-- TOC entry 5623 (class 0 OID 0)
-- Dependencies: 458
-- Name: task_task_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE task_task_id_seq OWNED BY task.task_id;


--
-- TOC entry 459 (class 1259 OID 16784568)
-- Name: task_type; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE task_type (
    task_type_id integer NOT NULL,
    name character varying(32) NOT NULL,
    label character varying(64) NOT NULL,
    xml text NOT NULL
);


ALTER TABLE public.task_type OWNER TO postgres;

--
-- TOC entry 5625 (class 0 OID 0)
-- Dependencies: 459
-- Name: COLUMN task_type.task_type_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_type.task_type_id IS 'Surrogate primary key of the task type

Internal ID.  Do not publish.

The value of this column is questionable.  Consider dropping it and using
name or label as the primary key in its place.';


--
-- TOC entry 5626 (class 0 OID 0)
-- Dependencies: 459
-- Name: COLUMN task_type.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_type.name IS 'User-assigned name for the task type, intended for programatic purposes

Also used as the XML ID for references from job_type.xml.';


--
-- TOC entry 5627 (class 0 OID 0)
-- Dependencies: 459
-- Name: COLUMN task_type.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_type.label IS 'User-assigned name for the task type, intended for display';


--
-- TOC entry 5628 (class 0 OID 0)
-- Dependencies: 459
-- Name: COLUMN task_type.xml; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN task_type.xml IS 'XML specification of the task type.

Because this information is stored as XML in a text field, we can''t
enforce constraints or use SQL to manipulate task types.  Consider creating new
tables to manage the information currently encoded in XML.

All current task types define at least one Input and at least one Output,
just as the DTD indicates.  It is not clear to me why the SOURCE task type has
an input or why the SINK task type has an output.  CeLMA might depend on this.

The DTD for the XML is as follows:

<!DOCTYPE TaskType [
  <!-- root element -->
  <!ELEMENT TaskType TaskInterface>
  <!-- ID of the task type, should be the same as task_type.name -->
  <!ATTLIST TaskType id ID #REQUIRED>
  <!-- Name of bitmap file for rendering.  If not specified a generic bitmap
    -- should be used -->
  <!ATTLIST TaskType bitmap CDATA #IMPLIED>
  <!-- DEPRECATED.  XML file for processing UI.  Ignored by CeLMA -->
  <!ATTLIST TaskType plugin_xml CDATA #IMPLIED>
  <!-- DEPRECATED.  Module for processing UI.  Ignored by CeLMA -->
  <!ATTLIST TaskType module CDATA #IMPLIED>
  <!-- DEPRECATED.  Widget name for processing UI.  Ignored by CeLMA -->
  <!ATTLIST TaskType widget_name CDATA #IMPLIED>
  <!-- DEPRECATED.  Python package for processing UI.  Ignored by CeLMA -->
  <!ATTLIST TaskType path CDATA #IMPLIED>
  <!-- DEPRECATED.  Size in pixels of processing UI in tuple syntax.
    -- Ignored by CeLMA -->
  <!ATTLIST TaskType size CDATA #IMPLIED>
  <!ELEMENT TaskInterface (Input, Output)>
  <!-- Container for input connectors -->
  <!ELEMENT Input Connector+>
  <!-- Container for output connectors -->
  <!ELEMENT Output Connector+>
  <!ELEMENT Connector>
  <!-- Not an XML ID.  Rather a zero-based integer index.  Indexes for input
    -- connectors are independent of indexes for output connectors -->
  <!ATTLIST Connector id CDATA #REQUIRED>
  <!-- All current entries have an item_type of PLATE.  I don''t know what
    -- this was intended to do -->
  <!ATTLIST Connector item_type NMTOKEN>
]>';


--
-- TOC entry 460 (class 1259 OID 16784574)
-- Name: task_type_task_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE task_type_task_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.task_type_task_type_id_seq OWNER TO postgres;

--
-- TOC entry 5630 (class 0 OID 0)
-- Dependencies: 460
-- Name: task_type_task_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE task_type_task_type_id_seq OWNED BY task_type.task_type_id;


--
-- TOC entry 461 (class 1259 OID 16784576)
-- Name: transcript_gene; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE transcript_gene (
    transcript_id integer NOT NULL,
    gene_id integer NOT NULL
);


ALTER TABLE public.transcript_gene OWNER TO thelma;

--
-- TOC entry 5632 (class 0 OID 0)
-- Dependencies: 461
-- Name: TABLE transcript_gene; Type: COMMENT; Schema: public; Owner: thelma
--

COMMENT ON TABLE transcript_gene IS 'Maps a transcript to exactly one gene (if it has one).';


--
-- TOC entry 462 (class 1259 OID 16784579)
-- Name: transcript_identifier; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE transcript_identifier (
    transcript_identifier_id integer NOT NULL,
    name character varying(30) NOT NULL,
    seq_identifier_type_id integer NOT NULL,
    transcript_id integer NOT NULL
);


ALTER TABLE public.transcript_identifier OWNER TO postgres;

--
-- TOC entry 5634 (class 0 OID 0)
-- Dependencies: 462
-- Name: TABLE transcript_identifier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE transcript_identifier IS 'Identifier associated with transcript by annotation DB';


--
-- TOC entry 463 (class 1259 OID 16784582)
-- Name: transcript_identifier_transcript_identifier_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE transcript_identifier_transcript_identifier_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transcript_identifier_transcript_identifier_id_seq OWNER TO postgres;

--
-- TOC entry 5636 (class 0 OID 0)
-- Dependencies: 463
-- Name: transcript_identifier_transcript_identifier_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE transcript_identifier_transcript_identifier_id_seq OWNED BY transcript_identifier.transcript_identifier_id;


--
-- TOC entry 464 (class 1259 OID 16784584)
-- Name: transfection_job_step; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE transfection_job_step (
    job_step_id integer NOT NULL,
    cell_line_id integer NOT NULL
);


ALTER TABLE public.transfection_job_step OWNER TO postgres;

--
-- TOC entry 5638 (class 0 OID 0)
-- Dependencies: 464
-- Name: TABLE transfection_job_step; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE transfection_job_step IS 'Extra information for scheduled transfection job steps.';


--
-- TOC entry 5639 (class 0 OID 0)
-- Dependencies: 464
-- Name: COLUMN transfection_job_step.cell_line_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN transfection_job_step.cell_line_id IS 'Cell line to be added during transfection.';


--
-- TOC entry 465 (class 1259 OID 16784587)
-- Name: transfer_type; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE transfer_type (
    name character varying(20) NOT NULL
);


ALTER TABLE public.transfer_type OWNER TO thelma;

--
-- TOC entry 466 (class 1259 OID 16784590)
-- Name: tube_transfer; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tube_transfer (
    tube_transfer_id integer NOT NULL,
    tube_id integer NOT NULL,
    source_rack_id integer NOT NULL,
    target_rack_id integer NOT NULL,
    source_position_id integer NOT NULL,
    target_position_id integer NOT NULL
);


ALTER TABLE public.tube_transfer OWNER TO thelma;

--
-- TOC entry 467 (class 1259 OID 16784593)
-- Name: tube_transfer_tube_transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE tube_transfer_tube_transfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tube_transfer_tube_transfer_id_seq OWNER TO thelma;

--
-- TOC entry 5643 (class 0 OID 0)
-- Dependencies: 467
-- Name: tube_transfer_tube_transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE tube_transfer_tube_transfer_id_seq OWNED BY tube_transfer.tube_transfer_id;


--
-- TOC entry 468 (class 1259 OID 16784595)
-- Name: tube_transfer_worklist; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tube_transfer_worklist (
    tube_transfer_worklist_id integer NOT NULL,
    db_user_id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tube_transfer_worklist OWNER TO thelma;

--
-- TOC entry 469 (class 1259 OID 16784599)
-- Name: tube_transfer_worklist_member; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE tube_transfer_worklist_member (
    tube_transfer_worklist_id integer NOT NULL,
    tube_transfer_id integer NOT NULL
);


ALTER TABLE public.tube_transfer_worklist_member OWNER TO thelma;

--
-- TOC entry 470 (class 1259 OID 16784602)
-- Name: tube_transfer_worklist_tube_transfer_worklist_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE tube_transfer_worklist_tube_transfer_worklist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tube_transfer_worklist_tube_transfer_worklist_id_seq OWNER TO thelma;

--
-- TOC entry 5646 (class 0 OID 0)
-- Dependencies: 470
-- Name: tube_transfer_worklist_tube_transfer_worklist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE tube_transfer_worklist_tube_transfer_worklist_id_seq OWNED BY tube_transfer_worklist.tube_transfer_worklist_id;


--
-- TOC entry 471 (class 1259 OID 16784604)
-- Name: user_preferences; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE user_preferences (
    user_id integer NOT NULL,
    app_name character varying(20) NOT NULL,
    preferences character varying NOT NULL,
    user_preferences_id integer NOT NULL
);


ALTER TABLE public.user_preferences OWNER TO thelma;

--
-- TOC entry 472 (class 1259 OID 16784610)
-- Name: user_preferences_user_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE user_preferences_user_preferences_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_preferences_user_preferences_id_seq OWNER TO thelma;

--
-- TOC entry 5648 (class 0 OID 0)
-- Dependencies: 472
-- Name: user_preferences_user_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE user_preferences_user_preferences_id_seq OWNED BY user_preferences.user_preferences_id;


--
-- TOC entry 473 (class 1259 OID 16784612)
-- Name: worklist_series; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE worklist_series (
    worklist_series_id integer NOT NULL
);


ALTER TABLE public.worklist_series OWNER TO thelma;

--
-- TOC entry 474 (class 1259 OID 16784615)
-- Name: worklist_series_experiment_design; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE worklist_series_experiment_design (
    experiment_design_id integer NOT NULL,
    worklist_series_id integer NOT NULL
);


ALTER TABLE public.worklist_series_experiment_design OWNER TO thelma;

--
-- TOC entry 475 (class 1259 OID 16784618)
-- Name: worklist_series_experiment_design_rack; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE worklist_series_experiment_design_rack (
    experiment_design_rack_id integer NOT NULL,
    worklist_series_id integer NOT NULL
);


ALTER TABLE public.worklist_series_experiment_design_rack OWNER TO thelma;

--
-- TOC entry 476 (class 1259 OID 16784621)
-- Name: worklist_series_iso_job; Type: TABLE; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE TABLE worklist_series_iso_job (
    job_id integer NOT NULL,
    worklist_series_id integer NOT NULL
);


ALTER TABLE public.worklist_series_iso_job OWNER TO gathmann;

--
-- TOC entry 477 (class 1259 OID 16784624)
-- Name: worklist_series_iso_request; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE worklist_series_iso_request (
    iso_request_id integer NOT NULL,
    worklist_series_id integer NOT NULL
);


ALTER TABLE public.worklist_series_iso_request OWNER TO thelma;

--
-- TOC entry 478 (class 1259 OID 16784627)
-- Name: worklist_series_member; Type: TABLE; Schema: public; Owner: thelma; Tablespace: 
--

CREATE TABLE worklist_series_member (
    worklist_series_id integer NOT NULL,
    planned_worklist_id integer NOT NULL,
    index integer NOT NULL,
    CONSTRAINT index_non_negative CHECK ((index >= 0))
);


ALTER TABLE public.worklist_series_member OWNER TO thelma;

--
-- TOC entry 479 (class 1259 OID 16784631)
-- Name: worklist_series_worklist_series_id_seq; Type: SEQUENCE; Schema: public; Owner: thelma
--

CREATE SEQUENCE worklist_series_worklist_series_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.worklist_series_worklist_series_id_seq OWNER TO thelma;

--
-- TOC entry 5654 (class 0 OID 0)
-- Dependencies: 479
-- Name: worklist_series_worklist_series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: thelma
--

ALTER SEQUENCE worklist_series_worklist_series_id_seq OWNED BY worklist_series.worklist_series_id;


--
-- TOC entry 3755 (class 2604 OID 16784635)
-- Name: cell_line_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cell_line ALTER COLUMN cell_line_id SET DEFAULT nextval('cell_line_cell_line_id_seq'::regclass);


--
-- TOC entry 3756 (class 2604 OID 16784636)
-- Name: chemical_structure_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY chemical_structure ALTER COLUMN chemical_structure_id SET DEFAULT nextval('chemical_structure_chemical_structure_id_seq'::regclass);


--
-- TOC entry 3757 (class 2604 OID 16784637)
-- Name: chromosome_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome ALTER COLUMN chromosome_id SET DEFAULT nextval('chromosome_chromosome_id_seq'::regclass);


--
-- TOC entry 3759 (class 2604 OID 16784638)
-- Name: container_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY container ALTER COLUMN container_id SET DEFAULT nextval('container_container_id_seq'::regclass);


--
-- TOC entry 3776 (class 2604 OID 16784639)
-- Name: container_specs_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY container_specs ALTER COLUMN container_specs_id SET DEFAULT nextval('container_specs_container_specs_id_seq'::regclass);


--
-- TOC entry 3781 (class 2604 OID 16784640)
-- Name: db_group_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY db_group ALTER COLUMN db_group_id SET DEFAULT nextval('db_group_db_group_id_seq'::regclass);


--
-- TOC entry 3779 (class 2604 OID 16784641)
-- Name: db_release_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY db_release ALTER COLUMN db_release_id SET DEFAULT nextval('db_release_db_release_id_seq'::regclass);


--
-- TOC entry 3780 (class 2604 OID 16784642)
-- Name: db_source_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY db_source ALTER COLUMN db_source_id SET DEFAULT nextval('db_source_db_source_id_seq'::regclass);


--
-- TOC entry 3782 (class 2604 OID 16784643)
-- Name: db_user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY db_user ALTER COLUMN db_user_id SET DEFAULT nextval('db_user_db_user_id_seq'::regclass);


--
-- TOC entry 3783 (class 2604 OID 16784644)
-- Name: device_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY device ALTER COLUMN device_id SET DEFAULT nextval('device_device_id_seq'::regclass);


--
-- TOC entry 3784 (class 2604 OID 16784645)
-- Name: device_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY device_type ALTER COLUMN device_type_id SET DEFAULT nextval('device_type_device_type_id_seq'::regclass);


--
-- TOC entry 3787 (class 2604 OID 16784646)
-- Name: executed_liquid_transfer_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_liquid_transfer ALTER COLUMN executed_liquid_transfer_id SET DEFAULT nextval('executed_liquid_transfer_executed_liquid_transfer_id_seq'::regclass);


--
-- TOC entry 3788 (class 2604 OID 16784647)
-- Name: executed_worklist_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_worklist ALTER COLUMN executed_worklist_id SET DEFAULT nextval('executed_worklist_executed_worklist_id_seq'::regclass);


--
-- TOC entry 3789 (class 2604 OID 16784649)
-- Name: experiment_design_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_design ALTER COLUMN experiment_design_id SET DEFAULT nextval('experiment_design_experiment_design_id_seq'::regclass);


--
-- TOC entry 3790 (class 2604 OID 16784650)
-- Name: experiment_design_rack_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_design_rack ALTER COLUMN experiment_design_rack_id SET DEFAULT nextval('experiment_design_rack_experiment_design_rack_id_seq'::regclass);


--
-- TOC entry 3792 (class 2604 OID 16784651)
-- Name: experiment_metadata_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_metadata ALTER COLUMN experiment_metadata_id SET DEFAULT nextval('experiment_metadata_experiment_metadata_id_seq'::regclass);


--
-- TOC entry 3794 (class 2604 OID 16784661)
-- Name: file_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file ALTER COLUMN file_id SET DEFAULT nextval('file_file_id_seq'::regclass);


--
-- TOC entry 3796 (class 2604 OID 16784662)
-- Name: file_set_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file_set ALTER COLUMN file_set_id SET DEFAULT nextval('file_set_file_set_id_seq'::regclass);


--
-- TOC entry 3797 (class 2604 OID 16784663)
-- Name: file_storage_site_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file_storage_site ALTER COLUMN file_storage_site_id SET DEFAULT nextval('file_storage_site_file_storage_site_id_seq'::regclass);


--
-- TOC entry 3799 (class 2604 OID 16784664)
-- Name: file_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file_type ALTER COLUMN file_type_id SET DEFAULT nextval('file_type_file_type_id_seq'::regclass);


--
-- TOC entry 3802 (class 2604 OID 16784665)
-- Name: gene_identifier_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY gene_identifier ALTER COLUMN gene_identifier_id SET DEFAULT nextval('gene_identifier_gene_identifier_id_seq'::regclass);


--
-- TOC entry 3803 (class 2604 OID 16784666)
-- Name: iso_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso ALTER COLUMN iso_id SET DEFAULT nextval('iso_iso_id_seq'::regclass);


--
-- TOC entry 3807 (class 2604 OID 16784667)
-- Name: iso_job_preparation_plate_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_job_preparation_plate ALTER COLUMN iso_job_preparation_plate_id SET DEFAULT nextval('iso_job_preparation_plate_iso_job_preparation_plate_id_seq'::regclass);


--
-- TOC entry 3808 (class 2604 OID 16784668)
-- Name: iso_plate_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_plate ALTER COLUMN iso_plate_id SET DEFAULT nextval('iso_plate_iso_plate_id_seq'::regclass);


--
-- TOC entry 3811 (class 2604 OID 16784669)
-- Name: iso_request_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso_request ALTER COLUMN iso_request_id SET DEFAULT nextval('iso_request_iso_request_id_seq'::regclass);


--
-- TOC entry 3821 (class 2604 OID 16784670)
-- Name: job_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job ALTER COLUMN job_id SET DEFAULT nextval('job_job_id_seq'::regclass);


--
-- TOC entry 3824 (class 2604 OID 16784671)
-- Name: job_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job_type ALTER COLUMN job_type_id SET DEFAULT nextval('job_type_job_type_id_seq'::regclass);


--
-- TOC entry 3826 (class 2604 OID 16784672)
-- Name: library_plate_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY library_plate ALTER COLUMN library_plate_id SET DEFAULT nextval('library_plate_library_plate_id_seq'::regclass);


--
-- TOC entry 3828 (class 2604 OID 16784673)
-- Name: liquid_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY liquid_type ALTER COLUMN liquid_type_id SET DEFAULT nextval('liquid_type_liquid_type_id_seq'::regclass);


--
-- TOC entry 3832 (class 2604 OID 16784674)
-- Name: molecule_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule ALTER COLUMN molecule_id SET DEFAULT nextval('molecule_molecule_id_seq'::regclass);


--
-- TOC entry 3833 (class 2604 OID 16784675)
-- Name: molecule_design_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule_design ALTER COLUMN molecule_design_id SET DEFAULT nextval('molecule_design_molecule_design_id_seq'::regclass);


--
-- TOC entry 3835 (class 2604 OID 16784676)
-- Name: molecule_design_library_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_library ALTER COLUMN molecule_design_library_id SET DEFAULT nextval('molecule_design_library_molecule_design_library_id_seq'::regclass);


--
-- TOC entry 3841 (class 2604 OID 16784677)
-- Name: molecule_design_pool_set_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_pool_set ALTER COLUMN molecule_design_pool_set_id SET DEFAULT nextval('molecule_design_pool_set_molecule_design_pool_set_id_seq'::regclass);


--
-- TOC entry 3842 (class 2604 OID 16784678)
-- Name: molecule_design_set_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY molecule_design_set ALTER COLUMN molecule_design_set_id SET DEFAULT nextval('molecule_design_set_molecule_design_set_id_seq'::regclass);


--
-- TOC entry 3849 (class 2604 OID 16784679)
-- Name: experiment_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY new_experiment ALTER COLUMN experiment_id SET DEFAULT nextval('new_experiment_experiment_id_seq'::regclass);


--
-- TOC entry 3850 (class 2604 OID 16784680)
-- Name: experiment_rack_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY new_experiment_rack ALTER COLUMN experiment_rack_id SET DEFAULT nextval('new_experiment_rack_experiment_rack_id_seq'::regclass);


--
-- TOC entry 3851 (class 2604 OID 16784681)
-- Name: job_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY new_job ALTER COLUMN job_id SET DEFAULT nextval('new_job_job_id_seq'::regclass);


--
-- TOC entry 3855 (class 2604 OID 16784682)
-- Name: pipetting_specs_id; Type: DEFAULT; Schema: public; Owner: berger
--

ALTER TABLE ONLY pipetting_specs ALTER COLUMN pipetting_specs_id SET DEFAULT nextval('pipetting_specs_pipetting_specs_id_seq'::regclass);


--
-- TOC entry 3860 (class 2604 OID 16784683)
-- Name: planned_liquid_transfer_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_liquid_transfer ALTER COLUMN planned_liquid_transfer_id SET DEFAULT nextval('planned_liquid_transfer_planned_liquid_transfer_id_seq'::regclass);


--
-- TOC entry 3867 (class 2604 OID 16784684)
-- Name: planned_worklist_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY planned_worklist ALTER COLUMN planned_worklist_id SET DEFAULT nextval('planned_worklist_planned_worklist_id_seq'::regclass);


--
-- TOC entry 3873 (class 2604 OID 16784685)
-- Name: project_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY project ALTER COLUMN project_id SET DEFAULT nextval('project_project_id_seq'::regclass);


--
-- TOC entry 3875 (class 2604 OID 16784686)
-- Name: rack_layout_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY rack_layout ALTER COLUMN rack_layout_id SET DEFAULT nextval('rack_layout_rack_layout_id_seq'::regclass);


--
-- TOC entry 3882 (class 2604 OID 16784687)
-- Name: rack_position_id; Type: DEFAULT; Schema: public; Owner: berger
--

ALTER TABLE ONLY rack_position ALTER COLUMN rack_position_id SET DEFAULT nextval('rack_position_rack_position_id_seq'::regclass);


--
-- TOC entry 3885 (class 2604 OID 16784688)
-- Name: rack_position_block_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_position_block ALTER COLUMN rack_position_block_id SET DEFAULT nextval('rack_position_block_rack_position_block_id_seq'::regclass);


--
-- TOC entry 3890 (class 2604 OID 16784689)
-- Name: rack_position_set_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY rack_position_set ALTER COLUMN rack_position_set_id SET DEFAULT nextval('rack_position_set_rack_position_set_id_seq'::regclass);


--
-- TOC entry 3898 (class 2604 OID 16784690)
-- Name: readout_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY readout_type ALTER COLUMN readout_type_id SET DEFAULT nextval('readout_type_readout_type_id_seq'::regclass);


--
-- TOC entry 3900 (class 2604 OID 16784691)
-- Name: release_gene_id; Type: DEFAULT; Schema: public; Owner: walsh
--

ALTER TABLE ONLY release_gene ALTER COLUMN release_gene_id SET DEFAULT nextval('release_gene_release_gene_id_seq'::regclass);


--
-- TOC entry 3902 (class 2604 OID 16784692)
-- Name: reservoir_specs_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY reservoir_specs ALTER COLUMN reservoir_specs_id SET DEFAULT nextval('reservoir_specs_reservoir_specs_id_seq'::regclass);


--
-- TOC entry 3908 (class 2604 OID 16784693)
-- Name: job_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rnai_experiment ALTER COLUMN job_id SET DEFAULT nextval('rnai_experiment_job_id_seq'::regclass);


--
-- TOC entry 3894 (class 2604 OID 16784694)
-- Name: sample_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample ALTER COLUMN sample_id SET DEFAULT nextval('sample_sample_id_seq'::regclass);


--
-- TOC entry 3917 (class 2604 OID 16784695)
-- Name: seq_identifier_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seq_identifier_type ALTER COLUMN seq_identifier_type_id SET DEFAULT nextval('seq_identifier_type_seq_identifier_type_id_seq'::regclass);


--
-- TOC entry 3918 (class 2604 OID 16784696)
-- Name: sequence_feature_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sequence_feature ALTER COLUMN sequence_feature_id SET DEFAULT nextval('sequence_feature_sequence_feature_id_seq'::regclass);


--
-- TOC entry 3870 (class 2604 OID 16784697)
-- Name: species_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY species ALTER COLUMN species_id SET DEFAULT nextval('species_species_id_seq'::regclass);


--
-- TOC entry 3925 (class 2604 OID 16784698)
-- Name: stock_rack_id; Type: DEFAULT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_rack ALTER COLUMN stock_rack_id SET DEFAULT nextval('stock_rack_stock_rack_id_seq'::regclass);


--
-- TOC entry 3941 (class 2604 OID 16784699)
-- Name: tag_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tag ALTER COLUMN tag_id SET DEFAULT nextval('tag_tag_id_seq'::regclass);


--
-- TOC entry 3942 (class 2604 OID 16784700)
-- Name: tag_domain_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tag_domain ALTER COLUMN tag_domain_id SET DEFAULT nextval('tag_domain_tag_domain_id_seq'::regclass);


--
-- TOC entry 3943 (class 2604 OID 16784701)
-- Name: tag_predicate_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tag_predicate ALTER COLUMN tag_predicate_id SET DEFAULT nextval('tag_predicate_tag_predicate_id_seq'::regclass);


--
-- TOC entry 3944 (class 2604 OID 16784702)
-- Name: tag_value_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tag_value ALTER COLUMN tag_value_id SET DEFAULT nextval('tag_value_tag_value_id_seq'::regclass);


--
-- TOC entry 3945 (class 2604 OID 16784703)
-- Name: tagged_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tagged ALTER COLUMN tagged_id SET DEFAULT nextval('tagged_tagged_id_seq'::regclass);


--
-- TOC entry 3946 (class 2604 OID 16784704)
-- Name: target_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY target ALTER COLUMN target_id SET DEFAULT nextval('target_target_id_seq'::regclass);


--
-- TOC entry 3947 (class 2604 OID 16784705)
-- Name: target_set_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY target_set ALTER COLUMN target_set_id SET DEFAULT nextval('target_set_target_set_id_seq'::regclass);


--
-- TOC entry 3948 (class 2604 OID 16784706)
-- Name: task_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task ALTER COLUMN task_id SET DEFAULT nextval('task_task_id_seq'::regclass);


--
-- TOC entry 3950 (class 2604 OID 16784707)
-- Name: task_type_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_type ALTER COLUMN task_type_id SET DEFAULT nextval('task_type_task_type_id_seq'::regclass);


--
-- TOC entry 3951 (class 2604 OID 16784708)
-- Name: transcript_identifier_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY transcript_identifier ALTER COLUMN transcript_identifier_id SET DEFAULT nextval('transcript_identifier_transcript_identifier_id_seq'::regclass);


--
-- TOC entry 3952 (class 2604 OID 16784709)
-- Name: tube_transfer_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer ALTER COLUMN tube_transfer_id SET DEFAULT nextval('tube_transfer_tube_transfer_id_seq'::regclass);


--
-- TOC entry 3954 (class 2604 OID 16784710)
-- Name: tube_transfer_worklist_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer_worklist ALTER COLUMN tube_transfer_worklist_id SET DEFAULT nextval('tube_transfer_worklist_tube_transfer_worklist_id_seq'::regclass);


--
-- TOC entry 3955 (class 2604 OID 16784711)
-- Name: user_preferences_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY user_preferences ALTER COLUMN user_preferences_id SET DEFAULT nextval('user_preferences_user_preferences_id_seq'::regclass);


--
-- TOC entry 3956 (class 2604 OID 16784712)
-- Name: worklist_series_id; Type: DEFAULT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series ALTER COLUMN worklist_series_id SET DEFAULT nextval('worklist_series_worklist_series_id_seq'::regclass);


--
-- TOC entry 3959 (class 2606 OID 16856594)
-- Name: _user_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY _user_messages
    ADD CONSTRAINT _user_messages_pkey PRIMARY KEY (guid);


--
-- TOC entry 3961 (class 2606 OID 16856602)
-- Name: acquisition_task_item_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY acquisition_task_item
    ADD CONSTRAINT acquisition_task_item_pkey PRIMARY KEY (task_item_id);


--
-- TOC entry 4452 (class 2606 OID 16856604)
-- Name: ambion_barcode_plate_id_unique; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY supplier_barcode
    ADD CONSTRAINT ambion_barcode_plate_id_unique UNIQUE (rack_id);


--
-- TOC entry 5655 (class 0 OID 0)
-- Dependencies: 4452
-- Name: CONSTRAINT ambion_barcode_plate_id_unique ON supplier_barcode; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT ambion_barcode_plate_id_unique ON supplier_barcode IS 'Historical name.  Consider renaming to supplier_barcode_rack_id_key';


--
-- TOC entry 3967 (class 2606 OID 16856606)
-- Name: annotation_accession_accession_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation_accession
    ADD CONSTRAINT annotation_accession_accession_key UNIQUE (accession);


--
-- TOC entry 3969 (class 2606 OID 16856608)
-- Name: annotation_accession_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation_accession
    ADD CONSTRAINT annotation_accession_pkey PRIMARY KEY (annotation_id, accession);


--
-- TOC entry 3963 (class 2606 OID 16856610)
-- Name: annotation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation
    ADD CONSTRAINT annotation_pkey PRIMARY KEY (annotation_id);


--
-- TOC entry 3971 (class 2606 OID 16856612)
-- Name: annotation_relationship_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation_relationship
    ADD CONSTRAINT annotation_relationship_pkey PRIMARY KEY (parent_annotation_id, child_annotation_id);


--
-- TOC entry 3973 (class 2606 OID 16856614)
-- Name: annotation_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation_type
    ADD CONSTRAINT annotation_type_pkey PRIMARY KEY (annotation_type_id);


--
-- TOC entry 3979 (class 2606 OID 16856616)
-- Name: barcoded_location_device_id_index_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY barcoded_location
    ADD CONSTRAINT barcoded_location_device_id_index_key UNIQUE (device_id, index);


--
-- TOC entry 3981 (class 2606 OID 16856618)
-- Name: barcoded_location_device_id_label_unique; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY barcoded_location
    ADD CONSTRAINT barcoded_location_device_id_label_unique UNIQUE (device_id, label);


--
-- TOC entry 3983 (class 2606 OID 16856620)
-- Name: barcoded_location_id; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY barcoded_location
    ADD CONSTRAINT barcoded_location_id PRIMARY KEY (barcoded_location_id);


--
-- TOC entry 3985 (class 2606 OID 16856622)
-- Name: barcoded_location_name_unique; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY barcoded_location
    ADD CONSTRAINT barcoded_location_name_unique UNIQUE (name);


--
-- TOC entry 4334 (class 2606 OID 16856624)
-- Name: carrier_barcoded_location_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_barcoded_location
    ADD CONSTRAINT carrier_barcoded_location_pkey PRIMARY KEY (rack_id);


--
-- TOC entry 4340 (class 2606 OID 16856626)
-- Name: carrier_mask_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_mask
    ADD CONSTRAINT carrier_mask_label_key UNIQUE (label);


--
-- TOC entry 4342 (class 2606 OID 16856628)
-- Name: carrier_mask_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_mask
    ADD CONSTRAINT carrier_mask_name_key UNIQUE (name);


--
-- TOC entry 4346 (class 2606 OID 16856630)
-- Name: carrier_mask_position_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_mask_position
    ADD CONSTRAINT carrier_mask_position_pkey PRIMARY KEY (rack_mask_id, "row", col);


--
-- TOC entry 4367 (class 2606 OID 16856632)
-- Name: carrier_specs_container_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_specs_container_specs
    ADD CONSTRAINT carrier_specs_container_specs_pkey PRIMARY KEY (rack_specs_id, container_specs_id);


--
-- TOC entry 4021 (class 2606 OID 16856634)
-- Name: carrier_specs_label_uq; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_specs
    ADD CONSTRAINT carrier_specs_label_uq UNIQUE (label);


--
-- TOC entry 4023 (class 2606 OID 16856636)
-- Name: carrier_specs_name_uq; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_specs
    ADD CONSTRAINT carrier_specs_name_uq UNIQUE (name);


--
-- TOC entry 3989 (class 2606 OID 16856638)
-- Name: cell_line_identifier_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cell_line
    ADD CONSTRAINT cell_line_identifier_key UNIQUE (identifier);


--
-- TOC entry 3991 (class 2606 OID 16856640)
-- Name: cell_line_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cell_line
    ADD CONSTRAINT cell_line_pkey PRIMARY KEY (cell_line_id);


--
-- TOC entry 3994 (class 2606 OID 16856642)
-- Name: chemical_structure_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY chemical_structure
    ADD CONSTRAINT chemical_structure_pkey PRIMARY KEY (chemical_structure_id);


--
-- TOC entry 3996 (class 2606 OID 16856644)
-- Name: chromosome_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY chromosome
    ADD CONSTRAINT chromosome_pkey PRIMARY KEY (chromosome_id);


--
-- TOC entry 3998 (class 2606 OID 16856646)
-- Name: chromosome_species_id_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY chromosome
    ADD CONSTRAINT chromosome_species_id_name_key UNIQUE (species_id, name);


--
-- TOC entry 4535 (class 2606 OID 16859049)
-- Name: compound_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY compound
    ADD CONSTRAINT compound_pkey PRIMARY KEY (molecule_design_id);


--
-- TOC entry 4537 (class 2606 OID 16859051)
-- Name: compound_smiles_key; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY compound
    ADD CONSTRAINT compound_smiles_key UNIQUE (smiles);


--
-- TOC entry 4007 (class 2606 OID 16856648)
-- Name: container_barcode_barcode_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY container_barcode
    ADD CONSTRAINT container_barcode_barcode_key UNIQUE (barcode);


--
-- TOC entry 4009 (class 2606 OID 16856650)
-- Name: container_barcode_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY container_barcode
    ADD CONSTRAINT container_barcode_pkey PRIMARY KEY (container_id);


--
-- TOC entry 4004 (class 2606 OID 16856653)
-- Name: container_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY container
    ADD CONSTRAINT container_pkey PRIMARY KEY (container_id);


--
-- TOC entry 4027 (class 2606 OID 16856655)
-- Name: container_specs_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY container_specs
    ADD CONSTRAINT container_specs_label_key UNIQUE (label);


--
-- TOC entry 4029 (class 2606 OID 16856657)
-- Name: container_specs_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY container_specs
    ADD CONSTRAINT container_specs_name_key UNIQUE (name);


--
-- TOC entry 4031 (class 2606 OID 16856659)
-- Name: container_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY container_specs
    ADD CONSTRAINT container_specs_pkey PRIMARY KEY (container_specs_id);


--
-- TOC entry 4011 (class 2606 OID 16856665)
-- Name: containment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY containment
    ADD CONSTRAINT containment_pkey PRIMARY KEY (held_id);


--
-- TOC entry 4034 (class 2606 OID 16856667)
-- Name: current_db_release_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY current_db_release
    ADD CONSTRAINT current_db_release_pkey PRIMARY KEY (db_source_id);


--
-- TOC entry 4046 (class 2606 OID 16856669)
-- Name: db_group_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_group
    ADD CONSTRAINT db_group_login_key UNIQUE (login);


--
-- TOC entry 4048 (class 2606 OID 16856671)
-- Name: db_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_group
    ADD CONSTRAINT db_group_pkey PRIMARY KEY (db_group_id);


--
-- TOC entry 4050 (class 2606 OID 16856673)
-- Name: db_group_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_group_users
    ADD CONSTRAINT db_group_users_pkey PRIMARY KEY (db_group_id, db_user_id);


--
-- TOC entry 4036 (class 2606 OID 16856675)
-- Name: db_release_db_source_id; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_release
    ADD CONSTRAINT db_release_db_source_id UNIQUE (db_release_id, db_source_id);


--
-- TOC entry 4038 (class 2606 OID 16856677)
-- Name: db_release_db_source_id_version_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_release
    ADD CONSTRAINT db_release_db_source_id_version_key UNIQUE (db_source_id, version);


--
-- TOC entry 4393 (class 2606 OID 16856679)
-- Name: db_release_gene_id_key; Type: CONSTRAINT; Schema: public; Owner: walsh; Tablespace: 
--

ALTER TABLE ONLY release_gene
    ADD CONSTRAINT db_release_gene_id_key UNIQUE (db_release_id, gene_id);


--
-- TOC entry 4040 (class 2606 OID 16856681)
-- Name: db_release_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_release
    ADD CONSTRAINT db_release_pkey PRIMARY KEY (db_release_id);


--
-- TOC entry 4042 (class 2606 OID 16856683)
-- Name: db_source_db_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_source
    ADD CONSTRAINT db_source_db_name_key UNIQUE (db_name);


--
-- TOC entry 4044 (class 2606 OID 16856685)
-- Name: db_source_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_source
    ADD CONSTRAINT db_source_pkey PRIMARY KEY (db_source_id);


--
-- TOC entry 3975 (class 2606 OID 16856687)
-- Name: db_source_type_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation_type
    ADD CONSTRAINT db_source_type_key UNIQUE (db_source_id, type);


--
-- TOC entry 4052 (class 2606 OID 16856691)
-- Name: db_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_user
    ADD CONSTRAINT db_user_pkey PRIMARY KEY (db_user_id);


--
-- TOC entry 4062 (class 2606 OID 16856693)
-- Name: device_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY device
    ADD CONSTRAINT device_name_key UNIQUE (name);


--
-- TOC entry 4064 (class 2606 OID 16856695)
-- Name: device_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY device
    ADD CONSTRAINT device_pkey PRIMARY KEY (device_id);


--
-- TOC entry 4066 (class 2606 OID 16856697)
-- Name: device_type_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY device_type
    ADD CONSTRAINT device_type_label_key UNIQUE (label);


--
-- TOC entry 4068 (class 2606 OID 16856699)
-- Name: device_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY device_type
    ADD CONSTRAINT device_type_name_key UNIQUE (name);


--
-- TOC entry 4070 (class 2606 OID 16856701)
-- Name: device_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY device_type
    ADD CONSTRAINT device_type_pkey PRIMARY KEY (device_type_id);


--
-- TOC entry 4072 (class 2606 OID 16856703)
-- Name: dilution_job_step_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY dilution_job_step
    ADD CONSTRAINT dilution_job_step_pkey PRIMARY KEY (job_step_id);


--
-- TOC entry 4074 (class 2606 OID 16856705)
-- Name: double_stranded_intended_target_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY double_stranded_intended_target
    ADD CONSTRAINT double_stranded_intended_target_pkey PRIMARY KEY (molecule_design_id, versioned_transcript_id);


--
-- TOC entry 4076 (class 2606 OID 16856707)
-- Name: evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY evidence
    ADD CONSTRAINT evidence_pkey PRIMARY KEY (release_gene2annotation_id, evidence);


--
-- TOC entry 4082 (class 2606 OID 16856709)
-- Name: executed_container_dilution_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY executed_sample_dilution
    ADD CONSTRAINT executed_container_dilution_pkey PRIMARY KEY (executed_liquid_transfer_id);


--
-- TOC entry 4084 (class 2606 OID 16856711)
-- Name: executed_container_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY executed_sample_transfer
    ADD CONSTRAINT executed_container_transfer_pkey PRIMARY KEY (executed_liquid_transfer_id);


--
-- TOC entry 4080 (class 2606 OID 16856713)
-- Name: executed_rack_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY executed_rack_sample_transfer
    ADD CONSTRAINT executed_rack_transfer_pkey PRIMARY KEY (executed_liquid_transfer_id);


--
-- TOC entry 4078 (class 2606 OID 16856715)
-- Name: executed_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY executed_liquid_transfer
    ADD CONSTRAINT executed_transfer_pkey PRIMARY KEY (executed_liquid_transfer_id);


--
-- TOC entry 4088 (class 2606 OID 16856717)
-- Name: executed_worklist_member_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY executed_worklist_member
    ADD CONSTRAINT executed_worklist_member_pkey PRIMARY KEY (executed_worklist_id, executed_liquid_transfer_id);


--
-- TOC entry 4086 (class 2606 OID 16856719)
-- Name: executed_worklist_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY executed_worklist
    ADD CONSTRAINT executed_worklist_pkey PRIMARY KEY (executed_worklist_id);


--
-- TOC entry 4090 (class 2606 OID 16856721)
-- Name: experiment_design_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY experiment_design
    ADD CONSTRAINT experiment_design_pkey PRIMARY KEY (experiment_design_id);


--
-- TOC entry 4092 (class 2606 OID 16856723)
-- Name: experiment_design_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY experiment_design_rack
    ADD CONSTRAINT experiment_design_rack_pkey PRIMARY KEY (experiment_design_rack_id);


--
-- TOC entry 4102 (class 2606 OID 16856725)
-- Name: experiment_metadata_iso_request_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY experiment_metadata_iso_request
    ADD CONSTRAINT experiment_metadata_iso_request_pkey PRIMARY KEY (experiment_metadata_id);


--
-- TOC entry 4096 (class 2606 OID 16856727)
-- Name: experiment_metadata_label_key; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY experiment_metadata
    ADD CONSTRAINT experiment_metadata_label_key UNIQUE (label);


--
-- TOC entry 4104 (class 2606 OID 16856729)
-- Name: experiment_metadata_molecule_design_set_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY experiment_metadata_molecule_design_set
    ADD CONSTRAINT experiment_metadata_molecule_design_set_pkey PRIMARY KEY (experiment_metadata_id);


--
-- TOC entry 4098 (class 2606 OID 16856731)
-- Name: experiment_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY experiment_metadata
    ADD CONSTRAINT experiment_metadata_pkey PRIMARY KEY (experiment_metadata_id);


--
-- TOC entry 4106 (class 2606 OID 16856733)
-- Name: experiment_metadata_target_set_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY experiment_metadata_target_set
    ADD CONSTRAINT experiment_metadata_target_set_pkey PRIMARY KEY (experiment_metadata_id);


--
-- TOC entry 4100 (class 2606 OID 16856735)
-- Name: experiment_metadata_ticket_number_key; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY experiment_metadata
    ADD CONSTRAINT experiment_metadata_ticket_number_key UNIQUE (ticket_number);


--
-- TOC entry 4108 (class 2606 OID 16856737)
-- Name: experiment_metadata_type_pkey; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY experiment_metadata_type
    ADD CONSTRAINT experiment_metadata_type_pkey PRIMARY KEY (experiment_metadata_type_id);


--
-- TOC entry 4110 (class 2606 OID 16856745)
-- Name: experiment_source_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY experiment_source_rack
    ADD CONSTRAINT experiment_source_rack_pkey PRIMARY KEY (experiment_id);


--
-- TOC entry 4112 (class 2606 OID 16856803)
-- Name: external_primer_carrier_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY external_primer_carrier
    ADD CONSTRAINT external_primer_carrier_pkey PRIMARY KEY (carrier_id);


--
-- TOC entry 4114 (class 2606 OID 16856805)
-- Name: file_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_pkey PRIMARY KEY (file_id);


--
-- TOC entry 4118 (class 2606 OID 16856808)
-- Name: file_set_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY file_set_files
    ADD CONSTRAINT file_set_files_pkey PRIMARY KEY (file_id, file_set_id);


--
-- TOC entry 4116 (class 2606 OID 16856811)
-- Name: file_set_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY file_set
    ADD CONSTRAINT file_set_pkey PRIMARY KEY (file_set_id);


--
-- TOC entry 4124 (class 2606 OID 16856813)
-- Name: file_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY file_type
    ADD CONSTRAINT file_type_pkey PRIMARY KEY (file_type_id);


--
-- TOC entry 4133 (class 2606 OID 16856815)
-- Name: gene2annotation_gene_id_annotation_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY gene2annotation
    ADD CONSTRAINT gene2annotation_gene_id_annotation_id_key UNIQUE (gene_id, annotation_id);


--
-- TOC entry 4135 (class 2606 OID 16856817)
-- Name: gene2annotation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY gene2annotation
    ADD CONSTRAINT gene2annotation_pkey PRIMARY KEY (gene2annotation_id);


--
-- TOC entry 4126 (class 2606 OID 16856819)
-- Name: gene_accession_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY gene
    ADD CONSTRAINT gene_accession_key UNIQUE (accession);


--
-- TOC entry 4000 (class 2606 OID 16856821)
-- Name: gene_feature_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY chromosome_gene_feature
    ADD CONSTRAINT gene_feature_pkey PRIMARY KEY (gene_id, sequence_feature_id);


--
-- TOC entry 4137 (class 2606 OID 16856823)
-- Name: gene_identifier_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY gene_identifier
    ADD CONSTRAINT gene_identifier_pkey PRIMARY KEY (gene_identifier_id);


--
-- TOC entry 4129 (class 2606 OID 16856825)
-- Name: gene_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY gene
    ADD CONSTRAINT gene_pkey PRIMARY KEY (gene_id);


--
-- TOC entry 4131 (class 2606 OID 16856827)
-- Name: gene_species_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY gene
    ADD CONSTRAINT gene_species_key UNIQUE (gene_id, species_id);


--
-- TOC entry 4139 (class 2606 OID 16856829)
-- Name: image_analysis_task_item_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY image_analysis_task_item
    ADD CONSTRAINT image_analysis_task_item_pkey PRIMARY KEY (task_item_id);


--
-- TOC entry 4141 (class 2606 OID 16856831)
-- Name: intended_mirna_target_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY intended_mirna_target
    ADD CONSTRAINT intended_mirna_target_pkey PRIMARY KEY (molecule_design_id, accession);


--
-- TOC entry 4143 (class 2606 OID 16856833)
-- Name: intended_target_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY intended_target
    ADD CONSTRAINT intended_target_pkey PRIMARY KEY (molecule_design_id, versioned_transcript_id);


--
-- TOC entry 4171 (class 2606 OID 16856835)
-- Name: internal_sample_order_racks_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY iso_racks
    ADD CONSTRAINT internal_sample_order_racks_pkey PRIMARY KEY (iso_id);


--
-- TOC entry 4147 (class 2606 OID 16856837)
-- Name: iso_aliquot_plate_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_aliquot_plate
    ADD CONSTRAINT iso_aliquot_plate_pkey PRIMARY KEY (iso_plate_id);


--
-- TOC entry 4149 (class 2606 OID 16856839)
-- Name: iso_job_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_job
    ADD CONSTRAINT iso_job_pkey PRIMARY KEY (job_id);


--
-- TOC entry 4153 (class 2606 OID 16856841)
-- Name: iso_job_preparation_plate_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_job_preparation_plate
    ADD CONSTRAINT iso_job_preparation_plate_pkey PRIMARY KEY (iso_job_preparation_plate_id);


--
-- TOC entry 4157 (class 2606 OID 16856843)
-- Name: iso_job_stock_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_job_stock_rack
    ADD CONSTRAINT iso_job_stock_rack_pkey PRIMARY KEY (stock_rack_id);


--
-- TOC entry 4155 (class 2606 OID 16856845)
-- Name: iso_job_unique_preparation_plate; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_job_preparation_plate
    ADD CONSTRAINT iso_job_unique_preparation_plate UNIQUE (rack_id);


--
-- TOC entry 4201 (class 2606 OID 16856847)
-- Name: iso_library_plate_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY lab_iso_library_plate
    ADD CONSTRAINT iso_library_plate_pkey PRIMARY KEY (library_plate_id);


--
-- TOC entry 4159 (class 2606 OID 16856849)
-- Name: iso_molecule_design_set_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_molecule_design_set
    ADD CONSTRAINT iso_molecule_design_set_pkey PRIMARY KEY (iso_id);


--
-- TOC entry 4145 (class 2606 OID 16856851)
-- Name: iso_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY iso
    ADD CONSTRAINT iso_pkey PRIMARY KEY (iso_id);


--
-- TOC entry 4161 (class 2606 OID 16856853)
-- Name: iso_plate_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_plate
    ADD CONSTRAINT iso_plate_pkey PRIMARY KEY (iso_plate_id);


--
-- TOC entry 4163 (class 2606 OID 16856855)
-- Name: iso_plate_unique_rack; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_plate
    ADD CONSTRAINT iso_plate_unique_rack UNIQUE (rack_id);


--
-- TOC entry 4165 (class 2606 OID 16856857)
-- Name: iso_pool_set_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_pool_set
    ADD CONSTRAINT iso_pool_set_pkey PRIMARY KEY (iso_id);


--
-- TOC entry 4169 (class 2606 OID 16856859)
-- Name: iso_preparation_plate_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_preparation_plate
    ADD CONSTRAINT iso_preparation_plate_pkey PRIMARY KEY (iso_plate_id);


--
-- TOC entry 4173 (class 2606 OID 16856861)
-- Name: iso_request_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY iso_request
    ADD CONSTRAINT iso_request_pkey PRIMARY KEY (iso_request_id);


--
-- TOC entry 4175 (class 2606 OID 16856863)
-- Name: iso_request_pool_set_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_request_pool_set
    ADD CONSTRAINT iso_request_pool_set_pkey PRIMARY KEY (iso_request_id);


--
-- TOC entry 4177 (class 2606 OID 16856865)
-- Name: iso_request_unique_pool_set; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_request_pool_set
    ADD CONSTRAINT iso_request_unique_pool_set UNIQUE (molecule_design_pool_set_id);


--
-- TOC entry 4179 (class 2606 OID 16856867)
-- Name: iso_sector_preparation_plate_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_sector_preparation_plate
    ADD CONSTRAINT iso_sector_preparation_plate_pkey PRIMARY KEY (iso_plate_id);


--
-- TOC entry 4181 (class 2606 OID 16856869)
-- Name: iso_sector_stock_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_sector_stock_rack
    ADD CONSTRAINT iso_sector_stock_rack_pkey PRIMARY KEY (stock_rack_id);


--
-- TOC entry 4183 (class 2606 OID 16856871)
-- Name: iso_stock_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_stock_rack
    ADD CONSTRAINT iso_stock_rack_pkey PRIMARY KEY (stock_rack_id);


--
-- TOC entry 4185 (class 2606 OID 16856873)
-- Name: item_status_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY item_status
    ADD CONSTRAINT item_status_name_key UNIQUE (name);


--
-- TOC entry 4187 (class 2606 OID 16856875)
-- Name: item_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY item_status
    ADD CONSTRAINT item_status_pkey PRIMARY KEY (item_status_id);


--
-- TOC entry 4189 (class 2606 OID 16856877)
-- Name: job_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY job
    ADD CONSTRAINT job_pkey PRIMARY KEY (job_id);


--
-- TOC entry 4193 (class 2606 OID 16856879)
-- Name: job_step_job_id_xml_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY job_step
    ADD CONSTRAINT job_step_job_id_xml_id_key UNIQUE (job_id, xml_id);


--
-- TOC entry 4195 (class 2606 OID 16856881)
-- Name: job_step_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY job_step
    ADD CONSTRAINT job_step_type_pkey PRIMARY KEY (job_step_id);


--
-- TOC entry 4197 (class 2606 OID 16856883)
-- Name: job_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY job_type
    ADD CONSTRAINT job_type_name_key UNIQUE (name);


--
-- TOC entry 4199 (class 2606 OID 16856885)
-- Name: job_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY job_type
    ADD CONSTRAINT job_type_pkey PRIMARY KEY (job_type_id);


--
-- TOC entry 4203 (class 2606 OID 16856887)
-- Name: lab_iso_request_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY lab_iso_request
    ADD CONSTRAINT lab_iso_request_pkey PRIMARY KEY (iso_request_id);


--
-- TOC entry 4205 (class 2606 OID 16856889)
-- Name: legacy_primer_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY legacy_primer_pair
    ADD CONSTRAINT legacy_primer_pair_pkey PRIMARY KEY (legacy_id);


--
-- TOC entry 4207 (class 2606 OID 16856891)
-- Name: library_plate_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY library_plate
    ADD CONSTRAINT library_plate_pkey PRIMARY KEY (library_plate_id);


--
-- TOC entry 4209 (class 2606 OID 16856893)
-- Name: liquid_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY liquid_type
    ADD CONSTRAINT liquid_type_name_key UNIQUE (name);


--
-- TOC entry 4211 (class 2606 OID 16856895)
-- Name: liquid_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY liquid_type
    ADD CONSTRAINT liquid_type_pkey PRIMARY KEY (liquid_type_id);


--
-- TOC entry 4213 (class 2606 OID 16856897)
-- Name: mirna_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY mirna
    ADD CONSTRAINT mirna_pkey PRIMARY KEY (accession);


--
-- TOC entry 4225 (class 2606 OID 16856899)
-- Name: molecule_design_gene_pkey; Type: CONSTRAINT; Schema: public; Owner: cebos; Tablespace: 
--

ALTER TABLE ONLY molecule_design_gene
    ADD CONSTRAINT molecule_design_gene_pkey PRIMARY KEY (molecule_design_id, gene_id);


--
-- TOC entry 4244 (class 2606 OID 16856901)
-- Name: molecule_design_library_iso_request_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_library_creation_iso_request
    ADD CONSTRAINT molecule_design_library_iso_request_pkey PRIMARY KEY (molecule_design_library_id);


--
-- TOC entry 4246 (class 2606 OID 16856903)
-- Name: molecule_design_library_lab_iso_request_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_library_lab_iso_request
    ADD CONSTRAINT molecule_design_library_lab_iso_request_pkey PRIMARY KEY (iso_request_id);


--
-- TOC entry 4240 (class 2606 OID 16856905)
-- Name: molecule_design_library_label_key; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_library
    ADD CONSTRAINT molecule_design_library_label_key UNIQUE (label);


--
-- TOC entry 4242 (class 2606 OID 16856907)
-- Name: molecule_design_library_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_library
    ADD CONSTRAINT molecule_design_library_pkey PRIMARY KEY (molecule_design_library_id);


--
-- TOC entry 4248 (class 2606 OID 16856909)
-- Name: molecule_design_mirna_target_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY molecule_design_mirna_target
    ADD CONSTRAINT molecule_design_mirna_target_pkey PRIMARY KEY (molecule_design_id, accession);


--
-- TOC entry 4219 (class 2606 OID 16856911)
-- Name: molecule_design_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY molecule_design
    ADD CONSTRAINT molecule_design_pkey PRIMARY KEY (molecule_design_id);


--
-- TOC entry 4262 (class 2606 OID 16856913)
-- Name: molecule_design_set_gene_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_set_gene
    ADD CONSTRAINT molecule_design_set_gene_pkey PRIMARY KEY (molecule_design_set_id, gene_id);


--
-- TOC entry 4265 (class 2606 OID 16856915)
-- Name: molecule_design_set_member_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY molecule_design_set_member
    ADD CONSTRAINT molecule_design_set_member_pkey PRIMARY KEY (molecule_design_set_id, molecule_design_id);


--
-- TOC entry 4258 (class 2606 OID 16856917)
-- Name: molecule_design_set_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY molecule_design_set
    ADD CONSTRAINT molecule_design_set_pkey PRIMARY KEY (molecule_design_set_id);


--
-- TOC entry 4267 (class 2606 OID 16856919)
-- Name: molecule_design_set_target_set_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY molecule_design_set_target_set
    ADD CONSTRAINT molecule_design_set_target_set_pkey PRIMARY KEY (molecule_design_set_id, target_set_id);


--
-- TOC entry 4271 (class 2606 OID 16859090)
-- Name: molecule_design_structure_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_structure
    ADD CONSTRAINT molecule_design_structure_pkey PRIMARY KEY (molecule_design_id, chemical_structure_id);


--
-- TOC entry 4227 (class 2606 OID 16856923)
-- Name: molecule_design_versioned_transcript_target_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY molecule_design_versioned_transcript_target
    ADD CONSTRAINT molecule_design_versioned_transcript_target_pkey PRIMARY KEY (molecule_design_id, versioned_transcript_id);


--
-- TOC entry 4216 (class 2606 OID 16856927)
-- Name: molecule_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY molecule
    ADD CONSTRAINT molecule_pkey PRIMARY KEY (molecule_id);


--
-- TOC entry 4273 (class 2606 OID 16856929)
-- Name: molecule_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY molecule_type
    ADD CONSTRAINT molecule_type_name_key UNIQUE (name);


--
-- TOC entry 4275 (class 2606 OID 16856931)
-- Name: molecule_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY molecule_type
    ADD CONSTRAINT molecule_type_pkey PRIMARY KEY (molecule_type_id);


--
-- TOC entry 3965 (class 2606 OID 16856933)
-- Name: name_annotation_type_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation
    ADD CONSTRAINT name_annotation_type_key UNIQUE (annotation_type_id, name);


--
-- TOC entry 4277 (class 2606 OID 16856935)
-- Name: new_experiment_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY new_experiment
    ADD CONSTRAINT new_experiment_pkey PRIMARY KEY (experiment_id);


--
-- TOC entry 4279 (class 2606 OID 16856937)
-- Name: new_experiment_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY new_experiment_rack
    ADD CONSTRAINT new_experiment_rack_pkey PRIMARY KEY (experiment_rack_id);


--
-- TOC entry 4120 (class 2606 OID 16856939)
-- Name: new_file_storage_site_path_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY file_storage_site
    ADD CONSTRAINT new_file_storage_site_path_key UNIQUE (path);


--
-- TOC entry 4122 (class 2606 OID 16856941)
-- Name: new_file_storage_site_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY file_storage_site
    ADD CONSTRAINT new_file_storage_site_pkey PRIMARY KEY (file_storage_site_id);


--
-- TOC entry 4281 (class 2606 OID 16856943)
-- Name: new_job_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY new_job
    ADD CONSTRAINT new_job_pkey PRIMARY KEY (job_id);


--
-- TOC entry 4428 (class 2606 OID 16856945)
-- Name: new_sequence_feature_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sequence_feature
    ADD CONSTRAINT new_sequence_feature_pkey PRIMARY KEY (sequence_feature_id);


--
-- TOC entry 4283 (class 2606 OID 16856947)
-- Name: oligo_order_plate_set_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY order_sample_set
    ADD CONSTRAINT oligo_order_plate_set_pkey PRIMARY KEY (sample_set_id);


--
-- TOC entry 4285 (class 2606 OID 16856951)
-- Name: organization_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY organization
    ADD CONSTRAINT organization_pkey PRIMARY KEY (organization_id);


--
-- TOC entry 4289 (class 2606 OID 16856953)
-- Name: pipetting_specs_name_key; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY pipetting_specs
    ADD CONSTRAINT pipetting_specs_name_key UNIQUE (name);


--
-- TOC entry 4291 (class 2606 OID 16856955)
-- Name: pipetting_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY pipetting_specs
    ADD CONSTRAINT pipetting_specs_pkey PRIMARY KEY (pipetting_specs_id);


--
-- TOC entry 4293 (class 2606 OID 16856957)
-- Name: planned_liquid_transfer_hash_value_key; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY planned_liquid_transfer
    ADD CONSTRAINT planned_liquid_transfer_hash_value_key UNIQUE (hash_value);


--
-- TOC entry 4295 (class 2606 OID 16856959)
-- Name: planned_liquid_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY planned_liquid_transfer
    ADD CONSTRAINT planned_liquid_transfer_pkey PRIMARY KEY (planned_liquid_transfer_id);


--
-- TOC entry 4299 (class 2606 OID 16856961)
-- Name: planned_worklist_member_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY planned_worklist_member
    ADD CONSTRAINT planned_worklist_member_pkey PRIMARY KEY (planned_worklist_id, planned_liquid_transfer_id);


--
-- TOC entry 4297 (class 2606 OID 16856963)
-- Name: planned_worklist_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY planned_worklist
    ADD CONSTRAINT planned_worklist_pkey PRIMARY KEY (planned_worklist_id);


--
-- TOC entry 4256 (class 2606 OID 16856965)
-- Name: pool_set_member_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_pool_set_member
    ADD CONSTRAINT pool_set_member_pkey PRIMARY KEY (molecule_design_pool_set_id, molecule_design_pool_id);


--
-- TOC entry 4254 (class 2606 OID 16856967)
-- Name: pool_set_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_pool_set
    ADD CONSTRAINT pool_set_pkey PRIMARY KEY (molecule_design_pool_set_id);


--
-- TOC entry 4302 (class 2606 OID 16856969)
-- Name: pooled_supplier_molecule_design_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY pooled_supplier_molecule_design
    ADD CONSTRAINT pooled_supplier_molecule_design_pkey PRIMARY KEY (supplier_molecule_design_id);


--
-- TOC entry 4304 (class 2606 OID 16856971)
-- Name: primer_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY primer_pair
    ADD CONSTRAINT primer_pair_pkey PRIMARY KEY (primer_pair_id);


--
-- TOC entry 4306 (class 2606 OID 16856973)
-- Name: primer_pair_primer_1_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY primer_pair
    ADD CONSTRAINT primer_pair_primer_1_id_key UNIQUE (primer_1_id, primer_2_id);


--
-- TOC entry 4324 (class 2606 OID 16856975)
-- Name: primer_validation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY primer_validation
    ADD CONSTRAINT primer_validation_pkey PRIMARY KEY (primer_pair_id, cell_line_id, project_id);


--
-- TOC entry 4326 (class 2606 OID 16856977)
-- Name: printer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY printer
    ADD CONSTRAINT printer_pkey PRIMARY KEY (device_id);


--
-- TOC entry 4328 (class 2606 OID 16856979)
-- Name: printer_queue_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY printer
    ADD CONSTRAINT printer_queue_name_key UNIQUE (queue_name);


--
-- TOC entry 4330 (class 2606 OID 16856981)
-- Name: project_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY project
    ADD CONSTRAINT project_label_key UNIQUE (label);


--
-- TOC entry 4446 (class 2606 OID 16856983)
-- Name: project_pass_file_storage_site_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY subproject
    ADD CONSTRAINT project_pass_file_storage_site_id_key UNIQUE (file_storage_site_id);


--
-- TOC entry 4332 (class 2606 OID 16856987)
-- Name: project_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY project
    ADD CONSTRAINT project_pkey PRIMARY KEY (project_id);


--
-- TOC entry 4338 (class 2606 OID 16856991)
-- Name: rack_layout_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY rack_layout
    ADD CONSTRAINT rack_layout_pkey PRIMARY KEY (rack_layout_id);


--
-- TOC entry 4344 (class 2606 OID 16856993)
-- Name: rack_mask_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_mask
    ADD CONSTRAINT rack_mask_pkey PRIMARY KEY (rack_mask_id);


--
-- TOC entry 4017 (class 2606 OID 16856995)
-- Name: rack_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack
    ADD CONSTRAINT rack_pkey PRIMARY KEY (rack_id);


--
-- TOC entry 4354 (class 2606 OID 16856997)
-- Name: rack_position_block_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_position_block
    ADD CONSTRAINT rack_position_block_pkey PRIMARY KEY (rack_position_block_id);


--
-- TOC entry 4348 (class 2606 OID 16856999)
-- Name: rack_position_pkey1; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY rack_position
    ADD CONSTRAINT rack_position_pkey1 PRIMARY KEY (rack_position_id);


--
-- TOC entry 4359 (class 2606 OID 16857001)
-- Name: rack_position_set_member_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY rack_position_set_member
    ADD CONSTRAINT rack_position_set_member_pkey PRIMARY KEY (rack_position_set_id, rack_position_id);


--
-- TOC entry 4357 (class 2606 OID 16857003)
-- Name: rack_position_set_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY rack_position_set
    ADD CONSTRAINT rack_position_set_pkey PRIMARY KEY (rack_position_set_id);


--
-- TOC entry 4361 (class 2606 OID 16857005)
-- Name: rack_shape_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_shape
    ADD CONSTRAINT rack_shape_label_key UNIQUE (label);


--
-- TOC entry 4363 (class 2606 OID 16857009)
-- Name: rack_shape_name_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_shape
    ADD CONSTRAINT rack_shape_name_pkey PRIMARY KEY (rack_shape_name);


--
-- TOC entry 4365 (class 2606 OID 16857011)
-- Name: rack_shape_number_rows_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_shape
    ADD CONSTRAINT rack_shape_number_rows_key UNIQUE (number_rows, number_columns);


--
-- TOC entry 4025 (class 2606 OID 16857013)
-- Name: rack_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack_specs
    ADD CONSTRAINT rack_specs_pkey PRIMARY KEY (rack_specs_id);


--
-- TOC entry 4376 (class 2606 OID 16857015)
-- Name: readout_task_item_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY readout_task_item
    ADD CONSTRAINT readout_task_item_pkey PRIMARY KEY (task_item_id);


--
-- TOC entry 4378 (class 2606 OID 16857017)
-- Name: readout_type_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY readout_type
    ADD CONSTRAINT readout_type_label_key UNIQUE (label);


--
-- TOC entry 4380 (class 2606 OID 16857019)
-- Name: readout_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY readout_type
    ADD CONSTRAINT readout_type_name_key UNIQUE (name);


--
-- TOC entry 4382 (class 2606 OID 16857021)
-- Name: readout_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY readout_type
    ADD CONSTRAINT readout_type_pkey PRIMARY KEY (readout_type_id);


--
-- TOC entry 4385 (class 2606 OID 16857023)
-- Name: rearrayed_containers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rearrayed_containers
    ADD CONSTRAINT rearrayed_containers_pkey PRIMARY KEY (source_container_id, destination_container_id, destination_sample_set_id);


--
-- TOC entry 4389 (class 2606 OID 16857027)
-- Name: refseq_gene_pkey; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY refseq_gene
    ADD CONSTRAINT refseq_gene_pkey PRIMARY KEY (gene_id);


--
-- TOC entry 4391 (class 2606 OID 16857029)
-- Name: refseq_update_species_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY refseq_update_species
    ADD CONSTRAINT refseq_update_species_pkey PRIMARY KEY (species_id);


--
-- TOC entry 4397 (class 2606 OID 16857031)
-- Name: release_gene2annotation_db_release_id_gene2annotation_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY release_gene2annotation
    ADD CONSTRAINT release_gene2annotation_db_release_id_gene2annotation_id_key UNIQUE (db_release_id, gene2annotation_id);


--
-- TOC entry 4399 (class 2606 OID 16857033)
-- Name: release_gene2annotation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY release_gene2annotation
    ADD CONSTRAINT release_gene2annotation_pkey PRIMARY KEY (release_gene2annotation_id);


--
-- TOC entry 4395 (class 2606 OID 16857035)
-- Name: release_gene_pkey; Type: CONSTRAINT; Schema: public; Owner: walsh; Tablespace: 
--

ALTER TABLE ONLY release_gene
    ADD CONSTRAINT release_gene_pkey PRIMARY KEY (release_gene_id);


--
-- TOC entry 4230 (class 2606 OID 16857037)
-- Name: release_gene_transcript_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY release_gene_transcript
    ADD CONSTRAINT release_gene_transcript_pkey PRIMARY KEY (transcript_id, db_release_id);


--
-- TOC entry 4232 (class 2606 OID 16857039)
-- Name: release_versioned_transcript_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY release_versioned_transcript
    ADD CONSTRAINT release_versioned_transcript_pkey PRIMARY KEY (db_release_id, versioned_transcript_id);


--
-- TOC entry 4401 (class 2606 OID 16857041)
-- Name: replaced_gene_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY replaced_gene
    ADD CONSTRAINT replaced_gene_pkey PRIMARY KEY (replaced_gene_id, replacement_gene_id);


--
-- TOC entry 4403 (class 2606 OID 16857043)
-- Name: replaced_transcript_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY replaced_transcript
    ADD CONSTRAINT replaced_transcript_pkey PRIMARY KEY (replaced_transcript_id, replacement_transcript_id, db_release_id);


--
-- TOC entry 4492 (class 2606 OID 16857045)
-- Name: report_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY task_report
    ADD CONSTRAINT report_pkey PRIMARY KEY (subproject_id, task_type_id);


--
-- TOC entry 4405 (class 2606 OID 16857047)
-- Name: reservoir_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY reservoir_specs
    ADD CONSTRAINT reservoir_specs_pkey PRIMARY KEY (reservoir_specs_id);


--
-- TOC entry 4407 (class 2606 OID 16857049)
-- Name: rnai_experiment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rnai_experiment
    ADD CONSTRAINT rnai_experiment_pkey PRIMARY KEY (job_id);


--
-- TOC entry 4409 (class 2606 OID 16857051)
-- Name: sample_cells_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_cells
    ADD CONSTRAINT sample_cells_pkey PRIMARY KEY (sample_id, cell_line_id);


--
-- TOC entry 4411 (class 2606 OID 16857055)
-- Name: sample_creation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_registration
    ADD CONSTRAINT sample_creation_pkey PRIMARY KEY (sample_id);


--
-- TOC entry 4374 (class 2606 OID 16857057)
-- Name: sample_molecule_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_molecule
    ADD CONSTRAINT sample_molecule_pkey PRIMARY KEY (sample_id, molecule_id);


--
-- TOC entry 4370 (class 2606 OID 16857059)
-- Name: sample_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample
    ADD CONSTRAINT sample_pkey PRIMARY KEY (sample_id);


--
-- TOC entry 4413 (class 2606 OID 16857061)
-- Name: sample_set_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_set
    ADD CONSTRAINT sample_set_label_key UNIQUE (label);


--
-- TOC entry 4415 (class 2606 OID 16857063)
-- Name: sample_set_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_set
    ADD CONSTRAINT sample_set_pkey PRIMARY KEY (sample_set_id);


--
-- TOC entry 4417 (class 2606 OID 16857065)
-- Name: sample_set_sample_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_set_sample
    ADD CONSTRAINT sample_set_sample_pkey PRIMARY KEY (sample_set_id, sample_id);


--
-- TOC entry 4420 (class 2606 OID 16857067)
-- Name: sample_set_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_set_type
    ADD CONSTRAINT sample_set_type_name_key UNIQUE (name);


--
-- TOC entry 4422 (class 2606 OID 16857069)
-- Name: sample_set_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY sample_set_type
    ADD CONSTRAINT sample_set_type_pkey PRIMARY KEY (sample_set_type_id);


--
-- TOC entry 4424 (class 2606 OID 16857071)
-- Name: seq_identifier_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY seq_identifier_type
    ADD CONSTRAINT seq_identifier_type_name_key UNIQUE (name);


--
-- TOC entry 4426 (class 2606 OID 16857073)
-- Name: seq_identifier_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY seq_identifier_type
    ADD CONSTRAINT seq_identifier_type_pkey PRIMARY KEY (seq_identifier_type_id);


--
-- TOC entry 4431 (class 2606 OID 16857075)
-- Name: single_supplier_molecule_design_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY single_supplier_molecule_design
    ADD CONSTRAINT single_supplier_molecule_design_pkey PRIMARY KEY (supplier_molecule_design_id);


--
-- TOC entry 4308 (class 2606 OID 16857077)
-- Name: species_acronym_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY species
    ADD CONSTRAINT species_acronym_key UNIQUE (acronym);


--
-- TOC entry 4310 (class 2606 OID 16857079)
-- Name: species_common_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY species
    ADD CONSTRAINT species_common_name_key UNIQUE (common_name);


--
-- TOC entry 4312 (class 2606 OID 16857081)
-- Name: species_genus_name_species_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY species
    ADD CONSTRAINT species_genus_name_species_name_key UNIQUE (genus_name, species_name);


--
-- TOC entry 4314 (class 2606 OID 16857083)
-- Name: species_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY species
    ADD CONSTRAINT species_pkey PRIMARY KEY (species_id);


--
-- TOC entry 4433 (class 2606 OID 16857085)
-- Name: status_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY status_type
    ADD CONSTRAINT status_type_name_key UNIQUE (name);


--
-- TOC entry 4435 (class 2606 OID 16857087)
-- Name: status_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY status_type
    ADD CONSTRAINT status_type_pkey PRIMARY KEY (status_type_id);


--
-- TOC entry 4437 (class 2606 OID 16857089)
-- Name: stock_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY stock_rack
    ADD CONSTRAINT stock_rack_pkey PRIMARY KEY (stock_rack_id);


--
-- TOC entry 4442 (class 2606 OID 16857091)
-- Name: stock_sample_creation_iso_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY stock_sample_creation_iso
    ADD CONSTRAINT stock_sample_creation_iso_pkey PRIMARY KEY (iso_id);


--
-- TOC entry 4444 (class 2606 OID 16857093)
-- Name: stock_sample_creation_iso_request_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY stock_sample_creation_iso_request
    ADD CONSTRAINT stock_sample_creation_iso_request_pkey PRIMARY KEY (iso_request_id);


--
-- TOC entry 4250 (class 2606 OID 16857095)
-- Name: stock_sample_molecule_design_set_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_pool
    ADD CONSTRAINT stock_sample_molecule_design_set_pkey PRIMARY KEY (molecule_design_set_id);


--
-- TOC entry 4440 (class 2606 OID 16857097)
-- Name: stock_sample_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY stock_sample
    ADD CONSTRAINT stock_sample_pkey PRIMARY KEY (sample_id);


--
-- TOC entry 4448 (class 2606 OID 16857101)
-- Name: subproject_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY subproject
    ADD CONSTRAINT subproject_pkey PRIMARY KEY (subproject_id);


--
-- TOC entry 4454 (class 2606 OID 16857103)
-- Name: supplier_barcode_supplier_barcode_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY supplier_barcode
    ADD CONSTRAINT supplier_barcode_supplier_barcode_key UNIQUE (supplier_id, supplier_barcode);


--
-- TOC entry 4456 (class 2606 OID 16857105)
-- Name: supplier_molecule_design_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY supplier_molecule_design
    ADD CONSTRAINT supplier_molecule_design_pkey PRIMARY KEY (supplier_molecule_design_id);


--
-- TOC entry 4460 (class 2606 OID 16857109)
-- Name: tag_domain_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tag_domain
    ADD CONSTRAINT tag_domain_pkey PRIMARY KEY (tag_domain_id);


--
-- TOC entry 4458 (class 2606 OID 16857111)
-- Name: tag_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tag
    ADD CONSTRAINT tag_pkey PRIMARY KEY (tag_id);


--
-- TOC entry 4464 (class 2606 OID 16857113)
-- Name: tag_predicate_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tag_predicate
    ADD CONSTRAINT tag_predicate_pkey PRIMARY KEY (tag_predicate_id);


--
-- TOC entry 4468 (class 2606 OID 16857117)
-- Name: tag_value_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tag_value
    ADD CONSTRAINT tag_value_pkey PRIMARY KEY (tag_value_id);


--
-- TOC entry 4472 (class 2606 OID 16857121)
-- Name: tagged_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tagged
    ADD CONSTRAINT tagged_pkey PRIMARY KEY (tagged_id);


--
-- TOC entry 4474 (class 2606 OID 16857123)
-- Name: tagging_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tagging
    ADD CONSTRAINT tagging_pkey PRIMARY KEY (tagged_id, tag_id);


--
-- TOC entry 4476 (class 2606 OID 16857125)
-- Name: target_molecule_design_id_key; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY target
    ADD CONSTRAINT target_molecule_design_id_key UNIQUE (molecule_design_id, transcript_id);


--
-- TOC entry 4478 (class 2606 OID 16857127)
-- Name: target_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY target
    ADD CONSTRAINT target_pkey PRIMARY KEY (target_id);


--
-- TOC entry 4482 (class 2606 OID 16857129)
-- Name: target_set_member_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY target_set_member
    ADD CONSTRAINT target_set_member_pkey PRIMARY KEY (target_set_id);


--
-- TOC entry 4480 (class 2606 OID 16857131)
-- Name: target_set_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY target_set
    ADD CONSTRAINT target_set_pkey PRIMARY KEY (target_set_id);


--
-- TOC entry 4488 (class 2606 OID 16857133)
-- Name: task_item_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY task_item
    ADD CONSTRAINT task_item_pkey PRIMARY KEY (task_item_id);


--
-- TOC entry 4485 (class 2606 OID 16857135)
-- Name: task_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY task
    ADD CONSTRAINT task_pkey PRIMARY KEY (task_id);


--
-- TOC entry 4494 (class 2606 OID 16857137)
-- Name: task_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY task_type
    ADD CONSTRAINT task_type_name_key UNIQUE (name);


--
-- TOC entry 4496 (class 2606 OID 16857139)
-- Name: task_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY task_type
    ADD CONSTRAINT task_type_pkey PRIMARY KEY (task_type_id);


--
-- TOC entry 4316 (class 2606 OID 16857141)
-- Name: transcript_accession_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY transcript
    ADD CONSTRAINT transcript_accession_key UNIQUE (accession);


--
-- TOC entry 4002 (class 2606 OID 16857143)
-- Name: transcript_feature_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY chromosome_transcript_feature
    ADD CONSTRAINT transcript_feature_pkey PRIMARY KEY (transcript_id, sequence_feature_id);


--
-- TOC entry 4498 (class 2606 OID 16857145)
-- Name: transcript_gene_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY transcript_gene
    ADD CONSTRAINT transcript_gene_pkey PRIMARY KEY (transcript_id);


--
-- TOC entry 4501 (class 2606 OID 16857147)
-- Name: transcript_identifier_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY transcript_identifier
    ADD CONSTRAINT transcript_identifier_pkey PRIMARY KEY (transcript_identifier_id);


--
-- TOC entry 4318 (class 2606 OID 16857149)
-- Name: transcript_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY transcript
    ADD CONSTRAINT transcript_pkey PRIMARY KEY (transcript_id);


--
-- TOC entry 4320 (class 2606 OID 16857151)
-- Name: transcript_species_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY transcript
    ADD CONSTRAINT transcript_species_key UNIQUE (transcript_id, species_id);


--
-- TOC entry 4503 (class 2606 OID 16857153)
-- Name: transfection_job_step_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY transfection_job_step
    ADD CONSTRAINT transfection_job_step_pkey PRIMARY KEY (job_step_id);


--
-- TOC entry 4505 (class 2606 OID 16857155)
-- Name: transfer_type_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY transfer_type
    ADD CONSTRAINT transfer_type_pkey PRIMARY KEY (name);


--
-- TOC entry 4507 (class 2606 OID 16857157)
-- Name: tube_transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tube_transfer
    ADD CONSTRAINT tube_transfer_pkey PRIMARY KEY (tube_transfer_id);


--
-- TOC entry 4511 (class 2606 OID 16857159)
-- Name: tube_transfer_worklist_member_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tube_transfer_worklist_member
    ADD CONSTRAINT tube_transfer_worklist_member_pkey PRIMARY KEY (tube_transfer_worklist_id, tube_transfer_id);


--
-- TOC entry 4509 (class 2606 OID 16857161)
-- Name: tube_transfer_worklist_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tube_transfer_worklist
    ADD CONSTRAINT tube_transfer_worklist_pkey PRIMARY KEY (tube_transfer_worklist_id);


--
-- TOC entry 3977 (class 2606 OID 16857163)
-- Name: type_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY annotation_type
    ADD CONSTRAINT type_key UNIQUE (type);


--
-- TOC entry 4151 (class 2606 OID 16857165)
-- Name: unique_iso_job_iso; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY iso_job_member
    ADD CONSTRAINT unique_iso_job_iso UNIQUE (iso_id);


--
-- TOC entry 4167 (class 2606 OID 16857167)
-- Name: unique_iso_pool_set_iso; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY iso_pool_set
    ADD CONSTRAINT unique_iso_pool_set_iso UNIQUE (iso_id);


--
-- TOC entry 4094 (class 2606 OID 16857169)
-- Name: unique_label_per_experiment_design; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY experiment_design_rack
    ADD CONSTRAINT unique_label_per_experiment_design UNIQUE (experiment_design_id, label);


--
-- TOC entry 4531 (class 2606 OID 16857175)
-- Name: unique_planned_worklist; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_member
    ADD CONSTRAINT unique_planned_worklist UNIQUE (planned_worklist_id);


--
-- TOC entry 3987 (class 2606 OID 16859084)
-- Name: uq_barcoded_location_barcode; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY barcoded_location
    ADD CONSTRAINT uq_barcoded_location_barcode UNIQUE (barcode);


--
-- TOC entry 4014 (class 2606 OID 16859086)
-- Name: uq_containment_holder_id_row_col; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY containment
    ADD CONSTRAINT uq_containment_holder_id_row_col UNIQUE (holder_id, "row", col);


--
-- TOC entry 4054 (class 2606 OID 16859080)
-- Name: uq_db_user_email_addr; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_user
    ADD CONSTRAINT uq_db_user_email_addr UNIQUE (email_addr);


--
-- TOC entry 4056 (class 2606 OID 16859078)
-- Name: uq_db_user_login; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_user
    ADD CONSTRAINT uq_db_user_login UNIQUE (login);


--
-- TOC entry 4058 (class 2606 OID 16859076)
-- Name: uq_db_user_username; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_user
    ADD CONSTRAINT uq_db_user_username UNIQUE (username);


--
-- TOC entry 4060 (class 2606 OID 16859082)
-- Name: uq_directory_user_id; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY db_user
    ADD CONSTRAINT uq_directory_user_id UNIQUE (directory_user_id);


--
-- TOC entry 4252 (class 2606 OID 16857173)
-- Name: uq_molecule_design_pool_structure_hash; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY molecule_design_pool
    ADD CONSTRAINT uq_molecule_design_pool_structure_hash UNIQUE (member_hash);


--
-- TOC entry 4221 (class 2606 OID 16857099)
-- Name: uq_molecule_design_structure_hash; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY molecule_design
    ADD CONSTRAINT uq_molecule_design_structure_hash UNIQUE (structure_hash);


--
-- TOC entry 4287 (class 2606 OID 16856949)
-- Name: uq_organization_name; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY organization
    ADD CONSTRAINT uq_organization_name UNIQUE (name);


--
-- TOC entry 4019 (class 2606 OID 16859095)
-- Name: uq_rack_barcode; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY rack
    ADD CONSTRAINT uq_rack_barcode UNIQUE (barcode);


--
-- TOC entry 4350 (class 2606 OID 16857181)
-- Name: uq_rack_position_label; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY rack_position
    ADD CONSTRAINT uq_rack_position_label UNIQUE (label);


--
-- TOC entry 4352 (class 2606 OID 16857179)
-- Name: uq_rack_position_row_index_column_index; Type: CONSTRAINT; Schema: public; Owner: berger; Tablespace: 
--

ALTER TABLE ONLY rack_position
    ADD CONSTRAINT uq_rack_position_row_index_column_index UNIQUE (row_index, column_index);


--
-- TOC entry 4450 (class 2606 OID 16856985)
-- Name: uq_subproject_project_id_label; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY subproject
    ADD CONSTRAINT uq_subproject_project_id_label UNIQUE (project_id, label);


--
-- TOC entry 4462 (class 2606 OID 16857107)
-- Name: uq_tag_domain_domain; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tag_domain
    ADD CONSTRAINT uq_tag_domain_domain UNIQUE (domain);


--
-- TOC entry 4466 (class 2606 OID 16857115)
-- Name: uq_tag_predicate_predicate; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tag_predicate
    ADD CONSTRAINT uq_tag_predicate_predicate UNIQUE (predicate);


--
-- TOC entry 4470 (class 2606 OID 16857119)
-- Name: uq_tag_value_value; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY tag_value
    ADD CONSTRAINT uq_tag_value_value UNIQUE (value);


--
-- TOC entry 4517 (class 2606 OID 16857185)
-- Name: uq_worklist_series_experiment_design_experiment_design_id; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_experiment_design
    ADD CONSTRAINT uq_worklist_series_experiment_design_experiment_design_id UNIQUE (experiment_design_id);


--
-- TOC entry 4521 (class 2606 OID 16857187)
-- Name: uq_worklist_series_experiment_design_rack_experiment_design_rac; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_experiment_design_rack
    ADD CONSTRAINT uq_worklist_series_experiment_design_rack_experiment_design_rac UNIQUE (experiment_design_rack_id);


--
-- TOC entry 4527 (class 2606 OID 16857189)
-- Name: uq_worlist_series_iso_request_iso_request_id; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_iso_request
    ADD CONSTRAINT uq_worlist_series_iso_request_iso_request_id UNIQUE (iso_request_id);


--
-- TOC entry 4513 (class 2606 OID 16857191)
-- Name: user_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY user_preferences
    ADD CONSTRAINT user_preferences_pkey PRIMARY KEY (user_preferences_id);


--
-- TOC entry 4234 (class 2606 OID 16857193)
-- Name: version_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY versioned_transcript
    ADD CONSTRAINT version_key UNIQUE (transcript_id, version);


--
-- TOC entry 4322 (class 2606 OID 16857195)
-- Name: versioned_transcript_amplicon_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY versioned_transcript_amplicon
    ADD CONSTRAINT versioned_transcript_amplicon_key UNIQUE (versioned_transcript_id, primer_pair_id, left_primer_start, right_primer_start);


--
-- TOC entry 4236 (class 2606 OID 16857197)
-- Name: versioned_transcript_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY versioned_transcript
    ADD CONSTRAINT versioned_transcript_pkey PRIMARY KEY (versioned_transcript_id);


--
-- TOC entry 4519 (class 2606 OID 16857199)
-- Name: worklist_series_experiment_design_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_experiment_design
    ADD CONSTRAINT worklist_series_experiment_design_pkey PRIMARY KEY (worklist_series_id, experiment_design_id);


--
-- TOC entry 4523 (class 2606 OID 16857201)
-- Name: worklist_series_experiment_design_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_experiment_design_rack
    ADD CONSTRAINT worklist_series_experiment_design_rack_pkey PRIMARY KEY (worklist_series_id, experiment_design_rack_id);


--
-- TOC entry 4525 (class 2606 OID 16857203)
-- Name: worklist_series_iso_job_pkey; Type: CONSTRAINT; Schema: public; Owner: gathmann; Tablespace: 
--

ALTER TABLE ONLY worklist_series_iso_job
    ADD CONSTRAINT worklist_series_iso_job_pkey PRIMARY KEY (job_id);


--
-- TOC entry 4529 (class 2606 OID 16857205)
-- Name: worklist_series_iso_request_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_iso_request
    ADD CONSTRAINT worklist_series_iso_request_pkey PRIMARY KEY (worklist_series_id, iso_request_id);


--
-- TOC entry 4533 (class 2606 OID 16857207)
-- Name: worklist_series_member_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series_member
    ADD CONSTRAINT worklist_series_member_pkey PRIMARY KEY (worklist_series_id, planned_worklist_id);


--
-- TOC entry 4515 (class 2606 OID 16857209)
-- Name: worklist_series_pkey; Type: CONSTRAINT; Schema: public; Owner: thelma; Tablespace: 
--

ALTER TABLE ONLY worklist_series
    ADD CONSTRAINT worklist_series_pkey PRIMARY KEY (worklist_series_id);


--
-- TOC entry 3992 (class 1259 OID 16857210)
-- Name: chemical_structure_md5_rpr; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE UNIQUE INDEX chemical_structure_md5_rpr ON chemical_structure USING btree (structure_type, md5((representation)::text));


--
-- TOC entry 4032 (class 1259 OID 16857213)
-- Name: current_db_release_db_release_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX current_db_release_db_release_id_idx ON current_db_release USING btree (db_release_id);


--
-- TOC entry 4127 (class 1259 OID 16857214)
-- Name: gene_locus_name_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX gene_locus_name_idx ON gene USING btree (locus_name);


--
-- TOC entry 4012 (class 1259 OID 16857212)
-- Name: ix_containment_holder_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_containment_holder_id ON containment USING btree (holder_id);


--
-- TOC entry 4222 (class 1259 OID 16857215)
-- Name: ix_molecule_design_gene_gene_id; Type: INDEX; Schema: public; Owner: cebos; Tablespace: 
--

CREATE INDEX ix_molecule_design_gene_gene_id ON molecule_design_gene USING btree (gene_id);


--
-- TOC entry 4223 (class 1259 OID 16857216)
-- Name: ix_molecule_design_gene_molecule_design_id; Type: INDEX; Schema: public; Owner: cebos; Tablespace: 
--

CREATE INDEX ix_molecule_design_gene_molecule_design_id ON molecule_design_gene USING btree (molecule_design_id);


--
-- TOC entry 4217 (class 1259 OID 16857219)
-- Name: ix_molecule_design_molecule_type; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_molecule_design_molecule_type ON molecule_design USING btree (molecule_type);


--
-- TOC entry 4259 (class 1259 OID 16857220)
-- Name: ix_molecule_design_set_gene_gene_id; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE INDEX ix_molecule_design_set_gene_gene_id ON molecule_design_set_gene USING btree (gene_id);


--
-- TOC entry 4260 (class 1259 OID 16857221)
-- Name: ix_molecule_design_set_gene_molecule_design_set_id; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE INDEX ix_molecule_design_set_gene_molecule_design_set_id ON molecule_design_set_gene USING btree (molecule_design_set_id);


--
-- TOC entry 4263 (class 1259 OID 16857222)
-- Name: ix_molecule_design_set_member_molecule_design_id; Type: INDEX; Schema: public; Owner: thelma; Tablespace: 
--

CREATE INDEX ix_molecule_design_set_member_molecule_design_id ON molecule_design_set_member USING btree (molecule_design_id);


--
-- TOC entry 4268 (class 1259 OID 16857223)
-- Name: ix_molecule_design_structure_chemical_structure_id; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE INDEX ix_molecule_design_structure_chemical_structure_id ON molecule_design_structure USING btree (chemical_structure_id);


--
-- TOC entry 4269 (class 1259 OID 16857225)
-- Name: ix_molecule_design_structure_molecule_design_id; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE INDEX ix_molecule_design_structure_molecule_design_id ON molecule_design_structure USING btree (molecule_design_id);


--
-- TOC entry 4214 (class 1259 OID 16857226)
-- Name: ix_molecule_molecule_design_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_molecule_molecule_design_id ON molecule USING btree (molecule_design_id);


--
-- TOC entry 4300 (class 1259 OID 16857227)
-- Name: ix_pooled_supplier_molecule_design_molecule_design_set_id; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE INDEX ix_pooled_supplier_molecule_design_molecule_design_set_id ON pooled_supplier_molecule_design USING btree (molecule_design_set_id);


--
-- TOC entry 4015 (class 1259 OID 16857228)
-- Name: ix_rack_barcode; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_rack_barcode ON rack USING btree (barcode);


--
-- TOC entry 4335 (class 1259 OID 16859096)
-- Name: ix_rack_barcoded_location_barcoded_location_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX ix_rack_barcoded_location_barcoded_location_id ON rack_barcoded_location USING btree (barcoded_location_id);


--
-- TOC entry 4355 (class 1259 OID 16859097)
-- Name: ix_rack_position_set_hash_value; Type: INDEX; Schema: public; Owner: thelma; Tablespace: 
--

CREATE UNIQUE INDEX ix_rack_position_set_hash_value ON rack_position_set USING btree (hash_value);


--
-- TOC entry 4386 (class 1259 OID 16859128)
-- Name: ix_refseq_gene_accession; Type: INDEX; Schema: public; Owner: berger; Tablespace: 
--

CREATE UNIQUE INDEX ix_refseq_gene_accession ON refseq_gene USING btree (accession);


--
-- TOC entry 4387 (class 1259 OID 16859129)
-- Name: ix_refseq_gene_locus_name; Type: INDEX; Schema: public; Owner: berger; Tablespace: 
--

CREATE INDEX ix_refseq_gene_locus_name ON refseq_gene USING btree (locus_name);


--
-- TOC entry 4368 (class 1259 OID 16857236)
-- Name: ix_sample_container_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX ix_sample_container_id ON sample USING btree (container_id);


--
-- TOC entry 5656 (class 0 OID 0)
-- Dependencies: 4368
-- Name: INDEX ix_sample_container_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON INDEX ix_sample_container_id IS 'This index improves the retrieval of sample info for containers';


--
-- TOC entry 4371 (class 1259 OID 16857237)
-- Name: ix_sample_molecule_molecule_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_sample_molecule_molecule_id ON sample_molecule USING btree (molecule_id);


--
-- TOC entry 4372 (class 1259 OID 16857240)
-- Name: ix_sample_molecule_sample_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_sample_molecule_sample_id ON sample_molecule USING btree (sample_id);


--
-- TOC entry 4429 (class 1259 OID 16857242)
-- Name: ix_single_supplier_molecule_design_molecule_design_id; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE INDEX ix_single_supplier_molecule_design_molecule_design_id ON single_supplier_molecule_design USING btree (molecule_design_id);


--
-- TOC entry 4438 (class 1259 OID 16857245)
-- Name: ix_stock_sample_molecule_type; Type: INDEX; Schema: public; Owner: gathmann; Tablespace: 
--

CREATE INDEX ix_stock_sample_molecule_type ON stock_sample USING btree (molecule_type);


--
-- TOC entry 4191 (class 1259 OID 16857217)
-- Name: job_step_job_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX job_step_job_id_idx ON job_step USING btree (job_id);


--
-- TOC entry 4190 (class 1259 OID 16857218)
-- Name: job_subproject_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX job_subproject_id_idx ON job USING btree (subproject_id);


--
-- TOC entry 4336 (class 1259 OID 16857230)
-- Name: rack_barcoded_location_log_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX rack_barcoded_location_log_idx ON rack_barcoded_location_log USING btree (rack_id, barcoded_location_id);


--
-- TOC entry 4383 (class 1259 OID 16857233)
-- Name: rearrayed_containers_destination_sample_set_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX rearrayed_containers_destination_sample_set_id_idx ON rearrayed_containers USING btree (destination_sample_set_id);


--
-- TOC entry 4228 (class 1259 OID 16857235)
-- Name: release_gene_transcript_gene_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX release_gene_transcript_gene_id_idx ON release_gene_transcript USING btree (gene_id);


--
-- TOC entry 4418 (class 1259 OID 16857241)
-- Name: sample_set_sample_sample_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX sample_set_sample_sample_id_idx ON sample_set_sample USING btree (sample_id);


--
-- TOC entry 4005 (class 1259 OID 16857243)
-- Name: stock_container_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX stock_container_idx ON container USING btree (container_id) WHERE (((item_status)::text = 'MANAGED'::text) AND (container_specs_id = 8));


--
-- TOC entry 5657 (class 0 OID 0)
-- Dependencies: 4005
-- Name: INDEX stock_container_idx; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON INDEX stock_container_idx IS 'This index improves significantly the retrieval of stock containers';


--
-- TOC entry 4486 (class 1259 OID 16857246)
-- Name: task_item_item_set_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX task_item_item_set_id_idx ON task_item USING btree (item_set_id);


--
-- TOC entry 4489 (class 1259 OID 16857247)
-- Name: task_item_rack_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX task_item_rack_id_idx ON task_item USING btree (rack_id);


--
-- TOC entry 4490 (class 1259 OID 16857248)
-- Name: task_item_task_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX task_item_task_id_idx ON task_item USING btree (task_id);


--
-- TOC entry 4483 (class 1259 OID 16857249)
-- Name: task_job_step_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX task_job_step_id_idx ON task USING btree (job_step_id);


--
-- TOC entry 4499 (class 1259 OID 16857250)
-- Name: transcript_identifier_name_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX transcript_identifier_name_idx ON transcript_identifier USING btree (name);


--
-- TOC entry 4237 (class 1259 OID 16857251)
-- Name: versioned_transcript_sequence_md5; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX versioned_transcript_sequence_md5 ON versioned_transcript USING btree (md5((sequence)::text));


--
-- TOC entry 4238 (class 1259 OID 16857252)
-- Name: versioned_transcript_transcript_id_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX versioned_transcript_transcript_id_idx ON versioned_transcript USING btree (transcript_id);


--
-- TOC entry 4961 (class 2618 OID 16857253)
-- Name: _RETURN; Type: RULE; Schema: public; Owner: gathmann
--

CREATE RULE "_RETURN" AS ON SELECT TO stock_info_view DO INSTEAD SELECT ((('ssmds'::text || ssmds.molecule_design_set_id) || 'c'::text) || COALESCE((ss.concentration * ((1000000)::numeric)::double precision), (0)::double precision)) AS stock_info_id, ssmds.molecule_design_set_id, ssmds.molecule_type AS molecule_type_id, COALESCE(ss.concentration, (0)::double precision) AS concentration, COALESCE(count(c.container_id), (0)::bigint) AS total_tubes, COALESCE(sum(s.volume), (0)::double precision) AS total_volume, COALESCE(min(s.volume), (0)::double precision) AS minimum_volume, COALESCE(max(s.volume), (0)::double precision) AS maximum_volume FROM (((molecule_design_pool ssmds LEFT JOIN stock_sample ss ON ((ss.molecule_design_set_id = ssmds.molecule_design_set_id))) LEFT JOIN sample s ON ((s.sample_id = ss.sample_id))) LEFT JOIN container c ON ((c.container_id = s.container_id))) WHERE ((c.item_status IS NULL) OR ((c.item_status)::text = 'MANAGED'::text)) GROUP BY ssmds.molecule_design_set_id, ss.concentration;


--
-- TOC entry 4962 (class 2618 OID 16857255)
-- Name: humane_rack_insert; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE humane_rack_insert AS ON INSERT TO humane_rack DO INSTEAD INSERT INTO rack (barcode, rack_specs_id, item_status) VALUES (new.barcode, (SELECT rack_specs.rack_specs_id FROM rack_specs WHERE ((rack_specs.name)::text = (new.rack_specs_name)::text)), new.item_status);


--
-- TOC entry 4963 (class 2618 OID 16857256)
-- Name: racked_molecule_sample_insert; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE racked_molecule_sample_insert AS ON INSERT TO racked_molecule_sample DO INSTEAD SELECT insert_racked_molecule_sample(new.container_specs_name, new.item_status, new.container_barcode, new.rack_barcode, new."row", new.col, new.volume, new.molecule_design_id, new.concentration) AS insert_racked_molecule_sample;


--
-- TOC entry 4964 (class 2618 OID 16857257)
-- Name: racked_sample_insert; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE racked_sample_insert AS ON INSERT TO racked_sample DO INSTEAD SELECT insert_racked_sample(new.container_specs_name, new.item_status, new.container_barcode, new.rack_barcode, new."row", new.col, new.volume) AS insert_racked_sample;


--
-- TOC entry 4965 (class 2618 OID 16857258)
-- Name: racked_tube_insert; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE racked_tube_insert AS ON INSERT TO racked_tube DO INSTEAD SELECT insert_racked_tube(new.container_specs_name, new.item_status, new.container_barcode, new.rack_barcode, new."row", new.col) AS insert_racked_tube;


--
-- TOC entry 4840 (class 2620 OID 16857259)
-- Name: refresh_table_molecule_design_gene; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER refresh_table_molecule_design_gene AFTER INSERT OR DELETE OR UPDATE ON molecule_design_versioned_transcript_target FOR EACH STATEMENT EXECUTE PROCEDURE refresh_table_molecule_design_gene();


--
-- TOC entry 5658 (class 0 OID 0)
-- Dependencies: 4840
-- Name: TRIGGER refresh_table_molecule_design_gene ON molecule_design_versioned_transcript_target; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TRIGGER refresh_table_molecule_design_gene ON molecule_design_versioned_transcript_target IS 'A trigger to update the molecule_design_gene materialized view on insert, delete or update operations';


--
-- TOC entry 4839 (class 2620 OID 16857260)
-- Name: refresh_table_refseq_gene; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER refresh_table_refseq_gene AFTER UPDATE ON current_db_release FOR EACH STATEMENT EXECUTE PROCEDURE refresh_table_refseq_gene();


--
-- TOC entry 5659 (class 0 OID 0)
-- Dependencies: 4839
-- Name: TRIGGER refresh_table_refseq_gene ON current_db_release; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TRIGGER refresh_table_refseq_gene ON current_db_release IS 'A trigger to update the refseq_gene materialized view on update operations on the current_db_release table.';


--
-- TOC entry 4837 (class 2620 OID 16857261)
-- Name: set_container_type; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER set_container_type BEFORE INSERT ON container FOR EACH ROW EXECUTE PROCEDURE set_container_type();


--
-- TOC entry 5660 (class 0 OID 0)
-- Dependencies: 4837
-- Name: TRIGGER set_container_type ON container; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TRIGGER set_container_type ON container IS 'A trigger to set the container type before an INSERT of a row into the container table.';


--
-- TOC entry 4838 (class 2620 OID 16857262)
-- Name: set_rack_type; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER set_rack_type AFTER INSERT ON rack FOR EACH STATEMENT EXECUTE PROCEDURE set_rack_type();


--
-- TOC entry 5661 (class 0 OID 0)
-- Dependencies: 4838
-- Name: TRIGGER set_rack_type ON rack; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TRIGGER set_rack_type ON rack IS 'A trigger to set the rack type on INSERTs into the rack table.';


--
-- TOC entry 4747 (class 2606 OID 16857263)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY readout_task_item
    ADD CONSTRAINT "$1" FOREIGN KEY (file_set_id) REFERENCES file_set(file_set_id);


--
-- TOC entry 5662 (class 0 OID 0)
-- Dependencies: 4747
-- Name: CONSTRAINT "$1" ON readout_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$1" ON readout_task_item IS 'Consider renaming to file_set_id.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4615 (class 2606 OID 16857268)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY image_analysis_task_item
    ADD CONSTRAINT "$1" FOREIGN KEY (image_file_set_id) REFERENCES file_set(file_set_id);


--
-- TOC entry 5663 (class 0 OID 0)
-- Dependencies: 4615
-- Name: CONSTRAINT "$1" ON image_analysis_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$1" ON image_analysis_task_item IS 'Consider renaming to image_file_set_id.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4749 (class 2606 OID 16857273)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rearrayed_containers
    ADD CONSTRAINT "$1" FOREIGN KEY (source_container_id) REFERENCES container(container_id);


--
-- TOC entry 5664 (class 0 OID 0)
-- Dependencies: 4749
-- Name: CONSTRAINT "$1" ON rearrayed_containers; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$1" ON rearrayed_containers IS 'Consider renaming to source_container_id.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4606 (class 2606 OID 16857278)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file
    ADD CONSTRAINT "$1" FOREIGN KEY (file_storage_site_id) REFERENCES file_storage_site(file_storage_site_id);


--
-- TOC entry 5665 (class 0 OID 0)
-- Dependencies: 4606
-- Name: CONSTRAINT "$1" ON file; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$1" ON file IS 'Consider renaming to file_storage_site_id

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4538 (class 2606 OID 16857283)
-- Name: $1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY acquisition_task_item
    ADD CONSTRAINT "$1" FOREIGN KEY (file_storage_site_id) REFERENCES file_storage_site(file_storage_site_id);


--
-- TOC entry 5666 (class 0 OID 0)
-- Dependencies: 4538
-- Name: CONSTRAINT "$1" ON acquisition_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$1" ON acquisition_task_item IS 'Consider renaming to file_storage_site_id.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4539 (class 2606 OID 16857288)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY acquisition_task_item
    ADD CONSTRAINT "$2" FOREIGN KEY (file_set_id) REFERENCES file_set(file_set_id);


--
-- TOC entry 5667 (class 0 OID 0)
-- Dependencies: 4539
-- Name: CONSTRAINT "$2" ON acquisition_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$2" ON acquisition_task_item IS 'Consider renaming to file_set_id.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4558 (class 2606 OID 16857293)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY containment
    ADD CONSTRAINT "$2" FOREIGN KEY (held_id) REFERENCES container(container_id) ON DELETE CASCADE;


--
-- TOC entry 5668 (class 0 OID 0)
-- Dependencies: 4558
-- Name: CONSTRAINT "$2" ON containment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$2" ON containment IS 'Consider renaming to held_id

Consider changing action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4750 (class 2606 OID 16857303)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rearrayed_containers
    ADD CONSTRAINT "$2" FOREIGN KEY (destination_container_id) REFERENCES container(container_id);


--
-- TOC entry 5669 (class 0 OID 0)
-- Dependencies: 4750
-- Name: CONSTRAINT "$2" ON rearrayed_containers; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$2" ON rearrayed_containers IS 'Consider renaming to destination_container_id.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4742 (class 2606 OID 16857308)
-- Name: $2; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_specs_container_specs
    ADD CONSTRAINT "$2" FOREIGN KEY (container_specs_id) REFERENCES container_specs(container_specs_id);


--
-- TOC entry 5670 (class 0 OID 0)
-- Dependencies: 4742
-- Name: CONSTRAINT "$2" ON rack_specs_container_specs; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$2" ON rack_specs_container_specs IS 'Consider renaming to container_specs_id.

Consider changing action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4732 (class 2606 OID 16857313)
-- Name: $3; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY project
    ADD CONSTRAINT "$3" FOREIGN KEY (project_leader_id) REFERENCES db_user(db_user_id);


--
-- TOC entry 5671 (class 0 OID 0)
-- Dependencies: 4732
-- Name: CONSTRAINT "$3" ON project; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$3" ON project IS 'Consider renaming to project_leader_id.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT.';


--
-- TOC entry 4555 (class 2606 OID 16857318)
-- Name: $6; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY container
    ADD CONSTRAINT "$6" FOREIGN KEY (container_specs_id) REFERENCES container_specs(container_specs_id);


--
-- TOC entry 5672 (class 0 OID 0)
-- Dependencies: 4555
-- Name: CONSTRAINT "$6" ON container; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT "$6" ON container IS 'Consider renaming to container_specs_id.

Consider changing actions to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4686 (class 2606 OID 16857323)
-- Name: accession_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule_design_mirna_target
    ADD CONSTRAINT accession_fkey FOREIGN KEY (accession) REFERENCES mirna(accession);


--
-- TOC entry 4617 (class 2606 OID 16857328)
-- Name: accession_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intended_mirna_target
    ADD CONSTRAINT accession_fkey FOREIGN KEY (accession) REFERENCES mirna(accession);


--
-- TOC entry 4542 (class 2606 OID 16857348)
-- Name: annotation_accession_annotation_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY annotation_accession
    ADD CONSTRAINT annotation_accession_annotation_id FOREIGN KEY (annotation_id) REFERENCES annotation(annotation_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4541 (class 2606 OID 16857353)
-- Name: annotation_annotation_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY annotation
    ADD CONSTRAINT annotation_annotation_type_id FOREIGN KEY (annotation_type_id) REFERENCES annotation_type(annotation_type_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4543 (class 2606 OID 16857358)
-- Name: annotation_relationship_child_annotation_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY annotation_relationship
    ADD CONSTRAINT annotation_relationship_child_annotation_id FOREIGN KEY (child_annotation_id) REFERENCES annotation(annotation_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4544 (class 2606 OID 16857363)
-- Name: annotation_relationship_parent_annotation_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY annotation_relationship
    ADD CONSTRAINT annotation_relationship_parent_annotation_id FOREIGN KEY (parent_annotation_id) REFERENCES annotation(annotation_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4545 (class 2606 OID 16857368)
-- Name: annotation_type_db_source_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY annotation_type
    ADD CONSTRAINT annotation_type_db_source_id FOREIGN KEY (db_source_id) REFERENCES db_source(db_source_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4734 (class 2606 OID 16857298)
-- Name: barcoded_location_barcoded_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_barcoded_location
    ADD CONSTRAINT barcoded_location_barcoded_location_id_fkey FOREIGN KEY (barcoded_location_id) REFERENCES barcoded_location(barcoded_location_id);


--
-- TOC entry 5673 (class 0 OID 0)
-- Dependencies: 4734
-- Name: CONSTRAINT barcoded_location_barcoded_location_id_fkey ON rack_barcoded_location; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT barcoded_location_barcoded_location_id_fkey ON rack_barcoded_location IS 'Consider renaming to barcoded_location_id.

Consider changing actions to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4767 (class 2606 OID 16857373)
-- Name: cell_line_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_cells
    ADD CONSTRAINT cell_line_id FOREIGN KEY (cell_line_id) REFERENCES cell_line(cell_line_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4815 (class 2606 OID 16857378)
-- Name: cell_line_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY transfection_job_step
    ADD CONSTRAINT cell_line_id FOREIGN KEY (cell_line_id) REFERENCES cell_line(cell_line_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4727 (class 2606 OID 16857383)
-- Name: cell_line_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY primer_validation
    ADD CONSTRAINT cell_line_id FOREIGN KEY (cell_line_id) REFERENCES cell_line(cell_line_id);


--
-- TOC entry 4549 (class 2606 OID 16857388)
-- Name: chromosome_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome_gene_feature
    ADD CONSTRAINT chromosome_id FOREIGN KEY (chromosome_id) REFERENCES chromosome(chromosome_id);


--
-- TOC entry 4552 (class 2606 OID 16857393)
-- Name: chromosome_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome_transcript_feature
    ADD CONSTRAINT chromosome_id FOREIGN KEY (chromosome_id) REFERENCES chromosome(chromosome_id);


--
-- TOC entry 4836 (class 2606 OID 16859052)
-- Name: compound_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY compound
    ADD CONSTRAINT compound_molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4557 (class 2606 OID 16857398)
-- Name: container_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY container_barcode
    ADD CONSTRAINT container_id FOREIGN KEY (container_id) REFERENCES container(container_id) ON DELETE CASCADE;


--
-- TOC entry 4744 (class 2606 OID 16857403)
-- Name: container_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample
    ADD CONSTRAINT container_id FOREIGN KEY (container_id) REFERENCES container(container_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4733 (class 2606 OID 16857408)
-- Name: customer_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY project
    ADD CONSTRAINT customer_id FOREIGN KEY (customer_id) REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4567 (class 2606 OID 16857413)
-- Name: db_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY db_group_users
    ADD CONSTRAINT db_group_id FOREIGN KEY (db_group_id) REFERENCES db_group(db_group_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4565 (class 2606 OID 16857418)
-- Name: db_release_db_source_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY current_db_release
    ADD CONSTRAINT db_release_db_source_id FOREIGN KEY (db_release_id, db_source_id) REFERENCES db_release(db_release_id, db_source_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4755 (class 2606 OID 16857423)
-- Name: db_release_id; Type: FK CONSTRAINT; Schema: public; Owner: walsh
--

ALTER TABLE ONLY release_gene
    ADD CONSTRAINT db_release_id FOREIGN KEY (db_release_id) REFERENCES db_release(db_release_id);


--
-- TOC entry 4677 (class 2606 OID 16857428)
-- Name: db_release_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY release_versioned_transcript
    ADD CONSTRAINT db_release_id FOREIGN KEY (db_release_id) REFERENCES db_release(db_release_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4759 (class 2606 OID 16857433)
-- Name: db_release_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY replaced_gene
    ADD CONSTRAINT db_release_id FOREIGN KEY (db_release_id) REFERENCES db_release(db_release_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4762 (class 2606 OID 16857438)
-- Name: db_release_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY replaced_transcript
    ADD CONSTRAINT db_release_id FOREIGN KEY (db_release_id) REFERENCES db_release(db_release_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4674 (class 2606 OID 16857443)
-- Name: db_release_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY release_gene_transcript
    ADD CONSTRAINT db_release_id_fkey FOREIGN KEY (db_release_id) REFERENCES db_release(db_release_id);


--
-- TOC entry 4566 (class 2606 OID 16857448)
-- Name: db_source_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY db_release
    ADD CONSTRAINT db_source_id FOREIGN KEY (db_source_id) REFERENCES db_source(db_source_id) ON UPDATE CASCADE;


--
-- TOC entry 4773 (class 2606 OID 16857453)
-- Name: db_source_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY seq_identifier_type
    ADD CONSTRAINT db_source_id FOREIGN KEY (db_source_id) REFERENCES db_source(db_source_id) ON UPDATE CASCADE;


--
-- TOC entry 4652 (class 2606 OID 16857458)
-- Name: db_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job
    ADD CONSTRAINT db_user_id FOREIGN KEY (db_user_id) REFERENCES db_user(db_user_id);


--
-- TOC entry 5674 (class 0 OID 0)
-- Dependencies: 4652
-- Name: CONSTRAINT db_user_id ON job; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT db_user_id ON job IS 'Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4803 (class 2606 OID 16857463)
-- Name: db_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task
    ADD CONSTRAINT db_user_id FOREIGN KEY (db_user_id) REFERENCES db_user(db_user_id);


--
-- TOC entry 5675 (class 0 OID 0)
-- Dependencies: 4803
-- Name: CONSTRAINT db_user_id ON task; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT db_user_id ON task IS 'Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4568 (class 2606 OID 16857468)
-- Name: db_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY db_group_users
    ADD CONSTRAINT db_user_id FOREIGN KEY (db_user_id) REFERENCES db_user(db_user_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4728 (class 2606 OID 16857473)
-- Name: db_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY primer_validation
    ADD CONSTRAINT db_user_id FOREIGN KEY (db_user_id) REFERENCES db_user(db_user_id);


--
-- TOC entry 4751 (class 2606 OID 16857478)
-- Name: destination_sample_set_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rearrayed_containers
    ADD CONSTRAINT destination_sample_set_id FOREIGN KEY (destination_sample_set_id) REFERENCES sample_set(sample_set_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4731 (class 2606 OID 16857483)
-- Name: device_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY printer
    ADD CONSTRAINT device_id FOREIGN KEY (device_id) REFERENCES device(device_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4546 (class 2606 OID 16857488)
-- Name: device_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY barcoded_location
    ADD CONSTRAINT device_id FOREIGN KEY (device_id) REFERENCES device(device_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4569 (class 2606 OID 16857493)
-- Name: device_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY device
    ADD CONSTRAINT device_type_id FOREIGN KEY (device_type_id) REFERENCES device_type(device_type_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4574 (class 2606 OID 16857498)
-- Name: evidence_release_gene2annotation_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY evidence
    ADD CONSTRAINT evidence_release_gene2annotation_id FOREIGN KEY (release_gene2annotation_id) REFERENCES release_gene2annotation(release_gene2annotation_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4581 (class 2606 OID 16857503)
-- Name: executed_container_dilution_executed_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_sample_dilution
    ADD CONSTRAINT executed_container_dilution_executed_transfer_id_fkey FOREIGN KEY (executed_liquid_transfer_id) REFERENCES executed_liquid_transfer(executed_liquid_transfer_id) ON DELETE CASCADE;


--
-- TOC entry 4582 (class 2606 OID 16857508)
-- Name: executed_container_dilution_reservoir_specs_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_sample_dilution
    ADD CONSTRAINT executed_container_dilution_reservoir_specs_id_fkey FOREIGN KEY (reservoir_specs_id) REFERENCES reservoir_specs(reservoir_specs_id);


--
-- TOC entry 4583 (class 2606 OID 16857513)
-- Name: executed_container_dilution_target_container_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_sample_dilution
    ADD CONSTRAINT executed_container_dilution_target_container_id_fkey FOREIGN KEY (target_container_id) REFERENCES container(container_id);


--
-- TOC entry 4584 (class 2606 OID 16857518)
-- Name: executed_container_transfer_executed_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_sample_transfer
    ADD CONSTRAINT executed_container_transfer_executed_transfer_id_fkey FOREIGN KEY (executed_liquid_transfer_id) REFERENCES executed_liquid_transfer(executed_liquid_transfer_id) ON DELETE CASCADE;


--
-- TOC entry 4585 (class 2606 OID 16857523)
-- Name: executed_container_transfer_source_container_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_sample_transfer
    ADD CONSTRAINT executed_container_transfer_source_container_id_fkey FOREIGN KEY (source_container_id) REFERENCES container(container_id);


--
-- TOC entry 4586 (class 2606 OID 16857528)
-- Name: executed_container_transfer_target_container_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_sample_transfer
    ADD CONSTRAINT executed_container_transfer_target_container_id_fkey FOREIGN KEY (target_container_id) REFERENCES container(container_id);


--
-- TOC entry 4575 (class 2606 OID 16857533)
-- Name: executed_liquid_transfer_planned_liquid_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_liquid_transfer
    ADD CONSTRAINT executed_liquid_transfer_planned_liquid_transfer_id_fkey FOREIGN KEY (planned_liquid_transfer_id) REFERENCES planned_liquid_transfer(planned_liquid_transfer_id) ON UPDATE CASCADE;


--
-- TOC entry 4578 (class 2606 OID 16857538)
-- Name: executed_rack_transfer_executed_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_rack_sample_transfer
    ADD CONSTRAINT executed_rack_transfer_executed_transfer_id_fkey FOREIGN KEY (executed_liquid_transfer_id) REFERENCES executed_liquid_transfer(executed_liquid_transfer_id) ON DELETE CASCADE;


--
-- TOC entry 4579 (class 2606 OID 16857543)
-- Name: executed_rack_transfer_source_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_rack_sample_transfer
    ADD CONSTRAINT executed_rack_transfer_source_rack_id_fkey FOREIGN KEY (source_rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4580 (class 2606 OID 16857548)
-- Name: executed_rack_transfer_target_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_rack_sample_transfer
    ADD CONSTRAINT executed_rack_transfer_target_rack_id_fkey FOREIGN KEY (target_rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4576 (class 2606 OID 16857553)
-- Name: executed_transfer_db_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_liquid_transfer
    ADD CONSTRAINT executed_transfer_db_user_id_fkey FOREIGN KEY (db_user_id) REFERENCES db_user(db_user_id);


--
-- TOC entry 4577 (class 2606 OID 16857558)
-- Name: executed_transfer_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_liquid_transfer
    ADD CONSTRAINT executed_transfer_type_fkey FOREIGN KEY (transfer_type) REFERENCES transfer_type(name) ON UPDATE CASCADE;


--
-- TOC entry 4588 (class 2606 OID 16857563)
-- Name: executed_worklist_member_executed_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_worklist_member
    ADD CONSTRAINT executed_worklist_member_executed_transfer_id_fkey FOREIGN KEY (executed_liquid_transfer_id) REFERENCES executed_liquid_transfer(executed_liquid_transfer_id);


--
-- TOC entry 4589 (class 2606 OID 16857568)
-- Name: executed_worklist_member_executed_worklist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_worklist_member
    ADD CONSTRAINT executed_worklist_member_executed_worklist_id_fkey FOREIGN KEY (executed_worklist_id) REFERENCES executed_worklist(executed_worklist_id) ON DELETE CASCADE;


--
-- TOC entry 4587 (class 2606 OID 16857573)
-- Name: executed_worklist_planned_worklist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY executed_worklist
    ADD CONSTRAINT executed_worklist_planned_worklist_id_fkey FOREIGN KEY (planned_worklist_id) REFERENCES planned_worklist(planned_worklist_id);


--
-- TOC entry 4590 (class 2606 OID 16857578)
-- Name: experiment_design_experiment_metadata_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_design
    ADD CONSTRAINT experiment_design_experiment_metadata_id_fkey FOREIGN KEY (experiment_metadata_id) REFERENCES experiment_metadata(experiment_metadata_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4592 (class 2606 OID 16857583)
-- Name: experiment_design_rack_experiment_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_design_rack
    ADD CONSTRAINT experiment_design_rack_experiment_design_id_fkey FOREIGN KEY (experiment_design_id) REFERENCES experiment_design(experiment_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4593 (class 2606 OID 16857588)
-- Name: experiment_design_rack_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_design_rack
    ADD CONSTRAINT experiment_design_rack_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4591 (class 2606 OID 16859098)
-- Name: experiment_design_rack_shape_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_design
    ADD CONSTRAINT experiment_design_rack_shape_name_fkey FOREIGN KEY (rack_shape_name) REFERENCES rack_shape(rack_shape_name);


--
-- TOC entry 4594 (class 2606 OID 16857613)
-- Name: experiment_metadata_experiment_metadata_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_metadata
    ADD CONSTRAINT experiment_metadata_experiment_metadata_type_id_fkey FOREIGN KEY (experiment_metadata_type_id) REFERENCES experiment_metadata_type(experiment_metadata_type_id) ON UPDATE CASCADE;


--
-- TOC entry 4596 (class 2606 OID 16857618)
-- Name: experiment_metadata_iso_request_experiment_metadata_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY experiment_metadata_iso_request
    ADD CONSTRAINT experiment_metadata_iso_request_experiment_metadata_id_fkey FOREIGN KEY (experiment_metadata_id) REFERENCES experiment_metadata(experiment_metadata_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4597 (class 2606 OID 16857623)
-- Name: experiment_metadata_iso_request_iso_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY experiment_metadata_iso_request
    ADD CONSTRAINT experiment_metadata_iso_request_iso_request_id_fkey FOREIGN KEY (iso_request_id) REFERENCES iso_request(iso_request_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4598 (class 2606 OID 16857628)
-- Name: experiment_metadata_molecule_design_experiment_metadata_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY experiment_metadata_molecule_design_set
    ADD CONSTRAINT experiment_metadata_molecule_design_experiment_metadata_id_fkey FOREIGN KEY (experiment_metadata_id) REFERENCES experiment_metadata(experiment_metadata_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4599 (class 2606 OID 16857633)
-- Name: experiment_metadata_molecule_design_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY experiment_metadata_molecule_design_set
    ADD CONSTRAINT experiment_metadata_molecule_design_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_set(molecule_design_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4595 (class 2606 OID 16857638)
-- Name: experiment_metadata_subproject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY experiment_metadata
    ADD CONSTRAINT experiment_metadata_subproject_id_fkey FOREIGN KEY (subproject_id) REFERENCES subproject(subproject_id);


--
-- TOC entry 4600 (class 2606 OID 16857643)
-- Name: experiment_metadata_target_set_experiment_metadata_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY experiment_metadata_target_set
    ADD CONSTRAINT experiment_metadata_target_set_experiment_metadata_id_fkey FOREIGN KEY (experiment_metadata_id) REFERENCES experiment_metadata(experiment_metadata_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4601 (class 2606 OID 16857648)
-- Name: experiment_metadata_target_set_target_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY experiment_metadata_target_set
    ADD CONSTRAINT experiment_metadata_target_set_target_set_id_fkey FOREIGN KEY (target_set_id) REFERENCES target_set(target_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4602 (class 2606 OID 16857678)
-- Name: experiment_source_rack_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: berger
--

ALTER TABLE ONLY experiment_source_rack
    ADD CONSTRAINT experiment_source_rack_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES new_experiment(experiment_id) ON UPDATE CASCADE;


--
-- TOC entry 4603 (class 2606 OID 16857688)
-- Name: experiment_source_rack_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: berger
--

ALTER TABLE ONLY experiment_source_rack
    ADD CONSTRAINT experiment_source_rack_rack_id_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id) ON UPDATE CASCADE;


--
-- TOC entry 4608 (class 2606 OID 16857778)
-- Name: file_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file_set_files
    ADD CONSTRAINT file_id FOREIGN KEY (file_id) REFERENCES file(file_id);


--
-- TOC entry 5676 (class 0 OID 0)
-- Dependencies: 4608
-- Name: CONSTRAINT file_id ON file_set_files; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT file_id ON file_set_files IS 'Consider changing action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4609 (class 2606 OID 16857785)
-- Name: file_set_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file_set_files
    ADD CONSTRAINT file_set_id FOREIGN KEY (file_set_id) REFERENCES file_set(file_set_id);


--
-- TOC entry 5677 (class 0 OID 0)
-- Dependencies: 4609
-- Name: CONSTRAINT file_set_id ON file_set_files; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT file_set_id ON file_set_files IS 'Consider changin action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4785 (class 2606 OID 16857790)
-- Name: file_storage_site_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subproject
    ADD CONSTRAINT file_storage_site_id FOREIGN KEY (file_storage_site_id) REFERENCES file_storage_site(file_storage_site_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4607 (class 2606 OID 16857795)
-- Name: file_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_type_id FOREIGN KEY (file_type_id) REFERENCES file_type(file_type_id);


--
-- TOC entry 5678 (class 0 OID 0)
-- Dependencies: 4607
-- Name: CONSTRAINT file_type_id ON file; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT file_type_id ON file IS 'Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4611 (class 2606 OID 16857800)
-- Name: gene2annotation_annotation_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY gene2annotation
    ADD CONSTRAINT gene2annotation_annotation_id FOREIGN KEY (annotation_id) REFERENCES annotation(annotation_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4612 (class 2606 OID 16857805)
-- Name: gene2annotation_gene_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY gene2annotation
    ADD CONSTRAINT gene2annotation_gene_id FOREIGN KEY (gene_id) REFERENCES gene(gene_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4550 (class 2606 OID 16857810)
-- Name: gene_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome_gene_feature
    ADD CONSTRAINT gene_id FOREIGN KEY (gene_id) REFERENCES gene(gene_id);


--
-- TOC entry 4613 (class 2606 OID 16857815)
-- Name: gene_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY gene_identifier
    ADD CONSTRAINT gene_id FOREIGN KEY (gene_id) REFERENCES gene(gene_id);


--
-- TOC entry 4756 (class 2606 OID 16857820)
-- Name: gene_id; Type: FK CONSTRAINT; Schema: public; Owner: walsh
--

ALTER TABLE ONLY release_gene
    ADD CONSTRAINT gene_id FOREIGN KEY (gene_id) REFERENCES gene(gene_id);


--
-- TOC entry 4675 (class 2606 OID 16857825)
-- Name: gene_species_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY release_gene_transcript
    ADD CONSTRAINT gene_species_fkey FOREIGN KEY (gene_id, species_id) REFERENCES gene(gene_id, species_id);


--
-- TOC entry 4559 (class 2606 OID 16857830)
-- Name: holder_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY containment
    ADD CONSTRAINT holder_id FOREIGN KEY (holder_id) REFERENCES rack(rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4640 (class 2606 OID 16857835)
-- Name: internal_sample_order_racks_iso_plate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso_racks
    ADD CONSTRAINT internal_sample_order_racks_iso_plate_id_fkey FOREIGN KEY (iso_plate_id) REFERENCES rack(rack_id);


--
-- TOC entry 4641 (class 2606 OID 16857840)
-- Name: internal_sample_order_racks_preparation_plate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso_racks
    ADD CONSTRAINT internal_sample_order_racks_preparation_plate_id_fkey FOREIGN KEY (preparation_plate_id) REFERENCES rack(rack_id);


--
-- TOC entry 4642 (class 2606 OID 16857845)
-- Name: internal_sample_order_racks_stock_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso_racks
    ADD CONSTRAINT internal_sample_order_racks_stock_rack_id_fkey FOREIGN KEY (stock_rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4623 (class 2606 OID 16857850)
-- Name: iso_aliquot_plate_iso_plate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_aliquot_plate
    ADD CONSTRAINT iso_aliquot_plate_iso_plate_id_fkey FOREIGN KEY (iso_plate_id) REFERENCES iso_plate(iso_plate_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4621 (class 2606 OID 16857855)
-- Name: iso_iso_request_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso
    ADD CONSTRAINT iso_iso_request_fkey FOREIGN KEY (iso_request_id) REFERENCES iso_request(iso_request_id);


--
-- TOC entry 4624 (class 2606 OID 16857860)
-- Name: iso_job_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_job
    ADD CONSTRAINT iso_job_job_id_fkey FOREIGN KEY (job_id) REFERENCES new_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4625 (class 2606 OID 16857865)
-- Name: iso_job_member_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso_job_member
    ADD CONSTRAINT iso_job_member_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON DELETE CASCADE;


--
-- TOC entry 4626 (class 2606 OID 16857870)
-- Name: iso_job_member_job_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso_job_member
    ADD CONSTRAINT iso_job_member_job_id_fkey1 FOREIGN KEY (job_id) REFERENCES new_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4627 (class 2606 OID 16857875)
-- Name: iso_job_preparation_plate_job_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_job_preparation_plate
    ADD CONSTRAINT iso_job_preparation_plate_job_id_fkey1 FOREIGN KEY (job_id) REFERENCES new_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4628 (class 2606 OID 16857880)
-- Name: iso_job_preparation_plate_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_job_preparation_plate
    ADD CONSTRAINT iso_job_preparation_plate_rack_id_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4629 (class 2606 OID 16857885)
-- Name: iso_job_preparation_plate_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_job_preparation_plate
    ADD CONSTRAINT iso_job_preparation_plate_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4630 (class 2606 OID 16857890)
-- Name: iso_job_stock_rack_job_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_job_stock_rack
    ADD CONSTRAINT iso_job_stock_rack_job_id_fkey1 FOREIGN KEY (job_id) REFERENCES new_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4631 (class 2606 OID 16857895)
-- Name: iso_job_stock_rack_stock_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_job_stock_rack
    ADD CONSTRAINT iso_job_stock_rack_stock_rack_id_fkey FOREIGN KEY (stock_rack_id) REFERENCES stock_rack(stock_rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4632 (class 2606 OID 16857900)
-- Name: iso_molecule_design_set_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_molecule_design_set
    ADD CONSTRAINT iso_molecule_design_set_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4633 (class 2606 OID 16857905)
-- Name: iso_molecule_design_set_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_molecule_design_set
    ADD CONSTRAINT iso_molecule_design_set_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_set(molecule_design_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4634 (class 2606 OID 16857910)
-- Name: iso_plate_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_plate
    ADD CONSTRAINT iso_plate_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4635 (class 2606 OID 16857915)
-- Name: iso_plate_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_plate
    ADD CONSTRAINT iso_plate_rack_id_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4636 (class 2606 OID 16857920)
-- Name: iso_pool_set_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_pool_set
    ADD CONSTRAINT iso_pool_set_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4637 (class 2606 OID 16857925)
-- Name: iso_pool_set_molecule_design_pool_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_pool_set
    ADD CONSTRAINT iso_pool_set_molecule_design_pool_set_id_fkey FOREIGN KEY (molecule_design_pool_set_id) REFERENCES molecule_design_pool_set(molecule_design_pool_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4638 (class 2606 OID 16857930)
-- Name: iso_preparation_plate_iso_plate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_preparation_plate
    ADD CONSTRAINT iso_preparation_plate_iso_plate_id_fkey FOREIGN KEY (iso_plate_id) REFERENCES iso_plate(iso_plate_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4639 (class 2606 OID 16857935)
-- Name: iso_preparation_plate_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_preparation_plate
    ADD CONSTRAINT iso_preparation_plate_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4622 (class 2606 OID 16857940)
-- Name: iso_rack_layout_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso
    ADD CONSTRAINT iso_rack_layout_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4643 (class 2606 OID 16857945)
-- Name: iso_racks_iso_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY iso_racks
    ADD CONSTRAINT iso_racks_iso_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id);


--
-- TOC entry 4644 (class 2606 OID 16857950)
-- Name: iso_request_pool_set_iso_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_request_pool_set
    ADD CONSTRAINT iso_request_pool_set_iso_request_id_fkey FOREIGN KEY (iso_request_id) REFERENCES iso_request(iso_request_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4645 (class 2606 OID 16857955)
-- Name: iso_request_pool_set_molecule_design_pool_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_request_pool_set
    ADD CONSTRAINT iso_request_pool_set_molecule_design_pool_set_id_fkey FOREIGN KEY (molecule_design_pool_set_id) REFERENCES molecule_design_pool_set(molecule_design_pool_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4646 (class 2606 OID 16857960)
-- Name: iso_sector_preparation_plate_iso_plate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_sector_preparation_plate
    ADD CONSTRAINT iso_sector_preparation_plate_iso_plate_id_fkey FOREIGN KEY (iso_plate_id) REFERENCES iso_plate(iso_plate_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4647 (class 2606 OID 16857965)
-- Name: iso_sector_preparation_plate_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_sector_preparation_plate
    ADD CONSTRAINT iso_sector_preparation_plate_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4648 (class 2606 OID 16857970)
-- Name: iso_sector_stock_rack_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_sector_stock_rack
    ADD CONSTRAINT iso_sector_stock_rack_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4649 (class 2606 OID 16857975)
-- Name: iso_sector_stock_rack_stock_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_sector_stock_rack
    ADD CONSTRAINT iso_sector_stock_rack_stock_rack_id_fkey FOREIGN KEY (stock_rack_id) REFERENCES stock_rack(stock_rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4650 (class 2606 OID 16857980)
-- Name: iso_stock_rack_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_stock_rack
    ADD CONSTRAINT iso_stock_rack_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4651 (class 2606 OID 16857985)
-- Name: iso_stock_rack_stock_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY iso_stock_rack
    ADD CONSTRAINT iso_stock_rack_stock_rack_id_fkey FOREIGN KEY (stock_rack_id) REFERENCES stock_rack(stock_rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4806 (class 2606 OID 16857990)
-- Name: item_set_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_item
    ADD CONSTRAINT item_set_id FOREIGN KEY (item_set_id) REFERENCES sample_set(sample_set_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4556 (class 2606 OID 16857995)
-- Name: item_status; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY container
    ADD CONSTRAINT item_status FOREIGN KEY (item_status) REFERENCES item_status(item_status_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4560 (class 2606 OID 16858000)
-- Name: item_status; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack
    ADD CONSTRAINT item_status FOREIGN KEY (item_status) REFERENCES item_status(item_status_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4656 (class 2606 OID 16858005)
-- Name: job_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job_step
    ADD CONSTRAINT job_id FOREIGN KEY (job_id) REFERENCES job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4804 (class 2606 OID 16858010)
-- Name: job_step_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task
    ADD CONSTRAINT job_step_id FOREIGN KEY (job_step_id) REFERENCES job_step(job_step_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4571 (class 2606 OID 16858015)
-- Name: job_step_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dilution_job_step
    ADD CONSTRAINT job_step_id FOREIGN KEY (job_step_id) REFERENCES job_step(job_step_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4816 (class 2606 OID 16858020)
-- Name: job_step_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY transfection_job_step
    ADD CONSTRAINT job_step_id FOREIGN KEY (job_step_id) REFERENCES job_step(job_step_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4653 (class 2606 OID 16858025)
-- Name: job_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job
    ADD CONSTRAINT job_type_id FOREIGN KEY (job_type_id) REFERENCES job_type(job_type_id);


--
-- TOC entry 5679 (class 0 OID 0)
-- Dependencies: 4653
-- Name: CONSTRAINT job_type_id ON job; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT job_type_id ON job IS 'Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4658 (class 2606 OID 16858030)
-- Name: lab_iso_library_plate_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY lab_iso_library_plate
    ADD CONSTRAINT lab_iso_library_plate_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4659 (class 2606 OID 16858035)
-- Name: lab_iso_library_plate_library_plate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY lab_iso_library_plate
    ADD CONSTRAINT lab_iso_library_plate_library_plate_id_fkey FOREIGN KEY (library_plate_id) REFERENCES library_plate(library_plate_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4660 (class 2606 OID 16858040)
-- Name: lab_iso_request_iso_plate_reservoir_specs_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY lab_iso_request
    ADD CONSTRAINT lab_iso_request_iso_plate_reservoir_specs_id_fkey FOREIGN KEY (iso_plate_reservoir_specs_id) REFERENCES reservoir_specs(reservoir_specs_id);


--
-- TOC entry 4661 (class 2606 OID 16858045)
-- Name: lab_iso_request_iso_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY lab_iso_request
    ADD CONSTRAINT lab_iso_request_iso_request_id_fkey FOREIGN KEY (iso_request_id) REFERENCES iso_request(iso_request_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4662 (class 2606 OID 16858050)
-- Name: lab_iso_request_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY lab_iso_request
    ADD CONSTRAINT lab_iso_request_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4663 (class 2606 OID 16858055)
-- Name: lab_iso_request_requester_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY lab_iso_request
    ADD CONSTRAINT lab_iso_request_requester_id_fkey FOREIGN KEY (requester_id) REFERENCES db_user(db_user_id);


--
-- TOC entry 4665 (class 2606 OID 16858060)
-- Name: library_plate_molecule_design_library_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY library_plate
    ADD CONSTRAINT library_plate_molecule_design_library_id_fkey FOREIGN KEY (molecule_design_library_id) REFERENCES molecule_design_library(molecule_design_library_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4666 (class 2606 OID 16858065)
-- Name: library_plate_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY library_plate
    ADD CONSTRAINT library_plate_rack_id_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4564 (class 2606 OID 16858070)
-- Name: manufacturer_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY container_specs
    ADD CONSTRAINT manufacturer_id FOREIGN KEY (manufacturer_id) REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4562 (class 2606 OID 16858075)
-- Name: manufacturer_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_specs
    ADD CONSTRAINT manufacturer_id FOREIGN KEY (manufacturer_id) REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4570 (class 2606 OID 16858080)
-- Name: manufacturer_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY device
    ADD CONSTRAINT manufacturer_id FOREIGN KEY (manufacturer_id) REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4670 (class 2606 OID 16858085)
-- Name: molecule_design_gene_gene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cebos
--

ALTER TABLE ONLY molecule_design_gene
    ADD CONSTRAINT molecule_design_gene_gene_id_fkey FOREIGN KEY (gene_id) REFERENCES gene(gene_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4671 (class 2606 OID 16858090)
-- Name: molecule_design_gene_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: cebos
--

ALTER TABLE ONLY molecule_design_gene
    ADD CONSTRAINT molecule_design_gene_molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4667 (class 2606 OID 16858095)
-- Name: molecule_design_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule
    ADD CONSTRAINT molecule_design_id FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4619 (class 2606 OID 16858100)
-- Name: molecule_design_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intended_target
    ADD CONSTRAINT molecule_design_id FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4572 (class 2606 OID 16858105)
-- Name: molecule_design_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY double_stranded_intended_target
    ADD CONSTRAINT molecule_design_id FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id);


--
-- TOC entry 4672 (class 2606 OID 16858110)
-- Name: molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule_design_versioned_transcript_target
    ADD CONSTRAINT molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id);


--
-- TOC entry 4687 (class 2606 OID 16858115)
-- Name: molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule_design_mirna_target
    ADD CONSTRAINT molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id);


--
-- TOC entry 4618 (class 2606 OID 16858120)
-- Name: molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intended_mirna_target
    ADD CONSTRAINT molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id);


--
-- TOC entry 4682 (class 2606 OID 16858125)
-- Name: molecule_design_library_iso_req_molecule_design_library_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_library_creation_iso_request
    ADD CONSTRAINT molecule_design_library_iso_req_molecule_design_library_id_fkey FOREIGN KEY (molecule_design_library_id) REFERENCES molecule_design_library(molecule_design_library_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4683 (class 2606 OID 16858130)
-- Name: molecule_design_library_iso_request_iso_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_library_creation_iso_request
    ADD CONSTRAINT molecule_design_library_iso_request_iso_request_id_fkey FOREIGN KEY (iso_request_id) REFERENCES stock_sample_creation_iso_request(iso_request_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4684 (class 2606 OID 16858135)
-- Name: molecule_design_library_lab_iso_molecule_design_library_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_library_lab_iso_request
    ADD CONSTRAINT molecule_design_library_lab_iso_molecule_design_library_id_fkey FOREIGN KEY (molecule_design_library_id) REFERENCES molecule_design_library(molecule_design_library_id) ON UPDATE CASCADE;


--
-- TOC entry 4685 (class 2606 OID 16858140)
-- Name: molecule_design_library_lab_iso_request_iso_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_library_lab_iso_request
    ADD CONSTRAINT molecule_design_library_lab_iso_request_iso_request_id_fkey FOREIGN KEY (iso_request_id) REFERENCES lab_iso_request(iso_request_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4680 (class 2606 OID 16858145)
-- Name: molecule_design_library_pool_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_library
    ADD CONSTRAINT molecule_design_library_pool_set_id_fkey FOREIGN KEY (molecule_design_pool_set_id) REFERENCES molecule_design_pool_set(molecule_design_pool_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4681 (class 2606 OID 16858150)
-- Name: molecule_design_library_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_library
    ADD CONSTRAINT molecule_design_library_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4690 (class 2606 OID 16858155)
-- Name: molecule_design_pool_set_molecule_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_pool_set
    ADD CONSTRAINT molecule_design_pool_set_molecule_type_id_fkey FOREIGN KEY (molecule_type_id) REFERENCES molecule_type(molecule_type_id);


--
-- TOC entry 4693 (class 2606 OID 16858160)
-- Name: molecule_design_set_gene_gene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_set_gene
    ADD CONSTRAINT molecule_design_set_gene_gene_id_fkey FOREIGN KEY (gene_id) REFERENCES gene(gene_id);


--
-- TOC entry 4694 (class 2606 OID 16858165)
-- Name: molecule_design_set_gene_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_set_gene
    ADD CONSTRAINT molecule_design_set_gene_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_pool(molecule_design_set_id);


--
-- TOC entry 4695 (class 2606 OID 16858170)
-- Name: molecule_design_set_member_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY molecule_design_set_member
    ADD CONSTRAINT molecule_design_set_member_molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id);


--
-- TOC entry 4696 (class 2606 OID 16858175)
-- Name: molecule_design_set_member_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY molecule_design_set_member
    ADD CONSTRAINT molecule_design_set_member_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_set(molecule_design_set_id);


--
-- TOC entry 4697 (class 2606 OID 16858180)
-- Name: molecule_design_set_target_set_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY molecule_design_set_target_set
    ADD CONSTRAINT molecule_design_set_target_set_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_set(molecule_design_set_id);


--
-- TOC entry 4698 (class 2606 OID 16858185)
-- Name: molecule_design_set_target_set_target_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY molecule_design_set_target_set
    ADD CONSTRAINT molecule_design_set_target_set_target_set_id_fkey FOREIGN KEY (target_set_id) REFERENCES target_set(target_set_id);


--
-- TOC entry 4699 (class 2606 OID 16858190)
-- Name: molecule_design_structure_chemical_structure_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_structure
    ADD CONSTRAINT molecule_design_structure_chemical_structure_id_fkey FOREIGN KEY (chemical_structure_id) REFERENCES chemical_structure(chemical_structure_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4700 (class 2606 OID 16858195)
-- Name: molecule_design_structure_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_structure
    ADD CONSTRAINT molecule_design_structure_molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4745 (class 2606 OID 16858200)
-- Name: molecule_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_molecule
    ADD CONSTRAINT molecule_id FOREIGN KEY (molecule_id) REFERENCES molecule(molecule_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4668 (class 2606 OID 16858205)
-- Name: molecule_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule
    ADD CONSTRAINT molecule_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES organization(organization_id);


--
-- TOC entry 4669 (class 2606 OID 16858210)
-- Name: molecule_type; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule_design
    ADD CONSTRAINT molecule_type FOREIGN KEY (molecule_type) REFERENCES molecule_type(molecule_type_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4701 (class 2606 OID 16858215)
-- Name: new_experiment_experiment_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY new_experiment
    ADD CONSTRAINT new_experiment_experiment_design_id_fkey FOREIGN KEY (experiment_design_id) REFERENCES experiment_design(experiment_design_id);


--
-- TOC entry 4702 (class 2606 OID 16858220)
-- Name: new_experiment_job_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY new_experiment
    ADD CONSTRAINT new_experiment_job_id_fkey1 FOREIGN KEY (job_id) REFERENCES new_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4703 (class 2606 OID 16858225)
-- Name: new_experiment_rack_experiment_design_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY new_experiment_rack
    ADD CONSTRAINT new_experiment_rack_experiment_design_rack_id_fkey FOREIGN KEY (experiment_design_rack_id) REFERENCES experiment_design_rack(experiment_design_rack_id);


--
-- TOC entry 4704 (class 2606 OID 16858230)
-- Name: new_experiment_rack_experiment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY new_experiment_rack
    ADD CONSTRAINT new_experiment_rack_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES new_experiment(experiment_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4705 (class 2606 OID 16858235)
-- Name: new_experiment_rack_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY new_experiment_rack
    ADD CONSTRAINT new_experiment_rack_rack_id_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4706 (class 2606 OID 16858240)
-- Name: new_job_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY new_job
    ADD CONSTRAINT new_job_user_id_fkey FOREIGN KEY (user_id) REFERENCES db_user(db_user_id) ON UPDATE RESTRICT ON DELETE RESTRICT;


--
-- TOC entry 4709 (class 2606 OID 16858245)
-- Name: planned_liquid_transfer_transfer_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_liquid_transfer
    ADD CONSTRAINT planned_liquid_transfer_transfer_type_fkey FOREIGN KEY (transfer_type) REFERENCES transfer_type(name) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4710 (class 2606 OID 16858250)
-- Name: planned_rack_sample_transfer_planned_liquid_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_rack_sample_transfer
    ADD CONSTRAINT planned_rack_sample_transfer_planned_liquid_transfer_id_fkey FOREIGN KEY (planned_liquid_transfer_id) REFERENCES planned_liquid_transfer(planned_liquid_transfer_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4711 (class 2606 OID 16858255)
-- Name: planned_sample_dilution_planned_liquid_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_sample_dilution
    ADD CONSTRAINT planned_sample_dilution_planned_liquid_transfer_id_fkey FOREIGN KEY (planned_liquid_transfer_id) REFERENCES planned_liquid_transfer(planned_liquid_transfer_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4712 (class 2606 OID 16858260)
-- Name: planned_sample_dilution_target_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_sample_dilution
    ADD CONSTRAINT planned_sample_dilution_target_position_id_fkey FOREIGN KEY (target_position_id) REFERENCES rack_position(rack_position_id) ON UPDATE CASCADE;


--
-- TOC entry 4713 (class 2606 OID 16858265)
-- Name: planned_sample_transfer_planned_liquid_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_sample_transfer
    ADD CONSTRAINT planned_sample_transfer_planned_liquid_transfer_id_fkey FOREIGN KEY (planned_liquid_transfer_id) REFERENCES planned_liquid_transfer(planned_liquid_transfer_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4714 (class 2606 OID 16858270)
-- Name: planned_sample_transfer_source_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_sample_transfer
    ADD CONSTRAINT planned_sample_transfer_source_position_id_fkey FOREIGN KEY (source_position_id) REFERENCES rack_position(rack_position_id) ON UPDATE CASCADE;


--
-- TOC entry 4715 (class 2606 OID 16858275)
-- Name: planned_sample_transfer_target_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_sample_transfer
    ADD CONSTRAINT planned_sample_transfer_target_position_id_fkey FOREIGN KEY (target_position_id) REFERENCES rack_position(rack_position_id) ON UPDATE CASCADE;


--
-- TOC entry 4718 (class 2606 OID 16858280)
-- Name: planned_worklist_member_planned_liquid_transfer_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_worklist_member
    ADD CONSTRAINT planned_worklist_member_planned_liquid_transfer_id_fkey1 FOREIGN KEY (planned_liquid_transfer_id) REFERENCES planned_liquid_transfer(planned_liquid_transfer_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4719 (class 2606 OID 16858285)
-- Name: planned_worklist_member_planned_worklist_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY planned_worklist_member
    ADD CONSTRAINT planned_worklist_member_planned_worklist_id_fkey1 FOREIGN KEY (planned_worklist_id) REFERENCES planned_worklist(planned_worklist_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4716 (class 2606 OID 16858290)
-- Name: planned_worklist_pipetting_specs_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY planned_worklist
    ADD CONSTRAINT planned_worklist_pipetting_specs_id_fkey FOREIGN KEY (pipetting_specs_id) REFERENCES pipetting_specs(pipetting_specs_id) ON UPDATE CASCADE;


--
-- TOC entry 4717 (class 2606 OID 16858295)
-- Name: planned_worklist_transfer_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY planned_worklist
    ADD CONSTRAINT planned_worklist_transfer_type_fkey FOREIGN KEY (transfer_type) REFERENCES transfer_type(name) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4691 (class 2606 OID 16858300)
-- Name: pool_set_member_pool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_pool_set_member
    ADD CONSTRAINT pool_set_member_pool_id_fkey FOREIGN KEY (molecule_design_pool_id) REFERENCES molecule_design_pool(molecule_design_set_id);


--
-- TOC entry 4692 (class 2606 OID 16858305)
-- Name: pool_set_member_pool_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_pool_set_member
    ADD CONSTRAINT pool_set_member_pool_set_id_fkey FOREIGN KEY (molecule_design_pool_set_id) REFERENCES molecule_design_pool_set(molecule_design_pool_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4720 (class 2606 OID 16858310)
-- Name: pooled_supplier_molecule_desig_supplier_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY pooled_supplier_molecule_design
    ADD CONSTRAINT pooled_supplier_molecule_desig_supplier_molecule_design_id_fkey FOREIGN KEY (supplier_molecule_design_id) REFERENCES supplier_molecule_design(supplier_molecule_design_id);


--
-- TOC entry 4721 (class 2606 OID 16858315)
-- Name: pooled_supplier_molecule_design_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY pooled_supplier_molecule_design
    ADD CONSTRAINT pooled_supplier_molecule_design_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_set(molecule_design_set_id);


--
-- TOC entry 4722 (class 2606 OID 16858320)
-- Name: primer_1_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY primer_pair
    ADD CONSTRAINT primer_1_id FOREIGN KEY (primer_1_id) REFERENCES molecule_design(molecule_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4723 (class 2606 OID 16858325)
-- Name: primer_2_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY primer_pair
    ADD CONSTRAINT primer_2_id FOREIGN KEY (primer_2_id) REFERENCES molecule_design(molecule_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4664 (class 2606 OID 16858330)
-- Name: primer_pair_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY legacy_primer_pair
    ADD CONSTRAINT primer_pair_id FOREIGN KEY (primer_pair_id) REFERENCES primer_pair(primer_pair_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4729 (class 2606 OID 16858335)
-- Name: primer_pair_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY primer_validation
    ADD CONSTRAINT primer_pair_id FOREIGN KEY (primer_pair_id) REFERENCES primer_pair(primer_pair_id);


--
-- TOC entry 4725 (class 2606 OID 16858340)
-- Name: primer_pair_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY versioned_transcript_amplicon
    ADD CONSTRAINT primer_pair_id_fkey FOREIGN KEY (primer_pair_id) REFERENCES primer_pair(primer_pair_id);


--
-- TOC entry 4786 (class 2606 OID 16858345)
-- Name: project_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY subproject
    ADD CONSTRAINT project_id FOREIGN KEY (project_id) REFERENCES project(project_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4730 (class 2606 OID 16858350)
-- Name: project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY primer_validation
    ADD CONSTRAINT project_id_fkey FOREIGN KEY (project_id) REFERENCES project(project_id);


--
-- TOC entry 4736 (class 2606 OID 16858355)
-- Name: rack_barcoded_location_log_barcoded_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_barcoded_location_log
    ADD CONSTRAINT rack_barcoded_location_log_barcoded_location_id_fkey FOREIGN KEY (barcoded_location_id) REFERENCES barcoded_location(barcoded_location_id);


--
-- TOC entry 4737 (class 2606 OID 16858360)
-- Name: rack_barcoded_location_log_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_barcoded_location_log
    ADD CONSTRAINT rack_barcoded_location_log_rack_id_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4604 (class 2606 OID 16858365)
-- Name: rack_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY external_primer_carrier
    ADD CONSTRAINT rack_id FOREIGN KEY (carrier_id) REFERENCES rack(rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4735 (class 2606 OID 16858370)
-- Name: rack_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_barcoded_location
    ADD CONSTRAINT rack_id FOREIGN KEY (rack_id) REFERENCES rack(rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4787 (class 2606 OID 16858375)
-- Name: rack_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY supplier_barcode
    ADD CONSTRAINT rack_id FOREIGN KEY (rack_id) REFERENCES rack(rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4738 (class 2606 OID 16859113)
-- Name: rack_layout_rack_shape_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY rack_layout
    ADD CONSTRAINT rack_layout_rack_shape_name_fkey FOREIGN KEY (rack_shape_name) REFERENCES rack_shape(rack_shape_name);


--
-- TOC entry 4739 (class 2606 OID 16858385)
-- Name: rack_mask_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_mask_position
    ADD CONSTRAINT rack_mask_id FOREIGN KEY (rack_mask_id) REFERENCES rack_mask(rack_mask_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4740 (class 2606 OID 16858390)
-- Name: rack_position_set_member_rack_position_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY rack_position_set_member
    ADD CONSTRAINT rack_position_set_member_rack_position_id_fkey1 FOREIGN KEY (rack_position_id) REFERENCES rack_position(rack_position_id);


--
-- TOC entry 4741 (class 2606 OID 16858395)
-- Name: rack_position_set_member_rack_position_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY rack_position_set_member
    ADD CONSTRAINT rack_position_set_member_rack_position_set_id_fkey FOREIGN KEY (rack_position_set_id) REFERENCES rack_position_set(rack_position_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4561 (class 2606 OID 16858400)
-- Name: rack_specs_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack
    ADD CONSTRAINT rack_specs_id FOREIGN KEY (rack_specs_id) REFERENCES rack_specs(rack_specs_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4743 (class 2606 OID 16858405)
-- Name: rack_specs_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_specs_container_specs
    ADD CONSTRAINT rack_specs_id FOREIGN KEY (rack_specs_id) REFERENCES rack_specs(rack_specs_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4563 (class 2606 OID 16859118)
-- Name: rack_specs_rack_shape_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rack_specs
    ADD CONSTRAINT rack_specs_rack_shape_name_fkey FOREIGN KEY (rack_shape_name) REFERENCES rack_shape(rack_shape_name);


--
-- TOC entry 4753 (class 2606 OID 16858420)
-- Name: refseq_gene_species_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: berger
--

ALTER TABLE ONLY refseq_gene
    ADD CONSTRAINT refseq_gene_species_id_fkey FOREIGN KEY (species_id) REFERENCES species(species_id);


--
-- TOC entry 4754 (class 2606 OID 16858425)
-- Name: refseq_update_species_species_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY refseq_update_species
    ADD CONSTRAINT refseq_update_species_species_id_fkey FOREIGN KEY (species_id) REFERENCES species(species_id);


--
-- TOC entry 4757 (class 2606 OID 16858430)
-- Name: release_gene2annotation_db_release_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY release_gene2annotation
    ADD CONSTRAINT release_gene2annotation_db_release_id FOREIGN KEY (db_release_id) REFERENCES db_release(db_release_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4758 (class 2606 OID 16858435)
-- Name: release_gene2annotation_gene2annotation_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY release_gene2annotation
    ADD CONSTRAINT release_gene2annotation_gene2annotation_id FOREIGN KEY (gene2annotation_id) REFERENCES gene2annotation(gene2annotation_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4760 (class 2606 OID 16858440)
-- Name: replaced_gene_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY replaced_gene
    ADD CONSTRAINT replaced_gene_id FOREIGN KEY (replaced_gene_id) REFERENCES gene(gene_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4763 (class 2606 OID 16858445)
-- Name: replaced_transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY replaced_transcript
    ADD CONSTRAINT replaced_transcript_id FOREIGN KEY (replaced_transcript_id) REFERENCES transcript(transcript_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4761 (class 2606 OID 16858450)
-- Name: replacement_gene_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY replaced_gene
    ADD CONSTRAINT replacement_gene_id FOREIGN KEY (replacement_gene_id) REFERENCES gene(gene_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4764 (class 2606 OID 16858455)
-- Name: replacement_transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY replaced_transcript
    ADD CONSTRAINT replacement_transcript_id FOREIGN KEY (replacement_transcript_id) REFERENCES transcript(transcript_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4765 (class 2606 OID 16859123)
-- Name: reservoir_specs_rack_shape_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY reservoir_specs
    ADD CONSTRAINT reservoir_specs_rack_shape_name_fkey FOREIGN KEY (rack_shape_name) REFERENCES rack_shape(rack_shape_name);


--
-- TOC entry 4766 (class 2606 OID 16858465)
-- Name: rnai_experiment_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY rnai_experiment
    ADD CONSTRAINT rnai_experiment_id FOREIGN KEY (job_id) REFERENCES job(job_id);


--
-- TOC entry 5680 (class 0 OID 0)
-- Dependencies: 4766
-- Name: CONSTRAINT rnai_experiment_id ON rnai_experiment; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT rnai_experiment_id ON rnai_experiment IS 'Consider renaming to job_id.

Consider changing action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4769 (class 2606 OID 16858470)
-- Name: sample_creation_sample_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_registration
    ADD CONSTRAINT sample_creation_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES sample(sample_id);


--
-- TOC entry 4746 (class 2606 OID 16858475)
-- Name: sample_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_molecule
    ADD CONSTRAINT sample_id FOREIGN KEY (sample_id) REFERENCES sample(sample_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4771 (class 2606 OID 16858480)
-- Name: sample_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_set_sample
    ADD CONSTRAINT sample_id FOREIGN KEY (sample_id) REFERENCES sample(sample_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4768 (class 2606 OID 16858485)
-- Name: sample_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_cells
    ADD CONSTRAINT sample_id FOREIGN KEY (sample_id) REFERENCES sample(sample_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4772 (class 2606 OID 16858490)
-- Name: sample_set_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_set_sample
    ADD CONSTRAINT sample_set_id FOREIGN KEY (sample_set_id) REFERENCES sample_set(sample_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4707 (class 2606 OID 16858495)
-- Name: sample_set_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY order_sample_set
    ADD CONSTRAINT sample_set_id FOREIGN KEY (sample_set_id) REFERENCES sample_set(sample_set_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4770 (class 2606 OID 16858500)
-- Name: sample_set_type; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY sample_set
    ADD CONSTRAINT sample_set_type FOREIGN KEY (sample_set_type) REFERENCES sample_set_type(sample_set_type_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4813 (class 2606 OID 16858505)
-- Name: seq_identifier_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY transcript_identifier
    ADD CONSTRAINT seq_identifier_type_id FOREIGN KEY (seq_identifier_type_id) REFERENCES seq_identifier_type(seq_identifier_type_id);


--
-- TOC entry 4614 (class 2606 OID 16858510)
-- Name: seq_identifier_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY gene_identifier
    ADD CONSTRAINT seq_identifier_type_id FOREIGN KEY (seq_identifier_type_id) REFERENCES seq_identifier_type(seq_identifier_type_id);


--
-- TOC entry 4553 (class 2606 OID 16858515)
-- Name: sequence_feature_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome_transcript_feature
    ADD CONSTRAINT sequence_feature_id FOREIGN KEY (sequence_feature_id) REFERENCES sequence_feature(sequence_feature_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4551 (class 2606 OID 16858520)
-- Name: sequence_feature_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome_gene_feature
    ADD CONSTRAINT sequence_feature_id FOREIGN KEY (sequence_feature_id) REFERENCES sequence_feature(sequence_feature_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4774 (class 2606 OID 16858525)
-- Name: single_supplier_molecule_desig_supplier_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY single_supplier_molecule_design
    ADD CONSTRAINT single_supplier_molecule_desig_supplier_molecule_design_id_fkey FOREIGN KEY (supplier_molecule_design_id) REFERENCES supplier_molecule_design(supplier_molecule_design_id);


--
-- TOC entry 4775 (class 2606 OID 16858530)
-- Name: single_supplier_molecule_design_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY single_supplier_molecule_design
    ADD CONSTRAINT single_supplier_molecule_design_molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id);


--
-- TOC entry 4547 (class 2606 OID 16858535)
-- Name: species_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cell_line
    ADD CONSTRAINT species_id FOREIGN KEY (species_id) REFERENCES species(species_id);


--
-- TOC entry 5681 (class 0 OID 0)
-- Dependencies: 4547
-- Name: CONSTRAINT species_id ON cell_line; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT species_id ON cell_line IS 'Consider changing actions to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4548 (class 2606 OID 16858540)
-- Name: species_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome
    ADD CONSTRAINT species_id FOREIGN KEY (species_id) REFERENCES species(species_id);


--
-- TOC entry 4605 (class 2606 OID 16858545)
-- Name: species_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY external_primer_carrier
    ADD CONSTRAINT species_id FOREIGN KEY (species_id) REFERENCES species(species_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4724 (class 2606 OID 16858550)
-- Name: species_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY transcript
    ADD CONSTRAINT species_id FOREIGN KEY (species_id) REFERENCES species(species_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4610 (class 2606 OID 16858555)
-- Name: species_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY gene
    ADD CONSTRAINT species_id FOREIGN KEY (species_id) REFERENCES species(species_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4654 (class 2606 OID 16858560)
-- Name: status_type; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job
    ADD CONSTRAINT status_type FOREIGN KEY (status_type) REFERENCES status_type(status_type_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4805 (class 2606 OID 16858565)
-- Name: status_type; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task
    ADD CONSTRAINT status_type FOREIGN KEY (status_type) REFERENCES status_type(status_type_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4776 (class 2606 OID 16858570)
-- Name: stock_rack_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_rack
    ADD CONSTRAINT stock_rack_rack_id_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4777 (class 2606 OID 16858575)
-- Name: stock_rack_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_rack
    ADD CONSTRAINT stock_rack_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4778 (class 2606 OID 16858580)
-- Name: stock_rack_worklist_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_rack
    ADD CONSTRAINT stock_rack_worklist_series_id_fkey FOREIGN KEY (worklist_series_id) REFERENCES worklist_series(worklist_series_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4783 (class 2606 OID 16858585)
-- Name: stock_sample_creation_iso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_sample_creation_iso
    ADD CONSTRAINT stock_sample_creation_iso_id_fkey FOREIGN KEY (iso_id) REFERENCES iso(iso_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4784 (class 2606 OID 16858590)
-- Name: stock_sample_creation_iso_request_iso_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_sample_creation_iso_request
    ADD CONSTRAINT stock_sample_creation_iso_request_iso_request_id_fkey FOREIGN KEY (iso_request_id) REFERENCES iso_request(iso_request_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4779 (class 2606 OID 16858595)
-- Name: stock_sample_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_sample
    ADD CONSTRAINT stock_sample_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_set(molecule_design_set_id);


--
-- TOC entry 4688 (class 2606 OID 16858600)
-- Name: stock_sample_molecule_design_set_molecule_design_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_pool
    ADD CONSTRAINT stock_sample_molecule_design_set_molecule_design_set_id_fkey FOREIGN KEY (molecule_design_set_id) REFERENCES molecule_design_set(molecule_design_set_id);


--
-- TOC entry 4689 (class 2606 OID 16858605)
-- Name: stock_sample_molecule_design_set_molecule_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY molecule_design_pool
    ADD CONSTRAINT stock_sample_molecule_design_set_molecule_type_fkey FOREIGN KEY (molecule_type) REFERENCES molecule_type(molecule_type_id);


--
-- TOC entry 4780 (class 2606 OID 16858610)
-- Name: stock_sample_molecule_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_sample
    ADD CONSTRAINT stock_sample_molecule_type_id_fkey FOREIGN KEY (molecule_type) REFERENCES molecule_type(molecule_type_id);


--
-- TOC entry 4781 (class 2606 OID 16858615)
-- Name: stock_sample_sample_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_sample
    ADD CONSTRAINT stock_sample_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES sample(sample_id);


--
-- TOC entry 4782 (class 2606 OID 16858620)
-- Name: stock_sample_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY stock_sample
    ADD CONSTRAINT stock_sample_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES organization(organization_id);


--
-- TOC entry 4809 (class 2606 OID 16858625)
-- Name: subproject_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_report
    ADD CONSTRAINT subproject_id FOREIGN KEY (subproject_id) REFERENCES subproject(subproject_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4655 (class 2606 OID 16858630)
-- Name: subproject_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job
    ADD CONSTRAINT subproject_id FOREIGN KEY (subproject_id) REFERENCES subproject(subproject_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5682 (class 0 OID 0)
-- Dependencies: 4655
-- Name: CONSTRAINT subproject_id ON job; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT subproject_id ON job IS 'Current action will cause all jobs to be deleted when the parent subproject
is removed.  This seems dangerous and backwards.

Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4708 (class 2606 OID 16858635)
-- Name: supplier_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY order_sample_set
    ADD CONSTRAINT supplier_id FOREIGN KEY (supplier_id) REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4788 (class 2606 OID 16858640)
-- Name: supplier_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY supplier_molecule_design
    ADD CONSTRAINT supplier_id FOREIGN KEY (supplier_id) REFERENCES organization(organization_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4789 (class 2606 OID 16858645)
-- Name: supplier_structure_annotation_chemical_structure_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY supplier_structure_annotation
    ADD CONSTRAINT supplier_structure_annotation_chemical_structure_id_fkey FOREIGN KEY (chemical_structure_id) REFERENCES chemical_structure(chemical_structure_id);


--
-- TOC entry 4790 (class 2606 OID 16858650)
-- Name: supplier_structure_annotation_supplier_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY supplier_structure_annotation
    ADD CONSTRAINT supplier_structure_annotation_supplier_molecule_design_id_fkey FOREIGN KEY (supplier_molecule_design_id) REFERENCES supplier_molecule_design(supplier_molecule_design_id);


--
-- TOC entry 4791 (class 2606 OID 16858655)
-- Name: tag_tag_domain_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tag
    ADD CONSTRAINT tag_tag_domain_fkey FOREIGN KEY (tag_domain_id) REFERENCES tag_domain(tag_domain_id);


--
-- TOC entry 4792 (class 2606 OID 16858660)
-- Name: tag_tag_predicate_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tag
    ADD CONSTRAINT tag_tag_predicate_fkey FOREIGN KEY (tag_predicate_id) REFERENCES tag_predicate(tag_predicate_id);


--
-- TOC entry 4793 (class 2606 OID 16858665)
-- Name: tag_tag_value_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tag
    ADD CONSTRAINT tag_tag_value_fkey FOREIGN KEY (tag_value_id) REFERENCES tag_value(tag_value_id);


--
-- TOC entry 4794 (class 2606 OID 16858670)
-- Name: tagged_rack_position_set_new_rack_position_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tagged_rack_position_set
    ADD CONSTRAINT tagged_rack_position_set_new_rack_position_set_id_fkey FOREIGN KEY (rack_position_set_id) REFERENCES rack_position_set(rack_position_set_id);


--
-- TOC entry 4795 (class 2606 OID 16858675)
-- Name: tagged_rack_position_set_rack_layout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tagged_rack_position_set
    ADD CONSTRAINT tagged_rack_position_set_rack_layout_id_fkey FOREIGN KEY (rack_layout_id) REFERENCES rack_layout(rack_layout_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4796 (class 2606 OID 16858680)
-- Name: tagged_rack_position_set_tagged_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tagged_rack_position_set
    ADD CONSTRAINT tagged_rack_position_set_tagged_id_fkey FOREIGN KEY (tagged_id) REFERENCES tagged(tagged_id);


--
-- TOC entry 4797 (class 2606 OID 16858685)
-- Name: tagging_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tagging
    ADD CONSTRAINT tagging_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES tag(tag_id);


--
-- TOC entry 4798 (class 2606 OID 16858690)
-- Name: tagging_tagged_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tagging
    ADD CONSTRAINT tagging_tagged_id_fkey FOREIGN KEY (tagged_id) REFERENCES tagged(tagged_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4799 (class 2606 OID 16858695)
-- Name: target_molecule_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY target
    ADD CONSTRAINT target_molecule_design_id_fkey FOREIGN KEY (molecule_design_id) REFERENCES molecule_design(molecule_design_id);


--
-- TOC entry 4801 (class 2606 OID 16858700)
-- Name: target_set_member_target_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY target_set_member
    ADD CONSTRAINT target_set_member_target_id_fkey FOREIGN KEY (target_id) REFERENCES target(target_id);


--
-- TOC entry 4802 (class 2606 OID 16858705)
-- Name: target_set_member_target_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY target_set_member
    ADD CONSTRAINT target_set_member_target_set_id_fkey FOREIGN KEY (target_set_id) REFERENCES target_set(target_set_id);


--
-- TOC entry 4800 (class 2606 OID 16858710)
-- Name: target_transcript_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY target
    ADD CONSTRAINT target_transcript_id_fkey FOREIGN KEY (transcript_id) REFERENCES transcript(transcript_id);


--
-- TOC entry 4807 (class 2606 OID 16858715)
-- Name: task_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_item
    ADD CONSTRAINT task_id FOREIGN KEY (task_id) REFERENCES task(task_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4540 (class 2606 OID 16858720)
-- Name: task_item_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY acquisition_task_item
    ADD CONSTRAINT task_item_id FOREIGN KEY (task_item_id) REFERENCES task_item(task_item_id);


--
-- TOC entry 5683 (class 0 OID 0)
-- Dependencies: 4540
-- Name: CONSTRAINT task_item_id ON acquisition_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT task_item_id ON acquisition_task_item IS 'Consider changing action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4748 (class 2606 OID 16858725)
-- Name: task_item_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY readout_task_item
    ADD CONSTRAINT task_item_id FOREIGN KEY (task_item_id) REFERENCES task_item(task_item_id);


--
-- TOC entry 5684 (class 0 OID 0)
-- Dependencies: 4748
-- Name: CONSTRAINT task_item_id ON readout_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT task_item_id ON readout_task_item IS 'Consider changing action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4616 (class 2606 OID 16858730)
-- Name: task_item_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY image_analysis_task_item
    ADD CONSTRAINT task_item_id FOREIGN KEY (task_item_id) REFERENCES readout_task_item(task_item_id);


--
-- TOC entry 5685 (class 0 OID 0)
-- Dependencies: 4616
-- Name: CONSTRAINT task_item_id ON image_analysis_task_item; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT task_item_id ON image_analysis_task_item IS 'Consider changing action to ON UPDATE CASCADE ON DELETE CASCADE';


--
-- TOC entry 4808 (class 2606 OID 16858735)
-- Name: task_item_rack_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_item
    ADD CONSTRAINT task_item_rack_fkey FOREIGN KEY (rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4657 (class 2606 OID 16858740)
-- Name: task_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY job_step
    ADD CONSTRAINT task_type_id FOREIGN KEY (task_type_id) REFERENCES task_type(task_type_id);


--
-- TOC entry 5686 (class 0 OID 0)
-- Dependencies: 4657
-- Name: CONSTRAINT task_type_id ON job_step; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT task_type_id ON job_step IS 'Consider changing action to ON UPDATE CASCADE ON DELETE RESTRICT';


--
-- TOC entry 4810 (class 2606 OID 16858745)
-- Name: task_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY task_report
    ADD CONSTRAINT task_type_id FOREIGN KEY (task_type_id) REFERENCES task_type(task_type_id);


--
-- TOC entry 4811 (class 2606 OID 16858750)
-- Name: transcript_gene_gene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY transcript_gene
    ADD CONSTRAINT transcript_gene_gene_id_fkey FOREIGN KEY (gene_id) REFERENCES gene(gene_id);


--
-- TOC entry 4812 (class 2606 OID 16858755)
-- Name: transcript_gene_transcript_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY transcript_gene
    ADD CONSTRAINT transcript_gene_transcript_id_fkey FOREIGN KEY (transcript_id) REFERENCES transcript(transcript_id);


--
-- TOC entry 4554 (class 2606 OID 16858760)
-- Name: transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY chromosome_transcript_feature
    ADD CONSTRAINT transcript_id FOREIGN KEY (transcript_id) REFERENCES transcript(transcript_id);


--
-- TOC entry 4814 (class 2606 OID 16858765)
-- Name: transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY transcript_identifier
    ADD CONSTRAINT transcript_id FOREIGN KEY (transcript_id) REFERENCES transcript(transcript_id);


--
-- TOC entry 4679 (class 2606 OID 16858770)
-- Name: transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY versioned_transcript
    ADD CONSTRAINT transcript_id FOREIGN KEY (transcript_id) REFERENCES transcript(transcript_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4676 (class 2606 OID 16858775)
-- Name: transcript_species_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY release_gene_transcript
    ADD CONSTRAINT transcript_species_fkey FOREIGN KEY (transcript_id, species_id) REFERENCES transcript(transcript_id, species_id);


--
-- TOC entry 4817 (class 2606 OID 16858780)
-- Name: tube_transfer_source_position_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer
    ADD CONSTRAINT tube_transfer_source_position_id_fkey1 FOREIGN KEY (source_position_id) REFERENCES rack_position(rack_position_id);


--
-- TOC entry 4818 (class 2606 OID 16858785)
-- Name: tube_transfer_source_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer
    ADD CONSTRAINT tube_transfer_source_rack_id_fkey FOREIGN KEY (source_rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4819 (class 2606 OID 16858790)
-- Name: tube_transfer_target_position_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer
    ADD CONSTRAINT tube_transfer_target_position_id_fkey1 FOREIGN KEY (target_position_id) REFERENCES rack_position(rack_position_id);


--
-- TOC entry 4820 (class 2606 OID 16858795)
-- Name: tube_transfer_target_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer
    ADD CONSTRAINT tube_transfer_target_rack_id_fkey FOREIGN KEY (target_rack_id) REFERENCES rack(rack_id);


--
-- TOC entry 4821 (class 2606 OID 16858800)
-- Name: tube_transfer_tube_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer
    ADD CONSTRAINT tube_transfer_tube_id_fkey FOREIGN KEY (tube_id) REFERENCES container(container_id);


--
-- TOC entry 4822 (class 2606 OID 16858805)
-- Name: tube_transfer_worklist_db_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer_worklist
    ADD CONSTRAINT tube_transfer_worklist_db_user_id_fkey FOREIGN KEY (db_user_id) REFERENCES db_user(db_user_id);


--
-- TOC entry 4823 (class 2606 OID 16858810)
-- Name: tube_transfer_worklist_member_tube_transfer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer_worklist_member
    ADD CONSTRAINT tube_transfer_worklist_member_tube_transfer_id_fkey FOREIGN KEY (tube_transfer_id) REFERENCES tube_transfer(tube_transfer_id);


--
-- TOC entry 4824 (class 2606 OID 16858815)
-- Name: tube_transfer_worklist_member_tube_transfer_worklist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY tube_transfer_worklist_member
    ADD CONSTRAINT tube_transfer_worklist_member_tube_transfer_worklist_id_fkey FOREIGN KEY (tube_transfer_worklist_id) REFERENCES tube_transfer_worklist(tube_transfer_worklist_id);


--
-- TOC entry 4825 (class 2606 OID 16858820)
-- Name: user_id; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY user_preferences
    ADD CONSTRAINT user_id FOREIGN KEY (user_id) REFERENCES db_user(db_user_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4678 (class 2606 OID 16858825)
-- Name: versioned_transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY release_versioned_transcript
    ADD CONSTRAINT versioned_transcript_id FOREIGN KEY (versioned_transcript_id) REFERENCES versioned_transcript(versioned_transcript_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4620 (class 2606 OID 16858832)
-- Name: versioned_transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY intended_target
    ADD CONSTRAINT versioned_transcript_id FOREIGN KEY (versioned_transcript_id) REFERENCES versioned_transcript(versioned_transcript_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 4573 (class 2606 OID 16858837)
-- Name: versioned_transcript_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY double_stranded_intended_target
    ADD CONSTRAINT versioned_transcript_id FOREIGN KEY (versioned_transcript_id, molecule_design_id) REFERENCES intended_target(versioned_transcript_id, molecule_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4673 (class 2606 OID 16858842)
-- Name: versioned_transcript_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY molecule_design_versioned_transcript_target
    ADD CONSTRAINT versioned_transcript_id_fkey FOREIGN KEY (versioned_transcript_id) REFERENCES versioned_transcript(versioned_transcript_id);


--
-- TOC entry 4726 (class 2606 OID 16858847)
-- Name: versioned_transcript_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY versioned_transcript_amplicon
    ADD CONSTRAINT versioned_transcript_id_fkey FOREIGN KEY (versioned_transcript_id) REFERENCES versioned_transcript(versioned_transcript_id);


--
-- TOC entry 4828 (class 2606 OID 16858852)
-- Name: worklist_series_experiment_desig_experiment_design_rack_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_experiment_design_rack
    ADD CONSTRAINT worklist_series_experiment_desig_experiment_design_rack_id_fkey FOREIGN KEY (experiment_design_rack_id) REFERENCES experiment_design_rack(experiment_design_rack_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4826 (class 2606 OID 16858857)
-- Name: worklist_series_experiment_design_experiment_design_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_experiment_design
    ADD CONSTRAINT worklist_series_experiment_design_experiment_design_id_fkey FOREIGN KEY (experiment_design_id) REFERENCES experiment_design(experiment_design_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4829 (class 2606 OID 16858862)
-- Name: worklist_series_experiment_design_rack_worklist_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_experiment_design_rack
    ADD CONSTRAINT worklist_series_experiment_design_rack_worklist_series_id_fkey FOREIGN KEY (worklist_series_id) REFERENCES worklist_series(worklist_series_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4827 (class 2606 OID 16858867)
-- Name: worklist_series_experiment_design_worklist_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_experiment_design
    ADD CONSTRAINT worklist_series_experiment_design_worklist_series_id_fkey FOREIGN KEY (worklist_series_id) REFERENCES worklist_series(worklist_series_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4830 (class 2606 OID 16858872)
-- Name: worklist_series_iso_job_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY worklist_series_iso_job
    ADD CONSTRAINT worklist_series_iso_job_job_id_fkey FOREIGN KEY (job_id) REFERENCES iso_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4831 (class 2606 OID 16858877)
-- Name: worklist_series_iso_job_worklist_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gathmann
--

ALTER TABLE ONLY worklist_series_iso_job
    ADD CONSTRAINT worklist_series_iso_job_worklist_series_id_fkey FOREIGN KEY (worklist_series_id) REFERENCES worklist_series(worklist_series_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4832 (class 2606 OID 16858882)
-- Name: worklist_series_iso_request_iso_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_iso_request
    ADD CONSTRAINT worklist_series_iso_request_iso_request_id_fkey FOREIGN KEY (iso_request_id) REFERENCES iso_request(iso_request_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4833 (class 2606 OID 16858887)
-- Name: worklist_series_iso_request_worklist_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_iso_request
    ADD CONSTRAINT worklist_series_iso_request_worklist_series_id_fkey FOREIGN KEY (worklist_series_id) REFERENCES worklist_series(worklist_series_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4834 (class 2606 OID 16858892)
-- Name: worklist_series_member_planned_worklist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_member
    ADD CONSTRAINT worklist_series_member_planned_worklist_id_fkey FOREIGN KEY (planned_worklist_id) REFERENCES planned_worklist(planned_worklist_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4835 (class 2606 OID 16858897)
-- Name: worklist_series_member_worklist_series_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: thelma
--

ALTER TABLE ONLY worklist_series_member
    ADD CONSTRAINT worklist_series_member_worklist_series_id_fkey FOREIGN KEY (worklist_series_id) REFERENCES worklist_series(worklist_series_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4972 (class 0 OID 0)
-- Dependencies: 6
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;
GRANT USAGE ON SCHEMA public TO knime;


--
-- TOC entry 5006 (class 0 OID 0)
-- Dependencies: 169
-- Name: _assertion_trigger_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE _assertion_trigger_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE _assertion_trigger_seq FROM postgres;
GRANT ALL ON SEQUENCE _assertion_trigger_seq TO postgres;
GRANT USAGE ON SEQUENCE _assertion_trigger_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE _assertion_trigger_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE _assertion_trigger_seq TO reader_role;


--
-- TOC entry 5007 (class 0 OID 0)
-- Dependencies: 170
-- Name: _user_messages; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE _user_messages FROM PUBLIC;
REVOKE ALL ON TABLE _user_messages FROM thelma;
GRANT ALL ON TABLE _user_messages TO thelma;
GRANT SELECT,INSERT ON TABLE _user_messages TO bioinf;


--
-- TOC entry 5011 (class 0 OID 0)
-- Dependencies: 171
-- Name: acquisition_task_item; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE acquisition_task_item FROM PUBLIC;
REVOKE ALL ON TABLE acquisition_task_item FROM postgres;
GRANT ALL ON TABLE acquisition_task_item TO postgres;
GRANT SELECT ON TABLE acquisition_task_item TO knime;
GRANT SELECT ON TABLE acquisition_task_item TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE acquisition_task_item TO jobscheduler;
GRANT SELECT ON TABLE acquisition_task_item TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE acquisition_task_item TO writer_role;
GRANT SELECT,INSERT ON TABLE acquisition_task_item TO bioinf;


--
-- TOC entry 5012 (class 0 OID 0)
-- Dependencies: 172
-- Name: annotation_annotation_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE annotation_annotation_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE annotation_annotation_id_seq FROM postgres;
GRANT ALL ON SEQUENCE annotation_annotation_id_seq TO postgres;
GRANT USAGE ON SEQUENCE annotation_annotation_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE annotation_annotation_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE annotation_annotation_id_seq TO reader_role;


--
-- TOC entry 5017 (class 0 OID 0)
-- Dependencies: 173
-- Name: annotation; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE annotation FROM PUBLIC;
REVOKE ALL ON TABLE annotation FROM postgres;
GRANT ALL ON TABLE annotation TO postgres;
GRANT SELECT ON TABLE annotation TO knime;
GRANT SELECT ON TABLE annotation TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE annotation TO jobscheduler;
GRANT SELECT ON TABLE annotation TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE annotation TO writer_role;
GRANT SELECT,INSERT ON TABLE annotation TO bioinf;


--
-- TOC entry 5021 (class 0 OID 0)
-- Dependencies: 174
-- Name: annotation_accession; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE annotation_accession FROM PUBLIC;
REVOKE ALL ON TABLE annotation_accession FROM postgres;
GRANT ALL ON TABLE annotation_accession TO postgres;
GRANT SELECT ON TABLE annotation_accession TO knime;
GRANT SELECT ON TABLE annotation_accession TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE annotation_accession TO jobscheduler;
GRANT SELECT ON TABLE annotation_accession TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE annotation_accession TO writer_role;
GRANT SELECT,INSERT ON TABLE annotation_accession TO bioinf;


--
-- TOC entry 5025 (class 0 OID 0)
-- Dependencies: 175
-- Name: annotation_relationship; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE annotation_relationship FROM PUBLIC;
REVOKE ALL ON TABLE annotation_relationship FROM postgres;
GRANT ALL ON TABLE annotation_relationship TO postgres;
GRANT SELECT ON TABLE annotation_relationship TO knime;
GRANT SELECT ON TABLE annotation_relationship TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE annotation_relationship TO jobscheduler;
GRANT SELECT ON TABLE annotation_relationship TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE annotation_relationship TO writer_role;
GRANT SELECT,INSERT ON TABLE annotation_relationship TO bioinf;


--
-- TOC entry 5026 (class 0 OID 0)
-- Dependencies: 176
-- Name: annotation_type_annotation_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE annotation_type_annotation_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE annotation_type_annotation_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE annotation_type_annotation_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE annotation_type_annotation_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE annotation_type_annotation_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE annotation_type_annotation_type_id_seq TO reader_role;


--
-- TOC entry 5031 (class 0 OID 0)
-- Dependencies: 177
-- Name: annotation_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE annotation_type FROM PUBLIC;
REVOKE ALL ON TABLE annotation_type FROM postgres;
GRANT ALL ON TABLE annotation_type TO postgres;
GRANT SELECT ON TABLE annotation_type TO knime;
GRANT SELECT ON TABLE annotation_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE annotation_type TO jobscheduler;
GRANT SELECT ON TABLE annotation_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE annotation_type TO writer_role;
GRANT SELECT,INSERT ON TABLE annotation_type TO bioinf;


--
-- TOC entry 5032 (class 0 OID 0)
-- Dependencies: 178
-- Name: barcode_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE barcode_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE barcode_seq FROM postgres;
GRANT ALL ON SEQUENCE barcode_seq TO postgres;
GRANT USAGE ON SEQUENCE barcode_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE barcode_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE barcode_seq TO reader_role;


--
-- TOC entry 5041 (class 0 OID 0)
-- Dependencies: 179
-- Name: barcoded_location; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE barcoded_location FROM PUBLIC;
REVOKE ALL ON TABLE barcoded_location FROM postgres;
GRANT ALL ON TABLE barcoded_location TO postgres;
GRANT ALL ON TABLE barcoded_location TO pylims;
GRANT ALL ON TABLE barcoded_location TO bioinf;
GRANT ALL ON TABLE barcoded_location TO koski;
GRANT ALL ON TABLE barcoded_location TO walsh;
GRANT ALL ON TABLE barcoded_location TO celma;
GRANT SELECT ON TABLE barcoded_location TO knime;
GRANT SELECT ON TABLE barcoded_location TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE barcoded_location TO jobscheduler;
GRANT SELECT ON TABLE barcoded_location TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE barcoded_location TO writer_role;


--
-- TOC entry 5042 (class 0 OID 0)
-- Dependencies: 180
-- Name: barcoded_location_barcoded_location_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE barcoded_location_barcoded_location_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE barcoded_location_barcoded_location_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE barcoded_location_barcoded_location_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE barcoded_location_barcoded_location_id_seq TO celma;
GRANT USAGE ON SEQUENCE barcoded_location_barcoded_location_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE barcoded_location_barcoded_location_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE barcoded_location_barcoded_location_id_seq TO reader_role;


--
-- TOC entry 5043 (class 0 OID 0)
-- Dependencies: 181
-- Name: carrier_content_type_carrier_content_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE carrier_content_type_carrier_content_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE carrier_content_type_carrier_content_type_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE carrier_content_type_carrier_content_type_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE carrier_content_type_carrier_content_type_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE carrier_content_type_carrier_content_type_id_seq TO celma;
GRANT USAGE ON SEQUENCE carrier_content_type_carrier_content_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE carrier_content_type_carrier_content_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE carrier_content_type_carrier_content_type_id_seq TO reader_role;


--
-- TOC entry 5044 (class 0 OID 0)
-- Dependencies: 182
-- Name: carrier_origin_type_carrier_origin_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE carrier_origin_type_carrier_origin_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE carrier_origin_type_carrier_origin_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE carrier_origin_type_carrier_origin_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE carrier_origin_type_carrier_origin_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE carrier_origin_type_carrier_origin_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE carrier_origin_type_carrier_origin_type_id_seq TO reader_role;


--
-- TOC entry 5045 (class 0 OID 0)
-- Dependencies: 183
-- Name: carrier_set_carrier_set_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE carrier_set_carrier_set_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE carrier_set_carrier_set_id_seq FROM postgres;
GRANT ALL ON SEQUENCE carrier_set_carrier_set_id_seq TO postgres;
GRANT USAGE ON SEQUENCE carrier_set_carrier_set_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE carrier_set_carrier_set_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE carrier_set_carrier_set_id_seq TO reader_role;


--
-- TOC entry 5046 (class 0 OID 0)
-- Dependencies: 184
-- Name: carrier_set_type_carrier_set_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE carrier_set_type_carrier_set_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE carrier_set_type_carrier_set_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE carrier_set_type_carrier_set_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE carrier_set_type_carrier_set_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE carrier_set_type_carrier_set_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE carrier_set_type_carrier_set_type_id_seq TO reader_role;


--
-- TOC entry 5051 (class 0 OID 0)
-- Dependencies: 185
-- Name: cell_line; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE cell_line FROM PUBLIC;
REVOKE ALL ON TABLE cell_line FROM postgres;
GRANT ALL ON TABLE cell_line TO postgres;
GRANT ALL ON TABLE cell_line TO pylims;
GRANT ALL ON TABLE cell_line TO bioinf;
GRANT ALL ON TABLE cell_line TO koski;
GRANT ALL ON TABLE cell_line TO walsh;
GRANT ALL ON TABLE cell_line TO celma;
GRANT SELECT ON TABLE cell_line TO knime;
GRANT SELECT ON TABLE cell_line TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE cell_line TO jobscheduler;
GRANT SELECT ON TABLE cell_line TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE cell_line TO writer_role;


--
-- TOC entry 5053 (class 0 OID 0)
-- Dependencies: 186
-- Name: cell_line_cell_line_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE cell_line_cell_line_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE cell_line_cell_line_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE cell_line_cell_line_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE cell_line_cell_line_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE cell_line_cell_line_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE cell_line_cell_line_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE cell_line_cell_line_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE cell_line_cell_line_id_seq TO celma;
GRANT USAGE ON SEQUENCE cell_line_cell_line_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE cell_line_cell_line_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE cell_line_cell_line_id_seq TO reader_role;


--
-- TOC entry 5055 (class 0 OID 0)
-- Dependencies: 187
-- Name: chemical_structure; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE chemical_structure FROM PUBLIC;
REVOKE ALL ON TABLE chemical_structure FROM gathmann;
GRANT ALL ON TABLE chemical_structure TO gathmann;
GRANT SELECT,INSERT ON TABLE chemical_structure TO bioinf;


--
-- TOC entry 5059 (class 0 OID 0)
-- Dependencies: 189
-- Name: chromosome; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE chromosome FROM PUBLIC;
REVOKE ALL ON TABLE chromosome FROM postgres;
GRANT ALL ON TABLE chromosome TO postgres;
GRANT ALL ON TABLE chromosome TO pylims;
GRANT ALL ON TABLE chromosome TO bioinf;
GRANT ALL ON TABLE chromosome TO koski;
GRANT ALL ON TABLE chromosome TO walsh;
GRANT ALL ON TABLE chromosome TO celma;
GRANT SELECT ON TABLE chromosome TO knime;
GRANT SELECT ON TABLE chromosome TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE chromosome TO jobscheduler;
GRANT SELECT ON TABLE chromosome TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE chromosome TO writer_role;


--
-- TOC entry 5061 (class 0 OID 0)
-- Dependencies: 190
-- Name: chromosome_chromosome_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE chromosome_chromosome_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE chromosome_chromosome_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE chromosome_chromosome_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE chromosome_chromosome_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE chromosome_chromosome_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE chromosome_chromosome_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE chromosome_chromosome_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE chromosome_chromosome_id_seq TO celma;
GRANT USAGE ON SEQUENCE chromosome_chromosome_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE chromosome_chromosome_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE chromosome_chromosome_id_seq TO reader_role;


--
-- TOC entry 5062 (class 0 OID 0)
-- Dependencies: 191
-- Name: chromosome_gene_feature; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE chromosome_gene_feature FROM PUBLIC;
REVOKE ALL ON TABLE chromosome_gene_feature FROM postgres;
GRANT ALL ON TABLE chromosome_gene_feature TO postgres;
GRANT ALL ON TABLE chromosome_gene_feature TO pylims;
GRANT ALL ON TABLE chromosome_gene_feature TO bioinf;
GRANT ALL ON TABLE chromosome_gene_feature TO koski;
GRANT ALL ON TABLE chromosome_gene_feature TO walsh;
GRANT ALL ON TABLE chromosome_gene_feature TO celma;
GRANT SELECT ON TABLE chromosome_gene_feature TO knime;
GRANT SELECT ON TABLE chromosome_gene_feature TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE chromosome_gene_feature TO jobscheduler;
GRANT SELECT ON TABLE chromosome_gene_feature TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE chromosome_gene_feature TO writer_role;


--
-- TOC entry 5064 (class 0 OID 0)
-- Dependencies: 192
-- Name: chromosome_transcript_feature; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE chromosome_transcript_feature FROM PUBLIC;
REVOKE ALL ON TABLE chromosome_transcript_feature FROM postgres;
GRANT ALL ON TABLE chromosome_transcript_feature TO postgres;
GRANT ALL ON TABLE chromosome_transcript_feature TO pylims;
GRANT ALL ON TABLE chromosome_transcript_feature TO bioinf;
GRANT ALL ON TABLE chromosome_transcript_feature TO koski;
GRANT ALL ON TABLE chromosome_transcript_feature TO walsh;
GRANT ALL ON TABLE chromosome_transcript_feature TO celma;
GRANT SELECT ON TABLE chromosome_transcript_feature TO knime;
GRANT SELECT ON TABLE chromosome_transcript_feature TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE chromosome_transcript_feature TO jobscheduler;
GRANT SELECT ON TABLE chromosome_transcript_feature TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE chromosome_transcript_feature TO writer_role;


--
-- TOC entry 5070 (class 0 OID 0)
-- Dependencies: 193
-- Name: container; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE container FROM PUBLIC;
REVOKE ALL ON TABLE container FROM postgres;
GRANT ALL ON TABLE container TO postgres;
GRANT ALL ON TABLE container TO pylims;
GRANT ALL ON TABLE container TO bioinf;
GRANT ALL ON TABLE container TO koski;
GRANT ALL ON TABLE container TO walsh;
GRANT ALL ON TABLE container TO celma;
GRANT SELECT ON TABLE container TO knime;
GRANT SELECT ON TABLE container TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE container TO jobscheduler;
GRANT SELECT ON TABLE container TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE container TO writer_role;


--
-- TOC entry 5072 (class 0 OID 0)
-- Dependencies: 194
-- Name: container_barcode; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE container_barcode FROM PUBLIC;
REVOKE ALL ON TABLE container_barcode FROM postgres;
GRANT ALL ON TABLE container_barcode TO postgres;
GRANT SELECT ON TABLE container_barcode TO knime;
GRANT SELECT ON TABLE container_barcode TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE container_barcode TO jobscheduler;
GRANT SELECT ON TABLE container_barcode TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE container_barcode TO writer_role;
GRANT SELECT,INSERT ON TABLE container_barcode TO bioinf;


--
-- TOC entry 5074 (class 0 OID 0)
-- Dependencies: 195
-- Name: container_container_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE container_container_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE container_container_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE container_container_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE container_container_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE container_container_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE container_container_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE container_container_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE container_container_id_seq TO celma;
GRANT USAGE ON SEQUENCE container_container_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE container_container_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE container_container_id_seq TO reader_role;


--
-- TOC entry 5080 (class 0 OID 0)
-- Dependencies: 196
-- Name: containment; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE containment FROM PUBLIC;
REVOKE ALL ON TABLE containment FROM postgres;
GRANT ALL ON TABLE containment TO postgres;
GRANT SELECT ON TABLE containment TO knime;
GRANT SELECT ON TABLE containment TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE containment TO jobscheduler;
GRANT SELECT ON TABLE containment TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE containment TO writer_role;
GRANT SELECT,INSERT ON TABLE containment TO bioinf;


--
-- TOC entry 5088 (class 0 OID 0)
-- Dependencies: 197
-- Name: rack; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack FROM PUBLIC;
REVOKE ALL ON TABLE rack FROM postgres;
GRANT ALL ON TABLE rack TO postgres;
GRANT ALL ON TABLE rack TO pylims;
GRANT ALL ON TABLE rack TO bioinf;
GRANT ALL ON TABLE rack TO koski;
GRANT ALL ON TABLE rack TO walsh;
GRANT ALL ON TABLE rack TO celma;
GRANT SELECT ON TABLE rack TO knime;
GRANT SELECT ON TABLE rack TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack TO jobscheduler;
GRANT SELECT ON TABLE rack TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack TO writer_role;


--
-- TOC entry 5097 (class 0 OID 0)
-- Dependencies: 198
-- Name: rack_specs; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_specs FROM PUBLIC;
REVOKE ALL ON TABLE rack_specs FROM postgres;
GRANT ALL ON TABLE rack_specs TO postgres;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_specs TO pylims;
GRANT ALL ON TABLE rack_specs TO celma;
GRANT SELECT ON TABLE rack_specs TO knime;
GRANT SELECT ON TABLE rack_specs TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_specs TO jobscheduler;
GRANT SELECT ON TABLE rack_specs TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_specs TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_specs TO bioinf;


--
-- TOC entry 5099 (class 0 OID 0)
-- Dependencies: 199
-- Name: container_info; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE container_info FROM PUBLIC;
REVOKE ALL ON TABLE container_info FROM postgres;
GRANT ALL ON TABLE container_info TO postgres;
GRANT SELECT ON TABLE container_info TO knime;
GRANT SELECT ON TABLE container_info TO ppfinder;
GRANT SELECT ON TABLE container_info TO jobscheduler;
GRANT SELECT,INSERT ON TABLE container_info TO bioinf;


--
-- TOC entry 5109 (class 0 OID 0)
-- Dependencies: 200
-- Name: container_specs; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE container_specs FROM PUBLIC;
REVOKE ALL ON TABLE container_specs FROM postgres;
GRANT ALL ON TABLE container_specs TO postgres;
GRANT SELECT ON TABLE container_specs TO knime;
GRANT SELECT ON TABLE container_specs TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE container_specs TO jobscheduler;
GRANT SELECT ON TABLE container_specs TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE container_specs TO writer_role;
GRANT SELECT,INSERT ON TABLE container_specs TO bioinf;


--
-- TOC entry 5111 (class 0 OID 0)
-- Dependencies: 201
-- Name: container_specs_container_specs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE container_specs_container_specs_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE container_specs_container_specs_id_seq FROM postgres;
GRANT ALL ON SEQUENCE container_specs_container_specs_id_seq TO postgres;
GRANT USAGE ON SEQUENCE container_specs_container_specs_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE container_specs_container_specs_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE container_specs_container_specs_id_seq TO reader_role;


--
-- TOC entry 5112 (class 0 OID 0)
-- Dependencies: 202
-- Name: current_db_release; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE current_db_release FROM PUBLIC;
REVOKE ALL ON TABLE current_db_release FROM postgres;
GRANT ALL ON TABLE current_db_release TO postgres;
GRANT SELECT ON TABLE current_db_release TO knime;
GRANT SELECT ON TABLE current_db_release TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE current_db_release TO jobscheduler;
GRANT SELECT ON TABLE current_db_release TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE current_db_release TO writer_role;
GRANT SELECT,INSERT ON TABLE current_db_release TO bioinf;


--
-- TOC entry 5116 (class 0 OID 0)
-- Dependencies: 203
-- Name: db_release; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE db_release FROM PUBLIC;
REVOKE ALL ON TABLE db_release FROM postgres;
GRANT ALL ON TABLE db_release TO postgres;
GRANT ALL ON TABLE db_release TO pylims;
GRANT ALL ON TABLE db_release TO bioinf;
GRANT ALL ON TABLE db_release TO koski;
GRANT ALL ON TABLE db_release TO walsh;
GRANT ALL ON TABLE db_release TO celma;
GRANT SELECT ON TABLE db_release TO knime;
GRANT SELECT ON TABLE db_release TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE db_release TO jobscheduler;
GRANT SELECT ON TABLE db_release TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE db_release TO writer_role;


--
-- TOC entry 5120 (class 0 OID 0)
-- Dependencies: 204
-- Name: db_source; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE db_source FROM PUBLIC;
REVOKE ALL ON TABLE db_source FROM postgres;
GRANT ALL ON TABLE db_source TO postgres;
GRANT ALL ON TABLE db_source TO pylims;
GRANT ALL ON TABLE db_source TO bioinf;
GRANT ALL ON TABLE db_source TO koski;
GRANT ALL ON TABLE db_source TO walsh;
GRANT ALL ON TABLE db_source TO celma;
GRANT SELECT ON TABLE db_source TO knime;
GRANT SELECT ON TABLE db_source TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE db_source TO jobscheduler;
GRANT SELECT ON TABLE db_source TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE db_source TO writer_role;


--
-- TOC entry 5122 (class 0 OID 0)
-- Dependencies: 205
-- Name: current_db_release_view; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE current_db_release_view FROM PUBLIC;
REVOKE ALL ON TABLE current_db_release_view FROM postgres;
GRANT ALL ON TABLE current_db_release_view TO postgres;
GRANT SELECT ON TABLE current_db_release_view TO knime;
GRANT SELECT ON TABLE current_db_release_view TO ppfinder;
GRANT SELECT ON TABLE current_db_release_view TO jobscheduler;
GRANT SELECT,INSERT ON TABLE current_db_release_view TO bioinf;


--
-- TOC entry 5127 (class 0 OID 0)
-- Dependencies: 206
-- Name: db_group; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE db_group FROM PUBLIC;
REVOKE ALL ON TABLE db_group FROM postgres;
GRANT ALL ON TABLE db_group TO postgres;
GRANT ALL ON TABLE db_group TO celma;
GRANT SELECT ON TABLE db_group TO knime;
GRANT SELECT ON TABLE db_group TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE db_group TO jobscheduler;
GRANT SELECT ON TABLE db_group TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE db_group TO writer_role;
GRANT SELECT,INSERT ON TABLE db_group TO bioinf;


--
-- TOC entry 5129 (class 0 OID 0)
-- Dependencies: 207
-- Name: db_group_db_group_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE db_group_db_group_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE db_group_db_group_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_group_db_group_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_group_db_group_id_seq TO celma;
GRANT USAGE ON SEQUENCE db_group_db_group_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE db_group_db_group_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE db_group_db_group_id_seq TO reader_role;


--
-- TOC entry 5131 (class 0 OID 0)
-- Dependencies: 208
-- Name: db_group_users; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE db_group_users FROM PUBLIC;
REVOKE ALL ON TABLE db_group_users FROM postgres;
GRANT ALL ON TABLE db_group_users TO postgres;
GRANT ALL ON TABLE db_group_users TO celma;
GRANT SELECT ON TABLE db_group_users TO knime;
GRANT SELECT ON TABLE db_group_users TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE db_group_users TO jobscheduler;
GRANT SELECT ON TABLE db_group_users TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE db_group_users TO writer_role;
GRANT SELECT,INSERT ON TABLE db_group_users TO bioinf;


--
-- TOC entry 5133 (class 0 OID 0)
-- Dependencies: 209
-- Name: db_release_db_release_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE db_release_db_release_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE db_release_db_release_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_release_db_release_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_release_db_release_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE db_release_db_release_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE db_release_db_release_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE db_release_db_release_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE db_release_db_release_id_seq TO celma;
GRANT USAGE ON SEQUENCE db_release_db_release_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE db_release_db_release_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE db_release_db_release_id_seq TO reader_role;


--
-- TOC entry 5135 (class 0 OID 0)
-- Dependencies: 210
-- Name: db_source_db_source_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE db_source_db_source_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE db_source_db_source_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_source_db_source_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_source_db_source_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE db_source_db_source_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE db_source_db_source_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE db_source_db_source_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE db_source_db_source_id_seq TO celma;
GRANT USAGE ON SEQUENCE db_source_db_source_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE db_source_db_source_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE db_source_db_source_id_seq TO reader_role;


--
-- TOC entry 5142 (class 0 OID 0)
-- Dependencies: 211
-- Name: db_user; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE db_user FROM PUBLIC;
REVOKE ALL ON TABLE db_user FROM postgres;
GRANT ALL ON TABLE db_user TO postgres;
GRANT ALL ON TABLE db_user TO celma;
GRANT SELECT ON TABLE db_user TO knime;
GRANT SELECT ON TABLE db_user TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE db_user TO jobscheduler;
GRANT SELECT ON TABLE db_user TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE db_user TO writer_role;
GRANT SELECT,INSERT ON TABLE db_user TO bioinf;


--
-- TOC entry 5144 (class 0 OID 0)
-- Dependencies: 212
-- Name: db_user_db_user_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE db_user_db_user_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE db_user_db_user_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_user_db_user_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE db_user_db_user_id_seq TO celma;
GRANT USAGE ON SEQUENCE db_user_db_user_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE db_user_db_user_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE db_user_db_user_id_seq TO reader_role;


--
-- TOC entry 5146 (class 0 OID 0)
-- Dependencies: 213
-- Name: db_version; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE db_version FROM PUBLIC;
REVOKE ALL ON TABLE db_version FROM postgres;
GRANT ALL ON TABLE db_version TO postgres;
GRANT SELECT ON TABLE db_version TO knime;
GRANT SELECT ON TABLE db_version TO ppfinder;
GRANT SELECT ON TABLE db_version TO jobscheduler;
GRANT SELECT,INSERT ON TABLE db_version TO bioinf;


--
-- TOC entry 5153 (class 0 OID 0)
-- Dependencies: 214
-- Name: device; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE device FROM PUBLIC;
REVOKE ALL ON TABLE device FROM postgres;
GRANT ALL ON TABLE device TO postgres;
GRANT ALL ON TABLE device TO celma;
GRANT SELECT ON TABLE device TO knime;
GRANT SELECT ON TABLE device TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE device TO jobscheduler;
GRANT SELECT ON TABLE device TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE device TO writer_role;
GRANT SELECT,INSERT ON TABLE device TO bioinf;


--
-- TOC entry 5155 (class 0 OID 0)
-- Dependencies: 215
-- Name: device_device_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE device_device_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE device_device_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE device_device_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE device_device_id_seq TO celma;
GRANT USAGE ON SEQUENCE device_device_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE device_device_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE device_device_id_seq TO reader_role;


--
-- TOC entry 5160 (class 0 OID 0)
-- Dependencies: 216
-- Name: device_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE device_type FROM PUBLIC;
REVOKE ALL ON TABLE device_type FROM postgres;
GRANT ALL ON TABLE device_type TO postgres;
GRANT ALL ON TABLE device_type TO celma;
GRANT SELECT ON TABLE device_type TO knime;
GRANT SELECT ON TABLE device_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE device_type TO jobscheduler;
GRANT SELECT ON TABLE device_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE device_type TO writer_role;
GRANT SELECT,INSERT ON TABLE device_type TO bioinf;


--
-- TOC entry 5162 (class 0 OID 0)
-- Dependencies: 217
-- Name: device_type_device_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE device_type_device_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE device_type_device_type_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE device_type_device_type_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE device_type_device_type_id_seq TO celma;
GRANT USAGE ON SEQUENCE device_type_device_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE device_type_device_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE device_type_device_type_id_seq TO reader_role;


--
-- TOC entry 5165 (class 0 OID 0)
-- Dependencies: 218
-- Name: dilution_job_step; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE dilution_job_step FROM PUBLIC;
REVOKE ALL ON TABLE dilution_job_step FROM postgres;
GRANT ALL ON TABLE dilution_job_step TO postgres;
GRANT SELECT ON TABLE dilution_job_step TO knime;
GRANT SELECT ON TABLE dilution_job_step TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE dilution_job_step TO jobscheduler;
GRANT SELECT ON TABLE dilution_job_step TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE dilution_job_step TO writer_role;
GRANT SELECT,INSERT ON TABLE dilution_job_step TO bioinf;


--
-- TOC entry 5168 (class 0 OID 0)
-- Dependencies: 219
-- Name: double_stranded_intended_target; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE double_stranded_intended_target FROM PUBLIC;
REVOKE ALL ON TABLE double_stranded_intended_target FROM postgres;
GRANT ALL ON TABLE double_stranded_intended_target TO postgres;
GRANT SELECT ON TABLE double_stranded_intended_target TO knime;
GRANT SELECT ON TABLE double_stranded_intended_target TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE double_stranded_intended_target TO jobscheduler;
GRANT SELECT ON TABLE double_stranded_intended_target TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE double_stranded_intended_target TO writer_role;
GRANT SELECT,INSERT ON TABLE double_stranded_intended_target TO bioinf;


--
-- TOC entry 5172 (class 0 OID 0)
-- Dependencies: 220
-- Name: evidence; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE evidence FROM PUBLIC;
REVOKE ALL ON TABLE evidence FROM postgres;
GRANT ALL ON TABLE evidence TO postgres;
GRANT SELECT ON TABLE evidence TO knime;
GRANT SELECT ON TABLE evidence TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE evidence TO jobscheduler;
GRANT SELECT ON TABLE evidence TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE evidence TO writer_role;
GRANT SELECT,INSERT ON TABLE evidence TO bioinf;


--
-- TOC entry 5173 (class 0 OID 0)
-- Dependencies: 221
-- Name: executed_liquid_transfer; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE executed_liquid_transfer FROM PUBLIC;
REVOKE ALL ON TABLE executed_liquid_transfer FROM thelma;
GRANT ALL ON TABLE executed_liquid_transfer TO thelma;
GRANT SELECT,INSERT ON TABLE executed_liquid_transfer TO bioinf;


--
-- TOC entry 5174 (class 0 OID 0)
-- Dependencies: 222
-- Name: executed_rack_sample_transfer; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE executed_rack_sample_transfer FROM PUBLIC;
REVOKE ALL ON TABLE executed_rack_sample_transfer FROM thelma;
GRANT ALL ON TABLE executed_rack_sample_transfer TO thelma;
GRANT SELECT,INSERT ON TABLE executed_rack_sample_transfer TO bioinf;


--
-- TOC entry 5175 (class 0 OID 0)
-- Dependencies: 223
-- Name: executed_sample_dilution; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE executed_sample_dilution FROM PUBLIC;
REVOKE ALL ON TABLE executed_sample_dilution FROM thelma;
GRANT ALL ON TABLE executed_sample_dilution TO thelma;
GRANT SELECT,INSERT ON TABLE executed_sample_dilution TO bioinf;


--
-- TOC entry 5176 (class 0 OID 0)
-- Dependencies: 224
-- Name: executed_sample_transfer; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE executed_sample_transfer FROM PUBLIC;
REVOKE ALL ON TABLE executed_sample_transfer FROM thelma;
GRANT ALL ON TABLE executed_sample_transfer TO thelma;
GRANT SELECT,INSERT ON TABLE executed_sample_transfer TO bioinf;


--
-- TOC entry 5178 (class 0 OID 0)
-- Dependencies: 226
-- Name: executed_worklist; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE executed_worklist FROM PUBLIC;
REVOKE ALL ON TABLE executed_worklist FROM thelma;
GRANT ALL ON TABLE executed_worklist TO thelma;
GRANT SELECT,INSERT ON TABLE executed_worklist TO bioinf;


--
-- TOC entry 5180 (class 0 OID 0)
-- Dependencies: 228
-- Name: executed_worklist_member; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE executed_worklist_member FROM PUBLIC;
REVOKE ALL ON TABLE executed_worklist_member FROM thelma;
GRANT ALL ON TABLE executed_worklist_member TO thelma;
GRANT SELECT,INSERT ON TABLE executed_worklist_member TO bioinf;


--
-- TOC entry 5182 (class 0 OID 0)
-- Dependencies: 229
-- Name: experiment_design; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE experiment_design FROM PUBLIC;
REVOKE ALL ON TABLE experiment_design FROM thelma;
GRANT ALL ON TABLE experiment_design TO thelma;
GRANT SELECT,INSERT ON TABLE experiment_design TO bioinf;


--
-- TOC entry 5185 (class 0 OID 0)
-- Dependencies: 231
-- Name: experiment_design_rack; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE experiment_design_rack FROM PUBLIC;
REVOKE ALL ON TABLE experiment_design_rack FROM thelma;
GRANT ALL ON TABLE experiment_design_rack TO thelma;
GRANT SELECT ON TABLE experiment_design_rack TO knime;
GRANT SELECT,INSERT ON TABLE experiment_design_rack TO bioinf;


--
-- TOC entry 5188 (class 0 OID 0)
-- Dependencies: 233
-- Name: experiment_metadata; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE experiment_metadata FROM PUBLIC;
REVOKE ALL ON TABLE experiment_metadata FROM thelma;
GRANT ALL ON TABLE experiment_metadata TO thelma;
GRANT SELECT ON TABLE experiment_metadata TO knime;
GRANT SELECT,INSERT ON TABLE experiment_metadata TO bioinf;


--
-- TOC entry 5190 (class 0 OID 0)
-- Dependencies: 235
-- Name: experiment_metadata_iso_request; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE experiment_metadata_iso_request FROM PUBLIC;
REVOKE ALL ON TABLE experiment_metadata_iso_request FROM gathmann;
GRANT ALL ON TABLE experiment_metadata_iso_request TO gathmann;
GRANT SELECT,INSERT ON TABLE experiment_metadata_iso_request TO bioinf;


--
-- TOC entry 5191 (class 0 OID 0)
-- Dependencies: 236
-- Name: experiment_metadata_molecule_design_set; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE experiment_metadata_molecule_design_set FROM PUBLIC;
REVOKE ALL ON TABLE experiment_metadata_molecule_design_set FROM gathmann;
GRANT ALL ON TABLE experiment_metadata_molecule_design_set TO gathmann;
GRANT SELECT,INSERT ON TABLE experiment_metadata_molecule_design_set TO bioinf;


--
-- TOC entry 5192 (class 0 OID 0)
-- Dependencies: 237
-- Name: experiment_metadata_target_set; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE experiment_metadata_target_set FROM PUBLIC;
REVOKE ALL ON TABLE experiment_metadata_target_set FROM gathmann;
GRANT ALL ON TABLE experiment_metadata_target_set TO gathmann;
GRANT SELECT,INSERT ON TABLE experiment_metadata_target_set TO bioinf;


--
-- TOC entry 5193 (class 0 OID 0)
-- Dependencies: 238
-- Name: experiment_metadata_type; Type: ACL; Schema: public; Owner: berger
--

REVOKE ALL ON TABLE experiment_metadata_type FROM PUBLIC;
REVOKE ALL ON TABLE experiment_metadata_type FROM berger;
GRANT ALL ON TABLE experiment_metadata_type TO berger;
GRANT SELECT,INSERT ON TABLE experiment_metadata_type TO bioinf;


--
-- TOC entry 5194 (class 0 OID 0)
-- Dependencies: 239
-- Name: experiment_sample_experiment_sample_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE experiment_sample_experiment_sample_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE experiment_sample_experiment_sample_id_seq FROM postgres;
GRANT ALL ON SEQUENCE experiment_sample_experiment_sample_id_seq TO postgres;
GRANT USAGE ON SEQUENCE experiment_sample_experiment_sample_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE experiment_sample_experiment_sample_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE experiment_sample_experiment_sample_id_seq TO reader_role;


--
-- TOC entry 5195 (class 0 OID 0)
-- Dependencies: 240
-- Name: experiment_source_rack; Type: ACL; Schema: public; Owner: berger
--

REVOKE ALL ON TABLE experiment_source_rack FROM PUBLIC;
REVOKE ALL ON TABLE experiment_source_rack FROM berger;
GRANT ALL ON TABLE experiment_source_rack TO berger;
GRANT SELECT,INSERT ON TABLE experiment_source_rack TO bioinf;


--
-- TOC entry 5198 (class 0 OID 0)
-- Dependencies: 241
-- Name: external_primer_carrier; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE external_primer_carrier FROM PUBLIC;
REVOKE ALL ON TABLE external_primer_carrier FROM postgres;
GRANT ALL ON TABLE external_primer_carrier TO postgres;
GRANT SELECT ON TABLE external_primer_carrier TO knime;
GRANT SELECT ON TABLE external_primer_carrier TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE external_primer_carrier TO jobscheduler;
GRANT SELECT ON TABLE external_primer_carrier TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE external_primer_carrier TO writer_role;
GRANT SELECT,INSERT ON TABLE external_primer_carrier TO bioinf;


--
-- TOC entry 5206 (class 0 OID 0)
-- Dependencies: 242
-- Name: file; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE file FROM PUBLIC;
REVOKE ALL ON TABLE file FROM postgres;
GRANT ALL ON TABLE file TO postgres;
GRANT ALL ON TABLE file TO pylims;
GRANT ALL ON TABLE file TO bioinf;
GRANT ALL ON TABLE file TO koski;
GRANT ALL ON TABLE file TO walsh;
GRANT ALL ON TABLE file TO celma;
GRANT SELECT ON TABLE file TO knime;
GRANT SELECT ON TABLE file TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE file TO jobscheduler;
GRANT SELECT ON TABLE file TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE file TO writer_role;


--
-- TOC entry 5208 (class 0 OID 0)
-- Dependencies: 243
-- Name: file_file_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE file_file_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE file_file_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE file_file_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE file_file_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE file_file_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE file_file_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE file_file_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE file_file_id_seq TO celma;
GRANT USAGE ON SEQUENCE file_file_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE file_file_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE file_file_id_seq TO reader_role;


--
-- TOC entry 5211 (class 0 OID 0)
-- Dependencies: 244
-- Name: file_set; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE file_set FROM PUBLIC;
REVOKE ALL ON TABLE file_set FROM postgres;
GRANT ALL ON TABLE file_set TO postgres;
GRANT ALL ON TABLE file_set TO pylims;
GRANT ALL ON TABLE file_set TO bioinf;
GRANT ALL ON TABLE file_set TO koski;
GRANT ALL ON TABLE file_set TO walsh;
GRANT ALL ON TABLE file_set TO celma;
GRANT SELECT ON TABLE file_set TO knime;
GRANT SELECT ON TABLE file_set TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE file_set TO jobscheduler;
GRANT SELECT ON TABLE file_set TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE file_set TO writer_role;


--
-- TOC entry 5213 (class 0 OID 0)
-- Dependencies: 245
-- Name: file_set_file_set_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE file_set_file_set_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE file_set_file_set_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE file_set_file_set_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE file_set_file_set_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE file_set_file_set_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE file_set_file_set_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE file_set_file_set_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE file_set_file_set_id_seq TO celma;
GRANT USAGE ON SEQUENCE file_set_file_set_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE file_set_file_set_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE file_set_file_set_id_seq TO reader_role;


--
-- TOC entry 5214 (class 0 OID 0)
-- Dependencies: 246
-- Name: file_set_files; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE file_set_files FROM PUBLIC;
REVOKE ALL ON TABLE file_set_files FROM postgres;
GRANT ALL ON TABLE file_set_files TO postgres;
GRANT ALL ON TABLE file_set_files TO pylims;
GRANT ALL ON TABLE file_set_files TO bioinf;
GRANT ALL ON TABLE file_set_files TO koski;
GRANT ALL ON TABLE file_set_files TO walsh;
GRANT ALL ON TABLE file_set_files TO celma;
GRANT SELECT ON TABLE file_set_files TO knime;
GRANT SELECT ON TABLE file_set_files TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE file_set_files TO jobscheduler;
GRANT SELECT ON TABLE file_set_files TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE file_set_files TO writer_role;


--
-- TOC entry 5219 (class 0 OID 0)
-- Dependencies: 247
-- Name: file_storage_site; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE file_storage_site FROM PUBLIC;
REVOKE ALL ON TABLE file_storage_site FROM postgres;
GRANT ALL ON TABLE file_storage_site TO postgres;
GRANT SELECT ON TABLE file_storage_site TO knime;
GRANT SELECT ON TABLE file_storage_site TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE file_storage_site TO jobscheduler;
GRANT SELECT ON TABLE file_storage_site TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE file_storage_site TO writer_role;
GRANT SELECT,INSERT ON TABLE file_storage_site TO bioinf;


--
-- TOC entry 5221 (class 0 OID 0)
-- Dependencies: 248
-- Name: file_storage_site_file_storage_site_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE file_storage_site_file_storage_site_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE file_storage_site_file_storage_site_id_seq FROM postgres;
GRANT ALL ON SEQUENCE file_storage_site_file_storage_site_id_seq TO postgres;
GRANT USAGE ON SEQUENCE file_storage_site_file_storage_site_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE file_storage_site_file_storage_site_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE file_storage_site_file_storage_site_id_seq TO reader_role;


--
-- TOC entry 5226 (class 0 OID 0)
-- Dependencies: 249
-- Name: file_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE file_type FROM PUBLIC;
REVOKE ALL ON TABLE file_type FROM postgres;
GRANT ALL ON TABLE file_type TO postgres;
GRANT ALL ON TABLE file_type TO pylims;
GRANT ALL ON TABLE file_type TO bioinf;
GRANT ALL ON TABLE file_type TO koski;
GRANT ALL ON TABLE file_type TO walsh;
GRANT ALL ON TABLE file_type TO celma;
GRANT SELECT ON TABLE file_type TO knime;
GRANT SELECT ON TABLE file_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE file_type TO jobscheduler;
GRANT SELECT ON TABLE file_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE file_type TO writer_role;


--
-- TOC entry 5228 (class 0 OID 0)
-- Dependencies: 250
-- Name: file_type_file_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE file_type_file_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE file_type_file_type_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE file_type_file_type_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE file_type_file_type_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE file_type_file_type_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE file_type_file_type_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE file_type_file_type_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE file_type_file_type_id_seq TO celma;
GRANT USAGE ON SEQUENCE file_type_file_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE file_type_file_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE file_type_file_type_id_seq TO reader_role;


--
-- TOC entry 5229 (class 0 OID 0)
-- Dependencies: 251
-- Name: gene_gene_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE gene_gene_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE gene_gene_id_seq FROM postgres;
GRANT ALL ON SEQUENCE gene_gene_id_seq TO postgres;
GRANT USAGE ON SEQUENCE gene_gene_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE gene_gene_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE gene_gene_id_seq TO reader_role;


--
-- TOC entry 5232 (class 0 OID 0)
-- Dependencies: 252
-- Name: gene; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE gene FROM PUBLIC;
REVOKE ALL ON TABLE gene FROM postgres;
GRANT ALL ON TABLE gene TO postgres;
GRANT ALL ON TABLE gene TO pylims;
GRANT ALL ON TABLE gene TO bioinf;
GRANT ALL ON TABLE gene TO koski;
GRANT ALL ON TABLE gene TO walsh;
GRANT ALL ON TABLE gene TO celma;
GRANT SELECT ON TABLE gene TO knime;
GRANT SELECT ON TABLE gene TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE gene TO jobscheduler;
GRANT SELECT ON TABLE gene TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE gene TO writer_role;


--
-- TOC entry 5233 (class 0 OID 0)
-- Dependencies: 253
-- Name: gene2annotation_gene2annotation_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE gene2annotation_gene2annotation_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE gene2annotation_gene2annotation_id_seq FROM postgres;
GRANT ALL ON SEQUENCE gene2annotation_gene2annotation_id_seq TO postgres;
GRANT USAGE ON SEQUENCE gene2annotation_gene2annotation_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE gene2annotation_gene2annotation_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE gene2annotation_gene2annotation_id_seq TO reader_role;


--
-- TOC entry 5235 (class 0 OID 0)
-- Dependencies: 254
-- Name: gene2annotation; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE gene2annotation FROM PUBLIC;
REVOKE ALL ON TABLE gene2annotation FROM postgres;
GRANT ALL ON TABLE gene2annotation TO postgres;
GRANT SELECT ON TABLE gene2annotation TO knime;
GRANT SELECT ON TABLE gene2annotation TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE gene2annotation TO jobscheduler;
GRANT SELECT ON TABLE gene2annotation TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE gene2annotation TO writer_role;
GRANT SELECT,INSERT ON TABLE gene2annotation TO bioinf;


--
-- TOC entry 5237 (class 0 OID 0)
-- Dependencies: 255
-- Name: gene_identifier; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE gene_identifier FROM PUBLIC;
REVOKE ALL ON TABLE gene_identifier FROM postgres;
GRANT ALL ON TABLE gene_identifier TO postgres;
GRANT ALL ON TABLE gene_identifier TO pylims;
GRANT ALL ON TABLE gene_identifier TO bioinf;
GRANT ALL ON TABLE gene_identifier TO koski;
GRANT ALL ON TABLE gene_identifier TO walsh;
GRANT ALL ON TABLE gene_identifier TO celma;
GRANT SELECT ON TABLE gene_identifier TO knime;
GRANT SELECT ON TABLE gene_identifier TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE gene_identifier TO jobscheduler;
GRANT SELECT ON TABLE gene_identifier TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE gene_identifier TO writer_role;


--
-- TOC entry 5239 (class 0 OID 0)
-- Dependencies: 256
-- Name: gene_identifier_gene_identifier_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE gene_identifier_gene_identifier_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE gene_identifier_gene_identifier_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO celma;
GRANT USAGE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE gene_identifier_gene_identifier_id_seq TO reader_role;


--
-- TOC entry 5241 (class 0 OID 0)
-- Dependencies: 257
-- Name: humane_rack; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE humane_rack FROM PUBLIC;
REVOKE ALL ON TABLE humane_rack FROM postgres;
GRANT ALL ON TABLE humane_rack TO postgres;
GRANT SELECT ON TABLE humane_rack TO knime;
GRANT SELECT ON TABLE humane_rack TO ppfinder;
GRANT SELECT ON TABLE humane_rack TO jobscheduler;
GRANT SELECT,INSERT ON TABLE humane_rack TO bioinf;


--
-- TOC entry 5242 (class 0 OID 0)
-- Dependencies: 258
-- Name: hybridization_hybridization_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE hybridization_hybridization_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE hybridization_hybridization_id_seq FROM postgres;
GRANT ALL ON SEQUENCE hybridization_hybridization_id_seq TO postgres;
GRANT USAGE ON SEQUENCE hybridization_hybridization_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE hybridization_hybridization_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE hybridization_hybridization_id_seq TO reader_role;


--
-- TOC entry 5245 (class 0 OID 0)
-- Dependencies: 259
-- Name: image_analysis_task_item; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE image_analysis_task_item FROM PUBLIC;
REVOKE ALL ON TABLE image_analysis_task_item FROM postgres;
GRANT ALL ON TABLE image_analysis_task_item TO postgres;
GRANT SELECT ON TABLE image_analysis_task_item TO knime;
GRANT SELECT ON TABLE image_analysis_task_item TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE image_analysis_task_item TO jobscheduler;
GRANT SELECT ON TABLE image_analysis_task_item TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE image_analysis_task_item TO writer_role;
GRANT SELECT,INSERT ON TABLE image_analysis_task_item TO bioinf;


--
-- TOC entry 5246 (class 0 OID 0)
-- Dependencies: 260
-- Name: image_object_image_object_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE image_object_image_object_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE image_object_image_object_id_seq FROM postgres;
GRANT ALL ON SEQUENCE image_object_image_object_id_seq TO postgres;
GRANT USAGE ON SEQUENCE image_object_image_object_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE image_object_image_object_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE image_object_image_object_id_seq TO reader_role;


--
-- TOC entry 5248 (class 0 OID 0)
-- Dependencies: 261
-- Name: intended_mirna_target; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE intended_mirna_target FROM PUBLIC;
REVOKE ALL ON TABLE intended_mirna_target FROM postgres;
GRANT ALL ON TABLE intended_mirna_target TO postgres;
GRANT SELECT ON TABLE intended_mirna_target TO knime;
GRANT SELECT ON TABLE intended_mirna_target TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE intended_mirna_target TO jobscheduler;
GRANT SELECT ON TABLE intended_mirna_target TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE intended_mirna_target TO writer_role;
GRANT SELECT,INSERT ON TABLE intended_mirna_target TO bioinf;


--
-- TOC entry 5250 (class 0 OID 0)
-- Dependencies: 262
-- Name: intended_target; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE intended_target FROM PUBLIC;
REVOKE ALL ON TABLE intended_target FROM postgres;
GRANT ALL ON TABLE intended_target TO postgres;
GRANT SELECT ON TABLE intended_target TO knime;
GRANT SELECT ON TABLE intended_target TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE intended_target TO jobscheduler;
GRANT SELECT ON TABLE intended_target TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE intended_target TO writer_role;
GRANT SELECT,INSERT ON TABLE intended_target TO bioinf;


--
-- TOC entry 5252 (class 0 OID 0)
-- Dependencies: 263
-- Name: iso; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE iso FROM PUBLIC;
REVOKE ALL ON TABLE iso FROM thelma;
GRANT ALL ON TABLE iso TO thelma;
GRANT SELECT,INSERT ON TABLE iso TO bioinf;


--
-- TOC entry 5254 (class 0 OID 0)
-- Dependencies: 267
-- Name: iso_job_member; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE iso_job_member FROM PUBLIC;
REVOKE ALL ON TABLE iso_job_member FROM thelma;
GRANT ALL ON TABLE iso_job_member TO thelma;
GRANT SELECT,INSERT ON TABLE iso_job_member TO bioinf;


--
-- TOC entry 5256 (class 0 OID 0)
-- Dependencies: 271
-- Name: iso_molecule_design_set; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE iso_molecule_design_set FROM PUBLIC;
REVOKE ALL ON TABLE iso_molecule_design_set FROM gathmann;
GRANT ALL ON TABLE iso_molecule_design_set TO gathmann;
GRANT SELECT,INSERT ON TABLE iso_molecule_design_set TO bioinf;


--
-- TOC entry 5258 (class 0 OID 0)
-- Dependencies: 274
-- Name: iso_pool_set; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE iso_pool_set FROM PUBLIC;
REVOKE ALL ON TABLE iso_pool_set FROM gathmann;
GRANT ALL ON TABLE iso_pool_set TO gathmann;
GRANT SELECT,INSERT ON TABLE iso_pool_set TO bioinf;


--
-- TOC entry 5259 (class 0 OID 0)
-- Dependencies: 276
-- Name: iso_racks; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE iso_racks FROM PUBLIC;
REVOKE ALL ON TABLE iso_racks FROM thelma;
GRANT ALL ON TABLE iso_racks TO thelma;
GRANT SELECT,INSERT ON TABLE iso_racks TO bioinf;


--
-- TOC entry 5261 (class 0 OID 0)
-- Dependencies: 277
-- Name: iso_request; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE iso_request FROM PUBLIC;
REVOKE ALL ON TABLE iso_request FROM thelma;
GRANT ALL ON TABLE iso_request TO thelma;
GRANT SELECT,INSERT ON TABLE iso_request TO bioinf;


--
-- TOC entry 5263 (class 0 OID 0)
-- Dependencies: 282
-- Name: item_status; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE item_status FROM PUBLIC;
REVOKE ALL ON TABLE item_status FROM postgres;
GRANT ALL ON TABLE item_status TO postgres;
GRANT SELECT ON TABLE item_status TO knime;
GRANT SELECT ON TABLE item_status TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE item_status TO jobscheduler;
GRANT SELECT ON TABLE item_status TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE item_status TO writer_role;
GRANT SELECT,INSERT ON TABLE item_status TO bioinf;


--
-- TOC entry 5273 (class 0 OID 0)
-- Dependencies: 283
-- Name: job; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE job FROM PUBLIC;
REVOKE ALL ON TABLE job FROM postgres;
GRANT ALL ON TABLE job TO postgres;
GRANT ALL ON TABLE job TO celma;
GRANT SELECT ON TABLE job TO knime;
GRANT SELECT ON TABLE job TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE job TO jobscheduler;
GRANT SELECT ON TABLE job TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE job TO writer_role;
GRANT SELECT,INSERT ON TABLE job TO bioinf;


--
-- TOC entry 5275 (class 0 OID 0)
-- Dependencies: 284
-- Name: job_job_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE job_job_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE job_job_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE job_job_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE job_job_id_seq TO celma;
GRANT USAGE ON SEQUENCE job_job_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE job_job_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE job_job_id_seq TO reader_role;


--
-- TOC entry 5281 (class 0 OID 0)
-- Dependencies: 285
-- Name: job_step; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE job_step FROM PUBLIC;
REVOKE ALL ON TABLE job_step FROM postgres;
GRANT ALL ON TABLE job_step TO postgres;
GRANT ALL ON TABLE job_step TO celma;
GRANT SELECT ON TABLE job_step TO knime;
GRANT SELECT ON TABLE job_step TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE job_step TO jobscheduler;
GRANT SELECT ON TABLE job_step TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE job_step TO writer_role;
GRANT SELECT,INSERT ON TABLE job_step TO bioinf;


--
-- TOC entry 5282 (class 0 OID 0)
-- Dependencies: 286
-- Name: job_step_job_step_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE job_step_job_step_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE job_step_job_step_id_seq FROM postgres;
GRANT ALL ON SEQUENCE job_step_job_step_id_seq TO postgres;
GRANT USAGE ON SEQUENCE job_step_job_step_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE job_step_job_step_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE job_step_job_step_id_seq TO reader_role;


--
-- TOC entry 5288 (class 0 OID 0)
-- Dependencies: 287
-- Name: job_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE job_type FROM PUBLIC;
REVOKE ALL ON TABLE job_type FROM postgres;
GRANT ALL ON TABLE job_type TO postgres;
GRANT ALL ON TABLE job_type TO celma;
GRANT SELECT ON TABLE job_type TO knime;
GRANT SELECT ON TABLE job_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE job_type TO jobscheduler;
GRANT SELECT ON TABLE job_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE job_type TO writer_role;
GRANT SELECT,INSERT ON TABLE job_type TO bioinf;


--
-- TOC entry 5290 (class 0 OID 0)
-- Dependencies: 288
-- Name: job_type_job_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE job_type_job_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE job_type_job_type_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE job_type_job_type_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE job_type_job_type_id_seq TO celma;
GRANT USAGE ON SEQUENCE job_type_job_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE job_type_job_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE job_type_job_type_id_seq TO reader_role;


--
-- TOC entry 5292 (class 0 OID 0)
-- Dependencies: 291
-- Name: legacy_primer_pair; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE legacy_primer_pair FROM PUBLIC;
REVOKE ALL ON TABLE legacy_primer_pair FROM postgres;
GRANT ALL ON TABLE legacy_primer_pair TO postgres;
GRANT SELECT ON TABLE legacy_primer_pair TO knime;
GRANT SELECT ON TABLE legacy_primer_pair TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE legacy_primer_pair TO jobscheduler;
GRANT SELECT ON TABLE legacy_primer_pair TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE legacy_primer_pair TO writer_role;
GRANT SELECT,INSERT ON TABLE legacy_primer_pair TO bioinf;


--
-- TOC entry 5298 (class 0 OID 0)
-- Dependencies: 294
-- Name: liquid_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE liquid_type FROM PUBLIC;
REVOKE ALL ON TABLE liquid_type FROM postgres;
GRANT ALL ON TABLE liquid_type TO postgres;
GRANT SELECT ON TABLE liquid_type TO knime;
GRANT SELECT ON TABLE liquid_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE liquid_type TO jobscheduler;
GRANT SELECT ON TABLE liquid_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE liquid_type TO writer_role;
GRANT SELECT,INSERT ON TABLE liquid_type TO bioinf;


--
-- TOC entry 5300 (class 0 OID 0)
-- Dependencies: 295
-- Name: liquid_type_liquid_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE liquid_type_liquid_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE liquid_type_liquid_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE liquid_type_liquid_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE liquid_type_liquid_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE liquid_type_liquid_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE liquid_type_liquid_type_id_seq TO reader_role;


--
-- TOC entry 5302 (class 0 OID 0)
-- Dependencies: 296
-- Name: mirna; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE mirna FROM PUBLIC;
REVOKE ALL ON TABLE mirna FROM postgres;
GRANT ALL ON TABLE mirna TO postgres;
GRANT SELECT ON TABLE mirna TO knime;
GRANT SELECT ON TABLE mirna TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE mirna TO jobscheduler;
GRANT SELECT ON TABLE mirna TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE mirna TO writer_role;
GRANT SELECT,INSERT ON TABLE mirna TO bioinf;


--
-- TOC entry 5306 (class 0 OID 0)
-- Dependencies: 297
-- Name: molecule; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE molecule FROM PUBLIC;
REVOKE ALL ON TABLE molecule FROM postgres;
GRANT ALL ON TABLE molecule TO postgres;
GRANT ALL ON TABLE molecule TO pylims;
GRANT ALL ON TABLE molecule TO bioinf;
GRANT ALL ON TABLE molecule TO koski;
GRANT ALL ON TABLE molecule TO walsh;
GRANT ALL ON TABLE molecule TO celma;
GRANT SELECT ON TABLE molecule TO knime;
GRANT SELECT ON TABLE molecule TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE molecule TO jobscheduler;
GRANT SELECT ON TABLE molecule TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE molecule TO writer_role;


--
-- TOC entry 5310 (class 0 OID 0)
-- Dependencies: 298
-- Name: molecule_design; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE molecule_design FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design FROM postgres;
GRANT ALL ON TABLE molecule_design TO postgres;
GRANT SELECT ON TABLE molecule_design TO knime;
GRANT SELECT ON TABLE molecule_design TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE molecule_design TO jobscheduler;
GRANT SELECT ON TABLE molecule_design TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE molecule_design TO writer_role;
GRANT SELECT,INSERT ON TABLE molecule_design TO bioinf;


--
-- TOC entry 5312 (class 0 OID 0)
-- Dependencies: 299
-- Name: molecule_design_gene; Type: ACL; Schema: public; Owner: cebos
--

REVOKE ALL ON TABLE molecule_design_gene FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_gene FROM cebos;
GRANT ALL ON TABLE molecule_design_gene TO cebos;
GRANT ALL ON TABLE molecule_design_gene TO bioinf;


--
-- TOC entry 5314 (class 0 OID 0)
-- Dependencies: 300
-- Name: molecule_design_versioned_transcript_target; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE molecule_design_versioned_transcript_target FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_versioned_transcript_target FROM postgres;
GRANT ALL ON TABLE molecule_design_versioned_transcript_target TO postgres;
GRANT SELECT ON TABLE molecule_design_versioned_transcript_target TO knime;
GRANT SELECT ON TABLE molecule_design_versioned_transcript_target TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE molecule_design_versioned_transcript_target TO jobscheduler;
GRANT SELECT ON TABLE molecule_design_versioned_transcript_target TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE molecule_design_versioned_transcript_target TO writer_role;
GRANT SELECT,INSERT ON TABLE molecule_design_versioned_transcript_target TO bioinf;


--
-- TOC entry 5316 (class 0 OID 0)
-- Dependencies: 301
-- Name: release_gene_transcript; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE release_gene_transcript FROM PUBLIC;
REVOKE ALL ON TABLE release_gene_transcript FROM postgres;
GRANT ALL ON TABLE release_gene_transcript TO postgres;
GRANT SELECT ON TABLE release_gene_transcript TO knime;
GRANT SELECT ON TABLE release_gene_transcript TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE release_gene_transcript TO jobscheduler;
GRANT SELECT ON TABLE release_gene_transcript TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE release_gene_transcript TO writer_role;
GRANT SELECT,INSERT ON TABLE release_gene_transcript TO bioinf;


--
-- TOC entry 5318 (class 0 OID 0)
-- Dependencies: 302
-- Name: release_versioned_transcript; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE release_versioned_transcript FROM PUBLIC;
REVOKE ALL ON TABLE release_versioned_transcript FROM postgres;
GRANT ALL ON TABLE release_versioned_transcript TO postgres;
GRANT SELECT ON TABLE release_versioned_transcript TO knime;
GRANT SELECT ON TABLE release_versioned_transcript TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE release_versioned_transcript TO jobscheduler;
GRANT SELECT ON TABLE release_versioned_transcript TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE release_versioned_transcript TO writer_role;
GRANT SELECT,INSERT ON TABLE release_versioned_transcript TO bioinf;


--
-- TOC entry 5319 (class 0 OID 0)
-- Dependencies: 303
-- Name: versioned_transcript_versioned_transcript_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE versioned_transcript_versioned_transcript_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE versioned_transcript_versioned_transcript_id_seq FROM postgres;
GRANT ALL ON SEQUENCE versioned_transcript_versioned_transcript_id_seq TO postgres;
GRANT USAGE ON SEQUENCE versioned_transcript_versioned_transcript_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE versioned_transcript_versioned_transcript_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE versioned_transcript_versioned_transcript_id_seq TO reader_role;


--
-- TOC entry 5321 (class 0 OID 0)
-- Dependencies: 304
-- Name: versioned_transcript; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE versioned_transcript FROM PUBLIC;
REVOKE ALL ON TABLE versioned_transcript FROM postgres;
GRANT ALL ON TABLE versioned_transcript TO postgres;
GRANT SELECT ON TABLE versioned_transcript TO knime;
GRANT SELECT ON TABLE versioned_transcript TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE versioned_transcript TO jobscheduler;
GRANT SELECT ON TABLE versioned_transcript TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE versioned_transcript TO writer_role;
GRANT SELECT,INSERT ON TABLE versioned_transcript TO bioinf;


--
-- TOC entry 5323 (class 0 OID 0)
-- Dependencies: 305
-- Name: molecule_design_gene_view; Type: ACL; Schema: public; Owner: cebos
--

REVOKE ALL ON TABLE molecule_design_gene_view FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_gene_view FROM cebos;
GRANT ALL ON TABLE molecule_design_gene_view TO cebos;
GRANT ALL ON TABLE molecule_design_gene_view TO bioinf;


--
-- TOC entry 5324 (class 0 OID 0)
-- Dependencies: 306
-- Name: molecule_design_library; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_library FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_library FROM gathmann;
GRANT ALL ON TABLE molecule_design_library TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_library TO bioinf;


--
-- TOC entry 5325 (class 0 OID 0)
-- Dependencies: 307
-- Name: molecule_design_library_creation_iso_request; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_library_creation_iso_request FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_library_creation_iso_request FROM gathmann;
GRANT ALL ON TABLE molecule_design_library_creation_iso_request TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_library_creation_iso_request TO bioinf;


--
-- TOC entry 5328 (class 0 OID 0)
-- Dependencies: 310
-- Name: molecule_design_mirna_target; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE molecule_design_mirna_target FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_mirna_target FROM postgres;
GRANT ALL ON TABLE molecule_design_mirna_target TO postgres;
GRANT SELECT ON TABLE molecule_design_mirna_target TO knime;
GRANT SELECT ON TABLE molecule_design_mirna_target TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE molecule_design_mirna_target TO jobscheduler;
GRANT SELECT ON TABLE molecule_design_mirna_target TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE molecule_design_mirna_target TO writer_role;
GRANT SELECT,INSERT ON TABLE molecule_design_mirna_target TO bioinf;


--
-- TOC entry 5330 (class 0 OID 0)
-- Dependencies: 311
-- Name: molecule_design_molecule_design_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE molecule_design_molecule_design_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE molecule_design_molecule_design_id_seq FROM postgres;
GRANT ALL ON SEQUENCE molecule_design_molecule_design_id_seq TO postgres;
GRANT USAGE ON SEQUENCE molecule_design_molecule_design_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE molecule_design_molecule_design_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE molecule_design_molecule_design_id_seq TO reader_role;


--
-- TOC entry 5331 (class 0 OID 0)
-- Dependencies: 312
-- Name: molecule_design_pool; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_pool FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_pool FROM gathmann;
GRANT ALL ON TABLE molecule_design_pool TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_pool TO bioinf;


--
-- TOC entry 5332 (class 0 OID 0)
-- Dependencies: 313
-- Name: molecule_design_pool_molecule_design_pool_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE molecule_design_pool_molecule_design_pool_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE molecule_design_pool_molecule_design_pool_id_seq FROM postgres;
GRANT ALL ON SEQUENCE molecule_design_pool_molecule_design_pool_id_seq TO postgres;
GRANT USAGE ON SEQUENCE molecule_design_pool_molecule_design_pool_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE molecule_design_pool_molecule_design_pool_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE molecule_design_pool_molecule_design_pool_id_seq TO reader_role;


--
-- TOC entry 5333 (class 0 OID 0)
-- Dependencies: 314
-- Name: molecule_design_pool_set; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_pool_set FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_pool_set FROM gathmann;
GRANT ALL ON TABLE molecule_design_pool_set TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_pool_set TO bioinf;


--
-- TOC entry 5334 (class 0 OID 0)
-- Dependencies: 315
-- Name: molecule_design_pool_set_member; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_pool_set_member FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_pool_set_member FROM gathmann;
GRANT ALL ON TABLE molecule_design_pool_set_member TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_pool_set_member TO bioinf;


--
-- TOC entry 5336 (class 0 OID 0)
-- Dependencies: 316
-- Name: molecule_design_set; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE molecule_design_set FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_set FROM thelma;
GRANT ALL ON TABLE molecule_design_set TO thelma;
GRANT SELECT,INSERT ON TABLE molecule_design_set TO bioinf;


--
-- TOC entry 5338 (class 0 OID 0)
-- Dependencies: 317
-- Name: molecule_design_set_gene; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_set_gene FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_set_gene FROM gathmann;
GRANT ALL ON TABLE molecule_design_set_gene TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_set_gene TO bioinf;


--
-- TOC entry 5340 (class 0 OID 0)
-- Dependencies: 318
-- Name: molecule_design_set_member; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE molecule_design_set_member FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_set_member FROM thelma;
GRANT ALL ON TABLE molecule_design_set_member TO thelma;
GRANT SELECT,INSERT ON TABLE molecule_design_set_member TO bioinf;


--
-- TOC entry 5341 (class 0 OID 0)
-- Dependencies: 319
-- Name: molecule_design_set_gene_view; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_set_gene_view FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_set_gene_view FROM gathmann;
GRANT ALL ON TABLE molecule_design_set_gene_view TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_set_gene_view TO bioinf;


--
-- TOC entry 5344 (class 0 OID 0)
-- Dependencies: 321
-- Name: molecule_design_set_target_set; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE molecule_design_set_target_set FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_set_target_set FROM thelma;
GRANT ALL ON TABLE molecule_design_set_target_set TO thelma;
GRANT SELECT,INSERT ON TABLE molecule_design_set_target_set TO bioinf;


--
-- TOC entry 5346 (class 0 OID 0)
-- Dependencies: 322
-- Name: molecule_design_structure; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_design_structure FROM PUBLIC;
REVOKE ALL ON TABLE molecule_design_structure FROM gathmann;
GRANT ALL ON TABLE molecule_design_structure TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_design_structure TO bioinf;


--
-- TOC entry 5348 (class 0 OID 0)
-- Dependencies: 323
-- Name: molecule_molecule_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE molecule_molecule_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE molecule_molecule_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE molecule_molecule_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE molecule_molecule_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE molecule_molecule_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE molecule_molecule_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE molecule_molecule_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE molecule_molecule_id_seq TO celma;
GRANT USAGE ON SEQUENCE molecule_molecule_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE molecule_molecule_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE molecule_molecule_id_seq TO reader_role;


--
-- TOC entry 5351 (class 0 OID 0)
-- Dependencies: 324
-- Name: molecule_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE molecule_type FROM PUBLIC;
REVOKE ALL ON TABLE molecule_type FROM postgres;
GRANT ALL ON TABLE molecule_type TO postgres;
GRANT SELECT ON TABLE molecule_type TO knime;
GRANT SELECT ON TABLE molecule_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE molecule_type TO jobscheduler;
GRANT SELECT ON TABLE molecule_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE molecule_type TO writer_role;
GRANT SELECT,INSERT ON TABLE molecule_type TO bioinf;


--
-- TOC entry 5352 (class 0 OID 0)
-- Dependencies: 325
-- Name: molecule_type_modification_view; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE molecule_type_modification_view FROM PUBLIC;
REVOKE ALL ON TABLE molecule_type_modification_view FROM gathmann;
GRANT ALL ON TABLE molecule_type_modification_view TO gathmann;
GRANT SELECT,INSERT ON TABLE molecule_type_modification_view TO bioinf;


--
-- TOC entry 5354 (class 0 OID 0)
-- Dependencies: 326
-- Name: new_experiment; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE new_experiment FROM PUBLIC;
REVOKE ALL ON TABLE new_experiment FROM thelma;
GRANT ALL ON TABLE new_experiment TO thelma;
GRANT SELECT ON TABLE new_experiment TO knime;
GRANT SELECT,INSERT ON TABLE new_experiment TO bioinf;


--
-- TOC entry 5357 (class 0 OID 0)
-- Dependencies: 328
-- Name: new_experiment_rack; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE new_experiment_rack FROM PUBLIC;
REVOKE ALL ON TABLE new_experiment_rack FROM thelma;
GRANT ALL ON TABLE new_experiment_rack TO thelma;
GRANT SELECT ON TABLE new_experiment_rack TO knime;
GRANT SELECT,INSERT ON TABLE new_experiment_rack TO bioinf;


--
-- TOC entry 5359 (class 0 OID 0)
-- Dependencies: 330
-- Name: new_file_storage_site_file_storage_site_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE new_file_storage_site_file_storage_site_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE new_file_storage_site_file_storage_site_id_seq FROM postgres;
GRANT ALL ON SEQUENCE new_file_storage_site_file_storage_site_id_seq TO postgres;
GRANT USAGE ON SEQUENCE new_file_storage_site_file_storage_site_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE new_file_storage_site_file_storage_site_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE new_file_storage_site_file_storage_site_id_seq TO reader_role;


--
-- TOC entry 5361 (class 0 OID 0)
-- Dependencies: 333
-- Name: new_sequence_sequence_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE new_sequence_sequence_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE new_sequence_sequence_id_seq FROM postgres;
GRANT ALL ON SEQUENCE new_sequence_sequence_id_seq TO postgres;
GRANT USAGE ON SEQUENCE new_sequence_sequence_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE new_sequence_sequence_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE new_sequence_sequence_id_seq TO reader_role;


--
-- TOC entry 5366 (class 0 OID 0)
-- Dependencies: 334
-- Name: order_sample_set; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE order_sample_set FROM PUBLIC;
REVOKE ALL ON TABLE order_sample_set FROM postgres;
GRANT ALL ON TABLE order_sample_set TO postgres;
GRANT ALL ON TABLE order_sample_set TO celma;
GRANT SELECT ON TABLE order_sample_set TO knime;
GRANT SELECT ON TABLE order_sample_set TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE order_sample_set TO jobscheduler;
GRANT SELECT ON TABLE order_sample_set TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE order_sample_set TO writer_role;
GRANT SELECT,INSERT ON TABLE order_sample_set TO bioinf;


--
-- TOC entry 5367 (class 0 OID 0)
-- Dependencies: 335
-- Name: organization_organization_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE organization_organization_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE organization_organization_id_seq FROM postgres;
GRANT ALL ON SEQUENCE organization_organization_id_seq TO postgres;
GRANT USAGE ON SEQUENCE organization_organization_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE organization_organization_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE organization_organization_id_seq TO reader_role;


--
-- TOC entry 5371 (class 0 OID 0)
-- Dependencies: 336
-- Name: organization; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE organization FROM PUBLIC;
REVOKE ALL ON TABLE organization FROM postgres;
GRANT ALL ON TABLE organization TO postgres;
GRANT SELECT ON TABLE organization TO knime;
GRANT SELECT ON TABLE organization TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE organization TO jobscheduler;
GRANT SELECT ON TABLE organization TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE organization TO writer_role;
GRANT SELECT,INSERT ON TABLE organization TO bioinf;


--
-- TOC entry 5372 (class 0 OID 0)
-- Dependencies: 337
-- Name: origin_type_origin_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE origin_type_origin_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE origin_type_origin_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE origin_type_origin_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE origin_type_origin_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE origin_type_origin_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE origin_type_origin_type_id_seq TO reader_role;


--
-- TOC entry 5373 (class 0 OID 0)
-- Dependencies: 338
-- Name: pipetting_specs; Type: ACL; Schema: public; Owner: berger
--

REVOKE ALL ON TABLE pipetting_specs FROM PUBLIC;
REVOKE ALL ON TABLE pipetting_specs FROM berger;
GRANT ALL ON TABLE pipetting_specs TO berger;
GRANT SELECT,INSERT ON TABLE pipetting_specs TO bioinf;


--
-- TOC entry 5375 (class 0 OID 0)
-- Dependencies: 340
-- Name: planned_liquid_transfer; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE planned_liquid_transfer FROM PUBLIC;
REVOKE ALL ON TABLE planned_liquid_transfer FROM gathmann;
GRANT ALL ON TABLE planned_liquid_transfer TO gathmann;


--
-- TOC entry 5377 (class 0 OID 0)
-- Dependencies: 342
-- Name: planned_rack_sample_transfer; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE planned_rack_sample_transfer FROM PUBLIC;
REVOKE ALL ON TABLE planned_rack_sample_transfer FROM gathmann;
GRANT ALL ON TABLE planned_rack_sample_transfer TO gathmann;


--
-- TOC entry 5378 (class 0 OID 0)
-- Dependencies: 343
-- Name: planned_sample_dilution; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE planned_sample_dilution FROM PUBLIC;
REVOKE ALL ON TABLE planned_sample_dilution FROM gathmann;
GRANT ALL ON TABLE planned_sample_dilution TO gathmann;


--
-- TOC entry 5379 (class 0 OID 0)
-- Dependencies: 344
-- Name: planned_sample_transfer; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE planned_sample_transfer FROM PUBLIC;
REVOKE ALL ON TABLE planned_sample_transfer FROM gathmann;
GRANT ALL ON TABLE planned_sample_transfer TO gathmann;


--
-- TOC entry 5380 (class 0 OID 0)
-- Dependencies: 345
-- Name: planned_worklist; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE planned_worklist FROM PUBLIC;
REVOKE ALL ON TABLE planned_worklist FROM thelma;
GRANT ALL ON TABLE planned_worklist TO thelma;
GRANT SELECT,INSERT ON TABLE planned_worklist TO bioinf;


--
-- TOC entry 5381 (class 0 OID 0)
-- Dependencies: 346
-- Name: planned_worklist_member; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE planned_worklist_member FROM PUBLIC;
REVOKE ALL ON TABLE planned_worklist_member FROM gathmann;
GRANT ALL ON TABLE planned_worklist_member TO gathmann;


--
-- TOC entry 5384 (class 0 OID 0)
-- Dependencies: 349
-- Name: pooled_supplier_molecule_design; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE pooled_supplier_molecule_design FROM PUBLIC;
REVOKE ALL ON TABLE pooled_supplier_molecule_design FROM gathmann;
GRANT ALL ON TABLE pooled_supplier_molecule_design TO gathmann;
GRANT SELECT,INSERT ON TABLE pooled_supplier_molecule_design TO bioinf;


--
-- TOC entry 5385 (class 0 OID 0)
-- Dependencies: 350
-- Name: primer_pair_primer_pair_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE primer_pair_primer_pair_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE primer_pair_primer_pair_id_seq FROM postgres;
GRANT ALL ON SEQUENCE primer_pair_primer_pair_id_seq TO postgres;
GRANT USAGE ON SEQUENCE primer_pair_primer_pair_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE primer_pair_primer_pair_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE primer_pair_primer_pair_id_seq TO reader_role;


--
-- TOC entry 5387 (class 0 OID 0)
-- Dependencies: 351
-- Name: primer_pair; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE primer_pair FROM PUBLIC;
REVOKE ALL ON TABLE primer_pair FROM postgres;
GRANT ALL ON TABLE primer_pair TO postgres;
GRANT SELECT ON TABLE primer_pair TO knime;
GRANT SELECT ON TABLE primer_pair TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE primer_pair TO jobscheduler;
GRANT SELECT ON TABLE primer_pair TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE primer_pair TO writer_role;
GRANT SELECT,INSERT ON TABLE primer_pair TO bioinf;


--
-- TOC entry 5390 (class 0 OID 0)
-- Dependencies: 352
-- Name: species; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE species FROM PUBLIC;
REVOKE ALL ON TABLE species FROM postgres;
GRANT ALL ON TABLE species TO postgres;
GRANT ALL ON TABLE species TO pylims;
GRANT ALL ON TABLE species TO bioinf;
GRANT ALL ON TABLE species TO koski;
GRANT ALL ON TABLE species TO walsh;
GRANT ALL ON TABLE species TO celma;
GRANT SELECT ON TABLE species TO knime;
GRANT SELECT ON TABLE species TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE species TO jobscheduler;
GRANT SELECT ON TABLE species TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE species TO writer_role;


--
-- TOC entry 5391 (class 0 OID 0)
-- Dependencies: 353
-- Name: transcript_transcript_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE transcript_transcript_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE transcript_transcript_id_seq FROM postgres;
GRANT ALL ON SEQUENCE transcript_transcript_id_seq TO postgres;
GRANT USAGE ON SEQUENCE transcript_transcript_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE transcript_transcript_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE transcript_transcript_id_seq TO reader_role;


--
-- TOC entry 5394 (class 0 OID 0)
-- Dependencies: 354
-- Name: transcript; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE transcript FROM PUBLIC;
REVOKE ALL ON TABLE transcript FROM postgres;
GRANT ALL ON TABLE transcript TO postgres;
GRANT ALL ON TABLE transcript TO pylims;
GRANT ALL ON TABLE transcript TO bioinf;
GRANT ALL ON TABLE transcript TO koski;
GRANT ALL ON TABLE transcript TO walsh;
GRANT ALL ON TABLE transcript TO celma;
GRANT SELECT ON TABLE transcript TO knime;
GRANT SELECT ON TABLE transcript TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE transcript TO jobscheduler;
GRANT SELECT ON TABLE transcript TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE transcript TO writer_role;


--
-- TOC entry 5398 (class 0 OID 0)
-- Dependencies: 355
-- Name: versioned_transcript_amplicon; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE versioned_transcript_amplicon FROM PUBLIC;
REVOKE ALL ON TABLE versioned_transcript_amplicon FROM postgres;
GRANT ALL ON TABLE versioned_transcript_amplicon TO postgres;
GRANT SELECT ON TABLE versioned_transcript_amplicon TO knime;
GRANT SELECT ON TABLE versioned_transcript_amplicon TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE versioned_transcript_amplicon TO jobscheduler;
GRANT SELECT ON TABLE versioned_transcript_amplicon TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE versioned_transcript_amplicon TO writer_role;
GRANT SELECT,INSERT ON TABLE versioned_transcript_amplicon TO bioinf;


--
-- TOC entry 5400 (class 0 OID 0)
-- Dependencies: 356
-- Name: primer_pair_target_view; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE primer_pair_target_view FROM PUBLIC;
REVOKE ALL ON TABLE primer_pair_target_view FROM postgres;
GRANT ALL ON TABLE primer_pair_target_view TO postgres;
GRANT SELECT ON TABLE primer_pair_target_view TO knime;
GRANT SELECT ON TABLE primer_pair_target_view TO ppfinder;
GRANT SELECT ON TABLE primer_pair_target_view TO jobscheduler;
GRANT SELECT,INSERT ON TABLE primer_pair_target_view TO bioinf;


--
-- TOC entry 5407 (class 0 OID 0)
-- Dependencies: 357
-- Name: primer_validation; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE primer_validation FROM PUBLIC;
REVOKE ALL ON TABLE primer_validation FROM postgres;
GRANT ALL ON TABLE primer_validation TO postgres;
GRANT SELECT ON TABLE primer_validation TO knime;
GRANT SELECT ON TABLE primer_validation TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE primer_validation TO jobscheduler;
GRANT SELECT ON TABLE primer_validation TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE primer_validation TO writer_role;
GRANT SELECT,INSERT ON TABLE primer_validation TO bioinf;


--
-- TOC entry 5410 (class 0 OID 0)
-- Dependencies: 358
-- Name: printer; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE printer FROM PUBLIC;
REVOKE ALL ON TABLE printer FROM postgres;
GRANT ALL ON TABLE printer TO postgres;
GRANT SELECT ON TABLE printer TO knime;
GRANT SELECT ON TABLE printer TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE printer TO jobscheduler;
GRANT SELECT ON TABLE printer TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE printer TO writer_role;
GRANT SELECT,INSERT ON TABLE printer TO bioinf;


--
-- TOC entry 5417 (class 0 OID 0)
-- Dependencies: 359
-- Name: project; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE project FROM PUBLIC;
REVOKE ALL ON TABLE project FROM postgres;
GRANT ALL ON TABLE project TO postgres;
GRANT SELECT ON TABLE project TO knime;
GRANT SELECT ON TABLE project TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE project TO jobscheduler;
GRANT SELECT ON TABLE project TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE project TO writer_role;
GRANT SELECT,INSERT ON TABLE project TO bioinf;


--
-- TOC entry 5419 (class 0 OID 0)
-- Dependencies: 360
-- Name: project_project_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE project_project_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE project_project_id_seq FROM postgres;
GRANT ALL ON SEQUENCE project_project_id_seq TO postgres;
GRANT USAGE ON SEQUENCE project_project_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE project_project_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE project_project_id_seq TO reader_role;


--
-- TOC entry 5422 (class 0 OID 0)
-- Dependencies: 361
-- Name: rack_barcoded_location; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_barcoded_location FROM PUBLIC;
REVOKE ALL ON TABLE rack_barcoded_location FROM postgres;
GRANT ALL ON TABLE rack_barcoded_location TO postgres;
GRANT SELECT ON TABLE rack_barcoded_location TO knime;
GRANT SELECT ON TABLE rack_barcoded_location TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_barcoded_location TO jobscheduler;
GRANT SELECT ON TABLE rack_barcoded_location TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_barcoded_location TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_barcoded_location TO bioinf;


--
-- TOC entry 5424 (class 0 OID 0)
-- Dependencies: 362
-- Name: rack_barcoded_location_log; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_barcoded_location_log FROM PUBLIC;
REVOKE ALL ON TABLE rack_barcoded_location_log FROM postgres;
GRANT ALL ON TABLE rack_barcoded_location_log TO postgres;
GRANT SELECT ON TABLE rack_barcoded_location_log TO knime;
GRANT SELECT ON TABLE rack_barcoded_location_log TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_barcoded_location_log TO jobscheduler;
GRANT SELECT ON TABLE rack_barcoded_location_log TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_barcoded_location_log TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_barcoded_location_log TO bioinf;


--
-- TOC entry 5426 (class 0 OID 0)
-- Dependencies: 363
-- Name: rack_info; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_info FROM PUBLIC;
REVOKE ALL ON TABLE rack_info FROM postgres;
GRANT ALL ON TABLE rack_info TO postgres;
GRANT SELECT ON TABLE rack_info TO knime;
GRANT SELECT ON TABLE rack_info TO ppfinder;
GRANT SELECT ON TABLE rack_info TO jobscheduler;
GRANT SELECT,INSERT ON TABLE rack_info TO bioinf;


--
-- TOC entry 5428 (class 0 OID 0)
-- Dependencies: 364
-- Name: rack_layout; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE rack_layout FROM PUBLIC;
REVOKE ALL ON TABLE rack_layout FROM thelma;
GRANT ALL ON TABLE rack_layout TO thelma;
GRANT SELECT ON TABLE rack_layout TO knime;
GRANT SELECT,INSERT ON TABLE rack_layout TO bioinf;


--
-- TOC entry 5437 (class 0 OID 0)
-- Dependencies: 366
-- Name: rack_mask; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_mask FROM PUBLIC;
REVOKE ALL ON TABLE rack_mask FROM postgres;
GRANT ALL ON TABLE rack_mask TO postgres;
GRANT SELECT ON TABLE rack_mask TO knime;
GRANT SELECT ON TABLE rack_mask TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_mask TO jobscheduler;
GRANT SELECT ON TABLE rack_mask TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_mask TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_mask TO bioinf;


--
-- TOC entry 5441 (class 0 OID 0)
-- Dependencies: 367
-- Name: rack_mask_position; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_mask_position FROM PUBLIC;
REVOKE ALL ON TABLE rack_mask_position FROM postgres;
GRANT ALL ON TABLE rack_mask_position TO postgres;
GRANT SELECT ON TABLE rack_mask_position TO knime;
GRANT SELECT ON TABLE rack_mask_position TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_mask_position TO jobscheduler;
GRANT SELECT ON TABLE rack_mask_position TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_mask_position TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_mask_position TO bioinf;


--
-- TOC entry 5442 (class 0 OID 0)
-- Dependencies: 368
-- Name: rack_mask_rack_mask_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE rack_mask_rack_mask_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE rack_mask_rack_mask_id_seq FROM postgres;
GRANT ALL ON SEQUENCE rack_mask_rack_mask_id_seq TO postgres;
GRANT USAGE ON SEQUENCE rack_mask_rack_mask_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE rack_mask_rack_mask_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE rack_mask_rack_mask_id_seq TO reader_role;


--
-- TOC entry 5443 (class 0 OID 0)
-- Dependencies: 369
-- Name: rack_position; Type: ACL; Schema: public; Owner: berger
--

REVOKE ALL ON TABLE rack_position FROM PUBLIC;
REVOKE ALL ON TABLE rack_position FROM berger;
GRANT ALL ON TABLE rack_position TO berger;
GRANT SELECT ON TABLE rack_position TO knime;
GRANT SELECT ON TABLE rack_position TO thelma;
GRANT SELECT ON TABLE rack_position TO reader_role;
GRANT SELECT ON TABLE rack_position TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_position TO bioinf;


--
-- TOC entry 5445 (class 0 OID 0)
-- Dependencies: 370
-- Name: rack_position_block; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_position_block FROM PUBLIC;
REVOKE ALL ON TABLE rack_position_block FROM postgres;
GRANT ALL ON TABLE rack_position_block TO postgres;
GRANT SELECT ON TABLE rack_position_block TO knime;
GRANT SELECT ON TABLE rack_position_block TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_position_block TO jobscheduler;
GRANT SELECT ON TABLE rack_position_block TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_position_block TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_position_block TO bioinf;


--
-- TOC entry 5447 (class 0 OID 0)
-- Dependencies: 371
-- Name: rack_position_block_rack_position_block_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE rack_position_block_rack_position_block_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE rack_position_block_rack_position_block_id_seq FROM postgres;
GRANT ALL ON SEQUENCE rack_position_block_rack_position_block_id_seq TO postgres;
GRANT USAGE ON SEQUENCE rack_position_block_rack_position_block_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE rack_position_block_rack_position_block_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE rack_position_block_rack_position_block_id_seq TO reader_role;


--
-- TOC entry 5450 (class 0 OID 0)
-- Dependencies: 373
-- Name: rack_position_set; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE rack_position_set FROM PUBLIC;
REVOKE ALL ON TABLE rack_position_set FROM thelma;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE ON TABLE rack_position_set TO thelma;
GRANT SELECT ON TABLE rack_position_set TO knime;
GRANT SELECT,INSERT ON TABLE rack_position_set TO bioinf;


--
-- TOC entry 5452 (class 0 OID 0)
-- Dependencies: 374
-- Name: rack_position_set_member; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE rack_position_set_member FROM PUBLIC;
REVOKE ALL ON TABLE rack_position_set_member FROM thelma;
GRANT ALL ON TABLE rack_position_set_member TO thelma;
GRANT SELECT ON TABLE rack_position_set_member TO knime;
GRANT SELECT,INSERT ON TABLE rack_position_set_member TO bioinf;


--
-- TOC entry 5454 (class 0 OID 0)
-- Dependencies: 376
-- Name: rack_rack_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE rack_rack_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE rack_rack_id_seq FROM postgres;
GRANT ALL ON SEQUENCE rack_rack_id_seq TO postgres;
GRANT USAGE ON SEQUENCE rack_rack_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE rack_rack_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE rack_rack_id_seq TO reader_role;


--
-- TOC entry 5456 (class 0 OID 0)
-- Dependencies: 377
-- Name: rack_shape; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_shape FROM PUBLIC;
REVOKE ALL ON TABLE rack_shape FROM postgres;
GRANT ALL ON TABLE rack_shape TO postgres;
GRANT SELECT ON TABLE rack_shape TO knime;
GRANT SELECT ON TABLE rack_shape TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_shape TO jobscheduler;
GRANT SELECT ON TABLE rack_shape TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_shape TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_shape TO bioinf;


--
-- TOC entry 5458 (class 0 OID 0)
-- Dependencies: 378
-- Name: rack_specs_container_specs; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rack_specs_container_specs FROM PUBLIC;
REVOKE ALL ON TABLE rack_specs_container_specs FROM postgres;
GRANT ALL ON TABLE rack_specs_container_specs TO postgres;
GRANT SELECT ON TABLE rack_specs_container_specs TO knime;
GRANT SELECT ON TABLE rack_specs_container_specs TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rack_specs_container_specs TO jobscheduler;
GRANT SELECT ON TABLE rack_specs_container_specs TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rack_specs_container_specs TO writer_role;
GRANT SELECT,INSERT ON TABLE rack_specs_container_specs TO bioinf;


--
-- TOC entry 5459 (class 0 OID 0)
-- Dependencies: 379
-- Name: rack_specs_rack_specs_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE rack_specs_rack_specs_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE rack_specs_rack_specs_id_seq FROM postgres;
GRANT ALL ON SEQUENCE rack_specs_rack_specs_id_seq TO postgres;
GRANT USAGE ON SEQUENCE rack_specs_rack_specs_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE rack_specs_rack_specs_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE rack_specs_rack_specs_id_seq TO reader_role;


--
-- TOC entry 5461 (class 0 OID 0)
-- Dependencies: 380
-- Name: racked_tube; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE racked_tube FROM PUBLIC;
REVOKE ALL ON TABLE racked_tube FROM postgres;
GRANT ALL ON TABLE racked_tube TO postgres;
GRANT SELECT ON TABLE racked_tube TO knime;
GRANT SELECT ON TABLE racked_tube TO ppfinder;
GRANT SELECT ON TABLE racked_tube TO jobscheduler;
GRANT SELECT,INSERT ON TABLE racked_tube TO bioinf;


--
-- TOC entry 5466 (class 0 OID 0)
-- Dependencies: 381
-- Name: sample; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sample FROM PUBLIC;
REVOKE ALL ON TABLE sample FROM postgres;
GRANT ALL ON TABLE sample TO postgres;
GRANT SELECT ON TABLE sample TO knime;
GRANT SELECT ON TABLE sample TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sample TO jobscheduler;
GRANT SELECT ON TABLE sample TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sample TO writer_role;
GRANT SELECT,INSERT ON TABLE sample TO bioinf;


--
-- TOC entry 5468 (class 0 OID 0)
-- Dependencies: 382
-- Name: racked_sample; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE racked_sample FROM PUBLIC;
REVOKE ALL ON TABLE racked_sample FROM postgres;
GRANT ALL ON TABLE racked_sample TO postgres;
GRANT SELECT ON TABLE racked_sample TO knime;
GRANT SELECT ON TABLE racked_sample TO ppfinder;
GRANT SELECT ON TABLE racked_sample TO jobscheduler;
GRANT SELECT,INSERT ON TABLE racked_sample TO bioinf;


--
-- TOC entry 5474 (class 0 OID 0)
-- Dependencies: 383
-- Name: sample_molecule; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sample_molecule FROM PUBLIC;
REVOKE ALL ON TABLE sample_molecule FROM postgres;
GRANT ALL ON TABLE sample_molecule TO postgres;
GRANT SELECT ON TABLE sample_molecule TO knime;
GRANT SELECT ON TABLE sample_molecule TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sample_molecule TO jobscheduler;
GRANT SELECT ON TABLE sample_molecule TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sample_molecule TO writer_role;
GRANT SELECT,INSERT ON TABLE sample_molecule TO bioinf;


--
-- TOC entry 5476 (class 0 OID 0)
-- Dependencies: 384
-- Name: racked_molecule_sample; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE racked_molecule_sample FROM PUBLIC;
REVOKE ALL ON TABLE racked_molecule_sample FROM postgres;
GRANT ALL ON TABLE racked_molecule_sample TO postgres;
GRANT SELECT ON TABLE racked_molecule_sample TO knime;
GRANT SELECT ON TABLE racked_molecule_sample TO ppfinder;
GRANT SELECT ON TABLE racked_molecule_sample TO jobscheduler;
GRANT SELECT,INSERT ON TABLE racked_molecule_sample TO bioinf;


--
-- TOC entry 5479 (class 0 OID 0)
-- Dependencies: 385
-- Name: readout_task_item; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE readout_task_item FROM PUBLIC;
REVOKE ALL ON TABLE readout_task_item FROM postgres;
GRANT ALL ON TABLE readout_task_item TO postgres;
GRANT SELECT ON TABLE readout_task_item TO knime;
GRANT SELECT ON TABLE readout_task_item TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE readout_task_item TO jobscheduler;
GRANT SELECT ON TABLE readout_task_item TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE readout_task_item TO writer_role;
GRANT SELECT,INSERT ON TABLE readout_task_item TO bioinf;


--
-- TOC entry 5484 (class 0 OID 0)
-- Dependencies: 386
-- Name: readout_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE readout_type FROM PUBLIC;
REVOKE ALL ON TABLE readout_type FROM postgres;
GRANT ALL ON TABLE readout_type TO postgres;
GRANT SELECT ON TABLE readout_type TO knime;
GRANT SELECT ON TABLE readout_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE readout_type TO jobscheduler;
GRANT SELECT ON TABLE readout_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE readout_type TO writer_role;
GRANT SELECT,INSERT ON TABLE readout_type TO bioinf;


--
-- TOC entry 5486 (class 0 OID 0)
-- Dependencies: 387
-- Name: readout_type_readout_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE readout_type_readout_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE readout_type_readout_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE readout_type_readout_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE readout_type_readout_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE readout_type_readout_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE readout_type_readout_type_id_seq TO reader_role;


--
-- TOC entry 5492 (class 0 OID 0)
-- Dependencies: 388
-- Name: rearrayed_containers; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rearrayed_containers FROM PUBLIC;
REVOKE ALL ON TABLE rearrayed_containers FROM postgres;
GRANT ALL ON TABLE rearrayed_containers TO postgres;
GRANT SELECT ON TABLE rearrayed_containers TO knime;
GRANT SELECT ON TABLE rearrayed_containers TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rearrayed_containers TO jobscheduler;
GRANT SELECT ON TABLE rearrayed_containers TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rearrayed_containers TO writer_role;
GRANT SELECT,INSERT ON TABLE rearrayed_containers TO bioinf;


--
-- TOC entry 5493 (class 0 OID 0)
-- Dependencies: 389
-- Name: refseq_gene; Type: ACL; Schema: public; Owner: berger
--

REVOKE ALL ON TABLE refseq_gene FROM PUBLIC;
REVOKE ALL ON TABLE refseq_gene FROM berger;
GRANT ALL ON TABLE refseq_gene TO berger;
GRANT SELECT,INSERT ON TABLE refseq_gene TO bioinf;


--
-- TOC entry 5494 (class 0 OID 0)
-- Dependencies: 390
-- Name: refseq_gene_view; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE refseq_gene_view FROM PUBLIC;
REVOKE ALL ON TABLE refseq_gene_view FROM thelma;
GRANT ALL ON TABLE refseq_gene_view TO thelma;
GRANT SELECT,INSERT ON TABLE refseq_gene_view TO bioinf;


--
-- TOC entry 5496 (class 0 OID 0)
-- Dependencies: 391
-- Name: refseq_update_species; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE refseq_update_species FROM PUBLIC;
REVOKE ALL ON TABLE refseq_update_species FROM postgres;
GRANT ALL ON TABLE refseq_update_species TO postgres;
GRANT SELECT ON TABLE refseq_update_species TO knime;
GRANT SELECT ON TABLE refseq_update_species TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE refseq_update_species TO jobscheduler;
GRANT SELECT ON TABLE refseq_update_species TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE refseq_update_species TO writer_role;
GRANT SELECT,INSERT ON TABLE refseq_update_species TO bioinf;


--
-- TOC entry 5498 (class 0 OID 0)
-- Dependencies: 392
-- Name: release_gene; Type: ACL; Schema: public; Owner: walsh
--

REVOKE ALL ON TABLE release_gene FROM PUBLIC;
REVOKE ALL ON TABLE release_gene FROM walsh;
GRANT ALL ON TABLE release_gene TO walsh;
GRANT SELECT ON TABLE release_gene TO knime;
GRANT SELECT ON TABLE release_gene TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE release_gene TO jobscheduler;
GRANT SELECT ON TABLE release_gene TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE release_gene TO writer_role;
GRANT SELECT,INSERT ON TABLE release_gene TO bioinf;


--
-- TOC entry 5499 (class 0 OID 0)
-- Dependencies: 393
-- Name: release_gene2annotation_release_gene2annotation_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE release_gene2annotation_release_gene2annotation_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE release_gene2annotation_release_gene2annotation_id_seq FROM postgres;
GRANT ALL ON SEQUENCE release_gene2annotation_release_gene2annotation_id_seq TO postgres;
GRANT USAGE ON SEQUENCE release_gene2annotation_release_gene2annotation_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE release_gene2annotation_release_gene2annotation_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE release_gene2annotation_release_gene2annotation_id_seq TO reader_role;


--
-- TOC entry 5501 (class 0 OID 0)
-- Dependencies: 394
-- Name: release_gene2annotation; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE release_gene2annotation FROM PUBLIC;
REVOKE ALL ON TABLE release_gene2annotation FROM postgres;
GRANT ALL ON TABLE release_gene2annotation TO postgres;
GRANT SELECT ON TABLE release_gene2annotation TO knime;
GRANT SELECT ON TABLE release_gene2annotation TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE release_gene2annotation TO jobscheduler;
GRANT SELECT ON TABLE release_gene2annotation TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE release_gene2annotation TO writer_role;
GRANT SELECT,INSERT ON TABLE release_gene2annotation TO bioinf;


--
-- TOC entry 5503 (class 0 OID 0)
-- Dependencies: 395
-- Name: release_gene_release_gene_id_seq; Type: ACL; Schema: public; Owner: walsh
--

REVOKE ALL ON SEQUENCE release_gene_release_gene_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE release_gene_release_gene_id_seq FROM walsh;
GRANT ALL ON SEQUENCE release_gene_release_gene_id_seq TO walsh;
GRANT USAGE ON SEQUENCE release_gene_release_gene_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE release_gene_release_gene_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE release_gene_release_gene_id_seq TO reader_role;


--
-- TOC entry 5504 (class 0 OID 0)
-- Dependencies: 396
-- Name: release_sirna_transcript_target_release_sirna_transcript_target; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE release_sirna_transcript_target_release_sirna_transcript_target FROM PUBLIC;
REVOKE ALL ON SEQUENCE release_sirna_transcript_target_release_sirna_transcript_target FROM postgres;
GRANT ALL ON SEQUENCE release_sirna_transcript_target_release_sirna_transcript_target TO postgres;
GRANT USAGE ON SEQUENCE release_sirna_transcript_target_release_sirna_transcript_target TO jobscheduler;
GRANT UPDATE ON SEQUENCE release_sirna_transcript_target_release_sirna_transcript_target TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE release_sirna_transcript_target_release_sirna_transcript_target TO reader_role;


--
-- TOC entry 5506 (class 0 OID 0)
-- Dependencies: 397
-- Name: replaced_gene; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE replaced_gene FROM PUBLIC;
REVOKE ALL ON TABLE replaced_gene FROM postgres;
GRANT ALL ON TABLE replaced_gene TO postgres;
GRANT SELECT ON TABLE replaced_gene TO knime;
GRANT SELECT ON TABLE replaced_gene TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE replaced_gene TO jobscheduler;
GRANT SELECT ON TABLE replaced_gene TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE replaced_gene TO writer_role;
GRANT SELECT,INSERT ON TABLE replaced_gene TO bioinf;


--
-- TOC entry 5508 (class 0 OID 0)
-- Dependencies: 398
-- Name: replaced_transcript; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE replaced_transcript FROM PUBLIC;
REVOKE ALL ON TABLE replaced_transcript FROM postgres;
GRANT ALL ON TABLE replaced_transcript TO postgres;
GRANT SELECT ON TABLE replaced_transcript TO knime;
GRANT SELECT ON TABLE replaced_transcript TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE replaced_transcript TO jobscheduler;
GRANT SELECT ON TABLE replaced_transcript TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE replaced_transcript TO writer_role;
GRANT SELECT,INSERT ON TABLE replaced_transcript TO bioinf;


--
-- TOC entry 5509 (class 0 OID 0)
-- Dependencies: 399
-- Name: reservoir_specs; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE reservoir_specs FROM PUBLIC;
REVOKE ALL ON TABLE reservoir_specs FROM thelma;
GRANT ALL ON TABLE reservoir_specs TO thelma;
GRANT SELECT,INSERT ON TABLE reservoir_specs TO bioinf;


--
-- TOC entry 5513 (class 0 OID 0)
-- Dependencies: 401
-- Name: rnai_experiment; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE rnai_experiment FROM PUBLIC;
REVOKE ALL ON TABLE rnai_experiment FROM postgres;
GRANT ALL ON TABLE rnai_experiment TO postgres;
GRANT ALL ON TABLE rnai_experiment TO celma;
GRANT SELECT ON TABLE rnai_experiment TO knime;
GRANT SELECT ON TABLE rnai_experiment TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE rnai_experiment TO jobscheduler;
GRANT SELECT ON TABLE rnai_experiment TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE rnai_experiment TO writer_role;
GRANT SELECT,INSERT ON TABLE rnai_experiment TO bioinf;


--
-- TOC entry 5515 (class 0 OID 0)
-- Dependencies: 402
-- Name: rnai_experiment_job_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE rnai_experiment_job_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE rnai_experiment_job_id_seq FROM postgres;
GRANT ALL ON SEQUENCE rnai_experiment_job_id_seq TO postgres;
GRANT USAGE ON SEQUENCE rnai_experiment_job_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE rnai_experiment_job_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE rnai_experiment_job_id_seq TO reader_role;


--
-- TOC entry 5516 (class 0 OID 0)
-- Dependencies: 403
-- Name: rnai_experiment_rnai_experiment_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE rnai_experiment_rnai_experiment_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE rnai_experiment_rnai_experiment_id_seq FROM postgres;
GRANT ALL ON SEQUENCE rnai_experiment_rnai_experiment_id_seq TO postgres;
GRANT USAGE ON SEQUENCE rnai_experiment_rnai_experiment_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE rnai_experiment_rnai_experiment_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE rnai_experiment_rnai_experiment_id_seq TO reader_role;


--
-- TOC entry 5518 (class 0 OID 0)
-- Dependencies: 404
-- Name: sample_cells; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sample_cells FROM PUBLIC;
REVOKE ALL ON TABLE sample_cells FROM postgres;
GRANT ALL ON TABLE sample_cells TO postgres;
GRANT SELECT ON TABLE sample_cells TO knime;
GRANT SELECT ON TABLE sample_cells TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sample_cells TO jobscheduler;
GRANT SELECT ON TABLE sample_cells TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sample_cells TO writer_role;
GRANT SELECT,INSERT ON TABLE sample_cells TO bioinf;


--
-- TOC entry 5520 (class 0 OID 0)
-- Dependencies: 406
-- Name: sample_registration; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sample_registration FROM PUBLIC;
REVOKE ALL ON TABLE sample_registration FROM postgres;
GRANT ALL ON TABLE sample_registration TO postgres;
GRANT SELECT ON TABLE sample_registration TO knime;
GRANT SELECT ON TABLE sample_registration TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sample_registration TO jobscheduler;
GRANT SELECT ON TABLE sample_registration TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sample_registration TO writer_role;
GRANT SELECT,INSERT ON TABLE sample_registration TO bioinf;


--
-- TOC entry 5522 (class 0 OID 0)
-- Dependencies: 407
-- Name: sample_sample_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sample_sample_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sample_sample_id_seq FROM postgres;
GRANT ALL ON SEQUENCE sample_sample_id_seq TO postgres;
GRANT USAGE ON SEQUENCE sample_sample_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sample_sample_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sample_sample_id_seq TO reader_role;


--
-- TOC entry 5523 (class 0 OID 0)
-- Dependencies: 408
-- Name: sample_set_auto_label_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sample_set_auto_label_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sample_set_auto_label_seq FROM postgres;
GRANT ALL ON SEQUENCE sample_set_auto_label_seq TO postgres;
GRANT USAGE ON SEQUENCE sample_set_auto_label_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sample_set_auto_label_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sample_set_auto_label_seq TO reader_role;


--
-- TOC entry 5529 (class 0 OID 0)
-- Dependencies: 409
-- Name: sample_set; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sample_set FROM PUBLIC;
REVOKE ALL ON TABLE sample_set FROM postgres;
GRANT ALL ON TABLE sample_set TO postgres;
GRANT ALL ON TABLE sample_set TO pylims;
GRANT ALL ON TABLE sample_set TO bioinf;
GRANT ALL ON TABLE sample_set TO koski;
GRANT ALL ON TABLE sample_set TO walsh;
GRANT ALL ON TABLE sample_set TO celma;
GRANT SELECT ON TABLE sample_set TO knime;
GRANT SELECT ON TABLE sample_set TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sample_set TO jobscheduler;
GRANT SELECT ON TABLE sample_set TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sample_set TO writer_role;


--
-- TOC entry 5531 (class 0 OID 0)
-- Dependencies: 410
-- Name: sample_set_sample; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sample_set_sample FROM PUBLIC;
REVOKE ALL ON TABLE sample_set_sample FROM postgres;
GRANT ALL ON TABLE sample_set_sample TO postgres;
GRANT SELECT ON TABLE sample_set_sample TO knime;
GRANT SELECT ON TABLE sample_set_sample TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sample_set_sample TO jobscheduler;
GRANT SELECT ON TABLE sample_set_sample TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sample_set_sample TO writer_role;
GRANT SELECT,INSERT ON TABLE sample_set_sample TO bioinf;


--
-- TOC entry 5532 (class 0 OID 0)
-- Dependencies: 411
-- Name: sample_set_sample_set_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sample_set_sample_set_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sample_set_sample_set_id_seq FROM postgres;
GRANT ALL ON SEQUENCE sample_set_sample_set_id_seq TO postgres;
GRANT USAGE ON SEQUENCE sample_set_sample_set_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sample_set_sample_set_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sample_set_sample_set_id_seq TO reader_role;


--
-- TOC entry 5534 (class 0 OID 0)
-- Dependencies: 412
-- Name: sample_set_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sample_set_type FROM PUBLIC;
REVOKE ALL ON TABLE sample_set_type FROM postgres;
GRANT ALL ON TABLE sample_set_type TO postgres;
GRANT SELECT ON TABLE sample_set_type TO knime;
GRANT SELECT ON TABLE sample_set_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sample_set_type TO jobscheduler;
GRANT SELECT ON TABLE sample_set_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sample_set_type TO writer_role;
GRANT SELECT,INSERT ON TABLE sample_set_type TO bioinf;


--
-- TOC entry 5535 (class 0 OID 0)
-- Dependencies: 413
-- Name: sample_set_type_sample_set_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sample_set_type_sample_set_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sample_set_type_sample_set_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE sample_set_type_sample_set_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE sample_set_type_sample_set_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sample_set_type_sample_set_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sample_set_type_sample_set_type_id_seq TO reader_role;


--
-- TOC entry 5536 (class 0 OID 0)
-- Dependencies: 414
-- Name: sample_type_sample_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sample_type_sample_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sample_type_sample_type_id_seq FROM postgres;
GRANT ALL ON SEQUENCE sample_type_sample_type_id_seq TO postgres;
GRANT USAGE ON SEQUENCE sample_type_sample_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sample_type_sample_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sample_type_sample_type_id_seq TO reader_role;


--
-- TOC entry 5538 (class 0 OID 0)
-- Dependencies: 415
-- Name: seq_identifier_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE seq_identifier_type FROM PUBLIC;
REVOKE ALL ON TABLE seq_identifier_type FROM postgres;
GRANT ALL ON TABLE seq_identifier_type TO postgres;
GRANT ALL ON TABLE seq_identifier_type TO pylims;
GRANT ALL ON TABLE seq_identifier_type TO bioinf;
GRANT ALL ON TABLE seq_identifier_type TO koski;
GRANT ALL ON TABLE seq_identifier_type TO walsh;
GRANT ALL ON TABLE seq_identifier_type TO celma;
GRANT SELECT ON TABLE seq_identifier_type TO knime;
GRANT SELECT ON TABLE seq_identifier_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE seq_identifier_type TO jobscheduler;
GRANT SELECT ON TABLE seq_identifier_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE seq_identifier_type TO writer_role;


--
-- TOC entry 5540 (class 0 OID 0)
-- Dependencies: 416
-- Name: seq_identifier_type_seq_identifier_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO celma;
GRANT USAGE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE seq_identifier_type_seq_identifier_type_id_seq TO reader_role;


--
-- TOC entry 5546 (class 0 OID 0)
-- Dependencies: 417
-- Name: sequence_feature; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sequence_feature FROM PUBLIC;
REVOKE ALL ON TABLE sequence_feature FROM postgres;
GRANT ALL ON TABLE sequence_feature TO postgres;
GRANT SELECT ON TABLE sequence_feature TO knime;
GRANT SELECT ON TABLE sequence_feature TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE sequence_feature TO jobscheduler;
GRANT SELECT ON TABLE sequence_feature TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE sequence_feature TO writer_role;
GRANT SELECT,INSERT ON TABLE sequence_feature TO bioinf;


--
-- TOC entry 5548 (class 0 OID 0)
-- Dependencies: 418
-- Name: sequence_feature_sequence_feature_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sequence_feature_sequence_feature_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sequence_feature_sequence_feature_id_seq FROM postgres;
GRANT ALL ON SEQUENCE sequence_feature_sequence_feature_id_seq TO postgres;
GRANT USAGE ON SEQUENCE sequence_feature_sequence_feature_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sequence_feature_sequence_feature_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sequence_feature_sequence_feature_id_seq TO reader_role;


--
-- TOC entry 5549 (class 0 OID 0)
-- Dependencies: 419
-- Name: sequence_hybridization_sequence_hybridization_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sequence_hybridization_sequence_hybridization_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sequence_hybridization_sequence_hybridization_id_seq FROM postgres;
GRANT ALL ON SEQUENCE sequence_hybridization_sequence_hybridization_id_seq TO postgres;
GRANT USAGE ON SEQUENCE sequence_hybridization_sequence_hybridization_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sequence_hybridization_sequence_hybridization_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sequence_hybridization_sequence_hybridization_id_seq TO reader_role;


--
-- TOC entry 5550 (class 0 OID 0)
-- Dependencies: 420
-- Name: sequence_transcript_target_sequence_transcript_target_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE sequence_transcript_target_sequence_transcript_target_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE sequence_transcript_target_sequence_transcript_target_id_seq FROM postgres;
GRANT ALL ON SEQUENCE sequence_transcript_target_sequence_transcript_target_id_seq TO postgres;
GRANT USAGE ON SEQUENCE sequence_transcript_target_sequence_transcript_target_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE sequence_transcript_target_sequence_transcript_target_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE sequence_transcript_target_sequence_transcript_target_id_seq TO reader_role;


--
-- TOC entry 5552 (class 0 OID 0)
-- Dependencies: 421
-- Name: single_supplier_molecule_design; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE single_supplier_molecule_design FROM PUBLIC;
REVOKE ALL ON TABLE single_supplier_molecule_design FROM gathmann;
GRANT ALL ON TABLE single_supplier_molecule_design TO gathmann;
GRANT SELECT,INSERT ON TABLE single_supplier_molecule_design TO bioinf;


--
-- TOC entry 5554 (class 0 OID 0)
-- Dependencies: 422
-- Name: species_species_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE species_species_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE species_species_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE species_species_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE species_species_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE species_species_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE species_species_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE species_species_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE species_species_id_seq TO celma;
GRANT USAGE ON SEQUENCE species_species_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE species_species_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE species_species_id_seq TO reader_role;


--
-- TOC entry 5555 (class 0 OID 0)
-- Dependencies: 423
-- Name: status_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE status_type FROM PUBLIC;
REVOKE ALL ON TABLE status_type FROM postgres;
GRANT ALL ON TABLE status_type TO postgres;
GRANT SELECT ON TABLE status_type TO knime;
GRANT SELECT ON TABLE status_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE status_type TO jobscheduler;
GRANT SELECT ON TABLE status_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE status_type TO writer_role;
GRANT SELECT,INSERT ON TABLE status_type TO bioinf;


--
-- TOC entry 5556 (class 0 OID 0)
-- Dependencies: 424
-- Name: stock_info_view; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE stock_info_view FROM PUBLIC;
REVOKE ALL ON TABLE stock_info_view FROM gathmann;
GRANT ALL ON TABLE stock_info_view TO gathmann;
GRANT SELECT,INSERT ON TABLE stock_info_view TO bioinf;


--
-- TOC entry 5559 (class 0 OID 0)
-- Dependencies: 427
-- Name: stock_sample; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE stock_sample FROM PUBLIC;
REVOKE ALL ON TABLE stock_sample FROM gathmann;
GRANT ALL ON TABLE stock_sample TO gathmann;
GRANT SELECT,INSERT ON TABLE stock_sample TO bioinf;


--
-- TOC entry 5560 (class 0 OID 0)
-- Dependencies: 428
-- Name: stock_sample_creation_iso; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE stock_sample_creation_iso FROM PUBLIC;
REVOKE ALL ON TABLE stock_sample_creation_iso FROM gathmann;
GRANT ALL ON TABLE stock_sample_creation_iso TO gathmann;
GRANT SELECT,INSERT ON TABLE stock_sample_creation_iso TO bioinf;


--
-- TOC entry 5561 (class 0 OID 0)
-- Dependencies: 430
-- Name: subproject_subproject_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE subproject_subproject_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE subproject_subproject_id_seq FROM postgres;
GRANT ALL ON SEQUENCE subproject_subproject_id_seq TO postgres;
GRANT USAGE ON SEQUENCE subproject_subproject_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE subproject_subproject_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE subproject_subproject_id_seq TO reader_role;


--
-- TOC entry 5568 (class 0 OID 0)
-- Dependencies: 431
-- Name: subproject; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE subproject FROM PUBLIC;
REVOKE ALL ON TABLE subproject FROM postgres;
GRANT ALL ON TABLE subproject TO postgres;
GRANT SELECT ON TABLE subproject TO knime;
GRANT SELECT ON TABLE subproject TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE subproject TO jobscheduler;
GRANT SELECT ON TABLE subproject TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE subproject TO writer_role;
GRANT SELECT,INSERT ON TABLE subproject TO bioinf;


--
-- TOC entry 5571 (class 0 OID 0)
-- Dependencies: 432
-- Name: supplier_barcode; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE supplier_barcode FROM PUBLIC;
REVOKE ALL ON TABLE supplier_barcode FROM postgres;
GRANT ALL ON TABLE supplier_barcode TO postgres;
GRANT ALL ON TABLE supplier_barcode TO celma;
GRANT SELECT ON TABLE supplier_barcode TO knime;
GRANT SELECT ON TABLE supplier_barcode TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE supplier_barcode TO jobscheduler;
GRANT SELECT ON TABLE supplier_barcode TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE supplier_barcode TO writer_role;
GRANT SELECT,INSERT ON TABLE supplier_barcode TO bioinf;


--
-- TOC entry 5575 (class 0 OID 0)
-- Dependencies: 434
-- Name: supplier_molecule_design; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE supplier_molecule_design FROM PUBLIC;
REVOKE ALL ON TABLE supplier_molecule_design FROM postgres;
GRANT ALL ON TABLE supplier_molecule_design TO postgres;
GRANT SELECT ON TABLE supplier_molecule_design TO knime;
GRANT SELECT ON TABLE supplier_molecule_design TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE supplier_molecule_design TO jobscheduler;
GRANT SELECT ON TABLE supplier_molecule_design TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE supplier_molecule_design TO writer_role;
GRANT SELECT,INSERT ON TABLE supplier_molecule_design TO bioinf;


--
-- TOC entry 5576 (class 0 OID 0)
-- Dependencies: 435
-- Name: supplier_molecule_design_view; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE supplier_molecule_design_view FROM PUBLIC;
REVOKE ALL ON TABLE supplier_molecule_design_view FROM gathmann;
GRANT ALL ON TABLE supplier_molecule_design_view TO gathmann;
GRANT SELECT,INSERT ON TABLE supplier_molecule_design_view TO bioinf;


--
-- TOC entry 5578 (class 0 OID 0)
-- Dependencies: 436
-- Name: supplier_structure_annotation; Type: ACL; Schema: public; Owner: gathmann
--

REVOKE ALL ON TABLE supplier_structure_annotation FROM PUBLIC;
REVOKE ALL ON TABLE supplier_structure_annotation FROM gathmann;
GRANT ALL ON TABLE supplier_structure_annotation TO gathmann;
GRANT SELECT,INSERT ON TABLE supplier_structure_annotation TO bioinf;


--
-- TOC entry 5580 (class 0 OID 0)
-- Dependencies: 437
-- Name: tag; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tag FROM PUBLIC;
REVOKE ALL ON TABLE tag FROM thelma;
GRANT ALL ON TABLE tag TO thelma;
GRANT SELECT ON TABLE tag TO knime;
GRANT SELECT,INSERT ON TABLE tag TO bioinf;


--
-- TOC entry 5582 (class 0 OID 0)
-- Dependencies: 438
-- Name: tag_domain; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tag_domain FROM PUBLIC;
REVOKE ALL ON TABLE tag_domain FROM thelma;
GRANT ALL ON TABLE tag_domain TO thelma;
GRANT SELECT ON TABLE tag_domain TO knime;
GRANT SELECT,INSERT ON TABLE tag_domain TO bioinf;


--
-- TOC entry 5585 (class 0 OID 0)
-- Dependencies: 440
-- Name: tag_predicate; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tag_predicate FROM PUBLIC;
REVOKE ALL ON TABLE tag_predicate FROM thelma;
GRANT ALL ON TABLE tag_predicate TO thelma;
GRANT SELECT ON TABLE tag_predicate TO knime;
GRANT SELECT,INSERT ON TABLE tag_predicate TO bioinf;


--
-- TOC entry 5589 (class 0 OID 0)
-- Dependencies: 443
-- Name: tag_value; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tag_value FROM PUBLIC;
REVOKE ALL ON TABLE tag_value FROM thelma;
GRANT ALL ON TABLE tag_value TO thelma;
GRANT SELECT ON TABLE tag_value TO knime;
GRANT SELECT,INSERT ON TABLE tag_value TO bioinf;


--
-- TOC entry 5592 (class 0 OID 0)
-- Dependencies: 445
-- Name: tagged; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tagged FROM PUBLIC;
REVOKE ALL ON TABLE tagged FROM thelma;
GRANT ALL ON TABLE tagged TO thelma;
GRANT SELECT ON TABLE tagged TO knime;
GRANT SELECT,INSERT ON TABLE tagged TO bioinf;


--
-- TOC entry 5594 (class 0 OID 0)
-- Dependencies: 446
-- Name: tagged_rack_position_set; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tagged_rack_position_set FROM PUBLIC;
REVOKE ALL ON TABLE tagged_rack_position_set FROM thelma;
GRANT ALL ON TABLE tagged_rack_position_set TO thelma;
GRANT SELECT ON TABLE tagged_rack_position_set TO knime;
GRANT SELECT,INSERT ON TABLE tagged_rack_position_set TO bioinf;


--
-- TOC entry 5597 (class 0 OID 0)
-- Dependencies: 448
-- Name: tagging; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tagging FROM PUBLIC;
REVOKE ALL ON TABLE tagging FROM thelma;
GRANT ALL ON TABLE tagging TO thelma;
GRANT SELECT ON TABLE tagging TO knime;
GRANT SELECT,INSERT ON TABLE tagging TO bioinf;


--
-- TOC entry 5599 (class 0 OID 0)
-- Dependencies: 449
-- Name: target; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE target FROM PUBLIC;
REVOKE ALL ON TABLE target FROM thelma;
GRANT ALL ON TABLE target TO thelma;
GRANT SELECT,INSERT ON TABLE target TO bioinf;


--
-- TOC entry 5601 (class 0 OID 0)
-- Dependencies: 450
-- Name: target_set; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE target_set FROM PUBLIC;
REVOKE ALL ON TABLE target_set FROM thelma;
GRANT ALL ON TABLE target_set TO thelma;
GRANT SELECT,INSERT ON TABLE target_set TO bioinf;


--
-- TOC entry 5603 (class 0 OID 0)
-- Dependencies: 451
-- Name: target_set_member; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE target_set_member FROM PUBLIC;
REVOKE ALL ON TABLE target_set_member FROM thelma;
GRANT ALL ON TABLE target_set_member TO thelma;
GRANT SELECT,INSERT ON TABLE target_set_member TO bioinf;


--
-- TOC entry 5613 (class 0 OID 0)
-- Dependencies: 454
-- Name: task; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE task FROM PUBLIC;
REVOKE ALL ON TABLE task FROM postgres;
GRANT ALL ON TABLE task TO postgres;
GRANT ALL ON TABLE task TO celma;
GRANT SELECT ON TABLE task TO knime;
GRANT SELECT ON TABLE task TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE task TO jobscheduler;
GRANT SELECT ON TABLE task TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE task TO writer_role;
GRANT SELECT,INSERT ON TABLE task TO bioinf;


--
-- TOC entry 5618 (class 0 OID 0)
-- Dependencies: 455
-- Name: task_item; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE task_item FROM PUBLIC;
REVOKE ALL ON TABLE task_item FROM postgres;
GRANT ALL ON TABLE task_item TO postgres;
GRANT ALL ON TABLE task_item TO celma;
GRANT SELECT ON TABLE task_item TO knime;
GRANT SELECT ON TABLE task_item TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE task_item TO jobscheduler;
GRANT SELECT ON TABLE task_item TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE task_item TO writer_role;
GRANT SELECT,INSERT ON TABLE task_item TO bioinf;


--
-- TOC entry 5619 (class 0 OID 0)
-- Dependencies: 456
-- Name: task_item_task_item_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE task_item_task_item_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE task_item_task_item_id_seq FROM postgres;
GRANT ALL ON SEQUENCE task_item_task_item_id_seq TO postgres;
GRANT USAGE ON SEQUENCE task_item_task_item_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE task_item_task_item_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE task_item_task_item_id_seq TO reader_role;


--
-- TOC entry 5622 (class 0 OID 0)
-- Dependencies: 457
-- Name: task_report; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE task_report FROM PUBLIC;
REVOKE ALL ON TABLE task_report FROM postgres;
GRANT ALL ON TABLE task_report TO postgres;
GRANT SELECT ON TABLE task_report TO knime;
GRANT SELECT ON TABLE task_report TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE task_report TO jobscheduler;
GRANT SELECT ON TABLE task_report TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE task_report TO writer_role;
GRANT SELECT,INSERT ON TABLE task_report TO bioinf;


--
-- TOC entry 5624 (class 0 OID 0)
-- Dependencies: 458
-- Name: task_task_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE task_task_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE task_task_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE task_task_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE task_task_id_seq TO celma;
GRANT USAGE ON SEQUENCE task_task_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE task_task_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE task_task_id_seq TO reader_role;


--
-- TOC entry 5629 (class 0 OID 0)
-- Dependencies: 459
-- Name: task_type; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE task_type FROM PUBLIC;
REVOKE ALL ON TABLE task_type FROM postgres;
GRANT ALL ON TABLE task_type TO postgres;
GRANT ALL ON TABLE task_type TO celma;
GRANT SELECT ON TABLE task_type TO knime;
GRANT SELECT ON TABLE task_type TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE task_type TO jobscheduler;
GRANT SELECT ON TABLE task_type TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE task_type TO writer_role;
GRANT SELECT,INSERT ON TABLE task_type TO bioinf;


--
-- TOC entry 5631 (class 0 OID 0)
-- Dependencies: 460
-- Name: task_type_task_type_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE task_type_task_type_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE task_type_task_type_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE task_type_task_type_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE task_type_task_type_id_seq TO celma;
GRANT USAGE ON SEQUENCE task_type_task_type_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE task_type_task_type_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE task_type_task_type_id_seq TO reader_role;


--
-- TOC entry 5633 (class 0 OID 0)
-- Dependencies: 461
-- Name: transcript_gene; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE transcript_gene FROM PUBLIC;
REVOKE ALL ON TABLE transcript_gene FROM thelma;
GRANT ALL ON TABLE transcript_gene TO thelma;
GRANT SELECT,INSERT ON TABLE transcript_gene TO bioinf;


--
-- TOC entry 5635 (class 0 OID 0)
-- Dependencies: 462
-- Name: transcript_identifier; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE transcript_identifier FROM PUBLIC;
REVOKE ALL ON TABLE transcript_identifier FROM postgres;
GRANT ALL ON TABLE transcript_identifier TO postgres;
GRANT ALL ON TABLE transcript_identifier TO pylims;
GRANT ALL ON TABLE transcript_identifier TO bioinf;
GRANT ALL ON TABLE transcript_identifier TO koski;
GRANT ALL ON TABLE transcript_identifier TO walsh;
GRANT ALL ON TABLE transcript_identifier TO celma;
GRANT SELECT ON TABLE transcript_identifier TO knime;
GRANT SELECT ON TABLE transcript_identifier TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE transcript_identifier TO jobscheduler;
GRANT SELECT ON TABLE transcript_identifier TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE transcript_identifier TO writer_role;


--
-- TOC entry 5637 (class 0 OID 0)
-- Dependencies: 463
-- Name: transcript_identifier_transcript_identifier_id_seq; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON SEQUENCE transcript_identifier_transcript_identifier_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE transcript_identifier_transcript_identifier_id_seq FROM postgres;
GRANT SELECT,UPDATE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO postgres;
GRANT SELECT,UPDATE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO pylims;
GRANT SELECT,UPDATE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO bioinf;
GRANT SELECT,UPDATE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO koski;
GRANT SELECT,UPDATE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO walsh;
GRANT SELECT,UPDATE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO celma;
GRANT USAGE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO jobscheduler;
GRANT UPDATE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO writer_role;
GRANT SELECT,USAGE ON SEQUENCE transcript_identifier_transcript_identifier_id_seq TO reader_role;


--
-- TOC entry 5640 (class 0 OID 0)
-- Dependencies: 464
-- Name: transfection_job_step; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE transfection_job_step FROM PUBLIC;
REVOKE ALL ON TABLE transfection_job_step FROM postgres;
GRANT ALL ON TABLE transfection_job_step TO postgres;
GRANT SELECT ON TABLE transfection_job_step TO knime;
GRANT SELECT ON TABLE transfection_job_step TO ppfinder;
GRANT SELECT,INSERT,UPDATE ON TABLE transfection_job_step TO jobscheduler;
GRANT SELECT ON TABLE transfection_job_step TO reader_role;
GRANT INSERT,DELETE,UPDATE ON TABLE transfection_job_step TO writer_role;
GRANT SELECT,INSERT ON TABLE transfection_job_step TO bioinf;


--
-- TOC entry 5641 (class 0 OID 0)
-- Dependencies: 465
-- Name: transfer_type; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE transfer_type FROM PUBLIC;
REVOKE ALL ON TABLE transfer_type FROM thelma;
GRANT ALL ON TABLE transfer_type TO thelma;
GRANT SELECT,INSERT ON TABLE transfer_type TO bioinf;


--
-- TOC entry 5642 (class 0 OID 0)
-- Dependencies: 466
-- Name: tube_transfer; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tube_transfer FROM PUBLIC;
REVOKE ALL ON TABLE tube_transfer FROM thelma;
GRANT ALL ON TABLE tube_transfer TO thelma;
GRANT SELECT,INSERT ON TABLE tube_transfer TO bioinf;


--
-- TOC entry 5644 (class 0 OID 0)
-- Dependencies: 468
-- Name: tube_transfer_worklist; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tube_transfer_worklist FROM PUBLIC;
REVOKE ALL ON TABLE tube_transfer_worklist FROM thelma;
GRANT ALL ON TABLE tube_transfer_worklist TO thelma;
GRANT SELECT,INSERT ON TABLE tube_transfer_worklist TO bioinf;


--
-- TOC entry 5645 (class 0 OID 0)
-- Dependencies: 469
-- Name: tube_transfer_worklist_member; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE tube_transfer_worklist_member FROM PUBLIC;
REVOKE ALL ON TABLE tube_transfer_worklist_member FROM thelma;
GRANT ALL ON TABLE tube_transfer_worklist_member TO thelma;
GRANT SELECT,INSERT ON TABLE tube_transfer_worklist_member TO bioinf;


--
-- TOC entry 5647 (class 0 OID 0)
-- Dependencies: 471
-- Name: user_preferences; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE user_preferences FROM PUBLIC;
REVOKE ALL ON TABLE user_preferences FROM thelma;
GRANT ALL ON TABLE user_preferences TO thelma;
GRANT SELECT,INSERT ON TABLE user_preferences TO bioinf;


--
-- TOC entry 5649 (class 0 OID 0)
-- Dependencies: 473
-- Name: worklist_series; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE worklist_series FROM PUBLIC;
REVOKE ALL ON TABLE worklist_series FROM thelma;
GRANT ALL ON TABLE worklist_series TO thelma;
GRANT SELECT,INSERT ON TABLE worklist_series TO bioinf;


--
-- TOC entry 5650 (class 0 OID 0)
-- Dependencies: 474
-- Name: worklist_series_experiment_design; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE worklist_series_experiment_design FROM PUBLIC;
REVOKE ALL ON TABLE worklist_series_experiment_design FROM thelma;
GRANT ALL ON TABLE worklist_series_experiment_design TO thelma;
GRANT SELECT,INSERT ON TABLE worklist_series_experiment_design TO bioinf;


--
-- TOC entry 5651 (class 0 OID 0)
-- Dependencies: 475
-- Name: worklist_series_experiment_design_rack; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE worklist_series_experiment_design_rack FROM PUBLIC;
REVOKE ALL ON TABLE worklist_series_experiment_design_rack FROM thelma;
GRANT ALL ON TABLE worklist_series_experiment_design_rack TO thelma;
GRANT SELECT,INSERT ON TABLE worklist_series_experiment_design_rack TO bioinf;


--
-- TOC entry 5652 (class 0 OID 0)
-- Dependencies: 477
-- Name: worklist_series_iso_request; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE worklist_series_iso_request FROM PUBLIC;
REVOKE ALL ON TABLE worklist_series_iso_request FROM thelma;
GRANT ALL ON TABLE worklist_series_iso_request TO thelma;
GRANT SELECT,INSERT ON TABLE worklist_series_iso_request TO bioinf;


--
-- TOC entry 5653 (class 0 OID 0)
-- Dependencies: 478
-- Name: worklist_series_member; Type: ACL; Schema: public; Owner: thelma
--

REVOKE ALL ON TABLE worklist_series_member FROM PUBLIC;
REVOKE ALL ON TABLE worklist_series_member FROM thelma;
GRANT ALL ON TABLE worklist_series_member TO thelma;
GRANT SELECT,INSERT ON TABLE worklist_series_member TO bioinf;


-- Completed on 2014-09-12 16:16:47 CEST

--
-- PostgreSQL database dump complete
--

