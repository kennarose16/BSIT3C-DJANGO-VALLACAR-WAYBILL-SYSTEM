from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.buses.models import Bus
from apps.drivers.models import Driver
from apps.payments.models import AutoPayment


@login_required(login_url='login')
def payment_list(request):
    if not AutoPayment.objects.exists():
        driver = Driver.objects.first()
        bus = Bus.objects.first()
        if driver:
            AutoPayment.objects.create(
                driver=driver,
                amount=2500,
                payment_method='Auto Debit',
                due_date=date.today(),
                frequency=AutoPayment.Frequency.MONTHLY,
                notes='Monthly salary payout',
            )
        if bus:
            AutoPayment.objects.create(
                bus=bus,
                amount=4800,
                payment_method='Auto Debit',
                due_date=date.today(),
                frequency=AutoPayment.Frequency.MONTHLY,
                notes='Fleet maintenance and fuel service',
            )

    for payment in AutoPayment.objects.filter(auto_pay=True, status='scheduled', due_date__lte=date.today()):
        payment.process_if_due()

    payments = AutoPayment.objects.select_related('driver', 'bus').order_by('-due_date')
    scheduled_total = payments.filter(status='scheduled').aggregate(total=Sum('amount'))['total'] or 0
    paid_total = payments.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'payments/list.html', {
        'payments': payments,
        'scheduled_total': scheduled_total,
        'paid_total': paid_total,
    })


@login_required(login_url='login')
@require_POST
def process_payments(request):
    processed = 0
    for payment in AutoPayment.objects.filter(auto_pay=True, status='scheduled', due_date__lte=date.today()):
        if payment.process_if_due():
            processed += 1

    if processed:
        messages.success(request, f'{processed} automatic payments were processed successfully.')
    else:
        messages.info(request, 'No scheduled automatic payments are due right now.')
    return redirect('payments:payment_list')
