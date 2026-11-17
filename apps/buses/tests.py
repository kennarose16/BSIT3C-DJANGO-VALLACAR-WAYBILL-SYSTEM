from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.drivers.models import Driver
from .models import Bus, BusRoute


class BusCrudTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='bus-user', password='test-password')
        self.client.force_login(user)
        self.driver = Driver.objects.create(
            first_name='Jordan',
            last_name='Lee',
            license_number='DL-1001',
        )

    def test_bus_and_route_ajax_crud(self):
        self.assertContains(self.client.get(reverse('buses:bus_list')), 'id="busModal"')
        bus_response = self.client.post(reverse('buses:bus_save_ajax'), {
            'fleet_number': 'BUS-01',
            'plate_number': 'ABC-123',
            'capacity': '40',
            'driver': str(self.driver.pk),
            'status': Bus.Status.ACTIVE,
        })
        self.assertEqual(bus_response.status_code, 200)
        bus = Bus.objects.get(pk=bus_response.json()['id'])
        self.assertEqual(bus.driver, self.driver)
        self.assertEqual(
            self.client.get(reverse('buses:bus_get_ajax', args=[bus.pk])).json()['fleet_number'],
            'BUS-01',
        )

        route_response = self.client.post(reverse('buses:route_save_ajax', args=[bus.pk]), {
            'name': 'West Line',
            'origin': 'Central',
            'destination': 'West Terminal',
            'departure_time': '08:00',
            'fare': '90.00',
            'is_active': 'on',
        })
        self.assertEqual(route_response.status_code, 200)
        route = BusRoute.objects.get(pk=route_response.json()['id'])
        route_page = self.client.get(reverse('buses:route_list', args=[bus.pk]))
        self.assertContains(route_page, 'id="routeModal"')
        self.assertEqual(
            self.client.get(reverse('buses:route_list_ajax', args=[bus.pk])).json()['data'][0]['name'],
            'West Line',
        )
        self.assertEqual(
            self.client.get(reverse('buses:route_get_ajax', args=[bus.pk, route.pk])).json()['destination'],
            'West Terminal',
        )
        self.assertEqual(
            self.client.post(reverse('buses:route_delete_ajax', args=[bus.pk, route.pk])).json()['status'],
            'deleted',
        )
        self.assertEqual(
            self.client.post(reverse('buses:bus_delete_ajax', args=[bus.pk])).json()['status'],
            'deleted',
        )

    def test_bus_cannot_be_deleted_while_routes_exist(self):
        bus = Bus.objects.create(
            fleet_number='BUS-02',
            plate_number='XYZ-456',
            capacity=30,
            driver=self.driver,
        )
        BusRoute.objects.create(bus=bus, name='South Line', origin='Central', destination='South')

        response = self.client.post(reverse('buses:bus_delete_ajax', args=[bus.pk]))

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Bus.objects.filter(pk=bus.pk).exists())