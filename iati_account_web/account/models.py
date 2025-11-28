from django.contrib.auth.models import AbstractUser
from django.db import models
from iati_account_web.settings import COUNTRY_LIST, TIMEZONE_LIST


class IATIUser(AbstractUser):
    email = models.EmailField(blank=False)
    oidc_sub = models.CharField(max_length=36, blank=False)
    unformatted_name = models.CharField(max_length=128, blank=False)
    inperson_name = models.CharField(max_length=128, blank=True)
    online_name = models.CharField(max_length=128, blank=True)
    mailinglist_subscriber = models.BooleanField(default=False)
    country = models.CharField(max_length=64, choices=COUNTRY_LIST, default="", blank=True)
    timezone = models.CharField(max_length=64, choices=TIMEZONE_LIST, default="", blank=True)
    language_en = models.BooleanField(default=False)
    language_fr = models.BooleanField(default=False)
    language_es = models.BooleanField(default=False)
    use_cases_migration = models.BooleanField(default=False)
    use_cases_publishing = models.BooleanField(default=False)
    use_cases_mailinglist = models.BooleanField(default=False)
    has_been_onboarded = models.BooleanField(default=False)
    has_been_provisioned = models.BooleanField(default=False)
    registry_id = models.CharField(max_length=36, blank=True, default="")

    @property
    def first_registration_use_cases(self) -> str:
        """Return string of first registration use cases.

        Use cases are stored in the Identity Service as a set of space-separated strings.
        This function formats the use case booleans into a string.

        Returns
        -------
        str
        """
        return " ".join(
            [
                "migration" if self.use_cases_migration else "",
                "publishing" if self.use_cases_publishing else "",
                "mailinglist" if self.use_cases_mailinglist else "",
            ]
        )

    def set_first_registration_use_cases(self, s: str) -> None:
        """Converts a string of first registration use cases into internal booleans

        Parameters
        ----------
        s : str
        """
        self.use_cases_migration = False
        self.use_cases_publishing = False
        self.use_cases_mailinglist = False
        if "migration" in s:
            self.use_cases_migration = True
        if "publishing" in s:
            self.use_cases_publishing = True
        if "mailinglist" in s:
            self.use_cases_mailinglist = True

    @property
    def languages(self) -> str:
        """Return string of preferred languages

        Use user's list of preferred languages are stored in the Identity Service as a set of
        space-separated strings. This function formats the language booleans into a string.

        Returns
        -------
        str
        """
        return " ".join(
            ["en" if self.language_en else "", "fr" if self.language_fr else "", "es" if self.language_es else ""]
        )

    def set_languages(self, s: str):
        """Converts a string of languages into internal booleans

        Parameters
        ----------
        s : str
        """
        self.language_en = False
        self.language_fr = False
        self.language_es = False
        if "en" in s:
            self.language_en = True
        if "fr" in s:
            self.language_fr = True
        if "es" in s:
            self.language_es = True
