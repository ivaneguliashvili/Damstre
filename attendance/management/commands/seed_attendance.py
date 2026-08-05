from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from attendance.models import Attendance, Group, Lesson, Student, UserProfile


class Command(BaseCommand):
    help = "Seed the database with sample groups, students, lessons, attendance records, and role-based users for DAMSSTRE."

    def handle(self, *args, **options):
        Group.objects.all().delete()
        Student.objects.all().delete()
        Lesson.objects.all().delete()
        Attendance.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        group_a = Group.objects.create(name="ჯგუფი 1")
        group_b = Group.objects.create(name="ჯგუფი 2")

        students = [
            ("ანა", "მამულაშვილი", "G-101-01", group_a),
            ("ზურაბ", "ქუთათელი", "G-101-02", group_a),
            ("ნინო", "გიორგაძე", "G-101-03", group_a),
            ("ლევან", "ტაბიძე", "K-202-01", group_b),
            ("მარიამ", "ხუციშვილი", "K-202-02", group_b),
            ("თამთა", "სალუქვაძე", "K-202-03", group_b),
        ]

        created_students = []
        for first_name, last_name, roll_number, group in students:
            student = Student.objects.create(
                first_name=first_name,
                last_name=last_name,
                roll_number=roll_number,
                group=group,
            )
            created_students.append(student)

        lessons = [
            ("მათემატიკა", date(2026, 7, 10), group_a),
            ("ფიზიკა", date(2026, 7, 12), group_a),
            ("პროგრამირება", date(2026, 7, 11), group_b),
            ("ბაზები", date(2026, 7, 13), group_b),
        ]

        created_lessons = []
        for subject_name, lesson_date, group in lessons:
            lesson = Lesson.objects.create(subject_name=subject_name, date=lesson_date, group=group)
            created_lessons.append(lesson)

        attendance_map = {
            group_a.id: [
                (created_students[0], created_lessons[0], "P"),
                (created_students[1], created_lessons[0], "L"),
                (created_students[2], created_lessons[0], "A"),
                (created_students[0], created_lessons[1], "P"),
                (created_students[1], created_lessons[1], "P"),
                (created_students[2], created_lessons[1], "L"),
            ],
            group_b.id: [
                (created_students[3], created_lessons[2], "P"),
                (created_students[4], created_lessons[2], "A"),
                (created_students[5], created_lessons[2], "P"),
                (created_students[3], created_lessons[3], "L"),
                (created_students[4], created_lessons[3], "P"),
                (created_students[5], created_lessons[3], "A"),
            ],
        }

        for _, records in attendance_map.items():
            for student, lesson, status in records:
                Attendance.objects.create(student=student, lesson=lesson, status=status)

        teacher = User.objects.create_user(username="teacher", password="teacher123")
        UserProfile.objects.create(user=teacher, role="teacher")

        admin_user = User.objects.create_user(username="admin", password="admin123")
        UserProfile.objects.create(user=admin_user, role="admin")

        for student in created_students:
            username = f"student_{student.roll_number.lower().replace('-', '_')}"
            user = User.objects.create_user(username=username, password="student123")
            UserProfile.objects.create(user=user, role="student", student=student)

        self.stdout.write(self.style.SUCCESS("Sample attendance data and role-based users seeded successfully."))
