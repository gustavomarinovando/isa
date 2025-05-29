from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse 
from django.views import generic 
from django.contrib.auth import login 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin 
from django.db.models import Q, Model, Count 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Indicator, Month, User, IndicatorChangeLog, RAATData 
from .forms import IndicatorFilterForm, CustomUserCreationForm, IndicatorDataUploadForm, RAATFilterForm # Added RAATFilterForm
import datetime
from django.contrib.auth import views as auth_views
from django import forms 
import json 
from django.contrib import messages 
from django.core.files.storage import FileSystemStorage 
import os 
from django.conf import settings 
from django.utils.encoding import force_str 
from django.utils.translation import gettext_lazy as _
import pandas as pd 
from django.db import transaction 
from django.http import HttpResponse, JsonResponse 


def get_chart_data(filters):
    base_queryset = RAATData.objects.filter(**filters)
    materia_data_qs = base_queryset.values('area').annotate(count=Count('id')).order_by('-count')
    materia_labels = [item['area'] for item in materia_data_qs]
    materia_counts = [item['count'] for item in materia_data_qs]
    grado_data_qs = base_queryset.values('grado').annotate(count=Count('id')).order_by('grado') 
    grado_labels = [item['grado'] for item in grado_data_qs]
    grado_counts = [item['count'] for item in grado_data_qs]
    ciclo_data_qs = base_queryset.values('ciclo').annotate(count=Count('id')).order_by('ciclo')
    ciclo_labels = [item['ciclo'] for item in ciclo_data_qs]
    ciclo_counts = [item['count'] for item in ciclo_data_qs]
    total_raat_count = base_queryset.count()
    return {
        "materia_labels": materia_labels, "materia_counts": materia_counts,
        "grado_labels": grado_labels, "grado_counts": grado_counts,
        "ciclo_labels": ciclo_labels, "ciclo_counts": ciclo_counts,
        "total_raat_count": total_raat_count,
    }

@login_required
def raat_dashboard_view(request):
    current_year = datetime.date.today().year
    # Query distinct years from data, ordered descending
    available_years_qs = RAATData.objects.values_list('year', flat=True).distinct().order_by('-year')
    available_years = [str(y) for y in available_years_qs]
    
    # Determine default year: current year if data exists, else most recent year with data, else current year
    default_year = str(current_year) if str(current_year) in available_years else (available_years[0] if available_years else str(current_year))
    
    # Determine default period: latest period for the default year, if any
    latest_period_with_data_qs = RAATData.objects.filter(year=int(default_year)).values_list('periodo', flat=True).order_by('-periodo')
    default_periodo = str(latest_period_with_data_qs.first()) if latest_period_with_data_qs.exists() else ''

    # Initialize form data with GET parameters or defaults
    form_initial_data = {
        'year': request.GET.get('year', default_year),
        'periodo': request.GET.get('periodo', default_periodo),
        'ciclo_local': request.GET.get('ciclo_local', ''), # For Materia chart filter
        'grado_local': request.GET.get('grado_local', ''),   # For Materia chart filter
    }
    filter_form = RAATFilterForm(form_initial_data) # Pass initial data to the form

    # Get query parameters from the (potentially updated by GET) form_initial_data
    query_year = int(form_initial_data['year']) if form_initial_data['year'] else None
    query_periodo = int(form_initial_data['periodo']) if form_initial_data['periodo'] else None
    query_ciclo_local = form_initial_data['ciclo_local']
    query_grado_local = form_initial_data['grado_local']

    # Base filters for database queries (Global: Year and Periodo)
    base_db_filters = {}
    if query_year: base_db_filters['year'] = query_year
    if query_periodo: base_db_filters['periodo'] = query_periodo

    # --- Chart 1: Cantidad total y por ciclo (Donut Chart & Table) ---
    # This chart is affected ONLY by global filters (Year, Periodo)
    ciclo_chart_filters = base_db_filters.copy() 
    ciclo_data_qs = RAATData.objects.filter(**ciclo_chart_filters)\
        .values('ciclo')\
        .annotate(count=Count('id'))\
        .order_by('ciclo') # Initial order, will be custom sorted for the table later
    
    ciclo_labels_from_db = []
    ciclo_counts_from_db = []
    # Define colors for cycles - can be expanded
    ciclo_color_map_view = { 
        'PRE': '#A1D99B', # Light Green
        'PRO': '#6BAED6', # Light Blue
        'EXP': '#FD8D3C', # Orange
        'INI': '#FFFFB3', # Light Yellow
        'PRI': '#FB8072', # Light Red/Pink
        'SEC': '#80B1D3', # Another Light Blue
        'N/A': '#D1D5DB', # Gray
    }

    temp_ciclo_data_map = {} # To hold data before custom sorting for the table
    for item in ciclo_data_qs:
        label = item['ciclo'] if item['ciclo'] else "N/A"
        count = item['count']
        # For the donut chart, order might not be critical, but we can build it consistently
        ciclo_labels_from_db.append(label)
        ciclo_counts_from_db.append(count)
        temp_ciclo_data_map[label] = count
            
    total_raat_count_for_period = sum(ciclo_counts_from_db)
    
    # Custom sort order for the table display
    custom_ciclo_order = ['PRE', 'PRO', 'EXP', 'INI', 'PRI', 'SEC', 'N/A'] # Add other cycles as needed
    ciclo_table_data = []
    
    # Data for Donut Chart (can use the order from DB or also apply custom sort if legend order matters)
    # For simplicity, using DB order for donut labels/counts here.
    # If specific order is needed for donut slices/legend, apply custom_ciclo_order to ciclo_labels_from_db and ciclo_counts_from_db too.
    final_ciclo_labels_for_donut = []
    final_ciclo_counts_for_donut = []

    for ciclo_key in custom_ciclo_order:
        if ciclo_key in temp_ciclo_data_map:
            count = temp_ciclo_data_map[ciclo_key]
            percentage = (count / total_raat_count_for_period * 100) if total_raat_count_for_period > 0 else 0
            ciclo_table_data.append({
                'ciclo': ciclo_key,
                'cantidad': count,
                'porcentaje': round(percentage),
                'color': ciclo_color_map_view.get(ciclo_key, '#CCCCCC') 
            })
            final_ciclo_labels_for_donut.append(ciclo_key)
            final_ciclo_counts_for_donut.append(count)

    # Handle cycles from DB not in custom_ciclo_order (append them at the end)
    for label, count in temp_ciclo_data_map.items():
        if label not in custom_ciclo_order:
            percentage = (count / total_raat_count_for_period * 100) if total_raat_count_for_period > 0 else 0
            ciclo_table_data.append({
                'ciclo': label,
                'cantidad': count,
                'porcentaje': round(percentage),
                'color': ciclo_color_map_view.get(label, '#CCCCCC')
            })
            if label not in final_ciclo_labels_for_donut: # Ensure not duplicated if already added
                 final_ciclo_labels_for_donut.append(label)
                 final_ciclo_counts_for_donut.append(count)


    # --- Chart 2: Cantidad de RAAT por materia (Vertical Bar) ---
    # This chart IS affected by local filters (Ciclo Local, Grado Local) in addition to global
    materia_chart_filters = base_db_filters.copy()
    if query_ciclo_local: materia_chart_filters['ciclo'] = query_ciclo_local
    if query_grado_local: materia_chart_filters['grado'] = query_grado_local
    
    materia_data_qs = RAATData.objects.filter(**materia_chart_filters)\
        .values('area')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:15] # Top 15 materias
    materia_labels = [item['area'] if item['area'] else _("N/A") for item in materia_data_qs]
    materia_counts = [item['count'] for item in materia_data_qs]

    # --- Chart 3: Cantidad por grado (Horizontal Bar) ---
    # This chart is affected ONLY by global filters (Year, Periodo).
    # **CORRECTION**: It should NOT be filtered by query_ciclo_local from the Materia chart's slicer.
    grado_chart_filters = base_db_filters.copy()
    # REMOVED: if query_ciclo_local: grado_chart_filters['ciclo'] = query_ciclo_local
    
    # Define the desired order for grados
    grado_order = ['1P','2P','3P','4P','5P','6P', '1S', '2S', '3S', '4S', '5S', '6S'] # Example order, adjust as needed
    
    grado_data_qs = RAATData.objects.filter(**grado_chart_filters)\
        .values('grado')\
        .annotate(count=Count('id'))
    
    # Convert QuerySet to a dictionary for easy lookup and ordering
    grado_data_dict = {item['grado']: item['count'] for item in grado_data_qs}
    
    grado_labels_ordered = []
    grado_counts_ordered = []
    for grado_key in grado_order:
        if grado_key in grado_data_dict and grado_data_dict[grado_key] > 0: # Only include grados with data
            grado_labels_ordered.append(grado_key)
            grado_counts_ordered.append(grado_data_dict[grado_key])
    
    # Optionally, add any grados from data_dict not in grado_order (e.g., 'N/A')
    for grado_db, count_db in grado_data_dict.items():
        if grado_db not in grado_labels_ordered and count_db > 0:
            grado_labels_ordered.append(grado_db if grado_db else _("N/A"))
            grado_counts_ordered.append(count_db)


    context = {
        'filter_form': filter_form,
        'chart_data_materia_labels_json': json.dumps(materia_labels),
        'chart_data_materia_counts_json': json.dumps(materia_counts),
        'chart_data_grado_labels_json': json.dumps(grado_labels_ordered),
        'chart_data_grado_counts_json': json.dumps(grado_counts_ordered),
        'chart_data_ciclo_labels_json': json.dumps(final_ciclo_labels_for_donut), # Use sorted for donut if desired
        'chart_data_ciclo_counts_json': json.dumps(final_ciclo_counts_for_donut), # Use sorted for donut if desired
        'chart_data_total_raat': total_raat_count_for_period,
        'ciclo_table_data': ciclo_table_data, # This is now custom sorted
        'ciclo_color_map_json': json.dumps(ciclo_color_map_view),
        'selected_year': query_year,
        'selected_periodo': query_periodo,
        'selected_ciclo_local': query_ciclo_local, 
        'selected_grado_local': query_grado_local,
        # Translations for chart labels (can be moved to template if preferred)
        'label_cantidad_raats': _("Cantidad de RAATs"), 
        'label_cantidad': _("Cantidad"),
        'label_materia': _("Materia"), 
        'label_grado': _("Grado"),
        'label_raats_por_ciclo': _("RAATs por Ciclo"),
    }

    if request.htmx:
        # For HTMX requests, render only the partial containing the charts and local filters
        return render(request, 'indicator_manager/_raat_charts_and_local_filters_partial.html', context)
    
    # For initial page load, render the full dashboard
    return render(request, 'indicator_manager/raat_dashboard.html', context)


def _clean_and_transform_raat_row(row_data, current_year, current_period, indicator_instance, row_number):
    try:
        curso_estudiante = str(row_data.get('Curso_estudiante', '')).strip()
        nombre_estudiante = str(row_data.get('Nombre estudiante', '')).strip()
        coordinacion = str(row_data.get('Coordinación', '')).strip()
        profesor_original = str(row_data.get('Profesor(a)', '')).strip()
        area = str(row_data.get('Area', '')).strip()
        if not all([curso_estudiante, nombre_estudiante, coordinacion, profesor_original, area]):
            return None, f"Fila {row_number}: Datos originales incompletos. Se omite."
        grado = None; curso_upper = curso_estudiante.upper()
        if "PRIMARIA - 6" in curso_upper or "P6" in curso_upper or "6P" in curso_upper or "6TO P" in curso_upper: grado = "6P"
        elif "PRIMARIA - 1" in curso_upper or "1RO P" in curso_upper : grado = "1P" 
        elif "PRIMARIA - 2" in curso_upper or "2DO P" in curso_upper : grado = "2P"
        elif "PRIMARIA - 3" in curso_upper or "3RO P" in curso_upper : grado = "3P"
        elif "PRIMARIA - 4" in curso_upper or "4TO P" in curso_upper : grado = "4P"
        elif "PRIMARIA - 5" in curso_upper or "5TO P" in curso_upper : grado = "5P"
        elif curso_estudiante and curso_estudiante[0].isdigit(): grado = curso_estudiante[0] + "S"
        paralelo = curso_estudiante[-1].upper() if curso_estudiante and curso_estudiante[-1].isalpha() else None
        estudiante = nombre_estudiante.replace(",", "").title()
        profesor = profesor_original.replace(",", "").title()
        parts = coordinacion.split(" ")
        ciclo = parts[1][:3].upper() if len(parts) > 1 else None
        if not ciclo and coordinacion: 
            coordinacion_upper = coordinacion.upper()
            if "PROFUNDIZACIÓN" in coordinacion_upper or "PROFU" in coordinacion_upper : ciclo = "PRO"
            elif "PREPARATORIA" in coordinacion_upper or "PREPA" in coordinacion_upper : ciclo = "PRE"
            elif "EXPLORACIÓN" in coordinacion_upper or "EXPLO" in coordinacion_upper : ciclo = "EXP"
            elif "INICIAL" in coordinacion_upper: ciclo = "INI"
            elif "PRIMARIO" in coordinacion_upper: ciclo = "PRI" 
            elif "SECUNDARIO" in coordinacion_upper: ciclo = "SEC" 
        if not all([area, grado, paralelo, estudiante, profesor, ciclo]):
            return None, f"Fila {row_number}: Datos transformados incompletos para '{curso_estudiante}'. Grado: {grado}, Paralelo: {paralelo}, Ciclo: {ciclo}. Se omite."
        return RAATData(indicator_source=indicator_instance, area=area, grado=grado, paralelo=paralelo, estudiante=estudiante, profesor=profesor, ciclo=ciclo, periodo=int(current_period), year=int(current_year)), None
    except Exception as e:
        return None, f"Error procesando fila {row_number}: {e}. Datos: {row_data}"

def process_raat_excel_data(request_user, uploaded_file_path, year, periodo, indicator_instance, for_preview=False, original_filename_for_log=None):
    processed_count = 0; error_count = 0; skipped_count = 0
    errors_list = []; preview_data = [] 
    try:
        df = pd.read_excel(uploaded_file_path, sheet_name="Datos")
        if df.empty: return {"status": "error", "message": "El archivo Excel o la pestaña 'Datos' está vacía."}
    except FileNotFoundError: return {"status": "error", "message": f"Error: Archivo no encontrado en {uploaded_file_path}"}
    except Exception as e: return {"status": "error", "message": f"Error al leer el archivo Excel: {e}"}
    records_to_create_or_preview = []
    for index, row in df.iterrows():
        raat_instance, error_message = _clean_and_transform_raat_row(row.to_dict(), year, periodo, indicator_instance, index + 2)
        if error_message:
            errors_list.append(error_message)
            if raat_instance is None: skipped_count +=1
            else: error_count += 1 
            continue
        if raat_instance:
            records_to_create_or_preview.append(raat_instance)
            if for_preview and len(preview_data) < 5: 
                preview_data.append({'Área': raat_instance.area, 'Grado': raat_instance.grado, 'Paralelo': raat_instance.paralelo,'Estudiante': raat_instance.estudiante, 'Profesor': raat_instance.profesor, 'Ciclo': raat_instance.ciclo,'Periodo': raat_instance.periodo, 'Año': raat_instance.year})
    if for_preview:
        return {"status": "preview", "message": f"Vista previa generada. Filas a crear: {len(records_to_create_or_preview)}, Omitidas: {skipped_count}, Errores de fila: {error_count}.","records_to_create_count": len(records_to_create_or_preview),"skipped_count": skipped_count,"error_count": error_count,"preview_data": preview_data,"detailed_errors": errors_list[:10]}
    else: 
        if records_to_create_or_preview:
            try:
                with transaction.atomic():
                    RAATData.objects.bulk_create(records_to_create_or_preview, ignore_conflicts=False) 
                processed_count = len(records_to_create_or_preview)
                summary = f"Datos importados exitosamente. Procesados: {processed_count}, Omitidos: {skipped_count}, Errores: {error_count}."
                if errors_list: summary += " Primeros errores/omisiones: " + " | ".join(errors_list[:3])
                IndicatorChangeLog.objects.create(indicator=indicator_instance,user=request_user, action_type='BULK_UPLOADED',changed_data={force_str(_("Archivo Original")): original_filename_for_log or uploaded_file_path.split(os.sep)[-1], force_str(_("Año de Datos")): year,force_str(_("Periodo de Datos")): periodo,force_str(_("Filas Procesadas Exitosamente")): processed_count,force_str(_("Filas Omitidas (Transformación)")): skipped_count,force_str(_("Filas con Errores (Transformación)")): error_count})
                return {"status": "success", "message": summary}
            except Exception as e: return {"status": "error", "message": f"Error al guardar en base de datos: {e}"}
        else:
            summary = f"No se crearon nuevos registros. Omitidos: {skipped_count}, Errores de fila: {error_count}."
            if errors_list: summary += " Primeros errores/omisiones: " + " | ".join(errors_list[:3])
            return {"status": "info", "message": summary}

@login_required
def indicator_list_view(request):
    queryset = Indicator.objects.select_related('academic_objective', 'sgc_objective').prefetch_related('review_months', 'responsible_persons').all().order_by('number')
    initial_form_data = request.GET.copy(); card_filtered_month_number = None 
    if 'filter_current_review_month' in initial_form_data:
        card_filtered_month_number = initial_form_data.get('filter_current_review_month')
        if card_filtered_month_number: initial_form_data.setlist('review_month', [card_filtered_month_number])
        if 'filter_current_review_month' in initial_form_data: del initial_form_data['filter_current_review_month']
    filter_form = IndicatorFilterForm(initial_form_data or None); applied_filters_summary_list = [] 
    if filter_form.is_valid():
        cleaned_data = filter_form.cleaned_data; search_text = cleaned_data.get('search_text')
        if search_text:
            q_search = Q(name__icontains=search_text) | Q(description__icontains=search_text)
            if search_text.isdigit(): q_search |= Q(number=int(search_text))
            queryset = queryset.filter(q_search)
            if search_text: applied_filters_summary_list.append(f"Búsqueda: '{search_text}'")
        if cleaned_data.get('shown_to_board'): queryset = queryset.filter(shown_to_board=True); applied_filters_summary_list.append("Directorio: Sí")
        selected_review_months = cleaned_data.get('review_month') 
        if selected_review_months: 
            queryset = queryset.filter(review_months__in=selected_review_months).distinct()
            month_names = ", ".join([m.get_number_display() for m in selected_review_months]); applied_filters_summary_list.append(f"Meses Rev.: {month_names}")
            if len(selected_review_months) == 1 and str(selected_review_months[0].number) == card_filtered_month_number: pass 
            elif card_filtered_month_number: card_filtered_month_number = None 
        selected_responsible_persons = cleaned_data.get('responsible_persons')
        if selected_responsible_persons: 
            queryset = queryset.filter(responsible_persons__in=selected_responsible_persons).distinct()
            person_names = ", ".join([p.username for p in selected_responsible_persons]); applied_filters_summary_list.append(f"Responsables: {person_names}")
        if cleaned_data.get('has_dashboard_filter'):
            powerbi_filled = Q(powerbi_url_token__isnull=False) & ~Q(powerbi_url_token__exact=''); local_filled = Q(local_dash_url__isnull=False) & ~Q(local_dash_url__exact=''); external_filled = Q(external_file_url__isnull=False) & ~Q(external_file_url__exact='')
            queryset = queryset.filter(powerbi_filled | local_filled | external_filled).distinct(); applied_filters_summary_list.append("Tiene Dashboard: Sí")
    applied_filters_summary_str = "; ".join(applied_filters_summary_list) if applied_filters_summary_list else "Ninguno aplicado"
    total_indicators_count = Indicator.objects.count(); filtered_indicators_count = queryset.distinct().count(); indicadores_presentados_count = 0 
    current_month_number_for_upcoming_card = datetime.date.today().month
    proximos_a_revision_count = Indicator.objects.filter(review_months__number=current_month_number_for_upcoming_card).distinct().count()
    paginator = Paginator(queryset.distinct(), 10); page_number = request.GET.get('page')
    try: page_obj = paginator.page(page_number)
    except PageNotAnInteger: page_obj = paginator.page(1)
    except EmptyPage: page_obj = paginator.page(paginator.num_pages)
    get_params = request.GET.copy()
    if 'page' in get_params: del get_params['page']
    if 'filter_current_review_month' in get_params: del get_params['filter_current_review_month']
    context = {
        'filter_form': filter_form, 'indicators': page_obj, 'total_indicators_count': total_indicators_count, 
        'filtered_indicators_count': filtered_indicators_count, 'indicadores_presentados_count': indicadores_presentados_count, 
        'proximos_a_revision_count': proximos_a_revision_count, 'current_month_number_for_card': current_month_number_for_upcoming_card,
        'get_params': get_params.urlencode(), 'request': request, 'applied_filters_summary_str': applied_filters_summary_str,
    }
    if request.htmx:
        response = render(request, 'indicator_manager/_indicator_table_partial.html', context)
        event_data = {"updateFilterSummary": {"value": applied_filters_summary_str}, "updateCounters": {"filtered": filtered_indicators_count, "total": total_indicators_count, "presented": indicadores_presentados_count, "upcoming": proximos_a_revision_count }}
        if card_filtered_month_number: event_data["setSelectedMonth"] = {"monthNumber": card_filtered_month_number}
        response['HX-Trigger'] = json.dumps(event_data)
        return response
    else: return render(request, 'indicator_manager/indicator_list.html', context)

class CustomLoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'

class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm 
    success_url = reverse_lazy('login') 
    template_name = 'accounts/signup.html'
    def form_valid(self, form):
        user = form.save(); return super().form_valid(form)

class IndicatorUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Indicator
    fields = [ 
        'number', 'name', 'description', 'shown_to_board', 
        'academic_objective', 'sgc_objective', 'review_months', 
        'responsible_persons', 
        'powerbi_url_token', 'local_dash_url', 'external_file_url',
        'data_ingestion_model_name', 'data_format_instructions'
    ]
    template_name = 'indicator_manager/indicator_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['indicator'] = self.object 
        preview_session_key = f'indicator_upload_preview_{self.object.pk}' 
        context['preview_data'] = self.request.session.get(preview_session_key)
        if self.object.data_ingestion_model_name and self.object.data_ingestion_model_name.strip() and not context['preview_data']:
            context['upload_form'] = IndicatorDataUploadForm(initial={'year': datetime.date.today().year})
        else: context['upload_form'] = None
        context['change_logs'] = IndicatorChangeLog.objects.filter(indicator=self.object).order_by('-timestamp')[:10]
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['review_months'].widget = forms.CheckboxSelectMultiple()
        form.fields['review_months'].queryset = Month.objects.all().order_by('number')
        form.fields['review_months'].help_text = "Seleccione los meses de revisión."
        form.fields['responsible_persons'].widget = forms.CheckboxSelectMultiple()
        form.fields['responsible_persons'].queryset = User.objects.filter(is_active=True).order_by('username')
        form.fields['responsible_persons'].help_text = "Seleccione las personas responsables."
        form.fields['data_ingestion_model_name'].widget.attrs.update({'placeholder': "Ej: RAATData (Nombre del Modelo)"})
        form.fields['data_format_instructions'].widget = forms.Textarea(attrs={'rows': 4, 'placeholder': "Ej: Columnas: Profesor, Periodo, CantidadRAAT. Formato: .xlsx"})
        common_input_classes = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary text-sm'
        textarea_classes = f'{common_input_classes} min-h-[80px]'
        for field_name, field in form.fields.items():
            current_classes = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.Textarea):
                 field.widget.attrs['class'] = f'{textarea_classes} {current_classes}'.strip()
            elif isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.EmailInput, forms.PasswordInput, forms.URLInput, forms.DateInput)):
                field.widget.attrs['class'] = f'{common_input_classes} {current_classes}'.strip()
            elif isinstance(field.widget, forms.Select) and not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs['class'] = f'{common_input_classes} {current_classes}'.strip()
            elif isinstance(field.widget, forms.CheckboxInput):
                 field.widget.attrs['class'] = f'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary mr-2 {current_classes}'.strip()
        return form

    def _get_display_value(self, value_from_cleaned_data_or_instance_attr):
        val = value_from_cleaned_data_or_instance_attr
        if hasattr(val, 'all'): 
            items = [force_str(item) for item in val.all().order_by('pk')] 
            return ", ".join(sorted(items)) if items else force_str(_("(ninguno)"))
        elif isinstance(val, Model): 
            return force_str(val)
        elif val is None:
            return force_str(_("(ninguno)"))
        elif isinstance(val, bool):
            return force_str(_("Sí")) if val else force_str(_("No"))
        elif isinstance(val, datetime.date):
            return val.strftime('%Y-%m-%d') 
        elif isinstance(val, datetime.datetime):
            return val.strftime('%Y-%m-%d %H:%M:%S') 
        return force_str(val)

    def form_valid(self, form):
        changed_fields_log_data = {}
        is_new_instance = not self.object.pk 
        old_instance_m2m_values = {}
        if not is_new_instance:
            try:
                temp_old_instance = Indicator.objects.get(pk=self.object.pk)
                for field_name in form.changed_data:
                    model_field = self.model._meta.get_field(field_name)
                    if model_field.many_to_many:
                         old_instance_m2m_values[field_name] = self._get_display_value(getattr(temp_old_instance, field_name))
            except Indicator.DoesNotExist: pass 
        response = super().form_valid(form) 
        action = 'CREATED' if is_new_instance else 'UPDATED'
        if action == 'CREATED':
            created_data_log = {}
            for field_name, field_obj in form.fields.items():
                if field_name in form.cleaned_data: 
                    val_cleaned = form.cleaned_data[field_name]
                    label = force_str(field_obj.label) if field_obj.label else field_name.replace('_',' ').capitalize()
                    created_data_log[label] = self._get_display_value(val_cleaned)
            IndicatorChangeLog.objects.create(indicator=self.object, user=self.request.user, action_type=action, changed_data={"creado_con_valores": created_data_log})
        elif form.has_changed(): 
            for field_name in form.changed_data:
                field_obj = form.fields.get(field_name)
                field_label = force_str(field_obj.label) if field_obj and field_obj.label else field_name.replace('_', ' ').capitalize()
                new_val_cleaned = form.cleaned_data.get(field_name)
                new_val_display = self._get_display_value(new_val_cleaned)
                if field_name in old_instance_m2m_values: 
                    old_val_display = old_instance_m2m_values[field_name]
                else: 
                    initial_val = form.initial.get(field_name)
                    old_val_display = self._get_display_value(initial_val)
                    if isinstance(form.fields[field_name], forms.BooleanField): 
                         old_val_display = force_str(_("Sí")) if initial_val else force_str(_("No"))
                if old_val_display != new_val_display:
                    changed_fields_log_data[field_label] = {'old': old_val_display, 'new': new_val_display}
            if changed_fields_log_data: 
                IndicatorChangeLog.objects.create(indicator=self.object, user=self.request.user, action_type=action, changed_data=changed_fields_log_data)
        messages.success(self.request, f"Indicador '{self.object.name}' {'creado' if action == 'CREATED' else 'actualizado'} exitosamente.")
        if '_save_and_return' in self.request.POST: return redirect(reverse_lazy('indicator_manager:dashboard'))
        return response 
    def get_success_url(self): return reverse('indicator_manager:indicator_manage', kwargs={'pk': self.object.pk})
    def test_func(self):
        indicator = self.get_object()
        return self.request.user in indicator.responsible_persons.all() or self.request.user.is_staff
    
    def post(self, request, *args, **kwargs):
        try: self.object = self.get_object()
        except AttributeError: self.object = None

        if '_save' in request.POST or '_save_and_return' in request.POST:
            form = self.get_form() 
            if form.is_valid(): return self.form_valid(form)
            else:
                for field_name_key, errors in form.errors.items():
                    field_label_str = force_str(form.fields[field_name_key].label) if field_name_key in form.fields and field_name_key != '__all__' else 'Formulario'
                    for error in errors: messages.error(request, f"{field_label_str}: {error}")
                return self.form_invalid(form)

        elif 'upload_indicator_data' in request.POST: 
            if not self.object:
                 messages.error(request, _("Indicador no encontrado para la subida de archivo."))
                 return redirect(reverse_lazy('indicator_manager:dashboard'))
            upload_form = IndicatorDataUploadForm(request.POST, request.FILES); indicator_instance = self.object 
            if upload_form.is_valid():
                data_file = request.FILES['data_file']; target_model_name = indicator_instance.data_ingestion_model_name
                year_for_data = upload_form.cleaned_data.get('year'); periodo_for_data = upload_form.cleaned_data.get('periodo')
                if not target_model_name or not target_model_name.strip():
                    messages.error(request, _("No se ha especificado un modelo destino para la ingesta de datos para este indicador."))
                    return redirect('indicator_manager:indicator_manage', pk=indicator_instance.pk)
                allowed_extensions = ['.xlsx', '.xls']
                file_name_orig, file_extension = os.path.splitext(data_file.name)
                if file_extension.lower() not in allowed_extensions:
                    messages.error(request, _("Formato de archivo no soportado. Use Excel (.xlsx, .xls)."))
                    return redirect('indicator_manager:indicator_manage', pk=indicator_instance.pk)
                if not settings.MEDIA_ROOT:
                    messages.error(request, _("Configuración de MEDIA_ROOT no encontrada para archivos temporales."))
                    return redirect('indicator_manager:indicator_manage', pk=indicator_instance.pk)
                temp_upload_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
                if not os.path.exists(temp_upload_dir):
                    try: os.makedirs(temp_upload_dir)
                    except OSError as e: messages.error(request, f"No se pudo crear el directorio temporal: {e}"); return redirect('indicator_manager:indicator_manage', pk=indicator_instance.pk)
                fs = FileSystemStorage(location=temp_upload_dir)
                safe_filename = os.path.basename(data_file.name) 
                filename_on_disk = fs.save(safe_filename, data_file) 
                uploaded_file_path = fs.path(filename_on_disk)
                preview_result = None; context = self.get_context_data(form=self.get_form()) 
                try:
                    if indicator_instance.data_ingestion_model_name == "RAATData":
                        preview_result = process_raat_excel_data(request.user, uploaded_file_path, year_for_data, periodo_for_data, indicator_instance, for_preview=True, original_filename_for_log=data_file.name) 
                        if preview_result.get("status") == "error":
                            messages.error(request, preview_result.get("message"))
                            if fs.exists(filename_on_disk): fs.delete(filename_on_disk)
                            context['upload_error_message'] = preview_result.get("message")
                            if request.htmx: return render(request, 'indicator_manager/_file_upload_section_partial.html', context)
                            return self.render_to_response(context) 
                        preview_session_key = f'indicator_upload_preview_{indicator_instance.pk}'
                        request.session[preview_session_key] = {'temp_file_path_on_disk': filename_on_disk, 'original_filename': data_file.name, 'year': year_for_data, 'periodo': periodo_for_data, 'stats': {'to_create': preview_result.get("records_to_create_count", 0), 'skipped': preview_result.get("skipped_count", 0), 'row_errors': preview_result.get("error_count", 0),}, 'preview_rows': preview_result.get("preview_data", []), 'detailed_errors': preview_result.get("detailed_errors", [])}
                        context['preview_data'] = request.session[preview_session_key]
                        context['upload_form'] = None 
                    else: 
                        messages.info(request, f"Archivo '{data_file.name}' recibido para {target_model_name}. Lógica de vista previa no implementada.")
                        if fs.exists(filename_on_disk): fs.delete(filename_on_disk)
                except ValueError as ve: messages.error(request, f"Error de validación/procesamiento: {ve}"); context['upload_error_message'] = str(ve);
                except Exception as e: messages.error(request, f"Error inesperado al procesar el archivo '{data_file.name}' para vista previa: {e}"); context['upload_error_message'] = str(e);
                if not request.session.get(f'indicator_upload_preview_{indicator_instance.pk}') and fs.exists(filename_on_disk):
                    fs.delete(filename_on_disk)
                if request.htmx: return render(request, 'indicator_manager/_file_upload_section_partial.html', context)
                return self.render_to_response(context) 
            else: 
                context = self.get_context_data(form=self.get_form()); context['upload_form'] = upload_form 
                messages.error(request, "Error en el formulario de subida del archivo. Por favor, revise.")
                if request.htmx: return render(request, 'indicator_manager/_file_upload_section_partial.html', context)
                return self.render_to_response(context)

        elif 'confirm_raat_data_save' in request.POST: 
            if not self.object: messages.error(request, _("Indicador no encontrado.")); return redirect(reverse_lazy('indicator_manager:dashboard'))
            indicator_instance = self.object; preview_session_key = f'indicator_upload_preview_{indicator_instance.pk}'; preview_info = request.session.get(preview_session_key)
            if not preview_info:
                messages.error(request, "No se encontró información de vista previa para guardar. Por favor, suba el archivo de nuevo.")
                if request.htmx: return HttpResponse("<div id='file-upload-and-preview-section-dynamic-content' class='mt-8'><p class='text-red-500 p-4 bg-red-100 rounded-md'>Error: No hay datos de vista previa. Recargue la página e intente de nuevo.</p></div>", status=200) 
                return redirect('indicator_manager:indicator_manage', pk=indicator_instance.pk)
            temp_filename_on_disk = preview_info['temp_file_path_on_disk']; temp_upload_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads'); fs = FileSystemStorage(location=temp_upload_dir); uploaded_file_path = fs.path(temp_filename_on_disk)
            year_for_data = preview_info['year']; periodo_for_data = preview_info['periodo']; original_filename = preview_info['original_filename']
            final_result_message = "Error desconocido durante el guardado."; 
            try:
                if indicator_instance.data_ingestion_model_name == "RAATData":
                    result = process_raat_excel_data(request.user, uploaded_file_path, year_for_data, periodo_for_data, indicator_instance, for_preview=False, original_filename_for_log=original_filename) 
                    final_result_message = result.get("message")
                    if result.get("status") == "success": messages.success(request, final_result_message)
                    elif result.get("status") == "info": messages.info(request, final_result_message)
                    else: messages.error(request, final_result_message)
                else: final_result_message = f"Lógica de guardado no implementada para: {indicator_instance.data_ingestion_model_name}"; messages.error(request, final_result_message)
            except ValueError as ve: final_result_message = f"Error de validación/guardado: {ve}"; messages.error(request, final_result_message)
            except Exception as e: final_result_message = f"Error inesperado al guardar '{original_filename}': {e}"; messages.error(request, final_result_message)
            finally:
                if fs.exists(temp_filename_on_disk): fs.delete(temp_filename_on_disk)
                if preview_session_key in request.session: del request.session[preview_session_key]
            if request.htmx:
                context = self.get_context_data(form=self.get_form()) 
                context['upload_form'] = IndicatorDataUploadForm(initial={'year': datetime.date.today().year}) if indicator_instance.data_ingestion_model_name else None
                return render(request, 'indicator_manager/_file_upload_section_partial.html', context)
            return redirect('indicator_manager:indicator_manage', pk=indicator_instance.pk)

        elif 'cancel_raat_data_upload' in request.POST:
            if not self.object: messages.error(request, _("Indicador no encontrado.")); return redirect(reverse_lazy('indicator_manager:dashboard'))
            indicator_instance = self.object; preview_session_key = f'indicator_upload_preview_{indicator_instance.pk}'; preview_info = request.session.get(preview_session_key)
            if preview_info and 'temp_file_path_on_disk' in preview_info:
                temp_filename_on_disk = preview_info['temp_file_path_on_disk']; temp_upload_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads'); fs = FileSystemStorage(location=temp_upload_dir)
                if fs.exists(temp_filename_on_disk):
                    try: fs.delete(temp_filename_on_disk)
                    except OSError as e_del: messages.warning(request, f"No se pudo eliminar el archivo temporal '{temp_filename_on_disk}': {e_del}")
            if preview_session_key in request.session: del request.session[preview_session_key]
            messages.info(request, "Subida de archivo cancelada.")
            if request.htmx:
                context = self.get_context_data(form=self.get_form())
                context['upload_form'] = IndicatorDataUploadForm(initial={'year': datetime.date.today().year}) if indicator_instance.data_ingestion_model_name else None
                return render(request, 'indicator_manager/_file_upload_section_partial.html', context)
            return redirect('indicator_manager:indicator_manage', pk=indicator_instance.pk)
        
        messages.warning(request, "Acción no reconocida.")
        return redirect(self.get_success_url())