from django import forms
from django.utils.translation import get_language_info
from django.utils.translation import gettext_lazy as _
from iati_account_web.account.models import IATIUser


class AccountSelfServiceForm(forms.ModelForm):
    class Meta:
        model = IATIUser

        fields = [
            "unformatted_name",
            "inperson_name",
            "online_name",
            "mailinglist_subscriber",
            "language_en",
            "language_fr",
            "language_es",
            "country",
            "timezone",
        ]

        labels = {
            "unformatted_name": _("Name"),
            "online_name": _("How do you want to be called online?"),
            "inperson_name": _("How do you want to be called in-person, for example at an IATI event?"),
            "mailinglist_subscriber": _("General mailing list"),
            "language_en": get_language_info("en")["name_translated"],
            "language_fr": get_language_info("fr")["name_translated"],
            "language_es": get_language_info("es")["name_translated"],
            "country": _("Country"),
            "timezone": _("Time Zone"),
        }

        widgets = {
            "unformatted_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "online_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "inperson_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "mailinglist_subscriber": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "language_en": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "language_fr": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "language_es": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "country": forms.Select(attrs={"class": "iati-select__control"}),
            "timezone": forms.Select(attrs={"class": "iati-select__control"}),
        }


class AccountOnboardingForm(forms.ModelForm):
    class Meta:
        model = IATIUser

        fields = [
            "unformatted_name",
            "inperson_name",
            "online_name",
            "mailinglist_subscriber",
            "language_en",
            "language_fr",
            "language_es",
            "country",
            "timezone",
            "use_cases_publishing",
            "use_cases_mailinglist",
        ]

        labels = {
            "unformatted_name": _("Name"),
            "online_name": _("How do you want to be called online?"),
            "inperson_name": _("How do you want to be called in-person, for example at an IATI event?"),
            "mailinglist_subscriber": _("General mailing list"),
            "language_en": get_language_info("en")["name_translated"],
            "language_fr": get_language_info("fr")["name_translated"],
            "language_es": get_language_info("es")["name_translated"],
            "country": _("Country"),
            "timezone": _("Time Zone"),
            "use_cases_publishing": _("Publishing IATI Data"),
            "use_cases_mailinglist": _("Join the IATI mailing list"),
        }

        widgets = {
            "unformatted_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "online_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "inperson_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "mailinglist_subscriber": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "language_en": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "language_fr": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "language_es": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "country": forms.Select(attrs={"class": "iati-select__control"}),
            "timezone": forms.Select(attrs={"class": "iati-select__control"}),
            "use_cases_publishing": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
            "use_cases_mailinglist": forms.CheckboxInput(attrs={"class": "iati-form__input"}),
        }
