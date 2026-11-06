from django.urls import path

from .views import chat_home, chat_room, delete_message, get_message, send_message

urlpatterns = [
    path("", chat_home, name="chat-home"),
    path("<int:match_id>/", chat_room, name="chat-room"),
    path("<int:match_id>/messages/", get_message, name="get-message"),
    path("<int:match_id>/send/", send_message, name="send-message"),
    path("messages/<int:message_id>/delete/", delete_message, name="delete-message"),
]
