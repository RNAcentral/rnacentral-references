"""
Copyright [2009-present] EMBL-European Bioinformatics Institute
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
     http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
import sqlalchemy as sa
from aiopg.sa import create_engine

from .settings import get_postgres_credentials


# Connection initialization code
# ------------------------------

async def init_pg(app):
    logger = logging.getLogger('aiohttp.web')
    logger.debug("POSTGRES_USER = %s" % app['settings'].POSTGRES_USER)
    logger.debug("POSTGRES_DATABASE = %s" % app['settings'].POSTGRES_DATABASE)
    logger.debug("POSTGRES_HOST = %s" % app['settings'].POSTGRES_HOST)
    logger.debug("POSTGRES_PORT = %s" % app['settings'].POSTGRES_PORT)

    app['engine'] = await create_engine(
        user=app['settings'].POSTGRES_USER,
        password=app['settings'].POSTGRES_PASSWORD,
        database=app['settings'].POSTGRES_DATABASE,
        host=app['settings'].POSTGRES_HOST,
        port=app['settings'].POSTGRES_PORT
    )


# Graceful shutdown
# -----------------

async def close_pg(app):
    app['engine'].close()
    await app['engine'].wait_closed()


# Models schema
# -------------

class JOB_STATUS_CHOICES(object):
    pending = 'pending'
    started = 'started'
    error = 'error'
    success = 'success'


class CONSUMER_STATUS_CHOICES(object):
    available = 'available'
    busy = 'busy'
    error = 'error'


metadata = sa.MetaData()

"""State of a consumer instance"""
Consumer = sa.Table(
    'litscan_consumer',
    metadata,
    sa.Column('ip', sa.String(20), primary_key=True),
    sa.Column('status', sa.String(10)),  # choices=CONSUMER_STATUS_CHOICES, default='available'
    sa.Column('job_id', sa.ForeignKey('job.job_id')),
    sa.Column('port', sa.String(5))
)

"""Metadata of a search job"""
Job = sa.Table(
    'litscan_job',
    metadata,
    sa.Column('job_id', sa.String(100), primary_key=True),
    sa.Column('display_id', sa.String(100)),
    sa.Column('query', sa.Text, nullable=True),
    sa.Column('search_limit', sa.Integer, nullable=True),
    sa.Column('status', sa.String(10)),  # choices=JOB_STATUS_CHOICES
    sa.Column('submitted', sa.DateTime),
    sa.Column('finished', sa.DateTime, nullable=True),
    sa.Column('hit_count', sa.Integer, nullable=True),
)

"""Info about a specific article"""
Article = sa.Table(
    'litscan_article',
    metadata,
    sa.Column('pmcid', sa.String(15), primary_key=True),
    sa.Column('title', sa.Text),
    sa.Column('abstract', sa.Text),
    sa.Column('author', sa.Text),
    sa.Column('pmid', sa.String(100)),
    sa.Column('doi', sa.String(100)),
    sa.Column('year', sa.Integer()),
    sa.Column('journal', sa.String(255)),
    sa.Column('score', sa.Integer()),
    sa.Column('cited_by', sa.Integer()),
    sa.Column('retracted', sa.Boolean),
)

"""Organisms identified in the article"""
Organism = sa.Table(
    'litscan_organism',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('pmcid', sa.String(15), sa.ForeignKey('article.pmcid')),
    sa.Column('organism', sa.Integer),
)

"""Result of a specific Job"""
Result = sa.Table(
    'litscan_result',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('pmcid', sa.String(15), sa.ForeignKey('article.pmcid')),
    sa.Column('job_id', sa.String(100), sa.ForeignKey('job.job_id')),
    sa.Column('id_in_title', sa.Boolean),
    sa.Column('id_in_abstract', sa.Boolean),
    sa.Column('id_in_body', sa.Boolean),
)

"""Sentences extracted from the abstract"""
AbstractSentence = sa.Table(
    'litscan_abstract_sentence',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('result_id', sa.Integer, sa.ForeignKey('result.id')),
    sa.Column('sentence', sa.Text),
)

"""Sentences extracted from the body"""
BodySentence = sa.Table(
    'litscan_body_sentence',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('result_id', sa.Integer, sa.ForeignKey('result.id')),
    sa.Column('sentence', sa.Text),
    sa.Column('location', sa.Text),
)

"""Job related to which DB"""
Database = sa.Table(
    'litscan_database',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(50)),
    sa.Column('job_id', sa.String(100), sa.ForeignKey('job.job_id')),
    sa.Column('primary_id', sa.String(100), sa.ForeignKey('job.job_id'), nullable=True),
)

"""Manually annotated articles"""
ManuallyAnnotated = sa.Table(
    'litscan_manually_annotated',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('pmcid', sa.String(15), sa.ForeignKey('article.pmcid')),
    sa.Column('urs', sa.String(100), sa.ForeignKey('job.job_id')),
)

"""Taxonomy-based retrieval of documents"""
LoadOrganism = sa.Table(
    'litscan_load_organism',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('pmid', sa.String(100)),
    sa.Column('organism', sa.Integer),
)

"""Get taxonomy name"""
Taxonomy = sa.Table(
    'rnc_taxonomy',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(255)),
)


# Migrations
# ----------


async def migrate(env):
    """
    Create the necessary tables in the database
    :param env: Environment used (local, prod or test)
    """
    settings = get_postgres_credentials(env)

    engine = await create_engine(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DATABASE,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT
    )

    async with engine:
        async with engine.acquire() as connection:
            await connection.execute('DROP TABLE IF EXISTS litscan_load_organism')
            await connection.execute('DROP TABLE IF EXISTS litscan_organism')
            await connection.execute('DROP TABLE IF EXISTS litscan_body_sentence')
            await connection.execute('DROP TABLE IF EXISTS litscan_abstract_sentence')
            await connection.execute('DROP TABLE IF EXISTS litscan_manually_annotated')
            await connection.execute('DROP TABLE IF EXISTS litscan_result')
            await connection.execute('DROP TABLE IF EXISTS litscan_article')
            await connection.execute('DROP TABLE IF EXISTS litscan_database')
            await connection.execute('DROP TABLE IF EXISTS litscan_job')
            await connection.execute('DROP TABLE IF EXISTS litscan_consumer')

            await connection.execute('''
                CREATE TABLE litscan_consumer (
                  ip VARCHAR(20) PRIMARY KEY,
                  status VARCHAR(10) NOT NULL,
                  job_id VARCHAR(100),
                  port VARCHAR(5))
            ''')

            await connection.execute('''
                CREATE TABLE litscan_job (
                  job_id VARCHAR(100) PRIMARY KEY,
                  display_id VARCHAR(100),
                  query TEXT,
                  search_limit INTEGER,
                  submitted TIMESTAMP,
                  finished TIMESTAMP,
                  status VARCHAR(10),
                  hit_count INTEGER)
            ''')

            await connection.execute('''
                CREATE TABLE litscan_article (
                  pmcid VARCHAR(15) PRIMARY KEY,
                  title TEXT,
                  abstract TEXT,
                  author TEXT,
                  pmid VARCHAR(100),
                  doi VARCHAR(100),
                  year INTEGER,
                  journal VARCHAR(255),
                  score INTEGER,
                  cited_by INTEGER,
                  retracted BOOLEAN)
            ''')

            await connection.execute('''
                CREATE TABLE litscan_organism (
                  id SERIAL PRIMARY KEY,
                  pmcid VARCHAR(15),
                  organism INTEGER,
                  FOREIGN KEY (pmcid) REFERENCES litscan_article(pmcid) ON UPDATE CASCADE ON DELETE CASCADE,
                  CONSTRAINT pmcid_organism UNIQUE (pmcid, organism))
            ''')

            await connection.execute('''
                CREATE TABLE litscan_result (
                  id SERIAL PRIMARY KEY,
                  pmcid VARCHAR(15),
                  job_id VARCHAR(100),
                  id_in_title BOOLEAN,
                  id_in_abstract BOOLEAN,
                  id_in_body BOOLEAN,
                  FOREIGN KEY (pmcid) REFERENCES litscan_article(pmcid) ON UPDATE CASCADE ON DELETE CASCADE,
                  FOREIGN KEY (job_id) REFERENCES litscan_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE,
                  CONSTRAINT pmcid_job_id UNIQUE (pmcid, job_id))
            ''')

            await connection.execute('''
                CREATE TABLE litscan_abstract_sentence (
                  id SERIAL PRIMARY KEY,
                  result_id INTEGER,
                  sentence TEXT,
                  FOREIGN KEY (result_id) REFERENCES litscan_result(id) ON UPDATE CASCADE ON DELETE CASCADE)
            ''')

            await connection.execute('''
                CREATE TABLE litscan_body_sentence (
                  id SERIAL PRIMARY KEY,
                  result_id INTEGER,
                  sentence TEXT,
                  location TEXT,
                  FOREIGN KEY (result_id) REFERENCES litscan_result(id) ON UPDATE CASCADE ON DELETE CASCADE)
            ''')

            await connection.execute('''
                CREATE TABLE litscan_database (
                  id SERIAL PRIMARY KEY,
                  name VARCHAR(50),
                  job_id VARCHAR(100),
                  primary_id VARCHAR(100),
                  FOREIGN KEY (job_id) REFERENCES litscan_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE,
                  FOREIGN KEY (primary_id) REFERENCES litscan_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE,
                  CONSTRAINT name_job UNIQUE (name, job_id, primary_id))
            ''')

            await connection.execute('''
                CREATE TABLE litscan_manually_annotated (
                  id SERIAL PRIMARY KEY,
                  pmcid VARCHAR(15),
                  urs VARCHAR(100),
                  FOREIGN KEY (pmcid) REFERENCES litscan_article(pmcid) ON UPDATE CASCADE ON DELETE CASCADE,
                  FOREIGN KEY (urs) REFERENCES litscan_job(job_id) ON UPDATE CASCADE ON DELETE CASCADE)
            ''')

            await connection.execute('''
                CREATE TABLE litscan_load_organism (
                  id SERIAL PRIMARY KEY,
                  pmid VARCHAR(100),
                  organism INTEGER,
                  CONSTRAINT pmid_organism UNIQUE (pmid, organism))
            ''')

            await connection.execute('''CREATE INDEX ON litscan_article (pmcid) WHERE retracted IS FALSE''')
            await connection.execute('''CREATE INDEX ON litscan_result (job_id)''')
            await connection.execute('''CREATE INDEX ON litscan_database (job_id)''')
            await connection.execute('''CREATE INDEX ON litscan_manually_annotated (urs)''')
            await connection.execute('''CREATE INDEX ON litscan_abstract_sentence (result_id)''')
            await connection.execute('''CREATE INDEX ON litscan_body_sentence (result_id)''')
