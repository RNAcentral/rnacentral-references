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
from aiohttp.test_utils import unittest_run_loop

from database.consumers import find_available_consumers, get_ip, get_consumer_status, register_consumer_in_the_database
from database.models import Consumer, CONSUMER_STATUS_CHOICES
from database.tests.test_base import DBTestCase


class RegisterConsumerInTheDatabaseTestCase(DBTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python -m unittest database.tests.test_consumers.RegisterConsumerInTheDatabaseTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

    @unittest_run_loop
    async def test_register_consumer_in_the_database(self):
        await register_consumer_in_the_database(self.app)
        consumer_ip = get_ip(self.app)

        consumer = await get_consumer_status(self.app['engine'], consumer_ip)
        assert consumer == CONSUMER_STATUS_CHOICES.available


class FindAvailableConsumersTestCase(DBTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python -m unittest database.tests.test_consumers.FindAvailableConsumersTestCase

    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Consumer.insert().values(
                    ip='192.168.0.2',
                    status=CONSUMER_STATUS_CHOICES.available
                )
            )

            await connection.execute(
                Consumer.insert().values(
                    ip='192.168.0.3',
                    status=CONSUMER_STATUS_CHOICES.busy
                )
            )

            await connection.execute(
                Consumer.insert().values(
                    ip='192.168.0.4',
                    status=CONSUMER_STATUS_CHOICES.available
                )
            )

    @unittest_run_loop
    async def test_find_available_consumer(self):
        consumers = await find_available_consumers(self.app['engine'])

        for index, row in enumerate(consumers):
            if index == 0:
                assert row.ip == '192.168.0.2'
                assert row.status == CONSUMER_STATUS_CHOICES.available
            elif index == 1:
                assert row.ip == '192.168.0.4'
                assert row.status == CONSUMER_STATUS_CHOICES.available
