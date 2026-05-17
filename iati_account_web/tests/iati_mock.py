import json
import random
import string
import time
import uuid
from urllib.parse import parse_qs, urlparse

import requests
import responses
from django.conf import settings
from iati_account_web.account.models import IATIUser
from iati_account_web.settings import COUNTRY_CODE_LOOKUP


class IatiInfrastructureMock:
    """Class containing a mock of the IATI infrastructure used by IATI Account

    This class replaces some of the earlier mocking done through Mockoon so
    that it's more tightly connected to the actual test cases, is more easily
    dynamic/integrated together (e.g., CRM and RYD), and reduces testing
    infrastructure.
    """

    RYD_BASE_URL = "https://testing.ryd/api/v1"
    CRM_BASE_URL = "https://testing.crm/"
    IDP_BASE_URL = "https://testing.idp/t/test"

    def __init__(self, num_discoverable_reporting_orgs: int = 2000) -> None:
        """Initialiser

        Parameters
        ----------
        num_discoverable_reporting_orgs : int, optional
            Number of discoverable reporting orgs generated at the start, by default 2000.
        """
        self._num_discoverable_reporting_orgs = num_discoverable_reporting_orgs
        self._discoverable_reporting_orgs = []

        self._generate_discoverable_reporting_orgs()

    def register_all(self) -> None:
        """Register all the callbacks in this infrastructure mock"""
        self.register_ryd_callbacks()

    def register_ryd_callbacks(self) -> None:
        """Register all the Register Your Data callbacks in this infrastructure mock"""
        responses.add_callback(
            responses.GET,
            f"{self.RYD_BASE_URL}/discoverable-reporting-orgs",
            callback=self._get_discoverable_reporting_orgs_callback,
            content_type="application/json",
        )

    def _generate_discoverable_reporting_orgs(self) -> None:
        """Generate a random set of discoverable reporting orgs"""
        rnd = random.Random()  # nosec B311

        country_codes = list(COUNTRY_CODE_LOOKUP.keys())
        country_codes.remove("")

        for x in range(self._num_discoverable_reporting_orgs):
            rnd.seed(x)
            country_code = rnd.choices(country_codes)[0]
            org_id = "-".join(
                [
                    country_code,
                    "".join(rnd.choices(string.ascii_uppercase, k=3)),
                    "".join(rnd.choices(string.digits, k=6)),
                ]
            )
            self._discoverable_reporting_orgs.append(
                {
                    "id": str(uuid.UUID(int=rnd.getrandbits(128), version=4)),
                    "metadata": {
                        "human_readable_name": f"Aid Agency {x}",
                        "hq_country": country_code,
                        "organisation_identifier": org_id,
                        "region": "",
                        "short_name": f"aidagy{x}",
                        "website": f"https://www.example.org/{x}/",
                    },
                }
            )

    def _get_discoverable_reporting_orgs_callback(self, request: requests.Request) -> tuple[int, dict, str]:
        """Handle discoverable reporting orgs calls

        Parameters
        ----------
        request : requests.Request

        Returns
        -------
        tuple[int, dict, str]
            The tuple contains (HTTP status code, headers, content)
        """

        query_params = parse_qs(urlparse(request.url).query)
        page = int(query_params.get("page", 1)[0])
        page_size = int(query_params.get("page_size", 10)[0])

        data = {
            "status": "success",
            "error": None,
            "data": self._discoverable_reporting_orgs[(page - 1) * page_size : (page) * page_size],
            "pagination": _generate_pagination(
                page,
                page_size,
                self._num_discoverable_reporting_orgs,
                f"{self.RYD_BASE_URL}/discoverable-reporting-orgs",
            ),
        }

        return (200, {}, json.dumps(data))


def _generate_pagination(page: int, page_size: int, total_records: int, url: str) -> dict:
    """Generate a pagination dict for Register Your Data paginated responses

    Parameters
    ----------
    page : int
        Page number
    page_size : int
        Page size
    total_records : int
        Number of records available
    url : str
        URL for the endpoint (used to generate links)

    Returns
    -------
    dict
    """
    total_pages = max(1, -(-total_records // page_size))
    pagination = {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_records": total_records,
        "links": {
            "first": f"{url}?page=1&page_size={page_size}",
            "last": f"{url}?page={total_pages}&page_size={page_size}",
            "next": None,
            "prev": None,
        },
    }

    if page != total_pages:
        pagination["links"]["next"] = f"{url}?page={page+1}&page_size={page_size}"

    if page != 1:
        pagination["links"]["prev"] = f"{url}?page={page-1}&page_size={page_size}"

    return pagination


class ForceIatiLoginMixin:
    """Mixin to provide forced IATI OIDC login for Django test cases

    This mixin provides functionality to force login / perform session
    manipulation for a Django TestCase to make it seem like a user has
    logged in using OIDC via mozilla-django-oidc.  It creates an IATIUser
    from a set of mocked claims, adds it to the Django database,
    logins in the user to the Client, and then manipulates the session
    so that SessionMiddleware will accept the login.

    No functionality has yet been added to properly fake tokens (e.g.,
    to send to the Register Your Data endpoints in IatiInfrastructureMock)
    or set nonce/state values.
    """

    iati_oidc_claims = None
    iati_oidc_access_token = "FAKED_ACCESS_TOKEN"  # nosec B105
    iati_oidc_id_token = "FAKED_ID_TOKEN"  # nosec B105
    iati_oidc_state = "FAKED_STATE"
    iati_oidc_nonce = "FAKED_NONCE"
    user = None

    def create_iati_user_claims(
        self,
        unformatted_name: str = "Unit Test User",
        email: str = "unittestuser@iatistandard.org",
        has_been_onboarded: bool = True,
        has_been_provisioned: bool = True,
        has_ryd_role: bool = True,
        iati_superadmin: bool = False,
        exp_delta: int = 600,
        registry_id: str = "",
    ) -> None:
        """Generates a set of mock user claims

        Parameters
        ----------
        unformatted_name : str, optional
            Unformatted name, by default "Unit Test User"
        email : str, optional
            Email address, by default "unittestuser@iatistandard.org"
        has_been_onboarded : bool, optional
            Has been onboarded into IATI, by default True
        has_been_provisioned : bool, optional
            User account has been provisioned, by default True
        has_ryd_role : bool, optional
            User has the IATI role to enable access to RYD, by default True
        iati_superadmin : bool, optional
            User has a superadmin role, by default False
        exp_delta : int, optional
            Offset for expiry of a related access/id token, by default 600 seconds
        registry_id : str, optional
            UUID for a matching RYD person record, by default ""

        Returns
        -------
        dict[str, str | int | bool]
            Dictionary of claims
        """
        now = int(time.time())
        self.iati_oidc_claims = {
            "sub": str(uuid.uuid4()),
            "name": unformatted_name,
            "email": email,
            "iatiRegistryId": registry_id,
            "iatiHasBeenOnboarded": "true" if has_been_onboarded else "false",
            "iatiHasBeenProvisioned": "true" if has_been_provisioned else "false",
            "roles": [],
            "exp": now + exp_delta,
            "iat": now,
        }
        if has_ryd_role:
            self.iati_oidc_claims["roles"].append("Internal/iati_register_your_data")
        if iati_superadmin:
            self.iati_oidc_claims["roles"].append("Internal/iati_superadmin")

    def create_user(self, **kwargs):
        """Create a user object and add to Django

        If claims have not already been created manually, this method will
        generate them using create_iati_user_claims and for convenience will pass
        any keyword arguments to this method.
        """
        if self.iati_oidc_claims is None:
            self.create_iati_user_claims(**kwargs)
        self.user = IATIUser.objects.create_user(
            username=self.iati_oidc_claims["email"], email=self.iati_oidc_claims["email"]
        )
        self.user.update_from_claims(self.iati_oidc_claims, include_sub=True)
        self.user.save()

    def force_oidc_login(self):
        """Force login by directly manipulating the session state

        If no user or claims have been setup, these will be automatically
        initialised by calling create_iati_user_claims() and create_user().
        """
        if self.user is None:
            self.create_user()
        self.client.force_login(self.user, backend=settings.AUTHENTICATION_BACKENDS[0])
        session = self.client.session
        session["oidc_id_token"] = self.iati_oidc_id_token
        session["oidc_id_token_expiration"] = self.iati_oidc_claims["exp"]
        session["oidc_access_token"] = self.iati_oidc_access_token
        session["oidc_state"] = self.iati_oidc_state
        session["oidc_nonce"] = self.iati_oidc_nonce
        session.save()
