import json

import responses
from django.test import TestCase
from iati_account_web.ryd_handling import RegisterYourDataSession, parse_pagination_links, reporting_orgs
from iati_account_web.tests.iati_mock import IatiInfrastructureMock


class RYDHelperPaginationParserTestCase(TestCase):
    def test_can_parse_pagination_links(self):
        test_data = {
            "page": 2,
            "page_size": 100,
            "total_pages": 3,
            "total_records": 315,
            "links": {
                "first": "http://dev.api.registeryourdata.iatistandard.org/api/v1/reporting-orgs/"
                "abcd1234-ab4e-4667-a6b6-a8424b8fd38d/datasets?page=1&page_size=100",
                "last": "http://dev.api.registeryourdata.iatistandard.org/api/v1/reporting-orgs/"
                "abcd1234-ab4e-4667-a6b6-a8424b8fd38d/datasets?page=3&page_size=100",
                "next": "http://dev.api.registeryourdata.iatistandard.org/api/v1/reporting-orgs/"
                "abcd1234-ab4e-4667-a6b6-a8424b8fd38d/datasets?page=3&page_size=100",
                "prev": "http://dev.api.registeryourdata.iatistandard.org/api/v1/reporting-orgs/"
                "abcd1234-ab4e-4667-a6b6-a8424b8fd38d/datasets?page=1&page_size=100",
            },
        }

        pagination = parse_pagination_links(test_data)

        self.assertEqual(pagination["page"], 2)
        self.assertEqual(pagination["page_size"], 100)
        self.assertEqual(pagination["total_pages"], 3)
        self.assertEqual(pagination["total_records"], 315)
        self.assertEqual(pagination["first_page"], 1)
        self.assertEqual(pagination["last_page"], 3)
        self.assertEqual(pagination["next_page"], 3)
        self.assertEqual(pagination["prev_page"], 1)
        self.assertEqual(len(pagination["pages"]), 3)
        self.assertEqual(pagination["pages"][0]["number"], 1)
        self.assertEqual(pagination["pages"][1]["number"], 2)
        self.assertEqual(pagination["pages"][2]["number"], 3)

    def test_can_parse_pagination_links_from_json(self):
        fh = open("iati_account_web/test_artefacts/ryd_responses/reporting_orgs/get_org_datasets_200.json", "r")
        pagination = parse_pagination_links(json.load(fh)["pagination"])
        fh.close()
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["page_size"], 100)
        self.assertEqual(pagination["total_pages"], 1)
        self.assertEqual(pagination["total_records"], 3)
        self.assertEqual(pagination["first_page"], 1)
        self.assertEqual(pagination["last_page"], 1)
        self.assertEqual(pagination["next_page"], None)
        self.assertEqual(pagination["prev_page"], None)
        self.assertEqual(len(pagination["pages"]), 1)
        self.assertEqual(pagination["pages"][0]["number"], 1)


class RYDHelperSessionTestCase(TestCase):
    def test_can_do_strip_auth_check(self):
        self.assertEqual(
            RegisterYourDataSession._strip_auth_check(
                "https://example.org:443/api/v1/", "http://example.org:80/api/v1/"
            ),
            False,
        )
        self.assertEqual(
            RegisterYourDataSession._strip_auth_check(
                "http://example.org:80/api/v1/", "https://example.org:443/api/v1/"
            ),
            False,
        )
        self.assertEqual(
            RegisterYourDataSession._strip_auth_check("http://example.org:80/api/v1/", "https://example.org/api/v1/"),
            False,
        )
        self.assertEqual(
            RegisterYourDataSession._strip_auth_check(
                "http://example.org:80/api/v1/", "https://example.org/different_path/"
            ),
            True,
        )
        self.assertEqual(
            RegisterYourDataSession._strip_auth_check(
                "http://example.org:80/api/v1/", "https://different_domain.example.org/api/v1/"
            ),
            True,
        )


class RYDGetAllDiscoverableOrgs(TestCase):
    @responses.activate
    def test_get_all_discoverable_reporting_orgs(self):
        iati_mock = IatiInfrastructureMock(num_discoverable_reporting_orgs=2051)
        iati_mock.register_all()

        session = RegisterYourDataSession("")
        orgs = reporting_orgs.get_all_discoverable_reporting_orgs(session)
        self.assertEqual(len(orgs), 2051)
