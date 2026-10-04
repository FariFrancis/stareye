from django.contrib import admin
from django.contrib.auth.models import Group, User
# from .models import Block

# Register your models here.



# Register your models here.
from django.contrib import admin

from date.models import UserProfile



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    pass


# @admin.register(Block)
# class BlockAdmin(admin.ModelAdmin):
#     list_display = ("blocker", "blocked", "created_at")
#     search_fields = ("blocker__user__username", "blocked__user__username")

admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)
admin.site.unregister(Group)
