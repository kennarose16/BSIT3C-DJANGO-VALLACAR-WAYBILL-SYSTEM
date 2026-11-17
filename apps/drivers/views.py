from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DriverForm
from .models import Driver


@login_required(login_url='login')
def driver_list(request):
    query = request.GET.get('q', '').strip()
    drivers = Driver.objects.prefetch_related('buses')
    if query:
        drivers = drivers.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(license_number__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(email__icontains=query)
        )
    page = Paginator(drivers, 10).get_page(request.GET.get('page', 1))
    return render(request, 'fleet/driver_list.html', {'drivers': page, 'query': query})


@login_required(login_url='login')
def driver_form(request, pk=None):
    driver = get_object_or_404(Driver, pk=pk) if pk else None
    form = DriverForm(request.POST if request.method == 'POST' else None, instance=driver)
    if request.method == 'POST' and form.is_valid():
        saved_driver = form.save()
        messages.success(request, f'Driver "{saved_driver}" was saved.')
        return redirect('drivers:driver_list')
    return render(request, 'fleet/form.html', {
        'form': form,
        'title': 'Edit driver' if driver else 'Add driver',
        'cancel_url': '/drivers/',
    })


@login_required(login_url='login')
@require_POST
def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    name = str(driver)
    driver.delete()
    messages.success(request, f'Driver "{name}" was deleted. Assigned buses are now unassigned.')
    return redirect('drivers:driver_list')


@login_required(login_url='login')
def driver_list_ajax(request):
    query = request.GET.get('q', '').strip()
    drivers = Driver.objects.all()
    if query:
        drivers = drivers.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(license_number__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(email__icontains=query)
        )
    page = Paginator(drivers, 10).get_page(request.GET.get('page', 1))
    return JsonResponse({
        'data': list(page.object_list.values(
            'id', 'first_name', 'last_name', 'license_number', 'phone_number', 'email', 'is_active'
        )),
        'has_next': page.has_next(),
        'has_prev': page.has_previous(),
        'page': page.number,
        'pages': page.paginator.num_pages,
        'total': page.paginator.count,
    })


@login_required(login_url='login')
def driver_get_ajax(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    return JsonResponse({
        'id': driver.pk,
        'first_name': driver.first_name,
        'last_name': driver.last_name,
        'license_number': driver.license_number,
        'phone_number': driver.phone_number,
        'email': driver.email,
        'is_active': driver.is_active,
    })


def _form_error(form):
    errors = []
    for field_name, field_errors in form.errors.items():
        label = form.fields[field_name].label if field_name in form.fields else ''
        errors.extend(f'{label}: {error}' if label else str(error) for error in field_errors)
    return ' '.join(errors)


@login_required(login_url='login')
@require_POST
def driver_save_ajax(request):
    driver_id = request.POST.get('id')
    driver = get_object_or_404(Driver, pk=driver_id) if driver_id else Driver()
    form = DriverForm(request.POST, instance=driver)
    if not form.is_valid():
        return JsonResponse({'error': _form_error(form)}, status=400)
    try:
        driver = form.save()
    except IntegrityError:
        return JsonResponse({'error': 'That license number is already in use.'}, status=400)
    messages.success(request, f'Driver "{driver}" was saved.')
    return JsonResponse({'status': 'success', 'id': driver.pk})


@login_required(login_url='login')
@require_POST
def driver_delete_ajax(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    name = str(driver)
    driver.delete()
    messages.success(request, f'Driver "{name}" was deleted. Assigned buses are now unassigned.')
    return JsonResponse({'status': 'deleted'})