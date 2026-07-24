# -*- coding: utf-8 -*-
import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client as HttpClient, TestCase, override_settings

from faker import Faker


class ProtectedMediaTestCase(TestCase):
    """
    Uploaded media (child photos, note images) must not be readable without
    authentication. Upload names are predictable, so public exposure of the
    media directory would make those files guessable.
    """

    @classmethod
    def setUpClass(cls):
        super(ProtectedMediaTestCase, cls).setUpClass()
        fake = Faker()
        call_command("migrate", verbosity=0)

        cls.media_root = tempfile.mkdtemp()
        cls.file_name = "child/picture/example.txt"
        file_path = os.path.join(cls.media_root, cls.file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as media_file:
            media_file.write("not-really-an-image")

        fake_user = fake.simple_profile()
        cls.credentials = {
            "username": fake_user["username"],
            "password": fake.password(),
        }
        cls.user = get_user_model().objects.create_user(
            is_superuser=True, **cls.credentials
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super(ProtectedMediaTestCase, cls).tearDownClass()

    def test_anonymous_access_is_redirected_to_login(self):
        c = HttpClient()
        with override_settings(MEDIA_ROOT=self.media_root):
            page = c.get(f"/media/{self.file_name}")
        self.assertEqual(page.status_code, 302)
        self.assertIn("/login/", page.url)

    def test_authenticated_access_returns_the_file(self):
        c = HttpClient()
        c.login(**self.credentials)
        with override_settings(MEDIA_ROOT=self.media_root):
            page = c.get(f"/media/{self.file_name}")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(b"".join(page.streaming_content), b"not-really-an-image")
        self.assertIn("private", page.headers["Cache-Control"])

    def test_missing_file_returns_not_found(self):
        c = HttpClient()
        c.login(**self.credentials)
        with override_settings(MEDIA_ROOT=self.media_root):
            page = c.get("/media/child/picture/does-not-exist.jpg")
        self.assertEqual(page.status_code, 404)

    def test_path_traversal_cannot_escape_media_root(self):
        outside_path = os.path.join(self.media_root, "outside.txt")
        with open(outside_path, "w") as outside_file:
            outside_file.write("secret")
        inside_root = os.path.join(self.media_root, "child")

        c = HttpClient()
        c.login(**self.credentials)
        with override_settings(MEDIA_ROOT=inside_root):
            page = c.get("/media/..%2Foutside.txt")
        self.assertNotEqual(page.status_code, 200)
