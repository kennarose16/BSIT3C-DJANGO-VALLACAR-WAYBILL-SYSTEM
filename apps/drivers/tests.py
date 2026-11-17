from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.buses.models import Bus
from .models import Driver


class DriverCrudTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='driver-user', password='test-password')
        self.client.force_login(user)

    def test_driver_ajax_crud_and_list_page(self):
        self.assertContains(self.client.get(reverse('drivers:driver_list')), 'id="driverModal"')
        response = self.client.post(reverse('drivers:driver_save_ajax'), {
            'first_name': 'Taylor',
            'last_name': 'Morgan',
            'license_number': 'DL-3003',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 200)
        driver = Driver.objects.get(pk=response.json()['id'])
        self.assertEqual(
            self.client.get(reverse('drivers:driver_get_ajax', args=[driver.pk])).json()['license_number'],
            'DL-3003',
        )
        self.assertEqual(
            self.client.get(reverse('drivers:driver_list_ajax')).json()['data'][0]['first_name'],
            'Taylor',
        )
        update_response = self.client.post(reverse('drivers:driver_save_ajax'), {
            'id': str(driver.pk),
            'first_name': 'Taylor',
            'last_name': 'Morgan',
            'license_number': 'DL-3003',
            'phone_number': '555-0303',
            'is_active': 'on',
        })
        self.assertEqual(update_response.status_code, 200)
        driver.refresh_from_db()
        self.assertEqual(driver.phone_number, '555-0303')

    def test_deleting_driver_unassigns_buses(self):
        driver = Driver.objects.create(first_name='Sam', last_name='Rivera', license_number='DL-2002')
        bus = Bus.objects.create(fleet_number='BUS-02', plate_number='XYZ-456', capacity=30, driver=driver)

        response = self.client.post(reverse('drivers:driver_delete_ajax', args=[driver.pk]))

        self.assertEqual(response.json()['status'], 'deleted')
        bus.refresh_from_db()
        self.assertIsNone(bus.driver)