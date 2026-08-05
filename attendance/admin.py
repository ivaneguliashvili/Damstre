from django.contrib import admin

from .models import Attendance, Group, Lesson, Student, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "student")
    list_filter = ("role",)
    search_fields = ("user__username", "student__first_name", "student__last_name")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_filter = ("name",)
    search_fields = ("name",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("roll_number", "first_name", "last_name", "group")
    list_filter = ("group",)
    search_fields = ("first_name", "last_name", "roll_number")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("subject_name", "date", "group")
    list_filter = ("group", "date", "subject_name")
    search_fields = ("subject_name", "group__name")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "lesson", "status")
    list_filter = ("lesson__group", "lesson__subject_name", "status")
    search_fields = ("student__first_name", "student__last_name", "student__roll_number")
