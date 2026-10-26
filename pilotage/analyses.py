"""
Moteur d'analyse : filtres, indicateurs et séries.
Utilisé par le tableau de bord, les fiches de synthèse, les exports et l'assistant en langage naturel,
pour que tous affichent exactement les mêmes chiffres.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from django.db.models import Avg, Count, Q, Sum

from django.conf import settings

from .models import (DEPARTEMENT_FILIERE, DOMAINES, DOMAINES_COURTS, FILIERES_PLATES, Cohorte, Financement, Jalon,
                     Partenariat, Porteur, Projet)

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


# --------------------------------------------------------------------------- Filtres
@dataclass
class Filtres:
    du: date | None = None
    au: date | None = None
    cohortes: list = field(default_factory=list)   # années
    domaines: list = field(default_factory=list)
    statuts: list = field(default_factory=list)
    genre: str = ""
    profil: str = ""
    region: str = ""
    filiere: str = ""                               # code filière ISEP, ou « dep:TIC » / « dep:Automobile »
    porteur: str = ""                               # recherche nom / code (coordonnateurs uniquement)

    @classmethod
    def depuis_requete(cls, get, voit_noms=False):
        def d(cle):
            try:
                return date.fromisoformat(get.get(cle, ""))
            except ValueError:
                return None

        cohortes = [int(c) for c in get.getlist("cohorte") if c.isdigit()]
        domaines = [x for x in get.getlist("domaine") if x in dict(DOMAINES)]
        statuts = [x for x in get.getlist("statut") if x in Projet.Statut.values]
        return cls(
            du=d("du"), au=d("au"), cohortes=cohortes, domaines=domaines, statuts=statuts,
            genre=get.get("genre", "") if get.get("genre") in ("F", "H") else "",
            profil=get.get("profil", "") if get.get("profil") in Porteur.Profil.values else "",
            region=get.get("region", "")[:40],
            filiere=get.get("filiere", "") if get.get("filiere") in dict(FILIERES_PLATES) or get.get("filiere", "").startswith("dep:") else "",
            porteur=get.get("porteur", "")[:60] if voit_noms else "",
        )

    @property
    def actifs(self):
        return any([self.du, self.au, self.cohortes, self.domaines, self.statuts, self.genre, self.profil,
                    self.region, self.filiere, self.porteur])

    def projets(self):
        qs = Projet.objects.select_related("porteur", "cohorte")
        if self.du:
            qs = qs.filter(date_depot__gte=self.du)
        if self.au:
            qs = qs.filter(date_depot__lte=self.au)
        if self.cohortes:
            qs = qs.filter(cohorte__annee__in=self.cohortes)
        if self.domaines:
            qs = qs.filter(domaine__in=self.domaines)
        if self.statuts:
            qs = qs.filter(statut__in=self.statuts)
        if self.genre:
            qs = qs.filter(porteur__genre=self.genre)
        if self.profil:
            qs = qs.filter(porteur__profil=self.profil)
        if self.region:
            qs = qs.filter(porteur__region=self.region)
        if self.filiere.startswith("dep:"):
            mot = self.filiere[4:]
            codes = [c for c, d in DEPARTEMENT_FILIERE.items() if mot in d]
            qs = qs.filter(porteur__filiere__in=codes)
        elif self.filiere:
            qs = qs.filter(porteur__filiere=self.filiere)
        if self.porteur:
            t = self.porteur
            qs = qs.filter(Q(porteur__nom__icontains=t) | Q(porteur__prenom__icontains=t) | Q(porteur__code__iexact=t))
        return qs

    def description(self):
        morceaux = []
        if self.cohortes:
            morceaux.append("Cohorte(s) " + ", ".join(map(str, self.cohortes)))
        if self.domaines:
            morceaux.append(", ".join(DOMAINES_COURTS[x] for x in self.domaines))
        if self.statuts:
            morceaux.append(", ".join(Projet.Statut(s).label for s in self.statuts))
        if self.genre:
            morceaux.append("Porteuses" if self.genre == "F" else "Porteurs (hommes)")
        if self.profil:
            morceaux.append(Porteur.Profil(self.profil).label)
        if self.region:
            morceaux.append(self.region)
        if self.filiere:
            morceaux.append(f"Département {self.filiere[4:]}" if self.filiere.startswith("dep:")
                            else dict(FILIERES_PLATES)[self.filiere])
        if self.du or self.au:
            morceaux.append(f"dépôts du {self.du or '…'} au {self.au or '…'}")
        if self.porteur:
            morceaux.append(f"porteur « {self.porteur} »")
        return " · ".join(morceaux) or "Toutes les données"


# --------------------------------------------------------------------------- Indicateurs
def indicateurs(projets, aujourd_hui=None):
    aujourd_hui = aujourd_hui or date.today()
    ids = list(projets.values_list("id", flat=True))
    p = Projet.objects.filter(id__in=ids)
    idees = len(ids)
    presel = p.filter(preselectionne=True).count()
    sel = p.filter(selectionne=True).count()
    protos = p.filter(selectionne=True, date_prototype__isnull=False).count()
    sortis = p.filter(statut=Projet.Statut.SORTI).count()
    abandons = p.filter(statut=Projet.Statut.ABANDONNE).count()
    en_cours = p.filter(statut=Projet.Statut.INCUBATION)

    jalons = list(Jalon.objects.filter(projet_id__in=ids).select_related("projet"))
    etats = Counter(j.etat(aujourd_hui) for j in jalons)
    # Base du taux de retard : jalons échus et suivis (hors « à venir » et hors projets terminés non atteints)
    echus = len(jalons) - etats[Jalon.Etat.A_VENIR] - etats[Jalon.Etat.NON_ATTEINT]
    en_retard = etats[Jalon.Etat.EN_RETARD] + etats[Jalon.Etat.REALISE_RETARD]
    projets_retard = {j.projet_id for j in jalons if j.etat(aujourd_hui) == Jalon.Etat.EN_RETARD}

    fin = Financement.objects.filter(projet_id__in=ids)
    obtenu = fin.filter(statut=Financement.Statut.OBTENU)
    montant_obtenu = obtenu.aggregate(s=Sum("montant"))["s"] or 0
    nb_finances = obtenu.values("projet").distinct().count()

    femmes = p.filter(porteur__genre="F")
    return {
        "idees": idees,
        "preselectionnes": presel,
        "selectionnes": sel,
        "prototypes": protos,
        "sortis": sortis,
        "abandons": abandons,
        "en_incubation": en_cours.count(),
        "taux_preselection": pct(presel, idees),
        "taux_selection": pct(sel, idees),
        "taux_prototype": pct(protos, sel),
        "taux_reussite": pct(sortis, sortis + abandons),
        "progression_moyenne": round(en_cours.aggregate(m=Avg("progression"))["m"] or 0),
        "jalons_total": len(jalons),
        "jalons_echus": echus,
        "jalons_non_atteints": etats[Jalon.Etat.NON_ATTEINT],
        "jalons_en_retard": etats[Jalon.Etat.EN_RETARD],
        "jalons_realises_retard": etats[Jalon.Etat.REALISE_RETARD],
        "taux_retard": pct(en_retard, echus),
        "projets_en_retard": len(projets_retard),
        "montant_obtenu": montant_obtenu,
        "montant_demande": fin.filter(statut=Financement.Statut.DEMANDE).aggregate(s=Sum("montant"))["s"] or 0,
        "nb_financements": obtenu.count(),
        "projets_finances": nb_finances,
        "taux_projets_finances": pct(nb_finances, sel),
        "montant_moyen": round(montant_obtenu / nb_finances) if nb_finances else 0,
        "partenariats_projets": Partenariat.objects.filter(projet_id__in=ids).count(),
        "partenariats_actifs": Partenariat.objects.filter(
            Q(projet_id__in=ids) | Q(projet__isnull=True), statut=Partenariat.Statut.ACTIF).count(),
        "part_femmes": pct(femmes.count(), idees),
        "part_femmes_selectionnes": pct(femmes.filter(selectionne=True).count(), sel),
        "taux_selection_femmes": pct(femmes.filter(selectionne=True).count(), femmes.count()),
        "taux_selection_hommes": pct(p.filter(porteur__genre="H", selectionne=True).count(),
                                     p.filter(porteur__genre="H").count()),
        "emplois_crees": p.aggregate(s=Sum("emplois_crees"))["s"] or 0,
        "idees_isep": p.exclude(porteur__filiere="").count(),
        "part_isep": pct(p.exclude(porteur__filiere="").count(), idees),
    }


# --------------------------------------------------------------------------- Séries pour les graphiques
def series(projets, aujourd_hui=None):
    aujourd_hui = aujourd_hui or date.today()
    ids = list(projets.values_list("id", flat=True))
    p = Projet.objects.filter(id__in=ids)
    k = indicateurs(p, aujourd_hui)

    entonnoir = [
        {"etape": "Idées reçues", "n": k["idees"]},
        {"etape": "Présélectionnées", "n": k["preselectionnes"]},
        {"etape": "Incubées", "n": k["selectionnes"]},
        {"etape": "Prototypes", "n": k["prototypes"]},
        {"etape": "Sorties (lancées)", "n": k["sortis"]},
    ]

    cohortes = []
    for c in Cohorte.objects.filter(projets__in=ids).distinct().order_by("annee"):
        kc = indicateurs(p.filter(cohorte=c), aujourd_hui)
        # Taux non significatifs → None (affichés « — » et absents des courbes) plutôt que 0 %
        terminee = c.date_fin < aujourd_hui
        selection_faite = kc["selectionnes"] > 0
        cohortes.append({"cohorte": c.annee, "idees": kc["idees"], "selectionnes": kc["selectionnes"],
                         "prototypes": kc["prototypes"], "sortis": kc["sortis"], "abandons": kc["abandons"],
                         "terminee": terminee,
                         "taux_selection": kc["taux_selection"] if selection_faite else None,
                         "taux_prototype": kc["taux_prototype"] if selection_faite else None,
                         "taux_reussite": kc["taux_reussite"] if terminee and selection_faite else None,
                         "part_femmes": kc["part_femmes"],
                         "montant_obtenu": kc["montant_obtenu"], "taux_retard": kc["taux_retard"]})

    domaines = []
    for code, _ in DOMAINES:
        d = p.filter(domaine=code)
        n = d.count()
        if n:
            s = d.filter(selectionne=True).count()
            domaines.append({"domaine": DOMAINES_COURTS[code], "code": code, "idees": n, "selectionnes": s,
                             "taux_selection": pct(s, n)})
    domaines.sort(key=lambda r: -r["idees"])

    genre = []
    for g, lib in Porteur.Genre.choices:
        d = p.filter(porteur__genre=g)
        n = d.count()
        genre.append({"genre": lib, "idees": n, "selectionnes": d.filter(selectionne=True).count(),
                      "sortis": d.filter(statut=Projet.Statut.SORTI).count(),
                      "taux_selection": pct(d.filter(selectionne=True).count(), n)})

    # Jalons par domaine et état (retards)
    retards = defaultdict(Counter)
    for j in Jalon.objects.filter(projet_id__in=ids).select_related("projet"):
        retards[j.projet.domaine][j.etat(aujourd_hui)] += 1
    jalons_domaine = [
        {"domaine": DOMAINES_COURTS[code], "a_temps": c[Jalon.Etat.A_TEMPS], "realise_retard": c[Jalon.Etat.REALISE_RETARD],
         "en_retard": c[Jalon.Etat.EN_RETARD], "a_venir": c[Jalon.Etat.A_VENIR],
         "non_atteint": c[Jalon.Etat.NON_ATTEINT],
         "taux_retard": pct(c[Jalon.Etat.EN_RETARD] + c[Jalon.Etat.REALISE_RETARD],
                            sum(c.values()) - c[Jalon.Etat.A_VENIR] - c[Jalon.Etat.NON_ATTEINT])}
        for code, c in retards.items()]
    jalons_domaine.sort(key=lambda r: -r["taux_retard"])

    fin = Financement.objects.filter(projet_id__in=ids, statut=Financement.Statut.OBTENU)
    financements_type = [{"type": Financement.Type(r["type"]).label, "montant": r["s"], "n": r["n"]}
                         for r in fin.values("type").annotate(s=Sum("montant"), n=Count("id")).order_by("-s")]

    depots = Counter((d.year, d.month) for d in p.values_list("date_depot", flat=True))
    depots_mois = [{"mois": f"{MOIS[m - 1]} {a}", "n": n} for (a, m), n in sorted(depots.items())]

    regions = [{"region": r["porteur__region"], "n": r["n"]}
               for r in p.values("porteur__region").annotate(n=Count("id")).order_by("-n")]

    filieres = []
    for code, lib in FILIERES_PLATES:
        d = p.filter(porteur__filiere=code)
        n = d.count()
        if n:
            filieres.append({"filiere": lib, "code": code, "departement": DEPARTEMENT_FILIERE[code].replace("Département ", ""),
                             "idees": n, "selectionnes": d.filter(selectionne=True).count(),
                             "sortis": d.filter(statut=Projet.Statut.SORTI).count()})
    filieres.sort(key=lambda r: -r["idees"])

    return {"entonnoir": entonnoir, "cohortes": cohortes, "filieres": filieres, "domaines": domaines, "genre": genre,
            "jalons_domaine": jalons_domaine, "financements_type": financements_type,
            "depots_mois": depots_mois, "regions": regions}


def projets_en_retard(projets, aujourd_hui=None, limite=15):
    """Projets en incubation ayant au moins un jalon échu non réalisé, triés par retard."""
    aujourd_hui = aujourd_hui or date.today()
    lignes = []
    for pr in projets.filter(statut=Projet.Statut.INCUBATION).prefetch_related("jalons__projet"):
        retard = [j for j in pr.jalons.all() if j.etat(aujourd_hui) == Jalon.Etat.EN_RETARD]
        if retard:
            pire = max(retard, key=lambda j: (aujourd_hui - j.echeance).days)
            lignes.append({"projet": pr, "jalon": pire.titre, "jours": (aujourd_hui - pire.echeance).days,
                           "nb": len(retard)})
    lignes.sort(key=lambda r: -r["jours"])
    return lignes[:limite]


def fr(x):
    """Nombre au format français : 25.9 → « 25,9 »."""
    return f"{x:g}".replace(".", ",") if isinstance(x, float) else str(x)


def faits_marquants(projets, aujourd_hui=None):
    """Constats calculés (non générés) pour les fiches de synthèse."""
    s = series(projets, aujourd_hui)
    k = indicateurs(projets, aujourd_hui)
    faits = []
    if s["domaines"]:
        top = s["domaines"][0]
        faits.append(f"{top['domaine']} est le premier domaine avec {fr(top['idees'])} idées "
                     f"({fr(pct(top['idees'], k['idees']))} % du total).")
    aujourd_hui = aujourd_hui or date.today()
    fin_cohortes = dict(Cohorte.objects.values_list("annee", "date_fin"))
    termines = [c for c in s["cohortes"] if c["selectionnes"] and fin_cohortes[c["cohorte"]] < aujourd_hui]
    if len(termines) >= 2:
        a, b = termines[-2], termines[-1]
        faits.append(f"Le taux de réussite en incubation passe de {fr(a['taux_reussite'])} % (cohorte {a['cohorte']}) "
                     f"à {fr(b['taux_reussite'])} % (cohorte {b['cohorte']}).")
    if k["idees"]:
        ecart = k["taux_selection_femmes"] - k["taux_selection_hommes"]
        faits.append(f"Les femmes portent {fr(k['part_femmes'])} % des idées ; leur taux de sélection est de "
                     f"{fr(k['taux_selection_femmes'])} % contre {fr(k['taux_selection_hommes'])} % pour les hommes "
                     f"({'+' if ecart >= 0 else ''}{fr(round(ecart, 1))} pt).")
    # Domaine le plus en retard, parmi ceux ayant assez de jalons échus pour que le taux ait un sens
    solides = [d for d in s["jalons_domaine"] if d["a_temps"] + d["realise_retard"] + d["en_retard"] >= 8]
    if solides:
        pire = solides[0]
        faits.append(f"Les retards de jalons sont les plus fréquents en {pire['domaine'].lower()} "
                     f"({fr(pire['taux_retard'])} % des jalons échus).")
    # Mise en perspective avec l'effectif réel de l'ISEP (1 194 apprenants, 2025)
    c2026 = projets.filter(cohorte__annee=2026, porteur__profil=Porteur.Profil.APPRENANT).count()
    total_2026 = Projet.objects.filter(cohorte__annee=2026, porteur__profil=Porteur.Profil.APPRENANT).count()
    if c2026 and c2026 == total_2026:  # ratio pertinent seulement sur l'ensemble de l'appel, pas un sous-groupe
        effectif = f"{settings.ISEP_EFFECTIF:,}".replace(",", " ")
        faits.append(f"Appel 2026 : {c2026} idées portées par des apprenants, soit {fr(pct(c2026, settings.ISEP_EFFECTIF))} % "
                     f"des {effectif} apprenants de l'ISEP (effectif 2025) : un vivier encore peu mobilisé.")
    if s["filieres"]:
        f0 = s["filieres"][0]
        faits.append(f"Filière ISEP la plus représentée parmi les porteurs : {f0['filiere']} ({f0['idees']} idées).")
    if k["montant_obtenu"]:
        faits.append(f"{fcfa(k['montant_obtenu'])} de financements obtenus pour {k['projets_finances']} projets "
                     f"({fr(k['taux_projets_finances'])} % des projets incubés).")
    return faits


def fcfa(montant):
    """1234567 → « 1,2 M FCFA » ; 450000 → « 450 000 FCFA »."""
    if montant >= 1_000_000:
        return f"{montant / 1_000_000:,.1f} M FCFA".replace(",", " ").replace(".", ",")
    return f"{montant:,} FCFA".replace(",", " ")
