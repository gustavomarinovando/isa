# Generated by Django 5.2.1 on 2025-05-28 18:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indicator_manager', '0005_indicator_data_format_instructions'),
    ]

    operations = [
        migrations.CreateModel(
            name='RAATData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('area', models.CharField(db_index=True, max_length=255, verbose_name='Área/Materia')),
                ('grado', models.CharField(db_index=True, max_length=10, verbose_name='Grado')),
                ('paralelo', models.CharField(db_index=True, max_length=5, verbose_name='Paralelo')),
                ('estudiante', models.CharField(max_length=255, verbose_name='Estudiante')),
                ('profesor', models.CharField(max_length=255, verbose_name='Profesor')),
                ('ciclo', models.CharField(db_index=True, max_length=10, verbose_name='Ciclo')),
                ('periodo', models.IntegerField(db_index=True, verbose_name='Periodo')),
                ('year', models.IntegerField(db_index=True, verbose_name='Año')),
                ('indicator_source', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='raat_data_entries', to='indicator_manager.indicator', verbose_name='Indicador de Origen')),
            ],
            options={
                'verbose_name': 'Dato de RAAT',
                'verbose_name_plural': 'Datos de RAAT',
                'indexes': [models.Index(fields=['year', 'periodo', 'ciclo'], name='indicator_m_year_d077ba_idx'), models.Index(fields=['year', 'periodo', 'grado', 'paralelo'], name='indicator_m_year_7c2c7b_idx'), models.Index(fields=['year', 'periodo', 'area'], name='indicator_m_year_87f0b2_idx')],
            },
        ),
    ]
