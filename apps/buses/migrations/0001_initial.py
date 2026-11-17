import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('drivers', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='Bus',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('fleet_number', models.CharField(max_length=30, unique=True)),
                        ('plate_number', models.CharField(max_length=20, unique=True)),
                        ('capacity', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                        ('status', models.CharField(choices=[('active', 'Active'), ('maintenance', 'Maintenance'), ('inactive', 'Inactive')], default='active', max_length=20)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('driver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='buses', to='drivers.driver')),
                    ],
                    options={
                        'db_table': 'fleet_bus',
                        'ordering': ['fleet_number'],
                    },
                ),
                migrations.CreateModel(
                    name='BusRoute',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100)),
                        ('origin', models.CharField(max_length=120)),
                        ('destination', models.CharField(max_length=120)),
                        ('departure_time', models.TimeField(blank=True, null=True)),
                        ('arrival_time', models.TimeField(blank=True, null=True)),
                        ('fare', models.DecimalField(decimal_places=2, default=0, max_digits=8, validators=[django.core.validators.MinValueValidator(0)])),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('bus', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='routes', to='buses.bus')),
                    ],
                    options={
                        'db_table': 'fleet_busroute',
                        'ordering': ['name'],
                        'constraints': [models.UniqueConstraint(fields=('bus', 'name'), name='fleet_bus_route_name_uniq')],
                    },
                ),
            ],
        ),
    ]