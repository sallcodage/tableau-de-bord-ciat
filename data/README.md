# Jeu de données du CIAT (fictif)

Données **fictives** générées pour la démonstration par `python manage.py generer_jeu` (graine 42, reproductible),
ancrées dans les données **réelles** de l'ISEP Amadou Trawaré : 10 filières des départements TIC et Automobile,
nouvelles filières annoncées pour 2025-2026, effectif de 1 194 apprenants en 2025
(sources : [Guindima](https://guindima.sn/educa/etablissement/institut-superieur-denseignement-professionnel-de-diamniadio/),
[AllAfrica / APS, 24/09/2025](https://fr.allafrica.com/stories/202509240276.html)). Aucune donnée publique n'existe sur le CIAT lui-même.
Date de référence : 26/10/2026. Format : CSV, séparateur `;`, UTF-8, dates `AAAA-MM-JJ`.

## Volumes

| Fichier | Lignes | Contenu |
|---|---|---|
| cohortes.csv | 4 | Appels 2024, 2025, 2026 (incubation en cours), 2027 (idées en évaluation) |
| porteurs.csv | 170 | Porteur principal de chaque idée |
| projets.csv | 170 | Idées déposées et leur parcours |
| jalons.csv | 200 | 5 jalons par projet incubé |
| financements.csv | 44 | Financements des projets incubés |
| partenariats.csv | 31 | 8 institutionnels + 23 liés à des projets |

## Dictionnaire des données

### cohortes.csv
| Champ | Type | Description | Exemple |
|---|---|---|---|
| annee | entier | Année de l'appel (clé) | 2025 |
| nom | texte | Libellé | Cohorte 2025 |
| date_debut | date | Début de l'incubation | 2025-02-03 |
| date_fin | date | Fin de l'incubation | 2025-08-29 |

### porteurs.csv
| Champ | Type | Description | Valeurs |
|---|---|---|---|
| code | texte | Identifiant anonyme (clé) | P-0042 |
| prenom, nom | texte | Identité (visible des coordonnateurs uniquement) | |
| genre | code | Genre | F, H |
| tranche_age | code | Âge au dépôt | 18-24, 25-34, 35+ |
| profil | code | Lien avec l'ISEP | apprenant, diplome, externe |
| filiere | code | Filière ISEP réelle (vide si externe) | back, front, apd, abd, asc, rsi, electromeca, elec_auto, froid, carrosserie ; ia, cyber, efficacite, biomed (appel 2027 seulement) |
| region | texte | Région de résidence | Dakar, Thiès… |

### projets.csv
| Champ | Type | Description | Valeurs / règle |
|---|---|---|---|
| code | texte | Identifiant (clé) | CIAT-2025-014 |
| titre | texte | Intitulé du projet | |
| domaine | code | Domaine prioritaire du CIAT | tic, mecanique, agriculture, energie, sante, education, services |
| cohorte | entier | Année de l'appel → cohortes.annee | |
| porteur | texte | → porteurs.code | |
| nb_membres | entier | Taille de l'équipe | 1 à 5 |
| date_depot | date | Dépôt de l'idée | |
| preselectionne | 0/1 | Retenu à la présélection | |
| selectionne | 0/1 | Retenu par le comité pour l'incubation | implique preselectionne = 1 |
| score_comite | entier | Note du comité sur 100 | renseignée si présélectionné |
| date_selection | date | Décision du comité | ≥ date_depot |
| date_prototype | date | Réalisation du prototype | seulement si selectionne = 1 |
| statut | code | État courant | evaluation, non_retenu, incubation, sorti, abandonne |
| progression | entier | Avancement en % | 0 à 100 |
| mentor | texte | Mentor affecté | |
| emplois_crees | entier | Emplois créés (projets sortis) | |

### jalons.csv
| Champ | Type | Description |
|---|---|---|
| projet | texte | → projets.code |
| titre | texte | Étude de marché validée, Prototype v1, Tests utilisateurs, Modèle économique finalisé, Pitch final |
| echeance | date | Date prévue |
| date_realisation | date | Vide si non réalisé |

L'état (à temps, réalisé en retard, en retard, à venir, non atteint) est **calculé**, jamais saisi.

### financements.csv
| Champ | Type | Description | Valeurs |
|---|---|---|---|
| projet | texte | → projets.code | |
| organisme | texte | Financeur (libellés génériques) | |
| type | code | Nature | subvention, pret, prix, prive |
| montant | entier | Montant en FCFA | |
| date | date | Date d'obtention ou de demande | |
| statut | code | | obtenu, demande, refuse |

### partenariats.csv
| Champ | Type | Description | Valeurs |
|---|---|---|---|
| partenaire | texte | Nom (fictif ou générique) | |
| type | code | | entreprise, public, ong, financier, academique |
| projet | texte | → projets.code, vide = partenariat institutionnel | |
| objet | texte | Objet du partenariat | |
| date_signature | date | | |
| statut | code | | actif, negociation, termine |

## Hypothèses de simulation

- Nombre d'idées en hausse : 36 (2024) → 52 (2025) → 64 (2026) → 18 déjà reçues pour 2027.
- Places en incubation : 10 → 14 → 16. Présélection d'environ 55 % des idées, sélection par note décroissante.
- Filière du porteur tirée selon le domaine du projet (ex. mécanique → filières Automobile, numérique → filières TIC) ; les nouvelles filières n'apparaissent que pour l'appel 2027, car elles ouvrent en 2025-2026.
- Part des femmes porteuses fixée par quota : 28 % → 36 % → 44 % → 45 %.
- Retards de jalons plus probables en mécanique et en santé (équipements, homologations), puis énergie.
- 20 % de risque d'abandon en incubation ; un projet « sort » s'il a atteint au moins 4 jalons dont le prototype.
- Financements plus nombreux pour les projets avancés ; montants par type (subvention 1–5 M, prêt 2–10 M, prix 0,3–2 M, privé 2–15 M FCFA).

## Anomalies volontaires (contrôle qualité)

Trois anomalies sont injectées pour démontrer la page « Données et qualité » :

| Code | Anomalie | Ligne concernée |
|---|---|---|
| A1 | Projet sélectionné sans note du comité | 4e projet sélectionné |
| A2 | Financement daté du 15/01/2019, avant le dépôt du projet | 6e financement |
| A3 | Prototype déclaré pour un projet non retenu | 1er projet non retenu |

## Limites

Données synthétiques : les écarts observés (par exemple entre femmes et hommes) résultent de la simulation et ne décrivent pas la réalité du CIAT. À remplacer par les données réelles via la page « Données » (import CSV).
