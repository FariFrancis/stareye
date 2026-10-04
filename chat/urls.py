from django.urls import path, include
from .views import get_message, send_message, delete_message

urlpatterns = [
    path('<int:match_id>/messages/', get_message, name="get-message"),
    path("<int:match_id>/send/", send_message, name="send-message"),
    path("messages/<int:message_id>/delete/", delete_message, name="delete-message")
]