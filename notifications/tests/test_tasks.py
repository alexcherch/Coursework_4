from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from habits.models import Habit
from notifications import tasks
from notifications.telegram import TelegramError

User = get_user_model()

pytestmark = pytest.mark.django_db

NOW = timezone.make_aware(datetime(2026, 1, 1, 9, 0))


@pytest.fixture
def user():
    return User.objects.create_user(
        email="owner@example.com",
        password="StrongPass123",
        telegram_id=100500,
    )


def create_habit(user, **overrides):
    defaults = {
        "user": user,
        "place": "Home",
        "time": time(9, 0),
        "action": "Stretch",
        "duration": 60,
    }
    defaults.update(overrides)
    return Habit.objects.create(**defaults)


@patch("notifications.tasks.send_message")
def test_send_reminder_sends_message_and_updates_timestamp(mock_send, user):
    mock_send.return_value = {"ok": True}
    habit = create_habit(user)

    result = tasks.send_habit_reminder(habit.id)

    assert result is True
    mock_send.assert_called_once()
    chat_id, text = mock_send.call_args.args
    assert chat_id == 100500
    assert "Stretch" in text

    habit.refresh_from_db()
    assert habit.last_reminded_at is not None


@patch("notifications.tasks.send_message")
def test_send_reminder_skips_user_without_telegram_id(mock_send):
    user = User.objects.create_user(email="no-tg@example.com", password="StrongPass123")
    habit = create_habit(user)

    result = tasks.send_habit_reminder(habit.id)

    assert result is False
    mock_send.assert_not_called()
    habit.refresh_from_db()
    assert habit.last_reminded_at is None


@patch("notifications.tasks.send_message")
def test_send_reminder_handles_telegram_error(mock_send, user):
    mock_send.side_effect = TelegramError("boom")
    habit = create_habit(user)

    result = tasks.send_habit_reminder(habit.id)

    assert result is False
    habit.refresh_from_db()
    assert habit.last_reminded_at is None


@patch("notifications.tasks.send_message")
def test_send_reminder_for_missing_habit(mock_send):
    result = tasks.send_habit_reminder(999999)

    assert result is False
    mock_send.assert_not_called()


def test_reminder_text_includes_reward(user):
    habit = Habit(
        user=user,
        place="Gym",
        time=time(9, 0),
        action="Run",
        duration=60,
        reward="Smoothie",
    )

    text = tasks.build_reminder_text(habit)

    assert "Run" in text
    assert "Smoothie" in text


def test_reminder_text_includes_linked_habit(user):
    pleasant = create_habit(user, action="Take a bath", is_pleasant=True)
    habit = Habit(
        user=user,
        place="Home",
        time=time(9, 0),
        action="Stretch",
        duration=60,
        linked_habit=pleasant,
    )

    text = tasks.build_reminder_text(habit)

    assert "Stretch" in text
    assert "Take a bath" in text


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_schedules_due_habit(mock_delay, user):
    habit = create_habit(user)

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 1
    mock_delay.assert_called_once_with(habit.id)


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_skips_habit_at_another_time(mock_delay, user):
    create_habit(user, time=time(10, 0))

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 0
    mock_delay.assert_not_called()


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_skips_pleasant_habit(mock_delay, user):
    create_habit(user, is_pleasant=True)

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 0
    mock_delay.assert_not_called()


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_skips_user_without_telegram_id(mock_delay):
    user = User.objects.create_user(email="no-tg@example.com", password="StrongPass123")
    create_habit(user)

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 0
    mock_delay.assert_not_called()


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_skips_habit_reminded_today(mock_delay, user):
    create_habit(user, last_reminded_at=NOW - timedelta(hours=1))

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 0
    mock_delay.assert_not_called()


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_schedules_daily_habit_reminded_yesterday(mock_delay, user):
    habit = create_habit(user, last_reminded_at=NOW - timedelta(days=1))

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 1
    mock_delay.assert_called_once_with(habit.id)


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_skips_weekly_habit_reminded_six_days_ago(mock_delay, user):
    create_habit(
        user,
        periodicity=7,
        last_reminded_at=NOW - timedelta(days=6),
    )

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 0
    mock_delay.assert_not_called()


@patch.object(tasks.send_habit_reminder, "delay")
def test_dispatch_schedules_weekly_habit_reminded_seven_days_ago(mock_delay, user):
    habit = create_habit(
        user,
        periodicity=7,
        last_reminded_at=NOW - timedelta(days=7),
    )

    scheduled = tasks.dispatch_habit_reminders(now=NOW)

    assert scheduled == 1
    mock_delay.assert_called_once_with(habit.id)
