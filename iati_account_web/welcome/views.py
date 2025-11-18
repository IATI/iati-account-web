from django.http import HttpRequest, HttpResponse
from django.template import loader


def index(request: HttpRequest) -> HttpResponse:

    if request.user.is_authenticated:
        template = loader.get_template("welcome/home.html")
        print(f"OIDC Access Token: {request.session.get("oidc_access_token", None)}")
        context = {"claims": request.session.get("claims", {})}
    else:
        template = loader.get_template("welcome/index.html")
        context = {}

    return HttpResponse(template.render(context, request))
