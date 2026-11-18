import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.buses.models import Bus
from apps.transactions.models import Transaction
from .forms import ReportFilterForm


def _report_data(start_date, end_date):
    trip_filter = Q(
        transactions__created_at__date__gte=start_date,
        transactions__created_at__date__lte=end_date,
    )
    completed_filter = trip_filter & Q(transactions__status=Transaction.Status.COMPLETED)
    paid_filter = trip_filter & Q(transactions__payment_status=Transaction.PaymentStatus.PAID)

    transactions = Transaction.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )
    revenue = transactions.filter(
        payment_status=Transaction.PaymentStatus.PAID,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    completed_trips = transactions.filter(status=Transaction.Status.COMPLETED).count()

    active_fleet = Bus.objects.filter(status=Bus.Status.ACTIVE)
    active_count = active_fleet.count()
    utilized_count = active_fleet.annotate(
        trip_count=Count('transactions', filter=trip_filter),
    ).filter(trip_count__gt=0).count()
    utilization = round((utilized_count / active_count) * 100, 1) if active_count else 0

    generated_at = timezone.localtime()
    date_range = f'{start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}'
    report_rows = Bus.objects.annotate(
        total_trips=Count('transactions', filter=trip_filter),
        capacity_handled=Sum('capacity', filter=trip_filter),
        revenue_collected=Sum('transactions__amount', filter=paid_filter),
    ).order_by('fleet_number')
    rows = [{
        'report_id': f'RPT-{start_date:%Y%m%d}-{end_date:%Y%m%d}-BUS{bus.pk:04d}',
        'date_range': date_range,
        'generated_at': generated_at,
        'fleet_number': bus.fleet_number,
        'plate_number': bus.plate_number,
        'total_trips': bus.total_trips or 0,
        'capacity_handled': bus.capacity_handled or 0,
        'revenue_collected': bus.revenue_collected or Decimal('0.00'),
    } for bus in report_rows]

    return {
        'rows': rows,
        'revenue': revenue,
        'completed_trips': completed_trips,
        'utilization': utilization,
        'active_fleet_count': active_count,
        'utilized_fleet_count': utilized_count,
        'date_range': date_range,
        'generated_at': generated_at,
    }


def _filter_form(request):
    today = timezone.localdate()
    defaults = {
        'start_date': today.replace(day=1),
        'end_date': today,
    }
    if request.GET:
        return ReportFilterForm(request.GET, initial=defaults)
    return ReportFilterForm(initial=defaults)


@login_required(login_url='login')
def report_list(request):
    form = _filter_form(request)
    if form.is_bound and form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    else:
        start_date = form.initial.get('start_date')
        end_date = form.initial.get('end_date')
    report = _report_data(start_date, end_date)
    return render(request, 'reports/list.html', {
        'form': form,
        'report': report,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required(login_url='login')
def report_export(request):
    form = _filter_form(request)
    if not form.is_valid():
        return HttpResponse('Please provide a valid date range.', status=400, content_type='text/plain')

    start_date = form.cleaned_data['start_date']
    end_date = form.cleaned_data['end_date']
    report = _report_data(start_date, end_date)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="waybill-report-{start_date:%Y%m%d}-{end_date:%Y%m%d}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Waybill Management System Report', report['date_range']])
    writer.writerow(['Total Revenue (PHP)', f"{report['revenue']:.2f}"])
    writer.writerow(['Completed Trips', report['completed_trips']])
    writer.writerow(['Active Fleet Utilization', f"{report['utilization']:.1f}%"])
    writer.writerow([])
    writer.writerow([
        'Report ID / Reference', 'Date Range', 'Generated Date', 'Fleet No.',
        'Plate No.', 'Total Trips Made', 'Capacity Handled', 'Revenue Collected (PHP)',
    ])
    for row in report['rows']:
        writer.writerow([
            row['report_id'],
            row['date_range'],
            row['generated_at'].strftime('%Y-%m-%d %H:%M'),
            row['fleet_number'],
            row['plate_number'],
            row['total_trips'],
            row['capacity_handled'],
            f"{row['revenue_collected']:.2f}",
        ])
    return response