from urllib.parse import parse_qs, urlparse

from django.utils.translation import gettext_lazy as _


def parse_pagination_links(pagination) -> dict:
    """Parse pagination links

    Parameters
    ----------
    datasets : list[dict]
        List of datasets as obtained from Register Your Data.

    Returns
    -------
    list[Dataset]
    """
    result = {
        "page": pagination["page"],
        "page_size": pagination["page_size"],
        "total_pages": pagination["total_pages"],
        "total_records": pagination["total_records"],
    }
    for pagination_link, pagination_link_url in pagination["links"].items():
        result[f"{pagination_link}_page"] = None
        if pagination_link_url:
            query_params = parse_qs(urlparse(pagination_link_url).query)
            result[f"{pagination_link}_page"] = int(query_params["page"][0])

    result["pages"] = [
        {"label": _("Page {} of {}").format(page, result["total_pages"]), "number": page}
        for page in range(1, result["total_pages"] + 1)
    ]

    return result
