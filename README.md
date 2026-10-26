# Tableau de bord décisionnel du CIAT

Application d'analyse des activités de l'incubateur du **Centre d'Innovation, d'Application et de Transfert (CIAT)** de l'ISEP Amadou Trawaré de Diamniadio.
Projet 3 — Évaluation pratique du cours d'Intelligence Artificielle Générative.

**Équipe** : Khady Sall · Mame Sanou Sadio · Fatima Samba Konté

## Couverture du sujet

| Fonctionnalité attendue | Réalisation |
|---|---|
| Filtres par période, cohorte, domaine, statut et porteur | Barre de filtres commune (+ genre, profil, région) ; recherche par porteur réservée aux coordonnateurs |
| Indicateurs sur les idées reçues, projets sélectionnés et prototypes | 8 indicateurs clés + entonnoir du parcours |
| Suivi de la progression, des retards, des partenariats et des financements | Jalons à 5 états calculés, liste des projets en retard, financements par type, partenariats actifs |
| Comparaison entre cohortes, répartition par domaine ou genre | Page Cohortes, graphiques domaine / genre / région |
| Graphiques interactifs et fiches de synthèse | Chart.js (info-bulles, clic = filtre) ; fiche cohorte, fiche projet, faits marquants calculés |
| Assistant pour interroger les données en langage naturel | Gemini → requête JSON validée par liste blanche → calcul par l'ORM ; repli par règles |
| Export PDF, Excel et image | PDF serveur (reportlab), Excel 7 onglets avec graphique natif, PNG de chaque graphique |

Fonctions complémentaires : note de synthèse rédigée par IA avec vérification automatique des chiffres, contrôle qualité des données, import CSV transactionnel, 3 rôles avec anonymisation, journal des requêtes IA, 17 tests automatisés.

## Architecture

```
Navigateur ── Django (templates responsive + Chart.js local)
               ├── accounts/          rôles : direction, coordonnateur, administrateur
               └── pilotage/
                     ├── models.py        cohortes, porteurs, projets, jalons, financements, partenariats
                     ├── analyses.py      filtres + indicateurs + séries (source unique des chiffres)
                     ├── assistant.py     question → spécification JSON → validation → ORM
                     ├── synthese.py      note IA à partir d'agrégats + contrôle des chiffres cités
                     ├── exports.py       Excel (openpyxl), PDF (reportlab + matplotlib)
                     ├── qualite.py       10 règles de cohérence
                     └── importation.py   import CSV transactionnel
           ── PostgreSQL (prod) / SQLite (local)
           ── API Google Gemini (gemini-2.5-flash), facultative
```

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate            # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # GEMINI_API_KEY facultative
python manage.py migrate
python manage.py seed_demo           # importe data/*.csv + comptes de démo
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000 — clé Gemini gratuite : https://aistudio.google.com/apikey

## Comptes de démonstration

Mot de passe : `DEMO_PASSWORD` (par défaut `Ciat2026!demo`, à changer pour le déploiement).

| Identifiant | Rôle | Accès |
|---|---|---|
| `demo_direction` | Direction | Analyses, exports, assistant — porteurs anonymisés (P-0042) |
| `demo_coordonnateur` | Coordonnateur | + noms des porteurs, recherche par porteur, qualité, import CSV |
| `demo_admin` | Administrateur | + administration Django (saisie, comptes) |

## Commandes

```bash
python manage.py test           # 17 tests (IA simulée)
python manage.py generer_jeu    # régénère data/*.csv (graine fixe)
python manage.py seed_demo      # recharge data/*.csv dans la base
```

## Déploiement (Render, gratuit)

1. Pousser le dépôt sur GitHub.
2. Render → **New → Blueprint** → choisir le dépôt (`render.yaml` crée l'application et la base PostgreSQL).
3. Renseigner `GEMINI_API_KEY` et `DEMO_PASSWORD`.
4. `build.sh` installe, migre et charge les données au premier déploiement seulement.

L'offre gratuite met l'application en veille après 15 minutes : ouvrir le lien quelques minutes avant la soutenance.

## Limites

- Données **fictives** (voir `data/README.md`) : les tendances observées viennent de la simulation.
- L'assistant ne couvre que les 16 mesures et 7 regroupements définis ; une question hors de ce cadre est refusée.
- Le taux de réussite n'est calculé que pour les cohortes terminées.
- Les dates des filtres utilisent le sélecteur du navigateur (format selon la langue du système).
