from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("profil/", views.profil, name="profil"),
    path("demande-acces/", views.demande_acces, name="demande_acces"),
    path("demandes/", views.demandes, name="demandes"),
    path("demandes/<int:pk>/", views.traiter_demande, name="traiter_demande"),
]
