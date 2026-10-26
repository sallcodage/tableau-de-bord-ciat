from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Utilisateur du tableau de bord avec un rôle métier.

    - Direction : consultation des analyses, données anonymisées (pas de nom de porteur)
    - Coordonnateur : consultation complète + saisie et import des données
    - Administrateur : tout, y compris la gestion des comptes
    """

    class Role(models.TextChoices):
        DIRECTION = "direction", "Direction (lecture)"
        COORDONNATEUR = "coordonnateur", "Coordonnateur de l'incubateur"
        ADMIN = "admin", "Administrateur"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DIRECTION)
    fonction = models.CharField(max_length=120, blank=True)

    @property
    def peut_saisir(self):
        return self.is_superuser or self.role in (self.Role.COORDONNATEUR, self.Role.ADMIN)

    @property
    def voit_noms(self):
        """Seuls les coordonnateurs et administrateurs voient l'identité des porteurs."""
        return self.peut_saisir

    def __str__(self):
        return self.get_full_name() or self.username
