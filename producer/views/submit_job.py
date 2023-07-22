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

from database.job import delete_job_data, save_job, search_performed


async def save_job_data(engine, data):
    """
    Function to save job in the database
    :param engine: params to connect to the db
    :param data: job details
    :return: job_id
    """
    # get params
    query = data['query'] if "query" in data else '("rna" OR "mrna" OR "ncrna" OR "lncrna" OR "rrna" OR "sncrna")'
    search_limit = int(data['search_limit']) if "search_limit" in data else None

    # save metadata about this job
    job_id = await save_job(engine, data['id'], query, search_limit)

    return job_id


@atomic
async def submit_job(request):
    """
    Function to start searching for ids. Run this command to test:
    curl -H "Content-Type:application/json" -d "{\"id\": \"RF00001\"}" localhost:8080/api/submit-job
    :param request: used to get the params to connect to the db
    :return: json with job_id
    """
    try:
        data = await request.json()
    except ValueError:
        return web.json_response({"Error": "Please check the parameters used in the search"}, status=400)

    if "id" not in data:
        return web.json_response({"Error": "Id not found"}, status=400)

    if "rescan" in data and type(data["rescan"]) is not bool:
        return web.json_response({"Error": "You must pass true or false in the rescan param"}, status=400)

    # check if this id has already been searched
    job = await search_performed(request.app['engine'], data['id'])

    if job and "rescan" in data and data["rescan"]:
        # delete old data
        await delete_job_data(request.app['engine'], job['job_id'])

        # run new search
        job_id = await save_job_data(request.app['engine'], data)
    elif job:
        # return current job_id
        job_id = job['job_id']
    else:
        # run new search
        job_id = await save_job_data(request.app['engine'], data)

    return web.json_response({"job_id": job_id}, status=201)
