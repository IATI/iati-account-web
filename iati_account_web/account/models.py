import logging

import oauthlib
import requests_oauthlib
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from iati_account_web.constants import TIMEZONE_LIST
from iati_account_web.exceptions import IdentityServiceConnectionError, IdentityServicePatchError
from iati_account_web.settings import COUNTRY_LIST
from requests import ConnectionError, HTTPError, Timeout

app_logger = logging.getLogger("iati_account")


class IATIUser(AbstractUser):
    email = models.EmailField(blank=False)
    oidc_sub = models.CharField(max_length=36, blank=False)
    unformatted_name = models.CharField(max_length=128, blank=False)
    inperson_name = models.CharField(max_length=128, blank=True)
    online_name = models.CharField(max_length=128, blank=True)
    mailinglist_subscriber = models.BooleanField(default=False)
    country = models.CharField(max_length=64, choices=COUNTRY_LIST, default="", blank=True)
    timezone = models.CharField(max_length=64, choices=TIMEZONE_LIST, default="", blank=True)
    language_en = models.BooleanField(default=False)
    language_fr = models.BooleanField(default=False)
    language_es = models.BooleanField(default=False)
    use_cases_migration = models.BooleanField(default=False)
    use_cases_publishing = models.BooleanField(default=False)
    use_cases_using_data = models.BooleanField(default=False)
    use_cases_mailinglist = models.BooleanField(default=False)
    use_cases_forum = models.BooleanField(default=False)
    has_been_onboarded = models.BooleanField(default=False)
    has_been_provisioned = models.BooleanField(default=False)
    registry_id = models.CharField(max_length=36, blank=True, default="")
    is_iati_superadmin = models.BooleanField(default=False)

    @property
    def has_complete_geolocation(self) -> bool:
        return self.country and self.timezone

    @property
    def has_complete_names(self) -> bool:
        return self.unformatted_name and self.inperson_name and self.online_name

    @property
    def has_subscribed_to_mailing_lists(self) -> bool:
        return self.mailinglist_subscriber

    @property
    def has_complete_profile(self) -> bool:
        return self.has_complete_geolocation and self.has_complete_names

    @property
    def first_registration_use_cases(self) -> str:
        """Return string of first registration use cases.

        Use cases are stored in the Identity Service as a set of space-separated strings.
        This function formats the use case booleans into a string.

        Returns
        -------
        str
        """
        return " ".join(
            filter(
                None,
                [
                    "migration" if self.use_cases_migration else None,
                    "publishing" if self.use_cases_publishing else None,
                    "usingdata" if self.use_cases_using_data else None,
                    "mailinglist" if self.use_cases_mailinglist else None,
                    "forum" if self.use_cases_forum else None,
                ],
            )
        )

    def set_first_registration_use_cases(self, s: str) -> None:
        """Converts a string of first registration use cases into internal booleans

        Parameters
        ----------
        s : str
        """
        self.use_cases_migration = False
        self.use_cases_publishing = False
        self.use_cases_using_data = False
        self.use_cases_mailinglist = False
        self.use_cases_forum = False
        if "migration" in s:
            self.use_cases_migration = True
        if "publishing" in s:
            self.use_cases_publishing = True
        if "usingdata" in s:
            self.use_cases_using_data = True
        if "mailinglist" in s:
            self.use_cases_mailinglist = True
        if "forum" in s:
            self.use_cases_forum = True

    @property
    def languages(self) -> str:
        """Return string of preferred languages

        Use user's list of preferred languages are stored in the Identity Service as a set of
        space-separated strings. This function formats the language booleans into a string.

        Returns
        -------
        str
        """
        return " ".join(
            filter(
                None,
                [
                    "en" if self.language_en else None,
                    "fr" if self.language_fr else None,
                    "es" if self.language_es else None,
                ],
            )
        )

    def set_languages(self, s: str):
        """Converts a string of languages into internal booleans

        Parameters
        ----------
        s : str
        """
        self.language_en = False
        self.language_fr = False
        self.language_es = False
        if "en" in s:
            self.language_en = True
        if "fr" in s:
            self.language_fr = True
        if "es" in s:
            self.language_es = True

    @property
    def log_label(self) -> str:
        """Short string to help identify users in audit logs"""
        if self.registry_id:
            return f"{self.oidc_sub} ({self.unformatted_name}) [crm id {self.registry_id}]"
        else:
            return f"{self.oidc_sub} ({self.unformatted_name})"

    def update_from_claims(self, claims: dict[str, str], include_sub: bool = False):
        """Update the user model fields from an OIDC claims dictionary

        Parameters
        ----------
        claims : dict[str, str]
            Dictionary of claims obtained via OIDC login.
        include_sub : bool, optional
            Update the ID from the identity service, by default False.
        """
        if include_sub:
            self.oidc_sub = claims.get("sub", "")
        self.unformatted_name = claims.get("name", "")
        self.email = claims.get("email", "")
        self.inperson_name = claims.get("iatiInPersonName", "")
        self.online_name = claims.get("iatiOnlineName", "")
        self.mailinglist_subscriber = True if claims.get("iatiMailingList", "false").lower() == "true" else False
        self.set_languages(claims.get("iatiPreferredLanguage", ""))
        self.country = claims.get("iatiCountry", "")
        self.timezone = claims.get("iatiTimeZone", "")
        self.set_first_registration_use_cases(claims.get("iatiFirstRegistrationUseCases", ""))
        self.has_been_onboarded = True if claims.get("iatiHasBeenOnboarded", "false").lower() == "true" else False
        self.registry_id = claims.get("iatiRegistryId", "")
        self.has_been_provisioned = True if claims.get("iatiHasBeenProvisioned", "false").lower() == "true" else False
        if "Internal/iati_superadmin" in claims.get("roles", []):
            self.is_iati_superadmin = True

    @staticmethod
    def _connect_to_identity_service(scope: str = settings.IDENTITY_SERVICE_SCIM2_SCOPES) -> dict[str, str] | None:
        """Connect to and get an access token from the identity service

        Parameters
        ----------
        scope : str, optional
            List of scopes to request from the identity service, default is IDENTITY_SERVICE_SCIM2_SCOPES
            from settings.

        Returns
        -------
        str | None
            Access token or None.
        """
        # Get an access token from Asgardeo.
        try:
            client = oauthlib.oauth2.BackendApplicationClient(
                client_id=settings.IDENTITY_SERVICE_CLIENT_ID,
                scope=scope,
            )
            session = requests_oauthlib.OAuth2Session(client=client)

            access_token = session.fetch_token(
                token_url=settings.IDENTITY_SERVICE_BASE_URL + "oauth2/token",
                client_id=settings.IDENTITY_SERVICE_CLIENT_ID,
                client_secret=settings.IDENTITY_SERVICE_CLIENT_SECRET,
            ).get("access_token", None)
        except Exception as exc:
            app_logger.debug(f"An exception was raised while fetching access token from Asgardeo (exception {exc})")
            return None

        return {"client": client, "session": session, "access_token": access_token}

    def patch_user_in_identity_service(  # noqa: C901
        self, update_registry_id: bool = False, update_provisioned: bool = False
    ):
        """Patches user record in the Identity Service

        Parameters
        ----------
        update_registry_id : bool, optional
            If true, updates the registry_id field in the identity service.  By default does not.
        update_provisioned : bool, optional
            If true, updates the has_been_provisioned field in the identity service.  By default does not.
        """

        idp = self._connect_to_identity_service()
        if idp is None:
            raise IdentityServiceConnectionError

        # Construct patch payload.
        payload = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {
                    "op": "replace",
                    "path": "name",
                    "value": {"familyName": self.unformatted_name, "formatted": self.unformatted_name},
                },
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiInPersonName",
                    "value": self.inperson_name,
                },
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiOnlineName",
                    "value": self.online_name,
                },
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiMailingList",
                    "value": "true" if self.mailinglist_subscriber else "false",
                },
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiPreferredLanguage",
                    "value": self.languages,
                },
                {"op": "replace", "path": "urn:scim:schemas:extension:custom:User:iatiCountry", "value": self.country},
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiTimeZone",
                    "value": self.timezone,
                },
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiHasBeenOnboarded",
                    "value": "true" if self.has_been_onboarded else "false",
                },
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiFirstRegistrationUseCases",
                    "value": self.first_registration_use_cases,
                },
            ],
        }
        if update_registry_id:
            payload["Operations"].append(
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiRegistryId",
                    "value": self.registry_id,
                }
            )
        if update_provisioned:
            payload["Operations"].append(
                {
                    "op": "replace",
                    "path": "urn:scim:schemas:extension:custom:User:iatiHasBeenProvisioned",
                    "value": self.has_been_provisioned,
                }
            )

        # Do the patch operation.
        try:
            response = idp["session"].patch(
                f"{settings.IDENTITY_SERVICE_BASE_URL}scim2/Users/{self.oidc_sub}",
                json=payload,
                headers={"Content-Type": "application/scim+json"},
            )
            response.raise_for_status()
        except HTTPError as exc:
            app_logger.debug(f"Cannot patch user in identity service due an HTTP Error ({exc})")
            raise IdentityServicePatchError(f"Cannot patch user the identity service due to HTTP Error ({exc})")
        except ConnectionError as exc:
            app_logger.debug(f"Cannot patch user in identity service due a connection error ({exc})")
            raise IdentityServicePatchError(f"Cannot patch user in identity service due a connection error ({exc})")
        except Timeout as exc:
            app_logger.debug(f"Cannot patch user in identity service due a timeout ({exc})")
            raise IdentityServicePatchError(f"Cannot patch user in identity service due a timeout ({exc})")
        except Exception as exc:
            app_logger.debug(f"Cannot patch user in identity service due an unknown error ({exc})")
            raise IdentityServicePatchError(f"Cannot patch user in identity service due an unknown error ({exc})")

    def lock_account(self) -> None:
        """Tries to lock user account in the identity service"""

        idp = self._connect_to_identity_service()
        if idp is None:
            raise IdentityServiceConnectionError

        # Construct patch payload.
        payload = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "replace", "path": "active", "value": "false"}],
        }

        # Do the patch operation.
        try:
            response = idp["session"].patch(
                f"{settings.IDENTITY_SERVICE_BASE_URL}scim2/Users/{self.oidc_sub}",
                json=payload,
                headers={"Content-Type": "application/scim+json"},
            )
            response.raise_for_status()
        except HTTPError as exc:
            app_logger.debug(f"Cannot lock user in the identity service due an HTTP Error ({exc})")
            raise IdentityServicePatchError(f"Cannot lock user in the identity service due to HTTP Error ({exc})")
        except ConnectionError as exc:
            app_logger.debug(f"Cannot lock user in the identity service due a connection error ({exc})")
            raise IdentityServicePatchError(f"Cannot lock user in the identity service due a connection error ({exc})")
        except Timeout as exc:
            app_logger.debug(f"Cannot lock user in the identity service due a timeout ({exc})")
            raise IdentityServicePatchError(f"Cannot lock user in the identity service due a timeout ({exc})")
        except Exception as exc:
            app_logger.debug(f"Cannot lock user in the identity service due an unknown error ({exc})")
            raise IdentityServicePatchError(f"Cannot lock user in the identity service due an unknown error ({exc})")

    def add_role_to_user_in_identity_service(self, role_id: str) -> None:
        """Sets the user the iati_register_your_data role in the Identity Service

        Parameters
        ----------
        role_id : str
            Role ID for the role we want to grant.
        """

        idp = self._connect_to_identity_service()
        if idp is None:
            raise IdentityServiceConnectionError

        try:
            response = idp["session"].patch(
                f"{settings.IDENTITY_SERVICE_BASE_URL}/scim2/v3/Roles/{role_id}/Users",
                json={
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [{"op": "add", "value": [{"value": self.oidc_sub}]}],
                },
                headers={"Content-Type": "application/scim+json"},
            )
            response.raise_for_status()
        except HTTPError as exc:
            app_logger.debug(f"Cannot add role to user in the identity service due an HTTP Error ({exc})")
            raise IdentityServicePatchError(
                f"Cannot add role to user in the identity service due to HTTP Error ({exc})"
            )
        except ConnectionError as exc:
            app_logger.debug(f"Cannot add role to user in the identity service due a connection error ({exc})")
            raise IdentityServicePatchError(
                f"Cannot add role to user in the identity service due a connection error ({exc})"
            )
        except Timeout as exc:
            app_logger.debug(f"Cannot add role to user in the identity service due a timeout ({exc})")
            raise IdentityServicePatchError(f"Cannot add role to user in the identity service due a timeout ({exc})")
        except Exception as exc:
            app_logger.debug(f"Cannot add role to user in the identity service due an unknown error ({exc})")
            raise IdentityServicePatchError(
                f"Cannot add role to user in the identity service due an unknown error ({exc})"
            )
