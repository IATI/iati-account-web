import logging
import tomllib

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
