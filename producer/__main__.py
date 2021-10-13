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

import argparse
import logging
import asyncio

import aiohttp_cors
from aiojobs.aiohttp import setup as setup_aiojobs
from aiohttp import web

from . import settings
from database.job import find_job_to_run
from database.consumers import find_available_consumers
from database.models import close_pg, init_pg, migrate
from database.settings import get_postgres_credentials
from producer.consumer_jobs import delegate_job_to_consumer
from .urls import setup_routes


async def on_startup(app):
    # initialize database connection
    await init_pg(app)

    if hasattr(app['settings'], "MIGRATE") and app['settings'].MIGRATE:
        # create initial migrations in the database
        await migrate(app['settings'].ENVIRONMENT)

    # initialize scheduling tasks to consumers in background
    await create_consumer_scheduler(app)


async def check_jobs_and_consumers(app):
    # if there are any pending jobs and free consumers, schedule their execution
    unfinished_job = await find_job_to_run(app['engine'])
    available_consumers = await find_available_consumers(app['engine'])

    for consumer in available_consumers:
        if unfinished_job:
            job = unfinished_job.pop(0)
            await delegate_job_to_consumer(
                consumer_ip=consumer.ip,
                consumer_port=consumer.port,
                job_id=job[0]
            )


async def create_consumer_scheduler(app):
    """
    Periodically runs a task that checks the status of consumers in the database and
     - schedules jobs to run on consumers
     - restarts stuck consumers

    Stolen from:
    https://stackoverflow.com/questions/37512182/how-can-i-periodically-execute-a-function-with-asyncio
    """
    async def periodic():
        while True:
            loop.create_task(check_jobs_and_consumers(app))
            await asyncio.sleep(4)

    loop = asyncio.get_event_loop()
    loop.create_task(periodic())


def create_app():
    """
    Create an Application instance
    """
    logging.basicConfig(level=logging.DEBUG)

    app = web.Application()
    app.update(name='producer', settings=settings)

    # get credentials of the correct environment
    for key, value in get_postgres_credentials(settings.ENVIRONMENT)._asdict().items():
        setattr(app['settings'], key, value)

    # create db connection on startup, shutdown on exit
    app.on_startup.append(on_startup)
    app.on_cleanup.append(close_pg)

    # setup views and routes
    setup_routes(app)

    # setup aiojobs scheduler
    setup_aiojobs(app)

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)

    return app


if __name__ == '__main__':
    """
    To start the producer, run: python3 -m producer
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--migrate',
        dest='MIGRATE',
        default=False,
        action='store_true',
        help='Should migrations (that clean the database) be applied on producer startup'
    )
    args = parser.parse_args()

    # update settings with args
    for key, value in vars(args).items():
        setattr(settings, key, value)

    app = create_app()
    web.run_app(app, host=app['settings'].HOST, port=app['settings'].PORT)
