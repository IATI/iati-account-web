from django.http import HttpRequest, HttpResponse
from django.template import loader
from iati_account_web.identity import preflight_checks


def index(request: HttpRequest) -> HttpResponse:

    preflight = preflight_checks(request)
    if preflight.not_okay_to_continue:
        return preflight.redirect

    if request.user.is_authenticated:
        template = loader.get_template("welcome/home.html")
    else:
        template = loader.get_template("welcome/index.html")

    context = {}

    return HttpResponse(template.render(context, request))
