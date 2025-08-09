"""
URL configuration for vehicule_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from tracking import views
from django.contrib.auth.views import LogoutView
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('map/', views.vehicle_map, name='vehicle_map'),  # Assure-toi que cette route est défin
    path('alerts/', views.alert_list, name='alert_list'),  # Liste des alertes
    path('history/', views.history_list, name='history_list'),  # Historique des positions
    path('users/', views.user_list, name='user_list'),  # Liste des utilisateurs/profils
    path('', views.home, name='home'),  # Accueil
    path('help/', views.help_contact, name='help_contact'),
    path('profil/', views.profile_view, name='profile'),
    path('modifier-email/', views.edit_email, name='edit_email'),
    path('modifier-mot-de-passe/', views.edit_password, name='edit_password'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),  # Redirige vers la page d'accueil après déconnexion
    path('save-zone/', views.save_zone, name='save_zone'),
    path('api/update_position/', views.update_position, name='update_position'),
    path('delete-zone/', views.delete_zone, name='delete_zone'),
    path('api/sms-positions/', views.sms_positions, name='sms_positions'),
    


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)