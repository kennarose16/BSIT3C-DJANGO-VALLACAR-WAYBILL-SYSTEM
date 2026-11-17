import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('fleet', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='Driver',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('first_name', models.CharField(max_length=100)),
                        ('last_name', models.CharField(max_length=100)),
                        ('license_number', models.CharField(max_length=50, unique=True)),
                        ('phone_number', models.CharField(blank=True, max_length=30)),
                        ('email', models.EmailField(blank=True, max_length=254)),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        'db_table': 'fleet_driver',
                        'ordering': ['last_name', 'first_name'],
                    },
                ),
            ],
        ),
    ]