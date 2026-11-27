from datetime import time

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from habits.models import Habit, HabitCompletion

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="StrongPass123")


@pytest.fixture
def other_user():
    return User.objects.create_user(email="other@example.com", password="StrongPass123")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def habit_payload(**overrides):
    payload = {
        "place": "Home",
        "time": "09:00",
        "action": "Stretch",
        "duration": 60,
    }
    payload.update(overrides)
    return payload


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


def test_list_requires_authentication(api_client):
    response = api_client.get(reverse("habit-list"))

    assert response.status_code == 401


def test_create_requires_authentication(api_client):
    response = api_client.post(reverse("habit-list"), habit_payload(), format="json")

    assert response.status_code == 401


def test_public_list_requires_authentication(api_client):
    response = api_client.get(reverse("habit-public"))

    assert response.status_code == 401


def test_create_habit(auth_client, user):
    response = auth_client.post(reverse("habit-list"), habit_payload(), format="json")

    assert response.status_code == 201
    assert response.data["user"] == user.id
    assert response.data["action"] == "Stretch"
    assert Habit.objects.filter(user=user, action="Stretch").exists()


def test_create_habit_with_pleasant_linked_habit(auth_client, user):
    pleasant = create_habit(user, action="Take a bath", is_pleasant=True)

    response = auth_client.post(
        reverse("habit-list"),
        habit_payload(linked_habit=pleasant.id),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["linked_habit"] == pleasant.id


def test_create_rejects_reward_and_linked_habit_together(auth_client, user):
    pleasant = create_habit(user, is_pleasant=True)

    response = auth_client.post(
        reverse("habit-list"),
        habit_payload(reward="Buy coffee", linked_habit=pleasant.id),
        format="json",
    )

    assert response.status_code == 400
    assert "reward" in response.data
    assert "linked_habit" in response.data


def test_create_rejects_too_long_duration(auth_client):
    response = auth_client.post(
        reverse("habit-list"),
        habit_payload(duration=121),
        format="json",
    )

    assert response.status_code == 400
    assert "duration" in response.data


def test_create_rejects_periodicity_out_of_range(auth_client):
    response = auth_client.post(
        reverse("habit-list"),
        habit_payload(periodicity=8),
        format="json",
    )

    assert response.status_code == 400
    assert "periodicity" in response.data


def test_create_rejects_pleasant_habit_with_reward(auth_client):
    response = auth_client.post(
        reverse("habit-list"),
        habit_payload(is_pleasant=True, reward="Buy coffee"),
        format="json",
    )

    assert response.status_code == 400
    assert "reward" in response.data


def test_create_rejects_linked_habit_of_another_user(auth_client, other_user):
    foreign_pleasant = create_habit(other_user, is_pleasant=True)

    response = auth_client.post(
        reverse("habit-list"),
        habit_payload(linked_habit=foreign_pleasant.id),
        format="json",
    )

    assert response.status_code == 400
    assert "linked_habit" in response.data


def test_create_rejects_linked_habit_that_is_not_pleasant(auth_client, user):
    not_pleasant = create_habit(user, action="Read a book", is_pleasant=False)

    response = auth_client.post(
        reverse("habit-list"),
        habit_payload(linked_habit=not_pleasant.id),
        format="json",
    )

    assert response.status_code == 400
    assert "linked_habit" in response.data


def test_list_returns_only_own_habits(auth_client, user, other_user):
    create_habit(user)
    create_habit(other_user)
    create_habit(other_user, action="Run")

    response = auth_client.get(reverse("habit-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1


def test_list_is_paginated_by_five_habits(auth_client, user):
    for index in range(6):
        create_habit(user, action=f"Habit {index}")

    response = auth_client.get(reverse("habit-list"))

    assert response.status_code == 200
    assert set(response.data) == {"count", "next", "previous", "results"}
    assert response.data["count"] == 6
    assert len(response.data["results"]) == 5
    assert response.data["next"] is not None
    assert response.data["previous"] is None


def test_list_supports_limit_and_offset(auth_client, user):
    for index in range(6):
        create_habit(user, action=f"Habit {index}")

    response = auth_client.get(reverse("habit-list"), {"limit": 2, "offset": 2})

    assert response.status_code == 200
    assert response.data["count"] == 6
    assert len(response.data["results"]) == 2


def test_list_allows_limit_greater_than_five(auth_client, user):
    for index in range(6):
        create_habit(user, action=f"Habit {index}")

    response = auth_client.get(reverse("habit-list"), {"limit": 10})

    assert response.status_code == 200
    assert len(response.data["results"]) == 6


def test_retrieve_own_habit(auth_client, user):
    habit = create_habit(user)

    response = auth_client.get(reverse("habit-detail", args=[habit.id]))

    assert response.status_code == 200
    assert response.data["id"] == habit.id


def test_retrieve_foreign_habit_returns_404(auth_client, other_user):
    foreign_habit = create_habit(other_user)

    response = auth_client.get(reverse("habit-detail", args=[foreign_habit.id]))

    assert response.status_code == 404


def test_update_own_habit(auth_client, user):
    habit = create_habit(user)

    response = auth_client.patch(
        reverse("habit-detail", args=[habit.id]),
        {"action": "Read a book"},
        format="json",
    )

    assert response.status_code == 200
    habit.refresh_from_db()
    assert habit.action == "Read a book"


def test_update_validates_duration(auth_client, user):
    habit = create_habit(user)

    response = auth_client.patch(
        reverse("habit-detail", args=[habit.id]),
        {"duration": 121},
        format="json",
    )

    assert response.status_code == 400
    assert "duration" in response.data


def test_update_foreign_habit_returns_404(auth_client, other_user):
    foreign_habit = create_habit(other_user)

    response = auth_client.patch(
        reverse("habit-detail", args=[foreign_habit.id]),
        {"action": "Hacked"},
        format="json",
    )

    assert response.status_code == 404


def test_delete_own_habit(auth_client, user):
    habit = create_habit(user)

    response = auth_client.delete(reverse("habit-detail", args=[habit.id]))

    assert response.status_code == 204
    assert not Habit.objects.filter(id=habit.id).exists()


def test_delete_foreign_habit_returns_404(auth_client, other_user):
    foreign_habit = create_habit(other_user)

    response = auth_client.delete(reverse("habit-detail", args=[foreign_habit.id]))

    assert response.status_code == 404


def test_public_list_shows_only_public_habits(auth_client, user, other_user):
    create_habit(user, action="Public own", is_public=True)
    create_habit(user, action="Private own")
    create_habit(other_user, action="Public foreign", is_public=True)

    response = auth_client.get(reverse("habit-public"))

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert all(item["is_public"] is True for item in response.data["results"])


def test_foreign_public_habit_cannot_be_modified(auth_client, other_user):
    foreign_public = create_habit(other_user, is_public=True)

    response = auth_client.patch(
        reverse("habit-detail", args=[foreign_public.id]),
        {"action": "Hacked"},
        format="json",
    )

    assert response.status_code == 404


def test_complete_habit(auth_client, user):
    habit = create_habit(user)

    response = auth_client.post(reverse("habit-complete", args=[habit.id]))

    assert response.status_code == 201
    assert response.data["completed_on"] == timezone.localdate().isoformat()
    assert HabitCompletion.objects.filter(habit=habit).count() == 1


def test_complete_habit_twice_returns_200(auth_client, user):
    habit = create_habit(user)

    first = auth_client.post(reverse("habit-complete", args=[habit.id]))
    second = auth_client.post(reverse("habit-complete", args=[habit.id]))

    assert first.status_code == 201
    assert second.status_code == 200
    assert HabitCompletion.objects.filter(habit=habit).count() == 1


def test_complete_foreign_habit_returns_404(auth_client, other_user):
    foreign_habit = create_habit(other_user)

    response = auth_client.post(reverse("habit-complete", args=[foreign_habit.id]))

    assert response.status_code == 404
