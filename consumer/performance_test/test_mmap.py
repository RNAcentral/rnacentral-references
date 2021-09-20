import mmap
import re
import timeit

from consumer.settings import PROJECT_ROOT


def test():
    # list of xml files
    path_to_xml_files = PROJECT_ROOT.parent / 'consumer' / 'files'
    xml_files = [file for file in path_to_xml_files.glob('*.xml') if file.name.startswith('PMC1350429')]

    # read each of the xml files present in the files folder
    for file in xml_files:
        with open(file, mode="r", encoding="utf8") as file_obj:
            with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                job_id = b"mir-21"
                if mmap_obj.find(job_id):
                    pass

                # job_id = "mir-21"
                # regex = br"\b" + re.escape(job_id.encode()) + br"\b"
                # # if re.search(regex, mmap_obj, re.IGNORECASE):
                # if re.findall(regex, mmap_obj, re.IGNORECASE):
                #     pass


if __name__ == "__main__":
    # mmap and find: ~ 0.17 (case sensitive)
    # mmap and re.search: ~ 0.65
    # mmap and re.findall: ~ 1.55
    print(timeit.timeit("test()", setup="from __main__ import test", number=10))
