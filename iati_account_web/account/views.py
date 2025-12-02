from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.utils.translation import gettext_lazy as _
from iati_account_web.account.forms import AccountOnboardingForm, AccountSelfServiceForm
from iati_account_web.helpers import preflight_checks
from iati_account_web.identity import (
    patch_user_in_identity_service,
)
import logging

app_logger = logging.getLogger("iati_account")

def self_service(request: HttpRequest) -> HttpResponse:
    """Generate self-service Account page view where users can self-service their account.

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

    if request.method == "POST":
        form = AccountSelfServiceForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save(commit=False)
            if patch_user_in_identity_service(request.user):
                messages.add_message(request, messages.SUCCESS, "Account updated successfully.")
                form.save()
            else:
                app_logger.error(f"Error in patching user {request.user.oidc_sub} in IdP")
                messages.add_message(
                    request, messages.ERROR, "There was a problem updating your account, please try again later."
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


def onboarding(request: HttpRequest) -> HttpResponse:
    """Generate onboarding page to let users complete their information.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """

    preflight = preflight_checks(request, check_onboarding=False)
    if not preflight.okay_to_continue:
        return preflight.redirect

    if request.method == "POST":
        form = AccountOnboardingForm(request.POST, instance=request.user)
        if form.is_valid():
            request.user.has_been_onboarded = True
            form.save(commit=False)
            if patch_user_in_identity_service(request.user):
                messages.add_message(request, messages.SUCCESS, "Account updated successfully.")
                request.user.save()
                return redirect("welcome:home")

            else:
                app_logger.error(f"Error in patching user {request.user.oidc_sub} in IdP")
                messages.add_message(
                    request, messages.ERROR, "There was a problem completing the onboarding process, please try again later."
                )
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
