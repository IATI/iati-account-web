"""Views for the main landing page for the data section of IATI Account"""

import logging

from django.http import HttpRequest, HttpResponse
from django.template import loader
from iati_account_web.helpers import preflight_checks
from iati_account_web.ryd_handling import RegisterYourDataSession
from iati_account_web.ryd_handling.reporting_orgs import parse_org_list_to_objects

audit_logger = logging.getLogger("audit")


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
