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
