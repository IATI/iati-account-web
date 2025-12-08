import json
import uuid

from django.test import TestCase
from iati_account_web.ryd_handling.reporting_orgs import (
    parse_discoverable_org_list_to_objects,
    parse_org_list_to_objects,
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
