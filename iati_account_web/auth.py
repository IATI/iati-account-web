import urllib.parse
from typing import cast

from django.http import HttpRequest
from iati_account_web.settings import OIDC_RP_CLIENT_ID
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
    return claims["username"]


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
        {"client_id": OIDC_RP_CLIENT_ID, "post_logout_redirect_uri": "https://localhost:8000/logout"}
    )
    return "https://api.eu.asgardeo.io/t/iati/oidc/logout?" + params


class IATIAccountOIDCAuthBackend(OIDCAuthenticationBackend):  # type: ignore[misc]
    """Custom OIDC authentication backend to verify claims"""

    def verify_claims(self, claims: dict[str, str]) -> bool:
        """Verifies claims and stores claims into the session

        Parameters
        ----------
        claims : dict[str, str]
            Claims obtained from the identity server.

        Returns
        -------
        bool
            True if the claims are okay.
        """
        verified = super(IATIAccountOIDCAuthBackend, self).verify_claims(claims)
        self.request.session["claims"] = {}
        for claim in claims.keys():
            self.request.session["claims"][claim] = claims[claim]
        return cast(bool, verified)
