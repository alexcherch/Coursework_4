import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_create_user_with_email():
    user = User.objects.create_user(email="user@example.com", password="StrongPass123")

    assert user.email == "user@example.com"
    assert user.check_password("StrongPass123")
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False


def test_create_user_normalizes_email_domain():
    user = User.objects.create_user(email="USER@EXAMPLE.COM", password="StrongPass123")

    assert user.email == "USER@example.com"


def test_create_user_without_email_raises():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="StrongPass123")


def test_create_superuser():
    user = User.objects.create_superuser(email="admin@example.com", password="StrongPass123")

    assert user.is_staff is True
    assert user.is_superuser is True


def test_create_superuser_requires_staff_flag():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123",
            is_staff=False,
        )


def test_create_superuser_requires_superuser_flag():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123",
            is_superuser=False,
        )


def test_email_is_unique():
    User.objects.create_user(email="user@example.com", password="StrongPass123")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create_user(email="user@example.com", password="StrongPass123")


def test_email_is_login_field():
    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []


def test_telegram_fields_are_optional():
    user = User.objects.create_user(email="user@example.com", password="StrongPass123")

    assert user.telegram_id is None
    assert user.telegram_username == ""


def test_string_representation_is_email():
    user = User(email="user@example.com")

    assert str(user) == "user@example.com"
