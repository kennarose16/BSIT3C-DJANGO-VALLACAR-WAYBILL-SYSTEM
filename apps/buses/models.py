from django.core.validators import MinValueValidator
from django.db import models

from apps.drivers.models import Driver


class Bus(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        MAINTENANCE = 'maintenance', 'Maintenance'
        INACTIVE = 'inactive', 'Inactive'

    fleet_number = models.CharField(max_length=30, unique=True)
    plate_number = models.CharField(max_length=20, unique=True)
    capacity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    driver = models.ForeignKey(
        Driver,
        related_name='buses',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fleet_bus'
        ordering = ['fleet_number']

    def __str__(self):
        return f'{self.fleet_number} ({self.plate_number})'


class BusRoute(models.Model):
    bus = models.ForeignKey(Bus, related_name='routes', on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    origin = models.CharField(max_length=120)
    destination = models.CharField(max_length=120)
    departure_time = models.TimeField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)
    fare = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fleet_busroute'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['bus', 'name'], name='fleet_bus_route_name_uniq'),
        ]

    def __str__(self):
        return f'{self.name}: {self.origin} to {self.destination}'