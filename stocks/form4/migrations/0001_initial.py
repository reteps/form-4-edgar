# Generated by Django 3.1.2 on 2020-12-15 06:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('cik', models.CharField(max_length=20)),
                ('symbol', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Filing',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_filed', models.DateField()),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='form4.company')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('amount', models.FloatField()),
                ('price', models.FloatField()),
                ('added_stock', models.BooleanField()),
                ('code', models.CharField(max_length=1)),
                ('amount_after', models.FloatField()),
                ('filing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='form4.filing')),
            ],
        ),
        migrations.CreateModel(
            name='FilingNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('on_field', models.CharField(choices=[('P', 'price'), ('A', 'amount')], max_length=1)),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='form4.transaction')),
            ],
        ),
        migrations.CreateModel(
            name='Filer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('cik', models.CharField(max_length=20)),
                ('is_director', models.BooleanField()),
                ('is_officer', models.BooleanField()),
                ('is_ten_percent_owner', models.BooleanField()),
                ('is_other', models.BooleanField()),
                ('officer_title', models.CharField(max_length=200, null=True)),
                ('other_text', models.CharField(max_length=200, null=True)),
                ('filing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='form4.filing')),
            ],
        ),
    ]
