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
    logger.debug("POSTGRES_PASSWORD = %s" % app['settings'].POSTGRES_PASSWORD)

    app['engine'] = await create_engine(
        user=app['settings'].POSTGRES_USER,
        database=app['settings'].POSTGRES_DATABASE,
        host=app['settings'].POSTGRES_HOST,
        password=app['settings'].POSTGRES_PASSWORD
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
    'consumer',
    metadata,
    sa.Column('ip', sa.String(20), primary_key=True),
    sa.Column('status', sa.String(10)),  # choices=CONSUMER_STATUS_CHOICES, default='available'
    sa.Column('job_id', sa.ForeignKey('job.job_id')),
    sa.Column('port', sa.String(5))
)

"""Metadata of a search job"""
Job = sa.Table(
    'job',
    metadata,
    sa.Column('job_id', sa.String(100), primary_key=True),
    sa.Column('status', sa.String(10)),  # choices=JOB_STATUS_CHOICES
    sa.Column('submitted', sa.DateTime),
    sa.Column('finished', sa.DateTime, nullable=True),
    sa.Column('hit_count', sa.Integer, nullable=True),
)

"""Results of a specific Job"""
Result = sa.Table(
    'result',
    metadata,
    sa.Column('result_id', sa.Integer, primary_key=True),
    sa.Column('job_id', sa.String(100), sa.ForeignKey('job.job_id')),
    sa.Column('title', sa.Text),
    sa.Column('title_value', sa.Boolean),
    sa.Column('abstract', sa.Text),
    sa.Column('abstract_value', sa.Boolean),
    sa.Column('body', sa.Text),
    sa.Column('body_value', sa.Boolean),
    sa.Column('author', sa.Text),
    sa.Column('pmcid', sa.String(100)),
    sa.Column('pmid', sa.String(100)),
    sa.Column('doi', sa.String(100)),
    sa.Column('year', sa.Integer()),
    sa.Column('journal', sa.String(255)),
    sa.Column('score', sa.Integer()),
    sa.Column('cited_by', sa.Integer()),
)

"""Job related to which DB"""
Database = sa.Table(
    'database',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(50)),
    sa.Column('job_id', sa.String(100), sa.ForeignKey('job.job_id')),
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
        database=settings.POSTGRES_DATABASE,
        host=settings.POSTGRES_HOST,
        password=settings.POSTGRES_PASSWORD
    )

    async with engine:
        async with engine.acquire() as connection:
            await connection.execute('DROP TABLE IF EXISTS result')
            await connection.execute('DROP TABLE IF EXISTS database')
            await connection.execute('DROP TABLE IF EXISTS job')
            await connection.execute('DROP TABLE IF EXISTS consumer')

            await connection.execute('''
                CREATE TABLE consumer (
                  ip VARCHAR(20) PRIMARY KEY,
                  status VARCHAR(10) NOT NULL,
                  job_id VARCHAR(100),
                  port VARCHAR(5))
            ''')

            await connection.execute('''
                CREATE TABLE job (
                  job_id VARCHAR(100) PRIMARY KEY,
                  submitted TIMESTAMP,
                  finished TIMESTAMP,
                  status VARCHAR(10),
                  hit_count INTEGER)
            ''')

            await connection.execute('''
                CREATE TABLE result (
                  result_id SERIAL PRIMARY KEY,
                  job_id VARCHAR(100),
                  title TEXT,
                  title_value BOOLEAN,
                  abstract TEXT,
                  abstract_value BOOLEAN,
                  body TEXT,
                  body_value BOOLEAN,
                  author TEXT,
                  pmcid VARCHAR(100),
                  pmid VARCHAR(100),
                  doi VARCHAR(100),
                  year INTEGER,
                  journal VARCHAR(255),
                  score INTEGER,
                  cited_by INTEGER,
                  FOREIGN KEY (job_id) REFERENCES job(job_id) ON UPDATE CASCADE ON DELETE CASCADE,
                  CONSTRAINT jobid_pmcid UNIQUE (job_id, pmcid))
            ''')

            await connection.execute('''
                CREATE TABLE database (
                  id SERIAL PRIMARY KEY,
                  name VARCHAR(50),
                  job_id VARCHAR(100),
                  FOREIGN KEY (job_id) REFERENCES job(job_id) ON UPDATE CASCADE ON DELETE CASCADE,
                  CONSTRAINT name_job UNIQUE (name, job_id))
            ''')

            await connection.execute('''CREATE INDEX on result (job_id)''')
            await connection.execute('''CREATE INDEX on database (job_id)''')
