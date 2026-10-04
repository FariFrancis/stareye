from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect
from django.http import JsonResponse

def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not username or not password:
            return JsonResponse({"error": "Username and password required"}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already taken"}, status=400)

        user = User.objects.create_user(username=username, email = email, password=password)
        auth_login(request, user)

        return JsonResponse({"status": "signup_success"})

    return render(request, "signup.html")


def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return JsonResponse({"error": "Invalid credentials"}, status=400)

        auth_login(request, user)
        return JsonResponse({"status": "login_success"})

    return render(request, "login.html")


def logout(request):
    auth_logout(request)
    return redirect("login")
    
@login_required
def change_email(request):
    user = request.user

    if request.method == "POST":
        new_email = request.POST.get("email")

        if User.objects.filter(email=new_email).exclude(id=user.id).exists():
            return render(request, "change_email.html", {
                "error": "Email already in use",
                "email": user.email
            })

        user.email = new_email
        user.save()

        return redirect("/profile/" + str(user.id))

    return render(request, "change_email.html", {"email": user.email})
