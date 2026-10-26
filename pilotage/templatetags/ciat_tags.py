import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from ..analyses import fcfa as _fcfa
from ..analyses import fr as _fr

register = template.Library()


@register.filter
def fcfa(v):
    return _fcfa(v or 0)


@register.filter
def nombre(v):
    """Nombre au format français (virgule décimale, espace des milliers)."""
    if isinstance(v, float):
        return _fr(v)
    if isinstance(v, int):
        return f"{v:,}".replace(",", " ")
    return v


@register.filter
def gras(texte):
    """**texte** → <strong>texte</strong> (après échappement du HTML)."""
    return mark_safe(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escape(texte)))


@register.simple_tag(takes_context=True)
def coche(context, nom, valeur):
    """Renvoie « selected » si la valeur figure dans le paramètre GET (listes acceptées)."""
    valeurs = context["request"].GET.getlist(nom)
    return "selected" if str(valeur) in valeurs else ""
