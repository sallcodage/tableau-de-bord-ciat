"""
Assistant d'interrogation des données en langage naturel.

Principe de sécurité : le modèle ne produit JAMAIS de SQL ni de chiffre.
  1. Gemini traduit la question en une spécification JSON (mesure, regroupement, filtres) ;
  2. la spécification est validée contre des listes blanches (valider) ;
  3. le calcul est fait par l'ORM Django via le moteur d'analyse (executer) ;
  4. la phrase de réponse est construite à partir des chiffres calculés (phrase).
Sans clé API, un analyseur à base de règles (analyser_regles) prend le relais.
"""
import json
import logging
import re
import time
import unicodedata
from datetime import date

from django.conf import settings
from django.db.models import Avg, Count, Q, Sum

from .analyses import Filtres, fcfa, fr, pct
from .models import DOMAINES, DOMAINES_COURTS, FILIERES_PLATES, Cohorte, Financement, Jalon, Partenariat, Porteur, Projet

logger = logging.getLogger("pilotage")

MESURES = {
    "nb_idees": "Nombre d'idées reçues",
    "nb_preselectionnes": "Nombre de projets présélectionnés",
    "nb_selectionnes": "Nombre de projets incubés (sélectionnés)",
    "nb_prototypes": "Nombre de prototypes réalisés",
    "nb_sortis": "Nombre de projets sortis (lancés)",
    "nb_abandons": "Nombre d'abandons",
    "taux_selection": "Taux de sélection (%)",
    "taux_prototype": "Taux de prototypes parmi les incubés (%)",
    "taux_reussite": "Taux de réussite en incubation (%)",
    "montant_finance": "Financements obtenus (FCFA)",
    "nb_financements": "Nombre de financements obtenus",
    "nb_jalons_retard": "Jalons réalisés en retard ou en retard",
    "nb_partenariats": "Nombre de partenariats liés aux projets",
    "emplois_crees": "Emplois créés",
    "progression_moyenne": "Progression moyenne (%)",
    "part_femmes": "Part des femmes porteuses (%)",
}
GROUPES = {
    "cohorte": "cohorte__annee", "domaine": "domaine", "genre": "porteur__genre", "statut": "statut",
    "region": "porteur__region", "profil": "porteur__profil", "tranche_age": "porteur__tranche_age",
    "filiere": "porteur__filiere",
}
LIBELLES_GROUPES = {"cohorte": "Cohorte", "domaine": "Domaine", "genre": "Genre", "statut": "Statut",
                    "region": "Région", "profil": "Profil du porteur", "tranche_age": "Tranche d'âge",
                    "filiere": "Filière ISEP"}
REGIONS = ["Dakar", "Thiès", "Diourbel", "Kaolack", "Saint-Louis", "Ziguinchor", "Kaffrine", "Louga", "Fatick",
           "Tambacounda", "Kolda", "Matam", "Kédougou", "Sédhiou"]

SYSTEME = f"""Tu traduis des questions en français sur les données de l'incubateur du CIAT
(ISEP Amadou Trawaré, Sénégal) en une requête JSON. Tu ne calcules rien et n'inventes aucun chiffre.

Réponds UNIQUEMENT avec un objet JSON de la forme :
{{"mesure": <une clé de MESURES>, "grouper_par": <une clé de GROUPES ou null>,
  "filtres": {{"cohortes": [années], "domaines": [codes], "statuts": [codes], "genre": "F"|"H"|"",
              "region": "", "profil": "", "du": "AAAA-MM-JJ"|"", "au": "AAAA-MM-JJ"|""}},
  "tri": "desc"|"asc"|null, "limite": entier|null, "graphique": "barres"|"ligne"|"camembert"|"aucun"}}

MESURES : {json.dumps(MESURES, ensure_ascii=False)}
GROUPES : {list(GROUPES)}
Codes de domaines : {json.dumps(dict(DOMAINES), ensure_ascii=False)}
Codes de statuts : {json.dumps(dict(Projet.Statut.choices), ensure_ascii=False)}
Profils : {list(Porteur.Profil.values)} · Régions : {REGIONS}
Filières de l'ISEP (regroupement « filiere ») : {json.dumps(dict(FILIERES_PLATES), ensure_ascii=False)}
Cohortes disponibles : 2024, 2025, 2026, 2027 (une cohorte = l'appel à projets de cette année).

Règles : « par X » → grouper_par ; « évolution » ou « par année » → grouper_par cohorte et graphique ligne ;
« quel domaine… le plus » → grouper_par domaine, tri desc, limite 1 ou plus ; une seule valeur → graphique aucun.
Si la question ne porte pas sur ces données (météo, opinion, données personnelles d'un porteur…),
réponds {{"hors_perimetre": true}}."""


class RequeteInvalide(Exception):
    pass


# --------------------------------------------------------------------------- Validation
def valider(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise RequeteInvalide("Format inattendu.")
    if spec.get("hors_perimetre"):
        return {"hors_perimetre": True}
    mesure = spec.get("mesure")
    if mesure not in MESURES:
        raise RequeteInvalide("Mesure non reconnue.")
    groupe = spec.get("grouper_par") or None
    if groupe is not None and groupe not in GROUPES:
        raise RequeteInvalide("Regroupement non reconnu.")
    f = spec.get("filtres") or {}
    if not isinstance(f, dict):
        raise RequeteInvalide("Filtres invalides.")

    def liste(cle, autorises, conv=str):
        valeurs = f.get(cle) or []
        if not isinstance(valeurs, list):
            valeurs = [valeurs]
        sortie = []
        for v in valeurs:
            try:
                v = conv(v)
            except (TypeError, ValueError):
                continue
            if v in autorises:
                sortie.append(v)
        return sortie

    def jour(cle):
        try:
            return date.fromisoformat(f.get(cle) or "").isoformat()
        except ValueError:
            return ""

    annees = set(Cohorte.objects.values_list("annee", flat=True))
    propre = {
        "mesure": mesure,
        "grouper_par": groupe,
        "filtres": {
            "cohortes": liste("cohortes", annees, int),
            "domaines": liste("domaines", dict(DOMAINES)),
            "statuts": liste("statuts", Projet.Statut.values),
            "genre": f.get("genre") if f.get("genre") in ("F", "H") else "",
            "region": f.get("region") if f.get("region") in REGIONS else "",
            "profil": f.get("profil") if f.get("profil") in Porteur.Profil.values else "",
            "du": jour("du"), "au": jour("au"),
        },
        "tri": spec.get("tri") if spec.get("tri") in ("asc", "desc") else None,
        "limite": spec.get("limite") if isinstance(spec.get("limite"), int) and 0 < spec["limite"] <= 20 else None,
        "graphique": spec.get("graphique") if spec.get("graphique") in ("barres", "ligne", "camembert", "aucun") else "barres",
    }
    if propre["grouper_par"] is None:
        propre["graphique"] = "aucun"
    return propre


# --------------------------------------------------------------------------- Exécution
def _valeur(mesure, qs):
    """Calcule une mesure sur un queryset de projets."""
    ids = qs.values("id")
    if mesure == "nb_idees":
        return qs.count()
    if mesure == "nb_preselectionnes":
        return qs.filter(preselectionne=True).count()
    if mesure == "nb_selectionnes":
        return qs.filter(selectionne=True).count()
    if mesure == "nb_prototypes":
        return qs.filter(selectionne=True, date_prototype__isnull=False).count()
    if mesure == "nb_sortis":
        return qs.filter(statut=Projet.Statut.SORTI).count()
    if mesure == "nb_abandons":
        return qs.filter(statut=Projet.Statut.ABANDONNE).count()
    if mesure == "taux_selection":
        return pct(qs.filter(selectionne=True).count(), qs.count())
    if mesure == "taux_prototype":
        return pct(qs.filter(selectionne=True, date_prototype__isnull=False).count(), qs.filter(selectionne=True).count())
    if mesure == "taux_reussite":
        s, a = qs.filter(statut=Projet.Statut.SORTI).count(), qs.filter(statut=Projet.Statut.ABANDONNE).count()
        return pct(s, s + a)
    if mesure == "montant_finance":
        return Financement.objects.filter(projet__in=ids, statut="obtenu").aggregate(s=Sum("montant"))["s"] or 0
    if mesure == "nb_financements":
        return Financement.objects.filter(projet__in=ids, statut="obtenu").count()
    if mesure == "nb_jalons_retard":
        jal = Jalon.objects.filter(projet__in=ids).select_related("projet")
        return sum(1 for j in jal if j.etat() in (Jalon.Etat.EN_RETARD, Jalon.Etat.REALISE_RETARD))
    if mesure == "nb_partenariats":
        return Partenariat.objects.filter(projet__in=ids).count()
    if mesure == "emplois_crees":
        return qs.aggregate(s=Sum("emplois_crees"))["s"] or 0
    if mesure == "progression_moyenne":
        return round(qs.filter(statut=Projet.Statut.INCUBATION).aggregate(m=Avg("progression"))["m"] or 0)
    if mesure == "part_femmes":
        return pct(qs.filter(porteur__genre="F").count(), qs.count())
    raise RequeteInvalide("Mesure non gérée.")


def _libelle_groupe(groupe, valeur):
    if groupe == "domaine":
        return DOMAINES_COURTS.get(valeur, valeur)
    if groupe == "genre":
        return dict(Porteur.Genre.choices).get(valeur, valeur)
    if groupe == "statut":
        return dict(Projet.Statut.choices).get(valeur, valeur)
    if groupe == "profil":
        return dict(Porteur.Profil.choices).get(valeur, valeur)
    if groupe == "filiere":
        return dict(FILIERES_PLATES).get(valeur, "Porteur externe")
    return str(valeur)


def executer(spec: dict):
    f = spec["filtres"]
    filtres = Filtres(
        du=date.fromisoformat(f["du"]) if f["du"] else None, au=date.fromisoformat(f["au"]) if f["au"] else None,
        cohortes=f["cohortes"], domaines=f["domaines"], statuts=f["statuts"], genre=f["genre"],
        profil=f["profil"], region=f["region"],
    )
    qs = filtres.projets()
    mesure, groupe = spec["mesure"], spec["grouper_par"]
    if not groupe:
        return {"valeur": _valeur(mesure, qs), "lignes": [], "filtres": filtres}
    champ = GROUPES[groupe]
    if groupe == "filiere":  # les porteurs externes n'ont pas de filière ISEP
        qs = qs.exclude(porteur__filiere="")
    valeurs = sorted(set(qs.values_list(champ, flat=True)))
    lignes = [{"groupe": _libelle_groupe(groupe, v), "valeur": _valeur(mesure, qs.filter(**{champ: v}))}
              for v in valeurs]
    if spec["tri"]:
        lignes.sort(key=lambda r: r["valeur"], reverse=spec["tri"] == "desc")
    if spec["limite"]:
        lignes = lignes[: spec["limite"]]
    return {"valeur": None, "lignes": lignes, "filtres": filtres}


def formater(mesure, v):
    if mesure == "montant_finance":
        return fcfa(v)
    if mesure.startswith("taux") or mesure in ("part_femmes", "progression_moyenne"):
        return f"{fr(v)} %"
    return fr(v)


def phrase(spec, resultat):
    mesure = spec["mesure"]
    perimetre = resultat["filtres"].description()
    perimetre = "" if perimetre == "Toutes les données" else f" ({perimetre})"
    if resultat["valeur"] is not None:
        return f"{MESURES[mesure]}{perimetre} : **{formater(mesure, resultat['valeur'])}**."
    if not resultat["lignes"]:
        return "Aucune donnée ne correspond à ces critères."
    if spec["limite"] == 1:
        top = resultat["lignes"][0]
        return (f"{LIBELLES_GROUPES[spec['grouper_par']]} en tête{perimetre} : **{top['groupe']}** "
                f"avec {formater(mesure, top['valeur'])}.")
    top = max(resultat["lignes"], key=lambda r: r["valeur"])
    return (f"{MESURES[mesure]} par {LIBELLES_GROUPES[spec['grouper_par']].lower()}{perimetre}. "
            f"Valeur la plus élevée : **{top['groupe']}** ({formater(mesure, top['valeur'])}).")


# --------------------------------------------------------------------------- Traduction de la question
def analyser_gemini(question: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    reponse = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=f"Question : {question}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEME, temperature=0, max_output_tokens=400,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return json.loads(reponse.text)


def _norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


MOTS_MESURES = [  # ordre important : les expressions les plus précises d'abord
    ("taux de selection", "taux_selection"), ("taux de reussite", "taux_reussite"),
    ("taux de prototype", "taux_prototype"), ("part des femmes", "part_femmes"), ("pourcentage de femmes", "part_femmes"),
    ("financement", "montant_finance"), ("fcfa", "montant_finance"), ("montant", "montant_finance"),
    ("argent", "montant_finance"), ("retard", "nb_jalons_retard"), ("partenari", "nb_partenariats"),
    ("emploi", "emplois_crees"), ("progression", "progression_moyenne"), ("avancement", "progression_moyenne"),
    ("prototype", "nb_prototypes"), ("abandon", "nb_abandons"), ("sorti", "nb_sortis"), ("lance", "nb_sortis"),
    ("preselection", "nb_preselectionnes"), ("selectionn", "nb_selectionnes"), ("incub", "nb_selectionnes"),
    ("idee", "nb_idees"), ("candidature", "nb_idees"), ("projet", "nb_idees"), ("depot", "nb_idees"),
    ("porteu", "nb_idees"), ("femmes", "nb_idees"),
]
MOTS_DOMAINES = {"agri": "agriculture", "agro": "agriculture", "numerique": "tic", "tic": "tic", " ia ": "tic",
                 "energie": "energie", "solaire": "energie", "mecanique": "mecanique", "sante": "sante",
                 "pharma": "sante", "education": "education", "formation": "education", "service": "services"}
MOTS_GROUPES = {"par cohorte": "cohorte", "par annee": "cohorte", "evolution": "cohorte", "par domaine": "domaine",
                "quel domaine": "domaine", "par genre": "genre", "par sexe": "genre", "femmes et hommes": "genre",
                "par statut": "statut", "par region": "region", "quelle region": "region",
                "par profil": "profil", "par age": "tranche_age", "par tranche": "tranche_age",
                "par filiere": "filiere", "quelle filiere": "filiere", "filiere": "filiere"}
HORS_SUJET = ["meteo", "temps qu'il fait", "president", "capitale", "recette", "football", "blague",
              "telephone de", "adresse de", "mot de passe"]


def analyser_regles(question: str) -> dict:
    q = f" {_norm(question)} "
    if any(m in q for m in HORS_SUJET):
        return {"hors_perimetre": True}
    mesure = next((m for mot, m in MOTS_MESURES if mot in q), None)
    if mesure is None:
        return {"hors_perimetre": True}
    groupe = next((g for mot, g in MOTS_GROUPES.items() if mot in q), None)
    domaines = sorted({code for mot, code in MOTS_DOMAINES.items() if mot in q})
    if groupe == "domaine":
        domaines = []
    cohortes = [int(a) for a in re.findall(r"\b(202[3-9])\b", q)]
    genre = "F" if re.search(r"\b(femmes?|porteuses?|feminin)\b", q) and groupe != "genre" and mesure != "part_femmes" else ""
    region = next((r for r in REGIONS if _norm(r) in q), "")
    plus = re.search(r"\b(le plus|la plus|les plus|meilleur|premier)\b", q)
    return {
        "mesure": mesure, "grouper_par": groupe,
        "filtres": {"cohortes": cohortes if groupe != "cohorte" else [], "domaines": domaines, "statuts": [],
                    "genre": genre, "region": region, "profil": "", "du": "", "au": ""},
        "tri": "desc" if plus or groupe in ("domaine", "region") else None,
        "limite": 1 if plus and groupe else None,
        "graphique": "ligne" if groupe == "cohorte" else ("barres" if groupe else "aucun"),
    }


def repondre(question: str):
    """Point d'entrée : retourne un dict prêt à afficher et à journaliser."""
    debut = time.monotonic()
    mode = "regles"
    try:
        if settings.GEMINI_API_KEY:
            try:
                brute, mode = analyser_gemini(question), "gemini"
            except Exception:  # quota, réseau, JSON invalide → repli sur les règles
                logger.exception("Analyse Gemini impossible, repli sur les règles")
                brute = analyser_regles(question)
        else:
            brute = analyser_regles(question)
        spec = valider(brute)
        if spec.get("hors_perimetre"):
            return {"succes": False, "mode": "refus", "spec": spec, "duree_ms": int((time.monotonic() - debut) * 1000),
                    "texte": "Je ne peux répondre qu'aux questions sur les données de l'incubateur du CIAT "
                             "(idées, sélection, prototypes, jalons, financements, partenariats, cohortes)."}
        resultat = executer(spec)
        return {"succes": True, "mode": mode, "spec": spec, "resultat": resultat, "texte": phrase(spec, resultat),
                "duree_ms": int((time.monotonic() - debut) * 1000)}
    except RequeteInvalide as exc:
        return {"succes": False, "mode": mode, "spec": None, "duree_ms": int((time.monotonic() - debut) * 1000),
                "texte": f"Je n'ai pas compris la question ({exc}). Essayez par exemple : "
                         "« Combien de projets incubés par domaine en 2025 ? »"}
