from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings
from django.http import JsonResponse
from .models import FacultyRegisteredTable, StudentTable, SemesterTable, SubjectMarks
from django.core.mail import send_mail
import io
import base64
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Import Bytez AI utility
from Management.ai_utils import generate_ai_suggestion as get_ai_suggestion, get_ai_chatbot_response


# ======================
# EMAIL FUNCTION
# ======================
def send_result_email(student, sem):
    marks = SubjectMarks.objects.filter(semester=sem)
    
    body = "Dear " + str(student.name) + ",\n\n"
    body += "Semester " + str(sem.semester) + " Results\n"
    body += "=" * 40 + "\n"
    body += "Attendance: " + str(sem.attendance) + "%\n\n"
    body += "Subject Marks:\n"
    body += "-" * 40 + "\n"
    
    total = 0
    count = 0
    for m in marks:
        body += str(m.subject) + ": " + str(m.marks) + " (" + str(m.pass_fail) + ")\n"
        total += m.marks
        count += 1
    
    if count > 0:
        body += "-" * 40 + "\n"
        body += "Average: " + str(round(total/count, 2)) + "\n"
    
    body += "\nBest regards,\nCollege Management"
    
    recipients = [student.email]
    if student.parent_email:
        recipients.append(student.parent_email)
    
    try:
        send_mail(
            "Semester " + str(sem.semester) + " Results - " + str(student.rollnumber),
            body,
            settings.EMAIL_HOST_USER,
            recipients,
            fail_silently=False,
        )
        return True
    except:
        return False


# ======================
# GRAPH FUNCTIONS
# ======================
def generate_graph(values, chart_type="line"):
    plt.figure(figsize=(10, 6))
    
    if chart_type == "line":
        plt.plot(values, marker='o', linewidth=2, color='#00ffd5')
        plt.fill_between(range(len(values)), values, alpha=0.3, color='#00ffd5')
    elif chart_type == "bar":
        plt.bar(range(len(values)), values, color='#00ffd5', edgecolor='white')
    else:
        plt.pie(values, autopct='%1.1f%%', colors=['#00ffd5', '#ff6b6b', '#4ecdc4'])
    
    plt.grid(True, alpha=0.3)
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', transparent=True, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64



# ======================
# FACULTY LOGIN
# ======================
def facultyLogin(request):
    if request.method == 'POST':
        fid = request.POST.get('facultyid')
        pwd = request.POST.get('password')
        
        try:
            faculty = FacultyRegisteredTable.objects.get(
                faculty_id=fid,
                password=pwd,
                status=True
            )
            request.session['faculty'] = faculty.id
            request.session['faculty_name'] = faculty.name
            return redirect('faculty_home')
        except:
            messages.error(request, "Invalid Login or Account Deactivated")
    
    return render(request, 'facultyLogin.html')


# ======================
# FACULTY HOME
# ======================
def faculty_home(request):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    faculty = FacultyRegisteredTable.objects.get(id=request.session['faculty'])
    students = StudentTable.objects.filter(faculty=faculty)
    
    return render(request, 'Faculty/facultyHome.html', {
        'faculty': faculty,
        'student_count': students.count()
    })


def faculty_logout(request):
    if request.session.get('faculty'):
        del request.session['faculty']
    return redirect('facultyLogin')


# ======================
# STUDENT MANAGEMENT
# ======================
def faculty_students(request):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    faculty = FacultyRegisteredTable.objects.get(id=request.session['faculty'])
    students = StudentTable.objects.filter(faculty=faculty).order_by('-created_at')
    
    return render(request, 'Faculty/facultyStudents.html', {'students': students})


def add_student(request):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    if request.method == 'POST':
        faculty = FacultyRegisteredTable.objects.get(id=request.session['faculty'])
        StudentTable.objects.create(
            faculty=faculty,
            name=request.POST.get('name'),
            rollnumber=request.POST.get('roll'),
            email=request.POST.get('email'),
            studentmobile=request.POST.get('mobile'),
            parent_name=request.POST.get('parentname'),
            parent_email=request.POST.get('parentemail'),
            parent_number=request.POST.get('parentnumber')
        )
        messages.success(request, "Student Added Successfully!")
        return redirect('faculty_students')
    
    return render(request, 'Faculty/addStudent.html')


def edit_student(request, id):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    student = StudentTable.objects.get(id=id)
    
    if request.method == 'POST':
        student.name = request.POST.get('name')
        student.rollnumber = request.POST.get('roll')
        student.email = request.POST.get('email')
        student.studentmobile = request.POST.get('mobile')
        student.password = request.POST.get('password')
        
        student.parent_name = request.POST.get('parentname')
        student.parent_email = request.POST.get('parentemail')
        student.parent_number = request.POST.get('parentnumber')
        student.save()
        messages.success(request, "Student Updated!")
        return redirect('faculty_students')
    
    return render(request, 'Faculty/editStudent.html', {'student': student})


def delete_student(request, id):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    StudentTable.objects.get(id=id).delete()
    messages.success(request, "Student Deleted!")
    return redirect('faculty_students')


# ======================
# SEMESTER & MARKS
# ======================
def add_semester(request, student_id):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    student = StudentTable.objects.get(id=student_id)
    
    if request.method == 'POST':
        sem = SemesterTable.objects.create(
            student=student,
            semester=request.POST.get('semester'),
            attendance=request.POST.get('attendance')
        )
        
        subjects = request.POST.getlist('subject')
        marks = request.POST.getlist('marks')
        pass_fails = request.POST.getlist('pass_fail')
        
        for s, m, pf in zip(subjects, marks, pass_fails):
            if s and m:
                SubjectMarks.objects.create(semester=sem, subject=s, marks=float(m), pass_fail=pf)
        
        send_result_email(student, sem)
        
        messages.success(request, "Marks Added & Email Sent!")
        return redirect('faculty_students')
    
    return render(request, 'Faculty/addSemester.html', {'student': student})


def view_student_semesters(request, student_id):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    student = StudentTable.objects.get(id=student_id)
    semesters = SemesterTable.objects.filter(student=student).order_by('-semester')
    
    semester_data = []
    for sem in semesters:
        marks = SubjectMarks.objects.filter(semester=sem)
        avg = sum(m.marks for m in marks) / len(marks) if marks else 0
        semester_data.append({
            'semester': sem,
            'marks': marks,
            'average': avg
        })
    
    # Convert to JSON for JavaScript
    semester_data_json = []
    for sd in semester_data:
        marks_list = []
        for m in sd['marks']:
            marks_list.append({
                'id': m.id,
                'subject': m.subject,
                'marks': m.marks,
                'pass_fail': m.pass_fail
            })
        semester_data_json.append({
            'semester': {
                'id': sd['semester'].id,
                'semester': sd['semester'].semester,
                'attendance': sd['semester'].attendance
            },
            'marks': marks_list,
            'average': sd['average']
        })
    
    return render(request, 'Faculty/viewSemesters.html', {
        'student': student,
        'semester_data': semester_data,
        'semester_data_json': json.dumps(semester_data_json)
    })


# ======================
# CLASS RANKINGS
# ======================
def class_rankings(request):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    faculty = FacultyRegisteredTable.objects.get(id=request.session['faculty'])
    students = StudentTable.objects.filter(faculty=faculty)
    
    rankings = []
    for student in students:
        semesters = SemesterTable.objects.filter(student=student)
        all_marks = []
        for sem in semesters:
            marks = SubjectMarks.objects.filter(semester=sem)
            if marks:
                avg = sum(m.marks for m in marks) / len(marks)
                all_marks.append(avg)
        
        overall = sum(all_marks) / len(all_marks) if all_marks else 0
        rankings.append({
            'student': student,
            'overall': overall,
            'semesters': len(semesters)
        })
    
    rankings.sort(key=lambda x: x['overall'], reverse=True)
    
    return render(request, 'Faculty/classRankings.html', {'rankings': rankings})


# ======================
# UPDATE SEMESTER MARKS
# ======================
def update_semester_marks(request):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    if request.method == 'POST':
        semester_id = request.POST.get('semester_id')
        student_id = request.POST.get('student_id')
        attendance = request.POST.get('attendance')
        
        # Get mark IDs and update
        mark_ids = request.POST.getlist('mark_ids')
        
        for mark_id in mark_ids:
            subject = request.POST.get(f'subject_{mark_id}')
            marks = request.POST.get(f'marks_{mark_id}')
            pass_fail = request.POST.get(f'pass_fail_{mark_id}')
            
            if subject and marks:
                SubjectMarks.objects.filter(id=mark_id).update(
                    subject=subject,
                    marks=float(marks),
                    pass_fail=pass_fail
                )
        
        # Update attendance
        SemesterTable.objects.filter(id=semester_id).update(attendance=attendance)
        
        messages.success(request, 'Marks updated successfully!')
        
    return redirect('view_student_semesters', student_id=request.POST.get('student_id'))


# ======================
# CHANGE PASSWORD
# ======================
def faculty_change_password(request):
    if not request.session.get('faculty'):
        return redirect('facultyLogin')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password == confirm_password:
            faculty = FacultyRegisteredTable.objects.get(id=request.session['faculty'])
            faculty.password = new_password
            faculty.save()
            messages.success(request, 'Password changed successfully!')
        else:
            messages.error(request, 'Passwords do not match!')
        
        return redirect('faculty_home')
    
    return redirect('faculty_home')
