import re
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _
from iati_account_web.constants import LICENCE_LIST_RECOMMENDED, LICENCE_LOOKUP, USER_ROLE_LOOKUP
from iati_account_web.data.models import Dataset, ReportingOrganisation, Tool, UserAndRole

ALPHA_LOWERCASE_NUMERIC_HYPHEN_REGEX = re.compile(r"^[a-z0-9-_]+$")


class OrganisationBaseForm(forms.ModelForm):
    default_licence_id = forms.ChoiceField(
        label=_("Default licence"),
        widget=forms.Select(attrs={"class": "iati-select__control"}),
    )

    def clean_data_portal_url(self):
        data_portal_url = self.cleaned_data["data_portal_url"]
        if (
            "d-portal.org" in data_portal_url
            or "iatiregistry.org" in data_portal_url
            or "aidstream.org" in data_portal_url
        ):
            raise ValidationError("Data portal should be the address of the reporting organisation's own data portal")

        return data_portal_url

    def clean_website(self):
        website = self.cleaned_data["website"]
        if "d-portal.org" in website or "iatiregistry.org" in website or "aidstream.org" in website:
            raise ValidationError("Website should be the address of the reporting organisation's main website")

        return website


class OrganisationDetailsForm(OrganisationBaseForm):
    """Form for users to view/edit details of a reporting organisation"""

    class Meta:
        model = ReportingOrganisation
        fields = "__all__"
        exclude = [
            "created_date",
            "first_publication_date",
            "number_of_published_datasets",
            "oid",
            "organisation_identifier",
            "registry_approved",
            "short_name",
        ]
        labels = {
            "address": _("Postal address"),
            "contact_email": _("Contact email address"),
            "data_portal_url": _("Data portal"),
            "description": _("Description"),
            "exclusions_policy_url": _("Exclusions policy website/document"),
            "fax": _("Fax number"),
            "hq_country": _("Country"),
            "human_readable_name": _("Organisation name"),
            "organisation_type": _("Organisation type"),
            "organisation_identifier": _("Organisation identifier"),
            "phone": _("Telephone number"),
            "region": _("Operating region"),
            "reporting_source_type": _("Reporting source type"),
            "short_name": _("Organisation short name"),
            "website": _("Website"),
        }
        error_messages = {}
        widgets = {
            "address": forms.TextInput(attrs={"class": "iati-form__input iati-account-input"}),
            "contact_email": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}
            ),
            "data_portal_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "description": forms.Textarea(),
            "exclusions_policy_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "fax": forms.TextInput(attrs={"class": "iati-form__input"}),
            "hq_country": forms.Select(attrs={"class": "iati-select__control"}),
            "human_readable_name": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}
            ),
            "organisation_type": forms.Select(attrs={"class": "iati-select__control"}),
            "organisation_identifier": forms.TextInput(attrs={"class": "iati-form__input", "disabled": "disabled"}),
            "phone": forms.TextInput(attrs={"class": "iati-form__input"}),
            "region": forms.Select(attrs={"class": "iati-select__control"}),
            "reporting_source_type": forms.Select(attrs={"class": "iati-select__control"}),
            "short_name": forms.TextInput(
                attrs={
                    "class": "iati-form__input",
                    "disabled": "disabled",
                    "style": "font-family: roboto mono; border-width: 2px !important;",
                }
            ),
            "website": forms.URLInput(attrs={"class": "iati-form__input"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        choices: list[tuple[str, str]] = list(LICENCE_LIST_RECOMMENDED)
        current: str = self.instance.default_licence_id
        if current and current not in {code for code, _ in choices}:
            choices.append((current, LICENCE_LOOKUP.get(current, current)))
        self.fields["default_licence_id"].choices = choices  # type: ignore[attr-defined]

    def get_ryd_patch_payload_from_cleaned_data(self) -> dict:
        """Generate patch payload for RYD from the cleaned data.

        Returns
        -------
        dict
        """
        return {field: self.cleaned_data[field] for field in self.changed_data}


class JoinOrganisationForm(forms.Form):
    org_id = forms.UUIDField(widget=forms.HiddenInput(), required=True)
    human_readable_name = forms.CharField(
        max_length=256,
        label=_("Organisation name"),
        widget=forms.TextInput(attrs={"class": "iati-form__input", "readonly": "readonly"}),
    )


class CreateOrganisationForm(OrganisationBaseForm):
    class Meta:
        model = ReportingOrganisation
        fields = "__all__"
        exclude = [
            "oid",
            "created_date",
            "first_publication_date",
            "number_of_published_datasets",
            "registry_approved",
        ]
        labels = {
            "address": _("Postal address"),
            "contact_email": _("Organisation Contact email address"),
            "data_portal_url": _("Data portal"),
            "description": _("Description"),
            "exclusions_policy_url": _("Link to exclusions policy"),
            "fax": _("Fax number"),
            "hq_country": _("Country"),
            "human_readable_name": _("Organisation name"),
            "organisation_type": _("Organisation type"),
            "organisation_identifier": _("Organisation identifier"),
            "phone": _("Telephone number"),
            "region": _("Operating region"),
            "reporting_source_type": _("Reporting source type"),
            "short_name": _("Organisation short name"),
            "website": _("Website"),
        }
        error_messages = {}
        widgets = {
            "address": forms.TextInput(attrs={"class": "iati-form__input"}),
            "contact_email": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}
            ),
            "data_portal_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "description": forms.Textarea(),
            "exclusions_policy_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "fax": forms.TextInput(attrs={"class": "iati-form__input"}),
            "hq_country": forms.Select(attrs={"class": "iati-select__control"}),
            "human_readable_name": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}
            ),
            "organisation_type": forms.Select(attrs={"class": "iati-select__control"}),
            "organisation_identifier": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}
            ),
            "phone": forms.TextInput(attrs={"class": "iati-form__input"}),
            "region": forms.Select(attrs={"class": "iati-select__control"}),
            "reporting_source_type": forms.Select(attrs={"class": "iati-select__control"}),
            "short_name": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "font-family: roboto mono; border-width: 2px !important;"}
            ),
            "website": forms.URLInput(attrs={"class": "iati-form__input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["default_licence_id"].choices = LICENCE_LIST_RECOMMENDED  # type: ignore

    def clean_short_name(self):
        short_name = self.cleaned_data["short_name"]
        if not ALPHA_LOWERCASE_NUMERIC_HYPHEN_REGEX.match(short_name):
            raise ValidationError(
                "Short names must contain only lowercase alphanumeric characters, hyphens, or underscores"
            )

        return short_name

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data is not None and cleaned_data.get("hq_country") == "" and cleaned_data.get("region") == "":
            self.add_error("hq_country", "Must select either a country or a region")
            self.add_error("region", "Must select either a country or a region")

        return cleaned_data

    def get_ryd_post_payload_from_cleaned_data(self):
        def _get_field(field_name: str) -> str | None:
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
            "fax": _get_field("fax"),
            "phone": _get_field("phone"),
            "website": _get_field("website"),
            "short_name": _get_field("short_name"),
            "organisation_identifier": _get_field("organisation_identifier"),
        }


class OrgUserForm(forms.ModelForm):
    class Meta:
        model = UserAndRole
        fields = "__all__"
        error_messages = {}
        widgets = {
            "name": forms.HiddenInput(),
            "email": forms.HiddenInput(),
            "uid": forms.HiddenInput(),
            "role": forms.Select(attrs={"class": "iati-select__control"}),
            "oid": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            choice for choice in self.fields["role"].choices if choice[0] not in ["provider_admin", "super_admin"]
        ]

    @property
    def get_role_display(self):
        return USER_ROLE_LOOKUP[self["role"].value()]


OrgUserFormSet = formset_factory(OrgUserForm, extra=0, can_delete=True)


class ToolForm(forms.ModelForm):
    class Meta:
        model = Tool
        # tool_id is the only form field: it round-trips (hidden) purely to
        # identify the Tool row, becuase the only operation the user can perform
        # is to revoke the tool's authorisation (DELETE). The tool name/provider
        # are display-only and rendered from the trusted server-side Tool
        # objects.
        fields = ["tool_id"]
        widgets = {
            "tool_id": forms.HiddenInput(),
        }


ToolFormSet = formset_factory(ToolForm, extra=0, can_delete=True)


class AuthoriseToolForm(forms.Form):
    """Form for authorising a new third-party tool for a reporting org.

    The selectable tools are populated at instantiation from the tools available
    via the RYD /tools endpoint, with those already authorised being removed by
    the view handler.  The choices are built from server-side data, so a
    submission which passes validation is inherently one the org is allowed to
    authorise.
    """

    tool_id = forms.ChoiceField(
        label="Tool",
        widget=forms.Select(attrs={"class": "iati-select__control"}),
    )

    def __init__(self, *args, available_tools=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tool_id"].choices = [  # type: ignore[attr-defined]
            (str(tool.tool_id), f"{tool.name} ({tool.provider})") for tool in available_tools or []
        ]


class OrganisationDeleteForm(forms.Form):
    oid = forms.UUIDField(required=True, widget=forms.HiddenInput())
    human_readable_name = forms.CharField(required=True, widget=forms.HiddenInput())
    confirm_human_readable_name = forms.CharField(
        required=True, widget=forms.TextInput(attrs={"class": "iati-form__input"})
    )


class DatasetDetailsForm(forms.ModelForm):
    licence_id = forms.ChoiceField(
        label=_("Licence"),
        widget=forms.Select(attrs={"class": "iati-select__control", "style": "border-width: 2px !important;"}),
    )

    class Meta:
        model = Dataset
        fields = "__all__"
        exclude = [
            "dataset_id",
            "last_url_update_date",
            "last_metadata_update_date",
            "owner_organisation_id",
        ]
        labels = {
            "human_readable_name": _("Dataset name"),
            "short_name": _("Dataset short name"),
            "source_type": _("Reporting source type"),
            "visibility": _("Visibility"),
            "url": _("URL"),
        }
        error_messages = {}
        widgets = {
            "human_readable_name": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}
            ),
            "short_name": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "font-family: roboto mono; border-width: 2px !important;"}
            ),
            "source_type": forms.Select(
                attrs={"class": "iati-select__control", "style": "border-width: 2px !important;"}
            ),
            "visibility": forms.Select(
                attrs={"class": "iati-select__control", "style": "border-width: 2px !important;"}
            ),
            "url": forms.URLInput(attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        choices: list[tuple[str, str]] = list(LICENCE_LIST_RECOMMENDED)
        current: str = self.instance.licence_id
        if current and current not in {code for code, _ in choices}:
            choices.append((current, LICENCE_LOOKUP.get(current, current)))
        self.fields["licence_id"].choices = choices  # type: ignore[attr-defined]

    def clean_short_name(self):
        short_name = self.cleaned_data["short_name"]
        if not ALPHA_LOWERCASE_NUMERIC_HYPHEN_REGEX.match(short_name):
            raise ValidationError(
                "Short names must contain only lowercase alphanumeric characters, hyphens, or underscores"
            )

        return short_name

    def get_ryd_patch_payload_from_cleaned_data(self, fields_editable_status: dict[str, bool]):
        def _get_field(field_name: str) -> str | None:
            return self.cleaned_data[field_name] if self.cleaned_data[field_name] else None

        return {field: _get_field(field) for field, editable in fields_editable_status.items() if editable}


class CreateDatasetForm(forms.ModelForm):
    licence_id = forms.ChoiceField(
        label=_("Licence"),
        widget=forms.Select(attrs={"class": "iati-select__control", "style": "border-width: 2px !important;"}),
    )

    class Meta:
        model = Dataset
        fields = "__all__"
        exclude = [
            "dataset_id",
            "last_url_update_date",
            "last_metadata_update_date",
            "owner_organisation_id",
        ]
        labels = {
            "human_readable_name": _("Dataset name"),
            "source_type": _("Reporting source type"),
            "short_name": _("Dataset short name"),
            "visibility": _("Visibility"),
            "url": _("URL"),
        }
        error_messages = {}
        widgets = {
            "human_readable_name": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}
            ),
            "source_type": forms.Select(
                attrs={"class": "iati-select__control", "style": "border-width: 2px !important;"}
            ),
            "short_name": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "font-family: roboto mono; border-width: 2px !important;"}
            ),
            "visibility": forms.Select(
                attrs={"class": "iati-select__control", "style": "border-width: 2px !important;"}
            ),
            "url": forms.URLInput(attrs={"class": "iati-form__input", "style": "border-width: 2px !important;"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["licence_id"].choices = LICENCE_LIST_RECOMMENDED  # type: ignore

    def clean_short_name(self):
        short_name = self.cleaned_data["short_name"]
        if not ALPHA_LOWERCASE_NUMERIC_HYPHEN_REGEX.match(short_name):
            raise ValidationError(
                "Short names must contain only lowercase alphanumeric characters, hyphens, or underscores"
            )

        return short_name


class DatasetDeleteForm(forms.Form):
    dataset_id = forms.UUIDField(required=True, widget=forms.HiddenInput())
    human_readable_name = forms.CharField(required=True, widget=forms.HiddenInput())
