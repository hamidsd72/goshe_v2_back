# Generated by Django 3.2.7 on 2021-12-02 23:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='birthDay',
            field=models.CharField(max_length=12, null=True, verbose_name='تاریخ تولد'),
        ),
    ]
