from django.contrib import admin

from .models import Cohorte, Financement, Jalon, Partenariat, Porteur, Projet, Requete


class JalonInline(admin.TabularInline):
    model = Jalon
    extra = 0


class FinancementInline(admin.TabularInline):
    model = Financement
    extra = 0


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ("code", "titre", "domaine", "cohorte", "statut", "selectionne", "progression")
    list_filter = ("cohorte", "domaine", "statut", "selectionne", "porteur__genre")
    search_fields = ("code", "titre", "porteur__nom", "porteur__prenom")
    inlines = [JalonInline, FinancementInline]
    autocomplete_fields = ["porteur"]


@admin.register(Porteur)
class PorteurAdmin(admin.ModelAdmin):
    list_display = ("code", "prenom", "nom", "genre", "profil", "region")
    list_filter = ("genre", "profil", "region")
    search_fields = ("code", "nom", "prenom")


@admin.register(Partenariat)
class PartenariatAdmin(admin.ModelAdmin):
    list_display = ("partenaire", "type", "projet", "statut", "date_signature")
    list_filter = ("type", "statut")


@admin.register(Requete)
class RequeteAdmin(admin.ModelAdmin):
    list_display = ("question", "utilisateur", "mode", "succes", "cree_le")
    list_filter = ("mode", "succes")


admin.site.register(Cohorte)
admin.site.register(Financement)
