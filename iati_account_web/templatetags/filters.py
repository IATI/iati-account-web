from django import template
from iati_account_web.settings import COUNTRY_CODE_LOOKUP

register = template.Library()


@register.filter
def country_from_countrycode(code: str) -> str:
    """Fetch the country name that matches a country code from the codelist.

    Example usage in a template: {{ org.hq_country|country_from_countrycode }}.

    Parameters
    ----------
    code : str
        Codelist country code.

    Returns
    -------
    str
    """
    return COUNTRY_CODE_LOOKUP.get(code, "")
