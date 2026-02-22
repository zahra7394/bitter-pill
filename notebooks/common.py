# Directory containing HAR files from the data collection phase (Algorithm 1).
# For reproducibility, place HAR files in this path or set it to your data location.
from os.path import dirname, join, abspath

_REPO_ROOT = dirname(dirname(abspath(__file__)))
BASE_HAR_DIR = join(_REPO_ROOT, 'har_data')

# Placeholder persona details used during checkout for leak detection.
# For actual data collection, replace with your test personas (unique per consent mode).
PERSONA_DETAILS = {
    "accept_social": {
        "email": "accept-social@example.com",
        "first_name": "given",
        "last_name": "surname",
        "birthday_1": "01-01-2002",
        "birthday_2": "20020101",
        "phone_1": "+31600000001",
        "phone_2": "0600000001",
        "phone_3": "31600000001",
        "gender_1": "female",
        "gender_2": "f"
    },
    "accept_tracking": {
        "email": "accept-tracking@example.com",
        "first_name": "given",
        "last_name": "surname",
        "birthday_1": "01-01-2002",
        "birthday_2": "20020101",
        "phone_1": "+31600000001",
        "phone_2": "0600000001",
        "phone_3": "31600000001",
        "gender_1": "female",
        "gender_2": "f"
    },
    "reject_social": {
        "email": "reject-social@example.com",
        "first_name": "given",
        "last_name": "surname",
        "birthday_1": "01-01-2002",
        "birthday_2": "20020101",
        "phone_1": "+31600000002",
        "phone_2": "0600000002",
        "phone_3": "31600000002",
        "gender_1": "female",
        "gender_2": "f"
    },
    "reject_tracking": {
        "email": "reject-tracking@example.com",
        "first_name": "given",
        "last_name": "surname",
        "birthday_1": "01-01-2002",
        "birthday_2": "20020101",
        "phone_1": "+31600000002",
        "phone_2": "0600000002",
        "phone_3": "31600000002",
        "gender_1": "female",
        "gender_2": "f"
    },
    "nl_address": {
        "street": "Example Street 1",
        "city": "Amsterdam",
        "province": "Noord-Holland",
        "zip": "1000aa"
    },
    "de_address": {
        "street": "Beispielstraße 1",
        "city": "Berlin",
        "province": "Berlin",
        "zip": "10115"
    },
    "fr_address": {
        "street": "1 Rue Example",
        "city": "Paris",
        "province": "Île-de-France",
        "zip": "75000"
    },
    "it_address": {
        "street": "Via Esempio 1",
        "city": "Milano",
        "province": "Milano",
        "zip": "20100"
    },
    "es_address": {
        "street": "Calle Ejemplo 1",
        "city": "Madrid",
        "province": "Madrid",
        "zip": "28001"
    }
}
