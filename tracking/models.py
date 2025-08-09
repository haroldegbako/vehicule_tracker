# models.py
from django.db import models
from django.contrib.auth.models import User


class VehicleData(models.Model):
    vehicle_id = models.CharField(max_length=50, default="V1", db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.vehicle_id} @ {self.timestamp}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    vehicle_id = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.user.username


class UserZone(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default="Zone de surveillance")
    geojson = models.JSONField()  # Stocke le polygone dessiné

    def __str__(self):
        return f"Zone de {self.user.username}"




class Alert(models.Model):
    # L'utilisateur associé (optionnel, si plusieurs utilisateurs)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    # Véhicule concerné
    vehicle = models.CharField(max_length=50)

    # Type d'alerte (choix prédéfinis pour plus de cohérence)
    ALERT_TYPES = [
        ('out_of_geofence', 'Hors zone'),
        ('speeding', 'Excès de vitesse'),
        ('no_signal', 'Perte de signal GPS'),
        ('maintenance', 'Maintenance requise'),
        ('ignition_on', 'Démarrage du véhicule'),
        ('ignition_off', 'Arrêt du véhicule'),
    ]
    alert_type = models.CharField(max_length=100, choices=ALERT_TYPES)
    description = models.TextField()

    # Horodatage
    timestamp = models.DateTimeField(auto_now_add=True)

    # ✅ Nouveaux champs utiles
    is_read = models.BooleanField(default=False)  # Pour "marquer comme vu"
    resolved = models.BooleanField(default=False)  # Optionnel : pour suivre les alertes résolues

    def __str__(self):
        return f"🚨 {self.get_alert_type_display()} - {self.vehicle}"

    class Meta:
        ordering = ['-timestamp']  # Tri par date décroissante
        verbose_name = "Alerte"
        verbose_name_plural = "Alertes"



# models.py
class History(models.Model):
    vehicle = models.CharField(max_length=50)
    path = models.JSONField(db_column='data')  # déjà corrigé
    date = models.DateTimeField(auto_now_add=True, db_column='start_time')  # Ajoute db_column
    distance_km = models.FloatField(default=0)

    class Meta:
        db_table = 'tracking_history'

    def __str__(self):
        return f"Historique {self.vehicle} du {self.date}"






class ContactMessage(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.subject}"
class SMSPosition(models.Model):
    vehicle_id = models.CharField(max_length=50, default="LILYGO-GPS-001")
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    sent_by_sms = models.BooleanField(default=True)

    def __str__(self):
        return f"SMS: {self.latitude}, {self.longitude}"
