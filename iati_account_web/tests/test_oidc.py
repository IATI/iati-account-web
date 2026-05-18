import unittest
import urllib.parse
from typing import Any

import responses
from django.conf import settings
from django.shortcuts import reverse
from django.test import TestCase
from iati_account_web.oidc.discovery import LazyOpenIdConfiguration, get_openid_configuration
from iati_account_web.oidc.utils import generate_username, logout_uri
from parameterized import parameterized


class OIDCTestCase(TestCase):
    def test_username_generation_from_claims(self):
        self.assertEqual(
            generate_username("user@example.org", {"email": "username@example.org"}), "username@example.org"
        )

    def test_logout_uri_generation(self):
        params = urllib.parse.urlencode(
            {
                "client_id": settings.OIDC_RP_CLIENT_ID,
                "post_logout_redirect_uri": urllib.parse.urljoin("http://localhost:8443", reverse("logout")),
            }
        )
        self.assertEqual(logout_uri(None), "https://testing.idp/t/test/oidc/logout?" + params)


class OpenIDConfigTestCase(unittest.TestCase):
    def setUp(self):
        responses.reset()

    @parameterized.expand(
        [
            (
                "https://example.org/oauth/token/.well-known/openid-configuration-okay",
                {
                    "authorization_endpoint": "auth",
                    "token_endpoint": "token",
                    "userinfo_endpoint": "userinfo",
                    "jwks_uri": "jwks",
                    "end_session_endpoint": "end_session",
                },
            ),
        ]
    )
    @responses.activate
    def test_okay(self, url: str, json_body: dict[str, Any]):
        responses.add(method=responses.GET, url=url, json=json_body, status=200)

        config = get_openid_configuration(url)
        for key in json_body.keys():
            self.assertIn(key, config)
            self.assertNotEqual(config[key], "")
            self.assertEqual(config[key], json_body[key])

    @parameterized.expand(
        [
            (
                "https://example.org/oauth/token/.well-known/openid-configuration-missing-auth",
                ["token_endpoint", "userinfo_endpoint", "jwks_uri", "end_session_endpoint"],
                "authorization_endpoint",
            ),
            (
                "https://example.org/oauth/token/.well-known/openid-configuration-missing-token",
                ["authorization_endpoint", "userinfo_endpoint", "jwks_uri", "end_session_endpoint"],
                "token_endpoint",
            ),
            (
                "https://example.org/oauth/token/.well-known/openid-configuration-missing-userinfo",
                ["authorization_endpoint", "token_endpoint", "userinfo_endpoint", "end_session_endpoint"],
                "jwks_uri",
            ),
            (
                "https://example.org/oauth/token/.well-known/openid-configuration-missing-jwks",
                ["authorization_endpoint", "token_endpoint", "jwks_uri", "end_session_endpoint"],
                "userinfo_endpoint",
            ),
            (
                "https://example.org/oauth/token/.well-known/openid-configuration-missing-endsession",
                ["authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri"],
                "end_session_endpoint",
            ),
        ]
    )
    @responses.activate
    def test_missing_keys(self, url: str, present_keys: dict[str, Any], missing_key: str):
        responses.add(method=responses.GET, url=url, json={key: "abcdef" for key in present_keys}, status=200)

        with self.assertRaises(RuntimeError) as cm:
            get_openid_configuration(url)

        self.assertIn("OpenID configuration doesn't have the required fields: missing", repr(cm.exception))
        self.assertIn(missing_key, repr(cm.exception))

    @responses.activate
    def test_404(self):
        responses.add(
            method=responses.GET,
            url="https://example.org/oauth/token/.well-known/openid-configuration-notfound",
            status=404,
        )

        with self.assertRaises(RuntimeError) as cm:
            get_openid_configuration("https://example.org/oauth/token/.well-known/openid-configuration-notfound")

        self.assertIn("Cannot get OpenID configuration", repr(cm.exception))

    @responses.activate
    def test_lazy_initialisation(self):
        DISCOVERY_ENDPOINT_URL = "https://example.org/.well-known/openid-configuration"
        OIDC_CONFIG = {
            "authorization_endpoint": "auth",
            "token_endpoint": "token",
            "userinfo_endpoint": "userinfo",
            "jwks_uri": "jwks",
            "end_session_endpoint": "end_session",
        }
        responses.add(
            method=responses.GET,
            url=DISCOVERY_ENDPOINT_URL,
            status=200,
            json=OIDC_CONFIG,
        )
        authorization_endpoint = LazyOpenIdConfiguration("authorization_endpoint", DISCOVERY_ENDPOINT_URL)
        token_endpoint = LazyOpenIdConfiguration("token_endpoint", DISCOVERY_ENDPOINT_URL)
        userinfo_endpoint = LazyOpenIdConfiguration("userinfo_endpoint", DISCOVERY_ENDPOINT_URL)
        jwks_uri = LazyOpenIdConfiguration("jwks_uri", DISCOVERY_ENDPOINT_URL)

        # The first assertion forces an access of the parameter.  After this all the parameters should be initialised.
        self.assertEqual(str(authorization_endpoint), OIDC_CONFIG["authorization_endpoint"])
        self.assertEqual(str(token_endpoint), OIDC_CONFIG["token_endpoint"])
        self.assertEqual(str(userinfo_endpoint), OIDC_CONFIG["userinfo_endpoint"])
        self.assertEqual(str(jwks_uri), OIDC_CONFIG["jwks_uri"])

        # Check trying to change the URL.
        with self.assertRaises(RuntimeError) as cm:
            end_session_endpoint = LazyOpenIdConfiguration("end_session_endpoint", "https://example.org/.different")  # noqa: F841

        self.assertIn("There is a conflict between the existing discovery endpoint", repr(cm.exception))
        self.assertIn("https://example.org/.different", repr(cm.exception))
        self.assertIn("https://example.org/.well-known/openid-configuration", repr(cm.exception))
