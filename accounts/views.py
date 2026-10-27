from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DemandeAccesForm, ProfilForm
from .models import User, donner_droits


@login_required
def profil(request):
    form = ProfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil mis à jour.")
        return redirect("accounts:profil")
    return render(request, "accounts/profil.html", {"form": form})


def demande_acces(request):
    """Formulaire public : crée un compte inactif, validé ensuite par le CIAT."""
    if request.user.is_authenticated:
        return redirect("pilotage:dashboard")
    form = DemandeAccesForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return render(request, "accounts/demande_envoyee.html", {"prenom": form.cleaned_data["first_name"]})
    return render(request, "accounts/demande_acces.html", {"form": form})


def _gestionnaire(request):
    if not request.user.peut_saisir:
        raise PermissionDenied


@login_required
def demandes(request):
    _gestionnaire(request)
    return render(request, "accounts/demandes.html", {
        "demandes": User.objects.filter(demande_en_attente=True).order_by("date_joined"),
        "roles": DemandeAccesForm.ROLES,
    })


@login_required
@require_POST
def traiter_demande(request, pk):
    _gestionnaire(request)
    u = get_object_or_404(User, pk=pk, demande_en_attente=True)
    if request.POST.get("action") == "refuser":
        nom = u.get_full_name() or u.username
        u.delete()
        messages.info(request, f"Demande de {nom} refusée.")
    else:
        role = request.POST.get("role")
        if role not in dict(DemandeAccesForm.ROLES):
            role = User.Role.DIRECTION
        u.is_active, u.demande_en_attente = True, False
        donner_droits(u, role)
        messages.success(request, f"Accès de {u.get_full_name() or u.username} validé : {u.get_role_display()}.")
    return redirect("accounts:demandes")
