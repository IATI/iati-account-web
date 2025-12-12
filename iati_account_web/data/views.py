import logging
from datetime import datetime, timezone
from uuid import UUID

from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from iati_account_web.data.forms import (
    CreateDatasetForm,
    CreateOrganisationForm,
    DatasetDeleteForm,
    DatasetDetailsForm,
    JoinOrganisationForm,
    OrganisationDeleteForm,
    OrganisationDetailsForm,
    OrgUserFormSet,
)
from iati_account_web.data.models import Dataset, ReportingOrganisation, UserAndRole
from iati_account_web.exceptions import RegisterYourDataFieldValidationError, RegisterYourDataRecordAlreadyExists
from iati_account_web.helpers import preflight_checks
from iati_account_web.ryd_handling import RegisterYourDataSession, parse_pagination_links
from iati_account_web.ryd_handling.reporting_orgs import (
    parse_dataset_list_to_objects,
    parse_discoverable_org_list_to_objects,
    parse_org_list_to_objects,
)

audit_logger = logging.getLogger("audit")
app_logger = logging.getLogger("iati_account")


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
    if not preflight.okay_to_continue:
        return preflight.redirect

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)
    try:
        response_json = session.get("/reporting-orgs")
        org_list = parse_org_list_to_objects(response_json["data"], request.user.oidc_sub)
    except Exception as exc:
        audit_logger.error(f"Could not access RYD for user {request.user.oidc_sub} with error {exc}")
        raise exc

    context = {"orgs": org_list}
    template = loader.get_template("data/multiple_org_list.html")
    return HttpResponse(template.render(context, request))


def join_reporting_org(request: HttpRequest) -> HttpResponse:  # noqa: C901
    """Generate the join organisation page.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """

    preflight = preflight_checks(request)
    if not preflight.okay_to_continue:
        return preflight.redirect

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    if request.method == "POST":
        # Handle the form submission.  We check the form and then call RYD assuming everything
        # was okay.  After this we return the user to the data home page.  If the form was invalid
        # (which it shouldn't be) then we raise an exception.
        form = JoinOrganisationForm(request.POST)
        if form.is_valid():

            audit_logger.info(
                f"Trying to add user {request.user.log_label} to organisation {str(form.cleaned_data["org_id"])}"
            )
            try:
                response_json = session.post(
                    f"/users/{request.user.registry_id}/reporting-org", json={"oid": str(form.cleaned_data["org_id"])}
                )
            except Exception as exc:
                audit_logger.error(
                    f"Could not add user {request.user.log_label} with error {exc} "
                    f"to organisation {str(form.cleaned_data["org_id"])}"
                )
                raise exc

            return redirect("data:home")
        else:
            audit_logger.error(f"Form error when trying to add user {request.user.log_label} to an organisation")
            raise ValueError("Join organisation form validation error")

    else:
        # Get list of reporting orgs for this user, and the list of discoverable reporting orgs from RYD.
        try:
            response_json = session.get("/reporting-orgs")
            user_org_ids = [org.get("id", "") for org in response_json["data"]]

            response_json = session.get("/discoverable-reporting-orgs")
            discoverable_reporting_orgs = parse_discoverable_org_list_to_objects(response_json["data"])
        except Exception as exc:
            audit_logger.error(f"Could not access RYD for user {request.user.oidc_sub} with error {exc}")
            raise exc

        # Remove user's organisations from the list.
        discoverable_reporting_orgs = list(
            filter(lambda org: org.oid not in user_org_ids, discoverable_reporting_orgs)
        )

        # Generate the page.
        form = JoinOrganisationForm()
        template = loader.get_template("data/join_reporting_org.html")
        context = {
            "discoverable_reporting_orgs": discoverable_reporting_orgs,
            "form": form,
        }
        return HttpResponse(template.render(context, request))


def organisation_detail(request: HttpRequest, oid: str) -> HttpResponse:  # noqa: C901
    """Generate the organisation detail page.

    Parameters
    ----------
    request : HttpRequest
        Request
    oid : str
        Organisation UUID.

    Returns
    -------
    HttpResponse
    """
    preflight = preflight_checks(request)
    if not preflight.okay_to_continue:
        return preflight.redirect

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    # Fetch the data from RYD for each request, POST or otherwise.  This is done
    # so that fields are loaded from the API, rather than being passed around in
    # POST requests to protect against penetration attacks.
    try:
        reporting_org_data = session.get(f"/reporting-orgs/{oid}").get("data", {})
        reporting_org_user_data = session.get(f"/reporting-orgs/{oid}/users").get("data", {})
    except Exception as exc:
        audit_logger.error(
            f"Could not access RYD for user {request.user.log_label} "
            f"trying to load reporting org {oid} with error {exc}"
        )
        raise exc

    # Parse the reporting org response from RYD into two model objects.
    reporting_org = ReportingOrganisation.from_ryd_reporting_organisation(reporting_org_data)
    this_user = UserAndRole.from_ryd(
        reporting_org_data["user_role"], request.user.registry_id, reporting_org_data["id"], None, None
    )

    # Parse user data into a set of UserAndRole objects.
    users_and_roles = {
        UUID(x["id"]): UserAndRole.from_ryd(
            role_string=x["role"], uid=x["id"], oid=oid, name=x["name"], email=["email"]
        )
        for x in reporting_org_user_data
    }

    # Build and organisation delete form that is used for organisation delete
    # confirmations.
    delete_org_form = OrganisationDeleteForm(
        {"oid": reporting_org.oid, "human_readable_name": reporting_org.human_readable_name}
    )

    # Handle form submission.  We can receive submissions from either the organisation
    # change form, or the user role form.
    form = None
    user_formset = None
    if request.POST:

        if "saveOrgChanges" in request.POST:
            # The organisation details form was submitted.  Build the form and
            # validate it.  If it is valid we make the changes via RYD, otherwise
            # suitable messages are generated.
            form = OrganisationDetailsForm(request.POST, instance=reporting_org)
            app_logger.debug(f"Updating organisation {oid}; form validation result {form.is_valid()}")
            if form.is_valid():
                try:
                    session.patch(f"/reporting-orgs/{oid}", json=form.get_ryd_patch_payload_from_cleaned_data())
                    audit_logger.info(
                        f"User {request.user.log_label} changed fields {form.changed_data} in organisation {oid}"
                    )
                    messages.add_message(request, messages.SUCCESS, "Your changes were saved successfully.")
                except Exception as exc:
                    audit_logger.error(
                        f"Could not patch organisation {oid} in RYD for user {request.user.log_label} with error {exc}"
                    )
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "There was an error in saving your changes.  Please try again "
                        "later, and if the error persists please contact IATI Support.",
                    )
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was an error in saving your changes.  Please correct the errors below and try again.",
                )

        elif "saveUserChanges" in request.POST:
            # The save user changes form was submitted.  We build and validate the formset, and
            # if the formset is valid we do a manual check to see which roles have changed and
            # update each of them in turn.  If there is an error at any of the RYD calls, we
            # refetch the list (to show the saved roles in RYD) and generate the page with an
            # error for the user to then take corrective action.  Any integrity errors are
            # flagged as SuspiciousOperation (even though it may be due to simultaneous changes
            # elsewhere, or an attempted attack).  We ignore any users that are in the response
            # from RYD but not in the form as this could occur in normal operation.
            user_formset = OrgUserFormSet(
                request.POST,
                initial=[
                    {
                        "uid": x["id"],
                        "name": x["name"],
                        "email": x["email"],
                        "role": x["role"],
                        "oid": reporting_org.oid,
                    }
                    for x in reporting_org_user_data
                ],
            )

            app_logger.debug(f"Updating organisation {oid} users; form validation result {user_formset.is_valid()}")
            if user_formset.is_valid():
                user_removed = False
                for user_form in user_formset:
                    form_uid = user_form.cleaned_data["uid"]

                    if form_uid not in users_and_roles.keys():
                        audit_logger.error(
                            f"User {request.user.log_label} has tried to change the role "
                            f"for user {form_uid} but they are not in the reporting org "
                            "from RYD"
                        )
                        raise SuspiciousOperation

                    if user_form.cleaned_data["DELETE"]:
                        try:
                            session.delete(
                                f"/users/{form_uid}/reporting-org/{oid}", json={"role": user_form.cleaned_data["role"]}
                            )
                            audit_logger.info(
                                f"User {request.user.log_label} removed user {form_uid} from organisation {oid}"
                            )
                            messages.add_message(
                                request,
                                messages.SUCCESS,
                                f"{users_and_roles[form_uid].name} was successfully removed from this organisation.",
                            )
                            user_removed = True
                        except Exception as exc:
                            audit_logger.error(
                                f"Could not fulfill request from {request.user.log_label} to remove "
                                f"user {form_uid} from organisation {oid} with error {exc}"
                            )
                            messages.add_message(
                                request,
                                messages.ERROR,
                                f"There was an error in removing {users_and_roles[form_uid].name} "
                                "from this organisation.  Please try again later, and if the error "
                                "persists please contact IATI Support.",
                            )
                    elif users_and_roles[form_uid].role != user_form.cleaned_data["role"]:
                        if user_form.cleaned_data["role"] not in ("admin", "editor", "contributor"):
                            messages.add_message(
                                request,
                                messages.ERROR(
                                    "You can only change the user roles to Admin, Editor or "
                                    f"Contributor, not {user_form.cleaned_data["role"]}"
                                ),
                            )
                        else:
                            try:
                                session.put(
                                    f"/users/{form_uid}/reporting-org/{oid}",
                                    json={"role": user_form.cleaned_data["role"]},
                                )
                                audit_logger.info(
                                    f"User {request.user.log_label} changed user role for "
                                    f"user {form_uid} in organisation {oid} from "
                                    f"{users_and_roles[form_uid].role} to "
                                    f"{user_form.cleaned_data["role"]}"
                                )
                                messages.add_message(
                                    request,
                                    messages.SUCCESS,
                                    f"Your changes for {users_and_roles[form_uid].name} were saved successfully.",
                                )
                            except Exception as exc:
                                audit_logger.error(
                                    f"Could not change user role in request by {request.user.log_label} "
                                    f"to change user role for user {form_uid} in organisation {oid} from "
                                    f"{users_and_roles[form_uid].role} to "
                                    f"{user_form.cleaned_data["role"]} with error {exc}"
                                )
                                messages.add_message(
                                    request,
                                    messages.ERROR,
                                    "There was an error in saving your changes for "
                                    f"{users_and_roles[form_uid].name}.  Please try again later, and "
                                    "if the error persists please contact IATI Support.",
                                )

                # All the user changes have been made, if we deleted a user the redirect back to
                # this view to refresh the formset.
                if user_removed:
                    return redirect("data:reporting-org-detail", oid=oid)

            else:
                raise SuspiciousOperation("User formset for changing user roles in an organisation is invalid")
        else:
            audit_logger.error("Could not tell which form was submitted")
            raise SuspiciousOperation

    if form is None:
        form = OrganisationDetailsForm(instance=reporting_org)
    if user_formset is None:
        user_formset = OrgUserFormSet(
            initial=[
                {"uid": x["id"], "name": x["name"], "email": x["email"], "role": x["role"], "oid": reporting_org.oid}
                for x in reporting_org_user_data
            ],
        )

    # Here we have an organisation change form and we need to set the editability
    # of certain fields depending on the user role.
    if this_user.role == "contributor":
        form.fields["address"].disabled = True
        form.fields["contact_email"].disabled = True
        form.fields["data_portal_url"].disabled = True
        form.fields["default_licence_id"].disabled = True
        form.fields["description"].disabled = True
        form.fields["exclusions_policy_url"].disabled = True
        form.fields["fax"].disabled = True
        form.fields["hq_country"].disabled = True
        form.fields["human_readable_name"].disabled = True
        form.fields["organisation_type"].disabled = True
        form.fields["phone"].disabled = True
        form.fields["region"].disabled = True
        form.fields["reporting_source_type"].disabled = True
        form.fields["website"].disabled = True

    # Build the context and then render the page.
    context = {
        "org_form": form,
        "user_formset": user_formset,
        "org": reporting_org,
        "this_user": this_user,
        "show_delete_org_button": True if this_user.role == "admin" else False,
        "show_org_info_button_box": False if this_user.role == "contributor" else True,
        "delete_form": delete_org_form,
    }
    template = loader.get_template("data/org_detail.html")
    return HttpResponse(template.render(context, request))


def create_organisation(request: HttpRequest) -> HttpResponse:  # noqa: C901
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

    form = None

    if request.method == "POST":
        form = CreateOrganisationForm(request.POST)
        app_logger.debug(f"Creating organisation; form validation result {form.is_valid()}")
        if form.is_valid():
            session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)
            try:
                result = session.post(
                    "/reporting-orgs",
                    json=form.get_ryd_post_payload_from_cleaned_data(),
                )
                messages.add_message(request, messages.SUCCESS, "Reporting organisation created    successfully.")
                return redirect("data:reporting-org-detail", oid=result["data"]["id"])
            except RegisterYourDataRecordAlreadyExists:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "An organisation already exists in the registry with the same short name. "
                    "Please try a different short name and try again.",
                )
                form.add_error("short_name", "Already exists in the registry")
            except RegisterYourDataFieldValidationError as exc:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem in creating your new organisation.  Please correct the "
                    "errors below and try again.",
                )
                if "short_name" in str(exc):
                    form.add_error(
                        "short_name",
                        "Short names should only contain alphanumeric characters, hyphens, or underscores.",
                    )
                else:
                    audit_logger.error(
                        f"Could not create reporting org in RYD for user {request.user.log_label} with error {exc}"
                    )
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "There was a problem in creating your new organisation.  Please try again "
                        "later, or if the problem persists, please contact IATI Support.",
                    )
                    raise exc
            except Exception as exc:
                audit_logger.error(
                    f"Could not create reporting org in RYD for user {request.user.log_label} with error {exc}"
                )
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem in creating your new organisation.  Please try again "
                    "later, or if the problem persists, please contact IATI Support.",
                )
        else:
            messages.add_message(
                request,
                messages.WARNING,
                "There was a problem in creating your new organisation.  Please correct the "
                "errors below and try again.",
            )

    context = {"form": form if form else CreateOrganisationForm()}
    template = loader.get_template("data/create_org.html")
    return HttpResponse(template.render(context, request))


def organisation_delete(request: HttpRequest, oid: str) -> HttpResponse:  # noqa: C901
    """Respond to a user's request to delete an organisation.

    Parameters
    ----------
    request : HttpRequest
        Request object.
    oid : str
        Organisation UUID for the organisation to delete.

    Returns
    -------
    HttpResponse

    Raises
    ------
    SuspiciousOperation
    """

    # Do a small pre-flight check, as we need to check that the user is provisioned and
    # authenticated.
    preflight = preflight_checks(request, check_onboarding=False)
    if not preflight.okay_to_continue:
        if not request.user.is_authenticated:
            audit_logger.error("Organisation delete page was called but user was not authenticated.")
        else:
            audit_logger.error("Organisation delete page was called but there was a preflight error.")
        raise SuspiciousOperation(
            f"Called {request.method} on delete organisation page but there was a preflight/authentication issue"
        )

    # This page should only be called with POST.
    if not request.method == "POST":
        audit_logger.error(
            f"User {request.user.log_label} called the organisation delete page "
            f"with an incorrect method ({request.method})"
        )
        raise SuspiciousOperation(f"Called {request.method} on delete organisation page")

    # Build the form and validate it.
    form = OrganisationDeleteForm(request.POST)
    if not form.is_valid():
        audit_logger.error(
            f"User {request.user.log_label} called the organisation delete page but the form was invalid"
        )
        raise SuspiciousOperation(f"Called {request.method} on delete organisation page")

    if form.cleaned_data["human_readable_name"] != form.cleaned_data["confirm_human_readable_name"]:
        audit_logger.error(
            f"User {request.user.log_label} called the organisation delete page to "
            f"try to delete organisation {oid} but the confirmation human readable "
            f"name ({form.cleaned_data["confirm_human_readable_name"]}) did not match "
            f"the name of the organisation ({form.cleaned_data["human_readable_name"]}) "
            f"they were trying to delete."
        )
        raise SuspiciousOperation("Oranisation delete page was called with a mismatching confirmation text")

    if form.cleaned_data["oid"] != oid:
        audit_logger.error(
            f"User {request.user.log_label} called the organisation delete page "
            f"to try to delete organisation {oid} but there was a mismatch between "
            f"the organisation id in the form {form.cleaned_data["oid"]} and in the "
            f"URL {oid}."
        )
        raise SuspiciousOperation("Oranisation delete page was called with a mismatching organisation id")

    # All okay, so call RYD to delete the organisation.
    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)
    try:
        session.delete(f"/reporting-orgs/{oid}")
    except Exception as exc:
        audit_logger.error(f"Problem deleting organisaiton {oid} by user {request.user.log_label} with error {exc}")
        raise exc

    # All okay - redirect to the organisation list page.
    messages.add_message(
        request,
        messages.SUCCESS,
        f"Reporting organisation '{form.cleaned_data["human_readable_name"]}' was successfully deleted.",
    )
    return redirect("data:home")


def dataset_list(request: HttpRequest, oid: str) -> HttpResponse:

    preflight = preflight_checks(request)
    if not preflight.okay_to_continue:
        return preflight.redirect

    page = request.GET.get("page", 1)
    page_size = 2
    # page_size = request.GET.get("page_size", 100)

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    # Get the dataset list.
    try:
        dataset_response = session.get(
            f"/reporting-orgs/{oid}/datasets", params={"page": page, "page_size": page_size}
        )
        datasets = parse_dataset_list_to_objects(dataset_response.get("data", []))
        pagination = parse_pagination_links(dataset_response.get("pagination", {}))
    except Exception as exc:
        audit_logger.error(
            f"Could not access RYD for user {request.user.log_label} "
            f"trying to load datasets for reporting org {oid} with error {exc}"
        )
        raise exc

    # Get the reporting org details to decorate the page.
    try:
        reporting_org_data = session.get(f"/reporting-orgs/{oid}").get("data", {})
        reporting_org = ReportingOrganisation.from_ryd_reporting_organisation(reporting_org_data)
        this_user = UserAndRole.from_ryd(
            reporting_org_data["user_role"], request.user.registry_id, reporting_org_data["id"], None, None
        )
    except Exception as exc:
        audit_logger.error(
            f"Could not access RYD for user {request.user.log_label} "
            f"trying to load reporting org {oid} with error {exc}"
        )
        raise exc

    context = {
        "org": reporting_org,
        "datasets": datasets,
        "pagination": pagination,
        "this_user": this_user,
    }

    template = loader.get_template("data/dataset_list.html")
    return HttpResponse(template.render(context, request))


def create_dataset(request: HttpRequest, oid: str) -> HttpResponse:  # noqa: C901
    """Generates the create dataset page and handles POST responses

    Parameters
    ----------
    request : HttpRequest
    oid : str

    Returns
    -------
    HttpResponse
    """

    preflight = preflight_checks(request)
    if preflight.not_okay_to_continue:
        return preflight.redirect

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    form = None

    if request.method == "POST":
        form = CreateDatasetForm(request.POST)
        app_logger.debug(f"Creating dataset; form validation result {form.is_valid()}")
        if form.is_valid():
            try:
                result = session.post(
                    "/datasets",
                    json={"owner_organisation_id": str(oid), **form.instance.get_ryd_post_payload()},
                )
                messages.add_message(request, messages.SUCCESS, "Dataset created successfully.")
                return redirect("data:dataset-detail", oid=oid, dataset_id=result["data"]["id"])
            except RegisterYourDataRecordAlreadyExists:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "A dataset already exists in the registry with the same short name. "
                    "Please try a different short name and try again.",
                )
                form.add_error("short_name", "Already exists in the registry")
            except RegisterYourDataFieldValidationError as exc:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem in creating your new dataset.  Please correct the "
                    "errors below and try again.",
                )
                if "short_name" in str(exc):
                    form.add_error(
                        "short_name",
                        "Short names should only contain alphanumeric characters, hyphens, or underscores.",
                    )
                else:
                    audit_logger.error(
                        f"Could not create dataset in RYD for organisation {oid} on behalf of user "
                        f"{request.user.log_label} with error {exc}"
                    )
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "There was a problem in creating your new dataset.  Please try again "
                        "later, or if the problem persists, please contact IATI Support.",
                    )
                    raise exc
            except Exception as exc:
                audit_logger.error(
                    f"Could not create dataset in RYD for organisation {oid} on behalf of user "
                    f"{request.user.log_label} with error {exc}"
                )
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem in creating your new dataset.  Please try again "
                    "later, or if the problem persists, please contact IATI Support.",
                )
        else:
            messages.add_message(
                request,
                messages.WARNING,
                "There was a problem in creating your new dataset.  Please correct the " "errors below and try again.",
            )

    # Get the reporting org details to decorate the page.
    try:
        reporting_org_data = session.get(f"/reporting-orgs/{oid}").get("data", {})
        reporting_org = ReportingOrganisation.from_ryd_reporting_organisation(reporting_org_data)
        this_user = UserAndRole.from_ryd(
            reporting_org_data["user_role"], request.user.registry_id, reporting_org_data["id"], None, None
        )
    except Exception as exc:
        audit_logger.error(
            f"Could not access RYD for user {request.user.log_label} "
            f"trying to load reporting org {oid} with error {exc}"
        )
        raise exc

    context = {
        "form": (
            form
            if form
            else CreateDatasetForm(
                initial={
                    "licence_id": reporting_org.default_licence_id,
                    "source_type": reporting_org.reporting_source_type,
                    "visibility": "private",
                }
            )
        ),
        "org": reporting_org,
        "this_user": this_user,
    }
    template = loader.get_template("data/create_dataset.html")
    return HttpResponse(template.render(context, request))


def dataset_detail(request: HttpRequest, oid: str, dataset_id: str) -> HttpResponse:  # noqa: C901
    """Generate dataset detail page for editing/deleting datasets.

    Parameters
    ----------
    request : HttpRequest
    oid : str
        UUID of the owner organisation for the dataset.
    dataset_id : str
        UUID of the dataset that needs to be edited/deleted.

    Returns
    -------
    HttpResponse
    """

    preflight = preflight_checks(request)
    if not preflight.okay_to_continue:
        return preflight.redirect

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    # Get reporting org data so we can decorate the page.
    try:
        reporting_org_data = session.get(f"/reporting-orgs/{oid}").get("data", {})
        reporting_org = ReportingOrganisation.from_ryd_reporting_organisation(reporting_org_data)
        this_user = UserAndRole.from_ryd(
            reporting_org_data["user_role"], request.user.registry_id, reporting_org_data["id"], None, None
        )
    except Exception as exc:
        audit_logger.error(
            f"Could not access RYD for user {request.user.log_label} "
            f"trying to load reporting org {oid} with error {exc}"
        )
        raise exc

    # Get the dataset details.
    try:
        dataset_data = session.get(f"/datasets/{dataset_id}").get("data", {})
        dataset = Dataset.from_ryd(dataset_data)
    except Exception as exc:
        audit_logger.error(
            f"Could not access RYD for user {request.user.log_label} "
            f"trying to load dataset {dataset_id} from org {oid} with error {exc}"
        )
        raise exc

    form = DatasetDetailsForm(instance=dataset)
    if request.POST:
        form = form = DatasetDetailsForm(request.POST, instance=dataset)
        app_logger.debug(f"Updating a dataset - form validation state: {form.is_valid()}")
        if form.is_valid():
            try:
                session.patch(
                    f"/datasets/{dataset_id}",
                    json=form.get_ryd_patch_payload_from_cleaned_data(),
                )

                # Figure out what has changed so we can reflect that on the dataset form without
                # calling RYD again.
                if "url" in form.changed_data:
                    dataset.last_url_update_date = datetime.now(timezone.utc)
                if (
                    len(
                        [
                            field
                            for field in form.changed_data
                            if field
                            in ["human_readable_name", "source_type", "short_name", "visibility", "licence_id"]
                        ]
                    )
                    > 0
                ):
                    dataset.last_metadata_update_date = datetime.now(timezone.utc)
                messages.add_message(request, messages.SUCCESS, "Dataset updated successfully.")
            except RegisterYourDataRecordAlreadyExists:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "A dataset already exists in the registry with the same short name. "
                    "Please try a different short name and try again.",
                )
                form.add_error("short_name", "Already exists in the registry")
            except RegisterYourDataFieldValidationError as exc:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem in creating your new dataset.  Please correct the "
                    "errors below and try again.",
                )
                if "short_name" in str(exc):
                    form.add_error(
                        "short_name",
                        "Short names should only contain alphanumeric characters, hyphens, or underscores.",
                    )
                else:
                    audit_logger.error(
                        f"Could not update dataset in RYD for organisation {oid} on behalf of "
                        f"user {request.user.log_label} with error {exc}"
                    )
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "There was a problem in updating this dataset.  Please try again "
                        "later, or if the problem persists, please contact IATI Support.",
                    )
                    raise exc
            except Exception as exc:
                audit_logger.error(
                    f"Could not update dataset in RYD for organisation {oid} on behalf of "
                    f"user {request.user.log_label} with error {exc}"
                )
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem in updating this dataset.  Please try again "
                    "later, or if the problem persists, please contact IATI Support.",
                )
                raise exc
        else:
            messages.add_message(
                request,
                messages.WARNING,
                "There was a problem in updating the new dataset.  Please correct the " "errors below and try again.",
            )

    # Here we have an organisation change form and we need to set the editability
    # of certain fields depending on the user role.
    if not this_user.can_edit_dataset:
        form.fields["human_readable_name"].disabled = True
        form.fields["source_type"].disabled = True
        form.fields["url"].disabled = True
        form.fields["licence_id"].disabled = True

    form.fields["visibility"].disabled = True
    if this_user.can_change_dataset_visibility:
        form.fields["visibility"].disabled = False

    # Build the context and then render the page.
    context = {
        "form": form,
        "org": reporting_org,
        "dataset": dataset,
        "dataset_delete_form": DatasetDeleteForm(
            initial={"dataset_id": dataset.dataset_id, "human_readable_name": dataset.human_readable_name}
        ),
        "this_user": this_user,
        "show_delete_org_button": True if this_user.can_delete_dataset else False,
    }
    template = loader.get_template("data/dataset_detail.html")
    return HttpResponse(template.render(context, request))


def dataset_delete(request: HttpRequest, oid: str, dataset_id: str) -> HttpResponse:  # noqa: C901

    # Do a small pre-flight check, as we need to check that the user is provisioned and
    # authenticated.
    preflight = preflight_checks(request, check_onboarding=False)
    if not preflight.okay_to_continue:
        if not request.user.is_authenticated:
            audit_logger.error("Dataset delete page was called but user was not authenticated.")
        else:
            audit_logger.error("Dataset delete page was called but there was a preflight error.")
        raise SuspiciousOperation(
            f"Called {request.method} on delete dataset page but there was a preflight/authentication issue"
        )

    # This page should only be called with POST.
    if not request.method == "POST":
        audit_logger.error(
            f"User {request.user.log_label} called the dataset delete page "
            f"with an incorrect method ({request.method})"
        )
        raise SuspiciousOperation(f"Called {request.method} on delete dataset page")

    # Build the form and validate it.
    form = DatasetDeleteForm(request.POST)
    if not form.is_valid():
        audit_logger.error(f"User {request.user.log_label} called the dataset delete page but the form was invalid")
        raise SuspiciousOperation(f"Called {request.method} on delete dataset page")

    if form.cleaned_data["dataset_id"] != dataset_id:
        audit_logger.error(
            f"User {request.user.log_label} called the dataset delete page to "
            f"try to delete dataset {dataset_id} but the dataset id in the form "
            f"did not match the id of the dataset {form.cleaned_data["dataset_id"]} "
            f"they were trying to delete."
        )
        raise SuspiciousOperation("Dataset delete page was called with a mismatching dataset UUIDs")

    # All okay, so call RYD to delete the dataset.
    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)
    try:
        session.delete(f"/datasets/{dataset_id}")
    except Exception as exc:
        audit_logger.error(f"Problem deleting dataset {dataset_id} by user {request.user.log_label} with error {exc}")
        raise exc

    # All okay - redirect to the dataset list page.
    messages.add_message(
        request,
        messages.SUCCESS,
        f"Dataset '{form.cleaned_data["human_readable_name"]}' was successfully deleted.",
    )
    return redirect("data:dataset-list", oid=oid)
