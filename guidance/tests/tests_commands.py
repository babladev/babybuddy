# -*- coding: utf-8 -*-
import json
import os
import tempfile

from django.core.management import CommandError, call_command
from django.test import TestCase

from guidance.models import GuidanceEntry, Kind, Scale


class LoadGuidanceTestCase(TestCase):
    def _write_content(self, entries):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump({"version": 1, "entries": entries}, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_bundled_content_is_loaded_by_migrate(self):
        # The migrate command loads content, so the test database already has
        # it. This is the behaviour a deployment relies on.
        self.assertTrue(GuidanceEntry.objects.filter(scale=Scale.PRENATAL).exists())
        self.assertTrue(GuidanceEntry.objects.filter(scale=Scale.DAY).exists())
        self.assertTrue(GuidanceEntry.objects.filter(scale=Scale.MONTH).exists())

    def test_bundled_content_covers_the_first_month_daily(self):
        days = set(
            GuidanceEntry.objects.filter(scale=Scale.DAY).values_list(
                "period", flat=True
            )
        )
        self.assertIn(0, days)
        self.assertIn(7, days)
        self.assertIn(28, days)
        self.assertEqual(max(days), 30)

    def test_bundled_content_has_all_three_kinds(self):
        for kind in [Kind.ACTION, Kind.WATCH, Kind.RECAP]:
            self.assertTrue(
                GuidanceEntry.objects.filter(kind=kind).exists(),
                f"No bundled content of kind {kind}",
            )

    def test_reloading_updates_instead_of_duplicating(self):
        before = GuidanceEntry.objects.count()
        call_command("loadguidance", verbosity=0)
        self.assertEqual(GuidanceEntry.objects.count(), before)

    def test_changed_content_is_applied_to_existing_entries(self):
        path = self._write_content(
            [
                {
                    "slug": "day-0-skin-to-skin",
                    "scale": "day",
                    "period": 0,
                    "kind": "action",
                    "title": "Replaced title",
                    "description": "Replaced description",
                }
            ]
        )
        call_command("loadguidance", file=path, verbosity=0)
        entry = GuidanceEntry.objects.get(slug="day-0-skin-to-skin")
        self.assertEqual(entry.title, "Replaced title")

    def test_prune_removes_entries_not_in_the_file(self):
        path = self._write_content(
            [
                {
                    "slug": "only-entry",
                    "scale": "day",
                    "period": 1,
                    "kind": "action",
                    "title": "Only entry",
                }
            ]
        )
        call_command("loadguidance", file=path, prune=True, verbosity=0)
        self.assertEqual(GuidanceEntry.objects.count(), 1)
        self.assertEqual(GuidanceEntry.objects.first().slug, "only-entry")

    def test_missing_file_is_reported(self):
        with self.assertRaises(CommandError):
            call_command("loadguidance", file="/nonexistent/guidance.json")

    def test_invalid_json_is_reported(self):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        handle.write("{not json")
        handle.close()
        self.addCleanup(os.unlink, handle.name)

        with self.assertRaises(CommandError):
            call_command("loadguidance", file=handle.name)

    def test_an_entry_without_a_slug_is_rejected(self):
        path = self._write_content(
            [{"scale": "day", "period": 1, "kind": "action", "title": "No slug"}]
        )
        with self.assertRaises(CommandError):
            call_command("loadguidance", file=path, verbosity=0)
