from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from openpyxl import Workbook
from django.contrib.auth import authenticate, login
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from exams.models import Exams, Question, Result, GradingInterval, StudentProfile, StudentExamAccess, StudentActivity, UserExam
from exams.forms import ExamForm, QuestionForm, GradingIntervalForm
from django.contrib.auth.models import User
from django.forms import formset_factory
from django.db.models import Avg, Count, Q, F
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models.functions import TruncDate
from datetime import timedelta
import csv
import json
from django.db.models.expressions import ExpressionWrapper, F
from users.models import Profile

User = get_user_model()

def is_teacher(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_teacher)
@login_required
def teacher_dashboard(request):
    profile = Profile.objects.get(user=request.user)
    total_exams = Exams.objects.filter(created_by=request.user).count()
    total_students = User.objects.filter(result__exam__created_by=request.user).distinct().count()
    results = Result.objects.filter(exam__created_by=request.user)
    average_score = results.aggregate(Avg('score'))['score__avg'] or 0
    passing_results = results.filter(score__gte=F('exam__passing_percentage')).count()
    total_results = results.count()
    pass_rate = (passing_results / total_results * 100) if total_results > 0 else 0

    end_date = timezone.now()
    start_date = end_date - timedelta(days=6)
    daily_scores = results.filter(
        created_at__range=[start_date, end_date]
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        average_score=Avg('score')
    ).order_by('date')

    performance_labels = [d['date'].strftime('%b %d') for d in daily_scores]
    performance_data = [float(d['average_score']) for d in daily_scores]

    score_distribution = [
        results.filter(score__gte=90).count(),
        results.filter(score__gte=80, score__lt=90).count(),
        results.filter(score__gte=70, score__lt=80).count(),
        results.filter(score__gte=60, score__lt=70).count(),
        results.filter(score__lt=60).count(),
    ]

    recent_exams = Exams.objects.filter(
        created_by=request.user
    ).annotate(
        total_students=Count('result'),
        average_score=Avg('result__score')
    ).order_by('-created_at')[:5]

    top_students = User.objects.filter(
        result__exam__created_by=request.user
    ).annotate(
        exams_taken=Count('result'),
        average_score=Avg('result__score')
    ).order_by('-average_score')[:5]

    context = {
        'profile': profile,
        'total_exams': total_exams,
        'total_students': total_students,
        'average_score': average_score,
        'pass_rate': pass_rate,
        'performance_labels': performance_labels,
        'performance_data': performance_data,
        'score_distribution': score_distribution,
        'recent_exams': recent_exams,
        'top_students': top_students,
    }

    return render(request, 'teacher/dashboard.html', context)

@login_required
@user_passes_test(is_teacher)
def create_exam(request):
    profile = Profile.objects.get(user=request.user)    
    GradingIntervalFormSet = formset_factory(GradingIntervalForm, extra=1, can_delete=True)
    
    if request.method == 'POST':
        form = ExamForm(request.POST)
        formset = GradingIntervalFormSet(request.POST, prefix='intervals')
        
        if form.is_valid() and formset.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            
    
            for interval_form in formset:
                if interval_form.cleaned_data and not interval_form.cleaned_data.get('DELETE', False):
                    interval = interval_form.save(commit=False)
                    interval.exam = exam
                    interval.save()
            
            messages.success(request, 'Exam created successfully!')
            return redirect('add_questions', exam_id=exam.id)
    else:
        form = ExamForm()
        formset = GradingIntervalFormSet(prefix='intervals')
    
    return render(request, 'teacher/create_exam.html', {
        'form': form,
        'formset': formset,
        'profile': profile,
    })

@user_passes_test(is_teacher)
@login_required
def add_questions(request, exam_id):
    profile = Profile.objects.get(user=request.user)
    exam = get_object_or_404(Exams, id=exam_id, created_by=request.user)
    questions_count = Question.objects.filter(exam=exam).count()
    
    if questions_count >= exam.number_of_questions:
        messages.warning(request, f'Maximum number of questions ({exam.number_of_questions}) reached for this exam.')
        return redirect('exam_questions', exam_id=exam.id)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()
            
            questions_remaining = exam.number_of_questions - (questions_count + 1)
            if questions_remaining > 0:
                messages.success(request, f'Question added successfully! {questions_remaining} questions remaining.')
                if 'add_another' in request.POST:
                    return redirect('add_questions', exam_id=exam.id)
            else:
                messages.success(request, 'All questions have been added successfully!')
            
            return redirect('exam_questions', exam_id=exam.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = QuestionForm()
    
    context = {
        'form': form,
        'exam': exam,
        'questions_count': questions_count,
        'questions_remaining': exam.number_of_questions - questions_count,
        'profile': profile,
    }
    return render(request, 'teacher/add_questions.html', context)

@user_passes_test(is_teacher)
def exam_questions(request, exam_id):
    profile = Profile.objects.get(user=request.user)
    exam = get_object_or_404(Exams, id=exam_id, created_by=request.user)
    questions = Question.objects.filter(exam=exam)
    
    context = {
        'exam': exam,
        'questions': questions,
        'profile': profile,
    }
    return render(request, 'teacher/exam_questions.html', context)

@user_passes_test(is_teacher)
@login_required
def edit_question(request, question_id):
    profile = Profile.objects.get(user=request.user)
    question = get_object_or_404(Question, id=question_id, exam__created_by=request.user)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question updated successfully!')
            return redirect('exam_questions', exam_id=question.exam.id)
    else:
        form = QuestionForm(instance=question)
    
    context = {
        'form': form,
        'question': question,
        'exam': question.exam,
        'profile': profile,
    }
    return render(request, 'teacher/edit_question.html', context)

@user_passes_test(is_teacher)
@login_required
def delete_question(request, question_id):
    profile = Profile.objects.get(user=request.user)
    question = get_object_or_404(Question, id=question_id, exam__created_by=request.user)
    exam_id = question.exam.id
    
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted successfully!')
        return redirect('exam_questions', exam_id=exam_id)
    
    return render(request, 'teacher/delete_question.html', {'question': question, 'profile': profile})

@user_passes_test(is_teacher)
@login_required
def exam_results(request, exam_id):
    profile = Profile.objects.get(user=request.user)
    exam = get_object_or_404(Exams, id=exam_id, created_by=request.user)
    results = Result.objects.filter(exam=exam).select_related('user')
    
    total_students = results.count()
    passing_students = results.filter(score__gte=exam.passing_percentage).count()
    failing_students = total_students - passing_students
    
    if total_students > 0:
        average_score = sum(result.score for result in results) / total_students
        passing_rate = (passing_students / total_students) * 100
    else:
        average_score = 0
        passing_rate = 0
    
    context = {
        'exam': exam,
        'results': results,
        'total_students': total_students,
        'passing_students': passing_students,
        'failing_students': failing_students,
        'average_score': round(average_score, 2),
        'passing_rate': round(passing_rate, 2),
        'profile': profile,
    }
    return render(request, 'teacher/exam_results.html', context)

@login_required
@user_passes_test(is_teacher)
def exam_list(request):
    profile = Profile.objects.get(user=request.user)

    exams = Exams.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'teacher/exams_lists.html', {'exams': exams, 'profile': profile})

@login_required
@user_passes_test(is_teacher)
def student_performance(request):
    profile = Profile.objects.get(user=request.user)
    exam_id = request.GET.get('exam_id')
    exams = Exams.objects.filter(created_by=request.user)
    
    if exam_id:
        exam = exams.get(id=exam_id)
    else:
        exam = exams.first()

    if not exam:
        context = {'no_exams': True, 'profile': profile}
        return render(request, 'teacher/student_performance.html', context)

    results = Result.objects.filter(exam=exam).select_related('user')
    
    total_students = results.values('user').distinct().count()
    average_score = results.aggregate(Avg('score'))['score__avg'] or 0
    passing_students = results.filter(score__gte=exam.passing_percentage).values('user').distinct().count()
    passing_rate = (passing_students / total_students * 100) if total_students > 0 else 0

    grading_intervals = GradingInterval.objects.filter(exam=exam).order_by('-min_score')
    
    grade_distribution = []
    for interval in grading_intervals:
        count = results.filter(
            score__gte=interval.min_score,
            score__lte=interval.max_score
        ).count()
        
        grade_distribution.append({
            'grade': interval.grade,
            'description': interval.description or f"{interval.min_score}-{interval.max_score}%",
            'min_score': float(interval.min_score),
            'max_score': float(interval.max_score),
            'count': count
        })

    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_performance = (
        results.filter(created_at__gte=thirty_days_ago)
        .values('created_at__date')
        .annotate(
            average_score=Avg('score'),
            total_attempts=Count('id')
        )
        .order_by('created_at__date')
    )

    performance_labels = [item['created_at__date'].strftime('%b %d') for item in daily_performance]
    performance_data = [float(item['average_score']) for item in daily_performance]

   
    student_results = []
    for result in results.order_by('-created_at')[:50]: 
        grade = 'N/A'
        for interval in grading_intervals:
            if interval.min_score <= result.score <= interval.max_score:
                grade = interval.grade
                break
                
        student_results.append({
            'user': result.user,
            'score': result.score,
            'grade': grade,
            'created_at': result.created_at,
            'passed': result.score >= exam.passing_percentage
        })

    context = {
        'exams': exams,
        'selected_exam': exam,
        'total_students': total_students,
        'average_score': average_score,
        'passing_students': passing_students,
        'passing_rate': passing_rate,
        'grade_distribution': json.dumps(grade_distribution),
        'student_results': student_results,
        'performance_labels': json.dumps(performance_labels),
        'performance_data': json.dumps(performance_data),
        'profile': profile,
    }

    return render(request, 'teacher/student_performance.html', context)


@user_passes_test(is_teacher)
@user_passes_test(is_teacher)
def exam_settings(request):
    profile = Profile.objects.get(user=request.user)
    exams = Exams.objects.filter(created_by=request.user).order_by('-created_at')
    
    for exam in exams:
        total_results = Result.objects.filter(exam=exam).count()
        passing_count = Result.objects.filter(exam=exam, score__gte=exam.passing_percentage).count()
        pass_rate = (passing_count / total_results * 100) if total_results > 0 else 0
        
        
        exam.total_results = total_results
        exam.pass_rate = pass_rate
        
        exam.grade_intervals = exam.grading_intervals.all()

    context = {
        'exams': exams,
        'profile': profile,
    }
    return render(request, 'teacher/analytics.html', context)

@login_required
@user_passes_test(is_teacher)
def generate_report(request):
    
    exams = Exams.objects.filter(created_by=request.user)
    
    if request.method == 'POST':
        exam_id = request.POST.get('exam_id')
        report_type = request.POST.get('report_type', 'detailed')
        
        if exam_id:
            exam = Exams.objects.get(id=exam_id)
            results = Result.objects.filter(exam=exam)
            
           
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="exam_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            writer = csv.writer(response)
            
            if report_type == 'detailed':
               
                writer.writerow(['Student Name', 'Email', 'Score', 'Grade', 'Attempt Number', 'Date Taken', 'Time Taken'])
                
          
                for result in results:
                    
                    grade = 'N/A'
                    grading_intervals = GradingInterval.objects.filter(exam=exam)
                    
                    for interval in grading_intervals:
                        if interval.min_score <= result.score <= interval.max_score:
                            grade = interval.grade
                            break
                    
                    writer.writerow([
                        result.user.get_full_name(),
                        result.user.email,
                        f"{result.score}%",
                        grade,
                        result.attempt_number,
                        result.created_at.strftime("%Y-%m-%d %H:%M"),
                        str(result.time_taken) if result.time_taken else 'N/A'
                    ])
            
            else:  
               
                total_students = results.count()
                avg_score = results.aggregate(Avg('score'))['score__avg'] or 0
                
                
                grade_distribution = {}
                for result in results:
                    grade = 'N/A'
                    for interval in GradingInterval.objects.filter(exam=exam):
                        if interval.min_score <= result.score <= interval.max_score:
                            grade = interval.grade
                            break
                    grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
                
                
                writer.writerow(['Exam Summary Report'])
                writer.writerow(['Exam Title', exam.title])
                writer.writerow(['Total Students', total_students])
                writer.writerow(['Average Score', f"{avg_score:.2f}%"])
                writer.writerow([])
                writer.writerow(['Grade Distribution'])
                for grade, count in grade_distribution.items():
                    writer.writerow([grade, count, f"{(count/total_students)*100:.1f}%"])
            
            return response
    
    context = {
        'exams': exams
    }
    return render(request, 'teacher/exam_setting.html', context)


@login_required
@user_passes_test(is_teacher)
def student_management(request):
    profile = Profile.objects.get(user=request.user)
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    
    students = User.objects.filter(
        Q(result__isnull=False) | 
        Q(userexam__isnull=False)
    ).distinct()
    
    if search_query:
        students = students.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'blocked':
            students = students.filter(student_profile__is_blocked=True)
        elif status_filter == 'active':
            students = students.filter(Q(student_profile__is_blocked=False) | Q(student_profile__isnull=True))

    students = students.annotate(
        exam_count=Count('result', distinct=True),
        avg_score=Avg('result__score')
    )
    
    context = {
        'students': students,
        'search_query': search_query,
        'status_filter': status_filter,
        'profile': profile,
    }
    return render(request, 'teacher/student_management.html', context)

@login_required
@user_passes_test(is_teacher)
def block_student(request, student_id):
    if request.method == 'POST':
        student = get_object_or_404(User, id=student_id)
        reason = request.POST.get('block_reason', '')
        
        
        profile, created = StudentProfile.objects.get_or_create(user=student)
        
       
        profile.is_blocked = True
        profile.blocked_at = timezone.now()
        profile.blocked_by = request.user
        profile.block_reason = reason
        profile.save()
        
        
        StudentActivity.objects.create(
            student=student,
            activity_type='block',
            performed_by=request.user,
            description=f"Blocked by {request.user.get_full_name()}. Reason: {reason}"
        )
        
        messages.success(request, f'Student {student.get_full_name()} has been blocked.')
    return redirect('student_management')

@login_required
@user_passes_test(is_teacher)
def unblock_student(request, student_id):
    if request.method == 'POST':
        student = get_object_or_404(User, id=student_id)
        profile = get_object_or_404(StudentProfile, user=student)
        
       
        profile.is_blocked = False
        profile.blocked_at = None
        profile.blocked_by = None
        profile.block_reason = ''
        profile.save()
        
        
        StudentActivity.objects.create(
            student=student,
            activity_type='unblock',
            performed_by=request.user,
            description=f"Unblocked by {request.user.get_full_name()}"
        )
        
        messages.success(request, f'Student {student.get_full_name()} has been unblocked.')
    return redirect('student_management')

@login_required
@user_passes_test(is_teacher)
def block_exam_access(request, student_id, exam_id):
    if request.method == 'POST':
        student = get_object_or_404(User, id=student_id)
        exam = get_object_or_404(Exams, id=exam_id)
        reason = request.POST.get('block_reason', '')
        
       
        access, created = StudentExamAccess.objects.get_or_create(
            student=student,
            exam=exam,
            defaults={
                'is_blocked': True,
                'blocked_at': timezone.now(),
                'blocked_by': request.user,
                'block_reason': reason
            }
        )
        
        if not created:
            access.is_blocked = True
            access.blocked_at = timezone.now()
            access.blocked_by = request.user
            access.block_reason = reason
            access.save()
        
        
        StudentActivity.objects.create(
            student=student,
            activity_type='exam_block',
            exam=exam,
            performed_by=request.user,
            description=f"Exam access blocked by {request.user.get_full_name()}. Reason: {reason}"
        )
        
        messages.success(request, f'Exam access blocked for {student.get_full_name()}')
    return redirect('student_details', student_id=student_id)

@login_required
@user_passes_test(is_teacher)
def unblock_exam_access(request, student_id, exam_id):
    if request.method == 'POST':
        access = get_object_or_404(StudentExamAccess, 
                                 student_id=student_id, 
                                 exam_id=exam_id)
        
      
        access.is_blocked = False
        access.blocked_at = None
        access.blocked_by = None
        access.block_reason = ''
        access.save()
        
        
        StudentActivity.objects.create(
            student_id=student_id,
            activity_type='exam_unblock',
            exam_id=exam_id,
            performed_by=request.user,
            description=f"Exam access unblocked by {request.user.get_full_name()}"
        )
        
        messages.success(request, 'Exam access has been restored.')
    return redirect('student_details', student_id=student_id)

@login_required
@user_passes_test(is_teacher)
def student_details(request, student_id):
    student = get_object_or_404(User, id=student_id)
    
    
    profile, created = StudentProfile.objects.get_or_create(user=student)
    
    
    results = Result.objects.filter(user=student).select_related('exam')
    
    
    blocked_exams = StudentExamAccess.objects.filter(
        student=student,
        is_blocked=True
    ).select_related('exam')
    
   
    total_exams = results.count()
    avg_score = results.aggregate(Avg('score'))['score__avg'] or 0
    passed_exams = results.filter(score__gte=F('exam__passing_percentage')).count()
    
    context = {
        'student': student,
        'profile': profile,
        'results': results,
        'blocked_exams': blocked_exams,
        'total_exams': total_exams,
        'avg_score': round(avg_score, 2),
        'passed_exams': passed_exams,
        'recent_activities': StudentActivity.objects.filter(student=student).order_by('-created_at')[:10]
    }
    

    return render(request, 'teacher/student_details.html', context)

@login_required
@user_passes_test(is_teacher)
def student_activity_log(request, student_id):
    student = get_object_or_404(User, id=student_id)
    activities = StudentActivity.objects.filter(student=student).order_by('-created_at')
    profile = Profile.objects.get(user=request.user)
    context = {
        'student': student,
        'activities': activities,
        'profile': profile,
    }
    
    return render(request, 'teacher/student_activity_log.html', context)

@login_required
@user_passes_test(is_teacher)
def analytics(request):
    profile = Profile.objects.get(user=request.user)
    exams = Exams.objects.filter(created_by=request.user)
    selected_exam_id = request.GET.get('exam_id')
    date_range = request.GET.get('date_range', '7')
    
    if selected_exam_id:
        selected_exam = get_object_or_404(Exams, id=selected_exam_id, created_by=request.user)
    else:
        selected_exam = exams.first()
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=int(date_range))
    
    results = Result.objects.filter(exam__created_by=request.user)
    if selected_exam:
        results = results.filter(exam=selected_exam)
    
    total_attempts = results.count()
    total_students = results.values('user').distinct().count()
    average_score = results.aggregate(Avg('score'))['score__avg'] or 0
    passing_results = results.filter(score__gte=F('exam__passing_percentage')).count()
    pass_rate = (passing_results / total_attempts * 100) if total_attempts > 0 else 0
    
    daily_data = results.filter(
        created_at__range=[start_date, end_date]
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        attempts=Count('id'),
        avg_score=Avg('score')
    ).order_by('date')
    
    performance_labels = [d['date'].strftime('%Y-%m-%d') for d in daily_data]
    performance_scores = [float(d['avg_score']) if d['avg_score'] else 0 for d in daily_data]
    daily_attempts = [d['attempts'] for d in daily_data]
    
    score_ranges = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
    score_distribution = []
    
    for min_score, max_score in score_ranges:
        count = results.filter(score__gte=min_score, score__lte=max_score).count()
        score_distribution.append({
            'range': f'{min_score}-{max_score}%',
            'count': count,
            'percentage': (count / total_attempts * 100) if total_attempts > 0 else 0
        })
    
    top_students = User.objects.filter(
        result__exam__created_by=request.user
    ).annotate(
        exams_taken=Count('result'),
        average_score=Avg('result__score')
    ).order_by('-average_score')[:10]
    
    context = {
        'exams': exams,
        'selected_exam': selected_exam,
        'date_range': date_range,
        'total_attempts': total_attempts,
        'total_students': total_students,
        'average_score': round(average_score, 2),
        'pass_rate': round(pass_rate, 2),
        'performance_labels': json.dumps(performance_labels),
        'performance_scores': json.dumps(performance_scores),
        'daily_attempts': json.dumps(daily_attempts),
        'score_distribution': score_distribution,
        'top_students': top_students,
        'profile': profile,
    }
    
    return render(request, 'teacher/analytics.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_profile(request):
    profile = Profile.objects.get(user=request.user)
    
    
    total_exams = Exams.objects.filter(created_by=request.user).count()
    total_students = User.objects.filter(result__exam__created_by=request.user).distinct().count()
    results = Result.objects.filter(exam__created_by=request.user)
    total_results = results.count()
    passing_results = results.filter(score__gte=F('exam__passing_percentage')).count()
    average_pass_rate = (passing_results / total_results * 100) if total_results > 0 else 0
    
    if request.method == 'POST':
        
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
        
       
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        
        
        profile.bio = request.POST.get('bio', '')
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('teacher_profile')
    
    context = {
        'profile': profile,
        'total_exams': total_exams,
        'total_students': total_students,
        'average_pass_rate': round(average_pass_rate, 1),
    }
    
    return render(request, 'teacher/profile.html', context)

@login_required
@user_passes_test(is_teacher)
def change_password(request):
    profile = Profile.objects.get(user=request.user)
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
       
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('teacher_profile')
        
        
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return redirect('teacher_profile')
        
     
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('teacher_profile')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        messages.success(request, 'Password changed successfully! Please login again.')
        return redirect('signin')
    
    return redirect('teacher_profile')

@login_required
@user_passes_test(is_teacher)
def add_student(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        try:
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'A user with this email already exists.')
                return redirect('student_management')
            
           
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=User.objects.make_random_password(), 
                is_staff=False,
                is_active=True
            )
            
          
            Profile.objects.create(user=user)
            
            messages.success(request, f'Student {user.get_full_name()} has been added successfully.')
            
        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
        
        return redirect('student_management')
    
    return redirect('student_management')

@login_required
@user_passes_test(is_teacher)
def toggle_student_status(request, student_id):
    if request.method == 'POST':
        try:
            student = User.objects.get(id=student_id, is_staff=False)
            student.is_active = not student.is_active
            student.save()
            
            status = 'activated' if student.is_active else 'deactivated'
            messages.success(request, f'Student {student.get_full_name()} has been {status}.')
            
            return JsonResponse({'status': 'success'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
@user_passes_test(is_teacher)
def reset_student_progress(request, student_id):
    if request.method == 'POST':
        try:
            student = User.objects.get(id=student_id, is_staff=False)
            
            Result.objects.filter(user=student).delete()
            
           
            StudentActivity.objects.filter(user=student).delete()
            StudentExamAccess.objects.filter(student=student).delete()
            
            messages.success(request, f'Progress reset for student {student.get_full_name()}.')
            return JsonResponse({'status': 'success'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
@user_passes_test(is_teacher)
def view_student_details(request, student_id):
    try:
        student = get_object_or_404(User, id=student_id, is_staff=False)
        results = Result.objects.filter(user=student).order_by('-created_at')
        
        context = {
            'student': student,
            'results': results,
            'total_exams': results.count(),
            'average_score': results.aggregate(Avg('score'))['score__avg'] or 0,
        }
        
        return render(request, 'teacher/student_details.html', context)
    except Exception as e:
        messages.error(request, f'Error viewing student details: {str(e)}')
        return redirect('student_management')
def signin(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password) 
            if user is not None:
                login(request, user)
                return redirect('teacher_dashboard')
            else:
                messages.error(request, 'Incorrect credentials')  
        else:
            messages.error(request, 'Both fields are required.') 

    return render(request, 'teacher/login.html', {})
from django.views.decorators.http import require_POST

@login_required
@user_passes_test(is_teacher)
@require_POST
def delete_exam(request, exam_id):
    try:
        exam = Exams.objects.get(id=exam_id)
        exam.delete()
        return JsonResponse({'status': 'success'})
    except Exams.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)