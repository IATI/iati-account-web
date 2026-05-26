import urllib.parse

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import reverse
from iati_account_web.account.models import IATIUser
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
            "client_id": settings.OIDC_RP_CLIENT_ID,
            "post_logout_redirect_uri": urllib.parse.urljoin(settings.SERVER_URL_BASE, reverse("logout")),
        }
    )
    return f"{settings.IDENTITY_SERVICE_BASE_URL}/oidc/logout?" + params


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
        user.update_from_claims(claims, include_sub=True)
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
        user.update_from_claims(claims)
        user.save()

        return user
