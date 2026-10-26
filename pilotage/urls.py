from django.urls import path

from . import views

app_name = "pilotage"
urlpatterns = [
    path("tableau-de-bord/", views.tableau_de_bord, name="dashboard"),
    path("projets/", views.projets, name="projets"),
    path("projets/<str:code>/", views.fiche_projet, name="fiche_projet"),
    path("cohortes/", views.cohortes, name="cohortes"),
    path("cohortes/<int:annee>/", views.fiche_cohorte, name="fiche_cohorte"),
    path("assistant/", views.assistant_donnees, name="assistant"),
    path("export/excel/", views.export_excel, name="export_excel"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path("donnees/", views.donnees, name="donnees"),
    path("donnees/modele/<str:nom>.csv", views.modele_csv, name="modele_csv"),
    path("methodologie/", views.methodologie, name="methodologie"),
]
