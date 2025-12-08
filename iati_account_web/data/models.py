from __future__ import annotations

from datetime import datetime

from django.db import models
from iati_account_web.exceptions import RegisterYourDataResponseParsingIssue
from iati_account_web.settings import (
    COUNTRY_LIST,
    LICENCE_LIST,
    ORGANISATION_TYPE_LIST,
    REGION_LIST,
    REPORTING_SOURCE_TYPE_LIST,
    USER_ROLE_LIST,
)


class UserAndRole(models.Model):
    class Meta:
        managed = False

    uid = models.UUIDField(blank=False)
    oid = models.UUIDField(blank=False)
    email = models.EmailField(blank=True)
    role = models.CharField(choices=USER_ROLE_LIST, blank=False)
    name = models.CharField(blank=True)
    pending = models.BooleanField(default=False)

    @classmethod
    def from_ryd(cls, role_string: str, uid: str, oid: str, email: str = None, name: str = None) -> UserAndRole:
        if role_string.lower() == "contributor_pending":
            return cls(role="contributor_pending", pending=True, uid=uid, oid=oid, email=email, name=name)
        elif role_string.lower() == "provider_admin":
            return cls(role="provider_admin", pending=False, uid=uid, oid=oid, email=email, name=name)
        elif role_string.lower() == "contributor":
            return cls(role="contributor", pending=False, uid=uid, oid=oid, email=email, name=name)
        elif role_string.lower() == "editor":
            return cls(role="editor", pending=False, uid=uid, oid=oid, email=email, name=name)
        elif role_string.lower() == "admin":
            return cls(role="admin", pending=False, uid=uid, oid=oid, email=email, name=name)
        else:
            raise RegisterYourDataResponseParsingIssue(f"Cannot parse user role {role_string}")


class ReportingOrganisation(models.Model):
    class Meta:
        managed = False

    oid = models.UUIDField()
    address = models.CharField(blank=True)
    contact_email = models.EmailField()
    created_date = models.DateTimeField(blank=True)
    data_portal_url = models.URLField(blank=True)
    default_licence_id = models.CharField(choices=LICENCE_LIST, blank=True)
    description = models.CharField(blank=True)
    exclusions_policy_url = models.URLField(blank=True)
    fax = models.CharField(blank=True)
    first_publication_date = models.DateTimeField(blank=True)
    hq_country = models.CharField(choices=COUNTRY_LIST, blank=True)
    human_readable_name = models.CharField()
    number_of_published_datasets = models.IntegerField()
    organisation_identifier = models.CharField(blank=True)
    organisation_type = models.CharField(choices=ORGANISATION_TYPE_LIST, blank=True)
    phone = models.CharField(blank=True)
    region = models.CharField(choices=REGION_LIST, blank=True)
    registry_approved = models.BooleanField(default=False)
    reporting_source_type = models.CharField(choices=REPORTING_SOURCE_TYPE_LIST, blank=True)
    short_name = models.CharField(blank=True)
    website = models.URLField(blank=True)

    @classmethod
    def from_ryd_reporting_organisation(cls, reporting_org_dict: dict) -> ReportingOrganisation:
        """Parse a dictionary of reporting org data from RYD and generate a new ReportingOrganisation object

        Parameters
        ----------
        reporting_org_dict : dict
            Dictionary from RYD response.

        Returns
        -------
        ReportingOrganisation

        Raises
        ------
        RegisterYourDataResponseParsingIssue
            If there are issues in the parsing of the dictionary.
        """

        if "id" not in reporting_org_dict:
            raise RegisterYourDataResponseParsingIssue("Reporting organisation is missing its UUID")
        if "metadata" not in reporting_org_dict:
            raise RegisterYourDataResponseParsingIssue(
                f"Reporting organisation {reporting_org_dict["id"]} is missing its metadata"
            )
        metadata = reporting_org_dict.get("metadata", {})
        return cls(
            oid=reporting_org_dict["id"],
            address=metadata.get("address", None),
            contact_email=metadata.get("contact_email", None),
            created_date=metadata.get("created_date", None),
            data_portal_url=metadata.get("data_portal_url", None),
            default_licence_id=metadata.get("default_licence_id", None),
            description=metadata.get("description", None),
            exclusions_policy_url=metadata.get("exclusions_policy_url", None),
            fax=metadata.get("fax", None),
            first_publication_date=(
                datetime.fromisoformat(metadata["first_publication_date"])
                if metadata.get("first_publication_date", "")
                else None
            ),
            hq_country=metadata.get("hq_country", None),
            human_readable_name=metadata.get("human_readable_name", None),
            number_of_published_datasets=metadata.get("number_of_published_datasets", None),
            organisation_identifier=metadata.get("organisation_identifier", None),
            organisation_type=metadata.get("organisation_type", None),
            phone=metadata.get("phone", None),
            region=metadata.get("region", None),
            registry_approved=metadata.get("registry_approved", None),
            reporting_source_type=metadata.get("reporting_source_type", None),
            short_name=metadata.get("short_name", None),
            website=metadata.get("website", None),
        )

    def get_ryd_post_payload(self):
        return {
            "address": self.address if self.address else None,
            "contact_email": self.contact_email,
            "data_portal_url": self.data_portal_url if self.data_portal_url else None,
            "default_licence_id": self.default_licence_id,
            "description": self.description if self.description else None,
            "exclusions_policy_url": self.exclusions_policy_url if self.exclusions_policy_url else None,
            "fax": self.fax if self.fax else None,
            "hq_country": self.hq_country if self.hq_country else None,
            "human_readable_name": self.human_readable_name,
            "organisation_identifier": self.organisation_identifier if self.organisation_identifier else None,
            "organisation_type": self.organisation_type if self.organisation_type else None,
            "phone": self.phone if self.phone else None,
            "region": self.region,
            "reporting_source_type": self.reporting_source_type if self.address else None,
            "short_name": self.address if self.address else None,
            "website": self.address if self.address else None,
        }
