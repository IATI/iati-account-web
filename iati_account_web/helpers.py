import json
import logging
from collections import namedtuple

from django.http import HttpRequest
from django.shortcuts import redirect


def _codelist_helper(filename: str) -> (list[tuple[str, str]], dict[str, str]):
    """Helper to load a codelist JSON file and generate a choice list and lookup

    Parameters
    ----------
    filename : str
        JSON codelist filename.

    Returns
    -------
    list[tuple[str,str]]
        Choice list for use in forms.
    dict[str, str]
        Lookup mapping codes to names.
    """

    choice_list = [("", "--")]
    lookup = {}
    if filename is not None:
        with open(filename, "r") as fh:
            data = json.load(fh)

            choice_list += [(x["code"], x["name"]) for x in data.get("data", [])]
            choice_list.sort(key=lambda x: x[1])

            lookup = {x["code"]: x["name"] for x in data.get("data", [])}

    lookup[""] = ""

    return choice_list, lookup


PreFlightStatus = namedtuple("PreFlightStatus", ["not_okay_to_continue", "redirect"])


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
        return PreFlightStatus(not_okay_to_continue=True, redirect=redirect("oidc_authentication_init"))

    if not request.user.has_been_provisioned:
        logging.getLogger("iati_account").debug(f"Preflight checks for {request.path}: not provisioned")
        return PreFlightStatus(not_okay_to_continue=True, redirect=redirect("provisioning"))

    if check_onboarding and not request.user.has_been_onboarded:
        logging.getLogger("iati_account").debug(f"Preflight checks for {request.path}: not onboarded")
        return PreFlightStatus(not_okay_to_continue=True, redirect=redirect("account:onboarding"))

    return PreFlightStatus(not_okay_to_continue=False, redirect=None)
