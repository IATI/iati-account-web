"""View tests for the reporting organisation_detail page (handler in organisations.py)

Basic tests for page authentication, and tests to cover the add/revoke tool
functionality.
"""

import responses
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from iati_account_web.constants import LICENCE_LIST, LICENCE_LIST_RECOMMENDED, LICENCE_LOOKUP
from iati_account_web.data.forms import OrganisationDetailsForm
from iati_account_web.data.models import ReportingOrganisation
from iati_account_web.tests.iati_mock import ForceIatiLoginMixin

RYD = settings.REGISTER_YOUR_DATA_BASE_URL

ORG_ID = "abcd1234-ab4e-4667-a6b6-a8424b8fd38d"
USER_ID = "abcd1234-cffd-419f-942f-e6e0aa902230"
TOOL_A_ID = "abcd1234-1111-4b1a-9c11-000000000001"  # authorised for the org
TOOL_B_ID = "abcd1234-2222-4b2a-9c22-000000000002"  # in the /tools catalogue, not yet authorised

REPORTING_ORG = {
    "id": ORG_ID,
    "user_role": "admin",
    "metadata": {
        "human_readable_name": "Amundsen BA",
        "short_name": "amuba",
        "contact_email": "contact@example.org",
    },
}
ORG_USERS = [{"id": USER_ID, "name": "Person One", "email": "one@example.org", "role": "admin"}]
ORG_TOOLS = [{"id": TOOL_A_ID, "name": "Tool A", "provider": "Provider A"}]
ALL_TOOLS = [
    {"id": TOOL_A_ID, "name": "Tool A", "provider": "Provider A"},
    {"id": TOOL_B_ID, "name": "Tool B", "provider": "Provider B"},
]


def _wrap_in_ryd_envelope(data):
    """Wrap 'data' in the standard RYD response envelope."""

    return {"status": "success", "error": None, "data": data}


def _make_revoke_payload(tool_id):
    """Create POST payload for the revoke authorisation action."""

    return {
        "saveToolChanges": "",
        "tools-TOTAL_FORMS": "1",
        "tools-INITIAL_FORMS": "1",
        "tools-MIN_NUM_FORMS": "0",
        "tools-MAX_NUM_FORMS": "1000",
        "tools-0-tool_id": tool_id,
        "tools-0-DELETE": "on",
    }


class OrganisationDetailViewTests(ForceIatiLoginMixin, TestCase):
    def setUp(self):
        super().setUp()
        # Provisioned + onboarded by default, so preflight_checks passes once logged in.
        self.create_user(iati_superadmin=False)
        self.url = reverse("data:reporting-org-detail", kwargs={"oid": ORG_ID})
        self.authorise_tool_url = reverse("data:authorise-tool", kwargs={"oid": ORG_ID})
        self.revoke_tool_url = reverse("data:revoke-tool", kwargs={"oid": ORG_ID})

    def _register_ryd_reads(self):
        """Register the four RYD GET endpoints the view fetches on every request."""
        responses.add(responses.GET, f"{RYD}/reporting-orgs/{ORG_ID}", json=_wrap_in_ryd_envelope(REPORTING_ORG))
        responses.add(responses.GET, f"{RYD}/reporting-orgs/{ORG_ID}/users", json=_wrap_in_ryd_envelope(ORG_USERS))
        responses.add(responses.GET, f"{RYD}/reporting-orgs/{ORG_ID}/tools", json=_wrap_in_ryd_envelope(ORG_TOOLS))
        responses.add(responses.GET, f"{RYD}/tools", json=_wrap_in_ryd_envelope(ALL_TOOLS))

    def test_organisation_detail_view_redirects_to_login_when_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("oidc_authentication_init"), fetch_redirect_response=False)

    def test_authorise_tool_redirects_to_login_when_unauthenticated(self):
        response = self.client.get(self.authorise_tool_url)
        self.assertRedirects(response, reverse("oidc_authentication_init"), fetch_redirect_response=False)

    def test_revoke_tool_redirects_to_login_when_unauthenticated(self):
        response = self.client.get(self.revoke_tool_url)
        self.assertRedirects(response, reverse("oidc_authentication_init"), fetch_redirect_response=False)

    @responses.activate
    def test_renders_page_for_authenticated_user(self):
        self._register_ryd_reads()
        self.force_oidc_login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "data/org_detail.html")
        for key in ("org_form", "user_formset", "tool_formset", "tool_rows", "authorise_tool_form"):
            self.assertIn(key, response.context)
        self.assertContains(response, "Third Party Tool Authorisations")
        self.assertContains(response, "Tool A")  # authorised tool shown in the revoke table
        self.assertContains(response, "Tool B")  # addable tool offered in the authorise dropdown

    @responses.activate
    def test_authorise_new_tool_succeeds(self):
        self._register_ryd_reads()
        responses.add(responses.POST, f"{RYD}/reporting-orgs/{ORG_ID}/tools", json=_wrap_in_ryd_envelope({}))
        self.force_oidc_login()

        response = self.client.post(self.authorise_tool_url, {"authoriseTool": "", "tool_id": TOOL_B_ID}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("successfully authorised" in str(m).lower() for m in response.context["messages"]))

    @responses.activate
    def test_authorising_a_badly_formed_tool_id_rerenders_with_error(self):
        self._register_ryd_reads()
        self.force_oidc_login()

        response = self.client.post(self.authorise_tool_url, {"authoriseTool": "", "tool_id": "not-a-valid-choice"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "data/org_detail.html")
        self.assertTrue(response.context["authorise_tool_form"].errors)

    @responses.activate
    def test_authorising_a_non_addable_tool_rerenders_with_error(self):
        self._register_ryd_reads()
        self.force_oidc_login()

        response = self.client.post(
            self.authorise_tool_url, {"authoriseTool": "", "tool_id": "225d21e1-eefb-4e57-9650-cc85b04ca89d"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "data/org_detail.html")
        self.assertTrue(response.context["authorise_tool_form"].errors)

    @responses.activate
    def test_revoking_a_tool_not_authorised_is_rejected(self):
        self._register_ryd_reads()
        self.force_oidc_login()

        # TOOL_B is in the catalogue but not authorised for this org, so revoking it is rejected.
        response = self.client.post(self.revoke_tool_url, _make_revoke_payload(TOOL_B_ID))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "errors/unknown.html")

    @responses.activate
    def test_unrecognised_post_to_edit_organisation_is_rejected(self):
        self._register_ryd_reads()
        self.force_oidc_login()

        response = self.client.post(self.url, {"somethingUnexpected": ""})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "errors/unknown.html")

    @responses.activate
    def test_unrecognised_post_to_revoke_tool_is_rejected(self):
        self._register_ryd_reads()
        self.force_oidc_login()

        response = self.client.post(self.revoke_tool_url, {"somethingUnexpected": ""})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "errors/unknown.html")

    @responses.activate
    def test_revoking_an_authorised_tool_succeeds(self):
        self._register_ryd_reads()
        responses.add(
            responses.DELETE, f"{RYD}/reporting-orgs/{ORG_ID}/tools/{TOOL_A_ID}", json=_wrap_in_ryd_envelope({})
        )
        self.force_oidc_login()

        response = self.client.post(self.revoke_tool_url, _make_revoke_payload(TOOL_A_ID), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("successfully revoked" in str(m).lower() for m in response.context["messages"]))


class OrganisationDetailsFormLicenceTests(TestCase):
    """The org edit form offers the recommended licence list plus the org's current licence.

    This keeps an org already on a non-recommended licence able to see it
    selected, keep it, and pass validation, while any code outside the offered
    set is rejected.
    """

    def _edit_form(self, current_licence):
        return OrganisationDetailsForm(instance=ReportingOrganisation(default_licence_id=current_licence))

    def _a_non_recommended_code(self):
        recommended = {code for code, _ in LICENCE_LIST_RECOMMENDED}
        return next(code for code, _ in LICENCE_LIST if code and code not in recommended)

    def test_current_non_recommended_licence_is_appended_to_recommended_list(self):
        current = self._a_non_recommended_code()

        choices = list(self._edit_form(current).fields["default_licence_id"].choices)  # type: ignore[attr-defined]

        self.assertEqual(len(choices), len(LICENCE_LIST_RECOMMENDED) + 1)
        self.assertEqual(dict(choices)[current], LICENCE_LOOKUP[current])

    def test_current_non_recommended_licence_is_accepted_but_junk_is_rejected(self):
        current = self._a_non_recommended_code()
        field = self._edit_form(current).fields["default_licence_id"]

        self.assertEqual(field.clean(current), current)
        with self.assertRaises(ValidationError):
            field.clean("not-a-real-licence")

    def test_current_recommended_licence_is_not_duplicated(self):
        current = next(code for code, _ in LICENCE_LIST_RECOMMENDED if code)

        choices = list(self._edit_form(current).fields["default_licence_id"].choices)  # type: ignore[attr-defined]

        self.assertEqual(len(choices), len(LICENCE_LIST_RECOMMENDED))
