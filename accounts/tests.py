from django.test import TestCase
from django.urls import reverse

from .models import User


class AccueilEtDemandesTests(TestCase):
    def setUp(self):
        self.coord = User.objects.create_user("coord", password="Mdp-solide-2026", role=User.Role.COORDONNATEUR)
        self.dir = User.objects.create_user("dir", password="Mdp-solide-2026", role=User.Role.DIRECTION)

    def demande(self, **extra):
        data = {"first_name": "Moussa", "last_name": "Fall", "email": "moussa@isep.sn", "fonction": "Directeur des études",
                "role": "coordonnateur", "motif": "Suivi", "username": "mfall",
                "password1": "Diamniadio-2026!", "password2": "Diamniadio-2026!"}
        data.update(extra)
        return self.client.post(reverse("accounts:demande_acces"), data)

    def test_accueil_public(self):
        r = self.client.get("/")
        self.assertContains(r, "piloté par les données")
        self.assertContains(r, "Demander un accès")

    def test_accueil_connecte_propose_tableau_de_bord(self):
        self.client.force_login(self.dir)
        self.assertContains(self.client.get("/"), "Ouvrir le tableau de bord")

    def test_demande_cree_compte_inactif(self):
        r = self.demande()
        self.assertContains(r, "votre demande est envoyée")
        u = User.objects.get(username="mfall")
        self.assertFalse(u.is_active)
        self.assertFalse(u.is_staff)
        self.assertTrue(u.demande_en_attente)

    def test_connexion_en_attente_message_clair(self):
        self.demande()
        r = self.client.post(reverse("login"), {"username": "mfall", "password": "Diamniadio-2026!"})
        self.assertContains(r, "en attente de validation")

    def test_email_unique(self):
        self.demande()
        r = self.demande(username="autre")
        self.assertContains(r, "existe déjà")

    def test_direction_ne_voit_pas_les_demandes(self):
        self.client.force_login(self.dir)
        self.assertEqual(self.client.get(reverse("accounts:demandes")).status_code, 403)

    def test_coordonnateur_valide_puis_connexion(self):
        self.demande()
        u = User.objects.get(username="mfall")
        self.client.force_login(self.coord)
        self.assertContains(self.client.get(reverse("accounts:demandes")), "Moussa Fall")
        self.client.post(reverse("accounts:traiter_demande", args=[u.pk]), {"action": "valider", "role": "direction"})
        u.refresh_from_db()
        self.assertTrue(u.is_active)
        self.assertEqual(u.role, User.Role.DIRECTION)
        self.assertFalse(u.is_staff)
        self.client.logout()
        r = self.client.post(reverse("login"), {"username": "mfall", "password": "Diamniadio-2026!"})
        self.assertRedirects(r, reverse("pilotage:dashboard"), fetch_redirect_response=False)

    def test_refus_supprime(self):
        self.demande()
        u = User.objects.get(username="mfall")
        self.client.force_login(self.coord)
        self.client.post(reverse("accounts:traiter_demande", args=[u.pk]), {"action": "refuser"})
        self.assertFalse(User.objects.filter(username="mfall").exists())

    def test_role_admin_impossible_par_le_formulaire(self):
        self.demande(role="admin")
        self.assertFalse(User.objects.filter(username="mfall").exists())
