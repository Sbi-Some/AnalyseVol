from django.db import models
from django.contrib.auth.models import User

class ImportSession(models.Model):
    """Session d'importation de fichiers"""
    name = models.CharField(max_length=200, verbose_name="Nom de l'import")
    file_type = models.CharField(
        max_length=20,
        choices=[
            ('flight_data', 'Données de vol'),
            ('red_zones', 'Zones rouges'),
            ('alerts', 'Alertes'),
        ],
        verbose_name="Type de fichier"
    )
    file_path = models.FileField(upload_to='imports/', verbose_name="Fichier")
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'En attente'),
            ('processing', 'En cours'),
            ('completed', 'Terminé'),
            ('failed', 'Échoué'),
        ],
        default='pending'
    )
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_errors = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Session d'importation"
        verbose_name_plural = "Sessions d'importation"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_file_type_display()}"

class ColumnMapping(models.Model):
    """Mapping des colonnes pour l'importation"""
    import_session = models.ForeignKey(ImportSession, on_delete=models.CASCADE, related_name='column_mappings')
    source_column = models.CharField(max_length=100, verbose_name="Colonne source")
    target_field = models.CharField(max_length=100, verbose_name="Champ cible")
    is_required = models.BooleanField(default=False)
    default_value = models.CharField(max_length=200, blank=True, verbose_name="Valeur par défaut")
    
    class Meta:
        verbose_name = "Mapping de colonne"
        verbose_name_plural = "Mappings de colonnes"
        unique_together = ['import_session', 'target_field']
    
    def __str__(self):
        return f"{self.source_column} -> {self.target_field}"