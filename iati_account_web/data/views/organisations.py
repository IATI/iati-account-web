"""Views for joining, viewing, creating and deleting reporting organisations."""

import logging
from uuid import UUID

from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.views.decorators.http import require_POST
from iati_account_web.constants import COUNTRY_LIST, USER_ROLE_LOOKUP
from iati_account_web.data.forms import (
    AuthoriseToolForm,
    CreateOrganisationForm,
    JoinOrganisationForm,
    OrganisationDeleteForm,
    OrganisationDetailsForm,
    OrgUserFormSet,
    ToolFormSet,
)
from iati_account_web.data.models import Tool
from iati_account_web.exceptions import RegisterYourDataFieldValidationError, RegisterYourDataRecordAlreadyExists
from iati_account_web.helpers import preflight_checks, require_preflight
from iati_account_web.ryd_handling import RegisterYourDataSession
from iati_account_web.ryd_handling.reporting_orgs import OrgDetail, get_all_discoverable_reporting_orgs, get_org_detail
from iati_account_web.typing import AuthedHttpRequest

audit_logger = logging.getLogger("audit")
app_logger = logging.getLogger("iati_account")


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

            discoverable_reporting_orgs = get_all_discoverable_reporting_orgs(session)
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
            "COUNTRY_LIST": COUNTRY_LIST,
        }
        return HttpResponse(template.render(context, request))


def _build_org_detail_context(  # noqa: C901
    data: OrgDetail,
    *,
    org_form: OrganisationDetailsForm | None = None,
    user_formset: OrgUserFormSet | None = None,  # type: ignore
    revoke_tool_formset: ToolFormSet | None = None,  # type: ignore
    authorise_tool_form: AuthoriseToolForm | None = None,
) -> dict:
    """Assemble the template context for the organisation detail page.

    Assembles the context for the organisation detail page (performs no I/O) so
    a caller fetches the page data once (via 'get_org_detail') and reuses it for
    both the initial render and any re-render after a failed POST.

    Any of the four forms may be supplied by the caller. A POST handler that has
    built a bound form but which fails validation passes that form in so it
    renders with its state and errors intact, while the remaining forms are
    built unbound for display.

    Parameters
    ----------
    data : OrgDetail
        Pre-fetched organisation detail data (see 'get_org_detail').
    org_form : OrganisationDetailsForm, optional
        Pre-built org-details form to render instead of a fresh one.
    user_formset : OrgUserFormSet, optional
        Pre-built user formset to render instead of a fresh one.
    revoke_tool_formset : ToolFormSet, optional
        Pre-built revoke-tool formset to render instead of a fresh one.
    authorise_tool_form : AuthoriseToolForm, optional
        Pre-built authorise-a-tool form to render instead of a fresh one.

    Returns
    -------
    dict
        Template context for data/org_detail.html.
    """
    reporting_org = data.reporting_org
    this_user = data.current_user

    # Build any unbound forms (the ones the caller did not supply) for display

    if org_form is None:
        org_form = OrganisationDetailsForm(instance=reporting_org)

    if user_formset is None:
        user_formset = OrgUserFormSet(
            prefix="users",
            initial=[
                {"uid": x.uid, "name": x.name, "email": x.email, "role": x.role, "oid": reporting_org.oid}
                for x in data.users_and_roles.values()
                if x.role != "provider_admin"
            ],
        )

    if revoke_tool_formset is None:
        revoke_tool_formset = ToolFormSet(
            prefix="tools",
            initial=[{"tool_id": t.tool_id} for t in data.authorised_tools],
        )

    if authorise_tool_form is None:
        authorise_tool_form = AuthoriseToolForm(available_tools=data.addable_tools)

    # Contributors get a read-only organisation-details form.
    if this_user.role == "contributor":
        for field in org_form.fields.values():
            field.disabled = True
        for field in authorise_tool_form.fields.values():
            field.disabled = True

    # Pair each revoke tool sub-form (hidden tool_id + revoke checkbox) with its
    # server-side Tool so the template shows name/provider from trusted data.
    revoke_tool_rows = list(zip(revoke_tool_formset, data.authorised_tools))  # type: ignore

    return {
        "org_form": org_form,
        "user_formset": user_formset,
        "tool_formset": revoke_tool_formset,
        "tool_rows": revoke_tool_rows,
        "authorise_tool_form": authorise_tool_form,
        "org": reporting_org,
        "this_user": this_user,
        "show_delete_org_button": this_user.role == "admin" or this_user.super_admin,
        "show_org_info_button_box": this_user.role != "contributor",
        "delete_form": OrganisationDeleteForm(
            {"oid": reporting_org.oid, "human_readable_name": reporting_org.human_readable_name}
        ),
    }


@require_preflight
def organisation_detail(request: AuthedHttpRequest, oid: str) -> HttpResponse:  # noqa: C901
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

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    org_data = get_org_detail(request, session, oid, request.user.registry_id)

    # Handle form submission.  We can receive submissions from either the organisation
    # change form, the manage users form, or the manage tools form
    form = None
    user_formset = None
    revoke_tool_formset = None
    authorise_tool_form = None

    if request.POST:

        if "saveOrgChanges" in request.POST:
            # The organisation details form was submitted.  Build the form and
            # validate it.  If it is valid we make the changes via RYD, otherwise
            # suitable messages are generated.
            form = OrganisationDetailsForm(request.POST, instance=org_data.reporting_org)
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
                prefix="users",
                initial=[
                    {
                        "uid": x.uid,
                        "name": x.name,
                        "email": x.email,
                        "role": x.role,
                        "oid": org_data.reporting_org.oid,
                    }
                    for x in org_data.users_and_roles.values()
                    if x.role != "provider_admin"
                ],
            )

            app_logger.debug(f"Updating organisation {oid} users; form validation result {user_formset.is_valid()}")
            if user_formset.is_valid():
                user_removed = False
                for user_form in user_formset:
                    form_uid = user_form.cleaned_data["uid"]

                    if form_uid not in org_data.users_and_roles.keys():
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
                                (
                                    f"{org_data.users_and_roles[form_uid].name} was "
                                    "successfully removed from this organisation."
                                ),
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
                                f"There was an error in removing {org_data.users_and_roles[form_uid].name} "
                                "from this organisation.  Please try again later, and if the error "
                                "persists please contact IATI Support.",
                            )
                    elif org_data.users_and_roles[form_uid].role != user_form.cleaned_data["role"]:
                        if user_form.cleaned_data["role"] not in ("admin", "editor", "contributor"):
                            messages.add_message(
                                request,
                                messages.ERROR,
                                "You can only change the user roles to Admin, Editor or "
                                f"Contributor, not {USER_ROLE_LOOKUP[user_form.cleaned_data["role"]]}",
                            ),
                        else:
                            try:
                                session.put(
                                    f"/users/{form_uid}/reporting-org/{oid}",
                                    json={"role": user_form.cleaned_data["role"]},
                                )
                                audit_logger.info(
                                    f"User {request.user.log_label} changed user role for "
                                    f"user {form_uid} in organisation {oid} from "
                                    f"{org_data.users_and_roles[form_uid].role} to "
                                    f"{user_form.cleaned_data["role"]}"
                                )
                                messages.add_message(
                                    request,
                                    messages.SUCCESS,
                                    (
                                        f"Your changes for {org_data.users_and_roles[form_uid].name} "
                                        "were saved successfully."
                                    ),
                                )
                            except Exception as exc:
                                audit_logger.error(
                                    f"Could not change user role in request by {request.user.log_label} "
                                    f"to change user role for user {form_uid} in organisation {oid} from "
                                    f"{org_data.users_and_roles[form_uid].role} to "
                                    f"{user_form.cleaned_data["role"]} with error {exc}"
                                )
                                messages.add_message(
                                    request,
                                    messages.ERROR,
                                    "There was an error in saving your changes for "
                                    f"{org_data.users_and_roles[form_uid].name}.  Please try again later, and "
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

    context = _build_org_detail_context(
        org_data,
        org_form=form,
        user_formset=user_formset,
        revoke_tool_formset=revoke_tool_formset,
        authorise_tool_form=authorise_tool_form,
    )

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


@require_preflight
@require_POST
def organisation_tool_authorise(request: AuthedHttpRequest, oid: str) -> HttpResponse:
    """Authorise a third party tool to be used with this organisation

    Args:
        request (AuthedHttpRequest): the HttpRequest
        oid (str): organisation ID
    """

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    org_data = get_org_detail(request, session, oid, request.user.registry_id)

    authorise_tool_form = AuthoriseToolForm(request.POST, available_tools=org_data.addable_tools)

    if authorise_tool_form.is_valid():
        chosen_tool = {str(t.tool_id): t for t in org_data.addable_tools}[authorise_tool_form.cleaned_data["tool_id"]]

        try:
            session.post(f"/reporting-orgs/{oid}/tools", json={"tid": str(chosen_tool.tool_id)})

            audit_logger.info(
                f"User {request.user.log_label} authorised tool {chosen_tool.name} "
                f"(tool id: {chosen_tool.tool_id}) for organisation {oid}"
            )

            messages.add_message(request, messages.SUCCESS, f"You have successfully authorised {chosen_tool.name}.")

            return redirect("data:reporting-org-detail", oid=oid)

        except Exception as exc:
            audit_logger.error(
                f"Could not authorise tool {chosen_tool.name} (tool id: {chosen_tool.tool_id} "
                f"in request by {request.user.log_label} with error {exc}"
            )
            messages.add_message(
                request,
                messages.ERROR,
                f"There was an error in authorising {chosen_tool.name}. "
                "Please try again later, and if the error persists please contact IATI Support.",
            )

    else:
        messages.add_message(
            request, messages.ERROR, "That tool is not available to authorise: it may already be authorised."
        )

    context = _build_org_detail_context(org_data, authorise_tool_form=authorise_tool_form)

    template = loader.get_template("data/org_detail.html")

    return HttpResponse(template.render(context, request))


@require_preflight
@require_POST
def organisation_tool_revoke(request: AuthedHttpRequest, oid: str) -> HttpResponse:  # noqa: C901
    """Handler for the revoke tool(s) authorisation form.

    Args:
        request (AuthedHttpRequest): the HTTP request
        oid (str): reporting organissation ID
    """

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)

    org_data = get_org_detail(request, session, oid, request.user.registry_id)

    # The revoke-tool-authorisations form was submitted.  Build and validate the
    # formset, then revoke authorisation for each tool marked for removal.
    # Compare against the authoritative tool list fetched from RYD (org_data)
    # and reject any submitted tool that is not in it.
    revoke_tool_formset = ToolFormSet(
        request.POST,
        prefix="tools",
        initial=[{"tool_id": t.tool_id} for t in org_data.authorised_tools],
    )

    if revoke_tool_formset.is_valid():
        tool_revoked = False
        for this_tool_form in revoke_tool_formset:
            form_tool_id: UUID = this_tool_form.cleaned_data["tool_id"]

            if this_tool_form.cleaned_data["DELETE"]:

                if form_tool_id not in org_data.authorised_tools_by_id.keys():
                    audit_logger.error(
                        f"User {request.user.log_label} tried to revoke authorisation for "
                        f"tool {form_tool_id} but it is not in the list of authorised tools for "
                        f"organisation {oid}"
                    )
                    raise SuspiciousOperation

                tool_being_revoked: Tool = org_data.authorised_tools_by_id[form_tool_id]

                try:
                    session.delete(f"/reporting-orgs/{oid}/tools/{str(form_tool_id)}")
                    tool_revoked = True
                    audit_logger.info(
                        f"User {request.user.log_label} revoked authorisation for tool "
                        f"{tool_being_revoked.name} (tool id: {tool_being_revoked.tool_id}) for "
                        f"organisation {oid}"
                    )
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        f"You have successfully revoked authorisation for {tool_being_revoked.name}.",
                    )
                except Exception as exc:
                    audit_logger.error(
                        f"Could not revoke authorisation for tool {tool_being_revoked.name} (tool id: "
                        f"{tool_being_revoked.tool_id}) in request by {request.user.log_label} with error "
                        f"{exc}"
                    )
                    messages.add_message(
                        request,
                        messages.ERROR,
                        f"There was an error in revoking authorisation for {tool_being_revoked.name}. "
                        "Please try again later, and if the error persists please contact IATI Support.",
                    )

        # If we successfully revoked anything, redirect back to refresh the re-fetched tool list.
        if tool_revoked:
            return redirect("data:reporting-org-detail", oid=oid)

    else:
        audit_logger.error(
            f"User {request.user.log_label} submitted a malformed payload to "
            f"the revoke tool endpoint for organisation {oid}"
        )
        raise SuspiciousOperation

    context = _build_org_detail_context(org_data, revoke_tool_formset=revoke_tool_formset)

    template = loader.get_template("data/org_detail.html")

    return HttpResponse(template.render(context, request))
