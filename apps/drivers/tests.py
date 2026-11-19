from io import BytesIO
import os
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from django.test import TestCase
from django.urls import reverse

from apps.buses.models import Bus
from .models import Driver


class DriverCrudTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='driver-user', password='test-password')
        self.client.force_login(user)

    def make_photo(self, name):
        image_buffer = BytesIO()
        Image.new('RGB', (4, 4), color='purple').save(image_buffer, format='PNG')
        return SimpleUploadedFile(name, image_buffer.getvalue(), content_type='image/png')

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

    def test_driver_photo_upload_edit_retention_and_replacement(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            create_response = self.client.post(reverse('drivers:driver_save_ajax'), {
                'first_name': 'Taylor',
                'last_name': 'Morgan',
                'license_number': 'DL-PHOTO-01',
                'is_active': 'on',
                'profile_picture': self.make_photo('portrait.png'),
            })

            self.assertEqual(create_response.status_code, 200)
            driver = Driver.objects.get(pk=create_response.json()['id'])
            first_photo_name = driver.profile_picture.name
            self.assertTrue(os.path.isfile(os.path.join(media_root, first_photo_name)))
            self.assertIn('/media/driver_profiles/', create_response.json()['profile_picture_url'])

            edit_data = {
                'id': str(driver.pk),
                'first_name': 'Taylor',
                'last_name': 'Morgan',
                'license_number': 'DL-PHOTO-01',
                'is_active': 'on',
            }
            self.assertEqual(self.client.post(reverse('drivers:driver_save_ajax'), edit_data).status_code, 200)
            driver.refresh_from_db()
            self.assertEqual(driver.profile_picture.name, first_photo_name)

            edit_data['profile_picture'] = self.make_photo('new-portrait.png')
            replace_response = self.client.post(reverse('drivers:driver_save_ajax'), edit_data)
            driver.refresh_from_db()
            self.assertEqual(replace_response.status_code, 200)
            self.assertNotEqual(driver.profile_picture.name, first_photo_name)
            self.assertFalse(os.path.exists(os.path.join(media_root, first_photo_name)))
            self.assertTrue(os.path.isfile(os.path.join(media_root, driver.profile_picture.name)))
            self.assertContains(self.client.get(reverse('drivers:driver_list')), driver.profile_picture.url)