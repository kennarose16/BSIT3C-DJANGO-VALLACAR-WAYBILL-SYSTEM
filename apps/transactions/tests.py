from io import BytesIO
import os
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.buses.models import Bus, BusRoute
from apps.transactions.models import Transaction


class TransactionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='transaction-user', password='test-password')
        self.client.force_login(user)
        self.bus = Bus.objects.create(
            fleet_number='BUS-TX-01',
            plate_number='TX-101',
            capacity=30,
        )
        self.route = BusRoute.objects.create(
            bus=self.bus,
            name='North route',
            origin='Central Terminal',
            destination='North Terminal',
            fare='100.00',
        )

    def make_proof_image(self, name='proof.png'):
        image_buffer = BytesIO()
        Image.new('RGB', (2, 2), color='blue').save(image_buffer, format='PNG')
        return SimpleUploadedFile(name, image_buffer.getvalue(), content_type='image/png')

    def test_create_transaction_returns_table_data_and_persists(self):
        response = self.client.post(reverse('transactions:transaction_create_ajax'), {
            'bus': self.bus.pk,
            'destination': 'North Terminal',
            'sender_name': 'Alex Sender',
            'receiver_name': 'Taylor Receiver',
            'payment_status': Transaction.PaymentStatus.UNPAID,
            'status': Transaction.Status.IN_TRANSIT,
        })

        self.assertEqual(response.status_code, 200)
        transaction = Transaction.objects.get(pk=response.json()['transaction']['id'])
        self.assertEqual(transaction.bus, self.bus)
        self.assertEqual(transaction.route, self.route)
        self.assertEqual(transaction.destination, 'North Terminal')
        self.assertEqual(str(transaction.amount), '800.00')
        self.assertEqual(transaction.payment_status, Transaction.PaymentStatus.UNPAID)
        self.assertEqual(response.json()['transaction']['transaction_id'], f'TXN-{transaction.pk:06d}')
        self.assertEqual(response.json()['transaction']['status_display'], 'In Transit')

    def test_manual_destination_calculates_amount_and_accepts_override(self):
        response = self.client.post(reverse('transactions:transaction_create_ajax'), {
            'bus': self.bus.pk,
            'destination': 'Manila',
            'sender_name': 'Alex Sender',
            'receiver_name': 'Taylor Receiver',
            'payment_status': Transaction.PaymentStatus.UNPAID,
            'status': Transaction.Status.PENDING,
        })

        self.assertEqual(response.status_code, 200)
        transaction = Transaction.objects.get(pk=response.json()['transaction']['id'])
        self.assertEqual(transaction.destination, 'Manila')
        self.assertIsNone(transaction.route)
        self.assertEqual(str(transaction.amount), '800.00')
        list_response = self.client.get(reverse('transactions:transaction_list'))
        self.assertContains(list_response, 'Manila')
        self.assertContains(list_response, '800.00')

        override_response = self.client.post(reverse('transactions:transaction_create_ajax'), {
            'bus': self.bus.pk,
            'destination': 'Cebu City',
            'sender_name': 'Jordan Sender',
            'receiver_name': 'Morgan Receiver',
            'amount': '300.50',
            'payment_status': Transaction.PaymentStatus.UNPAID,
            'status': Transaction.Status.PENDING,
        })

        self.assertEqual(override_response.status_code, 200)
        overridden = Transaction.objects.get(pk=override_response.json()['transaction']['id'])
        self.assertEqual(overridden.destination, 'Cebu City')
        self.assertEqual(str(overridden.amount), '300.50')

    def test_bus_data_returns_capacity_and_default_base_rate(self):
        response = self.client.get(reverse('transactions:transaction_bus_data', args=[self.bus.pk]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['capacity'], self.bus.capacity)
        self.assertEqual(data['plate_number'], self.bus.plate_number)
        self.assertEqual(data['default_base_rate'], '50.00')

    def test_transaction_form_uses_free_text_destination(self):
        response = self.client.get(reverse('transactions:transaction_list'))

        self.assertContains(response, 'id="id_destination"')
        self.assertContains(response, 'type="text" name="destination"')
        self.assertNotContains(response, 'id="id_destination_choice"')
        self.assertContains(response, 'Proof of Delivery')
        self.assertContains(response, 'Upload Proof')
        self.assertContains(response, 'id="proofLightboxFleet"')

    def test_search_and_status_filters(self):
        transaction = Transaction.objects.create(
            bus=self.bus,
            sender_name='Alex Sender',
            receiver_name='Taylor Receiver',
            destination='North Terminal',
            status=Transaction.Status.COMPLETED,
        )

        response = self.client.get(reverse('transactions:transaction_list'), {
            'q': 'North Terminal',
            'payment_status': Transaction.PaymentStatus.PENDING,
            'trip_status': Transaction.Status.COMPLETED,
        })

        self.assertContains(response, transaction.transaction_id)
        self.assertContains(response, 'North Terminal')
        self.assertEqual(len(response.context['transactions']), 1)

    def test_mark_paid_updates_payment_summary(self):
        transaction = Transaction.objects.create(
            bus=self.bus,
            sender_name='Alex Sender',
            receiver_name='Taylor Receiver',
            destination='North Terminal',
            amount='850.00',
            payment_status=Transaction.PaymentStatus.UNPAID,
        )

        response = self.client.post(reverse('transactions:transaction_mark_paid', args=[transaction.pk]))

        transaction.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(transaction.payment_status, Transaction.PaymentStatus.PAID)
        self.assertEqual(response.json()['summary']['revenue'], '850.00')
        self.assertEqual(response.json()['summary']['pending'], '0.00')

    def test_delete_transaction_updates_total(self):
        transaction = Transaction.objects.create(
            bus=self.bus,
            sender_name='Alex Sender',
            receiver_name='Taylor Receiver',
            destination='North Terminal',
        )

        response = self.client.post(reverse('transactions:transaction_delete', args=[transaction.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(pk=transaction.pk).exists())
        self.assertEqual(response.json()['summary']['total'], 0)

    def test_legacy_payments_page_redirects_to_transactions(self):
        response = self.client.get(reverse('payments:payment_list'))

        self.assertRedirects(response, reverse('transactions:transaction_list'))

    def test_bus_selector_includes_existing_non_active_buses(self):
        inactive_bus = Bus.objects.create(
            fleet_number='BUS-TX-02',
            plate_number='TX-102',
            capacity=25,
            status=Bus.Status.MAINTENANCE,
        )

        response = self.client.get(reverse('transactions:transaction_list'))

        self.assertContains(response, inactive_bus.fleet_number)
        self.assertContains(response, inactive_bus.plate_number)

    def test_transaction_details_and_print_view(self):
        transaction = Transaction.objects.create(
            bus=self.bus,
            sender_name='Alex Sender',
            receiver_name='Taylor Receiver',
            destination='North Terminal',
        )

        response = self.client.get(reverse('transactions:transaction_detail', args=[transaction.pk]))
        print_response = self.client.get(
            reverse('transactions:transaction_detail', args=[transaction.pk]),
            {'print': '1'},
        )

        self.assertContains(response, transaction.transaction_id)
        self.assertContains(print_response, 'window.print()')

    def test_create_transaction_saves_proof_and_marks_received(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('transactions:transaction_create_ajax'), {
                'bus': self.bus.pk,
                'destination': 'Manila',
                'sender_name': 'Alex Sender',
                'receiver_name': 'Taylor Receiver',
                'payment_status': Transaction.PaymentStatus.UNPAID,
                'status': Transaction.Status.IN_TRANSIT,
                'proof_image': self.make_proof_image(),
            })

            self.assertEqual(response.status_code, 200)
            transaction = Transaction.objects.get(pk=response.json()['transaction']['id'])
            self.assertTrue(transaction.proof_image)
            self.assertTrue(os.path.isfile(os.path.join(media_root, transaction.proof_image.name)))
            self.assertEqual(transaction.status, Transaction.Status.COMPLETED)
            self.assertIsNotNone(transaction.received_at)
            self.assertIn('/media/transaction_proofs/', response.json()['transaction']['proof_url'])
            table_response = self.client.get(reverse('transactions:transaction_list'))
            self.assertContains(table_response, 'data-fleet-number="BUS-TX-01"')
            self.assertContains(table_response, 'View proof photo')

    def test_existing_transaction_can_receive_proof_upload(self):
        transaction = Transaction.objects.create(
            bus=self.bus,
            sender_name='Alex Sender',
            receiver_name='Taylor Receiver',
            destination='Manila',
            status=Transaction.Status.IN_TRANSIT,
        )

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('transactions:transaction_proof_upload', args=[transaction.pk]),
                {'proof_image': self.make_proof_image('received.png')},
            )

        transaction.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(transaction.status, Transaction.Status.COMPLETED)
        self.assertIsNotNone(transaction.received_at)
        self.assertTrue(transaction.proof_image)
        self.assertEqual(response.json()['transaction']['receiver_name'], 'Taylor Receiver')
