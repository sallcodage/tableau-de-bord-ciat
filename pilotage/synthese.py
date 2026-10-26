"""
Note de synthèse rédigée par l'IA à partir des indicateurs DÉJÀ CALCULÉS.
Le modèle ne reçoit que des agrégats (aucun nom de porteur) et a l'interdiction d'ajouter des chiffres.
"""
import json
import logging
import re

from django.conf import settings

from .analyses import faits_marquants, indicateurs, series

logger = logging.getLogger("pilotage")

SYSTEME = """Tu es analyste au CIAT (ISEP Amadou Trawaré, Diamniadio, Sénégal).
Rédige une note de synthèse destinée à la direction, en français, en 3 courts paragraphes :
1. Résultats (ce que montrent les indicateurs) ;
2. Points d'attention (retards, abandons, écarts femmes/hommes, domaines faibles) ;
3. Recommandations concrètes (3 maximum).
RÈGLES : utilise UNIQUEMENT les chiffres fournis dans le JSON, sans en calculer de nouveaux ni en inventer ;
montants en FCFA ; 180 mots maximum ; pas de titre ni de liste à puces ; ton factuel."""


def rediger(filtres):
    """Retourne (texte, None) ou (None, message d'erreur)."""
    if not settings.GEMINI_API_KEY:
        return None, "Ajoutez une clé GEMINI_API_KEY pour générer la note de synthèse."
    projets = filtres.projets()
    k, s = indicateurs(projets), series(projets)
    donnees = {
        "perimetre": filtres.description(),
        "indicateurs": k,
        "cohortes": s["cohortes"],
        "domaines": s["domaines"],
        "genre": s["genre"],
        "retards_par_domaine": [{x: d[x] for x in ("domaine", "taux_retard")} for d in s["jalons_domaine"]],
        "faits_marquants": faits_marquants(projets),
    }
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        reponse = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="Données (JSON) :\n" + json.dumps(donnees, ensure_ascii=False, default=str),
            config=types.GenerateContentConfig(system_instruction=SYSTEME, temperature=0.3, max_output_tokens=600,
                                               thinking_config=types.ThinkingConfig(thinking_budget=0)),
        )
        texte = (reponse.text or "").strip()
    except Exception:
        logger.exception("Synthèse IA impossible")
        return None, "Le service d'IA est momentanément indisponible."
    # Contrôle : tout nombre cité doit exister dans les données fournies
    autorises = set(re.findall(r"\d+(?:[.,]\d+)?", json.dumps(donnees, default=str)))
    autorises |= {a.replace(".", ",") for a in autorises}
    cites = set(re.findall(r"\d+(?:[.,]\d+)?", texte.replace(" ", "").replace(" ", "")))
    inconnus = sorted(c for c in cites if c not in autorises and len(c) > 1)
    if inconnus:
        texte += f"\n\n⚠️ Vérification automatique : chiffres non retrouvés dans les données ({', '.join(inconnus[:5])}). À contrôler."
    return texte, None
