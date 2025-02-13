from django.shortcuts import render, redirect
from .models import Exams, Question, Option, Result, ShortAnswer, GradingInterval
from .forms import ExamForm, QuestionForm, OptionForm, ShortAnswerForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from users.models import Profile
from .models import UserResponse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from .models import TeacherProfile
import json
from .models import StudentProfile
from django.http import HttpResponse
from .models import SubscriptionPlan, StudentActivity, SupportTicket, TicketResponse, TicketAttachment
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from .models import SupportTicket
from django.contrib.auth.decorators import user_passes_test
from .models import Transaction, UserExam, Subscription, PaymentTransaction
import requests
from datetime import datetime, timedelta
import uuid
from django.utils import timezone
from django.contrib import messages
from django.db.models import Avg, Max, Count, F
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.db import models

def is_admin(user):
    return user.is_staff or user.is_superuser
@user_passes_test(is_admin)
def subscription_plan_detail(request, plan_id):
    """
    API endpoint to get subscription plan details
    """
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    return JsonResponse({
        'id': plan.id,
        'name': plan.name,
        'price': str(plan.price),
        'duration': plan.duration,
        'description': plan.description,
        'features': plan.features,
        'is_active': plan.is_active
    })
@login_required
def payment_failed(request):
    """
    Handle failed payment redirect
    """
    messages.error(request, 'Payment failed. Please try again.')
    return render(request, 'payment_failed.html', {
        'title': 'Payment Failed',
        'message': 'Your payment could not be processed. Please try again or contact support if the problem persists.'
    })
@staff_member_required
def get_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    return JsonResponse({
        'id': subscription.id,
        'user_id': subscription.user.id,
        'subscription_type': subscription.subscription_type,
        'end_date': subscription.end_date.strftime('%Y-%m-%d'),
        'price': str(subscription.price),
        'auto_renew': subscription.auto_renew
    })

@user_passes_test(is_admin)
def manage_subscription_plans(request):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        if plan_id:
            plan = get_object_or_404(SubscriptionPlan, id=plan_id)
        else:
            plan = SubscriptionPlan()
        
        plan.name = request.POST.get('name')
        plan.price = request.POST.get('price')
        plan.duration = request.POST.get('duration')
        plan.description = request.POST.get('description')
        plan.features = request.POST.getlist('features[]')
        plan.is_active = request.POST.get('is_active') == 'on'
        plan.save()
        
        messages.success(request, 'Subscription plan saved successfully!')
        return redirect('manage_subscription_plans')
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    plans = SubscriptionPlan.objects.all()
    return render(request, 'admin/manage_subscription_plans.html', {
        'plans': plans,
        'exam': exam,
        'profile': profile
    })

@staff_member_required
@require_http_methods(["POST"])
def toggle_subscription_renew(request):
    try:
        data = json.loads(request.body)
        subscription = get_object_or_404(Subscription, id=data.get('subscription_id'))
        subscription.auto_renew = not subscription.auto_renew
        subscription.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
def student_dashboard(request):
    exams = Exams.objects.all()
    return render(request, 'student_dashboard.html', {'exams': exams})

def is_admin(user):
    return user.is_staff or user.is_superuser
@user_passes_test(is_admin)
def subscription_management(request):
    subscription_plans = SubscriptionPlan.objects.filter(is_active=True)
    subscriptions = Subscription.objects.select_related('user').all()
    users = User.objects.filter(is_staff=False)
    
    for plan in subscription_plans:
        plan.subscribers_count = Subscription.objects.filter(
            subscription_type=plan.name.lower(),
            is_active=True
        ).count()
    
    context = {
        'subscription_plans': subscription_plans,
        'subscriptions': subscriptions,
        'users': users,
    }
    return render(request, 'subscription_management.html', context)
@user_passes_test(is_admin)
def save_subscription(request):
    if request.method == 'POST':
        try:
            user_id = request.POST['user']
            subscription_type = request.POST['subscription_type']
            duration = int(request.POST['duration'])
            
            amounts = {
                'basic': 9.99,
                'premium': 19.99,
                'enterprise': 49.99
            }
            
            amount = amounts[subscription_type] * duration
            end_date = timezone.now() + timedelta(days=30*duration)
            
            subscription = Subscription.objects.create(
                user_id=user_id,
                subscription_type=subscription_type,
                amount=amount,
                end_date=end_date,
                is_active=True,
                transaction_reference=f"SUB-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Subscription created successfully'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })
@staff_member_required
@require_http_methods(["POST"])
def delete_user(request):
    try:
        data = json.loads(request.body)
        user = get_object_or_404(User, id=data.get('user_id'))
        if user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Cannot delete superuser'})
        user.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@user_passes_test(is_admin)
def delete_exam(request):
    if request.method == 'POST':
        exam_id = request.POST.get('exam_id')
        try:
            exam = Exams.objects.get(id=exam_id)
            exam.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Exam deleted successfully'
            })
        except Exams.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Exam not found'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def transaction_history(request):
    transactions = PaymentTransaction.objects.all().order_by('-created_at')
    
    paginator = Paginator(transactions, 10) 
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    total_amount = PaymentTransaction.objects.filter(status='success').aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    context = {
        'page_obj': page_obj,
        'total_amount': total_amount,
    }
    
    return render(request, 'transaction_history.html', context)
@user_passes_test(is_admin)
def block_student(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = StudentProfile.objects.get(user_id=student_id)
            student.is_blocked = True
            student.blocked_at = timezone.now()
            student.blocked_by = request.user
            student.save()
            
            StudentActivity.objects.create(
                student_id=student_id,
                activity_type='block',
                performed_by=request.user,
                description=f'Student blocked by {request.user.get_full_name()}'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Student blocked successfully'
            })
        except StudentProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student not found'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })
@staff_member_required
@require_http_methods(["POST"])
def cancel_subscription(request):
    try:
        data = json.loads(request.body)
        subscription = get_object_or_404(Subscription, id=data.get('subscription_id'))
        subscription.status = 'cancelled'
        subscription.auto_renew = False
        subscription.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
@user_passes_test(is_admin)
def add_student(request):
    if request.method == 'POST':
        try:
            user = User.objects.create_user(
                username=request.POST['email'],
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name']
            )
            StudentProfile.objects.create(user=user)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Student added successfully'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }) 
@user_passes_test(is_admin)
def student_details(request):
    student_id = request.GET.get('id')
    try:
        student = StudentProfile.objects.select_related('user').get(user_id=student_id)
        results = Result.objects.filter(user=student.user).select_related('exam')
        activities = StudentActivity.objects.filter(student=student.user).select_related('exam')
        
        context = {
            'student': student,
            'results': results,
            'activities': activities
        }
        return render(request, 'dashboard/partials/student_details.html', context)
    except StudentProfile.DoesNotExist:
        return HttpResponse('Student not found', status=404)

@user_passes_test(is_admin)
def unblock_student(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = StudentProfile.objects.get(user_id=student_id)
            student.is_blocked = False
            student.blocked_at = None
            student.blocked_by = None
            student.block_reason = ''
            student.save()
            
            StudentActivity.objects.create(
                student_id=student_id,
                activity_type='unblock',
                performed_by=request.user,
                description=f'Student unblocked by {request.user.get_full_name()}'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Student unblocked successfully'
            })
        except StudentProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student not found'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


@staff_member_required
@require_http_methods(["POST"])
def save_subscription(request):
    try:
        subscription_id = request.POST.get('subscription_id')
        if subscription_id:
            subscription = get_object_or_404(Subscription, id=subscription_id)
        else:
            subscription = Subscription()
        
        subscription.user = get_object_or_404(User, id=request.POST.get('user_id'))
        subscription.subscription_type = request.POST.get('subscription_type')
        subscription.end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d')
        subscription.price = request.POST.get('price')
        subscription.auto_renew = request.POST.get('auto_renew') == 'on'
        subscription.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def view_results(request, exam_id):
    results = Result.objects.filter(exam_id=exam_id)
    return render(request, 'view_results.html', {'results': results})
def auto_grade(result):
    score = 0
    answers = result.answers 
    for question in Question.objects.filter(exam=result.exam):
        if question.question_type == 'MCQ':
            correct_option = Option.objects.filter(question=question, is_correct=True).first()
            if answers.get(str(question.id)) == correct_option.id:
                score += 1
        elif question.question_type == 'TF':
            pass
        elif question.question_type == 'SA':
            pass
    result.score = score
    result.save()
@login_required
def student_analytics(request):
    results = Result.objects.filter(user=request.user)
    data = {
        'exams': [result.exam.title for result in results],
        'scores': [result.score for result in results],
    }
    return render(request, 'student_analytics.html', {'data': data})
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    questions = exam.question_set.all()
    return render(request, 'exam_detail.html', {'exam': exam, 'questions': questions})
def exam_list(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    exams = Exams.objects.all()  
    return render(request, 'exam_list.html', {'exams': exams, 'profile': profile, "exam":exam})  # Render the exam list template
def exam_questions(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    questions = Question.objects.filter(exam=exam)

    context = {
        'exam': exam,
        'questions': questions,
    }
    
    return render(request, 'exam_questions.html', context)

@login_required
def take_exam(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    questions = Question.objects.filter(exam=exam)
    
    user_exam, created = UserExam.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={'completed': False}
    )

    if user_exam.completed:
        messages.warning(request, 'You have already completed this exam.')
        return redirect('exam_list')

    if request.method == 'POST':
        try:
            answers = {}
            correct_answers = 0
            total_questions = questions.count()

            for question in questions:
                answer_key = f'question_{question.id}'
                if answer_key in request.POST:
                    selected_option = request.POST[answer_key].strip()
                    answers[str(question.id)] = selected_option

                    UserResponse.objects.create(
                        user=request.user, 
                        question=question,
                        selected_option=selected_option
                    )

                    
                    if selected_option.lower() == question.correct_answer.strip().lower():
                        correct_answers += 1

           
            percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            percentage = round(percentage, 2) 

            
            Result.objects.create(
                user=request.user,
                exam=exam,
                score=percentage,  
                answers=json.dumps(answers)
            )

            
            user_exam.completed = True
            user_exam.save()

            
            passed = percentage >= exam.passing_percentage
            
            context = {
                'exam': exam,
                'score': percentage,  
                'total_questions': total_questions,
                'correct_answers': correct_answers,
                'percentage': percentage,
                'passed': passed
            }
            
            messages.success(request, 'Exam completed successfully!')
            return redirect('exam_result', exam_id=exam.id)

        except Exception as e:
            messages.error(request, f'Error submitting exam: {str(e)}')
            return redirect('take_exam', exam_id=exam_id)

    context = {
        'exam': exam,
        'questions': questions,
    }
    return render(request, 'take_exam.html', context)

def exam_results(request, exam_id):
    profile = Profile.objects.get(user=request.user)
    exam = get_object_or_404(Exams, id=exam_id)
    questions = Question.objects.filter(exam=exam)
    
    try:
        result = Result.objects.get(user=request.user, exam=exam)
    except Result.DoesNotExist:
        result = None

    responses = []
    correct_answers = 0
    
    for question in questions:
        try:
            response = UserResponse.objects.get(
                question=question,
                user=request.user  
            )
            
            is_correct = response.selected_option.strip().lower() == question.correct_answer.strip().lower()
            if is_correct:
                correct_answers += 1
            
            responses.append({
                'question': question,
                'selected_option': response.selected_option,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct
            })
        except UserResponse.DoesNotExist:
            continue

    total_questions = questions.count()
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    passed = score >= exam.passing_percentage

    context = {
        'exam': exam,
        'responses': responses,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'score': round(score, 2),
        'passed': passed,
        'profile': profile,
        'result': result
    }
    
    return render(request, 'exam_results.html', context)
@login_required
def payment_view(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)

    if not exam.is_premium:
        return redirect('exam_detail', exam_id=exam.id) 

    if request.method == 'POST':
       
        amount = int(exam.price * 100)  
        email = request.user.email

        
        transaction = Transaction.objects.create(
            user=request.user,
            exam=exam,
            amount=exam.price,
            currency='ETB', 
            email=email,
            status='pending'
        )

        
        headers = {
            'Authorization': 'Bearer YOUR_SECRET_KEY',
        }
        
        
        payment_data = {
            "amount": amount,
            "currency": "ETB",
            "email": email,
            "transaction_id": str(transaction.id),
            "callback_url": "http://127.0.0.1:8000/payment/callback/"
        }

        response = requests.post('https://api.chapa.co/v1/transaction/initialize', headers=headers, json=payment_data)

        if response.status_code == 200:
            payment_url = response.json().get('data').get('url')
            return redirect(payment_url) 
        else:
            
            return render(request, 'payment_error.html', {'error': response.json()})

    return render(request, 'payment.html', {'exam': exam})

def get_chapa_secret_key():
    return settings.CHAPA_SECRET_KEY

@login_required
def initialize_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subscription_type = data.get('subscription_type')
            amount = data.get('amount')
            
          
            tx_ref = str(uuid.uuid4())
            
          
            headers = {
                "Authorization": f"Bearer {get_chapa_secret_key()}",
                "Content-Type": "application/json"
            }
            
           
            payload = {
                "amount": str(amount),
                "currency": "ETB",
                "email": request.user.email,
                "first_name": request.user.first_name or "Customer",
                "last_name": request.user.last_name or "Name",
                "tx_ref": tx_ref,
                "callback_url": f"{settings.BASE_URL}/payment/verify/{tx_ref}/",
                "return_url": f"{settings.BASE_URL}/payment/success/",
                "customization[title]": f"Online Exam {subscription_type} Subscription",
                "customization[description]": f"Payment for {subscription_type} subscription"
            }
            
            response = requests.post(
                "https://api.chapa.co/v1/transaction/initialize",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
               
                end_date = datetime.now() + timedelta(days=30)
                subscription = Subscription.objects.create(
                    user=request.user,
                    subscription_type=subscription_type,
                    amount=amount,
                    end_date=end_date,
                    transaction_reference=tx_ref
                )
                
                
                PaymentTransaction.objects.create(
                    user=request.user,
                    subscription=subscription,
                    amount=amount,
                    transaction_reference=tx_ref
                )
                
                return JsonResponse({
                    'status': 'success',
                    'checkout_url': response_data['data']['checkout_url']
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to initialize payment'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@csrf_exempt
def verify_payment(request, tx_ref):
    try:
        headers = {
            "Authorization": f"Bearer {get_chapa_secret_key()}",
        }
        
        response = requests.get(
            f"https://api.chapa.co/v1/transaction/verify/{tx_ref}",
            headers=headers
        )
        
        if response.status_code == 200:
            verification_data = response.json()
            
            if verification_data.get('status') == 'success':
                try:
                   
                    transaction = PaymentTransaction.objects.get(transaction_reference=tx_ref)
                    subscription = transaction.subscription
                    
                   
                    transaction.status = 'success'
                    transaction.save()
                    
                    
                    subscription.is_active = True
                    subscription.save()
                    
                    
                    profile = Profile.objects.get(user=transaction.user)
                    profile.subscription_status = 'premium'
                    profile.subscription_end_date = subscription.end_date
                    profile.save()
                    
                  
                    return redirect('payment_success')  
                    
                except Exception as e:
                    print(f"Error in payment verification: {str(e)}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Invalid transaction: {str(e)}'
                    })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Payment verification failed'
        })
        
    except Exception as e:
        print(f"Exception in verify_payment: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def payment_success(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    return render(request, 'exams/payment_success.html', {'exam': exam, 'profile': profile})

@login_required
def subscription_status(request):
    try:
        active_subscription = Subscription.objects.get(
            user=request.user,
            is_active=True,
            end_date__gt=datetime.now()
        )
        return JsonResponse({
            'status': 'success',
            'has_subscription': True,
            'subscription_type': active_subscription.subscription_type,
            'end_date': active_subscription.end_date.strftime('%Y-%m-%d')
        })
    except Subscription.DoesNotExist:
        return JsonResponse({
            'status': 'success',
            'has_subscription': False
        })

def recent_exams(request):
   
    recent_date = timezone.now() - timedelta(days=30)
    recent_exams = Exams.objects.filter(
        created_at__gte=recent_date
    ).order_by('-created_at')[:5]  
    
    profile = Profile.objects.get(user=request.user)
    
    context = {
        'recent_exams': recent_exams,
        'profile': profile,
    }
    return render(request, 'exams/recent_exams.html', context)

def get_grade(score, exam):
    interval = GradingInterval.objects.filter(
        exam=exam,
        min_score__lte=score,
        max_score__gte=score
    ).first()
    return interval if interval else None

@login_required
def exam_result(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    
    try:
       
        result = Result.objects.filter(
            user=request.user,
            exam=exam
        ).latest('created_at') 
    except Result.DoesNotExist:
        messages.error(request, 'No result found for this exam.')
        return redirect('exam_list')
    
    questions = Question.objects.filter(exam=exam)
    responses = []
    correct_answers = 0
    
    for question in questions:
        try:
            response = UserResponse.objects.filter(
                question=question,
                user=request.user
            ).latest('created_at')
            
            is_correct = response.selected_option.strip().lower() == question.correct_answer.strip().lower()
            if is_correct:
                correct_answers += 1
            
            responses.append({
                'question': question,
                'selected_option': response.selected_option,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct
            })
        except UserResponse.DoesNotExist:
            continue

    total_questions = questions.count()
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    passed = score >= exam.passing_percentage

   
    grade_interval = get_grade(score, exam)
    
    context = {
        'exam': exam,
        'result': result,
        'responses': responses,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'score': round(score, 2),
        'passed': passed,
        'grade': grade_interval.grade if grade_interval else None,
        'grade_description': grade_interval.description if grade_interval else None,
    }
    
    return render(request, 'exam_results.html', context)

@login_required
def performance_view(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)

    user_results = Result.objects.filter(user=request.user).select_related('exam')
    
  
    total_exams = user_results.count()
    exams_passed = user_results.filter(score__gte=F('exam__passing_percentage')).count()
    average_score = user_results.aggregate(Avg('score'))['score__avg'] or 0
    
    
    recent_results = user_results.order_by('-id')[:5]
    
    premium_performance = {
        'total_exams': user_results.filter(exam__is_premium=True).count(),
        'average_score': user_results.filter(exam__is_premium=True).aggregate(Avg('score'))['score__avg'] or 0,
        'highest_score': user_results.filter(exam__is_premium=True).aggregate(Max('score'))['score__max'] or 0,
    }
    
    free_performance = {
        'total_exams': user_results.filter(exam__is_premium=False).count(),
        'average_score': user_results.filter(exam__is_premium=False).aggregate(Avg('score'))['score__avg'] or 0,
        'highest_score': user_results.filter(exam__is_premium=False).aggregate(Max('score'))['score__max'] or 0,
    }

    context = {
        'total_exams': total_exams,
        'exams_passed': exams_passed,
        'average_score': average_score,
        'recent_results': recent_results,
        'premium_performance': premium_performance,
        'free_performance': free_performance,
        'exam': exam,
        'profile': profile,
    }
    
    return render(request, 'performance.html', context)


@login_required
def support_management(request):
    if not request.user.is_staff:
        return redirect('student_support')
        
    tickets = SupportTicket.objects.all().order_by('-created_at')
    context = {
        'open_tickets_count': tickets.filter(status='open').count(),
        'pending_tickets_count': tickets.filter(status='pending').count(),
        'resolved_tickets_count': tickets.filter(status='resolved').count(),
        'tickets': tickets,
    }
    return render(request, 'support_management.html', context)



@login_required
def create_ticket(request):

    
    if request.method == 'POST':
        try:
           
           
            
          
            subject = request.POST.get('subject')
            message = request.POST.get('message')
            priority = request.POST.get('priority', 'low')
            
            if not subject or not message:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Subject and message are required'
                })
            
           
            ticket = SupportTicket(
                user=request.user,
                subject=subject,
                message=message,
                priority=priority,
                status='open'
            )
            ticket.save()
            
            
            
            files = request.FILES.getlist('attachments')
            for file in files:
                attachment = TicketAttachment(
                    ticket=ticket,
                    file=file
                )
                attachment.save()            
            messages.success(request, 'Support ticket created successfully!')
            
            return JsonResponse({
                'status': 'success',
                'message': 'Ticket created successfully',
                'ticket_id': ticket.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error creating ticket: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
def view_ticket(request, ticket_id):
    if request.user.is_staff:
        return admin_view_ticket(request, ticket_id)
    else:
        return student_view_ticket(request, ticket_id)



@login_required
def cancel_ticket(request):
    if request.method == 'POST':
        try:
            ticket_id = request.POST.get('ticket_id')
            ticket = get_object_or_404(SupportTicket, id=ticket_id)
            
            if not (request.user.is_staff or ticket.user == request.user):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'})
            
            ticket.status = 'resolved'
            ticket.save()
            
            messages.success(request, f'Ticket #{ticket.id} has been cancelled.')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def student_support(request):
    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
 
    exams = Exams.objects.all().order_by('title')
    profile = Profile.objects.get(user=request.user)
    exam = Exams.objects.all()
    if request.method == 'POST':
        try:
            
            exam_id = request.POST.get('exam')
            exam = None
            if exam_id:
                exam = get_object_or_404(Exams, id=exam_id)
                
            ticket = SupportTicket.objects.create(
                user=request.user,
                exam=exam,  
                subject=request.POST.get('subject'),
                message=request.POST.get('message'),
                priority=request.POST.get('priority', 'low'),
                status='open'
            )
            
            if 'attachments' in request.FILES:
                for file in request.FILES.getlist('attachments'):
                    TicketAttachment.objects.create(
                        ticket=ticket,
                        file=file
                    )
            
            messages.success(request, 'Ticket created successfully!')
            return redirect('student_support')
        except Exception as e:
            messages.error(request, f'Error creating ticket: {str(e)}')
    
    return render(request, 'student/support.html', {
        'tickets': tickets,
        'exams': exams,
        'profile': profile,
        'exam': exam
    })


@login_required
def student_view_ticket(request, ticket_id):
    profile = Profile.objects.get(user=request.user)
    exam = Exams.objects.all()
    ticket = get_object_or_404(SupportTicket, id=ticket_id, user=request.user)
    responses = ticket.responses.select_related('user').prefetch_related('attachments').all()
    return render(request, 'student/ticket_detail.html', {
        'ticket': ticket,
        'responses': responses,
        'profile': profile,
        'exam': exam
    })


@user_passes_test(is_admin)
def admin_support(request):
    tickets = SupportTicket.objects.all().order_by('-created_at')
    context = {
        'tickets': tickets,
        'open_tickets_count': tickets.filter(status='open').count(),
        'pending_tickets_count': tickets.filter(status='pending').count(),
        'resolved_tickets_count': tickets.filter(status='resolved').count(),
    }
    return render(request, 'admin/support_management.html', context)

@user_passes_test(is_admin)
def admin_view_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    responses = ticket.responses.select_related('user').prefetch_related('attachments').all()
    return render(request, 'admin/ticket_detail.html', {
        'ticket': ticket,
        'responses': responses
    })

@login_required
def respond_ticket(request):
    if request.method == 'POST':
        try:
            ticket_id = request.POST.get('ticket_id')
            ticket = get_object_or_404(SupportTicket, id=ticket_id)
            
            
            if not (request.user.is_staff or ticket.user == request.user):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'})
            
            response = TicketResponse.objects.create(
                ticket=ticket,
                user=request.user,
                message=request.POST.get('message')
            )
            
          
            if 'attachments' in request.FILES:
                for file in request.FILES.getlist('attachments'):
                    TicketAttachment.objects.create(
                        ticket=ticket,
                        response=response,
                        file=file
                    )
            
           
            if request.user.is_staff:
                ticket.status = 'pending'
                ticket.save()
            
            messages.success(request, 'Response added successfully!')
            
            if request.user.is_staff:
                return redirect('admin_view_ticket', ticket_id=ticket.id)
            else:
                return redirect('student_view_ticket', ticket_id=ticket.id)
            
        except Exception as e:
            messages.error(request, f'Error adding response: {str(e)}')
            return redirect('student_support')
    
    return redirect('student_support')

@user_passes_test(is_admin)
def resolve_ticket(request):
    if request.method == 'POST':
        try:
            ticket_id = request.POST.get('ticket_id')
            ticket = get_object_or_404(SupportTicket, id=ticket_id)
            ticket.status = 'resolved'
            ticket.save()
            
            messages.success(request, f'Ticket #{ticket.id} has been resolved.')
            return redirect('admin_view_ticket', ticket_id=ticket.id)
        except Exception as e:
            messages.error(request, f'Error resolving ticket: {str(e)}')
    
    return redirect('admin_support')









from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
import json

@staff_member_required
def exam_management(request):
    exams = Exams.objects.all().order_by('-created_at')
    return render(request, 'admin/exam_management.html', {'exams': exams})

@staff_member_required
def get_exam(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    return JsonResponse({
        'id': exam.id,
        'title': exam.title,
        'description': exam.description,
        'duration': exam.duration,
        'is_premium': exam.is_premium
    })

@staff_member_required
@require_http_methods(["POST"])
def save_exam(request):
    try:
        exam_id = request.POST.get('examId')
        if exam_id:
            exam = get_object_or_404(Exams, id=exam_id)
        else:
            exam = Exams()
        
        exam.title = request.POST.get('title')
        exam.description = request.POST.get('description')
        exam.duration = request.POST.get('duration')
        exam.is_premium = request.POST.get('is_premium') == 'on'
        exam.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_http_methods(["POST"])
def add_question(request):
    try:
        exam_id = request.POST.get('examId')
        exam = get_object_or_404(Exams, id=exam_id)
        
        question = Question.objects.create(
            exam=exam,
            text=request.POST.get('questionText')
        )
        
        options = json.loads(request.POST.get('options'))
        for option in options:
            Option.objects.create(
                question=question,
                text=option['text'],
                is_correct=option['is_correct']
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
def get_questions(request):
    try:
        exam_id = request.GET.get('exam_id')
        questions = Question.objects.filter(exam_id=exam_id)
        questions_data = []
        
        for question in questions:
            options = [{'text': opt.text, 'is_correct': opt.is_correct} 
                      for opt in question.option_set.all()]
            questions_data.append({
                'id': question.id,
                'text': question.text,
                'options': options
            })
        
        return JsonResponse(questions_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@staff_member_required
@require_http_methods(["POST"])
def delete_question(request):
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        question = get_object_or_404(Question, id=question_id)
        question.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})







from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

User = get_user_model()

@staff_member_required
def student_management(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin/student_management.html', {'users': users})

@staff_member_required
def get_user_details(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return JsonResponse({
        'username': user.username,
        'full_name': user.get_full_name(),
        'email': user.email,
        'date_joined': user.date_joined.strftime('%B %d, %Y'),
        'last_login': user.last_login.strftime('%B %d, %Y %H:%M') if user.last_login else 'Never',
        'is_active': user.is_active
    })

@staff_member_required
@require_http_methods(["POST"])
def toggle_user_status(request):
    try:
        data = json.loads(request.body)
        user = get_object_or_404(User, id=data.get('user_id'))
        user.is_active = data.get('is_active', False)
        user.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_http_methods(["POST"])
def delete_user(request):
    try:
        data = json.loads(request.body)
        user = get_object_or_404(User, id=data.get('user_id'))
        if user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Cannot delete superuser'})
        user.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    






User = get_user_model()

@staff_member_required
def teacher_management(request):
    
    teachers_group = Group.objects.get_or_create(name='Teachers')[0]
    teachers = User.objects.filter(groups=teachers_group).order_by('-date_joined')
    return render(request, 'admin/teacher_management.html', {'teachers': teachers})

@staff_member_required
def get_teacher_details(request, teacher_id):
    teacher = get_object_or_404(User, id=teacher_id)
    try:
        subject = teacher.teacher_profile.subject
    except TeacherProfile.DoesNotExist:
        subject = 'Not specified'
        
    return JsonResponse({
        'username': teacher.username,
        'full_name': teacher.get_full_name(),
        'email': teacher.email,
        'subject': subject,
        'date_joined': teacher.date_joined.strftime('%B %d, %Y'),
        'last_login': teacher.last_login.strftime('%B %d, %Y %H:%M') if teacher.last_login else 'Never',
        'is_active': teacher.is_active
    })

@staff_member_required
@require_http_methods(["POST"])
def add_teacher(request):
    try:
        
        user = User.objects.create_user(
            username=request.POST['username'],
            email=request.POST['email'],
            password=request.POST['password'],
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name']
        )
        
     
        teachers_group = Group.objects.get_or_create(name='Teachers')[0]
        user.groups.add(teachers_group)
        
       
        TeacherProfile.objects.create(
            user=user,
            subject=request.POST.get('subject', '')
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_http_methods(["POST"])
def toggle_teacher_status(request):
    try:
        data = json.loads(request.body)
        teacher = get_object_or_404(User, id=data.get('teacher_id'))
        teacher.is_active = data.get('is_active', False)
        teacher.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_http_methods(["POST"])
def delete_teacher(request):
    try:
        data = json.loads(request.body)
        teacher = get_object_or_404(User, id=data.get('teacher_id'))
        teacher.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
from .models import SubscriptionPlan    
def subscription_plans(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    plans = SubscriptionPlan.objects.all()
    return render(request, 'exams/subscription_plans.html', {'plans': plans, 'profile': profile, "exam":exam})




