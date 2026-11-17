from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('fleet', '0001_initial'),
        ('buses', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='BusRoute'),
                migrations.DeleteModel(name='Bus'),
                migrations.DeleteModel(name='Driver'),
            ],
        ),
    ]