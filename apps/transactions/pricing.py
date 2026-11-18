from decimal import Decimal

from django.conf import settings


def default_base_rate():
    return Decimal(str(getattr(settings, 'WAYBILL_DEFAULT_BASE_RATE', '50.00')))


def rate_multiplier():
    return Decimal(str(getattr(settings, 'WAYBILL_RATE_MULTIPLIER', '25.00')))


def calculate_amount(bus, base_fare):
    return (Decimal(base_fare) + Decimal(bus.capacity) * rate_multiplier()).quantize(Decimal('0.01'))