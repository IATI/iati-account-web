import logging
import tomllib

import pytz
from django.conf import settings

app_logger = logging.getLogger("iati_account")


def get_version_from_pyproject() -> str:
    try:
        fh = open(settings.PYPROJECT_TOML_PATH, "rb")
        data = tomllib.load(fh)
        if "project" not in data:
            raise RuntimeError("Cannot understand pyproject.toml structure")
        if "version" not in data["project"]:
            raise RuntimeError("Cannot understand pyproject.toml structure")
        return data["project"]["version"]
    except Exception as exc:
        app_logger.error("Cannot retrieve software version from pyproject.toml")
        raise exc


IATI_ACCOUNT_VERSION = get_version_from_pyproject()

# Format a list of timezones using the internal list in pytz.  These
# are used to allow end users to select their timezone.
TIMEZONE_LIST = [("", "--")]
for tz in pytz.common_timezones:
    tz_parts = tz.replace("_", " ").split("/")
    if len(tz_parts) == 1:
        TIMEZONE_LIST.append((tz, f"{tz}"))
    elif len(tz_parts) == 2:
        region, city = tz_parts[0], tz_parts[1]
        TIMEZONE_LIST.append((tz, f"{city} - {region}"))
    elif len(tz_parts) == 3:
        region, country, city = tz_parts[0], tz_parts[1], tz_parts[2]
        TIMEZONE_LIST.append((tz, f"{city} - {country}/{region}"))
    else:
        raise ValueError()

# Additional choice fields
REPORTING_SOURCE_TYPE_LIST = [("primary_source", "Primary Source"), ("secondary_source", "Secondary Source")]
REPORTING_SOURCE_TYPE_LOOKUP = {x[0]: x[1] for x in REPORTING_SOURCE_TYPE_LIST}
VISIBILITY_LIST = [("private", "Private"), ("public", "Public")]
VISIBILITY_LOOKUP = {x[0]: x[1] for x in VISIBILITY_LIST}
USER_ROLE_LIST = [
    ("admin", "Admin"),
    ("editor", "Editor"),
    ("contributor", "Contributor"),
    ("provider_admin", "Provider Admin"),
    ("contributor_pending", "Pending"),
    ("super_admin", "Superadmin"),
]
USER_ROLE_LOOKUP = {x[0]: x[1] for x in USER_ROLE_LIST}
