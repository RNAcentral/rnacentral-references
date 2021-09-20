import subprocess
import timeit

from consumer.settings import PROJECT_ROOT


def test():
    # list of xml files
    path_to_xml_files = PROJECT_ROOT.parent / 'consumer' / 'files'
    xml_files = [file for file in path_to_xml_files.glob('*.xml') if file.name.startswith('PMC1350429')]

    # read each of the xml files present in the files folder
    for file in xml_files:
        command = ["/usr/bin/grep", "-o", "-m 1", "-w", "-iF", "mir-21", file]
        if subprocess.Popen(command, stdout=subprocess.PIPE).stdout.read():
            pass


if __name__ == "__main__":
    # grep: ~ 1.02
    print(timeit.timeit("test()", setup="from __main__ import test", number=10))
