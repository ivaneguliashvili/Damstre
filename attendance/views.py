from calendar import monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import Attendance, Group, Lesson, Student, UserProfile


def get_profile_for_user(user):
    return UserProfile.objects.get_or_create(user=user, defaults={"role": "student", "is_approved": False})[0]


def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_profile_for_user(request.user)
        if request.user.is_superuser or profile.role == "admin":
            return view_func(request, *args, **kwargs)
        raise PermissionDenied

    return _wrapped_view


def teacher_or_admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        profile = get_profile_for_user(request.user)
        if request.user.is_superuser or profile.role in {"teacher", "admin"}:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied

    return _wrapped_view


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        role = (request.POST.get("role") or "student").strip()

        if not first_name or not last_name:
            messages.error(request, "სახელი და გვარი სავალდებულოა.")
        elif not username:
            messages.error(request, "მომხმარებლის სახელი სავალდებულოა.")
        elif User.objects.filter(username__iexact=username).exists():
            messages.error(request, "ეს მომხმარებლის სახელი უკვე დაკავებულია.")
        elif len(password) < 6:
            messages.error(request, "პაროლი უნდა იყოს მინიმუმ 6 სიმბოლო.")
        elif role not in {"student", "teacher"}:
            messages.error(request, "აირჩიეთ სწორი როლი.")
        else:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
            UserProfile.objects.create(user=user, role=role, is_approved=False)
            messages.success(
                request,
                f"{first_name} {last_name}, თქვენი მოთხოვნა მიღებულია. ადმინი დაეთანხმება თქვენს მოთხოვნას.",
            )
            return redirect("login")

    return render(request, "attendance/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            profile = get_profile_for_user(user)
            if profile.role in {"student", "teacher"} and not profile.is_approved:
                messages.error(request, "თქვენი ანგარიში ჯერ არ არის დადასტურებული.")
                return render(request, "attendance/login.html")
            login(request, user)
            messages.success(request, "მოგესალმებით!")
            return redirect("dashboard")

        messages.error(request, "არასწორი მომხმარებლის სახელი ან პაროლი.")

    return render(request, "attendance/login.html")


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "თქვენ გამოხვალეთ სისტემიდან.")
    return redirect("login")


@login_required
def dashboard(request):
    profile = get_profile_for_user(request.user)

    if profile.role == "student":
        if not profile.is_approved:
            logout(request)
            messages.error(request, "თქვენი ანგარიში არ არის დადასტურებული.")
            return redirect("login")
        if profile.student:
            return redirect("student_report", student_id=profile.student.id)

    groups = Group.objects.all().order_by("name")
    selected_group_id = request.GET.get("group")
    selected_group = None
    students = []
    lessons = []
    selected_date = None
    calendar_days = []
    calendar_entries = []
    lessons_by_date = {}
    selected_lessons = []

    current_month = request.GET.get("month")
    if current_month:
        try:
            year, month = map(int, current_month.split("-"))
        except ValueError:
            year, month = date.today().year, date.today().month
    else:
        today = date.today()
        year, month = today.year, today.month

    month_date = date(year, month, 1)
    month_days = monthrange(year, month)[1]
    start_weekday = month_date.weekday()

    for _ in range(start_weekday):
        calendar_days.append(None)
    for day_number in range(1, month_days + 1):
        calendar_days.append(date(year, month, day_number))
    while len(calendar_days) % 7 != 0:
        calendar_days.append(None)

    selected_date_value = request.GET.get("date")
    if selected_date_value:
        try:
            selected_date = date.fromisoformat(selected_date_value)
        except ValueError:
            selected_date = None

    if selected_group_id:
        selected_group = get_object_or_404(Group, id=selected_group_id)
        students = selected_group.students.all()
        lessons = list(selected_group.lessons.all().order_by("date", "subject_name"))

        for lesson in lessons:
            lessons_by_date.setdefault(lesson.date.isoformat(), []).append(lesson)

        if selected_date is None:
            selected_date = date.today()
        if selected_date.month != month:
            selected_date = month_date.replace(day=1)

        selected_lessons = lessons_by_date.get(selected_date.isoformat(), [])

    for day in calendar_days:
        if day is None:
            calendar_entries.append({"date": None, "has_lessons": False, "is_selected": False})
            continue

        iso_key = day.isoformat()
        calendar_entries.append({
            "date": day,
            "has_lessons": iso_key in lessons_by_date,
            "is_selected": selected_date == day,
        })

    for student in students:
        student.attendance_percentage = student.calculate_attendance_percentage()

    pending_users = UserProfile.objects.filter(role__in={"student", "teacher"}, is_approved=False).select_related("user")

    context = {
        "groups": groups,
        "selected_group": selected_group,
        "students": students,
        "lessons": lessons,
        "profile": profile,
        "pending_users": pending_users,
        "calendar_days": calendar_days,
        "calendar_entries": calendar_entries,
        "selected_lessons": selected_lessons,
        "selected_date": selected_date,
        "current_month": month_date,
        "calendar_year": year,
        "calendar_month": month,
        "previous_month": (month_date - timedelta(days=1)).replace(day=1),
        "next_month": (month_date.replace(day=28) + timedelta(days=4)).replace(day=1),
    }
    return render(request, "attendance/dashboard.html", context)


@admin_required
def approve_user(request, user_id):
    profile = get_object_or_404(UserProfile, user_id=user_id)
    profile.is_approved = True
    profile.approved_by = request.user
    profile.save()
    messages.success(request, "მომხმარებელი დამტკიცებულია.")
    return redirect("dashboard")


@admin_required
def reject_user(request, user_id):
    profile = get_object_or_404(UserProfile, user_id=user_id)
    user = profile.user
    profile.delete()
    user.delete()
    messages.warning(request, "მომხმარებელი წაიშალა.")
    return redirect("dashboard")


@teacher_or_admin_required
def create_student(request):
    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        roll_number = (request.POST.get("roll_number") or "").strip()
        group_id = request.POST.get("group")

        if not first_name or not last_name or not roll_number or not group_id:
            messages.error(request, "ყველა ველი სავალდებულოა.")
            return redirect("dashboard")

        group = get_object_or_404(Group, id=group_id)
        if Student.objects.filter(roll_number=roll_number).exists():
            messages.error(request, "ეს როლის ნომერი უკვე არსებობს.")
            return redirect("dashboard")

        student = Student.objects.create(first_name=first_name, last_name=last_name, roll_number=roll_number, group=group)
        username = slugify(f"{first_name}-{last_name}-{roll_number}") or f"student-{student.id}"
        base = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1

        user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, password="student123")
        profile = UserProfile.objects.get_or_create(user=user, defaults={"role": "student", "is_approved": True})[0]
        profile.role = "student"
        profile.student = student
        profile.is_approved = True
        profile.save()
        messages.success(request, "ახალი სტუდენტი წარმატებით შეიქმნა.")

    return redirect("dashboard")


@teacher_or_admin_required
def assign_existing_student_to_group(request):
    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        group_id = request.POST.get("group")

        if not first_name or not last_name or not group_id:
            messages.error(request, "სახელი, გვარი და ჯგუფი სავალდებულოა.")
            return redirect("dashboard")

        group = get_object_or_404(Group, id=group_id)
        profile = UserProfile.objects.filter(
            role="student",
            user__first_name__iexact=first_name,
            user__last_name__iexact=last_name,
        ).first()

        if not profile:
            messages.error(request, "ასეთი რეგისტრირებული სტუდენტი ვერ მოიძებნა.")
            return redirect("dashboard")

        student = profile.student
        if not student:
            base_roll = slugify(f"{first_name}-{last_name}-{group.name}") or f"student-{profile.user_id}"
            roll_number = base_roll
            counter = 1
            while Student.objects.filter(roll_number=roll_number).exists():
                roll_number = f"{base_roll}-{counter}"
                counter += 1

            student = Student.objects.create(
                first_name=first_name,
                last_name=last_name,
                roll_number=roll_number,
                group=group,
            )

        elif student.group_id != group.id:
            student.group = group
            student.save(update_fields=["group"])

        profile.student = student
        profile.is_approved = True
        profile.save(update_fields=["student", "is_approved"])
        messages.success(request, f"{first_name} {last_name} წარმატებით დაემატა ჯგუფს {group.name}.")

    return redirect("dashboard")


@admin_required
def create_teacher(request):
    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        if not first_name or not last_name or not username:
            messages.error(request, "სახელი, გვარი და username სავალდებულოა.")
            return redirect("dashboard")

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "ეს username უკვე დაკავებულია.")
            return redirect("dashboard")

        if len(password) < 6:
            messages.error(request, "პაროლი უნდა იყოს მინიმუმ 6 სიმბოლო.")
            return redirect("dashboard")

        user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, password=password)
        profile = UserProfile.objects.get_or_create(user=user, defaults={"role": "teacher", "is_approved": True})[0]
        profile.role = "teacher"
        profile.is_approved = True
        profile.student = None
        profile.save()
        messages.success(request, "ახალი მასწავლებელი წარმატებით შეიქმნა.")

    return redirect("dashboard")


@teacher_or_admin_required
def create_lesson(request):
    if request.method == "POST":
        subject_name = (request.POST.get("subject_name") or "").strip()
        date = request.POST.get("date")
        group_id = request.POST.get("group")

        if not subject_name or not date or not group_id:
            messages.error(request, "სასწორი ინფორმაცია აუცილებელია.")
            return redirect("dashboard")

        group = get_object_or_404(Group, id=group_id)
        Lesson.objects.create(subject_name=subject_name, date=date, group=group)
        messages.success(request, "საგანი დამატებულია.")

    return redirect("dashboard")


@admin_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    lesson.delete()
    messages.warning(request, "საგანი წაიშალა.")
    return redirect("dashboard")


@admin_required
def create_group(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            Group.objects.create(name=name)
            messages.success(request, "ჯგუფი დამატებულია.")
    return redirect("dashboard")


@admin_required
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    group.delete()
    messages.warning(request, "ჯგუფი წაიშალა.")
    return redirect("dashboard")


@login_required
def mark_attendance(request, lesson_id):
    profile = get_profile_for_user(request.user)
    if profile.role not in {"teacher", "admin"}:
        raise PermissionDenied

    lesson = get_object_or_404(Lesson, id=lesson_id)
    students = lesson.group.students.all().order_by("roll_number")

    if request.method == "POST":
        for student in students:
            status = request.POST.get(f"status_{student.id}", "A")
            Attendance.objects.update_or_create(
                student=student,
                lesson=lesson,
                defaults={"status": status},
            )
        messages.success(request, "დასწრება წარმატებით შენახულია.")
        return redirect("dashboard")

    for student in students:
        attendance_record = Attendance.objects.filter(student=student, lesson=lesson).first()
        student.current_status = attendance_record.status if attendance_record else "A"

    context = {
        "lesson": lesson,
        "students": students,
    }
    return render(request, "attendance/mark_attendance.html", context)


@login_required
def student_report(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    profile = get_profile_for_user(request.user)

    if profile.role == "student" and profile.student_id != student.id:
        raise PermissionDenied

    attendance_history = Attendance.objects.filter(student=student).select_related("lesson").order_by("-lesson__date")
    percentage = student.calculate_attendance_percentage()

    current_month = request.GET.get("month")
    if current_month:
        try:
            year, month = map(int, current_month.split("-"))
        except ValueError:
            year, month = date.today().year, date.today().month
    else:
        today = date.today()
        year, month = today.year, today.month

    month_date = date(year, month, 1)
    month_days = monthrange(year, month)[1]
    start_weekday = month_date.weekday()
    calendar_days = []
    for _ in range(start_weekday):
        calendar_days.append(None)
    for day_number in range(1, month_days + 1):
        calendar_days.append(date(year, month, day_number))
    while len(calendar_days) % 7 != 0:
        calendar_days.append(None)

    attendance_by_date = {}
    for record in attendance_history:
        attendance_by_date[record.lesson.date.isoformat()] = record.status

    calendar_entries = []
    for day in calendar_days:
        if day is None:
            calendar_entries.append({"date": None, "status": None})
            continue
        iso_key = day.isoformat()
        calendar_entries.append({
            "date": day,
            "status": attendance_by_date.get(iso_key),
        })

    context = {
        "student": student,
        "attendance_history": attendance_history,
        "percentage": percentage,
        "profile": profile,
        "calendar_days": calendar_days,
        "calendar_entries": calendar_entries,
        "attendance_by_date": attendance_by_date,
        "current_month": month_date,
        "calendar_year": year,
        "calendar_month": month,
        "previous_month": (month_date - timedelta(days=1)).replace(day=1),
        "next_month": (month_date.replace(day=28) + timedelta(days=4)).replace(day=1),
    }
    return render(request, "attendance/student_report.html", context)
