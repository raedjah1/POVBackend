# Generated by Django 4.2 on 2024-07-26 05:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_alter_event_vision'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='thumbnail',
            field=models.URLField(max_length=500, null=True),
        ),
    ]
