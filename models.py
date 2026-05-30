from django.db import models


# ================= FACULTY =================
class FacultyRegisteredTable(models.Model):
    name = models.CharField(max_length=100)
    faculty_id = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.faculty_id


# ================= STUDENT =================
class StudentTable(models.Model):
    faculty = models.ForeignKey(
        FacultyRegisteredTable,
        on_delete=models.CASCADE,
        related_name='students'
    )

    name = models.CharField(max_length=100)
    rollnumber = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    studentmobile = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=100)

    parent_name = models.CharField(max_length=100)
    parent_email = models.EmailField()
    parent_number = models.CharField(max_length=15)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.rollnumber


# ================= SEMESTER =================
class SemesterTable(models.Model):
    student = models.ForeignKey(StudentTable, on_delete=models.CASCADE, related_name='semesters')
    semester = models.IntegerField()
    attendance = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Semester {self.semester} - {self.student.rollnumber}"


# ================= SUBJECT =================
class SubjectMarks(models.Model):
    semester = models.ForeignKey(SemesterTable, on_delete=models.CASCADE, related_name='subjects')
    subject = models.CharField(max_length=100)
    marks = models.FloatField()
    pass_fail = models.CharField(max_length=10, choices=[('Pass', 'Pass'), ('Fail', 'Fail')], default='Pass')

    def __str__(self):
        return f"{self.subject}: {self.marks} ({self.pass_fail})"
