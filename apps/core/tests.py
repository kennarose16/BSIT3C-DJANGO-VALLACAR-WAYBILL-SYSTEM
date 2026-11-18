from decimal import Decimal

import re

from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.buses.models import Bus
from apps.transactions.models import Transaction


class HomeViewTests(TestCase):
    def test_home_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(username='admin', password='secret1234')

        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, '<turbo-frame id="main-content"')
        self.assertContains(response, 'data-turbo-action="advance"')
        users_url = reverse('users:user_list')
        self.assertContains(
            response,
            f'href="{users_url}" data-turbo-frame="main-content"',
            html=False,
        )

    def test_home_requires_login(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_uses_dashboard_url(self):
        self.assertEqual(reverse('dashboard'), '/dashboard/')

    def test_login_page_has_forgot_password_link(self):
        response = self.client.get(reverse('login'))

        self.assertContains(response, reverse('password_reset'))
        self.assertContains(response, 'Forgot password?')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_email_can_change_password(self):
        user = get_user_model().objects.create_user(
            username='reset-user',
            email='reset@example.com',
            password='old-password-123',
        )

        response = self.client.post(reverse('password_reset'), {'email': user.email})

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        reset_url = re.search(r'http://testserver(/reset/[^\s]+)', mail.outbox[0].body).group(1)
        reset_response = self.client.get(reset_url, follow=True)
        self.assertTemplateUsed(reset_response, 'auth/password_reset_confirm.html')

        new_password = 'BrandNew-Unique-Password-482!'
        complete_response = self.client.post(reset_response.request['PATH_INFO'], {
            'new_password1': new_password,
            'new_password2': new_password,
        })

        self.assertRedirects(complete_response, reverse('password_reset_complete'))
        user.refresh_from_db()
        self.assertTrue(check_password(new_password, user.password))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_response_does_not_disclose_unknown_email(self):
        response = self.client.post(reverse('password_reset'), {'email': 'unknown@example.com'})

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_dashboard_summarizes_today_transactions(self):
        user = get_user_model().objects.create_user(username='dispatcher', password='secret1234')
        self.client.force_login(user)
        bus = Bus.objects.create(
            fleet_number='DASH-01',
            plate_number='DASH-001',
            capacity=20,
        )
        transaction = Transaction.objects.create(
            bus=bus,
            sender_name='Sender',
            receiver_name='Receiver',
            destination='Manila',
            amount=Decimal('375.50'),
            payment_status=Transaction.PaymentStatus.PAID,
            status=Transaction.Status.COMPLETED,
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['trips_today'], 1)
        self.assertEqual(response.context['completed_trips_today'], 1)
        self.assertEqual(response.context['revenue_today'], Decimal('375.50'))
        self.assertContains(response, transaction.transaction_id)
