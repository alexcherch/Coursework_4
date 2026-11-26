from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Habit, HabitCompletion
from .pagination import HabitPagination
from .permissions import IsOwner
from .serializers import HabitCompletionSerializer, HabitSerializer


@extend_schema_view(
    list=extend_schema(tags=["habits"], summary="List habits of the current user"),
    create=extend_schema(tags=["habits"], summary="Create a habit"),
    retrieve=extend_schema(tags=["habits"], summary="Get a habit"),
    update=extend_schema(tags=["habits"], summary="Update a habit"),
    partial_update=extend_schema(tags=["habits"], summary="Partially update a habit"),
    destroy=extend_schema(tags=["habits"], summary="Delete a habit"),
)
class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    pagination_class = HabitPagination
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Habit.objects.none()
        return Habit.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(tags=["habits"], summary="List public habits")
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def public(self, request):
        queryset = Habit.objects.filter(is_public=True).select_related("user")
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["habits"],
        summary="Mark a habit as completed today",
        responses={
            200: HabitCompletionSerializer,
            201: HabitCompletionSerializer,
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsOwner])
    def complete(self, request, pk=None):
        habit = self.get_object()
        completion, created = HabitCompletion.objects.get_or_create(
            habit=habit,
            completed_on=timezone.localdate(),
        )
        serializer = HabitCompletionSerializer(completion)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)
