from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("profil/", views.profil, name="profil"),
]
