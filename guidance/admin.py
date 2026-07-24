# -*- coding: utf-8 -*-
from django.contrib import admin

from guidance.models import GuidanceCompletion, GuidanceEntry, Pregnancy


@admin.register(GuidanceEntry)
class GuidanceEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "scale", "period", "kind", "is_active")
    list_filter = ("scale", "kind", "is_active")
    search_fields = ("slug", "title", "description")


@admin.register(Pregnancy)
class PregnancyAdmin(admin.ModelAdmin):
    list_display = ("__str__", "due_date", "child")


@admin.register(GuidanceCompletion)
class GuidanceCompletionAdmin(admin.ModelAdmin):
    list_display = ("entry", "child", "pregnancy", "user", "completed_at")
    list_filter = ("child", "pregnancy")
