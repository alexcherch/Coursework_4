from django.contrib import admin

from .models import Habit, HabitCompletion


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "user",
        "time",
        "periodicity",
        "is_pleasant",
        "is_public",
    )
    list_filter = ("is_pleasant", "is_public", "periodicity")
    search_fields = ("action", "place", "user__email")
    autocomplete_fields = ("user", "linked_habit")
    readonly_fields = ("last_reminded_at", "created_at", "updated_at")


@admin.register(HabitCompletion)
class HabitCompletionAdmin(admin.ModelAdmin):
    list_display = ("id", "habit", "completed_on")
    search_fields = ("habit__action", "habit__user__email")
    readonly_fields = ("habit", "completed_on")

    def has_add_permission(self, request):
        return False
