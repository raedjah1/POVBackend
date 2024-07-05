# Generated by Django 4.2 on 2024-07-03 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_creator_subscription_price_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='sign_in_method',
            field=models.CharField(choices=[('apple', 'Apple'), ('google', 'Google'), ('facebook', 'Facebook'), ('email', 'Email')], default='email', max_length=10),
        ),
    ]
