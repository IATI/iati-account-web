import functools
import logging
from collections import namedtuple

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

app_logger = logging.getLogger("iati_account")


PreFlightStatus = namedtuple("PreFlightStatus", ["not_okay_to_continue", "okay_to_continue", "redirect"])


def preflight_checks(request: HttpRequest, check_onboarding: bool = True) -> PreFlightStatus:
    """Performs repetitive checks that are needed in all views.

    Parameters
    ----------
    request : HttpRequest
        The Django request object.
    check_onboarding : bool, optional
        If true this checks that the user has been onboarded, and if not will return a
        redirect to onboarding pages.  By default this is checked.

    Returns
    -------
    PreFlightStatus
    """
    logging.getLogger("iati_account").debug(f"Preflight checks for {request.path}")
    if not request.user.is_authenticated:
        logging.getLogger("iati_account").debug(f"Preflight checks for {request.path}: not authenticated")
        return PreFlightStatus(
            not_okay_to_continue=True, okay_to_continue=False, redirect=redirect("oidc_authentication_init")
        )

    if not request.user.has_been_provisioned:
        logging.getLogger("iati_account").debug(f"Preflight checks for {request.path}: not provisioned")
        return PreFlightStatus(not_okay_to_continue=True, okay_to_continue=False, redirect=redirect("provisioning"))

    if check_onboarding and not request.user.has_been_onboarded:
        logging.getLogger("iati_account").debug(f"Preflight checks for {request.path}: not onboarded")
        return PreFlightStatus(
            not_okay_to_continue=True, okay_to_continue=False, redirect=redirect("account:onboarding")
        )

    return PreFlightStatus(not_okay_to_continue=False, okay_to_continue=True, redirect=None)


def require_preflight(view_func=None, *, check_onboarding=True):
    """Run preflight_checks and short-circuit with redirect if the user can't continue."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            preflight = preflight_checks(request, check_onboarding=check_onboarding)
            if not preflight.okay_to_continue:
                return preflight.redirect
            return func(request, *args, **kwargs)

        return wrapper

    return decorator(view_func) if callable(view_func) else decorator
