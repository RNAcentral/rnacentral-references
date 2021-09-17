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

from database.results import get_job_results
from database import DatabaseConnectionError


@atomic
async def job_result(request):
    """
    Function that returns job results
    :param request: used to get job_id and params to connect to the db
    :return: list of json object
    """
    job_id = request.match_info['job_id'].lower()
    engine = request.app['engine']

    try:
        results = await get_job_results(engine, job_id)
    except DatabaseConnectionError as e:
        raise web.HTTPNotFound() from e

    return web.json_response(results)
