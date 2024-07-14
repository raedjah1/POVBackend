# Generated by Django 4.0.4 on 2024-07-14 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='interests',
        ),
        migrations.AddField(
            model_name='spectator',
            name='interests',
            field=models.ManyToManyField(blank=True, to='users.interest'),
        ),
    ]