from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    # path("profiles/", views.profile_list, name="profile_list"),
    # path("profiles/<int:profile_id>/", views.profile_detail, name="profile_detail"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),
]