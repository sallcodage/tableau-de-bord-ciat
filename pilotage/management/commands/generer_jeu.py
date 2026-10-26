"""
Génère le jeu de données FICTIF du CIAT dans data/*.csv (reproductible : graine fixe).

    python manage.py generer_jeu            # écrit data/cohortes.csv, porteurs.csv, projets.csv, ...

Hypothèses de simulation (documentées dans data/README.md) :
- 4 appels à projets : cohortes 2024, 2025, 2026 (en cours d'incubation) et 2027 (idées en évaluation) ;
- nombre d'idées en hausse (36 → 52 → 64), places limitées en incubation (10 → 14 → 16) ;
- part des femmes porteuses en hausse (28 % → 45 %) ;
- 5 jalons standard par projet incubé, retards plus fréquents en mécanique et en santé (besoins en équipements) ;
- 3 anomalies volontaires pour illustrer le contrôle qualité (voir data/README.md).
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

AUJOURDHUI = date(2026, 10, 26)

COHORTES = [
    # annee, debut, fin, nb_idees, places, part_femmes, depot_debut, depot_fin
    (2024, date(2024, 2, 5), date(2024, 8, 30), 36, 10, 0.28, date(2023, 11, 2), date(2023, 12, 15)),
    (2025, date(2025, 2, 3), date(2025, 8, 29), 52, 14, 0.36, date(2024, 11, 4), date(2024, 12, 16)),
    (2026, date(2026, 6, 1), date(2026, 12, 18), 64, 16, 0.44, date(2025, 11, 3), date(2026, 1, 16)),
    (2027, date(2027, 3, 1), date(2027, 11, 30), 18, 0, 0.45, date(2026, 9, 21), date(2026, 10, 24)),
]
DOMAINES = {"agriculture": 26, "tic": 24, "energie": 14, "mecanique": 12, "education": 10, "services": 8, "sante": 6}
RETARD = {"mecanique": 0.45, "sante": 0.45, "energie": 0.30, "agriculture": 0.25, "tic": 0.18, "education": 0.2, "services": 0.2}
REGIONS = {"Dakar": 40, "Thiès": 25, "Diourbel": 6, "Kaolack": 6, "Saint-Louis": 6, "Ziguinchor": 5,
           "Kaffrine": 4, "Louga": 4, "Fatick": 4}
PRENOMS_F = ["Aminata", "Fatou", "Awa", "Mariama", "Khady", "Ndeye", "Aïssatou", "Coumba", "Rokhaya", "Bineta",
             "Astou", "Marième", "Seynabou", "Adji", "Dieynaba", "Sokhna", "Yacine", "Ramatoulaye"]
PRENOMS_H = ["Moussa", "Mamadou", "Ousmane", "Cheikh", "Ibrahima", "Abdoulaye", "Modou", "Pape", "Alioune",
             "Babacar", "Serigne", "Lamine", "Omar", "Saliou", "Malick", "Assane", "Elhadji", "Souleymane"]
NOMS = ["Diop", "Ndiaye", "Fall", "Sow", "Ba", "Sarr", "Diallo", "Faye", "Gueye", "Mbaye", "Cissé", "Diouf",
        "Thiam", "Kane", "Sy", "Seck", "Ndour", "Camara", "Niang", "Badji", "Mendy", "Sène", "Touré", "Konté"]
TITRES = {
    "agriculture": ["Séchoir solaire de mangues", "Farine enrichie au mil", "Compost à base de typha",
                    "Irrigation goutte-à-goutte connectée", "Transformation de l'arachide en pâte",
                    "Conservation de l'oignon", "Bissap en poudre", "Aliment de bétail local",
                    "Jus de baobab pasteurisé", "Maraîchage hors-sol"],
    "tic": ["Plateforme de covoiturage Diamniadio", "Application de suivi scolaire", "Marketplace artisans",
            "Chatbot santé en wolof", "Gestion de stock pour boutiques", "Paiement mobile des tontines",
            "Cartographie des déchets", "Agenda partagé pour GIE", "Détection de maladies du manioc",
            "Billetterie de bus interurbains"],
    "energie": ["Kit solaire pour boutiques", "Foyer amélioré au charbon de typha", "Biodigesteur familial",
                "Lampes solaires recyclées", "Pompe solaire pour maraîchers", "Audit énergétique PME"],
    "mecanique": ["Atelier de réparation de motopompes", "Presse à briques de terre", "Décortiqueuse de fonio",
                  "Pièces détachées reconditionnées", "Remorque agricole légère", "Batteuse de riz mobile",
                  "Diagnostic automobile connecté", "Conversion de motos Jakarta à l'électrique",
                  "Climatisation solaire pour taxis", "Atelier mobile de carrosserie"],
    "education": ["Cours de soutien en ligne", "Bootcamp de code pour jeunes", "Kits de sciences pour collèges",
                  "Plateforme de stages", "Formation aux métiers du solaire"],
    "services": ["Collecte de déchets à vélo", "Laverie solidaire", "Services de livraison du dernier kilomètre",
                 "Gestion de marchés communaux", "Conciergerie pour PME"],
    "sante": ["Dispensateur de médicaments", "Savon antiseptique au neem", "Suivi des femmes enceintes par SMS",
              "Fabrication de masques réutilisables", "Pommade à base de plantes locales"],
}
# Filière ISEP du porteur selon le domaine du projet (poids) ; nouvelles filières seulement pour l'appel 2027
FILIERES_PAR_DOMAINE = {
    "tic": {"back": 3, "front": 3, "apd": 2, "abd": 2, "rsi": 1, "asc": 1},
    "mecanique": {"electromeca": 3, "carrosserie": 2, "elec_auto": 2, "froid": 1},
    "energie": {"froid": 2, "elec_auto": 2, "rsi": 1, "electromeca": 1},
    "agriculture": {"rsi": 2, "apd": 1, "back": 1, "electromeca": 1, "froid": 1},
    "education": {"front": 2, "back": 2, "apd": 2},
    "services": {"apd": 2, "back": 1, "front": 1, "abd": 1},
    "sante": {"abd": 1, "back": 1, "rsi": 1, "froid": 1},
}
NOUVELLES_FILIERES = {"tic": {"ia": 3, "cyber": 2}, "energie": {"efficacite": 3}, "sante": {"biomed": 3},
                      "agriculture": {"ia": 1}, "services": {"cyber": 1}}

JALONS = [("Étude de marché validée", 30), ("Prototype v1", 90), ("Tests utilisateurs", 120),
          ("Modèle économique finalisé", 150), ("Pitch final (demo day)", 175)]
MENTORS = ["M. Diagne (ingénieur)", "Mme Sall (experte agro)", "M. Faye (entrepreneur)", "Mme Ndiaye (finance)",
           "M. Thiam (énergie)", "Mme Ba (marketing)", "M. Kane (numérique)"]
ORGANISMES = {
    "subvention": ["Fonds public d'entrepreneuriat des jeunes", "Agence d'appui aux PME", "Programme de coopération UE"],
    "pret": ["Banque commerciale partenaire", "Institution de microfinance", "Fonds de garantie public"],
    "prix": ["Concours national d'innovation", "Prix jeunes entrepreneurs ISEP", "Challenge agritech régional"],
    "prive": ["Business angel", "Fondation d'entreprise", "Entreprise partenaire"],
}
MONTANTS = {"subvention": (1_000_000, 5_000_000), "pret": (2_000_000, 10_000_000),
            "prix": (300_000, 2_000_000), "prive": (2_000_000, 15_000_000)}
PARTENAIRES_INSTIT = [
    ("Commune de Diamniadio", "public", "Mise à disposition d'espaces de test", date(2023, 9, 14)),
    ("Banque commerciale partenaire", "financier", "Guichet de crédit pour projets incubés", date(2024, 3, 6)),
    ("Programme de coopération UE", "ong", "Cofinancement des cohortes 2025-2026", date(2024, 10, 2)),
    ("Université partenaire (laboratoire énergie)", "academique", "Accès au laboratoire solaire", date(2025, 1, 20)),
    ("Fondation d'entreprise", "entreprise", "Prix et mentorat", date(2025, 5, 12)),
    ("Agence d'appui aux PME", "public", "Formalisation des entreprises sorties", date(2025, 11, 4)),
    ("Opérateur télécom (programme startups)", "entreprise", "Crédits cloud et SMS", date(2026, 2, 17)),
    ("Institution de microfinance", "financier", "Microcrédits post-incubation", date(2026, 6, 8)),
]
PARTENAIRES_PROJET = ["Coopérative de femmes transformatrices", "GIE des maraîchers des Niayes", "PME de distribution",
                      "Supermarché local", "Lycée technique", "Atelier de soudure partenaire", "Hôpital régional",
                      "Association de quartier", "Startup de logistique", "Coopérative agricole"]


def tirer(poids):
    return random.choices(list(poids), weights=list(poids.values()))[0]


def date_entre(d1, d2):
    return d1 + timedelta(days=random.randint(0, max(0, (d2 - d1).days)))


class Command(BaseCommand):
    help = "Génère le jeu de données fictif du CIAT dans data/*.csv"

    def handle(self, *args, **opts):
        random.seed(42)
        dossier = Path(settings.BASE_DIR) / "data"
        dossier.mkdir(exist_ok=True)
        cohortes, porteurs, projets, jalons, financements, partenariats = [], [], [], [], [], []
        n_porteur = 0

        for annee, debut, fin, nb_idees, places, part_f, d_dep1, d_dep2 in COHORTES:
            cohortes.append({"annee": annee, "nom": f"Cohorte {annee}", "date_debut": debut, "date_fin": fin})
            idees = []
            nb_femmes = round(part_f * nb_idees)  # quota exact : la tendance reste lisible malgré l'aléa
            genres = ["F"] * nb_femmes + ["H"] * (nb_idees - nb_femmes)
            random.shuffle(genres)
            for i in range(1, nb_idees + 1):
                n_porteur += 1
                genre = genres[i - 1]
                domaine = tirer(DOMAINES)
                profil = random.choices(["apprenant", "diplome", "externe"], weights=[45, 30, 25])[0]
                filiere = ""
                if profil != "externe":
                    poids = dict(FILIERES_PAR_DOMAINE[domaine])
                    if annee == 2027 and profil == "apprenant":
                        poids.update(NOUVELLES_FILIERES.get(domaine, {}))
                    filiere = tirer(poids)
                porteurs.append({
                    "code": f"P-{n_porteur:04d}",
                    "prenom": random.choice(PRENOMS_F if genre == "F" else PRENOMS_H),
                    "nom": random.choice(NOMS), "genre": genre,
                    "tranche_age": random.choices(["18-24", "25-34", "35+"], weights=[38, 46, 16])[0],
                    "profil": profil, "filiere": filiere,
                    "region": tirer(REGIONS),
                })
                p = {
                    "code": f"CIAT-{annee}-{i:03d}", "titre": random.choice(TITRES[domaine]), "domaine": domaine,
                    "cohorte": annee, "porteur": f"P-{n_porteur:04d}", "nb_membres": random.choice([1, 2, 2, 3, 3, 4, 5]),
                    "date_depot": date_entre(d_dep1, d_dep2), "preselectionne": 0, "selectionne": 0,
                    "score_comite": "", "date_selection": "", "date_prototype": "", "statut": "evaluation",
                    "progression": 0, "mentor": "", "emplois_crees": 0,
                }
                idees.append(p)
            projets.extend(idees)
            if annee == 2027:
                continue  # appel en cours : toutes les idées sont en évaluation

            # Présélection (~55 %) puis sélection par score
            for p in idees:
                p["preselectionne"] = int(random.random() < 0.55)
                if p["preselectionne"]:
                    p["score_comite"] = random.randint(48, 92)
            preselect = sorted([p for p in idees if p["preselectionne"]], key=lambda p: -p["score_comite"])
            retenus = preselect[:places]
            for p in idees:
                p["statut"] = "non_retenu"
            for p in retenus:
                p["selectionne"] = 1
                p["date_selection"] = debut - timedelta(days=random.randint(10, 25))
                p["mentor"] = random.choice(MENTORS)
                p["statut"] = "incubation"
                self.simuler_incubation(p, debut, fin, jalons, financements, partenariats)

        # Partenariats institutionnels
        for nom, typ, objet, d in PARTENAIRES_INSTIT:
            partenariats.append({"partenaire": nom, "type": typ, "projet": "", "objet": objet,
                                 "date_signature": d, "statut": "actif" if d.year >= 2025 else "termine"})

        # Anomalies volontaires (contrôle qualité)
        sel = [p for p in projets if p["selectionne"]]
        sel[3]["score_comite"] = ""                                     # A1 : projet sélectionné sans note
        financements[5]["date"] = date(2019, 1, 15)                      # A2 : financement daté avant le dépôt
        non = next(p for p in projets if p["statut"] == "non_retenu")
        non["date_prototype"] = date(2025, 6, 2)                         # A3 : prototype sans sélection

        self.ecrire(dossier / "cohortes.csv", cohortes)
        self.ecrire(dossier / "porteurs.csv", porteurs)
        self.ecrire(dossier / "projets.csv", projets)
        self.ecrire(dossier / "jalons.csv", jalons)
        self.ecrire(dossier / "financements.csv", financements)
        self.ecrire(dossier / "partenariats.csv", partenariats)
        self.stdout.write(self.style.SUCCESS(
            f"{len(projets)} projets, {len(porteurs)} porteurs, {len(jalons)} jalons, "
            f"{len(financements)} financements, {len(partenariats)} partenariats → {dossier}"))

    def simuler_incubation(self, p, debut, fin, jalons, financements, partenariats):
        domaine = p["domaine"]
        abandon = random.random() < 0.2
        rang_abandon = random.randint(1, 3) if abandon else 99
        faits = 0
        for k, (titre, offset) in enumerate(JALONS):
            echeance = debut + timedelta(days=offset)
            realisation = ""
            # un jalon peut ne jamais être atteint (difficulté technique, équipement manquant)
            echec = random.random() < RETARD[domaine] * 0.45
            if k < rang_abandon and not echec:
                retard = random.random() < RETARD[domaine]
                prevue = echeance + timedelta(days=random.randint(8, 45) if retard else -random.randint(0, 10))
                if prevue <= AUJOURDHUI:
                    realisation = prevue
                    faits += 1
            jalons.append({"projet": p["code"], "titre": titre, "echeance": echeance, "date_realisation": realisation})
            if titre == "Prototype v1" and realisation:
                p["date_prototype"] = realisation

        termine = fin < AUJOURDHUI
        if abandon and (termine or debut + timedelta(days=60 * rang_abandon) < AUJOURDHUI):
            p["statut"] = "abandonne"
        elif termine:
            p["statut"] = "sorti" if faits >= 4 and p["date_prototype"] else "abandonne"
        p["progression"] = 100 if p["statut"] == "sorti" else round(100 * faits / len(JALONS))
        if p["statut"] == "sorti":
            p["emplois_crees"] = random.randint(1, 6)

        # Financements : plus probables pour les projets avancés
        for _ in range(random.choices([0, 1, 2, 3], weights=[2, 4, 3, 1] if faits >= 3 else [5, 4, 1, 0])[0]):
            typ = random.choices(list(MONTANTS), weights=[4, 2, 3, 2])[0]
            d = date_entre(debut, min(fin + timedelta(days=90), AUJOURDHUI))
            statut = "obtenu" if d < AUJOURDHUI - timedelta(days=45) else random.choice(["demande", "obtenu"])
            if random.random() < 0.12:
                statut = "refuse"
            lo, hi = MONTANTS[typ]
            financements.append({"projet": p["code"], "organisme": random.choice(ORGANISMES[typ]), "type": typ,
                                 "montant": round(random.randint(lo, hi), -5), "date": d, "statut": statut})
        # Partenariats projet
        if random.random() < 0.55:
            partenariats.append({"partenaire": random.choice(PARTENAIRES_PROJET),
                                 "type": random.choice(["entreprise", "ong", "public"]), "projet": p["code"],
                                 "objet": "Test terrain / premiers clients",
                                 "date_signature": date_entre(debut, min(fin, AUJOURDHUI)),
                                 "statut": random.choice(["actif", "actif", "negociation", "termine"])})

    def ecrire(self, chemin, lignes):
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()), delimiter=";")
            w.writeheader()
            for ligne in lignes:
                w.writerow({k: (v.isoformat() if isinstance(v, date) else v) for k, v in ligne.items()})
