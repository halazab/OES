from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    subject = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.subject}"

    class Meta:
        verbose_name = 'Teacher Profile'
        verbose_name_plural = 'Teacher Profiles'

class Exams(models.Model):
    title = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    number_of_questions = models.PositiveIntegerField(help_text="Total number of questions")
    total_marks = models.PositiveIntegerField()
    passing_percentage = models.PositiveIntegerField()
    description = models.TextField()
    def __str__(self):
        return self.title

class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice'),
        ('TF', 'True/False'),
        ('SA', 'Short Answer'),
    ]
    exam = models.ForeignKey(Exams, on_delete=models.CASCADE)
    text = models.TextField()
    question_type = models.CharField(max_length=100, choices=QUESTION_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    correct_answer = models.CharField(max_length=200)
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    def __str__(self):
        return self.exam.title
class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    is_correct = models.BooleanField(default=False)
    def __str__(self):
        return self.question.exam.title

class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exams, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    answers = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    attempt_number = models.PositiveIntegerField(default=1)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.DurationField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'exam', 'attempt_number']

    def save(self, *args, **kwargs):
        if not self.pk:  # New result
            # Get the count of previous attempts
            previous_attempts = Result.objects.filter(
                user=self.user,
                exam=self.exam
            ).count()
            self.attempt_number = previous_attempts + 1

        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
            if self.created_at:
                self.time_taken = self.completed_at - self.created_at

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.exam.title} (Attempt {self.attempt_number})"

class ShortAnswer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    correct_answer = models.TextField()
class UserResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['user', 'question']

    def __str__(self):
        return f"{self.question.text} - {self.selected_option}"
class UserExam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exams, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exams, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    email = models.EmailField()
    status = models.CharField(max_length=20)  # e.g., 'pending', 'completed', 'failed'
    created_at = models.DateTimeField(auto_now_add=True)

class Subscription(models.Model):
    SUBSCRIPTION_TYPES = (
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    transaction_reference = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.subscription_type}"

class PaymentTransaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class GradingInterval(models.Model):
    exam = models.ForeignKey(Exams, on_delete=models.CASCADE, related_name='grading_intervals')
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=10)  # e.g., 'A', 'B', 'C', etc.
    description = models.CharField(max_length=100, blank=True)  # e.g., 'Excellent', 'Good', etc.

    class Meta:
        ordering = ['-min_score']
        unique_together = ['exam', 'grade']

    def __str__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score})"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    is_blocked = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blocked_students')
    block_reason = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {'Blocked' if self.is_blocked else 'Active'}"

class StudentExamAccess(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_access')
    exam = models.ForeignKey(Exams, on_delete=models.CASCADE)
    is_blocked = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blocked_exam_access')
    block_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'exam']
        verbose_name_plural = 'Student Exam Access'

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.exam.title}"

class StudentActivity(models.Model):
    ACTIVITY_TYPES = (
        ('block', 'Blocked'),
        ('unblock', 'Unblocked'),
        ('exam_block', 'Exam Access Blocked'),
        ('exam_unblock', 'Exam Access Unblocked'),
        ('exam_attempt', 'Exam Attempted'),
        ('exam_complete', 'Exam Completed'),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    exam = models.ForeignKey(Exams, on_delete=models.SET_NULL, null=True, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='performed_activities')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Student Activities'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.get_activity_type_display()}"
class SupportTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exams, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject}"
    

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)  # e.g., 'Basic', 'Premium', 'Enterprise'
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField(help_text="Duration in days")
    description = models.TextField()
    features = models.JSONField(help_text="List of features included in this plan")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.price} ETB"

    class Meta:
        ordering = ['price']

class StudentActivity(models.Model):
    ACTIVITY_TYPES = (
        ('block', 'Blocked'),
        ('unblock', 'Unblocked'),
        ('exam_block', 'Exam Access Blocked'),
        ('exam_unblock', 'Exam Access Unblocked'),
        ('exam_attempt', 'Exam Attempted'),
        ('exam_complete', 'Exam Completed'),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    exam = models.ForeignKey(Exams, on_delete=models.SET_NULL, null=True, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='performed_activities')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Student Activities'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.get_activity_type_display()}"
    
class SupportTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exams, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject}"

class TicketResponse(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Response to Ticket #{self.ticket.id}"

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='attachments')
    response = models.ForeignKey(TicketResponse, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    file = models.FileField(upload_to='support_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for Ticket #{self.ticket.id}"
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    is_blocked = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blocked_students')
    block_reason = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {'Blocked' if self.is_blocked else 'Active'}"



