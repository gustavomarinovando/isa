from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re
import datetime

class Month(models.Model):
    SPANISH_MONTH_CHOICES = [
        (1, _('Enero')), (2, _('Febrero')), (3, _('Marzo')), (4, _('Abril')),
        (5, _('Mayo')), (6, _('Junio')), (7, _('Julio')), (8, _('Agosto')),
        (9, _('Septiembre')), (10, _('Octubre')), (11, _('Noviembre')), (12, _('Diciembre')),
    ]
    number = models.PositiveSmallIntegerField(primary_key=True, choices=SPANISH_MONTH_CHOICES, verbose_name=_("Número de Mes"), help_text=_("Mes (1=Enero, 12=Diciembre)"))
    def __str__(self): return self.get_number_display()
    class Meta: ordering = ['number']; verbose_name = _("Mes"); verbose_name_plural = _("Meses")

class AcademicObjective(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Nombre del Objetivo"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))
    def __str__(self): return self.name
    class Meta: ordering = ['name']; verbose_name = _("Objetivo Académico"); verbose_name_plural = _("Objetivos Académicos")

class SGCObjective(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Nombre del Objetivo SGC"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción SGC"))
    def __str__(self): return self.name
    class Meta: ordering = ['name']; verbose_name = _("Objetivo SGC"); verbose_name_plural = _("Objetivos SGC")

class Indicator(models.Model):
    number = models.PositiveIntegerField(unique=True, verbose_name=_("Número de KPI"), help_text=_("El número oficial (1-68) que identifica este KPI."))
    name = models.CharField(max_length=500, verbose_name=_("Nombre Corto / Título"), help_text=_("El nombre corto o título del KPI."))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción Detallada"), help_text=_("Descripción explicando el KPI, su propósito y método de cálculo."))
    shown_to_board = models.BooleanField(default=False, verbose_name=_("Mostrar a la Junta Directiva"))
    academic_objective = models.ForeignKey(AcademicObjective, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpis', verbose_name=_("Objetivo Académico Relacionado"))
    sgc_objective = models.ForeignKey(SGCObjective, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpis', verbose_name=_("Objetivo SGC Relacionado"))
    review_months = models.ManyToManyField(Month, blank=True, verbose_name=_("Meses de Revisión"), help_text=_("Seleccione los meses en que este KPI debe ser revisado/reportado."))
    responsible_persons = models.ManyToManyField( User, blank=True, related_name='responsible_kpis', verbose_name=_("Personas Responsables"), help_text=_("Personas responsables de la revisión y reporte del KPI."))
    powerbi_url_token = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Power BI Embed ID/Token"), help_text=_("Solo el ID/Token de embed para Power BI (ej: eyJrI...). Si pega la URL completa, se intentará extraer el token."))
    local_dash_url = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("URL de Dashboard Local/Alternativo"), help_text=_("Ruta relativa (ej: /dashboard/kpi1) o URL completa para dashboards no Power BI."))
    external_file_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name=_("URL de Archivo Externo (Imagen/Documento)"), help_text=_("URL directa a una imagen o documento relevante para el KPI."))
    data_ingestion_model_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Modelo Destino para Datos"), help_text=_("Nombre de la clase del modelo Django (ej: 'AttendanceData') donde se ingestarían los datos para este KPI."))
    data_format_instructions = models.TextField(blank=True, null=True, verbose_name=_("Instrucciones de Formato de Datos"), help_text=_("Describa el formato esperado del archivo a subir (columnas, tipos de datos, etc.) para la ingesta de datos."))
    def __str__(self): return f"KPI {self.number}: {self.name}"
    def clean(self):
        super().clean()
        if self.powerbi_url_token:
            self.powerbi_url_token = self.powerbi_url_token.strip()
            if ' ' in self.powerbi_url_token: raise ValidationError({'powerbi_url_token': _("El Power BI URL/Token no puede contener espacios.")})
            match = re.search(r'(?:[?&]r=)([^&"\']+)', self.powerbi_url_token)
            is_likely_direct_token = (len(self.powerbi_url_token) > 50 and (self.powerbi_url_token.startswith("ey") or ("http" not in self.powerbi_url_token and "/" not in self.powerbi_url_token and "." not in self.powerbi_url_token)))
            if not is_likely_direct_token and match: self.powerbi_url_token = match.group(1)
            elif not is_likely_direct_token and not match:
                if 'app.powerbi.com' in self.powerbi_url_token or 'app.fabric.microsoft.com' in self.powerbi_url_token: raise ValidationError({'powerbi_url_token': _("Formato de Power BI URL no válido o token 'r=' no encontrado. Ingrese solo el token o la URL completa con 'r=TOKEN_AQUI'.")})
    class Meta: ordering = ['number']; verbose_name = _("Indicador (KPI)"); verbose_name_plural = _("Indicadores (KPIs)")
    @property
    def review_months_display(self):
        if self.review_months.exists(): return ", ".join([month.get_number_display() for month in self.review_months.all().order_by('number')])
        return _("No especificado")
    @property
    def next_or_current_review_month_display(self):
        if not self.review_months.exists(): return _("No especificado")
        current_month_number = datetime.date.today().month
        all_review_month_numbers = sorted([m.number for m in self.review_months.all()])
        future_months_current_year = [m_num for m_num in all_review_month_numbers if m_num >= current_month_number]
        display_month_number = min(future_months_current_year) if future_months_current_year else (min(all_review_month_numbers) if all_review_month_numbers else None)
        if display_month_number is not None:
            try: return Month.objects.get(number=display_month_number).get_number_display()
            except Month.DoesNotExist: return _("Error Mes")
        return _("No especificado")
    @property
    def has_dashboard(self): return bool(self.powerbi_url_token and self.powerbi_url_token.strip()) or bool(self.local_dash_url and self.local_dash_url.strip()) or bool(self.external_file_url and self.external_file_url.strip())
    @property
    def full_powerbi_url(self):
        if self.powerbi_url_token and self.powerbi_url_token.strip(): return f"https://app.fabric.microsoft.com/view?r={self.powerbi_url_token.strip()}"
        return None
    @property
    def dashboard_url(self): 
        if self.local_dash_url and self.local_dash_url.strip(): return self.local_dash_url.strip()
        if self.full_powerbi_url: return self.full_powerbi_url
        if self.external_file_url and self.external_file_url.strip(): return self.external_file_url.strip()
        return None

class IndicatorChangeLog(models.Model):
    ACTION_CHOICES = [('CREATED', _('Creado')), ('UPDATED', _('Actualizado')), ('BULK_UPLOADED', _('Carga Masiva')), ('DELETED', _('Eliminado'))]
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name='change_logs', verbose_name=_("Indicador"))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Usuario"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha y Hora"))
    action_type = models.CharField(max_length=15, choices=ACTION_CHOICES, verbose_name=_("Tipo de Acción"))
    changed_data = models.JSONField(null=True, blank=True, verbose_name=_("Datos Modificados")) 
    def __str__(self): return f"{self.get_action_type_display()} en '{self.indicator.name}' por {self.user.username if self.user else 'Sistema'} a las {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    class Meta: ordering = ['-timestamp']; verbose_name = _("Registro de Cambio de Indicador"); verbose_name_plural = _("Registros de Cambios de Indicadores")

class RAATData(models.Model):
    indicator_source = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name='raat_data_entries', verbose_name=_("Indicador de Origen"), null=True, blank=True) # Optional link back to the specific Indicator instance
    area = models.CharField(max_length=255, db_index=True, verbose_name=_("Área/Materia"))
    grado = models.CharField(max_length=10, db_index=True, verbose_name=_("Grado")) # e.g., "3S", "6P"
    paralelo = models.CharField(max_length=5, db_index=True, verbose_name=_("Paralelo")) # e.g., "A", "B"
    estudiante = models.CharField(max_length=255, verbose_name=_("Estudiante"))
    profesor = models.CharField(max_length=255, verbose_name=_("Profesor"))
    ciclo = models.CharField(max_length=10, db_index=True, verbose_name=_("Ciclo")) # e.g., "PRO", "PRE"
    periodo = models.IntegerField(db_index=True, verbose_name=_("Periodo")) # e.g., 1, 2, 3
    year = models.IntegerField(db_index=True, verbose_name=_("Año")) # e.g., 2025

    def __str__(self):
        return f"{self.estudiante} - {self.area} ({self.grado}{self.paralelo}) - P{self.periodo}, {self.year}"

    class Meta:
        verbose_name = _("Dato de RAAT")
        verbose_name_plural = _("Datos de RAAT")
        # Combined indexes for common query patterns
        indexes = [
            models.Index(fields=['year', 'periodo', 'ciclo']),
            models.Index(fields=['year', 'periodo', 'grado', 'paralelo']),
            models.Index(fields=['year', 'periodo', 'area']),
        ]