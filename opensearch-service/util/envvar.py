import os

current_directory = os.path.dirname(os.path.abspath(__file__))
newrelic_file = os.path.abspath(os.path.join(current_directory, "../newrelic.ini"))

STAGE = os.environ.get("STAGE", "")
PRODUCTS_INDEX = os.environ.get("PRODUCTS_INDEX", "products")
NEW_RELIC_CONFIG_FILE = os.environ.get("NEW_RELIC_CONFIG_FILE", newrelic_file)
AD_SERVICE_ENABLED = os.environ.get("AD_SERVICE_ENABLED", "false") == "true"
PULSE_API_KEY = os.environ.get("PULSE_API_KEY", "")
BEARER_TOKEN_LIST_ENV_VALUE = os.environ.get("SALTED_BEARER_TOKEN_LIST", "test")
OPEN_SEARCH_HOST = os.environ.get("OPEN_SEARCH_HOST", "")


def is_prod():
    return STAGE == "prod"


def is_qa():
    return STAGE == "qa"
