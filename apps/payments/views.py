from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required(login_url='login')
def payment_list(request):
    return redirect('transactions:transaction_list')


@login_required(login_url='login')
def process_payments(request):
    return redirect('payments:payment_list')
