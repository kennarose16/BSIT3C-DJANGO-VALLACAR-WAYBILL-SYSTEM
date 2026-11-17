from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.buses.models import Bus, BusRoute
from apps.drivers.models import Driver


@login_required(login_url='login')
def fleet_dashboard(request):
    buses = Bus.objects.select_related('driver').prefetch_related('routes')
    return render(request, 'fleet/dashboard.html', {
        'driver_count': Driver.objects.count(),
        'bus_count': Bus.objects.count(),
        'route_count': BusRoute.objects.count(),
        'buses': buses,
    })
