from producer.settings import PROJECT_ROOT

# hostname to listen on
HOST = '0.0.0.0'

# TCP port for the server to listen on
PORT = 8080

# path to XML files for search index
path_to_xml_files = PROJECT_ROOT.parent / 'producer' / 'files'