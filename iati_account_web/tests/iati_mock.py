import json
import random
import string
import uuid
from urllib.parse import parse_qs, urlparse

import requests
import responses
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
