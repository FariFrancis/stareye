from django.contrib import admin
from django.contrib.auth.models import Group, User

# Register your models here.



# Register your models here.
from django.contrib import admin

from date.models import UserProfile



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    pass

admin.site.unregister(User)
admin.site.register(User, UserProfileAdmin)
admin.site.unregister(Group)
