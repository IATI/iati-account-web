import json

from django.test import TestCase
from iati_account_web.exceptions_middleware import IATIAccountExceptionHandlerMiddleware
from iati_account_web.ryd_handling import RegisterYourDataSession, parse_pagination_links


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


class ExceptionHandlerTestCase(TestCase):
    def setUp(self):
        self.handler = IATIAccountExceptionHandlerMiddleware(lambda x: None)

    def test_tracking_code_length(self):
        # Check range of times from 1970-01-02 to 2040-01-01.
        for t in [86400000, 1735693200000, 1893459600000, 2051226000000, 2208992400000]:
            with self.subTest():
                self.assertEqual(len(self.handler._generate_error_tracking_code(time_ms=t)), 19)

    def test_tracking_code_early_date_zero_padding(self):
        # Check zero-padding of 1970-01-02.
        self.assertEqual(self.handler._generate_error_tracking_code(time_ms=86400000)[0:2], "00")

    def test_tracking_codes_have_invertible_times(self):
        for t in [1735693200000, 1893459600000, 2051226000000, 2208992400000, 86400000]:
            with self.subTest():
                tracking_code = self.handler._generate_error_tracking_code(t)
                tracking_code_time = tracking_code[0:4] + tracking_code[5:9]
                self.assertEqual(int(tracking_code_time, 36), t)
