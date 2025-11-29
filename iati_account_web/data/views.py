from datetime import datetime

from django.http import HttpRequest, HttpResponse
from django.template import loader
from iati_account_web.data.forms import OrganisationDetailsForm
from iati_account_web.identity import preflight_checks
from iati_account_web.settings import (
    COUNTRY_CODE_LOOKUP,
    COUNTRY_LIST,
    ORGANISATION_TYPE_LOOKUP,
    env,
)
from requests import Session


def home(request: HttpRequest) -> HttpResponse:
    """Generates the main landing page for organistions and data.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """
    preflight = preflight_checks(request)
    if preflight.not_okay_to_continue:
        return preflight.redirect

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
        context = {"orgs": []}
        # return redirect("data:join-reporting-org")

    else:
        # We have organisations in the payload, so show all the organisations, along with a join organisation button.
        context = {"orgs": []}
        for org in org_list:
            org["metadata"]["hq_country"] = COUNTRY_CODE_LOOKUP[org["metadata"]["hq_country"]]
            org["metadata"]["organisation_type"] = ORGANISATION_TYPE_LOOKUP[org["metadata"]["organisation_type"]]
            context["orgs"].append({"id": org["id"], **org["metadata"], "user_role": org["user_role"]})
        context["orgs"].sort(key=lambda x: x["human_readable_name"])

    template = loader.get_template("data/multiple_org_list.html")
    return HttpResponse(template.render(context, request))


def join_reporting_org(request: HttpRequest) -> HttpResponse:

    preflight = preflight_checks(request)
    if preflight.not_okay_to_continue:
        return preflight.redirect

    # Get list of discoverable reporting orgs.  Until the endpoint is running we just
    # substitute a mock list here.
    discoverable_reporting_orgs = [
        {
            "id": "abcd1234-b6df-4143-8895-100ec70877cd",
            "human_readable_name": "Masibekela Group",
            "hq_country": "ZA",
            "organisation_identifier": "ZA-PPE-27669040",
        },
        {
            "id": "abcd1234-ab4e-4667-a6b6-a8424b8fd38d",
            "human_readable_name": "Amundsen BA",
            "hq_country": "NO",
            "organisation_identifier": "NO-BJK-41447156",
        },
    ]
    for org in discoverable_reporting_orgs:
        org["country"] = COUNTRY_CODE_LOOKUP.get(org["hq_country"], "")

    template = loader.get_template("data/join_reporting_org.html")
    context = {
        "discoverable_reporting_orgs": discoverable_reporting_orgs,
        "COUNTRY_LIST": COUNTRY_LIST,
    }
    return HttpResponse(template.render(context, request))


def organisation_detail(request: HttpRequest, oid: str) -> HttpResponse:
    preflight = preflight_checks(request)
    if preflight.not_okay_to_continue:
        return preflight.redirect

    # Try to fetch the organisation from RYD.
    session = Session()
    session.headers["Authorization"] = f"Bearer {request.session["oidc_access_token"]}"
    session.should_strip_auth = lambda old_url, new_url: False
    response = session.get(f"{env("REGISTER_YOUR_DATA_BASE_URL")}/reporting-orgs/{oid}", allow_redirects=True)

    # Handle the case where the request failed.  This is handled with an alert in the template.
    if response.status_code != 200:
        context = {"ryd_outcome": "failed", "ryd_status_code": response.status_code}

    else:
        org = response.json()["data"]
        form = OrganisationDetailsForm(
            initial={
                "short_name": org["metadata"]["short_name"],
                "human_readable_name": org["metadata"]["human_readable_name"],
                "organisation_type": org["metadata"]["organisation_type"],
                "hq_country": org["metadata"]["hq_country"],
                "region": org["metadata"]["region"],
                "contact_email": org["metadata"]["contact_email"],
                "website": org["metadata"]["website"],
                "phone": org["metadata"]["phone"],
                "address": org["metadata"]["address"],
                "description": org["metadata"]["description"],
                "data_portal_url": org["metadata"]["data_portal_url"],
                "exclusions_policy_url": org["metadata"]["exclusions_policy_url"],
                "default_licence_id": org["metadata"]["default_licence_id"],
                "reporting_source_type": org["metadata"]["reporting_source_type"],
                "organisation_identifier": org["metadata"]["organisation_identifier"],
            }
        )

        # Set editability based on user permission.
        if org["user_role"].lower() == "contributor":
            form.fields["human_readable_name"].disabled = True
            form.fields["organisation_type"].disabled = True
            form.fields["hq_country"].disabled = True
            form.fields["region"].disabled = True
            form.fields["contact_email"].disabled = True
            form.fields["website"].disabled = True
            form.fields["phone"].disabled = True
            form.fields["address"].disabled = True
            form.fields["description"].disabled = True
            form.fields["data_portal_url"].disabled = True
            form.fields["exclusions_policy_url"].disabled = True
            form.fields["default_licence_id"].disabled = True
            form.fields["reporting_source_type"].disabled = True

        first_publication_date = ""
        if org["metadata"]["first_publication_date"] != "":
            first_publication_date = datetime.fromisoformat(org["metadata"]["first_publication_date"])

        context = {
            "ryd_outcome": "success",
            "org": {
                "id": org["id"],
                "user_role": org["user_role"],
                "registry_approved": org["metadata"]["registry_approved"],
                "first_publication_date": first_publication_date,
                "number_of_published_datasets": 0,
            },
            "form": form,
            "show_delete_org_button": True if org["user_role"].lower() == "admin" else False,
            "show_org_info_button_box": False if org["user_role"].lower() == "contributor" else True,
        }

    template = loader.get_template("data/org_detail.html")
    return HttpResponse(template.render(context, request))
