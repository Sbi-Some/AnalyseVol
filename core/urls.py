from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('aircraft/', views.aircraft_list, name='aircraft_list'),
    path('zones/', views.red_zones_list, name='red_zones_list'),
    path('alerts/', views.alerts_list, name='alerts_list'),
]