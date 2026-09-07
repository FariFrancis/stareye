from django.shortcuts import render
from .data import profiles

def home(request):
    return render(request, "date/home.html")

def profile_list(request):
    return render(request, "date/profile_list.html", {"profiles": profiles})

def profile_detail(request, profile_id):
    profile = next((p for p in profiles if p["id"] == profile_id), None)
    return render(request, "date/profile_detail.html", {"profile": profile})

def signup(request):
    return render(request, "date/signup.html")

def login(request):
    return render(request, "date/login.html")