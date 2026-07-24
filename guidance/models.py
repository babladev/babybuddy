# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import Child


class Scale(models.TextChoices):
    """
    How an entry is positioned on the timeline.

    PRENATAL entries count down to the due date, so a lower period means closer
    to birth. DAY and MONTH entries count up from the birth date.
    """

    PRENATAL = "prenatal", _("Days before birth")
    DAY = "day", _("Days after birth")
    MONTH = "month", _("Months after birth")


class Kind(models.TextChoices):
    ACTION = "action", _("Action")
    WATCH = "watch", _("Watch for")
    RECAP = "recap", _("Recap")


class GuidanceEntry(models.Model):
    """
    A single piece of guidance shown at a point on a child's timeline.

    Content is addressed by (scale, period):

    - ``prenatal`` with period 30 means "30 days before the due date"
    - ``day`` with period 0 means "the day of birth", 7 means "one week old"
    - ``month`` with period 1 means "the first month of life" (age 0-1 month),
      2 means the second month, and so on

    Periods do not need to be contiguous. When there is no entry for the exact
    day or month, the most recent earlier period is used instead, so the
    daily content can stop after the newborn weeks and the monthly content
    takes over.
    """

    model_name = "guidanceentry"

    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Slug"),
        help_text=_(
            "Stable identifier used to update this entry when guidance content "
            "is reloaded."
        ),
    )
    scale = models.CharField(
        choices=Scale.choices,
        default=Scale.DAY,
        max_length=10,
        verbose_name=_("Scale"),
    )
    period = models.IntegerField(
        verbose_name=_("Period"),
        help_text=_(
            "Days before birth, days after birth or months after birth, "
            "depending on the scale."
        ),
    )
    kind = models.CharField(
        choices=Kind.choices,
        default=Kind.ACTION,
        max_length=10,
        verbose_name=_("Kind"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Order"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["scale", "period", "order", "title"]
        verbose_name = _("Guidance Entry")
        verbose_name_plural = _("Guidance Entries")

    def __str__(self):
        return self.title

    def clean(self):
        if self.scale == Scale.PRENATAL and self.period < 1:
            raise ValidationError(
                {"period": _("Days before birth must be 1 or greater.")}
            )
        if self.scale == Scale.DAY and self.period < 0:
            raise ValidationError({"period": _("Days after birth cannot be negative.")})
        if self.scale == Scale.MONTH and self.period < 1:
            raise ValidationError(
                {"period": _("Months after birth must be 1 or greater.")}
            )

    @property
    def is_checkable(self):
        """
        Only actions can be ticked off. Recaps and things to watch for are
        informational.
        """
        return self.kind == Kind.ACTION


class Pregnancy(models.Model):
    """
    An expected child, used to place prenatal guidance on a timeline.

    Baby Buddy's Child model requires a birth date, so guidance for the month
    before birth needs its own anchor. Once the baby arrives the record can be
    linked to the new Child, which retires its prenatal guidance.
    """

    model_name = "pregnancy"

    name = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_("Name"),
        help_text=_('An optional label, for example "Baby #2".'),
    )
    due_date = models.DateField(verbose_name=_("Due date"))
    child = models.OneToOneField(
        Child,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="pregnancy",
        verbose_name=_("Child"),
        help_text=_("Set once the baby has arrived to end prenatal guidance."),
    )

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["due_date"]
        verbose_name = _("Pregnancy")
        verbose_name_plural = _("Pregnancies")

    def __str__(self):
        return self.name or str(_("Due %(date)s") % {"date": self.due_date.isoformat()})

    @property
    def is_active(self):
        """
        A pregnancy stops driving guidance once it is linked to a child.
        """
        return self.child_id is None

    def days_until_due(self, today=None):
        today = today or timezone.localdate()
        return (self.due_date - today).days


class GuidanceCompletion(models.Model):
    """
    Records that a guidance entry has been dealt with, for one child or one
    pregnancy.
    """

    model_name = "guidancecompletion"

    entry = models.ForeignKey(
        GuidanceEntry,
        on_delete=models.CASCADE,
        related_name="completions",
        verbose_name=_("Entry"),
    )
    child = models.ForeignKey(
        Child,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="guidance_completions",
        verbose_name=_("Child"),
    )
    pregnancy = models.ForeignKey(
        Pregnancy,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="guidance_completions",
        verbose_name=_("Pregnancy"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("User"),
    )
    completed_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Completed")
    )

    objects = models.Manager()

    class Meta:
        default_permissions = ("view", "add", "change", "delete")
        ordering = ["-completed_at"]
        verbose_name = _("Guidance Completion")
        verbose_name_plural = _("Guidance Completions")
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "child"],
                name="guidance_unique_entry_per_child",
            ),
            models.UniqueConstraint(
                fields=["entry", "pregnancy"],
                name="guidance_unique_entry_per_pregnancy",
            ),
            # A completion belongs to exactly one timeline.
            models.CheckConstraint(
                condition=models.Q(child__isnull=False, pregnancy__isnull=True)
                | models.Q(child__isnull=True, pregnancy__isnull=False),
                name="guidance_completion_single_subject",
            ),
        ]

    def __str__(self):
        return "{} - {}".format(self.subject, self.entry)

    @property
    def subject(self):
        return self.child or self.pregnancy

    def clean(self):
        if bool(self.child_id) == bool(self.pregnancy_id):
            raise ValidationError(
                _("A completion must reference either a child or a pregnancy.")
            )
