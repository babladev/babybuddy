# -*- coding: utf-8 -*-
import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from guidance.models import GuidanceEntry

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "guidance.json",
)


class Command(BaseCommand):
    help = (
        "Loads the bundled guidance content. Entries are matched on their slug, "
        "so running this repeatedly updates existing entries instead of "
        "duplicating them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            default=DATA_FILE,
            help="Path to a guidance JSON file. Defaults to the bundled content.",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            default=False,
            help=(
                "Delete entries whose slug is not present in the file. Use this "
                "to remove content that has been retired upstream."
            ),
        )

    def handle(self, *args, **options):
        path = options["file"]
        verbosity = options["verbosity"]

        try:
            with open(path, "r", encoding="utf-8") as data_file:
                data = json.load(data_file)
        except FileNotFoundError:
            raise CommandError(f"Guidance content file not found: {path}")
        except json.JSONDecodeError as error:
            raise CommandError(f"Guidance content file is not valid JSON: {error}")

        entries = data.get("entries")
        if not isinstance(entries, list):
            raise CommandError('Guidance content file has no "entries" list.')

        created = 0
        updated = 0

        with transaction.atomic():
            for entry in entries:
                slug = entry.get("slug")
                if not slug:
                    raise CommandError("Every guidance entry requires a slug.")

                _, was_created = GuidanceEntry.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "scale": entry["scale"],
                        "period": entry["period"],
                        "kind": entry["kind"],
                        "title": entry["title"],
                        "description": entry.get("description", ""),
                        "order": entry.get("order", 0),
                        "is_active": entry.get("is_active", True),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            deleted = 0
            if options["prune"]:
                slugs = [entry["slug"] for entry in entries]
                deleted, _ignored = GuidanceEntry.objects.exclude(
                    slug__in=slugs
                ).delete()

        if verbosity > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Guidance content loaded: "
                    f"{created} added, {updated} updated, {deleted} removed."
                )
            )
