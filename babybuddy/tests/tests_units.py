# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client as HttpClient, TestCase

from faker import Faker

from babybuddy import units
from core.models import Child, Weight


class UnitConversionTestCase(TestCase):
    """
    Values are stored in metric. Conversion happens only at the edges.
    """

    def test_metric_is_stored_unchanged(self):
        self.assertEqual(units.to_display(units.WEIGHT, 3.6, units.METRIC), 3.6)
        self.assertEqual(units.to_storage(units.WEIGHT, 3.6, units.METRIC), 3.6)

    def test_weight_converts_to_pounds(self):
        self.assertAlmostEqual(
            units.to_display(units.WEIGHT, 1, units.US), 2.2046, places=3
        )

    def test_length_converts_to_inches(self):
        self.assertAlmostEqual(
            units.to_display(units.LENGTH, 2.54, units.US), 1.0, places=4
        )

    def test_volume_converts_to_fluid_ounces(self):
        self.assertAlmostEqual(
            units.to_display(units.VOLUME, 29.5735, units.US), 1.0, places=4
        )

    def test_temperature_conversion_is_affine(self):
        self.assertAlmostEqual(
            units.to_display(units.TEMPERATURE, 0, units.US), 32.0, places=4
        )
        self.assertAlmostEqual(
            units.to_display(units.TEMPERATURE, 37, units.US), 98.6, places=4
        )
        self.assertAlmostEqual(
            units.to_storage(units.TEMPERATURE, 98.6, units.US), 37.0, places=4
        )

    def test_conversions_round_trip(self):
        for kind in [units.WEIGHT, units.LENGTH, units.VOLUME, units.TEMPERATURE]:
            with self.subTest(kind=kind):
                stored = units.to_storage(kind, 12.5, units.US)
                self.assertAlmostEqual(
                    units.to_display(kind, stored, units.US), 12.5, places=6
                )

    def test_none_stays_none(self):
        self.assertIsNone(units.to_display(units.WEIGHT, None, units.US))
        self.assertIsNone(units.to_storage(units.WEIGHT, None, units.US))
        self.assertEqual(units.format_value(units.WEIGHT, None), "")

    def test_formatting_includes_the_unit(self):
        self.assertEqual(units.format_value(units.WEIGHT, 3.6, units.METRIC), "3.6 kg")
        self.assertEqual(units.format_value(units.TEMPERATURE, 37, units.US), "98.6 °F")

    def test_formatting_drops_meaningless_decimals(self):
        self.assertEqual(units.format_value(units.VOLUME, 60, units.METRIC), "60 ml")
        self.assertEqual(
            units.format_value(units.WEIGHT, 3.625, units.METRIC), "3.625 kg"
        )

    def test_formatting_can_omit_the_unit(self):
        self.assertEqual(
            units.format_value(units.WEIGHT, 3.6, units.METRIC, with_unit=False),
            "3.6",
        )

    def test_axis_label(self):
        self.assertEqual(
            units.axis_label("Weight", units.WEIGHT, units.US), "Weight (lb)"
        )

    def test_convert_list(self):
        converted = units.convert_list(units.TEMPERATURE, [0, 100], units.US)
        self.assertEqual(converted, [32.0, 212.0])


class UnitSystemSettingTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("migrate", verbosity=0)

    def tearDown(self):
        Child.settings.unit_system = units.METRIC

    def test_metric_is_the_default(self):
        self.assertEqual(units.unit_system(), units.METRIC)

    def test_setting_selects_the_system(self):
        Child.settings.unit_system = units.US
        self.assertEqual(units.unit_system(), units.US)
        self.assertEqual(units.abbreviation(units.WEIGHT), "lb")

    def test_an_unrecognised_value_falls_back_to_metric(self):
        Child.settings.unit_system = "cubits"
        self.assertEqual(units.unit_system(), units.METRIC)


class MeasurementFormTestCase(TestCase):
    """
    Forms accept and display values in the configured unit system while the
    database keeps metric.
    """

    @classmethod
    def setUpClass(cls):
        super(MeasurementFormTestCase, cls).setUpClass()
        fake = Faker()
        call_command("migrate", verbosity=0)

        fake_user = fake.simple_profile()
        cls.credentials = {
            "username": fake_user["username"],
            "password": fake.password(),
        }
        cls.user = get_user_model().objects.create_user(
            is_superuser=True, **cls.credentials
        )

    def setUp(self):
        self.c = HttpClient()
        self.c.login(**self.credentials)
        self.child = Child.objects.create(
            first_name="Units",
            last_name="Test",
            birth_date=datetime.date.today() - datetime.timedelta(days=30),
        )

    def tearDown(self):
        Child.settings.unit_system = units.METRIC

    def test_metric_entry_is_stored_as_entered(self):
        page = self.c.post(
            "/weight/add/",
            {
                "child": self.child.id,
                "weight": "3.6",
                "date": datetime.date.today().isoformat(),
            },
        )
        self.assertEqual(page.status_code, 302)
        self.assertAlmostEqual(Weight.objects.get().weight, 3.6, places=3)

    def test_us_entry_is_converted_to_metric(self):
        Child.settings.unit_system = units.US
        page = self.c.post(
            "/weight/add/",
            {
                "child": self.child.id,
                "weight": "8",
                "date": datetime.date.today().isoformat(),
            },
        )
        self.assertEqual(page.status_code, 302)
        # Eight pounds is about 3.629 kg.
        self.assertAlmostEqual(Weight.objects.get().weight, 3.6287, places=3)

    def test_form_label_shows_the_unit(self):
        page = self.c.get("/weight/add/")
        self.assertContains(page, "Weight (kg)")

        Child.settings.unit_system = units.US
        page = self.c.get("/weight/add/")
        self.assertContains(page, "Weight (lb)")

    def test_editing_shows_the_value_in_display_units(self):
        weight = Weight.objects.create(
            child=self.child, weight=3.6287, date=datetime.date.today()
        )
        Child.settings.unit_system = units.US
        page = self.c.get(f"/weight/{weight.id}/")
        self.assertContains(page, 'value="8.0"')

    def test_editing_round_trips_without_drifting(self):
        Child.settings.unit_system = units.US
        weight = Weight.objects.create(
            child=self.child, weight=3.6287, date=datetime.date.today()
        )
        page = self.c.post(
            f"/weight/{weight.id}/",
            {
                "child": self.child.id,
                "weight": "8.00",
                "date": weight.date.isoformat(),
            },
        )
        self.assertEqual(page.status_code, 302)
        weight.refresh_from_db()
        self.assertAlmostEqual(weight.weight, 3.6287, places=3)

    def test_list_view_shows_the_unit(self):
        Weight.objects.create(child=self.child, weight=3.6, date=datetime.date.today())
        page = self.c.get("/weight/")
        self.assertContains(page, "3.6 kg")

        Child.settings.unit_system = units.US
        page = self.c.get("/weight/")
        self.assertContains(page, "7.94 lb")
