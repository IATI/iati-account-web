from django.http import HttpRequest
from iati_account_web.account.models import IATIUser


class AuthedHttpRequest(HttpRequest):
    user: IATIUser  # class-level annotation only — no value assigned
