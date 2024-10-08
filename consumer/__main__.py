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
import asyncio

from aiojobs.aiohttp import setup as setup_aiojobs
from aiohttp import web

from . import settings
from database.models import close_pg, init_pg
from database.consumers import register_consumer_in_the_database
from database.settings import get_postgres_credentials
from .urls import setup_routes


async def on_startup(app):
    # initialize database connection
    await init_pg(app)

    # register self in the database
    app["register_consumer_task"] = asyncio.create_task(register_consumer_in_the_database(app))


async def on_cleanup(app):
    # cancel the register consumer task
    task = app.get("register_consumer_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logging.info("Background task register_consumer_in_the_database was cancelled")

    # close the database connection
    await close_pg(app)



def create_app():
    logging.basicConfig(level=logging.WARNING)

    app = web.Application()
    app.update(name="consumer", settings=settings)

    # get credentials of the correct environment
    for key, value in get_postgres_credentials(settings.ENVIRONMENT)._asdict().items():
        setattr(app["settings"], key, value)

    # create db connection on startup, shutdown on exit
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    # setup views and routes
    setup_routes(app)

    # setup aiojobs scheduler
    setup_aiojobs(app)

    return app


app = create_app()


if __name__ == "__main__":
    """
    To start the consumer, run: python3 -m consumer
    """
    web.run_app(app, host=settings.HOST, port=settings.PORT)
