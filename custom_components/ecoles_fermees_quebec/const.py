"""Constants for the Écoles fermées Québec integration."""

from datetime import timedelta

DOMAIN = "ecoles_fermees_quebec"

CONF_SCHOOL_ID = "school_id"
CONF_SCHOOL_NAME = "school_name"
CONF_TOWN = "town"
CONF_SEARCH = "search"

URL_CLOSED = "https://www.tvanouvelles.ca/api/schools/closed"
URL_LIST = "https://www.tvanouvelles.ca/api/schools/list"
TVA_STATUS_URL = "https://www.tvanouvelles.ca/etat-ecoles-fermees"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; HomeAssistant-EcolesFermeesQuebec/1.0; "
        "+https://www.home-assistant.io/)"
    ),
    "Accept": "application/json",
}

UPDATE_INTERVAL = timedelta(minutes=5)
SCHOOL_LIST_CACHE_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT = 30

MIN_SEARCH_LENGTH = 2
MAX_SEARCH_RESULTS = 80

STATE_OPEN = "open"
STATE_CLOSED = "closed"
STATE_NONE = "none"

ATTR_SCHOOL_ID = "school_id"
ATTR_TOWN = "town"
ATTR_CSS = "css"
ATTR_MESSAGE = "message"
ATTR_INFORMATIONS = "informations"
ATTR_START = "start"
ATTR_END = "end"
ATTR_LAST_UPDATED = "last_updated"
