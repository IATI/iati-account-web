import logging

import responses
from django.test import TestCase
from iati_account_web.tests.iati_mock import ForceIatiLoginMixin, IatiInfrastructureMock


class TestNoSuperadminAccessForRegularUsers(TestCase, ForceIatiLoginMixin):
    def setUp(self):
        self.claims = self.create_user(iati_superadmin=False)
        iati_mock = IatiInfrastructureMock()
        iati_mock.register_all()

    @responses.activate
    def test_superadmin_home_page(self):
        # Test that the user is correctly not authenticated before we force login.
        with self.assertLogs("iati_account", level="DEBUG") as cm_log_app:
            response = self.client.get("/superadmin", follow=True)
            self.assertEqual(response.redirect_chain[1], ("/identity/oidc/authenticate/", 302))
            self.assertEqual(cm_log_app.records[1].levelno, logging.DEBUG)
            self.assertIn("not authenticated", cm_log_app.records[1].msg)

        self.force_oidc_login()

        # Test that the user does not have permission and is redirected to
        # the permission denied page.
        with self.assertLogs("audit", level="DEBUG") as cm_log_audit:
            response = self.client.get("/superadmin", follow=True)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "errors/permission_denied.html")
            self.assertContains(response, "You do not have permission to access this page or perform this action")

            self.assertEqual(cm_log_audit.records[0].levelno, logging.CRITICAL)
            self.assertEqual(
                f"User {self.user.oidc_sub} ({self.user.unformatted_name}) attempted "
                "to access a superadmin page but does not have superadmin privileges",
                cm_log_audit.records[0].msg,
            )
            self.assertEqual(cm_log_audit.records[1].levelno, logging.ERROR)


class TestSuperadminAccessForSuperadminUsers(TestCase, ForceIatiLoginMixin):
    def setUp(self):
        self.claims = self.create_user(iati_superadmin=True)
        iati_mock = IatiInfrastructureMock()
        iati_mock.register_all()

    @responses.activate
    def test_superadmin_home_page(self):

        # Test that the user is correctly not authenticated before we force login.
        with self.assertLogs("iati_account", level="DEBUG") as cm_log_app:
            response = self.client.get("/superadmin", follow=True)
            self.assertEqual(response.redirect_chain[1], ("/identity/oidc/authenticate/", 302))
            self.assertEqual(cm_log_app.records[1].levelno, logging.DEBUG)
            self.assertIn("not authenticated", cm_log_app.records[1].msg)

        self.force_oidc_login()

        # Test that the user has permission and gets the superadmin home page.
        response = self.client.get("/superadmin", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "superadmin/home.html")
        self.assertContains(response, "<h2>Superadmin</h2>")
        self.assertContains(response, "<h3>Find an organisation</h3>")
        self.assertContains(response, '<a href="/en/superadmin/" class="iati-tool-nav-link">Superadmin</a>')
        self.assertIn("discoverable_reporting_orgs", response.context)
        self.assertEqual(response.context["user"].is_iati_superadmin, True)
