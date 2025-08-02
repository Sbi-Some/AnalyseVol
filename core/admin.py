from django.contrib import admin
from .models import Aircraft, FlightData, RedZone, Alert, Violation, AnalysisSession

@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = ['aircraft_id', 'name', 'aircraft_type', 'created_at']
    list_filter = ['aircraft_type', 'created_at']
    search_fields = ['aircraft_id', 'name']
    ordering = ['aircraft_id']

@admin.register(FlightData)
class FlightDataAdmin(admin.ModelAdmin):
    list_display = ['aircraft', 'timestamp', 'latitude', 'longitude', 'altitude']
    list_filter = ['aircraft', 'timestamp']
    search_fields = ['aircraft__aircraft_id']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('aircraft')

@admin.register(RedZone)
class RedZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'coordinates_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def coordinates_count(self, obj):
        return obj.coordinates_count
    coordinates_count.short_description = 'Nb points'

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['red_zone', 'timestamp', 'alert_type', 'is_processed']
    list_filter = ['alert_type', 'is_processed', 'timestamp', 'red_zone']
    search_fields = ['red_zone__name', 'description']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('red_zone')

@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ['aircraft', 'alert', 'is_inside_zone', 'distance_to_zone', 'duration_in_zone']
    list_filter = ['is_inside_zone', 'alert__red_zone', 'aircraft']
    search_fields = ['aircraft__aircraft_id', 'alert__red_zone__name']
    ordering = ['-alert__timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('aircraft', 'alert', 'alert__red_zone')

@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'files_processed', 'violations_found', 'start_time', 'end_time']
    list_filter = ['status', 'start_time']
    search_fields = ['name']
    ordering = ['-start_time']
    readonly_fields = ['start_time', 'end_time']
