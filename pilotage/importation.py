"""
Import des fichiers CSV (séparateur « ; », UTF-8, dates AAAA-MM-JJ) dans la base.

L'import est idempotent (mise à jour par code) et transactionnel : une erreur de format annule tout.
Les incohérences métier (dates, notes…) ne bloquent pas l'import : elles sont signalées par le
contrôle qualité (qualite.py), comme dans un vrai processus de pilotage.
"""
import csv
import io
from datetime import date
from pathlib import Path

from django.db import transaction

from .models import Cohorte, Financement, Jalon, Partenariat, Porteur, Projet

FICHIERS = ["cohortes", "porteurs", "projets", "jalons", "financements", "partenariats"]


class ErreurImport(Exception):
    pass


def _d(valeur):
    return date.fromisoformat(valeur) if valeur else None


def _lire(source):
    if isinstance(source, (str, Path)):
        texte = Path(source).read_text(encoding="utf-8-sig")
    else:
        texte = source.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(texte), delimiter=";"))


@transaction.atomic
def importer(sources: dict, remplacer=False):
    """sources : {"projets": chemin_ou_fichier, ...}. Retourne un dict de compteurs."""
    stats = {}
    try:
        if remplacer:
            for m in (Jalon, Financement, Partenariat, Projet, Porteur, Cohorte):
                m.objects.all().delete()

        if "cohortes" in sources:
            lignes = _lire(sources["cohortes"])
            for r in lignes:
                Cohorte.objects.update_or_create(annee=int(r["annee"]), defaults={
                    "nom": r["nom"], "date_debut": _d(r["date_debut"]), "date_fin": _d(r["date_fin"])})
            stats["cohortes"] = len(lignes)

        if "porteurs" in sources:
            lignes = _lire(sources["porteurs"])
            for r in lignes:
                Porteur.objects.update_or_create(code=r["code"], defaults={
                    **{k: r[k] for k in ("prenom", "nom", "genre", "tranche_age", "profil", "region")},
                    "filiere": r.get("filiere", "") or ""})
            stats["porteurs"] = len(lignes)

        if "projets" in sources:
            cohortes = {c.annee: c for c in Cohorte.objects.all()}
            porteurs = {p.code: p for p in Porteur.objects.all()}
            lignes = _lire(sources["projets"])
            for n, r in enumerate(lignes, start=2):
                if int(r["cohorte"]) not in cohortes or r["porteur"] not in porteurs:
                    raise ErreurImport(f"projets.csv ligne {n} : cohorte ou porteur inconnu ({r['code']})")
                Projet.objects.update_or_create(code=r["code"], defaults={
                    "titre": r["titre"], "domaine": r["domaine"], "cohorte": cohortes[int(r["cohorte"])],
                    "porteur": porteurs[r["porteur"]], "nb_membres": int(r["nb_membres"] or 1),
                    "date_depot": _d(r["date_depot"]), "preselectionne": r["preselectionne"] == "1",
                    "selectionne": r["selectionne"] == "1",
                    "score_comite": int(r["score_comite"]) if r["score_comite"] else None,
                    "date_selection": _d(r["date_selection"]), "date_prototype": _d(r["date_prototype"]),
                    "statut": r["statut"], "progression": int(r["progression"] or 0), "mentor": r["mentor"],
                    "emplois_crees": int(r["emplois_crees"] or 0),
                })
            stats["projets"] = len(lignes)

        projets = {p.code: p for p in Projet.objects.all()}

        def projet(code, fichier, n):
            if code and code not in projets:
                raise ErreurImport(f"{fichier} ligne {n} : projet inconnu ({code})")
            return projets.get(code)

        if "jalons" in sources:
            lignes = _lire(sources["jalons"])
            Jalon.objects.filter(projet__code__in={r["projet"] for r in lignes}).delete()
            Jalon.objects.bulk_create([
                Jalon(projet=projet(r["projet"], "jalons.csv", n), titre=r["titre"], echeance=_d(r["echeance"]),
                      date_realisation=_d(r["date_realisation"]))
                for n, r in enumerate(lignes, start=2)])
            stats["jalons"] = len(lignes)

        if "financements" in sources:
            lignes = _lire(sources["financements"])
            Financement.objects.filter(projet__code__in={r["projet"] for r in lignes}).delete()
            Financement.objects.bulk_create([
                Financement(projet=projet(r["projet"], "financements.csv", n), organisme=r["organisme"],
                            type=r["type"], montant=int(r["montant"]), date=_d(r["date"]), statut=r["statut"])
                for n, r in enumerate(lignes, start=2)])
            stats["financements"] = len(lignes)

        if "partenariats" in sources:
            lignes = _lire(sources["partenariats"])
            Partenariat.objects.all().delete()  # le fichier décrit l'ensemble des partenariats
            Partenariat.objects.bulk_create([
                Partenariat(partenaire=r["partenaire"], type=r["type"], projet=projet(r["projet"], "partenariats.csv", n),
                            objet=r["objet"], date_signature=_d(r["date_signature"]), statut=r["statut"])
                for n, r in enumerate(lignes, start=2)])
            stats["partenariats"] = len(lignes)
    except (KeyError, ValueError) as exc:
        raise ErreurImport(f"Format invalide : {exc}") from exc
    return stats
