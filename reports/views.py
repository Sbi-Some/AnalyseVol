from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q
from datetime import datetime, timedelta
from core.models import Alert, Violation, Aircraft, RedZone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

def reports_dashboard(request):
    """Dashboard des rapports"""
    # Statistiques pour les rapports
    total_alerts = Alert.objects.count()
    total_violations = Violation.objects.count()
    recent_violations = Violation.objects.select_related('aircraft', 'alert__red_zone').order_by('-alert__timestamp')[:10]
    
    # Statistiques par zone rouge
    zones_stats = RedZone.objects.annotate(
        alerts_count=Count('alerts'),
        violations_count=Count('alerts__violations')
    ).order_by('-violations_count')[:5]
    
    context = {
        'total_alerts': total_alerts,
        'total_violations': total_violations,
        'recent_violations': recent_violations,
        'zones_stats': zones_stats,
    }
    return render(request, 'reports/dashboard.html', context)

def alert_report(request, alert_id):
    """Rapport détaillé d'une alerte"""
    alert = get_object_or_404(Alert, id=alert_id)
    violations = Violation.objects.filter(alert=alert).select_related('aircraft')
    
    context = {
        'alert': alert,
        'violations': violations,
        'violations_count': violations.count(),
    }
    return render(request, 'reports/alert_report.html', context)

def alert_report_pdf(request, alert_id):
    """Génération du rapport PDF pour une alerte"""
    alert = get_object_or_404(Alert, id=alert_id)
    violations = Violation.objects.filter(alert=alert).select_related('aircraft')
    
    # Création du PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Titre
    title = Paragraph(f"Rapport d'Alerte - {alert.red_zone.name}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Informations de l'alerte
    info_data = [
        ['Zone Rouge:', alert.red_zone.name],
        ['Date/Heure:', alert.timestamp.strftime('%d/%m/%Y %H:%M:%S')],
        ['Type d\'alerte:', alert.get_alert_type_display()],
        ['Statut:', 'Traitée' if alert.is_processed else 'En attente'],
        ['Violations détectées:', str(violations.count())],
    ]
    
    info_table = Table(info_data, colWidths=[150, 300])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Tableau des violations
    if violations.exists():
        story.append(Paragraph("Violations détectées:", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        violation_data = [['Aéronef', 'Dans la zone', 'Distance (m)', 'Durée']]
        
        for violation in violations:
            duration = str(violation.duration_in_zone) if violation.duration_in_zone else 'N/A'
            violation_data.append([
                violation.aircraft.aircraft_id,
                'Oui' if violation.is_inside_zone else 'Non',
                f"{violation.distance_to_zone:.0f}",
                duration
            ])
        
        violation_table = Table(violation_data, colWidths=[120, 80, 100, 100])
        violation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(violation_table)
    else:
        story.append(Paragraph("Aucune violation détectée pour cette alerte.", styles['Normal']))
    
    # Construction du PDF
    doc.build(story)
    
    # Retour de la réponse
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_alerte_{alert_id}.pdf"'
    
    return response

def violations_report(request):
    """Rapport général des violations"""
    # Filtres
    zone_filter = request.GET.get('zone')
    aircraft_filter = request.GET.get('aircraft')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    violations = Violation.objects.select_related('aircraft', 'alert__red_zone').order_by('-alert__timestamp')
    
    # Application des filtres
    if zone_filter:
        violations = violations.filter(alert__red_zone_id=zone_filter)
    
    if aircraft_filter:
        violations = violations.filter(aircraft_id=aircraft_filter)
    
    if date_from:
        violations = violations.filter(alert__timestamp__gte=date_from)
    
    if date_to:
        violations = violations.filter(alert__timestamp__lte=date_to)
    
    # Données pour les filtres
    zones = RedZone.objects.filter(is_active=True).order_by('name')
    aircraft = Aircraft.objects.order_by('aircraft_id')
    
    context = {
        'violations': violations[:100],  # Limite pour la performance
        'zones': zones,
        'aircraft': aircraft,
        'current_zone_filter': zone_filter,
        'current_aircraft_filter': aircraft_filter,
        'current_date_from': date_from,
        'current_date_to': date_to,
        'total_violations': violations.count(),
    }
    return render(request, 'reports/violations_report.html', context)