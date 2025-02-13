from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    SUBSCRIPTION_CHOICES = (
        ('free', 'Free'),
        ('premium', 'Premium'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default.jpg')
    subscription_status = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES, default='free')
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    education = models.CharField(max_length=100, blank=True, null=True)  # Free text field for education
    bio = models.TextField(max_length=500, blank=True, null=True)
    interests = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    def is_subscription_active(self):
        if self.subscription_status == 'premium' and self.subscription_end_date:
            return timezone.now() <= self.subscription_end_date
        return False

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
