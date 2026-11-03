from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ChangeEmailForm, SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("feed")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, "Welcome to Stareye! Finish your profile to get started.")
        return redirect("edit-profile")
    return render(request, "signup.html", {"form": form})


@login_required
def change_email(request):
    form = ChangeEmailForm(
        request.POST or None, user=request.user, initial={"email": request.user.email}
    )
    if request.method == "POST" and form.is_valid():
        request.user.email = form.cleaned_data["email"]
        request.user.save(update_fields=["email"])
        messages.success(request, "Email updated.")
        return redirect("profile-detail", profile_id=request.user.id)
    return render(request, "change_email.html", {"form": form})
