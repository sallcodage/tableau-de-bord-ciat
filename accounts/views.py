from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfilForm


@login_required
def profil(request):
    form = ProfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil mis à jour.")
        return redirect("accounts:profil")
    return render(request, "accounts/profil.html", {"form": form})
