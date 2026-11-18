from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.buses.models import Bus
from apps.transactions.models import Transaction


class ReportTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='report-user', password='test-password')
        self.client.force_login(user)
        self.bus = Bus.objects.create(
            fleet_number='REPORT-01',
            plate_number='RP-001',
            capacity=20,
            status=Bus.Status.ACTIVE,
        )
        self.idle_bus = Bus.objects.create(
            fleet_number='REPORT-02',
            plate_number='RP-002',
            capacity=35,
            status=Bus.Status.ACTIVE,
        )
        today = timezone.localdate()
        self.current_trip = Transaction.objects.create(
            bus=self.bus,
            sender_name='Sender One',
            receiver_name='Receiver One',
            destination='Manila',
            amount=Decimal('500.00'),
            payment_status=Transaction.PaymentStatus.PAID,
            status=Transaction.Status.COMPLETED,
        )
        self.pending_trip = Transaction.objects.create(
            bus=self.bus,
            sender_name='Sender Two',
            receiver_name='Receiver Two',
            destination='Cebu City',
            amount=Decimal('300.00'),
            payment_status=Transaction.PaymentStatus.UNPAID,
        )
        yesterday = today - timedelta(days=1)
        Transaction.objects.filter(pk=self.current_trip.pk).update(
            created_at=timezone.make_aware(datetime.combine(today, time(10, 0))),
        )
        Transaction.objects.filter(pk=self.pending_trip.pk).update(
            created_at=timezone.make_aware(datetime.combine(yesterday, time(10, 0))),
        )

    def test_report_summaries_and_fleet_aggregates_follow_date_range(self):
        today = timezone.localdate()
        response = self.client.get(reverse('reports:report_list'), {
            'start_date': today.isoformat(),
            'end_date': today.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        report = response.context['report']
        self.assertEqual(report['revenue'], Decimal('500.00'))
        self.assertEqual(report['completed_trips'], 1)
        self.assertEqual(report['utilization'], 50.0)
        bus_row = next(row for row in report['rows'] if row['fleet_number'] == self.bus.fleet_number)
        self.assertEqual(bus_row['total_trips'], 1)
        self.assertEqual(bus_row['capacity_handled'], 20)
        self.assertEqual(bus_row['revenue_collected'], Decimal('500.00'))

    def test_csv_export_contains_filtered_summary_and_rows(self):
        today = timezone.localdate()
        response = self.client.get(reverse('reports:report_export'), {
            'start_date': today.isoformat(),
            'end_date': today.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('500.00', response.content.decode('utf-8-sig'))
        self.assertIn('REPORT-01', response.content.decode('utf-8-sig'))

    def test_invalid_or_reversed_date_range_is_reported(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        response = self.client.get(reverse('reports:report_list'), {
            'start_date': today.isoformat(),
            'end_date': yesterday.isoformat(),
        })

        self.assertContains(response, 'Start date must be on or before end date.')