import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.template import loader
from iati_account_web.helpers import preflight_checks
from iati_account_web.ryd_handling import RegisterYourDataSession
from iati_account_web.ryd_handling.reporting_orgs import (
    get_all_discoverable_reporting_orgs,
)
from iati_account_web.settings import COUNTRY_LIST

audit_logger = logging.getLogger("audit")
app_logger = logging.getLogger("iati_account")


def home(request: HttpRequest) -> HttpResponse:
    """Generates the main landing page for superadmin

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

    if not request.user.is_iati_superadmin:
        audit_logger.critical(
            f"User {request.user.log_label} attempted to access a "
            "superadmin page but does not have superadmin privileges"
        )
        raise PermissionDenied

    session = RegisterYourDataSession(request.session["oidc_access_token"], allow_redirects=True)
    discoverable_reporting_orgs = get_all_discoverable_reporting_orgs(session)

    template = loader.get_template("superadmin/home.html")
    context = {
        "discoverable_reporting_orgs": discoverable_reporting_orgs,
        "COUNTRY_LIST": COUNTRY_LIST,
    }
    return HttpResponse(template.render(context, request))
