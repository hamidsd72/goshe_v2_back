# Generated by Django 3.2.7 on 2021-12-12 23:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='slug',
            field=models.SlugField(max_length=100, null=True, unique=True, verbose_name='اسلاگ'),
        ),
    ]
