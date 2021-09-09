from . import PROJECT_ROOT


# in test save queries and results in a temporary folder
TMP_DIR = PROJECT_ROOT / '.tmp'

# full path to query files
RESULTS_DIR = PROJECT_ROOT / '.tmp' / 'results'

# producer server location
PRODUCER_PROTOCOL = 'http'
PRODUCER_HOST = 'localhost'
PRODUCER_PORT = '8080'
PRODUCER_JOB_DONE_URL = 'api/job-done'
