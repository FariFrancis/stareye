from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("feed/", views.feed, name="feed"),
    path("matches/", views.matches, name="matches"),
    path("profile/me/", views.my_profile, name="my-profile"),
    path("profile/edit/", views.edit_profile, name="edit-profile"),
    path("profile/<int:profile_id>/", views.profile_detail, name="profile-detail"),
    path("match/<int:user_id>/", views.create_match, name="create-match"),
    path("photos/", views.photos, name="photos"),
    path("photos/<int:photo_id>/delete/", views.photo_delete, name="photo-delete"),
    path("location/", views.location, name="location"),
    path("location/clear/", views.clear_location, name="clear-location"),
    # path("pass/<int:user_id>/", views.pass_user, name="pass-user"),
    path("match/<int:match_id>/accept/", views.accept_match, name="accept-match"),
    path("match/<int:match_id>/reject/", views.reject_match, name="reject-match"),
    path("block/<int:user_id>/", views.block_user, name="block-user"),
    path("unblock/<int:user_id>/", views.unblock_user, name="unblock-user"),
]
