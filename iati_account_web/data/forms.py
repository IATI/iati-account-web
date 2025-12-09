from django import forms
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _
from iati_account_web.data.models import Dataset, ReportingOrganisation, UserAndRole


class OrganisationDetailsForm(forms.ModelForm):
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
            "data_portal_url": _("Publisher data portal"),
            "default_licence_id": _("Default licence"),
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
            "address": forms.TextInput(attrs={"class": "iati-form__input"}),
            "contact_email": forms.TextInput(attrs={"class": "iati-form__input"}),
            "data_portal_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "default_licence_id": forms.Select(attrs={"class": "iati-select__control"}),
            "description": forms.Textarea(),
            "exclusions_policy_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "fax": forms.TextInput(attrs={"class": "iati-form__input"}),
            "hq_country": forms.Select(attrs={"class": "iati-select__control"}),
            "human_readable_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "organisation_type": forms.Select(attrs={"class": "iati-select__control"}),
            "organisation_identifier": forms.TextInput(attrs={"class": "iati-form__input", "disabled": "disabled"}),
            "phone": forms.TextInput(attrs={"class": "iati-form__input"}),
            "region": forms.Select(attrs={"class": "iati-select__control"}),
            "reporting_source_type": forms.Select(attrs={"class": "iati-select__control"}),
            "short_name": forms.TextInput(
                attrs={"class": "iati-form__input", "disabled": "disabled", "style": "font-family: roboto mono;"}
            ),
            "website": forms.URLInput(attrs={"class": "iati-form__input"}),
        }

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


class CreateOrganisationForm(forms.ModelForm):
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
            "contact_email": _("Contact email address"),
            "data_portal_url": _("Publisher data portal"),
            "default_licence_id": _("Default licence"),
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
            "address": forms.TextInput(attrs={"class": "iati-form__input"}),
            "contact_email": forms.TextInput(attrs={"class": "iati-form__input"}),
            "data_portal_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "default_licence_id": forms.Select(attrs={"class": "iati-select__control"}),
            "description": forms.Textarea(),
            "exclusions_policy_url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "fax": forms.TextInput(attrs={"class": "iati-form__input"}),
            "hq_country": forms.Select(attrs={"class": "iati-select__control"}),
            "human_readable_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "organisation_type": forms.Select(attrs={"class": "iati-select__control"}),
            "organisation_identifier": forms.TextInput(
                attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}
            ),
            "phone": forms.TextInput(attrs={"class": "iati-form__input"}),
            "region": forms.Select(attrs={"class": "iati-select__control"}),
            "reporting_source_type": forms.Select(attrs={"class": "iati-select__control"}),
            "short_name": forms.TextInput(attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}),
            "website": forms.URLInput(attrs={"class": "iati-form__input"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("hq_country") == "" and cleaned_data.get("region") == "":
            self.add_error("hq_country", "Must select either a country or a region")
            self.add_error("region", "Must select either a country or a region")

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


OrgUserFormSet = formset_factory(OrgUserForm, extra=0, can_delete=True)


class OrganisationDeleteForm(forms.Form):
    oid = forms.UUIDField(required=True, widget=forms.HiddenInput())
    human_readable_name = forms.CharField(required=True, widget=forms.HiddenInput())
    confirm_human_readable_name = forms.CharField(
        required=True, widget=forms.TextInput(attrs={"class": "iati-form__input"})
    )


class DatasetDetailsForm(forms.ModelForm):
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
            "licence_id": _("Licence"),
        }
        error_messages = {}
        widgets = {
            "human_readable_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "short_name": forms.TextInput(attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}),
            "source_type": forms.Select(attrs={"class": "iati-select__control"}),
            "visibility": forms.Select(attrs={"class": "iati-select__control"}),
            "url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "licence_id": forms.Select(attrs={"class": "iati-select__control"}),
        }

    def get_ryd_patch_payload_from_cleaned_data(self):
        def _get_field(field_name: str) -> str:
            return self.cleaned_data[field_name] if self.cleaned_data[field_name] else None

        return {
            "human_readable_name": _get_field("human_readable_name"),
            "licence_id": _get_field("licence_id"),
            "short_name": _get_field("short_name"),
            "source_type": _get_field("source_type"),
            "url": _get_field("url"),
        }


class CreateDatasetForm(forms.ModelForm):
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
            "licence_id": _("Licence"),
        }
        error_messages = {}
        widgets = {
            "human_readable_name": forms.TextInput(attrs={"class": "iati-form__input"}),
            "source_type": forms.Select(attrs={"class": "iati-select__control"}),
            "short_name": forms.TextInput(attrs={"class": "iati-form__input", "style": "font-family: roboto mono;"}),
            "visibility": forms.Select(attrs={"class": "iati-select__control"}),
            "url": forms.URLInput(attrs={"class": "iati-form__input"}),
            "licence_id": forms.Select(attrs={"class": "iati-select__control"}),
        }


class DatasetDeleteForm(forms.Form):
    dataset_id = forms.UUIDField(required=True, widget=forms.HiddenInput())
    human_readable_name = forms.CharField(required=True, widget=forms.HiddenInput())
