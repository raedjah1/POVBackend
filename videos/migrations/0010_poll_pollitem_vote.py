# Generated by Django 4.2 on 2024-08-02 03:24

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_badge_userbadge'),
        ('videos', '0009_vision_search_vector_remove_comment_likes_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='PollItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255)),
                ('votes', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='videos.poll')),
            ],
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('poll_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes_cast', to='videos.pollitem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.user')),
            ],
            options={
                'unique_together': {('poll_item', 'user')},
            },
        ),
    ]
