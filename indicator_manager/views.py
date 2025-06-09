from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse 
from django.views import generic 
from django.contrib.auth import login 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin 
from django.db.models import Q, Model, Count 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Indicator, Month, User, IndicatorChangeLog, RAATData 
from .forms import IndicatorFilterForm, RegistrationForm, IndicatorDataUploadForm, RAATFilterForm, RegistrationForm
import datetime
from django.contrib.auth import views as auth_views
from django import forms 
import json 
from django.contrib import messages 
from django.core.files.storage import FileSystemStorage 
import io
import base64
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
    available_years_qs = RAATData.objects.values_list('year', flat=True).distinct().order_by('-year')
    available_years = [str(y) for y in available_years_qs]
    num_available_years = len(available_years) # For conditional display of year filter

    default_year = str(current_year) if str(current_year) in available_years else (available_years[0] if available_years else str(current_year))
    
    latest_period_with_data_qs = RAATData.objects.filter(year=int(default_year)).values_list('periodo', flat=True).order_by('-periodo')
    default_periodo = str(latest_period_with_data_qs.first()) if latest_period_with_data_qs.exists() else ''

    # Initial data for the form (which populates the visible slicers via context)
    form_initial_data = {
        'year': request.GET.get('year', default_year),
        'periodo': request.GET.get('periodo', default_periodo),
        'ciclo_local': request.GET.get('ciclo_local', ''),
        'grado_local': request.GET.get('grado_local', ''),
    }
    # The form itself is now mostly for providing the widgets to the template.
    # The actual selected values for HTMX request come from hidden fields updated by JS.
    filter_form = RAATFilterForm(initial=form_initial_data)


    # Query parameters are taken from GET request (which are from hidden fields populated by JS)
    query_year_str = request.GET.get('year', default_year)
    query_periodo_str = request.GET.get('periodo', default_periodo)
    
    query_year = int(query_year_str) if query_year_str else None
    query_periodo = int(query_periodo_str) if query_periodo_str else None
    query_ciclo_local = request.GET.get('ciclo_local', '') # From hidden field
    query_grado_local = request.GET.get('grado_local', '') # From hidden field


    base_db_filters = {}
    if query_year: base_db_filters['year'] = query_year
    if query_periodo: base_db_filters['periodo'] = query_periodo

    try:
        current_indicator = Indicator.objects.get(number=6) 
    except Indicator.DoesNotExist:
        current_indicator = None

    ciclo_chart_filters = base_db_filters.copy()
    ciclo_data_qs = RAATData.objects.filter(**ciclo_chart_filters)\
        .values('ciclo')\
        .annotate(count=Count('id'))\
        .order_by('ciclo')
    
    ciclo_color_map_view = { 'PRE': '#CCEBCF', 'PRO': '#65C0CC', 'EXP': '#1A72AE', 'N/A': '#D1D5DB', }
    custom_ciclo_order = ['PRE', 'PRO', 'EXP', 'N/A'] 

    temp_ciclo_data_map = {}
    for item in ciclo_data_qs:
        label = item['ciclo'] if item['ciclo'] else "N/A"
        if label not in custom_ciclo_order and label != "N/A": 
             label = "N/A" 
        count = item['count']
        temp_ciclo_data_map[label] = temp_ciclo_data_map.get(label, 0) + count 
            
    total_raat_count_for_period = sum(temp_ciclo_data_map.values())
    
    ciclo_table_data = [] # This is not used for table anymore, but data is prepared for donut
    final_ciclo_labels_for_donut = []
    final_ciclo_counts_for_donut = []

    for ciclo_key in custom_ciclo_order:
        if ciclo_key in temp_ciclo_data_map:
            count = temp_ciclo_data_map[ciclo_key]
            # percentage = (count / total_raat_count_for_period * 100) if total_raat_count_for_period > 0 else 0
            # ciclo_table_data.append({ ... }) # No longer needed for table
            final_ciclo_labels_for_donut.append(ciclo_key)
            final_ciclo_counts_for_donut.append(count)

    for label, count in temp_ciclo_data_map.items():
        if label not in final_ciclo_labels_for_donut: 
            # percentage = (count / total_raat_count_for_period * 100) if total_raat_count_for_period > 0 else 0
            # ciclo_table_data.append({ ... }) # No longer needed for table
            final_ciclo_labels_for_donut.append(label)
            final_ciclo_counts_for_donut.append(count)

    materia_chart_filters = base_db_filters.copy()
    if query_ciclo_local: materia_chart_filters['ciclo'] = query_ciclo_local
    if query_grado_local: materia_chart_filters['grado'] = query_grado_local
    
    materia_data_qs = RAATData.objects.filter(**materia_chart_filters)\
        .values('area')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:15]
    materia_labels = [item['area'] if item['area'] else _("N/A") for item in materia_data_qs]
    materia_counts = [item['count'] for item in materia_data_qs]

    grado_chart_filters = base_db_filters.copy()
    grado_order = ['6P', '1S', '2S', '3S', '4S', '5S', '6S'] 
    
    grado_data_qs = RAATData.objects.filter(**grado_chart_filters)\
        .values('grado')\
        .annotate(count=Count('id'))
    
    grado_data_dict = {}
    for item in grado_data_qs:
        grado_val = item['grado']
        if grado_val in grado_order:
            grado_data_dict[grado_val] = grado_data_dict.get(grado_val, 0) + item['count']

    grado_labels_ordered = []
    grado_counts_ordered = []
    for grado_key in grado_order:
        if grado_key in grado_data_dict and grado_data_dict[grado_key] > 0:
            grado_labels_ordered.append(grado_key)
            grado_counts_ordered.append(grado_data_dict[grado_key])
    
    context = {
        'filter_form': filter_form, # Still needed to render the filter widgets
        'indicator_manager': current_indicator, 
        'num_available_years': num_available_years, # Added for conditional year filter display
        'chart_data_materia_labels_json': json.dumps(materia_labels),
        'chart_data_materia_counts_json': json.dumps(materia_counts),
        'chart_data_grado_labels_json': json.dumps(grado_labels_ordered),
        'chart_data_grado_counts_json': json.dumps(grado_counts_ordered),
        'chart_data_ciclo_labels_json': json.dumps(final_ciclo_labels_for_donut),
        'chart_data_ciclo_counts_json': json.dumps(final_ciclo_counts_for_donut),
        'chart_data_total_raat': total_raat_count_for_period,
        # 'ciclo_table_data': ciclo_table_data, # No longer used for a table
        'ciclo_color_map_json': json.dumps(ciclo_color_map_view), 
        'selected_year': query_year_str, # Pass string versions for initial form population
        'selected_periodo': query_periodo_str,
        'selected_ciclo_local': query_ciclo_local, 
        'selected_grado_local': query_grado_local,
        'label_cantidad_raats': _("Cantidad de RAATs"), 
        'label_cantidad': _("Cantidad"),
        'label_materia': _("Materia"), 
        'label_grado': _("Grado"),
        'label_raats_por_ciclo': _("RAATs por Ciclo"),
    }

    if request.htmx:
        return render(request, 'indicator_manager/_raat_charts_and_local_filters_partial.html', context)
    
    return render(request, 'indicator_manager/raat_dashboard.html', context)


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


def _clean_and_transform_raat_row(row_data, current_year, current_period, indicator_instance, row_number):
    """
    Processes a single dictionary row from the Excel file to create a RAATData instance.
    This helper function does not need changes as it already works with dictionary data.
    """
    # ... (your complete, existing transformation logic) ...
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


def process_raat_excel_data(request_user, uploaded_file_obj, year, periodo, indicator_instance, for_preview=False, original_filename_for_log=None):
    """
    **** REFACTORED ****
    Processes an uploaded Excel file entirely in-memory using a file-like object (BytesIO).
    This function no longer interacts with the filesystem.
    """
    processed_count, error_count, skipped_count = 0, 0, 0
    errors_list, preview_data = [], []

    try:
        # Pandas reads directly from the in-memory file object. No more file paths!
        df = pd.read_excel(uploaded_file_obj, sheet_name="Datos")
        if df.empty:
            return {"status": "error", "message": "El archivo Excel o la pestaña 'Datos' está vacía."}
    except Exception as e:
        return {"status": "error", "message": f"Error al leer el archivo Excel: {e}"}

    records_to_create_or_preview = []
    for index, row in df.iterrows():
        raat_instance, error_message = _clean_and_transform_raat_row(row.to_dict(), year, periodo, indicator_instance, index + 2)
        if error_message:
            errors_list.append(error_message)
            skipped_count += 1 if raat_instance is None else 0
            error_count += 1 if raat_instance is not None else 0
            continue
        
        if raat_instance:
            records_to_create_or_preview.append(raat_instance)
            if for_preview and len(preview_data) < 5:
                preview_data.append({
                    'Área': raat_instance.area, 'Grado': raat_instance.grado, 'Paralelo': raat_instance.paralelo,
                    'Estudiante': raat_instance.estudiante, 'Profesor': raat_instance.profesor, 'Ciclo': raat_instance.ciclo,
                    'Periodo': raat_instance.periodo, 'Año': raat_instance.year
                })
    
    # Logic for returning preview or final result is the same, but it's now all based on in-memory data.
    if for_preview:
        return {
            "status": "preview", "records_to_create_count": len(records_to_create_or_preview),
            "skipped_count": skipped_count, "error_count": error_count,
            "preview_data": preview_data, "detailed_errors": errors_list[:10]
        }
    else: # Final save
        if not records_to_create_or_preview:
            summary = f"No se crearon nuevos registros. Omitidos: {skipped_count}, Errores: {error_count}."
            if errors_list: summary += " Primeros errores: " + " | ".join(errors_list[:3])
            return {"status": "info", "message": summary}
        try:
            with transaction.atomic():
                RAATData.objects.bulk_create(records_to_create_or_preview, ignore_conflicts=False)
            processed_count = len(records_to_create_or_preview)
            summary = f"Datos importados exitosamente. Procesados: {processed_count}, Omitidos: {skipped_count}, Errores: {error_count}."
            if errors_list: summary += " Primeros errores: " + " | ".join(errors_list[:3])
            IndicatorChangeLog.objects.create(
                indicator=indicator_instance, user=request_user, action_type='BULK_UPLOADED',
                changed_data={
                    force_str(_("Archivo Original")): original_filename_for_log,
                    force_str(_("Año")): year, force_str(_("Periodo")): periodo,
                    force_str(_("Filas Procesadas")): processed_count,
                    force_str(_("Omitidas")): skipped_count, force_str(_("Errores")): error_count
                })
            return {"status": "success", "message": summary}
        except Exception as e:
            return {"status": "error", "message": f"Error al guardar en base de datos: {e}"}


class IndicatorUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Indicator
    fields = [ 
        'number', 'name', 'description', 'shown_to_board', 
        'academic_objective', 'sgc_objective', 'review_months', 
        'responsible_persons', 'powerbi_url_token', 'local_dash_url', 
        'external_file_url', 'data_ingestion_model_name', 'data_format_instructions'
    ]
    template_name = 'indicator_manager/indicator_form.html'
    
    def test_func(self):
        indicator = self.get_object()
        return self.request.user in indicator.responsible_persons.all() or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['indicator'] = self.object
        preview_session_key = f'indicator_upload_preview_{self.object.pk}'
        context['preview_data'] = self.request.session.get(preview_session_key)
        
        if self.object.data_ingestion_model_name and not context['preview_data']:
            context['upload_form'] = IndicatorDataUploadForm(initial={'year': datetime.date.today().year})
        else:
            context['upload_form'] = None
            
        context['change_logs'] = IndicatorChangeLog.objects.filter(indicator=self.object).order_by('-timestamp')[:10]
        return context

    def get_form(self, form_class=None):
        """
        **** FIXED ****
        Restored your full custom styling logic.
        """
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
    
    def get_success_url(self):
        return reverse('indicator_manager:indicator_manage', kwargs={'pk': self.object.pk})

    def _get_display_value(self, value_from_cleaned_data_or_instance_attr):
        # This is your helper function for logging, restored from your code.
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
        elif isinstance(val, datetime.datetime):
            return val.strftime('%Y-%m-%d %H:%M:%S') 
        elif isinstance(val, datetime.date):
            return val.strftime('%Y-%m-%d')
        return force_str(val)

    def form_valid(self, form):
        """
        **** RESTORED ****
        Your custom form_valid logic for detailed change logging.
        """
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
            # ... (your create logging logic) ...
            pass
        elif form.has_changed(): 
            for field_name in form.changed_data:
                field_obj = form.fields.get(field_name)
                field_label = force_str(field_obj.label) if field_obj and field_obj.label else field_name.replace('_', ' ').capitalize()
                new_val_cleaned = form.cleaned_data.get(field_name)
                new_val_display = self._get_display_value(new_val_cleaned)
                old_val_display = old_instance_m2m_values.get(field_name, self._get_display_value(form.initial.get(field_name)))
                if old_val_display != new_val_display:
                    changed_fields_log_data[field_label] = {'old': old_val_display, 'new': new_val_display}
            if changed_fields_log_data: 
                IndicatorChangeLog.objects.create(indicator=self.object, user=self.request.user, action_type=action, changed_data=changed_fields_log_data)
        
        messages.success(self.request, f"Indicador '{self.object.name}' {'creado' if action == 'CREATED' else 'actualizado'} exitosamente.")
        if '_save_and_return' in self.request.POST: return redirect(reverse_lazy('indicator_manager:dashboard'))
        return response 

    def post(self, request, *args, **kwargs):
        """
        The refactored POST method with the `base64` bug fixed.
        """
        self.object = self.get_object()
        preview_session_key = f'indicator_upload_preview_{self.object.pk}'

        if '_save' in request.POST or '_save_and_return' in request.POST:
            return self.form_valid(self.get_form()) # Call form_valid directly

        elif 'upload_indicator_data' in request.POST:
            upload_form = IndicatorDataUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                uploaded_file = upload_form.cleaned_data['data_file']
                year = upload_form.cleaned_data['year']
                periodo = upload_form.cleaned_data['periodo']
                file_content_bytes = uploaded_file.read()
                result = process_raat_excel_data(request.user, io.BytesIO(file_content_bytes), year, periodo, self.object, for_preview=True, original_filename_for_log=uploaded_file.name)
                
                if result.get("status") == "preview":
                    request.session[preview_session_key] = {
                        # **** FIXED: Use standard library's base64 ****
                        'file_content_base64': base64.b64encode(file_content_bytes).decode('utf-8'),
                        'original_filename': uploaded_file.name, 'year': year, 'periodo': periodo,
                        'stats': {'to_create': result.get("records_to_create_count", 0), 'skipped': result.get("skipped_count", 0), 'row_errors': result.get("error_count", 0)},
                        'preview_rows': result.get("preview_data", []), 'detailed_errors': result.get("detailed_errors", [])
                    }
                else:
                    messages.error(request, result.get("message", "Ocurrió un error desconocido."))
            else:
                messages.error(request, "Error en el formulario. Por favor, revise los datos ingresados.")
        
        elif 'confirm_raat_data_save' in request.POST:
            preview_info = request.session.get(preview_session_key)
            if not preview_info:
                messages.error(request, "No se encontró información de vista previa. Por favor, suba el archivo de nuevo.")
            else:
                # **** FIXED: Use standard library's base64 ****
                file_content_bytes = base64.b64decode(preview_info['file_content_base64'])
                in_memory_file = io.BytesIO(file_content_bytes)
                result = process_raat_excel_data(request.user, in_memory_file, preview_info['year'], preview_info['periodo'], self.object, for_preview=False, original_filename_for_log=preview_info['original_filename'])
                status_tag = result.get("status", "error")
                getattr(messages, status_tag, messages.error)(request, result.get("message", "Error desconocido."))
                del request.session[preview_session_key]

        elif 'cancel_raat_data_upload' in request.POST:
            if preview_session_key in request.session:
                del request.session[preview_session_key]
                messages.info(request, "La carga de datos ha sido cancelada.")

        context = self.get_context_data()
        if request.htmx:
            # For any HTMX request (upload, confirm, cancel), render ONLY the partial.
            return render(request, 'indicator_manager/_file_upload_section_partial.html', context)
        else:
            # For a full-page refresh (unlikely here but safe), render the whole page.
            return self.render_to_response(context)


class CustomLoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'

class SignUpView(generic.CreateView):
    form_class = RegistrationForm
    success_url = reverse_lazy('login') 
    template_name = 'accounts/signup.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("¡Registro exitoso! Ahora puede iniciar sesión."))
        return response 
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            field_label = form.fields[field].label if field in form.fields and field != '__all__' else 'Formulario'
            for error in errors:
                messages.error(self.request, f"{force_str(field_label)}: {error}")
        return super().form_invalid(form)
