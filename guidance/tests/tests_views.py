# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client as HttpClient, TestCase
from django.utils import timezone

from faker import Faker

from core.models import Child, DiaperChange
from guidance import timeline
from guidance.models import GuidanceCompletion, Pregnancy, Scale


class GuidanceViewsTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(GuidanceViewsTestCase, cls).setUpClass()
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
            first_name="Guidance",
            last_name="View",
            birth_date=datetime.date.today() - datetime.timedelta(days=7),
        )

    def test_today_requires_login(self):
        c = HttpClient()
        page = c.get("/guidance/")
        self.assertEqual(page.status_code, 302)
        self.assertIn("/login/", page.url)

    def test_today_lists_children(self):
        page = self.c.get("/guidance/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Guidance View")
        self.assertContains(page, "Day 7")

    def test_today_lists_pregnancies(self):
        Pregnancy.objects.create(
            name="Baby Two",
            due_date=datetime.date.today() + datetime.timedelta(days=14),
        )
        page = self.c.get("/guidance/")
        self.assertContains(page, "Baby Two")
        self.assertContains(page, "14 days until the due date")

    def test_today_excludes_pregnancies_that_have_arrived(self):
        Pregnancy.objects.create(
            name="Already Here",
            due_date=datetime.date.today() - datetime.timedelta(days=7),
            child=self.child,
        )
        page = self.c.get("/guidance/")
        self.assertNotContains(page, "Already Here")

    def test_today_handles_having_nothing_to_show(self):
        self.child.delete()
        page = self.c.get("/guidance/")
        self.assertContains(page, "Nothing to guide yet")

    def test_child_guidance_page(self):
        page = self.c.get(f"/children/{self.child.slug}/guidance/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Day 7 of life")
        self.assertContains(page, "Month 1")

    def test_child_guidance_unknown_child_is_not_found(self):
        page = self.c.get("/children/nobody/guidance/")
        self.assertEqual(page.status_code, 404)

    def test_child_month_page_shows_guidance_and_recap(self):
        page = self.c.get(f"/children/{self.child.slug}/guidance/month/1/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Recap")
        # Nothing has been logged for this child, so the recap says so rather
        # than rendering a table of zeroes.
        self.assertContains(page, "Nothing was logged for this month.")
        self.assertContains(page, "Month one: survival, and it counts")

    def test_child_month_page_shows_logged_totals(self):
        DiaperChange.objects.create(
            child=self.child, time=timezone.now(), wet=True, solid=False
        )
        page = self.c.get(f"/children/{self.child.slug}/guidance/month/1/")
        self.assertContains(page, "Diaper changes")
        self.assertContains(page, "1 wet, 0 solid")

    def test_child_month_page_handles_a_month_without_content(self):
        page = self.c.get(f"/children/{self.child.slug}/guidance/month/99/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "No guidance is written for this month yet.")

    def test_completion_toggle_marks_and_unmarks(self):
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        entry = group.actions[0]

        page = self.c.post(
            "/guidance/complete/",
            {"entry": entry.id, "child": self.child.slug},
        )
        self.assertEqual(page.status_code, 302)
        self.assertTrue(
            GuidanceCompletion.objects.filter(entry=entry, child=self.child).exists()
        )

        self.c.post(
            "/guidance/complete/",
            {"entry": entry.id, "child": self.child.slug},
        )
        self.assertFalse(
            GuidanceCompletion.objects.filter(entry=entry, child=self.child).exists()
        )

    def test_completion_toggle_records_the_user(self):
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        entry = group.actions[0]
        self.c.post(
            "/guidance/complete/",
            {"entry": entry.id, "child": self.child.slug},
        )
        completion = GuidanceCompletion.objects.get(entry=entry, child=self.child)
        self.assertEqual(completion.user, self.user)

    def test_completion_toggle_ajax_returns_state(self):
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        entry = group.actions[0]
        page = self.c.post(
            "/guidance/complete/",
            {"entry": entry.id, "child": self.child.slug},
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.json(), {"entry": entry.id, "completed": True})

    def test_completion_toggle_requires_a_subject(self):
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        page = self.c.post("/guidance/complete/", {"entry": group.actions[0].id})
        self.assertEqual(page.status_code, 400)

    def test_completion_toggle_rejects_get(self):
        page = self.c.get("/guidance/complete/")
        self.assertEqual(page.status_code, 405)

    def test_completion_toggle_works_for_a_pregnancy(self):
        pregnancy = Pregnancy.objects.create(
            due_date=datetime.date.today() + datetime.timedelta(days=10)
        )
        group = timeline.group_for_period(Scale.PRENATAL, 10, pregnancy=pregnancy)
        entry = group.actions[0]
        self.c.post(
            "/guidance/complete/",
            {"entry": entry.id, "pregnancy": pregnancy.id},
        )
        self.assertTrue(
            GuidanceCompletion.objects.filter(entry=entry, pregnancy=pregnancy).exists()
        )


class PregnancyViewsTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(PregnancyViewsTestCase, cls).setUpClass()
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

    def test_list(self):
        page = self.c.get("/guidance/pregnancies/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "No pregnancies are being tracked.")

    def test_add(self):
        due_date = datetime.date.today() + datetime.timedelta(days=30)
        page = self.c.post(
            "/guidance/pregnancies/add/",
            {"name": "Baby Three", "due_date": due_date.isoformat()},
            follow=True,
        )
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Pregnancy added!")
        self.assertTrue(Pregnancy.objects.filter(name="Baby Three").exists())

    def test_update(self):
        pregnancy = Pregnancy.objects.create(
            name="Baby Four",
            due_date=datetime.date.today() + datetime.timedelta(days=20),
        )
        new_due_date = datetime.date.today() + datetime.timedelta(days=25)
        page = self.c.post(
            f"/guidance/pregnancies/{pregnancy.id}/edit/",
            {"name": "Baby Four", "due_date": new_due_date.isoformat()},
            follow=True,
        )
        self.assertEqual(page.status_code, 200)
        pregnancy.refresh_from_db()
        self.assertEqual(pregnancy.due_date, new_due_date)

    def test_delete(self):
        pregnancy = Pregnancy.objects.create(
            due_date=datetime.date.today() + datetime.timedelta(days=20)
        )
        page = self.c.post(f"/guidance/pregnancies/{pregnancy.id}/delete/", follow=True)
        self.assertEqual(page.status_code, 200)
        self.assertFalse(Pregnancy.objects.filter(id=pregnancy.id).exists())


class GuidanceReadOnlyUserTestCase(TestCase):
    """
    Read-only users can see guidance but must not be able to change progress.
    """

    @classmethod
    def setUpClass(cls):
        super(GuidanceReadOnlyUserTestCase, cls).setUpClass()
        fake = Faker()
        call_command("migrate", verbosity=0)

        fake_user = fake.simple_profile()
        cls.credentials = {
            "username": fake_user["username"],
            "password": fake.password(),
        }
        cls.user = get_user_model().objects.create_user(**cls.credentials)
        call_command(
            "createuser",
            "--read-only",
            username="guidancereadonly",
            password="readonlypassword",
            email="readonly@test.test",
            verbosity=0,
        )

    def setUp(self):
        self.c = HttpClient()
        self.c.login(username="guidancereadonly", password="readonlypassword")
        self.child = Child.objects.create(
            first_name="Read",
            last_name="Only",
            birth_date=datetime.date.today() - datetime.timedelta(days=7),
        )

    def test_read_only_user_can_view_guidance(self):
        page = self.c.get(f"/children/{self.child.slug}/guidance/")
        self.assertEqual(page.status_code, 200)

    def test_read_only_user_cannot_toggle_completion(self):
        group = timeline.group_for_period(Scale.MONTH, 1, child=self.child)
        page = self.c.post(
            "/guidance/complete/",
            {"entry": group.actions[0].id, "child": self.child.slug},
        )
        self.assertEqual(page.status_code, 403)
        self.assertFalse(GuidanceCompletion.objects.exists())

    def test_read_only_user_cannot_add_a_pregnancy(self):
        page = self.c.post(
            "/guidance/pregnancies/add/",
            {
                "due_date": (
                    datetime.date.today() + datetime.timedelta(days=30)
                ).isoformat()
            },
        )
        self.assertEqual(page.status_code, 403)
        self.assertFalse(Pregnancy.objects.exists())
