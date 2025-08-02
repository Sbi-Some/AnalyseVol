from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from .models import ImportSession, ColumnMapping
from .services import FlightDataImporter, RedZoneImporter, AlertImporter

def import_dashboard(request):
    """Dashboard des importations"""
    recent_imports = ImportSession.objects.order_by('-created_at')[:10]
    
    context = {
        'recent_imports': recent_imports,
        'pending_imports': ImportSession.objects.filter(status='pending').count(),
        'completed_imports': ImportSession.objects.filter(status='completed').count(),
        'failed_imports': ImportSession.objects.filter(status='failed').count(),
    }
    return render(request, 'imports/dashboard.html', context)

def import_flight_data(request):
    """Import des données de vol"""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Aucun fichier sélectionné')
            return redirect('imports:flight_data')
        
        file = request.FILES['file']
        session_name = request.POST.get('session_name', f'Import vol {file.name}')
        
        # Sauvegarde du fichier
        file_path = default_storage.save(f'imports/{file.name}', ContentFile(file.read()))
        
        # Création de la session d'import
        import_session = ImportSession.objects.create(
            name=session_name,
            file_type='flight_data',
            file_path=file_path,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Lancement de l'import
        try:
            importer = FlightDataImporter(import_session)
            result = importer.import_from_file(default_storage.path(file_path))
            
            if result['success']:
                messages.success(request, f'Import réussi : {result["records_created"]} enregistrements créés')
            else:
                messages.error(request, f'Erreur lors de l\'import : {result["error"]}')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'import : {str(e)}')
        
        return redirect('imports:dashboard')
    
    return render(request, 'imports/fligh_data.html')

def import_red_zones(request):
    """Import des zones rouges"""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Aucun fichier sélectionné')
            return redirect('imports:red_zones')
        
        file = request.FILES['file']
        session_name = request.POST.get('session_name', f'Import zones {file.name}')
        
        # Sauvegarde du fichier
        file_path = default_storage.save(f'imports/{file.name}', ContentFile(file.read()))
        
        # Création de la session d'import
        import_session = ImportSession.objects.create(
            name=session_name,
            file_type='red_zones',
            file_path=file_path,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Lancement de l'import
        try:
            importer = RedZoneImporter(import_session)
            result = importer.import_from_file(default_storage.path(file_path))
            
            if result['success']:
                messages.success(request, f'Import réussi : {result["records_created"]} zones créées')
            else:
                messages.error(request, f'Erreur lors de l\'import : {result["error"]}')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'import : {str(e)}')
        
        return redirect('imports:dashboard')
    
    return render(request, 'imports/red_zones.html')

def import_alerts(request):
    """Import des alertes"""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Aucun fichier sélectionné')
            return redirect('imports:alerts')
        
        file = request.FILES['file']
        session_name = request.POST.get('session_name', f'Import alertes {file.name}')
        
        # Sauvegarde du fichier
        file_path = default_storage.save(f'imports/{file.name}', ContentFile(file.read()))
        
        # Création de la session d'import
        import_session = ImportSession.objects.create(
            name=session_name,
            file_type='alerts',
            file_path=file_path,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Lancement de l'import
        try:
            importer = AlertImporter(import_session)
            result = importer.import_from_file(default_storage.path(file_path))
            
            if result['success']:
                messages.success(request, f'Import réussi : {result["records_created"]} alertes créées')
            else:
                messages.error(request, f'Erreur lors de l\'import : {result["error"]}')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'import : {str(e)}')
        
        return redirect('imports:dashboard')
    
    return render(request, 'imports/alerts-.html')

def import_session_detail(request, session_id):
    """Détail d'une session d'import"""
    session = get_object_or_404(ImportSession, id=session_id)
    
    context = {
        'session': session,
    }
    return render(request, 'imports/session_detail.html', context)