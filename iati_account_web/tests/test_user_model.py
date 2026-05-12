from uuid import uuid4

from django.test import TestCase
from iati_account_web.account.models import IATIUser


class IATIUserModelTestCase(TestCase):
    def setUp(self):
        self.user = IATIUser.objects.create(
            username="test@example.com", email="test@example.com", oidc_sub=str(uuid4()), unformatted_name="Test User"
        )

    def test_has_complete_geolocation(self):
        self.user.country = ""
        self.user.timezone = ""
        self.assertFalse(self.user.has_complete_geolocation)

        self.user.country = "GB"
        self.user.timezone = ""
        self.assertFalse(self.user.has_complete_geolocation)

        self.user.country = ""
        self.user.timezone = "Europe/London"
        self.assertFalse(self.user.has_complete_geolocation)

        self.user.country = "GB"
        self.user.timezone = "Europe/London"
        self.assertTrue(self.user.has_complete_geolocation)

    def test_has_complete_names(self):
        self.user.unformatted_name = "Test User"

        self.user.inperson_name = ""
        self.user.online_name = ""
        self.assertFalse(self.user.has_complete_names)

        self.user.inperson_name = "Test User In Person"
        self.user.online_name = ""
        self.assertFalse(self.user.has_complete_names)

        self.user.inperson_name = ""
        self.user.online_name = "Test User Online"
        self.assertFalse(self.user.has_complete_names)

        self.user.inperson_name = "Test User In Person"
        self.user.online_name = "Test User Online"
        self.assertTrue(self.user.has_complete_names)

    def test_has_subscribed_to_mailing_lists(self):
        self.user.mailinglist_subscriber = False
        self.assertFalse(self.user.has_subscribed_to_mailing_lists)

        self.user.mailinglist_subscriber = True
        self.assertTrue(self.user.has_subscribed_to_mailing_lists)

    def test_has_complete_profile(self):
        self.user.country = "GB"
        self.user.timezone = "Europe/London"
        self.user.unformatted_name = "Test User"
        self.user.inperson_name = "Test User In Person"
        self.user.online_name = "Test User Online"
        self.assertTrue(self.user.has_complete_profile)

        self.user.country = ""
        self.assertFalse(self.user.has_complete_profile)

    def test_first_registration_use_cases_property(self):
        self.user.use_cases_migration = False
        self.user.use_cases_publishing = False
        self.user.use_cases_using_data = True
        self.user.use_cases_mailinglist = False
        self.user.use_cases_forum = True
        self.assertEqual(self.user.first_registration_use_cases, "usingdata forum")

    def test_set_first_registration_use_cases(self):
        self.user.set_first_registration_use_cases("usingdata publishing forum")

        self.assertFalse(self.user.use_cases_migration)
        self.assertTrue(self.user.use_cases_publishing)
        self.assertTrue(self.user.use_cases_using_data)
        self.assertFalse(self.user.use_cases_mailinglist)
        self.assertTrue(self.user.use_cases_forum)

    def test_languages_property(self):
        self.user.language_en = True
        self.user.language_fr = True
        self.user.language_es = False

        self.assertEqual(self.user.languages, "en fr")

    def test_set_languages(self):
        self.user.set_languages("en es")

        self.assertTrue(self.user.language_en)
        self.assertFalse(self.user.language_fr)
        self.assertTrue(self.user.language_es)

    def test_log_label(self):
        sub = "str(uuid4())"
        self.user.oidc_sub = sub
        self.user.unformatted_name = "Test User"
        self.user.registry_id = ""
        self.assertEqual(self.user.log_label, f"{sub} (Test User)")

        registry_id = str(uuid4())
        self.user.registry_id = registry_id
        self.assertEqual(self.user.log_label, f"{sub} (Test User) [crm id {registry_id}]")

    def test_update_from_claims(self):
        claims = {
            "sub": "0500120b-537e-4270-93b3-f6512111eb17",
            "name": "Updated Name",
            "email": "updated@example.com",
            "iatiInPersonName": "Updated In Person",
            "iatiOnlineName": "updated_online",
            "iatiMailingList": "true",
            "iatiPreferredLanguage": "fr",
            "iatiCountry": "FR",
            "iatiTimeZone": "Europe/Paris",
            "iatiFirstRegistrationUseCases": "usingdata",
            "iatiHasBeenOnboarded": "true",
            "iatiRegistryId": "1dc1504b-67c9-4885-90a6-eed058409c0c",
            "iatiHasBeenProvisioned": "true",
            "roles": ["Internal/iati_superadmin"],
        }

        self.user.update_from_claims(claims, include_sub=True)

        self.assertEqual(self.user.oidc_sub, "0500120b-537e-4270-93b3-f6512111eb17")
        self.assertEqual(self.user.unformatted_name, "Updated Name")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.inperson_name, "Updated In Person")
        self.assertEqual(self.user.online_name, "updated_online")
        self.assertTrue(self.user.mailinglist_subscriber)
        self.assertFalse(self.user.language_en)
        self.assertTrue(self.user.language_fr)
        self.assertEqual(self.user.country, "FR")
        self.assertEqual(self.user.timezone, "Europe/Paris")
        self.assertTrue(self.user.use_cases_using_data)
        self.assertTrue(self.user.has_been_onboarded)
        self.assertEqual(self.user.registry_id, "1dc1504b-67c9-4885-90a6-eed058409c0c")
        self.assertTrue(self.user.has_been_provisioned)
        self.assertTrue(self.user.is_iati_superadmin)

    def test_update_from_claims_exclude_sub(self):
        claims = {"sub": "ab4ed844-544f-4eea-ab51-b59d39155ed1", "name": "Another Name"}
        old_sub = self.user.oidc_sub
        self.user.update_from_claims(claims, include_sub=False)
        self.assertEqual(self.user.oidc_sub, old_sub)
        self.assertEqual(self.user.unformatted_name, "Another Name")
