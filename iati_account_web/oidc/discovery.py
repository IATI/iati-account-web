import logging
import threading
from typing import Any

import requests
from django.core.exceptions import ImproperlyConfigured


def get_openid_configuration(
    discovery_endpoint: str,
    required_keys: set = {
        "authorization_endpoint",
        "token_endpoint",
        "userinfo_endpoint",
        "jwks_uri",
        "end_session_endpoint",
    },
) -> dict[str, Any]:
    """Get OpenID Connect configuration from the discovery_endpoint endpoint.

    Parameters
    ----------
    discovery_endpoint : str
        URL of the discovery (".well-known") endpoint, e.g., https://example.org/.well-known/openid-configuration.
    required_keys : set, optional
        Keys that this function will make sure are in the response, by default {"authorization_endpoint",
        "token_endpoint", "userinfo_endpoint", "jwks_uri", "end_session_endpoint"}

    Returns
    -------
    dict[str, Any]

    Raises
    ------
    RuntimeError
        In case of an error communicating with the identity server endpoint, parsing the
        result, or validating the required keys.
    """
    try:
        response = requests.get(discovery_endpoint)
        response.raise_for_status()
        config = response.json()
    except Exception as exc:
        raise RuntimeError("Cannot get OpenID configuration") from exc

    if not required_keys.issubset(set(config.keys())):
        raise RuntimeError(
            f"OpenID configuration doesn't have the required fields: " f"missing {required_keys-set(config.keys())}"
        )

    return config


class LazyOpenIdConfiguration:
    """Lazy loading of OpenId Connect configuration from discovery endpoint

    This class is a thread-safe container for OpenID Connect parameters
    obtained from a ".well-known" discovery endpoint.  The parameters are
    loaded lazily so that they can be defined in Django settings, and accessed
    via django.conf.settings, but the API call to fetch the settings doesn't
    happen at import time, only run time.
    """

    CONFIG_CACHE = None
    DISCOVERY_ENDPOINT = None
    REQUIRED_KEYS = set(
        [
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
            "end_session_endpoint",
        ]
    )
    _LOCK = threading.Lock()

    def __init__(self, name: str, discovery_endpoint: str):
        """Initialise parameter container

        Parameters
        ----------
        name : str
            Name of the parameter to return from this object.
        discovery_endpoint : str
            URL of the .well-known endpoint, e.g., https://example.org/.well-known/openid-configuration.
        """
        print(f"Initialising: {name} {discovery_endpoint}")
        self._name = name

        # Check the caller is not trying to change the discovery endpoint URL.
        if LazyOpenIdConfiguration.DISCOVERY_ENDPOINT is not None:
            with LazyOpenIdConfiguration._LOCK:
                if LazyOpenIdConfiguration.DISCOVERY_ENDPOINT != discovery_endpoint:
                    raise RuntimeError(
                        "There is a conflict between the existing discovery endpoint "
                        f"{LazyOpenIdConfiguration.DISCOVERY_ENDPOINT} and the requested endpoint {discovery_endpoint}"
                    )

        # Set the discovery endpoint.
        if LazyOpenIdConfiguration.DISCOVERY_ENDPOINT is None:
            with LazyOpenIdConfiguration._LOCK:
                if LazyOpenIdConfiguration.DISCOVERY_ENDPOINT is None:
                    LazyOpenIdConfiguration.DISCOVERY_ENDPOINT = discovery_endpoint

    def __str__(self) -> str:
        """Return the string for the configured OIDC configuration parameter

        Returns
        -------
        str

        Raises
        ------
        ImproperlyConfigured
            If the OIDC configuration cannot be fetched from the discovery endpoint.
        """

        if LazyOpenIdConfiguration.CONFIG_CACHE is None:
            with LazyOpenIdConfiguration._LOCK:

                # Double check in case another thread has initialised while waiting for the lock.
                if LazyOpenIdConfiguration.CONFIG_CACHE is None:

                    # Try to load the configuration from the discovery endpoint.
                    try:
                        logging.getLogger("iati_account").info("Fetching OIDC configuration from discovery endpoint")
                        config = get_openid_configuration(
                            LazyOpenIdConfiguration.DISCOVERY_ENDPOINT, LazyOpenIdConfiguration.REQUIRED_KEYS
                        )
                    except RuntimeError as exc:
                        logging.getLogger("iati_account").critical(
                            f"Cannot fetch OIDC configuration from discovery endpoint {exc}"
                        )
                        raise ImproperlyConfigured(
                            "Cannot fetch OIDC configuration from the discovery endpoint"
                        ) from exc

                    # Was loaded okay, so stored the retrieved configuration in the cache.
                    LazyOpenIdConfiguration.CONFIG_CACHE = config

        # Return the parameter as requested.
        return LazyOpenIdConfiguration.CONFIG_CACHE[self._name]
