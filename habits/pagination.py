from rest_framework.pagination import LimitOffsetPagination


class HabitPagination(LimitOffsetPagination):
    """Pagination with 5 habits per page by default (limit/offset)."""

    default_limit = 5
