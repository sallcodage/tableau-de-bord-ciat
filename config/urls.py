from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

admin.site.site_header = "Administration — Tableau de bord du CIAT"
admin.site.site_title = "CIAT"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="pilotage:dashboard", permanent=False)),
    path("connexion/", auth_views.LoginView.as_view(), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("compte/", include("accounts.urls")),
    path("", include("pilotage.urls")),
    path("admin/", admin.site.urls),
]
