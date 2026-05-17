from django.conf import settings
from iati_account_web.data.models import Dataset, DiscoverableReportingOrganisation, ReportingOrganisation, UserAndRole
from iati_account_web.ryd_handling import RegisterYourDataSession


def parse_user_list_to_objects(users_and_roles: list[dict], oid: str) -> list[UserAndRole]:
    """Parse list of reporting org users into UserAndRole objects

    Parameters
    ----------
    users_and_roles : list[dict]
        List of users and roles from the /reporting-orgs/{oid}/users endpoint.
    oid : str
        Organisation ID

    Returns
    -------
    list[UserAndOrgRole]
    """
    return [
        UserAndRole.from_ryd(role_string=x["role"], name=x["name"], email=x["email"], uid=x["id"], oid=oid)
        for x in users_and_roles
    ]


def parse_org_list_to_objects(
    reporting_orgs: list[dict], uid: str
) -> list[dict[str, ReportingOrganisation | UserAndRole]]:
    """Parse a list of reporting orgs into pairs of ReportingOrganisation and UserandRole objects

    Parameters
    ----------
    reporting_orgs : list[dict]
        List of dictionaries as received from GET /reporting-orgs
    uid : str
        UUID of the user the call was carried out for.

    Returns
    -------
    list[dict[str, ReportingOrganisation | UserAndRole]]
    """
    result = [
        {
            "org": ReportingOrganisation.from_ryd_reporting_organisation(org),
            "user_and_role": UserAndRole.from_ryd(role_string=org["user_role"], uid=uid, oid=org["id"]),
        }
        for org in reporting_orgs
    ]
    result.sort(key=lambda x: x["org"].human_readable_name)
    return result


def parse_discoverable_org_list_to_objects(
    discoverable_reporting_orgs: list[dict], sort_list: bool = False
) -> list[DiscoverableReportingOrganisation]:
    """Parse a list of reporting orgs into pairs of ReportingOrganisation and UserandRole objects

    Parameters
    ----------
    discoverable_reporting_orgs : list[dict]
        List of dictionaries as received from GET /discoverable-reporting-orgs
    sort_list : bool, optional
        If true, the list is sorted by human_readable_name, False by default.

    Returns
    -------
    list[DiscoverableReportingOrganisation]
    """
    result = [DiscoverableReportingOrganisation.from_ryd(x) for x in discoverable_reporting_orgs]
    if sort_list:
        result.sort(key=lambda x: x.human_readable_name)
    return result


def parse_dataset_list_to_objects(datasets: list[dict], sort_list: bool = False) -> list[Dataset]:
    """Parse a list of datasets into Dataset objects

    Parameters
    ----------
    datasets : list[dict]
        List of dataset dictionaries as obtained from RYD.
    sort_list : bool, optional
        If true, the list is sorted by human_readable_name, by default False

    Returns
    -------
    list[Dataset]
    """
    result = [Dataset.from_ryd(x) for x in datasets]
    if sort_list:
        result.sort(key=lambda x: x.human_readable_name)
    return result


def get_all_discoverable_reporting_orgs(session: RegisterYourDataSession) -> list[DiscoverableReportingOrganisation]:
    """Get all the discoverable reporting orgs from RYD

    Parameters
    ----------
    access_token : str

    Returns
    -------
    list[DiscoverableReportingOrganisation]
    """

    page = 1
    orgs = []
    r = {"data": [], "pagination": {"links": {"next": ""}}}
    while r["pagination"]["links"]["next"] is not None:
        r = session.get(
            "/discoverable-reporting-orgs",
            params={"page": page, "page_size": settings.REGISTER_YOUR_DATA_DISCOVERABLE_REPORTING_ORGS_PAGE_SIZE},
        )
        orgs += r["data"]
        page += 1

    return parse_discoverable_org_list_to_objects(orgs)
