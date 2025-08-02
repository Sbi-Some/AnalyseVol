from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='dashboard'),
    path('alert/<int:alert_id>/', views.alert_report, name='alert_report'),
    path('alert/<int:alert_id>/pdf/', views.alert_report_pdf, name='alert_report_pdf'),
    path('violations/', views.violations_report, name='violations_report'),
]