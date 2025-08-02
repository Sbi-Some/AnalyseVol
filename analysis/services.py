from datetime import datetime, timedelta
from django.db.models import Q
from shapely.geometry import Point, Polygon
from core.models import Aircraft, FlightData, RedZone, Alert, Violation, AnalysisSession
import math

class FlightAnalyzer:
    """Service principal d'analyse des vols"""
    
    def __init__(self, analysis_session=None):
        self.analysis_session = analysis_session
        self.violations_found = 0
    
    def analyze_alert(self, alert, time_window_minutes=5):
        """
        Analyse une alerte spécifique pour détecter les violations
        
        Args:
            alert: Instance d'Alert à analyser
            time_window_minutes: Fenêtre temporelle autour de l'alerte (en minutes)
        """
        try:
            # Définition de la fenêtre temporelle
            start_time = alert.timestamp - timedelta(minutes=time_window_minutes)
            end_time = alert.timestamp + timedelta(minutes=time_window_minutes)
            
            # Récupération des données de vol dans la fenêtre temporelle
            flight_data = FlightData.objects.filter(
                timestamp__gte=start_time,
                timestamp__lte=end_time
            ).select_related('aircraft').order_by('aircraft', 'timestamp')
            
            # Création du polygone de la zone rouge
            zone_polygon = self._create_polygon_from_coordinates(alert.red_zone.polygon_coordinates)
            
            violations = []
            
            # Analyse par aéronef
            current_aircraft = None
            aircraft_positions = []
            
            for data_point in flight_data:
                if current_aircraft != data_point.aircraft:
                    # Traitement de l'aéronef précédent
                    if current_aircraft and aircraft_positions:
                        violation = self._analyze_aircraft_trajectory(
                            current_aircraft, aircraft_positions, alert, zone_polygon
                        )
                        if violation:
                            violations.append(violation)
                    
                    # Nouveau aéronef
                    current_aircraft = data_point.aircraft
                    aircraft_positions = []
                
                aircraft_positions.append(data_point)
            
            # Traitement du dernier aéronef
            if current_aircraft and aircraft_positions:
                violation = self._analyze_aircraft_trajectory(
                    current_aircraft, aircraft_positions, alert, zone_polygon
                )
                if violation:
                    violations.append(violation)
            
            # Sauvegarde des violations
            for violation_data in violations:
                Violation.objects.create(**violation_data)
                self.violations_found += 1
            
            # Marquer l'alerte comme traitée
            alert.is_processed = True
            alert.save()
            
            return {
                'success': True,
                'violations_count': len(violations),
                'aircraft_analyzed': len(set(fp.aircraft for fp in flight_data))
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def analyze_all_unprocessed_alerts(self):
        """Analyse toutes les alertes non traitées"""
        unprocessed_alerts = Alert.objects.filter(is_processed=False)
        
        if self.analysis_session:
            self.analysis_session.status = 'running'
            self.analysis_session.save()
        
        results = []
        
        for alert in unprocessed_alerts:
            result = self.analyze_alert(alert)
            results.append({
                'alert_id': alert.id,
                'alert_zone': alert.red_zone.name,
                'alert_time': alert.timestamp,
                'result': result
            })
        
        if self.analysis_session:
            self.analysis_session.violations_found = self.violations_found
            self.analysis_session.status = 'completed'
            self.analysis_session.end_time = datetime.now()
            self.analysis_session.save()
        
        return results
    
    def _create_polygon_from_coordinates(self, coordinates):
        """Crée un polygone Shapely à partir des coordonnées"""
        if not coordinates or len(coordinates) < 3:
            raise ValueError("Au moins 3 points sont nécessaires pour définir un polygone")
        
        # Conversion des coordonnées [lat, lon] en [lon, lat] pour Shapely
        shapely_coords = [(coord[1], coord[0]) for coord in coordinates]
        return Polygon(shapely_coords)
    
    def _analyze_aircraft_trajectory(self, aircraft, positions, alert, zone_polygon):
        """Analyse la trajectoire d'un aéronef pour une alerte donnée"""
        # Position à l'instant exact de l'alerte (ou la plus proche)
        alert_position = self._find_closest_position(positions, alert.timestamp)
        
        if not alert_position:
            return None
        
        # Point géographique
        point = Point(alert_position.longitude, alert_position.latitude)
        
        # Vérification si l'aéronef est dans la zone
        is_inside = zone_polygon.contains(point)
        
        # Calcul de la distance à la zone
        distance = self._calculate_distance_to_zone(point, zone_polygon)
        
        # Si l'aéronef n'est pas dans la zone et est trop loin, pas de violation
        if not is_inside and distance > 1000:  # 1km de seuil
            return None
        
        # Calcul des temps d'entrée et sortie si dans la zone
        entry_time, exit_time, duration = None, None, None
        
        if is_inside:
            entry_time, exit_time = self._calculate_zone_entry_exit(positions, zone_polygon)
            if entry_time and exit_time:
                duration = exit_time - entry_time
        
        return {
            'alert': alert,
            'aircraft': aircraft,
            'position_at_alert': {
                'latitude': alert_position.latitude,
                'longitude': alert_position.longitude,
                'altitude': alert_position.altitude,
                'timestamp': alert_position.timestamp.isoformat()
            },
            'distance_to_zone': distance,
            'is_inside_zone': is_inside,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'duration_in_zone': duration
        }
    
    def _find_closest_position(self, positions, target_time):
        """Trouve la position la plus proche d'un instant donné"""
        if not positions:
            return None
        
        closest_position = None
        min_time_diff = None
        
        for position in positions:
            time_diff = abs((position.timestamp - target_time).total_seconds())
            if min_time_diff is None or time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_position = position
        
        return closest_position
    
    def _calculate_distance_to_zone(self, point, zone_polygon):
        """Calcule la distance d'un point à une zone (en mètres)"""
        if zone_polygon.contains(point):
            return 0.0
        
        # Distance au bord du polygone
        distance_degrees = point.distance(zone_polygon.boundary)
        
        # Conversion approximative en mètres (1 degré ≈ 111 km)
        distance_meters = distance_degrees * 111000
        
        return distance_meters
    
    def _calculate_zone_entry_exit(self, positions, zone_polygon):
        """Calcule les temps d'entrée et de sortie d'une zone"""
        entry_time = None
        exit_time = None
        was_inside = False
        
        for position in sorted(positions, key=lambda p: p.timestamp):
            point = Point(position.longitude, position.latitude)
            is_inside = zone_polygon.contains(point)
            
            if is_inside and not was_inside:
                # Entrée dans la zone
                entry_time = position.timestamp
            elif not is_inside and was_inside:
                # Sortie de la zone
                exit_time = position.timestamp
                break
            
            was_inside = is_inside
        
        return entry_time, exit_time

class GeospatialUtils:
    """Utilitaires pour les calculs géospatiaux"""
    
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calcule la distance entre deux points géographiques (formule de Haversine)
        Retourne la distance en mètres
        """
        R = 6371000  # Rayon de la Terre en mètres
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def point_in_polygon(lat, lon, polygon_coords):
        """
        Vérifie si un point est à l'intérieur d'un polygone
        Utilise l'algorithme ray casting
        """
        x, y = lon, lat
        n = len(polygon_coords)
        inside = False
        
        p1x, p1y = polygon_coords[0][1], polygon_coords[0][0]  # lon, lat
        
        for i in range(1, n + 1):
            p2x, p2y = polygon_coords[i % n][1], polygon_coords[i % n][0]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside