from django.contrib.auth.models import User
from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Student(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=50, unique=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="students")

    class Meta:
        ordering = ["roll_number"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.roll_number})"

    def calculate_attendance_percentage(self):
        attendance_records = self.attendance_records.all()
        total_lessons = attendance_records.count()
        if total_lessons == 0:
            return 0.0

        weighted_total = 0.0
        for record in attendance_records:
            if record.status == "P":
                weighted_total += 1.0
            elif record.status == "L":
                weighted_total += 0.5
            elif record.status == "A":
                weighted_total += 0.0

        return round((weighted_total / total_lessons) * 100, 2)


class Lesson(models.Model):
    subject_name = models.CharField(max_length=100)
    date = models.DateField()
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="lessons")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.subject_name} - {self.date}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ("P", "Present"),
        ("A", "Absent"),
        ("L", "Late"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ("student", "lesson")

    def __str__(self):
        return f"{self.student} - {self.lesson} - {self.status}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("teacher", "მასწავლებელი"),
        ("student", "სტუდენტი"),
        ("admin", "ადმინისტრატორი"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="teacher")
    student = models.OneToOneField(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="profile")
    is_approved = models.BooleanField(default=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_profiles")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
