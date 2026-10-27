from django.conf import settings


def ai_status(request):
    ctx = {"ia_active": bool(settings.GEMINI_API_KEY)}
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated and u.peut_saisir:
        from accounts.models import User
        ctx["nb_demandes"] = User.objects.filter(demande_en_attente=True).count()
    return ctx
