from iati_account_web.constants import IATI_ACCOUNT_VERSION


def iati_account_data(request):
    return {"IATI_ACCOUNT_VERSION": IATI_ACCOUNT_VERSION}
