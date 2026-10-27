from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts.forms import ConnexionForm
from pilotage.views import accueil

admin.site.site_header = "Administration — Tableau de bord du CIAT"
admin.site.site_title = "CIAT"

urlpatterns = [
    path("", accueil, name="accueil"),
    path("connexion/", auth_views.LoginView.as_view(authentication_form=ConnexionForm, redirect_authenticated_user=True), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("compte/", include("accounts.urls")),
    path("", include("pilotage.urls")),
    path("admin/", admin.site.urls),
]
