from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import Aircraft, FlightData, RedZone, Alert, Violation, AnalysisSession

def dashboard(request):
    """Vue principale du tableau de bord"""
    context = {
        'aircraft_count': Aircraft.objects.count(),
        'flight_data_count': FlightData.objects.count(),
        'red_zones_count': RedZone.objects.filter(is_active=True).count(),
        'alerts_count': Alert.objects.count(),
        'unprocessed_alerts_count': Alert.objects.filter(is_processed=False).count(),
        'violations_count': Violation.objects.count(),
        'recent_alerts': Alert.objects.select_related('red_zone').order_by('-timestamp')[:5],
        'recent_violations': Violation.objects.select_related('aircraft', 'alert__red_zone').order_by('-alert__timestamp')[:5],
        'recent_sessions': AnalysisSession.objects.order_by('-start_time')[:3],
    }
    return render(request, 'core/dashboard.html', context)

def aircraft_list(request):
    """Liste des aéronefs"""
    aircraft = Aircraft.objects.annotate(
        flight_data_count=Count('flight_data'),
        violations_count=Count('violations')
    ).order_by('aircraft_id')
    
    context = {
        'aircraft_list': aircraft,
    }
    return render(request, 'core/airscraft_list.html', context)

def red_zones_list(request):
    """Liste des zones rouges"""
    zones = RedZone.objects.annotate(
        alerts_count=Count('alerts')
    ).order_by('name')
    
    context = {
        'zones_list': zones,
    }
    return render(request, 'core/red_zones_list.html', context)

def alerts_list(request):
    """Liste des alertes"""
    alerts = Alert.objects.select_related('red_zone').annotate(
        violations_count=Count('violations')
    ).order_by('-timestamp')
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter == 'processed':
        alerts = alerts.filter(is_processed=True)
    elif status_filter == 'unprocessed':
        alerts = alerts.filter(is_processed=False)
    
    zone_filter = request.GET.get('zone')
    if zone_filter:
        alerts = alerts.filter(red_zone_id=zone_filter)
    
    context = {
        'alerts_list': alerts,
        'red_zones': RedZone.objects.filter(is_active=True).order_by('name'),
        'current_status_filter': status_filter,
        'current_zone_filter': zone_filter,
    }
    return render(request, 'core/alerts_list.html', context)

# Create your views here.
