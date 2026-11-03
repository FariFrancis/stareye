from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sending_user", "match", "creation_date", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("sending_user__user__username", "message")
