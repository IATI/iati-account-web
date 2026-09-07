"""Views for listing, viewing, creating and deleting datasets."""

import logging
from datetime import datetime, timezone

from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import loader
from iati_account_web.data.forms import CreateDatasetForm, DatasetDeleteForm, DatasetDetailsForm
from iati_account_web.data.models import Dataset, ReportingOrganisation, UserAndRole
from iati_account_web.exceptions import RegisterYourDataFieldValidationError, RegisterYourDataRecordAlreadyExists
from iati_account_web.helpers import preflight_checks, require_preflight
from iati_account_web.ryd_handling import RegisterYourDataSession, parse_pagination_links
from iati_account_web.ryd_handling.reporting_orgs import parse_dataset_list_to_objects
from iati_account_web.typing import AuthedHttpRequest

audit_logger = logging.getLogger("audit")
app_logger = logging.getLogger("iati_account")


@require_preflight
def dataset_list(request: AuthedHttpRequest, oid: str) -> HttpResponse:

    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 24)

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


@require_preflight
def create_dataset(request: AuthedHttpRequest, oid: str) -> HttpResponse:  # noqa: C901
    """Generates the create dataset page and handles POST responses

    Parameters
    ----------
    request : AuthedHttpRequest
    oid : str

    Returns
    -------
    HttpResponse
    """

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    form = None

    if request.method == "POST":
        form = CreateDatasetForm(request.POST)
        app_logger.debug(f"Creating dataset; form validation result {form.is_valid()}")
        if form.is_valid():
            try:
                _ = session.post(
                    "/datasets",
                    json={"owner_organisation_id": str(oid), **form.instance.get_ryd_post_payload()},
                )
                messages.add_message(request, messages.SUCCESS, "Dataset created successfully.")
                return redirect("data:dataset-list", oid=oid)

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
                    "visibility": "public",
                }
            )
        ),
        "org": reporting_org,
        "this_user": this_user,
    }
    template = loader.get_template("data/create_dataset.html")
    return HttpResponse(template.render(context, request))


@require_preflight
def dataset_detail(request: AuthedHttpRequest, oid: str, dataset_id: str) -> HttpResponse:  # noqa: C901
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

    updateable_fields: list[str] = [
        "human_readable_name",
        "licence_id",
        "source_type",
        "short_name",
        "url",
        "visibility",
    ]

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

    fields_editable_status: dict[str, bool] = {
        f: this_user.can_edit_dataset for f in updateable_fields if f != "visibility"
    }
    fields_editable_status["visibility"] = this_user.can_change_dataset_visibility

    form = DatasetDetailsForm(instance=dataset)
    if request.POST:
        form = DatasetDetailsForm(request.POST, instance=dataset)

    # Set field editability based on user role. This must happen before
    # is_valid() so disabled fields fall back to the instance value rather
    # than failing required-field validation when the disabled HTML control
    # was not submitted.
    for field_name, editable in fields_editable_status.items():
        form.fields[field_name].disabled = not editable

    if request.POST:
        app_logger.debug(f"Updating a dataset - form validation state: {form.is_valid()}")
        if form.is_valid():
            try:
                session.patch(
                    f"/datasets/{dataset_id}",
                    json=form.get_ryd_patch_payload_from_cleaned_data(fields_editable_status),
                )

                # Figure out what has changed so we can reflect that on the dataset form without
                # calling RYD again.
                if "url" in form.changed_data:
                    dataset.last_url_update_date = datetime.now(timezone.utc)
                if len(set(form.changed_data) & set([f for f in updateable_fields if f != "url"])) > 0:
                    dataset.last_metadata_update_date = datetime.now(timezone.utc)
                messages.add_message(request, messages.SUCCESS, "Dataset updated successfully.")
                return redirect("data:dataset-list", oid=oid)
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
                        f"Could not update dataset in RYD for organisation {oid} on behalf of "  # nosec B608
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
                    f"Could not update dataset in RYD for organisation {oid} on behalf of "  # nosec B608
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


def dataset_delete(request: AuthedHttpRequest, oid: str, dataset_id: str) -> HttpResponse:  # noqa: C901

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
