# Generated by Django 3.2.7 on 2021-12-10 17:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_auto_20211210_0424'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='status',
        ),
    ]
