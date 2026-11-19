from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.buses.models import Bus
from .forms import ProofUploadForm, TransactionForm
from .models import Transaction
from .pricing import default_base_rate, rate_multiplier


def _transaction_data(transaction):
    return {
        'id': transaction.pk,
        'transaction_id': transaction.transaction_id,
        'fleet_number': transaction.bus.fleet_number,
        'plate_number': transaction.bus.plate_number,
        'driver_name': str(transaction.bus.driver) if transaction.bus.driver else '',
        'driver_photo_url': transaction.bus.driver.profile_picture.url if transaction.bus.driver and transaction.bus.driver.profile_picture else '',
        'sender_name': transaction.sender_name,
        'receiver_name': transaction.receiver_name,
        'destination': transaction.destination,
        'amount': str(transaction.amount) if transaction.amount is not None else '',
        'payment_status': transaction.payment_status,
        'payment_status_display': transaction.get_payment_status_display(),
        'status': transaction.status,
        'status_display': transaction.get_status_display(),
        'proof_url': transaction.proof_image.url if transaction.proof_image else '',
        'received_at': timezone.localtime(transaction.received_at).strftime('%b %d, %Y %H:%M') if transaction.received_at else '',
        'proof_upload_url': reverse('transactions:transaction_proof_upload', args=[transaction.pk]),
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
    transactions = Transaction.objects.select_related('bus__driver').all()
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
        'default_base_rate': default_base_rate(),
        'rate_multiplier': rate_multiplier(),
        'form': TransactionForm(),
    })


@login_required(login_url='login')
@require_POST
def transaction_create_ajax(request):
    form = TransactionForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'error': _form_error(form)}, status=400)
    transaction = form.save()
    return JsonResponse({
        'status': 'success',
        'transaction': _transaction_data(transaction),
        'summary': _summary_data(),
    })


@login_required(login_url='login')
@require_POST
def transaction_proof_upload(request, pk):
    transaction = get_object_or_404(Transaction.objects.select_related('bus'), pk=pk)
    form = ProofUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'error': _form_error(form)}, status=400)
    old_image = transaction.proof_image
    transaction.proof_image = form.cleaned_data['proof_image']
    transaction.status = Transaction.Status.COMPLETED
    transaction.received_at = timezone.now()
    transaction.save(update_fields=['proof_image', 'status', 'received_at'])
    if old_image and old_image.name != transaction.proof_image.name:
        old_image.delete(save=False)
    return JsonResponse({
        'status': 'success',
        'transaction': _transaction_data(transaction),
        'summary': _summary_data(),
    })


@login_required(login_url='login')
def transaction_bus_data(request, bus_pk):
    bus = get_object_or_404(Bus, pk=bus_pk)
    return JsonResponse({
        'plate_number': bus.plate_number,
        'capacity': bus.capacity,
        'rate_multiplier': str(rate_multiplier()),
        'default_base_rate': str(default_base_rate()),
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
    proof_image = transaction.proof_image
    transaction.delete()
    if proof_image:
        proof_image.delete(save=False)
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
