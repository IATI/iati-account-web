import urllib.parse

from django.conf import settings
from django.shortcuts import reverse
from django.test import TestCase
from iati_account_web.oidc.utils import generate_username, logout_uri


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
