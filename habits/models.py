from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .validators import (
    MAX_DURATION_SECONDS,
    MAX_PERIODICITY_DAYS,
    MIN_PERIODICITY_DAYS,
    validate_habit,
)


class Habit(models.Model):
    """A habit that a user wants to track and get reminders about."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
        verbose_name=_("user"),
    )
    place = models.CharField(_("place"), max_length=255)
    time = models.TimeField(_("time"))
    action = models.CharField(_("action"), max_length=255)
    is_pleasant = models.BooleanField(_("is pleasant"), default=False)
    linked_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="linked_to",
        null=True,
        blank=True,
        limit_choices_to={"is_pleasant": True},
        verbose_name=_("linked habit"),
    )
    periodicity = models.PositiveSmallIntegerField(
        _("periodicity"),
        default=1,
        validators=[
            MinValueValidator(MIN_PERIODICITY_DAYS),
            MaxValueValidator(MAX_PERIODICITY_DAYS),
        ],
        help_text=_("Days between reminders (1-7)"),
    )
    reward = models.CharField(_("reward"), max_length=255, blank=True)
    duration = models.PositiveSmallIntegerField(
        _("duration"),
        validators=[
            MinValueValidator(1),
            MaxValueValidator(MAX_DURATION_SECONDS),
        ],
        help_text=_("Estimated time in seconds (max 120)"),
    )
    is_public = models.BooleanField(_("is public"), default=False)
    last_reminded_at = models.DateTimeField(
        _("last reminded at"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = _("habit")
        verbose_name_plural = _("habits")
        constraints = [
            models.CheckConstraint(
                condition=Q(duration__gte=1) & Q(duration__lte=MAX_DURATION_SECONDS),
                name="habit_duration_range",
            ),
            models.CheckConstraint(
                condition=Q(periodicity__gte=MIN_PERIODICITY_DAYS)
                & Q(periodicity__lte=MAX_PERIODICITY_DAYS),
                name="habit_periodicity_range",
            ),
            models.CheckConstraint(
                condition=Q(reward="") | Q(linked_habit__isnull=True),
                name="habit_reward_xor_linked",
            ),
            models.CheckConstraint(
                condition=Q(is_pleasant=False) | (Q(reward="") & Q(linked_habit__isnull=True)),
                name="habit_pleasant_has_no_reward_or_linked",
            ),
        ]

    def clean(self):
        super().clean()
        validate_habit(self)

    def __str__(self):
        return f"{self.action} at {self.time} in {self.place}"


class HabitCompletion(models.Model):
    """A record that a habit was completed on a certain date."""

    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name="completions",
        verbose_name=_("habit"),
    )
    completed_on = models.DateField(_("completed on"), default=timezone.localdate)

    class Meta:
        ordering = ["-completed_on"]
        verbose_name = _("habit completion")
        verbose_name_plural = _("habit completions")
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "completed_on"],
                name="unique_habit_completion_per_day",
            ),
        ]

    def __str__(self):
        return f"{self.habit} completed on {self.completed_on}"
