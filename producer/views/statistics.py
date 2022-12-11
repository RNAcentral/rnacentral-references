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

from aiohttp import web
from aiojobs.aiohttp import atomic

from database.statistics import get_urs_count
from database import DatabaseConnectionError


@atomic
async def urs_hit_count(request):
    """
    Function that returns the number of publications per urs_taxid
    :param request: extract params to connect to the db
    :return: list of json object
    """
    engine = request.app['engine']

    try:
        results = await get_urs_count(engine)
    except DatabaseConnectionError as e:
        raise web.HTTPNotFound() from e

    return web.json_response(results)
