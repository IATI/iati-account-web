from iati_account_web.data.models import DiscoverableReportingOrganisation, ReportingOrganisation, UserAndRole


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
