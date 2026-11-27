from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Habit, HabitCompletion
from .validators import validate_habit


class HabitSerializer(serializers.ModelSerializer):
    """Serializer for habits with the business rules validation."""

    WRITABLE_FIELDS = (
        "place",
        "time",
        "action",
        "is_pleasant",
        "linked_habit",
        "periodicity",
        "reward",
        "duration",
        "is_public",
    )

    linked_habit = serializers.PrimaryKeyRelatedField(
        queryset=Habit.objects.none(),
        required=False,
        allow_null=True,
        help_text="Pleasant habit of the same user that is done after this one.",
    )

    class Meta:
        model = Habit
        fields = (
            "id",
            "user",
            "place",
            "time",
            "action",
            "is_pleasant",
            "linked_habit",
            "periodicity",
            "reward",
            "duration",
            "is_public",
            "last_reminded_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "last_reminded_at",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["linked_habit"].queryset = Habit.objects.filter(
                user=request.user,
                is_pleasant=True,
            )

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request is not None else None

        data = {}
        for field in self.WRITABLE_FIELDS:
            if field in attrs:
                data[field] = attrs[field]
            elif self.instance is not None:
                data[field] = getattr(self.instance, field)

        candidate = Habit(user=user, **data)

        try:
            validate_habit(candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        return attrs


class HabitCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitCompletion
        fields = ("id", "habit", "completed_on")
        read_only_fields = ("id", "habit", "completed_on")
