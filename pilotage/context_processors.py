from django.conf import settings


def ai_status(request):
    return {"ia_active": bool(settings.GEMINI_API_KEY)}
