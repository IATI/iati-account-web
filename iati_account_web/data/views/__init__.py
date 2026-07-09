"""Views for the 'data' app.

Re-exported here so callers (e.g. urls.py) can reference them as 'views.<name>'
"""

from iati_account_web.data.views.datasets import (
    create_dataset,
    dataset_delete,
    dataset_detail,
    dataset_list,
)
from iati_account_web.data.views.home import home
from iati_account_web.data.views.organisations import (
    create_organisation,
    join_reporting_org,
    organisation_delete,
    organisation_detail,
)

__all__ = [
    "home",
    "join_reporting_org",
    "organisation_detail",
    "create_organisation",
    "organisation_delete",
    "dataset_list",
    "create_dataset",
    "dataset_detail",
    "dataset_delete",
]
