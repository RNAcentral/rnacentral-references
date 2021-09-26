import mmap
import timeit

from consumer.settings import path_to_xml_files


def test():
    # list of xml files
    xml_files = [file for file in path_to_xml_files.glob('*.xml') if file.name.startswith('PMC2580001')]
    job_id = b"pre-miR-138"
    # there are 238 matches in the whole file, including words like miR-122, hsa-miR-122, and others
    # there are 169 exact matches

    # read the xml file
    for file in xml_files:
        with open(file, mode="r", encoding="utf8") as file_obj:
            with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                if mmap_obj.find(job_id):
                    pass


if __name__ == "__main__":
    # mmap and find: ~ 0.05 (finds substring!)
    print((timeit.timeit("test()", setup="from __main__ import test", number=10))/10)
