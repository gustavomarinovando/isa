from django.contrib import admin
from django.utils.translation import gettext_lazy as _ 
from django.utils.html import format_html
from .models import Month, AcademicObjective, SGCObjective, Indicator, User, IndicatorChangeLog, RAATData, RegistrationInvite

@admin.register(Month)
class MonthAdmin(admin.ModelAdmin):
    list_display = ('number', '__str__') 
    ordering = ('number',)

@admin.register(AcademicObjective)
class AcademicObjectiveAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(SGCObjective)
class SGCObjectiveAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(IndicatorChangeLog) 
class IndicatorChangeLogAdmin(admin.ModelAdmin):
    list_display = ('indicator', 'user', 'timestamp', 'action_type', 'display_changed_data_summary')
    list_filter = ('action_type', 'user', 'timestamp')
    search_fields = ('indicator__name', 'user__username')
    readonly_fields = ('indicator', 'user', 'timestamp', 'action_type', 'changed_data_prettified') 
    fields = ('indicator', 'user', 'timestamp', 'action_type', 'changed_data_prettified') 
    @admin.display(description=_("Datos Modificados (Resumen)"))
    def display_changed_data_summary(self, obj):
        if not obj.changed_data: return "N/A"
        summary = [f"{field}: '{diff.get('old', '')}' → '{diff.get('new', '')}'" for field, diff in obj.changed_data.items()]
        return "; ".join(summary) if summary else "Sin cambios detallados"
    @admin.display(description=_("Datos Modificados (JSON)"))
    def changed_data_prettified(self, obj):
        import json
        if obj.changed_data: return format_html("<pre>{}</pre>", json.dumps(obj.changed_data, indent=2, ensure_ascii=False))
        return None
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(RAATData) # New Admin for RAATData
class RAATDataAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'area', 'grado', 'paralelo', 'profesor', 'ciclo', 'periodo', 'year')
    list_filter = ('year', 'periodo', 'ciclo', 'grado', 'area', 'profesor', 'indicator_source')
    search_fields = ('estudiante', 'profesor', 'area')
    list_per_page = 25

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'name', 'display_responsible_persons', 'shown_to_board',
        'review_months_display_admin', 'has_dashboard_admin', 
        'dashboard_url_link_admin', 'external_file_url_link_admin',
    )
    list_filter = (
        'shown_to_board', 'academic_objective', 'sgc_objective',
        'responsible_persons', 'review_months' 
    )
    search_fields = (
        'number', 'name', 'description',
        'responsible_persons__username', 
        'responsible_persons__first_name',
        'responsible_persons__last_name'
    )
    ordering = ('number',)
    filter_horizontal = ('review_months', 'responsible_persons',) 

    fieldsets = (
        (None, { 'fields': ('number', 'name', 'description', 'shown_to_board') }),
        (_('Relationships & Responsibility'), { 'fields': ('academic_objective', 'sgc_objective', 'responsible_persons') }),
        (_('Review Schedule'), { 'fields': ('review_months',) }),
        (_('Dashboard & Data Configuration'), {
            'fields': ('powerbi_url_token', 'local_dash_url', 'external_file_url', 
                       'data_ingestion_model_name', 'data_format_instructions') 
        }),
        (_('Generated Dashboard Info (Read-Only)'), {
            'fields': ('full_powerbi_url_display', 'dashboard_url_display'),
            'classes': ('collapse',), 
        }),
    )
    readonly_fields = (
        'full_powerbi_url_display', 'dashboard_url_display', 
        'review_months_display_admin', 'has_dashboard_admin', 
        'dashboard_url_link_admin', 'external_file_url_link_admin'
    )

    def display_responsible_persons(self, obj):
        return ", ".join([user.username for user in obj.responsible_persons.all()])
    display_responsible_persons.short_description = _("Personas Responsables")

    def review_months_display_admin(self, obj): return obj.review_months_display
    review_months_display_admin.short_description = _("Meses de Revisión")

    def has_dashboard_admin(self, obj): return obj.has_dashboard
    has_dashboard_admin.boolean = True 
    has_dashboard_admin.short_description = _("Tiene Dashboard")

    def full_powerbi_url_display(self, obj): return obj.full_powerbi_url
    full_powerbi_url_display.short_description = _("Full Power BI URL")

    def dashboard_url_display(self, obj): return obj.dashboard_url
    dashboard_url_display.short_description = _("URL del Dashboard Principal")

    def dashboard_url_link_admin(self, obj):
        url = obj.dashboard_url
        if url:
            link_text = _("Abrir Dashboard")
            if url == obj.local_dash_url: link_text = _("Abrir Local")
            elif url == obj.full_powerbi_url: link_text = _("Abrir Power BI")
            elif url == obj.external_file_url: link_text = _("Ver Archivo Externo")
            return format_html("<a href='{url}' target='_blank'>{url_text}</a>", url=url, url_text=link_text)
        return _("N/A")
    dashboard_url_link_admin.short_description = _("Enlace Principal")

    def external_file_url_link_admin(self, obj):
        if obj.external_file_url:
            return format_html("<a href='{url}' target='_blank'>{text}</a>", url=obj.external_file_url, text=_("Ver Archivo"))
        return _("N/A")
    external_file_url_link_admin.short_description = _("Enlace Archivo Ext.")

@admin.register(RegistrationInvite)
class RegistrationInviteAdmin(admin.ModelAdmin):
    list_display = ('code', 'email', 'created_at', 'is_used')
    readonly_fields = ('code', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('email', 'code')
    actions = ['mark_as_unused']

    @admin.action(description=_("Marcar seleccionados como NO usados"))
    def mark_as_unused(self, request, queryset):
        queryset.update(is_used=False)