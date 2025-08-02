from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.analysis_dashboard, name='dashboard'),
    path('run/', views.run_analysis, name='run_analysis'),
    path('session/<int:session_id>/', views.analysis_session_detail, name='session_detail'),
]