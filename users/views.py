from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .serializers import RegisterSerializer


@extend_schema(
    tags=["users"],
    summary="Register a new user",
    description=(
        "Creates a new user account. The email is used as the login field. "
        "After registration obtain a JWT pair via POST /api/users/token/."
    ),
)
class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
