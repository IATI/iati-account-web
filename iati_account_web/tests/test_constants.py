import json
import os
import tempfile
import unittest
from pathlib import Path

from django.conf import settings

_this_dir = os.path.dirname(__file__)

_project_root = os.path.join(_this_dir, "..", "..")

if not settings.configured:
    settings.configure(
        BASE_DIR=_project_root,
        PYPROJECT_TOML_PATH=os.path.join(_project_root, "pyproject.toml"),
        COUNTRY_CODELIST_PATH=os.path.join(_project_root, "Country.json"),
        ORGANISATION_TYPE_CODELIST_PATH=os.path.join(_project_root, "OrganisationType.json"),
        REGION_CODELIST_PATH=os.path.join(_project_root, "Region.json"),
        LICENCE_PATH=os.path.join(_project_root, "Licence.json"),
        LOCALE_PATHS=(Path(_project_root) / "iati_account_web" / "locale",),
        LOGGING_CONFIG=None,
        SECRET_KEY=None,
        DEBUG=True,
    )

from iati_account_web.constants import codelist_helper  # noqa: E402


class CodelistHelperTestCase(unittest.TestCase):
    def _make_codelist_file(self, data_items: list[dict[str, str]], filter: dict[str, list[str]] | None = None):
        content = {"attributes": {}, "metadata": filter if filter is not None else {}, "data": data_items}
        file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(content, file)
        file.close()
        return file.name

    def test_populates_choice_list(self):
        path = self._make_codelist_file(
            [
                {"code": "c", "name": "Chomsky"},
                {"code": "a", "name": "Adleman"},
                {"code": "b", "name": "Babbage"},
            ]
        )
        choice_list, lookup = codelist_helper(path)

        self.assertGreater(len(choice_list), 0)
        self.assertGreater(len(lookup), 0)
        self.assertIn(("a", "Adleman"), choice_list)
        self.assertIn(("b", "Babbage"), choice_list)
        self.assertIn(("c", "Chomsky"), choice_list)

    def test_choice_list_is_sorted_by_name(self):
        path = self._make_codelist_file(
            [
                {"code": "z", "name": "Zadeh"},
                {"code": "a", "name": "Adleman"},
                {"code": "m", "name": "McCarthy"},
            ]
        )
        choice_list, lookup = codelist_helper(path)

        names = [name for code, name in choice_list if code != ""]
        self.assertEqual(names, sorted(names))

    def test_blank_entry_present_when_include_blank_true(self):
        path = self._make_codelist_file(
            [
                {"code": "c", "name": "Chomsky"},
            ]
        )
        choice_list, lookup = codelist_helper(path, include_blank=True)

        self.assertIn(("", "--"), choice_list)

    def test_blank_entry_absent_when_include_blank_false(self):
        path = self._make_codelist_file(
            [
                {"code": "c", "name": "Chomsky"},
            ]
        )
        choice_list, lookup = codelist_helper(path, include_blank=False)

        self.assertNotIn(("", "--"), choice_list)
        self.assertNotIn("", lookup)

    def test_list_is_filtered(self):
        path = self._make_codelist_file(
            [
                {"code": "a", "name": "Adleman"},
                {"code": "b", "name": "Babbage"},
                {"code": "c", "name": "Chomsky"},
            ],
            filter={"recommended": ["a", "c"]},
        )

        choice_list, lookup = codelist_helper(path, include_blank=False, filter_by_list="recommended")

        self.assertNotIn(("", "--"), choice_list)
        self.assertNotIn("", lookup)

        self.assertEqual(choice_list, [("a", "Adleman"), ("c", "Chomsky")])

    def test_display_name_used_for_choice_list_and_lookup(self):
        path = self._make_codelist_file(
            [
                {"code": "a", "name": "Adleman", "display_name": "Lovelace"},
                {"code": "b", "name": "Babbage", "display_name": "Minsky"},
            ]
        )
        choice_list, lookup = codelist_helper(path, include_blank=False, use_display_name=True)

        self.assertEqual(choice_list, [("a", "Lovelace"), ("b", "Minsky")])
        self.assertEqual(lookup, {"a": "Lovelace", "b": "Minsky"})

    def test_display_name_used_when_filtered(self):
        path = self._make_codelist_file(
            [
                {"code": "a", "name": "Adleman", "display_name": "Lovelace"},
                {"code": "b", "name": "Babbage", "display_name": "Minsky"},
                {"code": "c", "name": "Chomsky", "display_name": "Naur"},
            ],
            filter={"recommended": ["a", "c"]},
        )

        choice_list, lookup = codelist_helper(
            path, include_blank=False, filter_by_list="recommended", use_display_name=True
        )

        self.assertEqual(choice_list, [("a", "Lovelace"), ("c", "Naur")])
        self.assertEqual(lookup, {"a": "Lovelace", "b": "Minsky", "c": "Naur"})

    def test_name_used_when_use_display_name_false(self):
        path = self._make_codelist_file(
            [
                {"code": "a", "name": "Adleman", "display_name": "Lovelace"},
                {"code": "b", "name": "Babbage", "display_name": "Minsky"},
            ]
        )
        choice_list, lookup = codelist_helper(path, include_blank=False)

        self.assertEqual(choice_list, [("a", "Adleman"), ("b", "Babbage")])
        self.assertEqual(lookup, {"a": "Adleman", "b": "Babbage"})
