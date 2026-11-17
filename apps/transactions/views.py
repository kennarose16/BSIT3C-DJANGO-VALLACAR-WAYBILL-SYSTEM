from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.buses.models import Bus, BusRoute
from .forms import TransactionForm
from .models import Transaction
from .pricing import DESTINATION_PRESETS, rate_multiplier


def _transaction_data(transaction):
    return {
        'id': transaction.pk,
        'transaction_id': transaction.transaction_id,
        'fleet_number': transaction.bus.fleet_number,
        'plate_number': transaction.bus.plate_number,
        'sender_name': transaction.sender_name,
        'receiver_name': transaction.receiver_name,
        'destination': transaction.destination,
        'amount': str(transaction.amount) if transaction.amount is not None else '',
        'payment_status': transaction.payment_status,
        'payment_status_display': transaction.get_payment_status_display(),
        'status': transaction.status,
        'status_display': transaction.get_status_display(),
        'detail_url': reverse('transactions:transaction_detail', args=[transaction.pk]),
        'receipt_url': reverse('transactions:transaction_detail', args=[transaction.pk]),
        'print_url': f"{reverse('transactions:transaction_detail', args=[transaction.pk])}?print=1",
        'mark_paid_url': reverse('transactions:transaction_mark_paid', args=[transaction.pk]),
        'delete_url': reverse('transactions:transaction_delete', args=[transaction.pk]),
    }


def _summary_data():
    summary = Transaction.objects.aggregate(
        total=Count('pk'),
        revenue=Sum('amount', filter=Q(payment_status=Transaction.PaymentStatus.PAID)),
        pending=Sum('amount', filter=Q(payment_status__in=[
            Transaction.PaymentStatus.UNPAID,
            Transaction.PaymentStatus.PENDING,
        ])),
    )
    return {
        'total': summary['total'] or 0,
        'revenue': format(summary['revenue'] or 0, '.2f'),
        'pending': format(summary['pending'] or 0, '.2f'),
    }


def _form_error(form):
    errors = []
    for field_name, field_errors in form.errors.items():
        label = form.fields[field_name].label if field_name in form.fields else ''
        errors.extend(f'{label}: {error}' if label else str(error) for error in field_errors)
    return ' '.join(errors)


@login_required(login_url='login')
def transaction_list(request):
    query = request.GET.get('q', '').strip()
    payment_status = request.GET.get('payment_status', '').strip()
    trip_status = request.GET.get('trip_status', '').strip()
    transactions = Transaction.objects.select_related('bus').all()
    valid_payment_statuses = {choice[0] for choice in Transaction.PaymentStatus.choices}
    valid_trip_statuses = {choice[0] for choice in Transaction.Status.choices}
    if payment_status in valid_payment_statuses:
        transactions = transactions.filter(payment_status=payment_status)
    else:
        payment_status = ''
    if trip_status in valid_trip_statuses:
        transactions = transactions.filter(status=trip_status)
    else:
        trip_status = ''
    if query:
        filters = (
            Q(bus__fleet_number__icontains=query) |
            Q(bus__plate_number__icontains=query) |
            Q(sender_name__icontains=query) |
            Q(receiver_name__icontains=query) |
            Q(destination__icontains=query)
        )
        transaction_number = query.upper().removeprefix('TXN-').removeprefix('WB-').lstrip('0')
        if transaction_number.isdigit():
            filters |= Q(pk=int(transaction_number))
        transactions = transactions.filter(filters)
    return render(request, 'transactions/list.html', {
        'transactions': transactions,
        'query': query,
        'selected_payment_status': payment_status,
        'selected_trip_status': trip_status,
        'payment_status_choices': Transaction.PaymentStatus.choices,
        'trip_status_choices': Transaction.Status.choices,
        'summary': _summary_data(),
        'rate_multiplier': rate_multiplier(),
        'form': TransactionForm(),
    })


@login_required(login_url='login')
@require_POST
def transaction_create_ajax(request):
    form = TransactionForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': _form_error(form)}, status=400)
    transaction = form.save()
    return JsonResponse({
        'status': 'success',
        'transaction': _transaction_data(transaction),
        'summary': _summary_data(),
    })


@login_required(login_url='login')
def transaction_bus_data(request, bus_pk):
    bus = get_object_or_404(Bus, pk=bus_pk)
    routes = BusRoute.objects.filter(bus=bus).order_by('destination', 'name')
    return JsonResponse({
        'plate_number': bus.plate_number,
        'capacity': bus.capacity,
        'rate_multiplier': str(rate_multiplier()),
        'presets': [{
            'key': key,
            'name': item['name'],
            'base_fare': str(item['base_fare']),
        } for key, item in DESTINATION_PRESETS.items()],
        'routes': [{
            'id': route.pk,
            'destination': route.destination,
            'name': route.name,
            'base_fare': str(route.fare),
        } for route in routes],
    })


@login_required(login_url='login')
@require_POST
def transaction_mark_paid(request, pk):
    transaction = get_object_or_404(Transaction.objects.select_related('bus'), pk=pk)
    transaction.payment_status = Transaction.PaymentStatus.PAID
    transaction.save(update_fields=['payment_status'])
    return JsonResponse({
        'status': 'success',
        'transaction': _transaction_data(transaction),
        'summary': _summary_data(),
    })


@login_required(login_url='login')
@require_POST
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    transaction.delete()
    return JsonResponse({'status': 'deleted', 'summary': _summary_data()})


@login_required(login_url='login')
def transaction_detail(request, pk):
    transaction = get_object_or_404(
        Transaction.objects.select_related('bus'),
        pk=pk,
    )
    return render(request, 'transactions/detail.html', {
        'transaction': transaction,
        'auto_print': request.GET.get('print') == '1',
    })
