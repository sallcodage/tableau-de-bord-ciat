from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class ProfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "fonction")
        labels = {"first_name": "Prénom", "last_name": "Nom", "email": "E-mail"}


class ConnexionForm(AuthenticationForm):
    """Connexion : message clair si la demande d'accès n'est pas encore validée."""

    error_messages = {
        "invalid_login": "Identifiant ou mot de passe incorrect.",
        "en_attente": "Votre demande d'accès est en attente de validation par le CIAT.",
        "inactive": "Ce compte est désactivé.",
    }

    def clean(self):
        username, password = self.cleaned_data.get("username"), self.cleaned_data.get("password")
        if username and password and authenticate(self.request, username=username, password=password) is None:
            u = User.objects.filter(username=username, is_active=False).first()
            if u and u.check_password(password):
                code = "en_attente" if u.demande_en_attente else "inactive"
                raise forms.ValidationError(self.error_messages[code], code=code)
        return super().clean()


class DemandeAccesForm(UserCreationForm):
    ROLES = [
        (User.Role.DIRECTION, "Direction : consulter les analyses (données anonymisées)"),
        (User.Role.COORDONNATEUR, "Coordination de l'incubateur : analyses, noms des porteurs, import des données"),
    ]
    role = forms.ChoiceField(label="Accès souhaité", choices=ROLES, widget=forms.RadioSelect,
                             initial=User.Role.DIRECTION)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "fonction", "username", "motif")
        labels = {"first_name": "Prénom", "last_name": "Nom", "email": "E-mail professionnel",
                  "fonction": "Fonction", "username": "Nom d'utilisateur", "motif": "Pourquoi avez-vous besoin d'un accès ?"}
        help_texts = {"username": "Lettres, chiffres et @ . + - _ uniquement.",
                      "fonction": "Exemple : Directeur des études, Chargée de suivi de l'incubateur."}
        widgets = {"motif": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom in ("first_name", "last_name", "email", "fonction"):
            self.fields[nom].required = True
        self.fields["motif"].required = False

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Une demande ou un compte existe déjà avec cette adresse.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.is_active = False
        user.is_staff = False
        user.demande_en_attente = True
        if commit:
            user.save()
        return user
