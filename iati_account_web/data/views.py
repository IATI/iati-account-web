from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader


def home(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("oidc_authentication_init")

    template = loader.get_template("data/home.html")
    context = {}
    return HttpResponse(template.render(context, request))
