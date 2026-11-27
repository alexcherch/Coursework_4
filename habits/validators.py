from django.core.exceptions import ValidationError

MAX_DURATION_SECONDS = 120
MIN_PERIODICITY_DAYS = 1
MAX_PERIODICITY_DAYS = 7


def validate_habit(habit):
    """Validate business rules of a habit that depend on several fields."""
    errors = {}

    if habit.reward and habit.linked_habit_id:
        message = "A habit cannot have both a reward and a linked habit."
        errors["reward"] = message
        errors["linked_habit"] = message

    if habit.is_pleasant:
        if habit.reward:
            errors.setdefault("reward", "A pleasant habit cannot have a reward.")
        if habit.linked_habit_id:
            errors.setdefault(
                "linked_habit",
                "A pleasant habit cannot have a linked habit.",
            )

    if habit.linked_habit_id:
        linked_habit = habit.linked_habit

        if not linked_habit.is_pleasant:
            errors["linked_habit"] = "A linked habit must be a pleasant habit."
        elif habit.user_id and linked_habit.user_id != habit.user_id:
            errors["linked_habit"] = "A linked habit must belong to the same user."

        if habit.pk and linked_habit.pk == habit.pk:
            errors["linked_habit"] = "A habit cannot be linked to itself."

    if errors:
        raise ValidationError(errors)
