from django import forms

from .models import User


class ProfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "fonction")
        labels = {"first_name": "Prénom", "last_name": "Nom", "email": "E-mail"}
