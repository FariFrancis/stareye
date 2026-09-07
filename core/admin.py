from django.contrib import admin

# Register your models here.

from core.models import Person, Course, Grade

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name",)

    # def show_average(self, obj):
    #     from django.db.models import Avg
        # result = Grade.objects.filter(person=obj).aggregate(Avg("grade"))
        # return result["grade_avg"]

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    pass

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    pass