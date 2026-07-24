# -*- coding: utf-8 -*-
import datetime

from django.test import TestCase
from django.utils import timezone

from core.models import DiaperChange, Feeding, Sleep, TummyTime, Weight
from core.models import Child
from guidance import recap


class MonthRangeTestCase(TestCase):
    def test_month_one_starts_at_birth(self):
        birth = datetime.date(2026, 1, 15)
        start, end = recap.month_range(birth, 1)
        self.assertEqual(start, birth)
        self.assertEqual(end, datetime.date(2026, 2, 15))

    def test_later_months_follow_calendar_months(self):
        birth = datetime.date(2026, 1, 15)
        start, end = recap.month_range(birth, 3)
        self.assertEqual(start, datetime.date(2026, 3, 15))
        self.assertEqual(end, datetime.date(2026, 4, 15))


class MonthRecapTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.birth = datetime.date(2026, 1, 15)
        cls.child = Child.objects.create(
            first_name="Recap", last_name="Test", birth_date=cls.birth
        )
        cls.inside = timezone.make_aware(
            datetime.datetime(2026, 1, 20, 12, 0), timezone.get_current_timezone()
        )
        cls.outside = timezone.make_aware(
            datetime.datetime(2026, 3, 20, 12, 0), timezone.get_current_timezone()
        )

    def test_empty_month_reports_no_data(self):
        result = recap.month_recap(self.child, 1, datetime.date(2026, 2, 20))
        self.assertFalse(result["has_data"])
        self.assertEqual(result["feeding_count"], 0)

    def test_logged_data_is_counted(self):
        Feeding.objects.create(
            child=self.child,
            start=self.inside,
            end=self.inside + datetime.timedelta(minutes=20),
            type="breast milk",
            method="left breast",
            amount=60,
        )
        DiaperChange.objects.create(
            child=self.child, time=self.inside, wet=True, solid=False
        )
        DiaperChange.objects.create(
            child=self.child, time=self.inside, wet=True, solid=True
        )
        Sleep.objects.create(
            child=self.child,
            start=self.inside,
            end=self.inside + datetime.timedelta(hours=2),
        )
        TummyTime.objects.create(
            child=self.child,
            start=self.inside,
            end=self.inside + datetime.timedelta(minutes=5),
        )

        result = recap.month_recap(self.child, 1, datetime.date(2026, 2, 20))
        self.assertTrue(result["has_data"])
        self.assertEqual(result["feeding_count"], 1)
        self.assertEqual(result["feeding_amount"], 60)
        self.assertEqual(result["change_count"], 2)
        self.assertEqual(result["change_wet_count"], 2)
        self.assertEqual(result["change_solid_count"], 1)
        self.assertEqual(result["sleep_total"], datetime.timedelta(hours=2))
        self.assertEqual(result["tummy_time_total"], datetime.timedelta(minutes=5))

    def test_data_from_other_months_is_excluded(self):
        Feeding.objects.create(
            child=self.child,
            start=self.outside,
            end=self.outside + datetime.timedelta(minutes=20),
            type="breast milk",
            method="left breast",
        )
        result = recap.month_recap(self.child, 1, datetime.date(2026, 2, 20))
        self.assertEqual(result["feeding_count"], 0)

    def test_weight_change_is_reported_across_the_month(self):
        Weight.objects.create(
            child=self.child, date=datetime.date(2026, 1, 16), weight=3.2
        )
        Weight.objects.create(
            child=self.child, date=datetime.date(2026, 2, 10), weight=4.1
        )
        result = recap.month_recap(self.child, 1, datetime.date(2026, 2, 20))
        self.assertAlmostEqual(result["weight_change"], 0.9, places=3)

    def test_a_single_weight_has_no_change(self):
        Weight.objects.create(
            child=self.child, date=datetime.date(2026, 1, 16), weight=3.2
        )
        result = recap.month_recap(self.child, 1, datetime.date(2026, 2, 20))
        self.assertIsNone(result["weight_change"])

    def test_a_month_in_progress_is_marked_partial(self):
        result = recap.month_recap(self.child, 1, datetime.date(2026, 1, 20))
        self.assertTrue(result["is_partial"])
        self.assertEqual(result["days_elapsed"], 6)

    def test_a_finished_month_is_not_partial(self):
        result = recap.month_recap(self.child, 1, datetime.date(2026, 3, 1))
        self.assertFalse(result["is_partial"])
        self.assertEqual(result["days_elapsed"], 31)

    def test_daily_sleep_average_is_scaled_to_elapsed_days(self):
        Sleep.objects.create(
            child=self.child,
            start=self.inside,
            end=self.inside + datetime.timedelta(hours=12),
        )
        result = recap.month_recap(self.child, 1, datetime.date(2026, 1, 20))
        # Six days elapsed, twelve hours logged.
        self.assertEqual(result["sleep_daily_average"], datetime.timedelta(hours=2))
