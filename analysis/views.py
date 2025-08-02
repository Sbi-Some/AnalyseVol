from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime
from core.models import Alert, AnalysisSession, Violation
from .services import FlightAnalyzer

def analysis_dashboard(request):
    """Dashboard des analyses"""
    recent_sessions = AnalysisSession.objects.order_by('-start_time')[:10]
    unprocessed_alerts = Alert.objects.filter(is_processed=False).count()
    
    context = {
        'recent_sessions': recent_sessions,
        'unprocessed_alerts': unprocessed_alerts,
        'total_violations': Violation.objects.count(),
        'running_sessions': AnalysisSession.objects.filter(status='running').count(),
    }
    return render(request, 'analysis/dashboard.html', context)

def run_analysis(request):
    """Lancement d'une nouvelle analyse"""
    if request.method == 'POST':
        session_name = request.POST.get('session_name', f'Analyse {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        
        # Création de la session d'analyse
        analysis_session = AnalysisSession.objects.create(
            name=session_name,
            status='pending'
        )
        
        try:
            # Lancement de l'analyse
            analyzer = FlightAnalyzer(analysis_session)
            results = analyzer.analyze_all_unprocessed_alerts()
            
            violations_count = sum(r['result'].get('violations_count', 0) for r in results if r['result'].get('success'))
            
            messages.success(request, f'Analyse terminée : {violations_count} violations détectées')
            
            return redirect('analysis:session_detail', session_id=analysis_session.id)
            
        except Exception as e:
            analysis_session.status = 'failed'
            analysis_session.error_message = str(e)
            analysis_session.end_time = datetime.now()
            analysis_session.save()
            
            messages.error(request, f'Erreur lors de l\'analyse : {str(e)}')
            return redirect('analysis:dashboard')
    
    # GET request - afficher le formulaire
    unprocessed_alerts = Alert.objects.filter(is_processed=False).select_related('red_zone')
    
    context = {
        'unprocessed_alerts': unprocessed_alerts,
    }
    return render(request, 'analysis/run_analysis.html', context)

def analysis_session_detail(request, session_id):
    """Détail d'une session d'analyse"""
    session = get_object_or_404(AnalysisSession, id=session_id)
    
    # Récupération des violations trouvées pendant cette session
    # (approximation basée sur la période de la session)
    violations = []
    if session.start_time and session.end_time:
        violations = Violation.objects.filter(
            alert__created_at__gte=session.start_time,
            alert__created_at__lte=session.end_time
        ).select_related('aircraft', 'alert__red_zone')[:20]
    
    context = {
        'session': session,
        'violations': violations,
    }
    return render(request, 'analysis/session_detail.html', context)