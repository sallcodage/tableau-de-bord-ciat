"""
Charge le jeu de données (data/*.csv) et crée les comptes de démonstration.

    python manage.py seed_demo
"""
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import User
from pilotage.importation import FICHIERS, importer


class Command(BaseCommand):
    help = "Importe data/*.csv et crée les comptes demo_direction, demo_coordonnateur, demo_admin"

    def handle(self, *args, **opts):
        dossier = Path(settings.BASE_DIR) / "data"
        stats = importer({nom: dossier / f"{nom}.csv" for nom in FICHIERS}, remplacer=True)
        self.stdout.write("  import : " + ", ".join(f"{v} {k}" for k, v in stats.items()))

        mdp = os.getenv("DEMO_PASSWORD", "Ciat2026!demo")
        for username, prenom, nom, role, fonction, superuser in [
            ("demo_direction", "Aïssatou", "Diallo", User.Role.DIRECTION, "Direction de l'ISEP", False),
            ("demo_coordonnateur", "Awa", "Ndiaye", User.Role.COORDONNATEUR, "Coordonnatrice de l'incubateur", False),
            ("demo_admin", "Admin", "CIAT", User.Role.ADMIN, "Administrateur technique", True),
        ]:
            u, _ = User.objects.get_or_create(username=username)
            u.first_name, u.last_name, u.role, u.fonction = prenom, nom, role, fonction
            u.email = f"{username}@exemple.sn"
            u.is_staff = u.is_superuser = superuser
            u.set_password(mdp)
            u.save()
            self.stdout.write(f"  compte {username} ({u.get_role_display()})")
        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes."))
