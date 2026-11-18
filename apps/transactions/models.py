from django.core.validators import MinValueValidator
from django.db import models

from apps.buses.models import Bus, BusRoute


class Transaction(models.Model):
    class PaymentStatus(models.TextChoices):
        PAID = 'paid', 'Paid'
        UNPAID = 'unpaid', 'Unpaid'
        PENDING = 'pending', 'Pending'

    class Status(models.TextChoices):
        COMPLETED = 'completed', 'Completed'
        IN_TRANSIT = 'in_transit', 'In Transit'
        PENDING = 'pending', 'Pending'

    bus = models.ForeignKey(Bus, related_name='transactions', on_delete=models.PROTECT)
    route = models.ForeignKey(
        BusRoute,
        related_name='transactions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sender_name = models.CharField(max_length=120)
    receiver_name = models.CharField(max_length=120)
    destination = models.CharField(max_length=180)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    proof_image = models.ImageField(upload_to='transaction_proofs/%Y/%m/', blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'waybill_transaction'
        ordering = ['-created_at', '-pk']

    def __str__(self):
        return self.transaction_id

    @property
    def transaction_id(self):
        return f'TXN-{self.pk:06d}' if self.pk else 'TXN-PENDING'
