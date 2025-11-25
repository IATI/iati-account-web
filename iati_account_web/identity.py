import urllib.parse

import oauthlib
import requests_oauthlib
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, reverse
from iati_account_web.account.models import IATIUser
from iati_account_web.settings import IDENTITY_SERVICE_SCIM2_SCOPES, OIDC_RP_CLIENT_ID, env
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


def generate_username(email: str, claims: dict[str, str]) -> str:
    """Generate a username for Django using the claims in the token

    Parameters
    ----------
    email : str
        Email address.
    claims : dict[str, str]
        Dictionary of claims in the token.

    Returns
    -------
    str
        Username to use in Django user database
    """
    return claims["email"]


def logout_uri(request: HttpRequest) -> str:
    """Generate a logout URL for Asgardeo

    Follows the guidance at
    https://wso2.com/asgardeo/docs/guides/authentication/oidc/add-logout/
    which generates a logout URL that causes Asgardeo to then redirect
    to a specific view for us to perform additional logout actions.

    Parameters
    ----------
    request : HttpRequest
        Django request object.

    Returns
    -------
    str
        Formatted URL
    """

    params = urllib.parse.urlencode(
        {
            "client_id": OIDC_RP_CLIENT_ID,
            "post_logout_redirect_uri": urllib.parse.urljoin(env("SERVER_URL_BASE"), reverse("logout")),
        }
    )
    return f"{env("IDENTITY_SERVICE_BASE_URL")}/oidc/logout?" + params


class IATIAccountOIDCAuthBackend(OIDCAuthenticationBackend):  # type: ignore[misc]
    """Custom OIDC authentication backend to verify claims"""

    def verify_claims(self, claims: dict[str, str]) -> bool:
        """Verifies claims

        Parameters
        ----------
        claims : dict[str, str]
            Claims obtained from the identity server.

        Returns
        -------
        bool
            True if the claims are okay.
        """
        if "sub" not in claims:
            return False
        if "username" not in claims:
            return False

        return True

    def create_user(self, claims: dict) -> IATIUser:
        """Create a new user record in Django

        Parameters
        ----------
        claims : dict
            Dictionary of claims received from the Identity Service.

        Returns
        -------
        IATIUser
        """
        user = super(IATIAccountOIDCAuthBackend, self).create_user(claims)
        user.oidc_sub = claims.get("sub", "")
        user.unformatted_name = claims.get("name", "")
        user.email = claims.get("email", "")
        user.inperson_name = claims.get("iatiInPersonName", "")
        user.online_name = claims.get("iatiOnlineName", "")
        user.mailinglist_subscriber = True if claims.get("iatiMailingList", "false").lower() == "true" else False
        user.set_languages(claims.get("iatiPreferredLanguage", ""))
        user.country = claims.get("iatiCountry", "")
        user.timezone = claims.get("iatiTimeZone", "")
        user.set_first_registration_use_cases(claims.get("iatiFirstRegistrationUseCases", ""))
        user.has_been_onboarded = True if claims.get("iatiHasBeenOnboarded", "false").lower() == "true" else False
        user.save()

        return user

    def update_user(self, user, claims: dict) -> IATIUser:
        """Update a user record in Django

        Parameters
        ----------
        claims : dict
            Dictionary of claims received from the Identity Service.

        Returns
        -------
        IATIUser
        """
        user.unformatted_name = claims.get("name", "")
        user.email = claims.get("email", "")
        user.inperson_name = claims.get("iatiInPersonName", "")
        user.online_name = claims.get("iatiOnlineName", "")
        user.mailinglist_subscriber = True if claims.get("iatiMailingList", "false").lower() == "true" else False
        user.set_languages(claims.get("iatiPreferredLanguage", ""))
        user.country = claims.get("iatiCountry", "")
        user.timezone = claims.get("iatiTimeZone", "")
        user.set_first_registration_use_cases(claims.get("iatiFirstRegistrationUseCases", ""))
        user.has_been_onboarded = True if claims.get("iatiHasBeenOnboarded", "false").lower() == "true" else False
        user.save()

        return user


def logout(request: HttpRequest) -> HttpResponseRedirect:
    """View called by Asgardeo on logout so that we can check session is clear.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponseRedirect
    """
    if "oidc_id_token" in request.session:
        del request.session["oidc_id_token"]
    if "oidc_access_token" in request.session:
        del request.session["oidc_access_token"]
    return redirect("/")


def connect_to_identity_service(scope: str = IDENTITY_SERVICE_SCIM2_SCOPES) -> str | None:
    """Connect to and get an access token from the identity service

    Parameters
    ----------
    scope : str, optional
        List of scopes to request from the identity service, default is IDENTITY_SERVICE_SCIM2_SCOPES.

    Returns
    -------
    str | None
        Access token or None.
    """
    # Get an access token from Asgardeo.
    client = oauthlib.oauth2.BackendApplicationClient(
        client_id=env("IDENTITY_SERVICE_CLIENT_ID"),
        scope=scope,
    )
    session = requests_oauthlib.OAuth2Session(client=client)

    access_token = session.fetch_token(
        token_url=env("IDENTITY_SERVICE_BASE_URL") + "oauth2/token",
        client_id=env("IDENTITY_SERVICE_CLIENT_ID"),
        client_secret=env("IDENTITY_SERVICE_CLIENT_SECRET"),
    ).get("access_token", None)

    return {"client": client, "session": session, "access_token": access_token}


def patch_user_in_identity_service(user: IATIUser) -> bool:
    """Patches a user record in the Identity Service

    Parameters
    ----------
    user : IATIUser
        Django user object.

    Returns
    -------
    bool
        True on success, False on failure.
    """

    idp = connect_to_identity_service()
    if idp["access_token"] is None:
        return False

    # Construct patch payload.
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "path": "name",
                "value": {"familyName": user.unformatted_name, "formatted": user.unformatted_name},
            },
            {
                "op": "replace",
                "path": "urn:scim:schemas:extension:custom:User:iatiInPersonName",
                "value": user.inperson_name,
            },
            {
                "op": "replace",
                "path": "urn:scim:schemas:extension:custom:User:iatiOnlineName",
                "value": user.online_name,
            },
            {
                "op": "replace",
                "path": "urn:scim:schemas:extension:custom:User:iatiMailingList",
                "value": "true" if user.mailinglist_subscriber else "false",
            },
            {
                "op": "replace",
                "path": "urn:scim:schemas:extension:custom:User:iatiPreferredLanguage",
                "value": user.languages,
            },
            {"op": "replace", "path": "urn:scim:schemas:extension:custom:User:iatiCountry", "value": user.country},
            {"op": "replace", "path": "urn:scim:schemas:extension:custom:User:iatiTimeZone", "value": user.timezone},
            {
                "op": "replace",
                "path": "urn:scim:schemas:extension:custom:User:iatiHasBeenOnboarded",
                "value": "true" if user.mailinglist_subscriber else "false",
            },
            {
                "op": "replace",
                "path": "urn:scim:schemas:extension:custom:User:iatiHasBeenOnboarded",
                "value": "true" if user.mailinglist_subscriber else "false",
            },
            {
                "op": "replace",
                "path": "urn:scim:schemas:extension:custom:User:iatiFirstRegistrationUseCases",
                "value": user.first_registration_use_cases,
            },
        ],
    }

    # Do the patch operation.
    response = idp["session"].patch(
        env("IDENTITY_SERVICE_BASE_URL") + f"scim2/Users/{user.oidc_sub}",
        json=payload,
        headers={"Content-Type": "application/scim+json"},
    )

    if response.status_code != 200:
        print(response.status_code)
        print(response.content)
        # TODO: add logging
        return False

    return True
