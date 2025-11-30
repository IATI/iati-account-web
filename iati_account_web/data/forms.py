from django import forms
from django.utils.translation import gettext_lazy as _
from iati_account_web.settings import COUNTRY_LIST, LICENCE_LIST, ORGANISATION_TYPE_LIST, REGION_LIST


class OrganisationDetailsForm(forms.Form):
    human_readable_name = forms.CharField(
        max_length=256, label=_("Organisation name"), widget=forms.TextInput(attrs={"class": "iati-form__input"})
    )
    organisation_type = forms.ChoiceField(
        label=_("Organisation type"),
        choices=ORGANISATION_TYPE_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    hq_country = forms.ChoiceField(
        label=_("Country"),
        choices=COUNTRY_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    region = forms.ChoiceField(
        label=_("Operating region"),
        choices=REGION_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    contact_email = forms.EmailField(
        label=_("Contact email address"),
        widget=forms.TextInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    website = forms.URLField(
        label=_("Website"),
        widget=forms.URLInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    phone = forms.CharField(
        label=_("Telephone number"),
        widget=forms.TextInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    address = forms.CharField(
        label=_("Postal address"),
        widget=forms.TextInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(),
        required=False,
    )
    data_portal_url = forms.URLField(
        label=_("Publisher data portal"),
        widget=forms.URLInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    exclusions_policy_url = forms.URLField(
        label=_("Exclusions policy website/document"),
        widget=forms.URLInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    default_licence_id = forms.ChoiceField(
        label=_("Default licence"),
        choices=LICENCE_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    reporting_source_type = forms.ChoiceField(
        label=_("Reporting source type"),
        choices=[("primary_source", "Primary Source"), ("secondary_source", "Secondary Source")],
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )

    def get_ryd_patch_payload_from_cleaned_data(self):
        def _get_field(field_name: str) -> str:
            return self.cleaned_data[field_name] if self.cleaned_data[field_name] else None

        return {
            "human_readable_name": _get_field("human_readable_name"),
            "description": _get_field("description"),
            "hq_country": _get_field("hq_country"),
            "region": _get_field("region"),
            "organisation_type": _get_field("organisation_type"),
            "data_portal_url": _get_field("data_portal_url"),
            "exclusions_policy_url": _get_field("exclusions_policy_url"),
            "reporting_source_type": _get_field("reporting_source_type"),
            "default_licence_id": _get_field("default_licence_id"),
            "contact_email": _get_field("contact_email"),
            "address": _get_field("address"),
            "phone": _get_field("phone"),
            "website": _get_field("website"),
        }


class JoinOrganisationForm(forms.Form):
    org_id = forms.UUIDField(widget=forms.HiddenInput(), required=True)
    human_readable_name = forms.CharField(
        max_length=256,
        label=_("Organisation name"),
        widget=forms.TextInput(attrs={"class": "iati-form__input", "readonly": "readonly"}),
    )


class CreateOrganisationForm(forms.Form):
    human_readable_name = forms.CharField(
        max_length=256, label=_("Organisation name"), widget=forms.TextInput(attrs={"class": "iati-form__input"})
    )
    short_name = forms.CharField(
        max_length=256,
        label=_("Organisation short name"),
        widget=forms.TextInput(attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}),
        required=False,
    )
    organisation_type = forms.ChoiceField(
        label=_("Organisation type"),
        choices=ORGANISATION_TYPE_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    hq_country = forms.ChoiceField(
        label=_("Country"),
        choices=COUNTRY_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    region = forms.ChoiceField(
        label=_("Operating region"),
        choices=REGION_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    contact_email = forms.EmailField(
        label=_("Contact email address"),
        widget=forms.TextInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    website = forms.URLField(
        label=_("Website"),
        widget=forms.URLInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    phone = forms.CharField(
        label=_("Telephone number"),
        widget=forms.TextInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    address = forms.CharField(
        label=_("Postal address"),
        widget=forms.TextInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(),
        required=False,
    )
    data_portal_url = forms.URLField(
        label=_("Publisher data portal"),
        widget=forms.URLInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    exclusions_policy_url = forms.URLField(
        label=_("Exclusions policy website/document"),
        widget=forms.URLInput(attrs={"class": "iati-form__input"}),
        required=False,
    )
    default_licence_id = forms.ChoiceField(
        label=_("Default licence"),
        choices=LICENCE_LIST,
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    reporting_source_type = forms.ChoiceField(
        label=_("Reporting source type"),
        choices=[("primary_source", "Primary Source"), ("secondary_source", "Secondary Source")],
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=False,
    )
    organisation_identifier = forms.CharField(
        label=_("Organisation identifier"),
        widget=forms.TextInput(attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}),
    )

    def get_ryd_patch_payload_from_cleaned_data(self):
        def _get_field(field_name: str) -> str:
            return self.cleaned_data[field_name] if self.cleaned_data[field_name] else None

        return {
            "human_readable_name": _get_field("human_readable_name"),
            "description": _get_field("description"),
            "hq_country": _get_field("hq_country"),
            "region": _get_field("region"),
            "organisation_type": _get_field("organisation_type"),
            "data_portal_url": _get_field("data_portal_url"),
            "exclusions_policy_url": _get_field("exclusions_policy_url"),
            "reporting_source_type": _get_field("reporting_source_type"),
            "default_licence_id": _get_field("default_licence_id"),
            "contact_email": _get_field("contact_email"),
            "address": _get_field("address"),
            "phone": _get_field("phone"),
            "website": _get_field("website"),
            "short_name": _get_field("short_name"),
            "organisation_identifier": _get_field("organisation_identifier"),
        }


class OrgUserForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "iati-form__input", "readonly": "readonly"}),
    )
    email = forms.EmailField(
        required=False, widget=forms.TextInput(attrs={"class": "iati-form__input", "readonly": "readonly"})
    )
    user_id = forms.CharField(required=True, widget=forms.HiddenInput())
    role = forms.ChoiceField(
        choices=[
            ("admin", "Admin"),
            ("editor", "Editor"),
            ("contributor", "Contributor"),
            ("contributor_pending", "Pending Approval"),
            ("remove", "Remove User"),
        ],
        widget=forms.Select(attrs={"class": "iati-select__control"}),
        required=True,
    )
