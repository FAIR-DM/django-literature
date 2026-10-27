# Depends on literature's first migration, as the upgrade guide tells a host
# project to, rather than on its latest.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('literature', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Citation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.ForeignKey(help_text='The reference this record cites.', on_delete=django.db.models.deletion.CASCADE, to='literature.item', verbose_name='reference')),
            ],
        ),
    ]
