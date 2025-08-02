from django.urls import path
from . import views

app_name = 'imports'

urlpatterns = [
    path('', views.import_dashboard, name='dashboard'),
    path('flight-data/', views.import_flight_data, name='flight_data'),
    path('red-zones/', views.import_red_zones, name='red_zones'),
    path('alerts/', views.import_alerts, name='alerts'),
    path('session/<int:session_id>/', views.import_session_detail, name='session_detail'),
]