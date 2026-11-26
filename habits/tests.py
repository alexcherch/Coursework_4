from datetime import time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Habit, HabitCompletion

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="strong-pass-1")


@pytest.fixture
def other_user():
    return User.objects.create_user(email="other@example.com", password="strong-pass-2")


def build_habit(user, **overrides):
    defaults = {
        "user": user,
        "place": "Home",
        "time": time(9, 0),
        "action": "Stretch",
        "duration": 60,
    }
    defaults.update(overrides)
    return Habit(**defaults)


def create_habit(user, **overrides):
    habit = build_habit(user, **overrides)
    habit.save()
    return habit


def test_habit_defaults(user):
    habit = build_habit(user)

    assert habit.periodicity == 1
    assert habit.is_pleasant is False
    assert habit.is_public is False
    assert habit.reward == ""
    assert habit.last_reminded_at is None
    assert habit.linked_habit is None


def test_habit_string_representation(user):
    habit = create_habit(user)

    assert "Stretch" in str(habit)


def test_habit_with_reward_is_valid(user):
    habit = build_habit(user, reward="Buy coffee")

    habit.full_clean()


def test_habit_with_pleasant_linked_habit_is_valid(user):
    pleasant = create_habit(user, action="Take a bath", is_pleasant=True)
    habit = build_habit(user, linked_habit=pleasant)

    habit.full_clean()


def test_reward_and_linked_habit_cannot_be_set_together(user):
    pleasant = create_habit(user, is_pleasant=True)
    habit = build_habit(user, reward="Buy coffee", linked_habit=pleasant)

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert {"reward", "linked_habit"} <= set(exc_info.value.message_dict)


def test_linked_habit_must_be_pleasant(user):
    not_pleasant = create_habit(user, action="Read a book")
    habit = build_habit(user, linked_habit=not_pleasant)

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert "linked_habit" in exc_info.value.message_dict


def test_linked_habit_must_belong_to_same_user(user, other_user):
    foreign_pleasant = create_habit(other_user, is_pleasant=True)
    habit = build_habit(user, linked_habit=foreign_pleasant)

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert "linked_habit" in exc_info.value.message_dict


def test_habit_cannot_be_linked_to_itself(user):
    habit = create_habit(user, is_pleasant=True)
    habit.linked_habit = habit

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert "linked_habit" in exc_info.value.message_dict


def test_pleasant_habit_cannot_have_reward(user):
    habit = build_habit(user, is_pleasant=True, reward="Buy coffee")

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert "reward" in exc_info.value.message_dict


def test_pleasant_habit_cannot_have_linked_habit(user):
    pleasant = create_habit(user, is_pleasant=True)
    habit = build_habit(user, is_pleasant=True, linked_habit=pleasant)

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert "linked_habit" in exc_info.value.message_dict


@pytest.mark.parametrize("duration", [1, 120])
def test_duration_within_limit_is_valid(user, duration):
    habit = build_habit(user, duration=duration)

    habit.full_clean()


@pytest.mark.parametrize("duration", [0, 121])
def test_duration_out_of_range_is_invalid(user, duration):
    habit = build_habit(user, duration=duration)

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert "duration" in exc_info.value.message_dict


@pytest.mark.parametrize("periodicity", [1, 7])
def test_periodicity_within_limit_is_valid(user, periodicity):
    habit = build_habit(user, periodicity=periodicity)

    habit.full_clean()


@pytest.mark.parametrize("periodicity", [0, 8])
def test_periodicity_out_of_range_is_invalid(user, periodicity):
    habit = build_habit(user, periodicity=periodicity)

    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()

    assert "periodicity" in exc_info.value.message_dict


def test_duration_db_constraint(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_habit(user, duration=121)


def test_periodicity_db_constraint(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_habit(user, periodicity=8)


def test_reward_and_linked_habit_db_constraint(user):
    pleasant = create_habit(user, is_pleasant=True)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_habit(user, reward="Buy coffee", linked_habit=pleasant)


def test_pleasant_habit_db_constraint(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_habit(user, is_pleasant=True, reward="Buy coffee")


def test_completion_can_be_created_only_once_per_day(user):
    habit = create_habit(user)
    HabitCompletion.objects.create(habit=habit)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            HabitCompletion.objects.create(habit=habit)


def test_completions_for_different_days_are_allowed(user):
    habit = create_habit(user)
    completion = HabitCompletion.objects.create(habit=habit)
    yesterday = completion.completed_on - timedelta(days=1)
    HabitCompletion.objects.filter(pk=completion.pk).update(completed_on=yesterday)

    HabitCompletion.objects.create(habit=habit)

    assert HabitCompletion.objects.filter(habit=habit).count() == 2


def test_completions_are_ordered_from_newest_to_oldest(user):
    habit = create_habit(user)
    old = HabitCompletion.objects.create(habit=habit)
    HabitCompletion.objects.filter(pk=old.pk).update(
        completed_on=timezone.localdate() - timedelta(days=3)
    )
    new = HabitCompletion.objects.create(habit=habit)

    assert list(habit.completions.all()) == [new, old]


def test_completions_are_deleted_with_habit(user):
    habit = create_habit(user)
    HabitCompletion.objects.create(habit=habit)
    habit_id = habit.pk

    habit.delete()

    assert not HabitCompletion.objects.filter(habit_id=habit_id).exists()
