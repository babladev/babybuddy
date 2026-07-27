# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client as HttpClient, TestCase

from faker import Faker

from core.models import Child, Weight
from core.widgets import ChildRadioSelect, PillRadioSelect


class RadioWidgetTestCase(TestCase):
    """
    The child, feeding type and feeding method choices are radio inputs hidden
    behind styled labels.

    Two things have to hold, or the forms become unusable:

    - the input keeps Bootstrap's .btn-check and must not also get .d-none,
      because a display:none control cannot be focused and browsers then refuse
      to submit a form with an unsatisfied required radio, silently
    - the label must not use a colour scheme specific Bootstrap variant, which
      is how these ended up as white text on a white background
    """

    def test_pill_widget_input_is_focusable(self):
        attrs = PillRadioSelect().build_attrs({"class": "form-select"})
        self.assertIn("btn-check", attrs["class"])
        self.assertNotIn("d-none", attrs["class"])

    def test_child_widget_input_is_focusable(self):
        attrs = ChildRadioSelect().build_attrs({"class": "form-select"})
        self.assertIn("btn-check", attrs["class"])
        self.assertNotIn("d-none", attrs["class"])

    def test_widget_class_is_not_duplicated(self):
        attrs = PillRadioSelect().build_attrs({"class": "btn-check"})
        self.assertEqual(attrs["class"].split().count("btn-check"), 1)


class RadioWidgetRenderingTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(RadioWidgetRenderingTestCase, cls).setUpClass()
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
        Child.objects.create(
            first_name="Widget",
            last_name="Test",
            birth_date=datetime.date.today() - datetime.timedelta(days=30),
        )

    def test_feeding_form_renders_readable_pills(self):
        page = self.c.get("/feedings/add/")
        self.assertEqual(page.status_code, 200)
        content = page.content.decode()

        self.assertIn("bb-pill", content)
        # btn-outline-light is white-on-white in the light colour scheme.
        self.assertNotIn("btn-outline-light", content)
        self.assertNotIn("btn-check d-none", content)

    def test_feeding_can_be_submitted(self):
        child = Child.objects.first()
        start = datetime.datetime.now().replace(microsecond=0, second=0)
        page = self.c.post(
            "/feedings/add/",
            {
                "child": child.id,
                "start": start.strftime("%Y-%m-%dT%H:%M"),
                "end": (start + datetime.timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "type": "formula",
                "method": "bottle",
            },
        )
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.url, "/feedings/")


class DurationPresetsTestCase(TestCase):
    """
    Activities with a start and an end time get quick duration buttons.
    """

    @classmethod
    def setUpClass(cls):
        super(DurationPresetsTestCase, cls).setUpClass()
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
        Child.objects.create(
            first_name="Preset",
            last_name="Test",
            birth_date=datetime.date.today() - datetime.timedelta(days=30),
        )

    def test_presets_are_offered_on_forms_with_a_start_and_end(self):
        for path in ["/feedings/add/", "/sleep/add/", "/tummy-time/add/"]:
            with self.subTest(path=path):
                page = self.c.get(path)
                content = page.content.decode()
                self.assertIn("bb-duration-presets", content)
                for minutes in [1, 5, 10]:
                    self.assertIn(f'data-bb-duration-minutes="{minutes}"', content)

    def test_presets_are_absent_from_forms_without_an_end_time(self):
        for path in ["/weight/add/", "/temperature/add/", "/changes/add/"]:
            with self.subTest(path=path):
                page = self.c.get(path)
                self.assertNotIn("bb-duration-presets", page.content.decode())


class CancelButtonTestCase(TestCase):
    """
    Every entry form offers a way out that is not the browser's back button.
    """

    @classmethod
    def setUpClass(cls):
        super(CancelButtonTestCase, cls).setUpClass()
        fake = Faker()
        call_command("migrate", verbosity=0)

        fake_user = fake.simple_profile()
        cls.credentials = {
            "username": fake_user["username"],
            "password": fake.password(),
        }
        cls.user = get_user_model().objects.create_user(
            is_superuser=True, is_staff=True, **cls.credentials
        )

    def setUp(self):
        self.c = HttpClient()
        self.c.login(**self.credentials)
        self.child = Child.objects.create(
            first_name="Cancel",
            last_name="Test",
            birth_date=datetime.date.today() - datetime.timedelta(days=30),
        )

    def test_add_forms_cancel_to_the_relevant_list(self):
        expected = {
            "/feedings/add/": "/feedings/",
            "/sleep/add/": "/sleep/",
            "/tummy-time/add/": "/tummy-time/",
            "/changes/add/": "/changes/",
            "/weight/add/": "/weight/",
            "/temperature/add/": "/temperature/",
            "/notes/add/": "/notes/",
            "/children/add/": "/children/",
        }
        for path, cancel_url in expected.items():
            with self.subTest(path=path):
                page = self.c.get(path)
                self.assertEqual(page.context["cancel_url"], cancel_url)
                self.assertContains(page, f'href="{cancel_url}"')
                self.assertContains(page, "bb-form-actions__cancel")

    def test_edit_forms_offer_cancel(self):
        weight = Weight.objects.create(
            child=self.child, weight=3.6, date=datetime.date.today()
        )
        page = self.c.get(f"/weight/{weight.id}/")
        self.assertEqual(page.context["cancel_url"], "/weight/")

    def test_a_new_timer_cancels_to_the_timer_list(self):
        # A timer redirects to its own detail page on success, which does not
        # exist yet while the form is open.
        page = self.c.get("/timers/add/")
        self.assertEqual(page.context["cancel_url"], "/timers/")

    def test_cancelling_creates_nothing(self):
        before = Weight.objects.count()
        page = self.c.get("/weight/add/")
        self.c.get(page.context["cancel_url"])
        self.assertEqual(Weight.objects.count(), before)
