import re
import timeit

from consumer.settings import PROJECT_ROOT


def test():
    # list of xml files
    path_to_xml_files = PROJECT_ROOT.parent / 'consumer' / 'files'
    xml_files = [file for file in path_to_xml_files.glob('*.xml') if file.name.startswith('PMC2580001')]
    job_id = "mir-122"
    # there are 238 matches in the whole file, including words like miR-122, hsa-miR-122, and others
    # there are 169 exact matches

    # read the xml file
    for file in xml_files:
        with open(file, "r") as f:
            read_data = f.read()
            regex = r"[\s*>]" + re.escape(job_id) + "[\s*<.,?!]"
            if re.search(regex, read_data.lower()):
                pass


if __name__ == "__main__":
    # re.search: ~ 0.38
    print((timeit.timeit("test()", setup="from __main__ import test", number=10))/10)
