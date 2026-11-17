from datetime import date
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.buses.models import Bus
from apps.drivers.models import Driver


class AutoPayment(models.Model):
    class PaymentStatus(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'

    class Frequency(models.TextChoices):
        ONE_TIME = 'one_time', 'One-time'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    reference_number = models.CharField(max_length=50, unique=True, blank=True)
    driver = models.ForeignKey(
        Driver,
        related_name='automatic_payments',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    bus = models.ForeignKey(
        Bus,
        related_name='automatic_payments',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=30, default='Auto Debit')
    due_date = models.DateField()
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.MONTHLY)
    auto_pay = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.SCHEDULED)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbl_autopayment'
        ordering = ['-due_date']

    def __str__(self):
        return self.reference_number or f'AutoPayment-{self.id}'

    @property
    def target_name(self):
        if self.driver:
            return str(self.driver)
        if self.bus:
            return str(self.bus)
        return 'General payment'

    def process_if_due(self):
        if self.auto_pay and self.status == self.PaymentStatus.SCHEDULED and self.due_date <= date.today():
            self.status = self.PaymentStatus.PAID
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = f'AP-{timezone.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)
