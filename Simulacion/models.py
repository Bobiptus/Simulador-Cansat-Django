from django.db import models

class SimulationResult(models.Model):
    timestamp = models.DateTimeField()
    apogee = models.FloatField(null=True, blank=True)
    inclination = models.FloatField()
    heading = models.FloatField()
    rail_length = models.FloatField()
    cansat_mass = models.FloatField()
    drag_coeff = models.FloatField()
    burn_time = models.FloatField()
    avg_thrust = models.FloatField()
    elevation = models.FloatField()

    def __str__(self):
        return f"Simulación del {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"