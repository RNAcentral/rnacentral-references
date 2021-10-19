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

from aiohttp import web
from aiojobs.aiohttp import atomic

from database.job import save_job, search_performed, search_urs_with_job_id, save_urs_with_job_id


@atomic
async def submit_job(request):
    """
    Function to start searching for ids. Run this command to test:
    curl -H "Content-Type:application/json" -d "{\"id\": \"UCA1:4\", \"urs_taxid\": \"URS00008C02AC_9606\"}" localhost:8080/api/submit-job
    :param request: used to get the params to connect to the db
    :return: json with job_id
    """
    data = await request.json()

    try:
        data['id'] = data['id'].lower()  # converts all uppercase characters to lowercase
        data['urs_taxid'] = data['urs_taxid']  # just checking if there is urs_taxid
    except KeyError:
        return web.json_response({"error": "id or urs_taxid not found"}, status=400)

    # check if this id has already been searched
    job = await search_performed(request.app['engine'], data['id'])

    # check if this id already exists with this urs_taxid in the database
    job_and_urs_taxid = await search_urs_with_job_id(request.app['engine'], data['id'], data['urs_taxid'])

    if job:
        if not job_and_urs_taxid:
            await save_urs_with_job_id(request.app['engine'], data['id'], data['urs_taxid'])

        # get job_id
        job_id = job['job_id']
    else:
        # save metadata about this job to the database
        job_id = await save_job(request.app['engine'], data['id'])

        # save urs_taxid associated with this job_id
        await save_urs_with_job_id(request.app['engine'], data['id'], data['urs_taxid'])

    return web.json_response({"job_id": job_id}, status=201)
