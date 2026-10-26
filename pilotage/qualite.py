"""Contrôle qualité des données : complétude et cohérence métier."""
from django.db.models import F, Q

from .models import Financement, Jalon, Porteur, Projet


def controles():
    """Retourne une liste de contrôles : {regle, gravite, nb, exemples}."""
    resultats = []

    def ajouter(regle, gravite, qs, libelle=lambda o: str(o)):
        """libelle renvoie un texte ; s'il commence par un code projet, un lien vers la fiche est proposé."""
        exemples = []
        for o in qs[:5]:
            texte = libelle(o)
            code = texte.split(" ")[0] if texte.startswith("CIAT-") else ""
            exemples.append({"code": code, "texte": texte})
        resultats.append({"regle": regle, "gravite": gravite, "nb": qs.count(), "exemples": exemples})

    ajouter("Projet sélectionné sans note du comité", "Moyenne",
            Projet.objects.filter(selectionne=True, score_comite__isnull=True), lambda p: p.code)
    ajouter("Projet sélectionné sans être présélectionné", "Haute",
            Projet.objects.filter(selectionne=True, preselectionne=False), lambda p: p.code)
    ajouter("Prototype déclaré sans sélection en incubation", "Haute",
            Projet.objects.filter(selectionne=False, date_prototype__isnull=False), lambda p: p.code)
    ajouter("Date de sélection antérieure au dépôt", "Haute",
            Projet.objects.filter(date_selection__lt=F("date_depot")), lambda p: p.code)
    ajouter("Statut d'incubation sans sélection", "Haute",
            Projet.objects.filter(selectionne=False, statut__in=["incubation", "sorti", "abandonne"]), lambda p: p.code)
    ajouter("Note du comité hors de 0 à 100", "Haute", Projet.objects.filter(score_comite__gt=100), lambda p: p.code)
    ajouter("Progression hors de 0 à 100 %", "Moyenne", Projet.objects.filter(progression__gt=100), lambda p: p.code)
    ajouter("Financement daté avant le dépôt du projet", "Moyenne",
            Financement.objects.filter(date__lt=F("projet__date_depot")).select_related("projet"),
            lambda f: f"{f.projet.code} ({f.date:%d/%m/%Y})")
    ajouter("Financement d'un montant nul ou supérieur à 100 M FCFA", "Moyenne",
            Financement.objects.filter(Q(montant=0) | Q(montant__gt=100_000_000)).select_related("projet"),
            lambda f: f.projet.code)
    ajouter("Jalon sans échéance", "Moyenne", Jalon.objects.filter(echeance__isnull=True), lambda j: j.titre)
    ajouter("Porteur sans région renseignée", "Faible", Porteur.objects.filter(region=""), lambda p: p.code)
    return resultats


def score_qualite(resultats=None):
    """Part des contrôles sans anomalie, en %."""
    resultats = resultats or controles()
    ok = sum(1 for r in resultats if r["nb"] == 0)
    return round(100 * ok / len(resultats)) if resultats else 100
