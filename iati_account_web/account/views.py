import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from iati_account_web.account.forms import AccountOnboardingForm, AccountSelfServiceForm
from iati_account_web.helpers import require_preflight

app_logger = logging.getLogger("iati_account")
audit_logger = logging.getLogger("audit")


@require_preflight
def self_service(request: HttpRequest) -> HttpResponse:
    """Generate self-service Account page view where users can self-service their account.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """

    if request.method == "POST":
        form = AccountSelfServiceForm(request.POST, instance=request.user)
        if form.is_valid():
            audit_logger.info(f"User {request.user.log_label} updating account ")
            form.save(commit=False)
            try:
                request.user.patch_user_in_identity_service()
                messages.add_message(request, messages.SUCCESS, "Account updated successfully.")
                form.save()
                request.user.save()
            except Exception as exc:
                app_logger.error(f"Could not update user in IdP with error {exc}")
                audit_logger.error(f"Could not update user {request.user.log_label} with error {exc}")
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem updating your account, please try again later.",
                )

        else:
            messages.add_message(
                request,
                messages.WARNING,
                "There was a problem with the form, please correct any errors and try again.",
            )

    else:
        form = AccountSelfServiceForm(instance=request.user)

    context = {"form": form}

    template = loader.get_template("account/self_service.html")

    return HttpResponse(template.render(context, request))


@require_preflight(check_onboarding=False)
def onboarding(request: HttpRequest) -> HttpResponse:
    """Generate onboarding page to let users complete their information.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """

    if request.method == "POST":
        form = AccountOnboardingForm(request.POST, instance=request.user)
        if form.is_valid():
            audit_logger.info(f"User {request.user.log_label} completing onboarding process")
            request.user.has_been_onboarded = True
            form.save(commit=False)
            try:
                request.user.patch_user_in_identity_service()
                messages.add_message(request, messages.SUCCESS, "Account updated successfully.")
                form.save()
                request.user.save()
            except Exception as exc:
                app_logger.error(f"Could not update user in IdP with error {exc}")
                audit_logger.error(f"Could not update user {request.user.log_label} with error {exc}")
                messages.add_message(
                    request,
                    messages.ERROR,
                    "There was a problem updating your account, please try again later.",
                )

            return redirect("welcome:home")

        else:
            messages.add_message(
                request,
                messages.WARNING,
                "There was a problem with the form, please correct any errors and try again.",
            )

    else:
        form = AccountOnboardingForm(instance=request.user)

    context = {"form": form}

    template = loader.get_template("account/onboarding.html")

    return HttpResponse(template.render(context, request))
