# -*- coding: utf-8 -*-
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import BadRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from babybuddy.mixins import (
    CancelUrlMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from core.models import Child
from guidance import recap, timeline
from guidance.forms import PregnancyForm
from guidance.models import GuidanceCompletion, GuidanceEntry, Pregnancy, Scale


class GuidanceToday(LoginRequiredMixin, TemplateView):
    """
    What to do, watch for and read about today, for every child and every
    pregnancy being tracked.
    """

    template_name = "guidance/today.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        context["today"] = today
        context["children"] = [
            timeline.child_guidance(child, today)
            for child in Child.objects.filter(birth_date__lte=today)
        ]
        context["pregnancies"] = [
            timeline.pregnancy_guidance(pregnancy, today)
            for pregnancy in Pregnancy.objects.filter(child__isnull=True)
        ]
        return context


class ChildGuidance(PermissionRequiredMixin, TemplateView):
    """
    A child's guidance: what applies now, and the months ahead and behind.
    """

    template_name = "guidance/child.html"
    permission_required = ("core.view_child",)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        child = get_object_or_404(Child, slug=self.kwargs.get("slug"))

        context["object"] = child
        context["today"] = today
        context.update(timeline.child_guidance(child, today))
        context["months"] = self._month_index(child, today)
        return context

    def _month_index(self, child, today):
        """
        Every month content exists for, flagged as past, current or upcoming.
        """
        current = timeline.month_of_life(child.birth_date, today)
        return [
            {
                "period": period,
                "is_current": period == current,
                "is_past": period < current,
            }
            for period in timeline.available_periods(Scale.MONTH)
        ]


class ChildGuidanceMonth(PermissionRequiredMixin, TemplateView):
    """
    One month of a child's life: the guidance for that month alongside a recap
    of what was actually logged.
    """

    template_name = "guidance/child_month.html"
    permission_required = ("core.view_child",)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        child = get_object_or_404(Child, slug=self.kwargs.get("slug"))
        month = int(self.kwargs.get("month"))

        context["object"] = child
        context["today"] = today
        context["month"] = month
        context["group"] = timeline.group_for_period(Scale.MONTH, month, child=child)
        context["recap"] = recap.month_recap(child, month, today)
        context["current_month"] = timeline.month_of_life(child.birth_date, today)

        available = timeline.available_periods(Scale.MONTH)
        context["month_previous"] = max(
            [period for period in available if period < month], default=None
        )
        context["month_next"] = min(
            [period for period in available if period > month], default=None
        )
        return context


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(require_POST, name="dispatch")
class GuidanceCompletionToggle(PermissionRequiredMixin, View):
    """
    Ticks a guidance action off, or clears it again.

    Requires permission to record completions, so read-only users cannot change
    another user's progress.
    """

    permission_required = ("guidance.add_guidancecompletion",)

    def post(self, request, *args, **kwargs):
        entry = get_object_or_404(GuidanceEntry, pk=request.POST.get("entry"))

        child = None
        pregnancy = None
        if request.POST.get("child"):
            child = get_object_or_404(Child, slug=request.POST.get("child"))
        elif request.POST.get("pregnancy"):
            pregnancy = get_object_or_404(Pregnancy, pk=request.POST.get("pregnancy"))
        else:
            raise BadRequest(_("A child or pregnancy is required."))

        existing = GuidanceCompletion.objects.filter(
            entry=entry, child=child, pregnancy=pregnancy
        ).first()
        if existing:
            existing.delete()
            completed = False
        else:
            GuidanceCompletion.objects.create(
                entry=entry,
                child=child,
                pregnancy=pregnancy,
                user=request.user,
            )
            completed = True

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"entry": entry.id, "completed": completed})

        return redirect(request.POST.get("next") or reverse("guidance:today"))


class PregnancyList(PermissionRequiredMixin, ListView):
    model = Pregnancy
    template_name = "guidance/pregnancy_list.html"
    permission_required = ("guidance.view_pregnancy",)


class PregnancyAdd(
    CancelUrlMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    model = Pregnancy
    template_name = "guidance/pregnancy_form.html"
    permission_required = ("guidance.add_pregnancy",)
    form_class = PregnancyForm
    success_url = reverse_lazy("guidance:pregnancy-list")
    success_message = gettext_lazy("Pregnancy added!")


class PregnancyUpdate(
    CancelUrlMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = Pregnancy
    template_name = "guidance/pregnancy_form.html"
    permission_required = ("guidance.change_pregnancy",)
    form_class = PregnancyForm
    success_url = reverse_lazy("guidance:pregnancy-list")
    success_message = gettext_lazy("Pregnancy updated.")


class PregnancyDelete(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Pregnancy
    template_name = "guidance/pregnancy_confirm_delete.html"
    permission_required = ("guidance.delete_pregnancy",)
    success_url = reverse_lazy("guidance:pregnancy-list")
    success_message = gettext_lazy("Pregnancy deleted.")
