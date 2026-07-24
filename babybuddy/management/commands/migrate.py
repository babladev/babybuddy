# -*- coding: utf-8 -*-
import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.management.commands import migrate
from django.db import DatabaseError

# Default username for the initial superuser. Override with the
# BABYBUDDY_ADMIN_USERNAME environment variable.
DEFAULT_ADMIN_USERNAME = "admin"


class Command(migrate.Command):
    help = (
        "Runs database migrations and, if no superuser exists yet, creates an "
        "initial one. The password comes from BABYBUDDY_ADMIN_PASSWORD; when "
        "that is unset a random password is generated and printed once."
    )

    def handle(self, *args, **kwargs):
        super(Command, self).handle(*args, **kwargs)
        self._create_initial_superuser(verbosity=kwargs.get("verbosity", 1))
        self._load_guidance_content(*args, **kwargs)

    def _load_guidance_content(self, *args, **kwargs):
        """
        Keeps the bundled guidance content in step with the code.

        Skipped when migrating a single app or to a specific migration, because
        the guidance tables may not exist at that point (`reset` walks apps back
        to zero this way).
        """
        if kwargs.get("app_label") or kwargs.get("migration_name"):
            return

        try:
            call_command("loadguidance", verbosity=kwargs.get("verbosity", 1))
        except (CommandError, DatabaseError) as error:
            # Content is not essential to a working install, so a failure here
            # must not abort the deployment.
            self.stderr.write(f"Could not load guidance content: {error}")

    def _create_initial_superuser(self, verbosity=1):
        """
        Creates an initial superuser account, but only when the instance has no
        superuser at all. Historically this created a well-known admin/admin
        account, which left every fresh deployment trivially accessible.
        """
        user_model = get_user_model()
        if user_model.objects.filter(is_superuser=True).exists():
            return

        username = os.environ.get("BABYBUDDY_ADMIN_USERNAME") or DEFAULT_ADMIN_USERNAME
        password = os.environ.get("BABYBUDDY_ADMIN_PASSWORD") or os.environ.get(
            "DJANGO_SUPERUSER_PASSWORD"
        )
        generated = False
        if not password:
            # A random password is still far better than a known default. It is
            # printed once so the operator can log in and change it.
            password = secrets.token_urlsafe(18)
            generated = True

        user = user_model.objects.create_user(username, password=password)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        if verbosity > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created initial superuser "{username}".')
            )
            if generated:
                self.stdout.write(
                    self.style.WARNING(
                        "No BABYBUDDY_ADMIN_PASSWORD was set, so a random "
                        "password was generated:\n\n"
                        f"    {password}\n\n"
                        "This is the only time it is shown. Log in and change "
                        "it now - anyone able to read this log can use it."
                    )
                )
