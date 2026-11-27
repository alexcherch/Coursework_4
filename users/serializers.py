from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer that creates a user account with an email and a password."""

    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Password is validated with the standard Django validators.",
    )

    class Meta:
        model = User
        fields = ("id", "email", "password", "telegram_id", "telegram_username")
        read_only_fields = ("id",)

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)
