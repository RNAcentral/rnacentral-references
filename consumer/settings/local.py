from . import PROJECT_ROOT


# full path to results files
RESULTS_DIR = PROJECT_ROOT / 'results'

# producer server location
PRODUCER_PROTOCOL = 'http'
PRODUCER_HOST = 'localhost'
PRODUCER_PORT = '8080'
PRODUCER_JOB_DONE_URL = 'api/job-done'
