import pandas as pd
import json
from datetime import datetime
from django.core.exceptions import ValidationError
from core.models import Aircraft, FlightData, RedZone, Alert
from .models import ImportSession, ColumnMapping

class FlightDataImporter:
    """Service d'importation des données de vol"""
    
    def __init__(self, import_session):
        self.import_session = import_session
        self.errors = []
        
    def import_from_file(self, file_path, column_mappings=None):
        """Importe les données de vol depuis un fichier CSV/Excel"""
        try:
            # Lecture du fichier
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Format de fichier non supporté")
            
            self.import_session.status = 'processing'
            self.import_session.save()
            
            # Mapping par défaut si non fourni
            if not column_mappings:
                column_mappings = self._get_default_flight_mappings(df.columns)
            
            records_created = 0
            records_errors = 0
            
            for index, row in df.iterrows():
                try:
                    self._process_flight_record(row, column_mappings)
                    records_created += 1
                except Exception as e:
                    records_errors += 1
                    self.errors.append(f"Ligne {index + 1}: {str(e)}")
            
            # Mise à jour de la session
            self.import_session.records_processed = len(df)
            self.import_session.records_created = records_created
            self.import_session.records_errors = records_errors
            self.import_session.error_log = '\n'.join(self.errors)
            self.import_session.status = 'completed' if records_errors == 0 else 'failed'
            self.import_session.save()
            
            return {
                'success': True,
                'records_processed': len(df),
                'records_created': records_created,
                'records_errors': records_errors,
                'errors': self.errors
            }
            
        except Exception as e:
            self.import_session.status = 'failed'
            self.import_session.error_log = str(e)
            self.import_session.save()
            return {'success': False, 'error': str(e)}
    
    def _process_flight_record(self, row, mappings):
        """Traite un enregistrement de vol"""
        # Récupération ou création de l'aéronef
        aircraft_id = row[mappings.get('aircraft_id', 'aircraft_id')]
        aircraft, created = Aircraft.objects.get_or_create(
            aircraft_id=aircraft_id,
            defaults={
                'name': row.get(mappings.get('aircraft_name', ''), ''),
                'aircraft_type': row.get(mappings.get('aircraft_type', ''), '')
            }
        )
        
        # Création des données de vol
        timestamp_str = row[mappings.get('timestamp', 'timestamp')]
        timestamp = pd.to_datetime(timestamp_str)
        
        FlightData.objects.create(
            aircraft=aircraft,
            timestamp=timestamp,
            latitude=float(row[mappings.get('latitude', 'latitude')]),
            longitude=float(row[mappings.get('longitude', 'longitude')]),
            altitude=float(row.get(mappings.get('altitude', 'altitude'), 0)) or None,
            speed=float(row.get(mappings.get('speed', 'speed'), 0)) or None,
            heading=float(row.get(mappings.get('heading', 'heading'), 0)) or None,
        )
    
    def _get_default_flight_mappings(self, columns):
        """Retourne un mapping par défaut basé sur les noms de colonnes"""
        mappings = {}
        
        # Mapping intelligent basé sur les noms de colonnes
        for col in columns:
            col_lower = col.lower()
            if 'aircraft' in col_lower or 'tail' in col_lower or 'id' in col_lower:
                mappings['aircraft_id'] = col
            elif 'lat' in col_lower:
                mappings['latitude'] = col
            elif 'lon' in col_lower or 'lng' in col_lower:
                mappings['longitude'] = col
            elif 'time' in col_lower or 'date' in col_lower:
                mappings['timestamp'] = col
            elif 'alt' in col_lower:
                mappings['altitude'] = col
            elif 'speed' in col_lower or 'vitesse' in col_lower:
                mappings['speed'] = col
            elif 'head' in col_lower or 'cap' in col_lower:
                mappings['heading'] = col
        
        return mappings

class RedZoneImporter:
    """Service d'importation des zones rouges"""
    
    def __init__(self, import_session):
        self.import_session = import_session
        self.errors = []
    
    def import_from_file(self, file_path):
        """Importe les zones rouges depuis un fichier"""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Format de fichier non supporté")
            
            self.import_session.status = 'processing'
            self.import_session.save()
            
            records_created = 0
            records_errors = 0
            
            for index, row in df.iterrows():
                try:
                    self._process_red_zone_record(row)
                    records_created += 1
                except Exception as e:
                    records_errors += 1
                    self.errors.append(f"Ligne {index + 1}: {str(e)}")
            
            self.import_session.records_processed = len(df)
            self.import_session.records_created = records_created
            self.import_session.records_errors = records_errors
            self.import_session.error_log = '\n'.join(self.errors)
            self.import_session.status = 'completed' if records_errors == 0 else 'failed'
            self.import_session.save()
            
            return {
                'success': True,
                'records_processed': len(df),
                'records_created': records_created,
                'records_errors': records_errors
            }
            
        except Exception as e:
            self.import_session.status = 'failed'
            self.import_session.error_log = str(e)
            self.import_session.save()
            return {'success': False, 'error': str(e)}
    
    def _process_red_zone_record(self, row):
        """Traite un enregistrement de zone rouge"""
        # Parsing des coordonnées du polygone
        coordinates_str = row.get('coordinates', row.get('polygon', ''))
        if isinstance(coordinates_str, str):
            # Format attendu: "lat1,lon1;lat2,lon2;lat3,lon3"
            coordinates = []
            for coord_pair in coordinates_str.split(';'):
                lat, lon = map(float, coord_pair.split(','))
                coordinates.append([lat, lon])
        else:
            raise ValueError("Format de coordonnées invalide")
        
        RedZone.objects.create(
            name=row['name'],
            description=row.get('description', ''),
            polygon_coordinates=coordinates,
            is_active=row.get('is_active', True)
        )

class AlertImporter:
    """Service d'importation des alertes"""
    
    def __init__(self, import_session):
        self.import_session = import_session
        self.errors = []
    
    def import_from_file(self, file_path):
        """Importe les alertes depuis un fichier"""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Format de fichier non supporté")
            
            self.import_session.status = 'processing'
            self.import_session.save()
            
            records_created = 0
            records_errors = 0
            
            for index, row in df.iterrows():
                try:
                    self._process_alert_record(row)
                    records_created += 1
                except Exception as e:
                    records_errors += 1
                    self.errors.append(f"Ligne {index + 1}: {str(e)}")
            
            self.import_session.records_processed = len(df)
            self.import_session.records_created = records_created
            self.import_session.records_errors = records_errors
            self.import_session.error_log = '\n'.join(self.errors)
            self.import_session.status = 'completed' if records_errors == 0 else 'failed'
            self.import_session.save()
            
            return {
                'success': True,
                'records_processed': len(df),
                'records_created': records_created,
                'records_errors': records_errors
            }
            
        except Exception as e:
            self.import_session.status = 'failed'
            self.import_session.error_log = str(e)
            self.import_session.save()
            return {'success': False, 'error': str(e)}
    
    def _process_alert_record(self, row):
        """Traite un enregistrement d'alerte"""
        # Recherche de la zone rouge
        zone_name = row['red_zone_name']
        try:
            red_zone = RedZone.objects.get(name=zone_name, is_active=True)
        except RedZone.DoesNotExist:
            raise ValueError(f"Zone rouge '{zone_name}' non trouvée")
        
        timestamp = pd.to_datetime(row['timestamp'])
        
        Alert.objects.create(
            timestamp=timestamp,
            red_zone=red_zone,
            description=row.get('description', ''),
            alert_type=row.get('alert_type', 'manual')
        )