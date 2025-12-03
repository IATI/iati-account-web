from django.http import HttpRequest, HttpResponse
from django.template import loader


def index(request: HttpRequest) -> HttpResponse:

    if request.user.is_authenticated:
        template = loader.get_template("welcome/home.html")
    else:
        template = loader.get_template("welcome/index.html")

    context = {}

    return HttpResponse(template.render(context, request))
