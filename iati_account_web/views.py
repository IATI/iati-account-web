import logging

import libsuitecrm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader
from iati_account_web.settings import env
from libsuitecrm import SuiteCRM

app_logger = logging.getLogger("iati_account")
audit_logger = logging.getLogger("audit")


def post_login(request: HttpRequest) -> HttpResponseRedirect:
    """Simple view that we call on login so we can log/count OIDC logins

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponseRedirect
    """
    audit_logger.info(f"User {request.user.log_label} logged in")
    return redirect("welcome:home")


def logout(request: HttpRequest) -> HttpResponseRedirect:
    """View called by Asgardeo on logout so that we can check session is clear.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponseRedirect
    """
    if "oidc_id_token" in request.session:
        del request.session["oidc_id_token"]
    if "oidc_access_token" in request.session:
        del request.session["oidc_access_token"]
    return redirect("/")


def provision_account(request: HttpRequest) -> HttpResponse:  # noqa: C901
    """Provision an account for a new user by making sure the user has a matching person record.

    To reduce the cyclomatic complexity of this function, with all its error checking,
    there are a number of helper functions defined after this one.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """

    if not request.user.is_authenticated:
        return redirect("oidc_authentication_init")

    oidc_access_token_needs_refreshing = False

    if request.user.has_been_provisioned:
        # There should be no reason why we should reach here, as we should only be
        # called if another view things we have not been provisioned.  Redirect to the
        # provisioning error page.  If we try to redirect to the home page we might end
        # with circular redirects.
        app_logger.error("Attempted to provision user, but it has already been carried out")
        audit_logger.error(f"Attempted to provision user {request.user.log_label} but it has already been carried out")
        template = loader.get_template("provisioning_error.html")
        return HttpResponse(template.render({}, request))

    audit_logger.info(f"Provisioning user {request.user.log_label}")

    # Add iati_register_your_data role in identity server.
    if not __provision_add_roles(request):
        __provision_try_to_lock_user_after_error(request)
        template = loader.get_template("provisioning_error.html")
        return HttpResponse(template.render({}, request))

    # If the logged-in user doesn't have a completed registry_id field then
    # we need to create a matching Person record in the CRM.
    if not request.user.registry_id:
        if not __provision_create_person_in_crm(request, request.user.log_label):
            __provision_try_to_lock_user_after_error(request)
            template = loader.get_template("provisioning_error.html")
            return HttpResponse(template.render({}, request))

        oidc_access_token_needs_refreshing = True

    # Completed, we just need to update the user record.
    request.user.has_been_provisioned = True
    if not __provision_patch_user_in_identity_service(request, request.user.log_label):
        __provision_try_to_lock_user_after_error(request)
        template = loader.get_template("provisioning_error.html")
        return HttpResponse(template.render({}, request))

    # All okay and complete.
    audit_logger.info(f"Provisioning for user {request.user.log_label} has been completed")
    request.user.save()
    if oidc_access_token_needs_refreshing:
        return redirect("oidc_authentication_init")

    return redirect("account:onboarding")


def __provision_add_roles(request: HttpRequest) -> bool:
    """Add roles to the user in the IdP as part of provisioning an account

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    bool
        True if this succeeded, false if failed.
    """

    audit_logger.debug(f"Provisioning: Adding iati_register_your_data role to user {request.user.log_label}")
    try:
        request.user.add_role_to_user_in_identity_service(env("IDENTITY_SERVICE_ROLE_ID_IATI_REGISTER_YOUR_DATA"))

    except Exception as exc:
        audit_logger.error(f"Provisioning: Failed to add role for user {request.user.log_label} with exception {exc}")
        app_logger.error(f"Provisioning: Failed to add role for user with exception {exc}.")

        audit_logger.info(f"Provisioning: Trying to lock account {request.user.log_label}")
        return False

    return True


def __provision_create_person_in_crm(request: HttpRequest) -> bool:
    """Craete person in the CRM as part of provisioning a user account

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    bool
        True if this succeeded, false if failed.
    """
    audit_logger.debug(f"Provisioning: trying to create person in the CRM for user {request.user.log_label}")
    try:
        app_logger.debug("Provisioning: connecting to SuiteCRM")
        crm = SuiteCRM(env("CRM_BASE_URL"), client_id=env("CRM_CLIENT_ID"), client_secret=env("CRM_CLIENT_SECRET"))
        crm.fetch_access_token()

        app_logger.debug("Provisioning: creating Person record")
        record = crm.create_record(
            "Contacts",
            {
                "last_name": request.user.unformatted_name,
                "email1": request.user.email,
                "iati_country": request.user.country,
                "iati_inperson_name": request.user.inperson_name,
                "iati_online_name": request.user.online_name,
                "iati_mailing_list_subscriber": request.user.mailinglist_subscriber,
                "iati_timezone": request.user.timezone,
                "iati_preferred_languages": request.user.languages,
                "iati_identityservice_id": request.user.oidc_sub,
            },
        )
        crm.logout()

        if "id" not in record:
            raise ValueError("CRM Record ID not in response from libsuitecrm")

        audit_logger.debug(f"Provisioning: Created CRM record {record["id"]} for user {request.user.log_label}")
        app_logger.debug("Provisioning: created record, updating user in IdP")

        request.user.registry_id = record["id"]

    except (
        libsuitecrm.RequestFailed,
        libsuitecrm.CannotUnderstandResponse,
        libsuitecrm.AuthorisationFailed,
        libsuitecrm.CreateRecordFailed,
    ) as exc:
        audit_logger.error(
            f"Provisioning: Failed to create record in CRM for user {request.user.log_label} in IdP with exception {exc}"
        )
        app_logger.error(f"Provisioning: Failed to create record in CRM with exception {exc}.")
        return False

    except Exception as exc:
        audit_logger.error(
            f"Provisioning: Failed creating CRM Person and adding to user account {request.user.log_label} "
            f"in IdP with an unexpected error {exc}"
        )
        app_logger.error(
            f"Provisioning: Failed to create CRM Person and add to user account in IdP with exception {exc}."
        )
        return False

    return True


def __provision_patch_user_in_identity_service(request: HttpRequest) -> bool:
    """Patch user account as part of provisioning

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    bool
        True if this succeeded, false if failed.
    """
    audit_logger.debug(f"Provisioning: updating user {request.user.log_label} in IdP")
    try:
        request.user.patch_user_in_identity_service(update_provisioned=True)
    except Exception as exc:
        audit_logger.error(f"Provisioning: Failed update user {request.user.log_label} in IdP with exception {exc}")
        app_logger.error(f"Provisioning: Failed to update user in IdP with exception {exc}.")
        return False

    return True


def __provision_try_to_lock_user_after_error(request: HttpRequest) -> None:
    """Try to lock the user account if there is a provisioning error

    Parameters
    ----------
    request : HttpRequest
    """
    try:
        request.user.lock_accout()
    except Exception as exc:
        audit_logger.error(f"Provisioning: Failed to lock account {request.user.log_label} with exception {exc}")
        app_logger.error(f"Provisioning: Failed to lock account with exception {exc}.")
