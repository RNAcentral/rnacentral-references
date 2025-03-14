#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER $LITSCAN_USER WITH PASSWORD '$LITSCAN_PASSWORD';
	CREATE DATABASE $LITSCAN_DB;
	GRANT ALL PRIVILEGES ON DATABASE $LITSCAN_DB TO $LITSCAN_USER;
	ALTER DATABASE $LITSCAN_DB OWNER TO $LITSCAN_USER;
	\connect $LITSCAN_DB $LITSCAN_USER
	BEGIN;
      CREATE TABLE public.litscan_abstract_sentence (
          id integer NOT NULL,
          result_id integer,
          sentence text
      );
      ALTER TABLE public.litscan_abstract_sentence OWNER TO $LITSCAN_USER;

      CREATE SEQUENCE public.litscan_abstract_sentence_id_seq
          AS integer
          START WITH 1
          INCREMENT BY 1
          NO MINVALUE
          NO MAXVALUE
          CACHE 1;
      ALTER TABLE public.litscan_abstract_sentence_id_seq OWNER TO $LITSCAN_USER;
      ALTER SEQUENCE public.litscan_abstract_sentence_id_seq OWNED BY public.litscan_abstract_sentence.id;

      CREATE TABLE public.litscan_article (
          pmcid character varying(15) NOT NULL,
          title text,
          abstract text,
          author text,
          pmid character varying(100),
          doi character varying(100),
          year integer,
          journal character varying(255),
          score integer,
          cited_by integer,
          retracted boolean,
          rna_related boolean,
          probability float,
          type character varying(100)
      );
      ALTER TABLE public.litscan_article OWNER TO $LITSCAN_USER;

      CREATE TABLE public.litscan_body_sentence (
          id integer NOT NULL,
          result_id integer,
          sentence text,
          location text
      );
      ALTER TABLE public.litscan_body_sentence OWNER TO $LITSCAN_USER;

      CREATE SEQUENCE public.litscan_body_sentence_id_seq
          AS integer
          START WITH 1
          INCREMENT BY 1
          NO MINVALUE
          NO MAXVALUE
          CACHE 1;
      ALTER TABLE public.litscan_body_sentence_id_seq OWNER TO $LITSCAN_USER;
      ALTER SEQUENCE public.litscan_body_sentence_id_seq OWNED BY public.litscan_body_sentence.id;

      CREATE TABLE public.litscan_consumer (
          ip character varying(20) NOT NULL,
          status character varying(10) NOT NULL,
          job_id character varying(100),
          port character varying(5)
      );
      ALTER TABLE public.litscan_consumer OWNER TO $LITSCAN_USER;

      CREATE TABLE public.litscan_database (
          id integer NOT NULL,
          name character varying(50),
          job_id character varying(100),
          primary_id character varying(100)
      );
      ALTER TABLE public.litscan_database OWNER TO $LITSCAN_USER;

      CREATE SEQUENCE public.litscan_database_id_seq
          AS integer
          START WITH 1
          INCREMENT BY 1
          NO MINVALUE
          NO MAXVALUE
          CACHE 1;
      ALTER TABLE public.litscan_database_id_seq OWNER TO $LITSCAN_USER;
      ALTER SEQUENCE public.litscan_database_id_seq OWNED BY public.litscan_database.id;

      CREATE TABLE public.litscan_job (
          job_id character varying(100) NOT NULL,
          display_id character varying(100),
          query text,
          search_limit integer,
          submitted timestamp without time zone,
          finished timestamp without time zone,
          status character varying(10),
          hit_count integer
      );
      ALTER TABLE public.litscan_job OWNER TO $LITSCAN_USER;

      CREATE TABLE public.litscan_result (
          id integer NOT NULL,
          pmcid character varying(15),
          job_id character varying(100),
          id_in_title boolean,
          id_in_abstract boolean,
          id_in_body boolean
      );
      ALTER TABLE public.litscan_result OWNER TO $LITSCAN_USER;

      CREATE SEQUENCE public.litscan_result_id_seq
          AS integer
          START WITH 1
          INCREMENT BY 1
          NO MINVALUE
          NO MAXVALUE
          CACHE 1;
      ALTER TABLE public.litscan_result_id_seq OWNER TO $LITSCAN_USER;
      ALTER SEQUENCE public.litscan_result_id_seq OWNED BY public.litscan_result.id;

      ALTER TABLE ONLY public.litscan_abstract_sentence ALTER COLUMN id SET DEFAULT nextval('public.litscan_abstract_sentence_id_seq'::regclass);
      ALTER TABLE ONLY public.litscan_body_sentence ALTER COLUMN id SET DEFAULT nextval('public.litscan_body_sentence_id_seq'::regclass);
      ALTER TABLE ONLY public.litscan_database ALTER COLUMN id SET DEFAULT nextval('public.litscan_database_id_seq'::regclass);
      ALTER TABLE ONLY public.litscan_result ALTER COLUMN id SET DEFAULT nextval('public.litscan_result_id_seq'::regclass);

      SELECT pg_catalog.setval('public.litscan_abstract_sentence_id_seq', 1, false);
      SELECT pg_catalog.setval('public.litscan_body_sentence_id_seq', 1, false);
      SELECT pg_catalog.setval('public.litscan_database_id_seq', 1, false);
      SELECT pg_catalog.setval('public.litscan_result_id_seq', 1, false);

      ALTER TABLE ONLY public.litscan_abstract_sentence ADD CONSTRAINT litscan_abstract_sentence_pkey PRIMARY KEY (id);
      ALTER TABLE ONLY public.litscan_article ADD CONSTRAINT litscan_article_pkey PRIMARY KEY (pmcid);
      ALTER TABLE ONLY public.litscan_body_sentence ADD CONSTRAINT litscan_body_sentence_pkey PRIMARY KEY (id);
      ALTER TABLE ONLY public.litscan_consumer ADD CONSTRAINT litscan_consumer_pkey PRIMARY KEY (ip);
      ALTER TABLE ONLY public.litscan_database ADD CONSTRAINT litscan_database_pkey PRIMARY KEY (id);
      ALTER TABLE ONLY public.litscan_job ADD CONSTRAINT litscan_job_pkey PRIMARY KEY (job_id);
      ALTER TABLE ONLY public.litscan_result ADD CONSTRAINT litscan_result_pkey PRIMARY KEY (id);
      ALTER TABLE ONLY public.litscan_result ADD CONSTRAINT pmcid_job_id UNIQUE (pmcid, job_id);
      ALTER TABLE ONLY public.litscan_database ADD CONSTRAINT name_job UNIQUE (name, job_id, primary_id);

      CREATE INDEX litscan_abstract_sentence_result_id_idx ON public.litscan_abstract_sentence USING btree (result_id);
      CREATE INDEX litscan_article_pmcid_idx ON public.litscan_article USING btree (pmcid) WHERE (retracted IS FALSE);
      CREATE INDEX litscan_body_sentence_result_id_idx ON public.litscan_body_sentence USING btree (result_id);
      CREATE INDEX litscan_database_job_id_idx ON public.litscan_database USING btree (job_id);
      CREATE INDEX litscan_result_job_id_idx ON public.litscan_result USING btree (job_id);

      ALTER TABLE ONLY public.litscan_abstract_sentence ADD CONSTRAINT litscan_abstract_sentence_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.litscan_result(id) ON UPDATE CASCADE ON DELETE CASCADE;
      ALTER TABLE ONLY public.litscan_body_sentence ADD CONSTRAINT litscan_body_sentence_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.litscan_result(id) ON UPDATE CASCADE ON DELETE CASCADE;
      ALTER TABLE ONLY public.litscan_database ADD CONSTRAINT litscan_database_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.litscan_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;
      ALTER TABLE ONLY public.litscan_database ADD CONSTRAINT litscan_database_primary_id_fkey FOREIGN KEY (primary_id) REFERENCES public.litscan_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;
      ALTER TABLE ONLY public.litscan_result ADD CONSTRAINT litscan_result_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.litscan_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE;
      ALTER TABLE ONLY public.litscan_result ADD CONSTRAINT litscan_result_pmcid_fkey FOREIGN KEY (pmcid) REFERENCES public.litscan_article(pmcid) ON UPDATE CASCADE ON DELETE CASCADE;
	COMMIT;
EOSQL