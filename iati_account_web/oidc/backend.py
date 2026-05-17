from iati_account_web.account.models import IATIUser
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


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
