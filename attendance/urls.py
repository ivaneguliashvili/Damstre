from django.urls import path

from .views import (
    approve_user,
    assign_existing_student_to_group,
    create_group,
    create_lesson,
    create_student,
    create_teacher,
    dashboard,
    delete_group,
    delete_lesson,
    login_view,
    logout_view,
    mark_attendance,
    reject_user,
    register_view,
    student_report,
)

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("approve-user/<int:user_id>/", approve_user, name="approve_user"),
    path("reject-user/<int:user_id>/", reject_user, name="reject_user"),
    path("student/create/", create_student, name="create_student"),
    path("student/assign-existing/", assign_existing_student_to_group, name="assign_existing_student_to_group"),
    path("teacher/create/", create_teacher, name="create_teacher"),
    path("lesson/create/", create_lesson, name="create_lesson"),
    path("lesson/<int:lesson_id>/delete/", delete_lesson, name="delete_lesson"),
    path("group/create/", create_group, name="create_group"),
    path("group/<int:group_id>/delete/", delete_group, name="delete_group"),
    path("lesson/<int:lesson_id>/mark/", mark_attendance, name="mark_attendance"),
    path("student/<int:student_id>/report/", student_report, name="student_report"),
]
