import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import assistant, exports, synthese
from .analyses import Filtres, faits_marquants, indicateurs, projets_en_retard, series
from .importation import FICHIERS, ErreurImport, importer
from .models import DOMAINES, FILIERES, Cohorte, Financement, Jalon, Partenariat, Porteur, Projet, Requete
from .permissions import quota_atteint, saisie_requise
from .qualite import controles, score_qualite

REGIONS = ["Dakar", "Thiès", "Diourbel", "Kaolack", "Saint-Louis", "Ziguinchor", "Kaffrine", "Louga", "Fatick"]


def _contexte_filtres(request):
    filtres = Filtres.depuis_requete(request.GET, voit_noms=request.user.voit_noms)
    return filtres, {
        "filtres": filtres,
        "qs": request.GET.urlencode(),
        "choix": {
            "cohortes": Cohorte.objects.values_list("annee", flat=True),
            "domaines": DOMAINES,
            "statuts": Projet.Statut.choices,
            "profils": Porteur.Profil.choices,
            "regions": REGIONS,
            "filieres": FILIERES,
        },
    }


# --------------------------------------------------------------------------- Tableau de bord
@login_required
def tableau_de_bord(request):
    filtres, ctx = _contexte_filtres(request)
    projets = filtres.projets()
    k = indicateurs(projets)
    s = series(projets)
    ctx.update({
        "k": k,
        "series_json": json.dumps(s, default=str),
        "faits": faits_marquants(projets) if k["idees"] else [],
        "retards": projets_en_retard(projets, limite=8),
        "cohortes": s["cohortes"],
    })
    return render(request, "pilotage/dashboard.html", ctx)


# --------------------------------------------------------------------------- Projets
@login_required
def projets(request):
    filtres, ctx = _contexte_filtres(request)
    qs = filtres.projets().order_by("-cohorte__annee", "code")
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    ctx.update({"page": page, "total": qs.count(), "qs_sans_page": params.urlencode()})
    return render(request, "pilotage/projets.html", ctx)


@login_required
def fiche_projet(request, code):
    p = get_object_or_404(Projet.objects.select_related("porteur", "cohorte"), code=code)
    jalons = [{"j": j, "etat": j.etat()} for j in p.jalons.select_related("projet")]
    return render(request, "pilotage/fiche_projet.html", {
        "p": p, "jalons": jalons, "financements": p.financements.all(), "partenariats": p.partenariats.all(),
        "montant": sum(f.montant for f in p.financements.all() if f.statut == "obtenu"),
    })


# --------------------------------------------------------------------------- Cohortes
@login_required
def cohortes(request):
    s = series(Projet.objects.all())
    return render(request, "pilotage/cohortes.html", {"cohortes": s["cohortes"], "series_json": json.dumps(s, default=str)})


@login_required
def fiche_cohorte(request, annee):
    cohorte = get_object_or_404(Cohorte, annee=annee)
    filtres = Filtres(cohortes=[annee])
    projets = filtres.projets()
    note, erreur = None, None
    if request.method == "POST":
        if quota_atteint(request.user):
            erreur = "Limite horaire d'appels à l'IA atteinte."
        else:
            note, erreur = synthese.rediger(filtres)
            Requete.objects.create(utilisateur=request.user, question=f"Note de synthèse cohorte {annee}",
                                   reponse=note or erreur or "", mode="gemini", succes=bool(note))
    s = series(projets)
    return render(request, "pilotage/fiche_cohorte.html", {
        "cohorte": cohorte, "k": indicateurs(projets), "faits": faits_marquants(projets),
        "series_json": json.dumps(s, default=str), "s": s, "retards": projets_en_retard(projets),
        "note": note, "erreur": erreur,
        "incubes": projets.filter(selectionne=True).order_by("statut", "-progression"),
    })


# --------------------------------------------------------------------------- Assistant
EXEMPLES = [
    "Combien de projets incubés par domaine en 2025 ?",
    "Évolution du taux de réussite par cohorte",
    "Quel domaine a obtenu le plus de financements ?",
    "Part des femmes porteuses par cohorte",
    "Combien de prototypes en agriculture ?",
    "Jalons en retard par domaine",
    "Quelle filière de l'ISEP envoie le plus d'idées ?",
]


@login_required
def assistant_donnees(request):
    resultat = None
    question = ""
    if request.method == "POST":
        question = request.POST.get("question", "").strip()[:500]
        if len(question) < 4:
            messages.error(request, "Posez une question d'au moins quelques mots.")
        elif quota_atteint(request.user):
            messages.warning(request, "Limite horaire atteinte. Réessayez plus tard.")
        else:
            resultat = assistant.repondre(question)
            Requete.objects.create(
                utilisateur=request.user, question=question, specification=resultat.get("spec"),
                reponse=resultat["texte"], mode=resultat["mode"], succes=resultat["succes"],
                duree_ms=resultat["duree_ms"])
            if resultat.get("resultat"):
                r = resultat["resultat"]
                resultat["graphique"] = json.dumps({
                    "type": resultat["spec"]["graphique"], "mesure": assistant.MESURES[resultat["spec"]["mesure"]],
                    "labels": [l["groupe"] for l in r["lignes"]], "valeurs": [l["valeur"] for l in r["lignes"]]})
                resultat["lignes_fmt"] = [
                    {"groupe": l["groupe"], "valeur": assistant.formater(resultat["spec"]["mesure"], l["valeur"])}
                    for l in r["lignes"]]
                resultat["libelle_groupe"] = assistant.LIBELLES_GROUPES.get(resultat["spec"]["grouper_par"] or "", "")
    historique = Requete.objects.filter(utilisateur=request.user).exclude(question__startswith="Note de synthèse")[:10]
    return render(request, "pilotage/assistant.html", {
        "resultat": resultat, "question": question, "exemples": EXEMPLES, "historique": historique,
    })


# --------------------------------------------------------------------------- Exports
@login_required
def export_excel(request):
    filtres = Filtres.depuis_requete(request.GET, voit_noms=request.user.voit_noms)
    reponse = HttpResponse(exports.excel(filtres, request.user.voit_noms),
                           content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    reponse["Content-Disposition"] = f'attachment; filename="ciat_analyses_{date.today():%Y%m%d}.xlsx"'
    return reponse


@login_required
def export_pdf(request):
    filtres = Filtres.depuis_requete(request.GET, voit_noms=request.user.voit_noms)
    titre = "Fiche de synthèse"
    if len(filtres.cohortes) == 1:
        titre = f"Fiche de synthèse — Cohorte {filtres.cohortes[0]}"
    reponse = HttpResponse(exports.pdf(filtres, titre=titre, synthese_ia=request.POST.get("note")),
                           content_type="application/pdf")
    reponse["Content-Disposition"] = f'attachment; filename="ciat_synthese_{date.today():%Y%m%d}.pdf"'
    return reponse


# --------------------------------------------------------------------------- Données : qualité et import
@saisie_requise
def donnees(request):
    if request.method == "POST":
        fichiers = {nom: request.FILES[nom] for nom in FICHIERS if nom in request.FILES}
        if not fichiers:
            messages.error(request, "Sélectionnez au moins un fichier CSV.")
        else:
            try:
                stats = importer(fichiers, remplacer=request.POST.get("remplacer") == "1")
                messages.success(request, "Import réussi : " + ", ".join(f"{v} {k}" for k, v in stats.items()) + ".")
            except ErreurImport as exc:
                messages.error(request, f"Import annulé, aucune donnée modifiée. {exc}")
        return redirect("pilotage:donnees")
    resultats = controles()
    return render(request, "pilotage/donnees.html", {
        "controles": resultats, "score": score_qualite(resultats), "fichiers": FICHIERS,
        "volumes": {
            "Cohortes": Cohorte.objects.count(), "Porteurs": Porteur.objects.count(), "Projets": Projet.objects.count(),
            "Jalons": Jalon.objects.count(),
            "Financements": Financement.objects.count(), "Partenariats": Partenariat.objects.count(),
        },
    })


@saisie_requise
def modele_csv(request, nom):
    if nom not in FICHIERS:
        raise Http404
    from django.conf import settings
    chemin = settings.BASE_DIR / "data" / f"{nom}.csv"
    reponse = HttpResponse(chemin.read_bytes(), content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="{nom}.csv"'
    return reponse


@login_required
def methodologie(request):
    return render(request, "pilotage/methodologie.html")
