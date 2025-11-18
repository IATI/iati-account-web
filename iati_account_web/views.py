from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader


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
    # print("Views: Logout page")
    # print("  Session keys-value pairs:")
    # for k in request.session.keys():
    #     print(f"    {k}: {request.session[k]}")
    return redirect("/")
