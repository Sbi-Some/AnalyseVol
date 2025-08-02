from django.db import models
from django.contrib.auth.models import User
import json

class Aircraft(models.Model):
    """Modèle représentant un aéronef"""
    aircraft_id = models.CharField(max_length=50, unique=True, verbose_name="ID Aéronef")
    name = models.CharField(max_length=100, blank=True, verbose_name="Nom")
    aircraft_type = models.CharField(max_length=50, blank=True, verbose_name="Type")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Aéronef"
        verbose_name_plural = "Aéronefs"
        ordering = ['aircraft_id']
    
    def __str__(self):
        return f"{self.aircraft_id} - {self.name or 'Sans nom'}"

class FlightData(models.Model):
    """Données de vol pour chaque aéronef"""
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name='flight_data')
    timestamp = models.DateTimeField(verbose_name="Horodatage")
    latitude = models.FloatField(verbose_name="Latitude")
    longitude = models.FloatField(verbose_name="Longitude")
    altitude = models.FloatField(null=True, blank=True, verbose_name="Altitude (m)")
    speed = models.FloatField(null=True, blank=True, verbose_name="Vitesse (km/h)")
    heading = models.FloatField(null=True, blank=True, verbose_name="Cap (degrés)")
    
    class Meta:
        verbose_name = "Donnée de vol"
        verbose_name_plural = "Données de vol"
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.aircraft.aircraft_id} - {self.timestamp}"

class RedZone(models.Model):
    """Zone rouge définie par un polygone"""
    name = models.CharField(max_length=100, verbose_name="Nom de la zone")
    description = models.TextField(blank=True, verbose_name="Description")
    polygon_coordinates = models.JSONField(verbose_name="Coordonnées du polygone")
    is_active = models.BooleanField(default=True, verbose_name="Zone active")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Zone rouge"
        verbose_name_plural = "Zones rouges"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    @property
    def coordinates_count(self):
        """Retourne le nombre de points du polygone"""
        if isinstance(self.polygon_coordinates, list):
            return len(self.polygon_coordinates)
        return 0

class Alert(models.Model):
    """Alerte émise pour une zone rouge"""
    timestamp = models.DateTimeField(verbose_name="Horodatage de l'alerte")
    red_zone = models.ForeignKey(RedZone, on_delete=models.CASCADE, related_name='alerts')
    description = models.TextField(blank=True, verbose_name="Description")
    alert_type = models.CharField(
        max_length=50, 
        choices=[
            ('intrusion', 'Intrusion détectée'),
            ('proximity', 'Proximité'),
            ('manual', 'Alerte manuelle'),
        ],
        default='intrusion',
        verbose_name="Type d'alerte"
    )
    is_processed = models.BooleanField(default=False, verbose_name="Traitée")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Alerte"
        verbose_name_plural = "Alertes"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Alerte {self.red_zone.name} - {self.timestamp}"

class Violation(models.Model):
    """Violation détectée lors de l'analyse"""
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='violations')
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name='violations')
    position_at_alert = models.JSONField(verbose_name="Position à l'instant de l'alerte")
    distance_to_zone = models.FloatField(verbose_name="Distance à la zone (m)")
    is_inside_zone = models.BooleanField(verbose_name="À l'intérieur de la zone")
    entry_time = models.DateTimeField(null=True, blank=True, verbose_name="Heure d'entrée")
    exit_time = models.DateTimeField(null=True, blank=True, verbose_name="Heure de sortie")
    duration_in_zone = models.DurationField(null=True, blank=True, verbose_name="Durée dans la zone")
    
    class Meta:
        verbose_name = "Violation"
        verbose_name_plural = "Violations"
        ordering = ['-alert__timestamp']
    
    def __str__(self):
        return f"{self.aircraft.aircraft_id} - {self.alert.red_zone.name}"

class AnalysisSession(models.Model):
    """Session d'analyse pour tracer les traitements"""
    name = models.CharField(max_length=200, verbose_name="Nom de l'analyse")
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'En attente'),
            ('running', 'En cours'),
            ('completed', 'Terminée'),
            ('failed', 'Échouée'),
        ],
        default='pending'
    )
    files_processed = models.IntegerField(default=0)
    violations_found = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Session d'analyse"
        verbose_name_plural = "Sessions d'analyse"
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.name} - {self.status}"

# Create your models here.
