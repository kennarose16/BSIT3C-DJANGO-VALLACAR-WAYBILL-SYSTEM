from decimal import Decimal

from django.conf import settings


DESTINATION_PRESETS = {
    'route_a': {'name': 'Route A', 'base_fare': Decimal('50.00')},
    'route_b': {'name': 'Route B', 'base_fare': Decimal('120.00')},
    'route_c': {'name': 'Route C', 'base_fare': Decimal('200.00')},
}


def rate_multiplier():
    return Decimal(str(getattr(settings, 'WAYBILL_RATE_MULTIPLIER', '25.00')))


def calculate_amount(bus, base_fare):
    return (Decimal(base_fare) + Decimal(bus.capacity) * rate_multiplier()).quantize(Decimal('0.01'))