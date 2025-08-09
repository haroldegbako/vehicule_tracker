
from django.urls import path
from . import views

app_name = 'tracking'

urlpatterns = [
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<int:alert_id>/read/', views.MarkAlertRead.as_view(), name='mark_alert_read'),
    path('alerts/<int:alert_id>/delete/', views.DeleteAlert.as_view(), name='delete_alert'),
]