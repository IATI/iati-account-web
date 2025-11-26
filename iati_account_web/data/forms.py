from django import forms
from django.utils.translation import gettext_lazy as _
from iati_account_web.settings import COUNTRY_LIST, LICENCE_LIST, ORGANISATION_TYPE_LIST, REGION_LIST


class OrganisationDetailsForm(forms.Form):
    human_readable_name = forms.CharField(
        max_length=256, label=_("Organisation name"), widget=forms.TextInput(attrs={"class": "iati-form__input"})
    )
    short_name = forms.CharField(
        max_length=256,
        label=_("Organisation short name"),
        widget=forms.TextInput(attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}),
        disabled=True,
    )
    organisation_type = forms.ChoiceField(
        label=_("Organisation type"),
        choices=ORGANISATION_TYPE_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
    )
    hq_country = forms.ChoiceField(
        label=_("Country"), choices=COUNTRY_LIST, widget=forms.Select(attrs={"class": "iati-select__control"})
    )
    region = forms.ChoiceField(
        label=_("Operating region"), choices=REGION_LIST, widget=forms.Select(attrs={"class": "iati-select__control"})
    )
    contact_email = forms.EmailField(
        label=_("Contact email address"), widget=forms.TextInput(attrs={"class": "iati-form__input"})
    )
    website = forms.URLField(label=_("Website"), widget=forms.URLInput(attrs={"class": "iati-form__input"}))
    phone = forms.CharField(label=_("Telephone number"), widget=forms.TextInput(attrs={"class": "iati-form__input"}))
    address = forms.CharField(label=_("Postal address"), widget=forms.TextInput(attrs={"class": "iati-form__input"}))
    description = forms.CharField(label=_("Description"), widget=forms.Textarea())
    data_portal_url = forms.URLField(
        label=_("Publisher data portal"), widget=forms.URLInput(attrs={"class": "iati-form__input"})
    )
    exclusions_policy_url = forms.URLField(
        label=_("Exclusions policy website/document"), widget=forms.URLInput(attrs={"class": "iati-form__input"})
    )
    default_licence_id = forms.ChoiceField(
        label=_("Default licence"),
        choices=LICENCE_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
    )
    reporting_source_type = forms.ChoiceField(
        label=_("Reporting source type"),
        choices=[("primary_source", "Primary Source"), ("secondary_source", "Secondary Source")],
        widget=forms.Select(attrs={"class": "iati-select__control"}),
    )
    organisation_identifier = forms.CharField(
        label=_("Organisation identifier"),
        widget=forms.TextInput(attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}),
        disabled=True,
    )
