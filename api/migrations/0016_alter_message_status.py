# Generated by Django 3.2.7 on 2021-12-29 23:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_category_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='status',
            field=models.BooleanField(default=True, verbose_name='هنوز ندیده'),
        ),
    ]