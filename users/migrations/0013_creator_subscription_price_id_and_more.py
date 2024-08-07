# Generated by Django 4.2 on 2024-07-02 04:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_remove_user_interests_spectator_interests'),
    ]

    operations = [
        migrations.AddField(
            model_name='creator',
            name='subscription_price_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='spectator',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
