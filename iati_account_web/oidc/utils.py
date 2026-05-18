import urllib.parse

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import reverse


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
            "client_id": settings.OIDC_RP_CLIENT_ID,
            "post_logout_redirect_uri": urllib.parse.urljoin(settings.SERVER_URL_BASE, reverse("logout")),
        }
    )
    return urllib.parse.urljoin(settings.IDENTITY_SERVICE_BASE_URL, "oidc/logout?" + params)
