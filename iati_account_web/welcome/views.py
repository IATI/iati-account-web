import logging

from django.http import HttpRequest, HttpResponse
from django.template import loader
from iati_account_web.helpers import preflight_checks
from iati_account_web.ryd_handling import RegisterYourDataSession
from iati_account_web.ryd_handling.reporting_orgs import parse_org_list_to_objects

audit_logger = logging.getLogger("audit")


def index(request: HttpRequest) -> HttpResponse:

    if request.user.is_authenticated:
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
        template = loader.get_template("welcome/home.html")
    else:
        context = {}
        template = loader.get_template("welcome/index.html")

    return HttpResponse(template.render(context, request))


def complete_registration(request: HttpRequest) -> HttpResponse:
    """Simple page to inform a user that they need to complete registration in IATI Account

    This is called when a user tries to log into a third party application (e.g., IATI Publisher)
    with an unprovisioned account.

    Parameters
    ----------
    request : HttpRequest

    Returns
    -------
    HttpResponseRedirect
    """
    template = loader.get_template("welcome/complete_registration.html")
    return HttpResponse(template.render({}, request))
