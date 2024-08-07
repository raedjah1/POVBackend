# Generated by Django 4.2 on 2024-06-27 14:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('thumbnail', models.URLField(max_length=500, null=True)),
                ('views', models.IntegerField(default=0)),
                ('url', models.URLField(max_length=500, null=True)),
                ('likes', models.IntegerField(default=0)),
                ('description', models.TextField()),
                ('live', models.BooleanField(default=False)),
                ('aspect_ratio', models.CharField(blank=True, default='', max_length=4, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='users.creator')),
                ('interests', models.ManyToManyField(blank=True, to='users.interest')),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('likes', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('parent_comment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='videos.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.user')),
                ('vision', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='videos.vision')),
            ],
        ),
    ]
