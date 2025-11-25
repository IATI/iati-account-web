from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.utils.translation import gettext_lazy as _
from iati_account_web.account.forms import AccountOnboardingForm, AccountSelfServiceForm
from iati_account_web.identity import add_ryd_role_in_identity_service, patch_user_in_identity_service


def self_service(request: HttpRequest) -> HttpResponse:
    """Generate self-service Account page view where users can self-service their account.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponse
    """

    if not request.user.is_authenticated:
        return redirect("oidc_authentication_init")

    context = {"detail_update": False, "detail_update_ok": None, "detail_update_text": ""}

    if request.method == "POST":
        context["detail_update"] = True
        context["detail_update_ok"] = False
        context["detail_update_text"] = _("There was an error updating your account details, please try again later.")
        form = AccountSelfServiceForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            if patch_user_in_identity_service(request.user):
                context["detail_update_ok"] = True
                context["detail_update_text"] = _("Account details updated successfully.")

    else:
        form = AccountSelfServiceForm(instance=request.user)

    context["form"] = form

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

    if not request.user.is_authenticated:
        return redirect("oidc_authentication_init")

    context = {"detail_update": False, "detail_update_ok": None, "detail_update_text": ""}

    if request.method == "POST":
        context["detail_update"] = True
        context["detail_update_ok"] = False
        context["detail_update_text"] = _("There was an error updating your account details, please try again later.")
        form = AccountOnboardingForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            request.user.has_been_onboarded = True
            request.user.save()
            if patch_user_in_identity_service(request.user):
                if add_ryd_role_in_identity_service(request.user):
                    return redirect("welcome:home")

    else:
        form = AccountOnboardingForm(instance=request.user)

    context["form"] = form

    template = loader.get_template("account/onboarding.html")

    return HttpResponse(template.render(context, request))
