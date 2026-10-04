from django.urls import path
from . import views
# from views import block_user, unblock_user

urlpatterns = [
    path("", views.home, name="home"),
    # path("profiles/", views.profile_list, name="profile_list"),
    # path("profiles/<int:profile_id>/", views.profile_detail, name="profile_detail"),
    path("feed/", views.feed, name="feed"),
    path("profile/<int:profile_id>/", views.profile_detail, name="profile-detail"),
    path("match/<int:user_id>/", views.create_match, name="create-match"),
    path("match/<int:match_id>/accept/", views.accept_match, name="accept-match"),
    path("profile/edit/", views.edit_profile, name="edit-profile"),
    path("profile/detail/", views.profile_detail, name="profile-detail")
    # path("block/<int:user_id>/", block_user, name="block-user"),
    # path("unblock/<int:user_id>/", unblock_user, name="unblock-user"),
]