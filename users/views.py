from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from exams.models import Exams, Result
from django.db import transaction
from django.db.models import Avg, Sum, F

def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        username = request.POST['username']
        profile_picture = request.FILES.get('profile_picture')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already taken')
            return redirect('register')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match')
            return redirect('register')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
            return redirect('register')

        else:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        password=password1
                    )
                    
                    
                    if profile_picture:
                        user.profile.profile_picture = profile_picture
                        user.profile.save()

                messages.success(request, 'Successfully registered! Login here.')
                return redirect('signin')

            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
                return redirect('register')

    return render(request, 'register.html', {})

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
                return redirect('exam_list')
            else:
                messages.error(request, 'Incorrect credentials') 
        else:
            messages.error(request, 'Both fields are required.') 

    return render(request, 'login.html', {})

@login_required
def signout(request):
    logout(request)
    return redirect('signin')

def home(request):
    return render(request, 'home.html', {})

@login_required
def profile(request):
    profile = Profile.objects.get(user=request.user)
    exam = Exams.objects.all()

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        education = request.POST.get('education')
        bio = request.POST.get('bio')
        interests = request.POST.get('interests')
        profile_picture = request.FILES.get('profile_picture')

        try:
            
            user = request.user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

           
            profile.phone_number = phone_number
            profile.education = education
            profile.bio = bio
            profile.interests = interests
            
            
            if profile_picture:
                profile.profile_picture = profile_picture
            
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')

        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    
    results = Result.objects.filter(user=request.user)
    total_exams = results.count()
    passed_exams = results.filter(score__gte=F('exam__passing_percentage')).count()
    average_score = results.aggregate(Avg('score'))['score__avg'] or 0


    context = {
        'profile': profile,
        'exam': exam,
        'total_exams': total_exams,
        'passed_exams': passed_exams,
        'average_score': round(average_score, 1),
    }
    
    return render(request, 'profile.html', context)

@login_required
def user_dashboard(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    return render(request, 'user_dashboard.html', {'profile': profile, "exam":exam})

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        
        profile = Profile.objects.get(user=request.user)
        
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('profile')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('profile')
            
        if not any(char.isupper() for char in new_password):
            messages.error(request, 'Password must contain at least one uppercase letter.')
            return redirect('profile')
            
        if not any(char.islower() for char in new_password):
            messages.error(request, 'Password must contain at least one lowercase letter.')
            return redirect('profile')
            
        if not any(char.isdigit() for char in new_password):
            messages.error(request, 'Password must contain at least one number.')
            return redirect('profile')
            
        if not any(char in '!@#$%^&*' for char in new_password):
            messages.error(request, 'Password must contain at least one special character (!@#$%^&*).')
            return redirect('profile')
        
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('profile')
        
        try:
           
            request.user.set_password(new_password)
            request.user.save()
            
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
            
        except Exception as e:
            messages.error(request, 'An error occurred while changing your password. Please try again.')
            return redirect('profile')
    
    return redirect('profile')