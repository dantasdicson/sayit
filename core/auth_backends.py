from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsuarioOuEmailBackend(ModelBackend):
    """Resolve the identifier; Django still verifies passwords and active status."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None
        candidates = list(User.objects.filter(
            Q(username__iexact=username) | Q(email__iexact=username)
        )[:2])
        if len(candidates) != 1:
            # Match Django's dummy hash for missing/ambiguous identifiers.
            User().set_password(password)
            return None
        return super().authenticate(request, username=candidates[0].username, password=password)
