"""
Copyright [2009-2019] EMBL-European Bioinformatics Institute
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

import sqlalchemy as sa
import psycopg2

from collections import namedtuple
from consumer.settings import PORT
from database import DatabaseConnectionError
from database.models import CONSUMER_STATUS_CHOICES
from netifaces import interfaces, ifaddresses, AF_INET


def get_ip(app):
    """
    Stolen from:
    https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib?page=1&tab=active#tab-top
    """
    addresses = []
    for ifaceName in interfaces():
        for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr': 'No IP addr'}]):
            addresses.append(i['addr'])

    addresses = [address for address in addresses if address != 'No IP addr']

    # return first non-localhost IP, if available
    if app['settings'].ENVIRONMENT == 'LOCAL':
        return addresses[0]
    else:
        return addresses[1]


async def register_consumer_in_the_database(app):
    """
    Utility for consumer to register itself in the database
    :param app: params to connect to the db
    """
    try:
        async with app['engine'].acquire() as connection:
            sql_query = sa.text('''
                INSERT INTO consumer(ip, status, port)
                VALUES (:consumer_ip, :status, :port)
            ''')
            await connection.execute(
                sql_query,
                consumer_ip=get_ip(app),
                status=CONSUMER_STATUS_CHOICES.available,
                port=PORT
            )
    except psycopg2.IntegrityError as e:
        pass  # this is usually a duplicate key error - which is acceptable
    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def get_consumer_status(engine, consumer_ip):
    """
    Get consumer status from the database
    :param engine: params to connect to the db
    :param consumer_ip: IP address of the consumer
    :return: consumer status
    """
    try:
        async with engine.acquire() as connection:
            sql_query = sa.text('''
                SELECT status
                FROM consumer
                WHERE ip=:consumer_ip
            ''')
            async for row in connection.execute(sql_query, consumer_ip=consumer_ip):
                return row.status
    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def find_available_consumers(engine):
    """
    Returns a list of available consumers that can be used to run
    :param engine: params to connect to the db
    :return: list of consumers available, if any
    """
    Consumer = namedtuple('Consumer', ['ip', 'status', 'port', 'job_id'])

    try:
        async with engine.acquire() as connection:
            query = sa.text('''
                SELECT ip, status, port, job_id
                FROM consumer
                WHERE status=:status
            ''')

            result = []
            async for row in connection.execute(query, status=CONSUMER_STATUS_CHOICES.available):
                result.append(Consumer(row[0], row[1], row[2], row[3]))

        return result

    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e
