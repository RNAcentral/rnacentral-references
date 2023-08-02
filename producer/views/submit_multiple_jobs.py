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
from database.metadata import metadata, search_metadata


@atomic
async def submit_multiple_jobs(request):
    """
    Function to submit multiple jobs and also save metadata. Run this command to test:
    curl -H "Content-Type:application/json" -d "{\"job_list\": [\"5S rRNA\", \"5S ribosomal RNA\"], \"id\": \"RF00001\", \"search_limit\": 10}" localhost:8080/api/multiple-jobs
    :param request: used to get the params to connect to the db
    :return: json with metadata
    """
    try:
        data = await request.json()
    except ValueError:
        return web.json_response({"Error": "Please check the parameters used in the search"}, status=400)

    if "job_list" not in data and "id" not in data:
        return web.json_response({"Error": "You must submit id and/or job_list as a parameter"}, status=400)

    if "job_list" in data and not isinstance(data["job_list"], list):
        return web.json_response({"Error": "You must submit a list of ids as a parameter"}, status=400)

    if "id" in data and not isinstance(data["id"], str):
        return web.json_response({"Error": "You must submit a single id in string format as a parameter"}, status=400)

    if "rescan" in data and type(data["rescan"]) is not bool:
        return web.json_response({"Error": "You must pass true or false in the rescan param"}, status=400)

    if "database" in data:
        database = data["database"].lower()
    else:
        database = "uninformed"

    # get params
    job_list = data["job_list"] if "job_list" in data else []
    primary_id = data["id"] if "id" in data else None
    query = data['query'] if "query" in data else '("rna" OR "mrna" OR "ncrna" OR "lncrna" OR "rrna" OR "sncrna")'
    search_limit = int(data['search_limit']) if "search_limit" in data else None

    ids = []
    for job in job_list:
        # check if the job_id exists in the database
        job_id = await search_performed(request.app["engine"], job)

        if job_id and "rescan" in data and data["rescan"]:
            # delete old data
            await delete_job_data(request.app['engine'], job)

            # run new search
            job_id = await save_job(request.app["engine"], job, query, search_limit)
        elif job_id:
            # get job_id value
            job_id = job_id["job_id"]
        else:
            # save job_id
            job_id = await save_job(request.app["engine"], job, query, search_limit)

        ids.append(job_id.lower())

    if primary_id:
        # check if the primary_id exists in the database
        primary_id = await search_performed(request.app["engine"], data["id"])

        if primary_id and "rescan" in data and data["rescan"]:
            # delete old data
            await delete_job_data(request.app['engine'], primary_id["job_id"])

            # run new search
            primary_id = await save_job(request.app["engine"], primary_id["job_id"], query, search_limit)
        elif primary_id:
            # get primary_id value
            primary_id = primary_id["job_id"]
        else:
            # save primary_id
            primary_id = await save_job(request.app["engine"], data['id'], query, search_limit)

        primary_id = primary_id.lower()

    # data in table litscan_database is used by Litsumm for creating summaries
    metadata_list = []

    for job in ids:
        # check if this job already exists with this database and primary_id
        get_metadata = await search_metadata(request.app["engine"], job, database, primary_id)

        if not get_metadata:
            metadata_list.append({"job_id": job, "name": database, "primary_id": primary_id})

    if primary_id and ids:
        # if there is primary_id and job_list, the primary_id should be saved as
        # id | name | job_id | primary_id
        # ---+------+--------+-------------
        # 1  | db   | id     |

        # check if this primary_id already exists with this database
        get_metadata = await search_metadata(request.app["engine"], primary_id, database, None)

        if not get_metadata:
            metadata_list.append({"job_id": primary_id, "name": database, "primary_id": None})

    elif primary_id and not ids:
        # if there is no job_list, to enable Litsumm to create a summary, the primary_id should be saved as
        # id | name | job_id | primary_id
        # ---+------+--------+-------------
        # 1  | db   |        | id

        # check if this primary_id already exists with this database
        get_metadata = await search_metadata(request.app["engine"], None, database, primary_id)

        if not get_metadata:
            metadata_list.append({"job_id": None, "name": database, "primary_id": primary_id})

    if metadata_list:
        # save metadata
        await metadata(request.app['engine'], metadata_list)

    if ids and primary_id:
        response = {"id": primary_id, "job_list": ids}
    elif primary_id:
        response = {"id": primary_id}
    else:
        response = {"job_list": ids}

    return web.json_response(response, status=201)
