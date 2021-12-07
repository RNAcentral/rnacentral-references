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

import asyncio
import gzip
import os
import random
import string
import xml.etree.ElementTree as ET


from aiopg.sa import create_engine
from dotenv import load_dotenv

from database.job import get_jobs
from database.results import get_job_results
from producer.settings import path_to_xml_files

load_dotenv()


async def create_xml_file(results):
    """
    Creates the XML that will be used by the search index
    :param results: list of results
    :return: None
    """
    # start to create a XML file
    database = ET.Element("database")
    ET.SubElement(database, "name").text = "RNAcentral"
    entries = ET.SubElement(database, "entries")

    for item in results:
        entry = ET.SubElement(entries, "entry", item["job_id"] + "_" + item['pmcid'])
        additional_fields = ET.SubElement(entry, "additional_fields")
        ET.SubElement(additional_fields, "field", name="entry_type").text = "Publication"
        ET.SubElement(additional_fields, "field", name="job_id").text = item["job_id"]
        ET.SubElement(additional_fields, "field", name="title").text = item['title']
        ET.SubElement(additional_fields, "field", name="title_value").text = item['title_value']
        ET.SubElement(additional_fields, "field", name="abstract").text = item['abstract']
        ET.SubElement(additional_fields, "field", name="abstract_value").text = item['abstract_value']
        ET.SubElement(additional_fields, "field", name="body").text = item['body']
        ET.SubElement(additional_fields, "field", name="body_value").text = item['body_value']
        ET.SubElement(additional_fields, "field", name="author").text = item['author']
        ET.SubElement(additional_fields, "field", name="pmcid").text = item['pmcid']
        ET.SubElement(additional_fields, "field", name="pmid").text = item['pmid']
        ET.SubElement(additional_fields, "field", name="doi").text = item['doi']
        ET.SubElement(additional_fields, "field", name="journal").text = item['journal']
        ET.SubElement(additional_fields, "field", name="year").text = item['year']
        ET.SubElement(additional_fields, "field", name="score").text = item['score']
        ET.SubElement(additional_fields, "field", name="cited_by").text = item['cited_by']

    ET.SubElement(database, "entry_count").text = str(len(results))

    # save the file
    tree = ET.ElementTree(database)
    ET.indent(tree, space="\t", level=0)
    name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    with gzip.open(str(path_to_xml_files) + "/publications_" + name + ".xml.gz", "wb") as file:
        tree.write(file)


async def search_index():
    """
    This function fetches the results of each job_id and creates a temporary list to store the data.
    It calls the create_xml_file function when the temporary list exceeds 200k results.
    Run it with: python3 search_index.py
    :return: create xml file
    """
    # get credentials
    user = os.getenv("username")
    database = os.getenv("db")
    host = os.getenv("host")
    password = os.getenv("pass")

    async with create_engine(user=user, database=database, host=host, password=password) as engine:
        # get jobs
        job_ids = await get_jobs(engine)

        # create directory to store xml files, if necessary
        path_to_xml_files.mkdir(parents=True, exist_ok=True)

        # add results
        temp_results = []

        for job in job_ids:
            # get results
            results = await get_job_results(engine, job)

            for result in results:
                temp_results.append({
                    "job_id": job,
                    "title": result["title"],
                    "title_value": str(result['title_value']),
                    "abstract": result['abstract'],
                    "abstract_value": str(result['abstract_value']),
                    "body": result['body'],
                    "body_value": str(result['body_value']),
                    "author": result['author'],
                    "pmcid": result['pmcid'],
                    "pmid": result['pmid'],
                    "doi": result['doi'],
                    "journal": result['journal'],
                    "year": str(result['year']),
                    "score": str(result['score']),
                    "cited_by": str(result['cited_by']),
                })

                if len(temp_results) > 200000:
                    await create_xml_file(temp_results)
                    temp_results = []

        await create_xml_file(temp_results)


if __name__ == '__main__':
    asyncio.run(search_index())
