import json
import uuid

from django.test import TestCase
from iati_account_web.data.models import Dataset
from iati_account_web.ryd_handling.reporting_orgs import (
    parse_dataset_list_to_objects,
    parse_discoverable_org_list_to_objects,
    parse_org_list_to_objects,
    parse_user_list_to_objects,
)


class UserAndRoleTestCase(TestCase):
    def test_can_parse_from_dict(self):
        oid = str(uuid.uuid4())
        test_data = [
            {"id": str(uuid.uuid4()), "name": "Person 1", "email": "1@example.org", "role": "admin"},
            {"id": str(uuid.uuid4()), "name": None, "email": "2@example.org", "role": "editor"},
            {"id": str(uuid.uuid4()), "name": "Person 3", "email": None, "role": "contributor"},
            {"id": str(uuid.uuid4()), "name": "Person 4", "email": "4@example.org", "role": "contributor_pending"},
            {"id": str(uuid.uuid4()), "name": "Person 5", "email": "5@example.org", "role": "provider_admin"},
        ]

        users_and_roles = parse_user_list_to_objects(test_data, oid)
        self.assertEqual(len(users_and_roles), len(test_data))
        for src, obj in zip(test_data, users_and_roles):
            self.assertEqual(src["id"], obj.uid)
            self.assertEqual(oid, obj.oid)
            self.assertEqual(src["email"], obj.email)
            self.assertEqual(src["name"], obj.name)
            self.assertEqual(src["role"], obj.role)
            if src["role"] == "contributor_pending":
                self.assertTrue(obj.pending)
            else:
                self.assertFalse(obj.pending)


class ReportingOrganisationTestCase(TestCase):
    def test_can_parse_from_get_reporting_org_list(self):
        fh = open("iati_account_web/test_artefacts/ryd_responses/reporting_orgs/get_orgs_list_200.json", "r")
        api_response_data = json.load(fh)["data"]
        fh.close()

        data = parse_org_list_to_objects(api_response_data, "abcd1234-cffd-419f-942f-e6e0aa902230")

        self.assertEqual(len(data), 2)

        self.assertEqual(data[0]["org"].oid, "abcd1234-ab4e-4667-a6b6-a8424b8fd38d")
        self.assertEqual(data[0]["org"].human_readable_name, "Amundsen BA")
        self.assertEqual(data[0]["user_and_role"].uid, "abcd1234-cffd-419f-942f-e6e0aa902230")
        self.assertEqual(data[0]["user_and_role"].oid, "abcd1234-ab4e-4667-a6b6-a8424b8fd38d")
        self.assertEqual(data[0]["user_and_role"].role, "editor")

        self.assertEqual(data[1]["org"].oid, "abcd1234-b6df-4143-8895-100ec70877cd")
        self.assertEqual(data[1]["org"].human_readable_name, "Masibekela Group")
        self.assertEqual(data[1]["user_and_role"].uid, "abcd1234-cffd-419f-942f-e6e0aa902230")
        self.assertEqual(data[1]["user_and_role"].oid, "abcd1234-b6df-4143-8895-100ec70877cd")
        self.assertEqual(data[1]["user_and_role"].role, "admin")


class DiscoverableReportingOrganisationTestCase(TestCase):
    def test_can_parse_from_get_discoverable_reporting_org_list(self):
        fh = open("iati_account_web/test_artefacts/ryd_responses/discoverable_reporting_orgs/get.json", "r")
        api_response_data = json.load(fh)["data"]
        fh.close()

        data = parse_discoverable_org_list_to_objects(api_response_data, sort_list=True)

        self.assertEqual(len(data), 2)

        self.assertEqual(data[0].human_readable_name, "Amundsen BA")
        self.assertEqual(data[0].oid, "abcd1234-ab4e-4667-a6b6-a8424b8fd38d")
        self.assertEqual(data[1].human_readable_name, "Masibekela Group")
        self.assertEqual(data[1].oid, "abcd1234-b6df-4143-8895-100ec70877cd")


class DatasetModelTestCase(TestCase):
    def test_can_parse_one(self):
        test_data = {
            "id": "abcd1234-d64c-4fa1-b980-33376bc560af",
            "owner_organisation_id": "abcd1234-ab4e-4667-a6b6-a8424b8fd38d",
            "metadata": {
                "human_readable_name": "Amundsen BA Organisation File",
                "short_name": "amuba-org-file",
                "source_type": "primary_source",
                "url": "https://example.org/same-environmental.xml",
                "visibility": "public",
                "licence_id": "gpl-3.0",
                "last_url_update_date": "2025-12-08T11:39:00+00:00",
                "last_metadata_update_date": "2025-12-08T11:39:00+00:00",
            },
        }
        dataset = Dataset().from_ryd(test_data)
        self.assertEqual(dataset.dataset_id, test_data["id"])
        self.assertEqual(dataset.owner_organisation_id, test_data["owner_organisation_id"])
        self.assertEqual(dataset.human_readable_name, test_data["metadata"]["human_readable_name"])
        self.assertEqual(dataset.short_name, test_data["metadata"]["short_name"])
        self.assertEqual(dataset.source_type, test_data["metadata"]["source_type"])
        self.assertEqual(dataset.visibility, test_data["metadata"]["visibility"])
        self.assertEqual(dataset.licence_id, test_data["metadata"]["licence_id"])
        self.assertEqual(dataset.url, test_data["metadata"]["url"])
        self.assertEqual(dataset.last_url_update_date.isoformat(), test_data["metadata"]["last_url_update_date"])
        self.assertEqual(
            dataset.last_metadata_update_date.isoformat(), test_data["metadata"]["last_metadata_update_date"]
        )

    def test_can_parse_from_dict(self):
        fh = open("iati_account_web/test_artefacts/ryd_responses/reporting_orgs/get_org_datasets_200.json", "r")
        api_response_data = json.load(fh)["data"]
        fh.close()
        dataset = Dataset().from_ryd(api_response_data[0])
        self.assertEqual(dataset.dataset_id, "abcd1234-4254-486a-a632-18f148a265b1")
        self.assertEqual(dataset.human_readable_name, "Amundsen BA Activity File 2")
        self.assertEqual(dataset.owner_organisation_id, "abcd1234-ab4e-4667-a6b6-a8424b8fd38d")
        self.assertEqual(dataset.short_name, "amuba-activity-file-2")
        self.assertEqual(dataset.source_type, "")
        self.assertEqual(dataset.url, "https://example.org/focus-ball-center.xml")
        self.assertEqual(dataset.visibility, "public")
        self.assertEqual(dataset.licence_id, "")
        self.assertEqual(dataset.last_url_update_date, None)
        self.assertEqual(dataset.last_metadata_update_date, None)

    def test_can_parse_from_json_response(self):
        fh = open("iati_account_web/test_artefacts/ryd_responses/reporting_orgs/get_org_datasets_200.json", "r")
        api_response_data = json.load(fh)["data"]
        fh.close()
        datasets = parse_dataset_list_to_objects(api_response_data, sort_list=True)

        self.assertEqual(len(datasets), 3)
        self.assertEqual(datasets[0].human_readable_name, "Amundsen BA Activity File 1")
        self.assertEqual(datasets[1].human_readable_name, "Amundsen BA Activity File 2")
        self.assertEqual(datasets[2].human_readable_name, "Amundsen BA Organisation File")
