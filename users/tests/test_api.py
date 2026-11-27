import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_register_creates_user(client):
    response = client.post(
        reverse("register"),
        {"email": "new@example.com", "password": "StrongPass123"},
        format="json",
    )

    assert response.status_code == 201
    assert "password" not in response.data
    assert response.data["email"] == "new@example.com"

    user = User.objects.get(email="new@example.com")
    assert user.check_password("StrongPass123")
    assert user.is_staff is False
    assert user.is_superuser is False


def test_register_accepts_telegram_fields(client):
    response = client.post(
        reverse("register"),
        {
            "email": "tg@example.com",
            "password": "StrongPass123",
            "telegram_id": 123456789,
            "telegram_username": "tg_user",
        },
        format="json",
    )

    assert response.status_code == 201

    user = User.objects.get(email="tg@example.com")
    assert user.telegram_id == 123456789
    assert user.telegram_username == "tg_user"


def test_register_rejects_duplicate_email(client):
    User.objects.create_user(email="dup@example.com", password="StrongPass123")

    response = client.post(
        reverse("register"),
        {"email": "dup@example.com", "password": "StrongPass123"},
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.data


def test_register_rejects_weak_password(client):
    response = client.post(
        reverse("register"),
        {"email": "weak@example.com", "password": "123"},
        format="json",
    )

    assert response.status_code == 400
    assert "password" in response.data


def test_register_rejects_invalid_email(client):
    response = client.post(
        reverse("register"),
        {"email": "not-an-email", "password": "StrongPass123"},
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.data


def test_obtain_token_with_valid_credentials(client):
    User.objects.create_user(email="login@example.com", password="StrongPass123")

    response = client.post(
        reverse("token-obtain-pair"),
        {"email": "login@example.com", "password": "StrongPass123"},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_obtain_token_with_wrong_password(client):
    User.objects.create_user(email="login@example.com", password="StrongPass123")

    response = client.post(
        reverse("token-obtain-pair"),
        {"email": "login@example.com", "password": "WrongPass123"},
        format="json",
    )

    assert response.status_code == 401


def test_refresh_token(client):
    User.objects.create_user(email="login@example.com", password="StrongPass123")
    tokens = client.post(
        reverse("token-obtain-pair"),
        {"email": "login@example.com", "password": "StrongPass123"},
        format="json",
    ).data

    response = client.post(
        reverse("token-refresh"),
        {"refresh": tokens["refresh"]},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
