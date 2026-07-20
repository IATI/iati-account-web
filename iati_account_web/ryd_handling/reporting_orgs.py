import logging
import uuid
from dataclasses import dataclass

from django.conf import settings
from iati_account_web.data.models import (
    Dataset,
    DiscoverableReportingOrganisation,
    ReportingOrganisation,
    Tool,
    UserAndRole,
)
from iati_account_web.ryd_handling import RegisterYourDataSession
from iati_account_web.typing import AuthedHttpRequest

audit_logger = logging.getLogger("audit")


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


def parse_tool_list_to_objects(tools: list[dict], sort_list: bool = False) -> list[Tool]:
    """Parse a list of tools into Tool objects

    Parameters
    ----------
    tools : list[dict]
        List of tool dictionaries as obtained from RYD.
    sort_list : bool, optional
        If true, the list is sorted by name, by default False

    Returns
    -------
    list[Tool]
    """
    result = [Tool.from_ryd(x) for x in tools]
    if sort_list:
        result.sort(key=lambda x: x.name)
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


@dataclass
class OrgDetail:
    """Everything the organisation detail page needs from RYD, fetched once.

    Attributes
    ----------
    reporting_org : ReportingOrganisation
    this_user : UserAndRole
        The requesting user's role within the organisation.
    users_data : list[dict]
        Raw user records from RYD (used to seed the user formset).
    authorised_tools : list[Tool]
        Tools currently authorised for the organisation.
    addable_tools : list[Tool]
        Catalogue tools not yet authorised (offered in the "authorise" dropdown).
    """

    reporting_org: ReportingOrganisation
    current_user: UserAndRole
    users_and_roles: dict[uuid.UUID, UserAndRole]
    authorised_tools: list[Tool]
    authorised_tools_by_id: dict[uuid.UUID, Tool]
    addable_tools: list[Tool]


def get_org_detail(
    request: AuthedHttpRequest, session: RegisterYourDataSession, oid: str, registry_id: str
) -> OrgDetail:
    """Fetch and parse everything the organisation detail page needs from RYD.

    Performs the four reads the page depends on and parses them into model objects,
    so a caller fetches this data once per request and reuses it -- e.g. a POST
    handler that validates a form against it and then re-renders the page on error.

    Parameters
    ----------
    request : AuthedHttpRequest
    session : RegisterYourDataSession
    oid : str
        Organisation UUID.
    registry_id : str
        RYD registry id of the requesting user (used to build this_user).

    Returns
    -------
    OrgDetail
    """
    try:
        org_basic_data = session.get(f"/reporting-orgs/{oid}").get("data", {})
        org_users_data = session.get(f"/reporting-orgs/{oid}/users").get("data", [])
        org_authorised_tools_data = session.get(f"/reporting-orgs/{oid}/tools").get("data", [])
        all_tools_data = session.get("/tools").get("data", [])
    except Exception as exc:
        audit_logger.error(
            f"Could not access RYD for user {request.user.log_label} "
            f"trying to load reporting org {oid} with error {exc}"
        )
        raise exc

    reporting_org = ReportingOrganisation.from_ryd_reporting_organisation(org_basic_data)

    current_user = UserAndRole.from_ryd(org_basic_data["user_role"], registry_id, org_basic_data["id"], None, None)

    authorised_tools = parse_tool_list_to_objects(org_authorised_tools_data)

    all_tools = parse_tool_list_to_objects(all_tools_data)

    authorised_tools_by_id = {t.tool_id: t for t in authorised_tools}

    addable_tools = [tool for tool in all_tools if tool.tool_id not in authorised_tools_by_id]

    users_and_roles = {
        uuid.UUID(x.uid): UserAndRole.from_ryd(role_string=x.role, uid=x.uid, oid=x.oid, name=x.name, email=x.email)
        for x in parse_user_list_to_objects(org_users_data, reporting_org.oid)
    }

    return OrgDetail(
        reporting_org=reporting_org,
        current_user=current_user,
        users_and_roles=users_and_roles,
        authorised_tools=authorised_tools,
        authorised_tools_by_id=authorised_tools_by_id,
        addable_tools=addable_tools,
    )
