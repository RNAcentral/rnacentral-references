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

from database.job import save_job, search_performed, save_db_with_job_id, search_db_name_with_job_id


@atomic
async def submit_job(request):
    """
    Function to start searching for ids. Run this command to test:
    curl -H "Content-Type:application/json" -d "{\"id\": \"UCA1:4\"}" localhost:8080/api/submit-job
    :param request: used to get the params to connect to the db
    :return: json with job_id
    """
    data = await request.json()

    if "id" not in data:
        return web.json_response({"id": "Not found"}, status=400)

    # check if this id has already been searched
    job = await search_performed(request.app['engine'], data['id'])

    if job:
        # get job_id
        job_id = job['job_id']
    else:
        if "primary_id" in data:
            # get primary_id
            primary_id = await search_performed(request.app['engine'], data['primary_id'])
            primary_id = primary_id['job_id']
        else:
            primary_id = None

        # save metadata about this job to the database
        job_id = await save_job(request.app['engine'], data['id'], primary_id)

    if "database" in data:
        # check if this id already exists with this database
        job_and_db_name = await search_db_name_with_job_id(request.app['engine'], data['id'], data['database'])

        if not job_and_db_name:
            await save_db_with_job_id(request.app['engine'], data['id'], data['database'])

    return web.json_response({"job_id": job_id}, status=201)
