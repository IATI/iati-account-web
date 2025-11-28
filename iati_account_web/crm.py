from iati_account_web.account.models import IATIUser
from iati_account_web.settings import env
from libsuitecrm import SuiteCRM


def create_person_in_crm(user: IATIUser) -> bool:
    """Creates a person matching this user in the CRM

    Parameters
    ----------
    user : IATIUser
        Django user object.

    Returns
    -------
    bool
        True if the record was created okay, False if not.
    """
    crm = SuiteCRM(env("CRM_BASE_URL"), client_id=env("CRM_CLIENT_ID"), client_secret=env("CRM_CLIENT_SECRET"))
    crm.fetch_access_token()
    crm_id = None
    try:
        record = crm.create_record(
            "Contacts",
            {
                "last_name": user.unformatted_name,
                "email1": user.email,
                "iati_country": user.country,
                "iati_inperson_name": user.inperson_name,
                "iati_online_name": user.online_name,
                "iati_mailing_list_subscriber": user.mailinglist_subscriber,
                "iati_timezone": user.timezone,
                "iati_preferred_languages": user.languages,
                "iati_identityservice_id": user.oidc_sub,
            },
        )
        crm_id = record.get("id", None)

    except Exception as exc:  # noqa: F841
        # TODO: add logging and proper error handling.
        pass

    crm.logout()

    if crm_id is None:
        return False

    user.registry_id = crm_id
    user.save()

    return True
