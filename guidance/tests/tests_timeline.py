# -*- coding: utf-8 -*-
import datetime

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from core.models import Child
from guidance import timeline
from guidance.models import (
    GuidanceCompletion,
    GuidanceEntry,
    Kind,
    Pregnancy,
    Scale,
)


class MonthOfLifeTestCase(TestCase):
    def test_day_of_birth_is_month_one(self):
        birth = datetime.date(2026, 1, 15)
        self.assertEqual(timeline.month_of_life(birth, birth), 1)

    def test_month_one_runs_up_to_the_first_month_birthday(self):
        birth = datetime.date(2026, 1, 15)
        self.assertEqual(timeline.month_of_life(birth, datetime.date(2026, 2, 14)), 1)
        self.assertEqual(timeline.month_of_life(birth, datetime.date(2026, 2, 15)), 2)

    def test_first_birthday_is_month_thirteen(self):
        birth = datetime.date(2026, 1, 15)
        self.assertEqual(timeline.month_of_life(birth, datetime.date(2027, 1, 15)), 13)

    def test_before_birth_is_zero(self):
        birth = datetime.date(2026, 1, 15)
        self.assertEqual(timeline.month_of_life(birth, datetime.date(2026, 1, 1)), 0)

    def test_age_in_days_counts_the_day_of_birth_as_zero(self):
        birth = datetime.date(2026, 1, 15)
        self.assertEqual(timeline.age_in_days(birth, birth), 0)
        self.assertEqual(timeline.age_in_days(birth, datetime.date(2026, 1, 22)), 7)


class ResolvePeriodTestCase(TestCase):
    """
    Content is deliberately sparse, so a date must always fall back to the
    nearest period that content exists for.
    """

    def test_counting_up_uses_the_latest_period_reached(self):
        self.assertEqual(
            timeline.resolve_period(Scale.DAY, 12, periods=[0, 7, 14, 28]), 7
        )

    def test_counting_up_falls_back_to_the_last_period_available(self):
        # Day 45 is past the end of the daily content.
        self.assertEqual(
            timeline.resolve_period(Scale.DAY, 45, periods=[0, 7, 14, 28]), 28
        )

    def test_counting_up_returns_none_before_the_first_period(self):
        self.assertIsNone(timeline.resolve_period(Scale.MONTH, 0, periods=[1, 2, 3]))

    def test_counting_down_uses_the_nearest_checkpoint_reached(self):
        # Twelve days before the due date, the 14-day checkpoint applies.
        self.assertEqual(
            timeline.resolve_period(Scale.PRENATAL, 12, periods=[1, 3, 7, 14, 21, 30]),
            14,
        )

    def test_counting_down_returns_none_when_still_too_early(self):
        self.assertIsNone(
            timeline.resolve_period(Scale.PRENATAL, 60, periods=[1, 3, 7, 14, 21, 30])
        )

    def test_counting_down_past_the_due_date_uses_the_last_checkpoint(self):
        self.assertEqual(
            timeline.resolve_period(Scale.PRENATAL, -3, periods=[1, 3, 7, 14, 21, 30]),
            1,
        )

    def test_no_content_resolves_to_none(self):
        self.assertIsNone(timeline.resolve_period(Scale.DAY, 5, periods=[]))


class ChildGuidanceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("migrate", verbosity=0)
        cls.child = Child.objects.create(
            first_name="Guidance",
            last_name="Test",
            birth_date=datetime.date(2026, 1, 15),
        )

    def test_current_day_and_month_groups_are_returned(self):
        guidance = timeline.child_guidance(self.child, datetime.date(2026, 1, 22))
        self.assertEqual(guidance["age_days"], 7)
        self.assertEqual(guidance["month"], 1)
        self.assertEqual(guidance["day_group"].period, 7)
        self.assertEqual(guidance["month_group"].period, 1)

    def test_day_group_falls_back_once_daily_content_runs_out(self):
        guidance = timeline.child_guidance(self.child, datetime.date(2026, 6, 15))
        # The bundled daily content stops at day 30.
        self.assertEqual(guidance["day_group"].period, 30)
        self.assertEqual(guidance["month_group"].period, 6)

    def test_groups_split_entries_by_kind(self):
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        self.assertTrue(group.actions)
        self.assertTrue(group.watch_for)
        self.assertTrue(group.recaps)
        for entry in group.actions:
            self.assertEqual(entry.kind, Kind.ACTION)

    def test_completion_progress_is_tracked_per_child(self):
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        self.assertEqual(group.action_completed, 0)
        self.assertFalse(group.is_complete)

        for entry in group.actions:
            GuidanceCompletion.objects.create(entry=entry, child=self.child)

        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        self.assertEqual(group.action_completed, group.action_total)
        self.assertTrue(group.is_complete)

    def test_another_child_progress_is_independent(self):
        other = Child.objects.create(
            first_name="Other",
            last_name="Child",
            birth_date=datetime.date(2026, 1, 15),
        )
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        GuidanceCompletion.objects.create(entry=group.actions[0], child=self.child)

        other_group = timeline.group_for_period(Scale.MONTH, 1, child=other)
        self.assertEqual(other_group.action_completed, 0)


class PregnancyGuidanceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("migrate", verbosity=0)

    def test_prenatal_guidance_starts_a_month_before_the_due_date(self):
        pregnancy = Pregnancy.objects.create(
            name="Baby", due_date=datetime.date(2026, 3, 1)
        )
        # Ten weeks out: nothing applies yet.
        early = timeline.pregnancy_guidance(pregnancy, datetime.date(2025, 12, 21))
        self.assertIsNone(early["group"])

        # Two weeks out: the 14-day checkpoint applies.
        near = timeline.pregnancy_guidance(pregnancy, datetime.date(2026, 2, 15))
        self.assertEqual(near["days_until_due"], 14)
        self.assertEqual(near["group"].period, 14)

    def test_a_pregnancy_linked_to_a_child_is_no_longer_active(self):
        child = Child.objects.create(
            first_name="Arrived",
            last_name="Baby",
            birth_date=datetime.date(2026, 3, 2),
        )
        pregnancy = Pregnancy.objects.create(
            due_date=datetime.date(2026, 3, 1), child=child
        )
        self.assertFalse(pregnancy.is_active)


class GuidanceEntryModelTestCase(TestCase):
    def test_prenatal_period_must_be_positive(self):
        entry = GuidanceEntry(
            slug="test-prenatal", scale=Scale.PRENATAL, period=0, title="Test"
        )
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_day_period_cannot_be_negative(self):
        entry = GuidanceEntry(slug="test-day", scale=Scale.DAY, period=-1, title="Test")
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_month_period_must_be_positive(self):
        entry = GuidanceEntry(
            slug="test-month", scale=Scale.MONTH, period=0, title="Test"
        )
        with self.assertRaises(ValidationError):
            entry.clean()

    def test_only_actions_are_checkable(self):
        self.assertTrue(
            GuidanceEntry(kind=Kind.ACTION, slug="a", period=1).is_checkable
        )
        self.assertFalse(
            GuidanceEntry(kind=Kind.RECAP, slug="b", period=1).is_checkable
        )


class GuidanceCompletionModelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.entry = GuidanceEntry.objects.create(
            slug="completion-test", scale=Scale.DAY, period=1, title="Test"
        )
        cls.child = Child.objects.create(
            first_name="Completion",
            last_name="Test",
            birth_date=datetime.date(2026, 1, 15),
        )

    def test_a_completion_needs_exactly_one_subject(self):
        with self.assertRaises(ValidationError):
            GuidanceCompletion(entry=self.entry).clean()

    def test_a_completion_cannot_have_both_subjects(self):
        pregnancy = Pregnancy.objects.create(due_date=datetime.date(2026, 3, 1))
        with self.assertRaises(ValidationError):
            GuidanceCompletion(
                entry=self.entry, child=self.child, pregnancy=pregnancy
            ).clean()

    def test_a_child_completion_is_valid(self):
        completion = GuidanceCompletion(entry=self.entry, child=self.child)
        completion.clean()
        completion.save()
        self.assertEqual(completion.subject, self.child)
