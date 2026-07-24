# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import gettext_lazy as _

from guidance.models import Pregnancy


class PregnancyForm(forms.ModelForm):
    class Meta:
        model = Pregnancy
        fields = ["name", "due_date", "child"]
        widgets = {
            "due_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }
        labels = {
            "child": _("Arrived as"),
        }
