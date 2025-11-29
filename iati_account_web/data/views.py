import logging
from datetime import datetime

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from iati_account_web.data.forms import CreateOrganisationForm, JoinOrganisationForm, OrganisationDetailsForm
from iati_account_web.helpers import preflight_checks
from iati_account_web.settings import (
    COUNTRY_CODE_LOOKUP,
    COUNTRY_LIST,
    ORGANISATION_TYPE_LOOKUP,
    env,
)
from requests import Session

iati_account_logger = logging.getLogger("iati_account")


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
        USER_ROLES = {
            "admin": "Admin",
            "editor": "Editor",
            "contributor": "Contributor",
            "contributor_pending": "Contributor (Pending)",
        }
        for org in org_list:
            org["metadata"]["hq_country"] = COUNTRY_CODE_LOOKUP[org["metadata"]["hq_country"]]
            org["metadata"]["organisation_type"] = ORGANISATION_TYPE_LOOKUP[
                org["metadata"].get("organisation_type", "")
            ]
            context["orgs"].append(
                {
                    "id": org["id"],
                    **org["metadata"],
                    "user_role": org["user_role"],
                    "user_role_label": USER_ROLES[org["user_role"]],
                }
            )
        context["orgs"].sort(key=lambda x: x["human_readable_name"])

    template = loader.get_template("data/multiple_org_list.html")
    return HttpResponse(template.render(context, request))


def join_reporting_org(request: HttpRequest) -> HttpResponse:

    preflight = preflight_checks(request)
    if preflight.not_okay_to_continue:
        return preflight.redirect

    if request.method == "POST":
        form = JoinOrganisationForm(request.POST)
        if form.is_valid():
            session = Session()
            session.headers["Authorization"] = f"Bearer {request.session["oidc_access_token"]}"
            session.should_strip_auth = lambda old_url, new_url: False
            iati_account_logger.debug(
                f"Trying to add user {request.user.registry_id} to organisation {str(form.cleaned_data["org_id"])}"
            )
            response = session.post(
                f"{env("REGISTER_YOUR_DATA_BASE_URL")}/users/{request.user.registry_id}/reporting-org",
                allow_redirects=True,
                json={"oid": str(form.cleaned_data["org_id"])},
            )
            return redirect("data:home")
        else:
            # TODO: handle form errors
            pass
    else:
        # Get list of reporting orgs for this user, and the list of discoverable reporting orgs from RYD.
        session = Session()
        session.headers["Authorization"] = f"Bearer {request.session["oidc_access_token"]}"
        session.should_strip_auth = lambda old_url, new_url: False
        response = session.get(f"{env("REGISTER_YOUR_DATA_BASE_URL")}/reporting-orgs", allow_redirects=True)
        user_org_ids = [org.get("id", "") for org in response.json()["data"]]

        # Handle the case where the request failed.  This is handled with an alert in the template.
        if response.status_code != 200:
            pass
            # TODO: handle error

        response = session.get(
            f"{env("REGISTER_YOUR_DATA_BASE_URL")}/discoverable-reporting-orgs", allow_redirects=True
        )
        # Handle the case where the request failed.  This is handled with an alert in the template.
        if response.status_code != 200:
            pass
            # TODO: handle error

        # Get list of discoverable reporting orgs.  Until the endpoint is running we just
        # substitute a mock list here.
        #        discoverable_reporting_orgs = response.json()["data"]
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

        # Remove user's organisations from the list.
        discoverable_reporting_orgs = list(
            filter(lambda org: org["id"] not in user_org_ids, discoverable_reporting_orgs)
        )

        form = JoinOrganisationForm()
        template = loader.get_template("data/join_reporting_org.html")
        context = {
            "discoverable_reporting_orgs": discoverable_reporting_orgs,
            "COUNTRY_LIST": COUNTRY_LIST,
            "form": form,
        }
        return HttpResponse(template.render(context, request))


def organisation_detail(request: HttpRequest, oid: str) -> HttpResponse:  # noqa: C901
    preflight = preflight_checks(request)
    if preflight.not_okay_to_continue:
        return preflight.redirect

    session = Session()
    session.headers["Authorization"] = f"Bearer {request.session["oidc_access_token"]}"
    session.should_strip_auth = lambda old_url, new_url: False

    context = {"errors": []}
    have_form = False

    # Handle form submission.
    if request.method == "POST":
        form = OrganisationDetailsForm(request.POST)
        have_form = True
        iati_account_logger.debug(f"Updating organisation {oid}; form validation result {form.is_valid()}")
        if form.is_valid():
            response = session.patch(
                f"{env("REGISTER_YOUR_DATA_BASE_URL")}/reporting-orgs/{oid}",
                allow_redirects=True,
                json=form.get_ryd_patch_payload_from_cleaned_data(),
            )
            iati_account_logger.debug(f"response from updating organisation {response.status_code}")
            if response.status_code != 200:
                context["errors"].append(
                    {
                        "title": "Could not save changes to organisations",
                        "message": "There was an error in saving your changes to the organisation. "
                        "Please try again later, and if the error persists please contact IATI Support",
                    }
                )

        else:
            context["errors"].append(
                {
                    "title": "There was an error in your form",
                    "message": "There was an error in saving your changes to the organisation.",
                }
            )

    # Here we need to load the organisation and build a form if necessary.
    response = session.get(f"{env("REGISTER_YOUR_DATA_BASE_URL")}/reporting-orgs/{oid}", allow_redirects=True)

    if response.status_code != 200:
        if response.status_code == 404:
            context["errors"].append(
                {
                    "title": "The organisation could not be found",
                    "message": "There was an error in loading this organisation. Please try again "
                    "later, and if the error persists please contact IATI Support.",
                }
            )
        elif response.status_code in (401, 403):
            context["errors"].append(
                {
                    "title": "No authorisation",
                    "message": "You are not authorised to view this organisation. If you believe this "
                    "is an error then please contact IATI Support.",
                }
            )
        elif response.status_code != 200:
            context["errors"].append(
                {
                    "title": "There was a problem loading the organisation",
                    "message": "There was an error in loading this organisation. Please try again later, "
                    "and if the error persists please contact IATI Support.",
                }
            )
        template = loader.get_template("data/org_detail_no_data.html")
        return HttpResponse(template.render(context, request))

    org = response.json()["data"]
    first_publication_date = ""
    if org["metadata"]["first_publication_date"] != "":
        first_publication_date = datetime.fromisoformat(org["metadata"]["first_publication_date"])

    if not have_form:
        form = OrganisationDetailsForm(
            initial={
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

    context["org"] = {
        "id": org["id"],
        "user_role": org["user_role"],
        "registry_approved": org["metadata"]["registry_approved"],
        "first_publication_date": first_publication_date,
        "number_of_published_datasets": 0,
        "organisation_identifier": org["metadata"]["organisation_identifier"],
        "short_name": org["metadata"]["short_name"],
    }
    context["form"] = form
    context["show_delete_org_button"] = True if org["user_role"].lower() == "admin" else False
    context["show_org_info_button_box"] = False if org["user_role"].lower() == "contributor" else True

    template = loader.get_template("data/org_detail.html")
    return HttpResponse(template.render(context, request))


def create_organisation(request: HttpRequest) -> HttpResponse:
    """Generates the create organisation page and handles creation on form submission

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

    context = {"errors": [], "form": None}

    if request.method == "POST":
        # Handle form submission - create and validate the form from the POST request.
        form = CreateOrganisationForm(request.POST)
        context["form"] = form
        iati_account_logger.debug(f"Creating organisation; form validation result {form.is_valid()}")
        if form.is_valid():

            # Form is valid so make the request to RYD to create the organisation.
            session = Session()
            session.headers["Authorization"] = f"Bearer {request.session["oidc_access_token"]}"
            session.should_strip_auth = lambda old_url, new_url: False
            response = session.post(
                f"{env("REGISTER_YOUR_DATA_BASE_URL")}/reporting-orgs",
                allow_redirects=True,
                json=form.get_ryd_patch_payload_from_cleaned_data(),
            )
            iati_account_logger.debug(f"Creating organisation; api_status={response.status_code}")

            if response.status_code != 200:
                # TODO: handle error
                pass

            # Organisation created okay, so go to org detail page for the new organisation.
            redirect("data:org-detail", oid=response.json()["data"]["id"])

        else:
            # Highlight to the user that there are form errors.
            context["errors"].append(
                {
                    "title": "There was an error in your form",
                    "message": "There was an error in saving your changes to the organisation.",
                }
            )

    if context["form"] is None:
        context["form"] = CreateOrganisationForm()
    template = loader.get_template("data/create_org.html")
    return HttpResponse(template.render(context, request))
