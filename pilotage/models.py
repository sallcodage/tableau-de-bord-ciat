"""
Modèle de données du tableau de bord décisionnel du CIAT.

Cohorte 1─n Projet n─1 Porteur
Projet 1─n Jalon · Projet 1─n Financement · Projet 1─n Partenariat (ou partenariat institutionnel sans projet)

Le parcours d'un projet est décrit par des étapes datées (dépôt, présélection, sélection, prototype)
et par un statut courant. L'entonnoir et les taux sont calculés à partir de ces étapes.
"""
from datetime import date

from django.db import models

DOMAINES = [
    ("tic", "TIC, numérique, IA et données"),
    ("mecanique", "Mécanique, fabrication et maintenance"),
    ("agriculture", "Agriculture, transformation et environnement"),
    ("energie", "Énergie et énergies renouvelables"),
    ("sante", "Pharmaceutique et biomédical"),
    ("education", "Éducation, formation et insertion"),
    ("services", "Services aux collectivités et entrepreneuriat"),
]
# Filières réelles de l'ISEP Amadou Trawaré (BTS, 2 départements) + filières annoncées pour 2025-2026
FILIERES = [
    ("Département TIC", [
        ("back", "Développement Back-End"),
        ("front", "Développement Front-End"),
        ("apd", "Analyse de Performance Digitale"),
        ("abd", "Administration des Bases de Données"),
        ("asc", "Administration Système, Sécurité et Cloud"),
        ("rsi", "Réseaux, Sécurité et IoT"),
    ]),
    ("Département Automobile", [
        ("electromeca", "Électromécanique Automobile"),
        ("elec_auto", "Électricité et Électronique Automobile"),
        ("froid", "Froid et Climatisation Automobile et Industriel"),
        ("carrosserie", "Carrosserie et Peinture Automobile"),
    ]),
    ("Nouvelles filières (2025-2026)", [
        ("ia", "Intelligence artificielle"),
        ("cyber", "Cybersécurité"),
        ("efficacite", "Efficacité énergétique"),
        ("biomed", "Maintenance biomédicale et industries pharmaceutiques"),
    ]),
]
FILIERES_PLATES = [(c, l) for _, groupe in FILIERES for c, l in groupe]
DEPARTEMENT_FILIERE = {c: d for d, groupe in FILIERES for c, _ in groupe}

DOMAINES_COURTS = {
    "tic": "Numérique & IA", "mecanique": "Mécanique", "agriculture": "Agriculture",
    "energie": "Énergie", "sante": "Santé", "education": "Éducation", "services": "Services",
}


class Cohorte(models.Model):
    nom = models.CharField(max_length=60, unique=True)
    annee = models.PositiveIntegerField(unique=True)
    date_debut = models.DateField(help_text="Début de l'incubation")
    date_fin = models.DateField(help_text="Fin de l'incubation")

    class Meta:
        ordering = ["annee"]

    def __str__(self):
        return self.nom


class Porteur(models.Model):
    class Genre(models.TextChoices):
        FEMME = "F", "Femme"
        HOMME = "H", "Homme"

    class Profil(models.TextChoices):
        APPRENANT = "apprenant", "Apprenant ISEP"
        DIPLOME = "diplome", "Diplômé ISEP"
        EXTERNE = "externe", "Porteur externe"

    class TrancheAge(models.TextChoices):
        A18 = "18-24", "18-24 ans"
        A25 = "25-34", "25-34 ans"
        A35 = "35+", "35 ans et plus"

    code = models.CharField(max_length=10, unique=True, help_text="Identifiant anonyme, ex. P-0042")
    prenom = models.CharField(max_length=60)
    nom = models.CharField(max_length=60)
    genre = models.CharField(max_length=1, choices=Genre.choices)
    tranche_age = models.CharField(max_length=6, choices=TrancheAge.choices)
    profil = models.CharField(max_length=10, choices=Profil.choices)
    filiere = models.CharField(max_length=12, choices=FILIERES_PLATES, blank=True,
                               help_text="Filière ISEP (apprenants et diplômés), vide pour un porteur externe")
    region = models.CharField(max_length=40)

    @property
    def departement(self):
        return DEPARTEMENT_FILIERE.get(self.filiere, "")

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.code})"


class Projet(models.Model):
    class Statut(models.TextChoices):
        EVALUATION = "evaluation", "En évaluation"
        NON_RETENU = "non_retenu", "Non retenu"
        INCUBATION = "incubation", "En incubation"
        SORTI = "sorti", "Sorti (lancé)"
        ABANDONNE = "abandonne", "Abandonné"

    code = models.CharField(max_length=16, unique=True)
    titre = models.CharField(max_length=150)
    resume = models.TextField(blank=True)
    domaine = models.CharField(max_length=20, choices=DOMAINES)
    cohorte = models.ForeignKey(Cohorte, on_delete=models.PROTECT, related_name="projets",
                                help_text="Cohorte de l'appel à projets auquel l'idée a été soumise")
    porteur = models.ForeignKey(Porteur, on_delete=models.PROTECT, related_name="projets")
    nb_membres = models.PositiveSmallIntegerField(default=1)
    date_depot = models.DateField()
    preselectionne = models.BooleanField(default=False)
    selectionne = models.BooleanField(default=False, help_text="Retenu par le comité pour l'incubation")
    score_comite = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Note sur 100")
    date_selection = models.DateField(null=True, blank=True)
    date_prototype = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EVALUATION)
    progression = models.PositiveSmallIntegerField(default=0, help_text="Avancement estimé, 0 à 100 %")
    mentor = models.CharField(max_length=80, blank=True)
    emplois_crees = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-date_depot"]

    def __str__(self):
        return f"{self.code} — {self.titre}"

    @property
    def domaine_court(self):
        return DOMAINES_COURTS.get(self.domaine, self.domaine)


class Jalon(models.Model):
    class Etat(models.TextChoices):
        A_TEMPS = "a_temps", "Réalisé à temps"
        REALISE_RETARD = "realise_retard", "Réalisé en retard"
        EN_RETARD = "en_retard", "En retard"
        A_VENIR = "a_venir", "À venir"
        NON_ATTEINT = "non_atteint", "Non atteint (projet terminé)"

    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="jalons")
    titre = models.CharField(max_length=120)
    echeance = models.DateField()
    date_realisation = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["echeance"]

    def etat(self, aujourd_hui=None):
        aujourd_hui = aujourd_hui or date.today()
        if self.date_realisation:
            return self.Etat.A_TEMPS if self.date_realisation <= self.echeance else self.Etat.REALISE_RETARD
        if self.projet.statut in (Projet.Statut.ABANDONNE, Projet.Statut.SORTI):
            return self.Etat.NON_ATTEINT  # plus suivi : ne compte pas comme un retard en cours
        return self.Etat.EN_RETARD if self.echeance < aujourd_hui else self.Etat.A_VENIR

    @property
    def jours_retard(self):
        fin = self.date_realisation or date.today()
        return max(0, (fin - self.echeance).days)


class Partenariat(models.Model):
    class Type(models.TextChoices):
        ENTREPRISE = "entreprise", "Entreprise"
        PUBLIC = "public", "Institution publique"
        ONG = "ong", "ONG / coopération"
        FINANCIER = "financier", "Banque / institution financière"
        ACADEMIQUE = "academique", "Université / recherche"

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        NEGOCIATION = "negociation", "En négociation"
        TERMINE = "termine", "Terminé"

    partenaire = models.CharField(max_length=120)
    type = models.CharField(max_length=12, choices=Type.choices)
    projet = models.ForeignKey(Projet, null=True, blank=True, on_delete=models.CASCADE, related_name="partenariats",
                               help_text="Vide pour un partenariat institutionnel du CIAT")
    objet = models.CharField(max_length=160, blank=True)
    date_signature = models.DateField()
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.ACTIF)

    class Meta:
        ordering = ["-date_signature"]

    def __str__(self):
        return self.partenaire


class Financement(models.Model):
    class Type(models.TextChoices):
        SUBVENTION = "subvention", "Subvention"
        PRET = "pret", "Prêt / crédit"
        PRIX = "prix", "Prix / concours"
        PRIVE = "prive", "Apport privé / investisseur"

    class Statut(models.TextChoices):
        OBTENU = "obtenu", "Obtenu"
        DEMANDE = "demande", "Demandé"
        REFUSE = "refuse", "Refusé"

    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="financements")
    organisme = models.CharField(max_length=120)
    type = models.CharField(max_length=12, choices=Type.choices)
    montant = models.PositiveBigIntegerField(help_text="Montant en FCFA")
    date = models.DateField()
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.OBTENU)

    class Meta:
        ordering = ["-date"]


class Requete(models.Model):
    """Journal des questions posées à l'assistant de données (traçabilité de l'usage de l'IA)."""

    utilisateur = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="requetes")
    question = models.CharField(max_length=500)
    specification = models.JSONField(null=True, blank=True, help_text="Requête structurée produite et validée")
    reponse = models.TextField(blank=True)
    mode = models.CharField(max_length=12, blank=True, help_text="gemini, regles ou refus")
    succes = models.BooleanField(default=True)
    duree_ms = models.PositiveIntegerField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le"]
