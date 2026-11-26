import logging

from celery import shared_task
from django.utils import timezone

from habits.models import Habit

from .telegram import TelegramError, send_message

logger = logging.getLogger(__name__)


def build_reminder_text(habit):
    """Build a human-readable reminder message for a habit."""
    text = f"Пора выполнить привычку: {habit.action} в {habit.time:%H:%M} в {habit.place}."

    if habit.reward:
        text += f" Вознаграждение: {habit.reward}."
    elif habit.linked_habit_id:
        text += f" После этого: {habit.linked_habit.action}."

    return text


@shared_task
def send_habit_reminder(habit_id):
    """Send a Telegram reminder for a single habit."""
    try:
        habit = Habit.objects.select_related("user", "linked_habit").get(pk=habit_id)
    except Habit.DoesNotExist:
        logger.warning("Habit %s does not exist, reminder skipped.", habit_id)
        return False

    if habit.user.telegram_id is None:
        logger.info("User %s has no telegram_id, reminder skipped.", habit.user_id)
        return False

    try:
        send_message(habit.user.telegram_id, build_reminder_text(habit))
    except TelegramError as exc:
        logger.error("Failed to send reminder for habit %s: %s", habit_id, exc)
        return False

    habit.last_reminded_at = timezone.now()
    habit.save(update_fields=["last_reminded_at"])
    return True


@shared_task
def dispatch_habit_reminders(now=None):
    """Schedule reminders for habits that are due at the current minute."""
    now = now or timezone.localtime()

    candidates = Habit.objects.filter(
        is_pleasant=False,
        user__telegram_id__isnull=False,
        time__hour=now.hour,
        time__minute=now.minute,
    ).select_related("user")

    scheduled = 0
    for habit in candidates:
        if habit.last_reminded_at is not None:
            last_date = timezone.localtime(habit.last_reminded_at).date()
            if (now.date() - last_date).days < habit.periodicity:
                continue
        send_habit_reminder.delay(habit.id)
        scheduled += 1

    logger.info("Scheduled %s habit reminders.", scheduled)
    return scheduled
