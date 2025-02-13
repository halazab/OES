from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import (
    Exams, Question, Option, Result, ShortAnswer, 
    Subscription, PaymentTransaction, UserResponse, UserExam, Transaction
)

User = get_user_model()

admin.site.unregister(User)
admin.site.register(Transaction)


def create_teacher_group():
    teacher_group, created = Group.objects.get_or_create(name='Teacher')
    if created:
        
        pass
    return teacher_group

class CustomUserCreationForm(UserCreationForm):
    is_teacher_checkbox = forms.BooleanField(required=False, label='Is Teacher')
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

class CustomUserChangeForm(forms.ModelForm):
    is_teacher_checkbox = forms.BooleanField(required=False, label='Is Teacher')
    
    class Meta:
        model = User
        fields = '__all__'

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_teacher', 'is_active')
    list_filter = ('is_staff', 'groups', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Teacher Status', {'fields': ('is_teacher_checkbox',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_teacher_checkbox', 'is_active')}
        ),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj: 
            form.base_fields['is_teacher_checkbox'].initial = obj.groups.filter(name='Teacher').exists()
        return form

    def save_model(self, request, obj, form, change):
        is_teacher = form.cleaned_data.get('is_teacher_checkbox', False)
        
        
        super().save_model(request, obj, form, change)
        
        teacher_group = create_teacher_group()
        
        if is_teacher:
            obj.groups.add(teacher_group)
            obj.is_staff = True
        else:
            obj.groups.remove(teacher_group)
            if not obj.is_superuser:  
                obj.is_staff = False
        
        obj.save()

    def is_teacher(self, obj):
        return obj.groups.filter(name='Teacher').exists()
    is_teacher.boolean = True
    is_teacher.short_description = 'Teacher'

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_type', 'amount', 'is_active', 'start_date', 'end_date')
    list_filter = ('subscription_type', 'is_active')
    search_fields = ('user__username', 'user__email', 'transaction_reference')
    date_hierarchy = 'start_date'

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at', 'transaction_reference')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'transaction_reference')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(Exams)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(Result)
admin.site.register(ShortAnswer)
admin.site.register(UserResponse)
admin.site.register(UserExam)

admin.site.register(User, CustomUserAdmin)