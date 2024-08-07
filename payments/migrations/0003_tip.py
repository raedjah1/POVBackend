# Generated by Django 4.2 on 2024-07-26 03:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0009_vision_search_vector_remove_comment_likes_and_more'),
        ('users', '0015_creator_search_vector_and_more'),
        ('payments', '0002_remove_transaction_user_transaction_from_user_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField()),
                ('message', models.TextField(blank=True, null=True)),
                ('comment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='videos.comment')),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tips_received', to='users.creator')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tips_given', to='users.user')),
            ],
        ),
    ]
