from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone


def saisie_requise(vue):
    """Réserve une vue aux coordonnateurs et administrateurs (import, qualité, données nominatives)."""

    @login_required
    @wraps(vue)
    def _vue(request, *args, **kwargs):
        if not request.user.peut_saisir:
            raise PermissionDenied("Accès réservé aux coordonnateurs du CIAT.")
        return vue(request, *args, **kwargs)

    return _vue


def quota_atteint(user) -> bool:
    from .models import Requete

    depuis = timezone.now() - timedelta(hours=1)
    return Requete.objects.filter(utilisateur=user, cree_le__gte=depuis).count() >= settings.AI_RATE_LIMIT_PER_HOUR
