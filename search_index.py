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
import os
import xml.etree.cElementTree as ET

from aiopg.sa import create_engine
from dotenv import load_dotenv

from database.job import get_jobs
from database.results import get_job_results
from producer.settings import path_to_xml_files

load_dotenv()


async def search_index():
    """
    This function fetches the results of each job_id and creates the XML that will be used by the search index
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

        # start to create a XML file
        database = ET.Element("database")
        ET.SubElement(database, "name").text = "RNAcentral"
        entries = ET.SubElement(database, "entries")

        for job in job_ids:
            results = await get_job_results(engine, job["job_id"])

            # iterate over the results to complete the xml
            for item in results:
                entry = ET.SubElement(entries, "entry", id=job["urs_taxid"] + "_" + item['pmcid'])
                additional_fields = ET.SubElement(entry, "additional_fields")
                ET.SubElement(additional_fields, "field", name="entry_type").text = "Publication"
                ET.SubElement(additional_fields, "field", name="job_id").text = job["job_id"]
                ET.SubElement(additional_fields, "field", name="urs_taxid").text = job["urs_taxid"]
                ET.SubElement(additional_fields, "field", name="title").text = item['title']
                ET.SubElement(additional_fields, "field", name="title_contains_value").text = item['title_contains_value']
                ET.SubElement(additional_fields, "field", name="abstract").text = item['abstract']
                ET.SubElement(additional_fields, "field", name="body").text = item['body']
                ET.SubElement(additional_fields, "field", name="author").text = item['author']
                ET.SubElement(additional_fields, "field", name="pmcid").text = item['pmcid']
                ET.SubElement(additional_fields, "field", name="pmid").text = item['pmid']
                ET.SubElement(additional_fields, "field", name="doi").text = item['doi']

        # save the file
        tree = ET.ElementTree(database)
        tree.write(str(path_to_xml_files) + "/publications.xml")


if __name__ == '__main__':
    asyncio.run(search_index())
