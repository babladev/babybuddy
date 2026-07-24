# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Child
from guidance.models import GuidanceCompletion, GuidanceEntry, Pregnancy, Scale


class GuidanceAPITestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("migrate", verbosity=0)
        cls.user = get_user_model().objects.get(username="admin")
        cls.child = Child.objects.create(
            first_name="API",
            last_name="Child",
            birth_date=datetime.date(2026, 1, 15),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.user)

    def test_entries_are_listed(self):
        response = self.client.get("/api/guidance-entries/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data["count"], 0)

    def test_entries_can_be_filtered_by_scale_and_period(self):
        response = self.client.get(
            "/api/guidance-entries/", {"scale": Scale.DAY, "period": 0}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data["count"], 0)
        for entry in response.data["results"]:
            self.assertEqual(entry["scale"], Scale.DAY)
            self.assertEqual(entry["period"], 0)

    def test_entries_require_authentication(self):
        client = APIClient()
        response = client.get("/api/guidance-entries/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pregnancy_create_and_read(self):
        response = self.client.post(
            "/api/pregnancies/",
            {"name": "API Baby", "due_date": "2026-09-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get("/api/pregnancies/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "API Baby")
        self.assertIn("days_until_due", response.data["results"][0])

    def test_completion_create_records_the_requesting_user(self):
        entry = GuidanceEntry.objects.filter(scale=Scale.MONTH, period=1).first()
        response = self.client.post(
            "/api/guidance-completions/",
            {"entry": entry.id, "child": self.child.id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        completion = GuidanceCompletion.objects.get(entry=entry, child=self.child)
        self.assertEqual(completion.user, self.user)

    def test_completion_requires_exactly_one_subject(self):
        entry = GuidanceEntry.objects.filter(scale=Scale.MONTH, period=1).first()
        response = self.client.post("/api/guidance-completions/", {"entry": entry.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        pregnancy = Pregnancy.objects.create(due_date=datetime.date(2026, 9, 1))
        response = self.client.post(
            "/api/guidance-completions/",
            {
                "entry": entry.id,
                "child": self.child.id,
                "pregnancy": pregnancy.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_completion_delete(self):
        entry = GuidanceEntry.objects.filter(scale=Scale.MONTH, period=1).first()
        completion = GuidanceCompletion.objects.create(entry=entry, child=self.child)
        response = self.client.delete(f"/api/guidance-completions/{completion.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(GuidanceCompletion.objects.exists())
