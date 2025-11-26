from requests import Session

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from iati_account_web.settings import (
    COUNTRY_CODE_LOOKUP,
    COUNTRY_LIST,
    env,
    CODELIST_ORGANISATION_TYPE_LIST,
    CODELIST_ORGANISATION_TYPE_LOOKUP,
)
from iati_account_web.data.forms import OrganisationDetailsForm


def home(request: HttpRequest) -> HttpResponse:
    """Generates the main landing page for organistions and data.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """
    if not request.user.is_authenticated:
        return redirect("oidc_authentication_init")

    # Get list of reporting orgs for this user from RYD.
    session = Session()
    session.headers["Authorization"] = f"Bearer {request.session["oidc_access_token"]}"
    session.should_strip_auth = lambda old_url, new_url: False
    response = session.get(f"{env("REGISTER_YOUR_DATA_BASE_URL")}/reporting-orgs", allow_redirects=True)

    # Handle the case where the request failed.  This is handled with an alert in the template.
    if response.status_code != 200:
        context = {"ryd_outcome": "failed", "ryd_status_code": response.status_code}
        template = loader.get_template("data/multiple_org_list_ryd_error.html")
        return HttpResponse(template.render(context, request))

    org_list = response.json()["data"]

    if len(org_list) == 0:
        # There were no organisations in the response, so redirect to offer the opportunity to join
        # an organisation.
        return redirect("data:join-reporting-org")

    else:
        # We have organisations in the payload, so show all the organisations, along with a join organisation button.
        context = {"orgs": []}
        for org in org_list:
            org["metadata"]["hq_country"] = COUNTRY_CODE_LOOKUP[org["metadata"]["hq_country"]]
            org["metadata"]["organisation_type"] = CODELIST_ORGANISATION_TYPE_LOOKUP[
                org["metadata"]["organisation_type"]
            ]
            context["orgs"].append({"id": org["id"], **org["metadata"], "user_role": org["user_role"]})
        context["orgs"].sort(key=lambda x: x["human_readable_name"])

    template = loader.get_template("data/multiple_org_list.html")
    return HttpResponse(template.render(context, request))


def join_reporting_org(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("oidc_authentication_init")
    return None


def organisation_detail(request: HttpRequest, oid: str) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("oidc_authenication_init")
    return None
