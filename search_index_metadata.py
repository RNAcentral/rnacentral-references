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
import sqlalchemy as sa
import string
import uuid
import xml.etree.ElementTree as ET


from aiopg.sa import create_engine
from dotenv import load_dotenv

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
        entry = ET.SubElement(entries, "entry", id="metadata" + "_" + str(uuid.uuid4()))
        additional_fields = ET.SubElement(entry, "additional_fields")
        ET.SubElement(additional_fields, "field", name="entry_type").text = "Metadata"
        ET.SubElement(additional_fields, "field", name="database").text = item["database"]
        ET.SubElement(additional_fields, "field", name="job_id").text = item["job_id"]
        ET.SubElement(additional_fields, "field", name="primary_id").text = item["primary_id"]
        ET.SubElement(additional_fields, "field", name="manually_annotated").text = item["manually_annotated"]

    ET.SubElement(database, "entry_count").text = str(len(results))

    # save the file
    tree = ET.ElementTree(database)
    ET.indent(tree, space="\t", level=0)
    name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    with gzip.open(str(path_to_xml_files) + "/metadata_" + name + ".xml.gz", "wb") as file:
        tree.write(file)


async def search_index():
    """
    This function gets the metadata and creates a temporary list to store the data.
    It calls the create_xml_file function when the temporary list exceeds 300k results.
    Run it with: python3 search_index_metadata.py
    :return: create xml file
    """
    # get credentials
    user = os.getenv("username")
    database = os.getenv("db")
    host = os.getenv("host")
    password = os.getenv("pass")

    # create directory to store xml files, if necessary
    path_to_xml_files.mkdir(parents=True, exist_ok=True)

    # add results
    temp_results = []

    async with create_engine(user=user, database=database, host=host, password=password) as engine:
        async with engine.acquire() as connection:
            query = sa.text('''SELECT name, job_id, primary_id, manually_annotated FROM database''')
            async for row in connection.execute(query):
                temp_results.append({
                    "database": row.name,
                    "job_id": row.job_id,
                    "primary_id": row.primary_id,
                    "manually_annotated": "t" if row.manually_annotated is True else "f"
                })

                if len(temp_results) > 300000:
                    await create_xml_file(temp_results)
                    temp_results = []

        await create_xml_file(temp_results)


if __name__ == '__main__':
    asyncio.run(search_index())