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
import requests

from bs4 import BeautifulSoup
from pathlib import Path


def main():
    """
    Function to get xml files
    :return: create xml file in consumer/files folder
    """
    # Get files from europepmc
    url = "https://europepmc.org/ftp/oa/"
    url_data = requests.get(url).text
    soup = BeautifulSoup(url_data, "html.parser")

    # create directory to store xml files, if necessary
    Path("consumer/files").mkdir(parents=True, exist_ok=True)

    # list of xml files in consumer/files directory
    path_to_xml_files = Path('consumer/files')
    xml_files = [file.name for file in path_to_xml_files.glob('*.xml.gz')]

    # check all links
    for link in soup.find_all('a'):
        file = link.get('href')

        # download and create a new file, if necessary
        if file.startswith("PMC1") and file not in xml_files:
            get_xml = requests.get(url + file, stream=True)
            with open('consumer/files/' + file, 'wb') as new_file:
                for chunk in get_xml.iter_content(chunk_size=10000):
                    new_file.write(chunk)


if __name__ == "__main__":
    main()
