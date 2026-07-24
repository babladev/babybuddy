# -*- coding: utf-8 -*-
from django.urls import path

from . import views

app_name = "guidance"

urlpatterns = [
    path("guidance/", views.GuidanceToday.as_view(), name="today"),
    path(
        "guidance/complete/",
        views.GuidanceCompletionToggle.as_view(),
        name="completion-toggle",
    ),
    path("guidance/pregnancies/", views.PregnancyList.as_view(), name="pregnancy-list"),
    path(
        "guidance/pregnancies/add/",
        views.PregnancyAdd.as_view(),
        name="pregnancy-add",
    ),
    path(
        "guidance/pregnancies/<int:pk>/edit/",
        views.PregnancyUpdate.as_view(),
        name="pregnancy-update",
    ),
    path(
        "guidance/pregnancies/<int:pk>/delete/",
        views.PregnancyDelete.as_view(),
        name="pregnancy-delete",
    ),
    path(
        "children/<str:slug>/guidance/",
        views.ChildGuidance.as_view(),
        name="child",
    ),
    path(
        "children/<str:slug>/guidance/month/<int:month>/",
        views.ChildGuidanceMonth.as_view(),
        name="child-month",
    ),
]
