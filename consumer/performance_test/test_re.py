import re
import timeit

from consumer.settings import PROJECT_ROOT


def test():
    # list of xml files
    path_to_xml_files = PROJECT_ROOT.parent / 'consumer' / 'files'
    xml_files = [file for file in path_to_xml_files.glob('*.xml') if file.name.startswith('PMC1350429')]

    # read each of the xml files present in the files folder
    for file in xml_files:
        with open(file, "r") as f:
            read_data = f.read()
            # if re.findall("mir-21", read_data.lower()):
            if re.search("mir-21", read_data.lower()):
                pass


if __name__ == "__main__":
    # re.search: ~ 0.16
    # re.findall: ~ 0.2
    print(timeit.timeit("test()", setup="from __main__ import test", number=10))
