from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from .views import user_dashboard, signin, register, home, profile, signout, change_password
urlpatterns = [
    path('user_dashboard/', user_dashboard, name='user_dashboard'),
    path('', home, name='home'),
    path('login/', signin, name='signin'),
    path('register/', register, name='register'),
    path('logout/', signout, name='signout' ), 
    path('profile/', profile, name='profile'),
    path('change-password/', change_password, name='user_change_password'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
