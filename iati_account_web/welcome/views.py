from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader


def index(request: HttpRequest) -> HttpResponse:

    if request.user.is_authenticated:
        if not request.user.has_been_onboarded:
            return redirect("account:start-onboarding")
        template = loader.get_template("welcome/home.html")
    else:
        template = loader.get_template("welcome/index.html")

    context = {}

    return HttpResponse(template.render(context, request))
