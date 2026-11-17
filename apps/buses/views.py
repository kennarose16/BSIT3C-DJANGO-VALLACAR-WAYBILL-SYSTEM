from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import ProtectedError, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.drivers.models import Driver
from .forms import BusForm, BusRouteForm
from .models import Bus, BusRoute


@login_required(login_url='login')
def bus_list(request):
    query = request.GET.get('q', '').strip()
    buses = Bus.objects.select_related('driver').all()
    if query:
        buses = buses.filter(
            Q(fleet_number__icontains=query) |
            Q(plate_number__icontains=query) |
            Q(driver__first_name__icontains=query) |
            Q(driver__last_name__icontains=query)
        )
    page = Paginator(buses, 10).get_page(request.GET.get('page', 1))
    return render(request, 'fleet/bus_list.html', {
        'buses': page,
        'query': query,
        'drivers': Driver.objects.filter(is_active=True).order_by('last_name', 'first_name'),
    })


@login_required(login_url='login')
def bus_form(request, pk=None):
    bus = get_object_or_404(Bus, pk=pk) if pk else None
    form = BusForm(request.POST if request.method == 'POST' else None, instance=bus)
    if request.method == 'POST' and form.is_valid():
        saved_bus = form.save()
        messages.success(request, f'Bus "{saved_bus.fleet_number}" was saved.')
        return redirect('buses:bus_list')
    return render(request, 'fleet/form.html', {
        'form': form,
        'title': 'Edit bus' if bus else 'Add bus',
        'cancel_url': reverse('buses:bus_list'),
    })


@login_required(login_url='login')
@require_POST
def bus_delete(request, pk):
    bus = get_object_or_404(Bus, pk=pk)
    try:
        bus.delete()
    except ProtectedError:
        messages.error(request, 'Delete this bus\'s routes before deleting the bus.')
    else:
        messages.success(request, f'Bus "{bus.fleet_number}" was deleted.')
    return redirect('buses:bus_list')


@login_required(login_url='login')
def bus_list_ajax(request):
    query = request.GET.get('q', '').strip()
    buses = Bus.objects.select_related('driver').all()
    if query:
        buses = buses.filter(
            Q(fleet_number__icontains=query) |
            Q(plate_number__icontains=query) |
            Q(driver__first_name__icontains=query) |
            Q(driver__last_name__icontains=query)
        )
    page = Paginator(buses, 10).get_page(request.GET.get('page', 1))
    data = [{
        'id': bus.pk,
        'fleet_number': bus.fleet_number,
        'plate_number': bus.plate_number,
        'capacity': bus.capacity,
        'driver_id': bus.driver_id,
        'driver': str(bus.driver) if bus.driver else '',
        'status': bus.status,
        'status_display': bus.get_status_display(),
        'routes': bus.routes.count(),
    } for bus in page.object_list]
    return JsonResponse({
        'data': data,
        'has_next': page.has_next(),
        'has_prev': page.has_previous(),
        'page': page.number,
        'pages': page.paginator.num_pages,
        'total': page.paginator.count,
    })


@login_required(login_url='login')
def bus_get_ajax(request, pk):
    bus = get_object_or_404(Bus.objects.select_related('driver'), pk=pk)
    return JsonResponse({
        'id': bus.pk,
        'fleet_number': bus.fleet_number,
        'plate_number': bus.plate_number,
        'capacity': bus.capacity,
        'driver_id': bus.driver_id,
        'driver': str(bus.driver) if bus.driver else '',
        'status': bus.status,
    })


def _form_error(form):
    errors = []
    for field_name, field_errors in form.errors.items():
        label = form.fields[field_name].label if field_name in form.fields else ''
        errors.extend(f'{label}: {error}' if label else str(error) for error in field_errors)
    return ' '.join(errors)


@login_required(login_url='login')
@require_POST
def bus_save_ajax(request):
    bus_id = request.POST.get('id')
    bus = get_object_or_404(Bus, pk=bus_id) if bus_id else Bus()
    form = BusForm(request.POST, instance=bus)
    if not form.is_valid():
        return JsonResponse({'error': _form_error(form)}, status=400)
    try:
        bus = form.save()
    except IntegrityError:
        return JsonResponse({'error': 'That fleet number or plate number is already in use.'}, status=400)
    messages.success(request, f'Bus "{bus.fleet_number}" was saved.')
    return JsonResponse({'status': 'success', 'id': bus.pk})


@login_required(login_url='login')
@require_POST
def bus_delete_ajax(request, pk):
    bus = get_object_or_404(Bus, pk=pk)
    fleet_number = bus.fleet_number
    try:
        bus.delete()
    except ProtectedError:
        return JsonResponse({'error': 'Delete this bus\'s routes before deleting the bus.'}, status=400)
    messages.success(request, f'Bus "{fleet_number}" was deleted.')
    return JsonResponse({'status': 'deleted'})


@login_required(login_url='login')
def route_list(request, bus_pk):
    bus = get_object_or_404(Bus, pk=bus_pk)
    routes = BusRoute.objects.filter(bus=bus)
    query = request.GET.get('q', '').strip()
    if query:
        routes = routes.filter(
            Q(name__icontains=query) |
            Q(origin__icontains=query) |
            Q(destination__icontains=query)
        )
    page = Paginator(routes, 10).get_page(request.GET.get('page', 1))
    return render(request, 'fleet/route_list.html', {'bus': bus, 'routes': page, 'query': query})


@login_required(login_url='login')
def route_form(request, bus_pk, pk=None):
    bus = get_object_or_404(Bus, pk=bus_pk)
    route = get_object_or_404(BusRoute, pk=pk, bus=bus) if pk else BusRoute(bus=bus)
    form = BusRouteForm(request.POST if request.method == 'POST' else None, instance=route)
    if request.method == 'POST' and form.is_valid():
        saved_route = form.save(commit=False)
        saved_route.bus = bus
        saved_route.save()
        messages.success(request, f'Route "{saved_route.name}" was saved for bus {bus.fleet_number}.')
        return redirect('buses:route_list', bus_pk=bus.pk)
    return render(request, 'fleet/form.html', {
        'form': form,
        'title': 'Edit route' if pk else f'Add route for {bus.fleet_number}',
        'cancel_url': reverse('buses:route_list', args=[bus.pk]),
    })


@login_required(login_url='login')
@require_POST
def route_delete(request, bus_pk, pk):
    bus = get_object_or_404(Bus, pk=bus_pk)
    route = get_object_or_404(BusRoute, pk=pk, bus=bus)
    route_name = route.name
    route.delete()
    messages.success(request, f'Route "{route_name}" was deleted.')
    return redirect('buses:route_list', bus_pk=bus.pk)


@login_required(login_url='login')
def route_list_ajax(request, bus_pk):
    bus = get_object_or_404(Bus, pk=bus_pk)
    query = request.GET.get('q', '').strip()
    routes = BusRoute.objects.filter(bus=bus)
    if query:
        routes = routes.filter(
            Q(name__icontains=query) |
            Q(origin__icontains=query) |
            Q(destination__icontains=query)
        )
    page = Paginator(routes, 10).get_page(request.GET.get('page', 1))
    data = [{
        'id': route.pk,
        'name': route.name,
        'origin': route.origin,
        'destination': route.destination,
        'departure_time': route.departure_time.strftime('%H:%M') if route.departure_time else '',
        'arrival_time': route.arrival_time.strftime('%H:%M') if route.arrival_time else '',
        'fare': str(route.fare),
        'is_active': route.is_active,
    } for route in page.object_list]
    return JsonResponse({
        'data': data,
        'has_next': page.has_next(),
        'has_prev': page.has_previous(),
        'page': page.number,
        'pages': page.paginator.num_pages,
        'total': page.paginator.count,
    })


@login_required(login_url='login')
def route_get_ajax(request, bus_pk, pk):
    route = get_object_or_404(BusRoute, bus_id=bus_pk, pk=pk)
    return JsonResponse({
        'id': route.pk,
        'name': route.name,
        'origin': route.origin,
        'destination': route.destination,
        'departure_time': route.departure_time.strftime('%H:%M') if route.departure_time else '',
        'arrival_time': route.arrival_time.strftime('%H:%M') if route.arrival_time else '',
        'fare': str(route.fare),
        'is_active': route.is_active,
    })


@login_required(login_url='login')
@require_POST
def route_save_ajax(request, bus_pk):
    bus = get_object_or_404(Bus, pk=bus_pk)
    route_id = request.POST.get('id')
    route = get_object_or_404(BusRoute, bus=bus, pk=route_id) if route_id else BusRoute(bus=bus)
    form = BusRouteForm(request.POST, instance=route)
    if not form.is_valid():
        return JsonResponse({'error': _form_error(form)}, status=400)
    route = form.save(commit=False)
    route.bus = bus
    try:
        route.save()
    except IntegrityError:
        return JsonResponse({'error': 'That route name is already used for this bus.'}, status=400)
    messages.success(request, f'Route "{route.name}" was saved for bus {bus.fleet_number}.')
    return JsonResponse({'status': 'success', 'id': route.pk})


@login_required(login_url='login')
@require_POST
def route_delete_ajax(request, bus_pk, pk):
    bus = get_object_or_404(Bus, pk=bus_pk)
    route = get_object_or_404(BusRoute, bus=bus, pk=pk)
    route_name = route.name
    route.delete()
    messages.success(request, f'Route "{route_name}" was deleted.')
    return JsonResponse({'status': 'deleted'})