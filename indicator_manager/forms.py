from django import forms
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth.models import User 
from .models import Month, AcademicObjective, SGCObjective, Indicator, IndicatorChangeLog, RAATData, RegistrationInvite
from django.utils.translation import gettext_lazy as _
import datetime

class IndicatorFilterForm(forms.Form):
    search_text = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Buscar por N°, nombre, o descripción...','class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm'}),label="") 
    shown_to_board = forms.BooleanField(required=False, label="Presenta a Directorio", widget=forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-2'}))
    review_month = forms.ModelMultipleChoiceField(queryset=Month.objects.all().order_by('number'), required=False, label="Meses de Revisión", widget=forms.CheckboxSelectMultiple(attrs={'class': 'text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-1 align-middle' }))
    responsible_persons = forms.ModelMultipleChoiceField(queryset=User.objects.filter(is_active=True).order_by('username'), required=False,label="Personas Responsables", widget=forms.CheckboxSelectMultiple(attrs={'class': 'text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-1 align-middle'}))
    has_dashboard_filter = forms.BooleanField(required=False,label="Tiene Dashboard", widget=forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-2'}))
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs)


class RegistrationForm(UserCreationForm):
    # --- FIX: Rename 'password' to 'password1' ---
    password1 = forms.CharField(
        label=_("Contraseña"), 
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label=_("Confirmar contraseña"), 
        widget=forms.PasswordInput
    )

    email = forms.EmailField(
        label=_("Correo Electrónico"),
        required=True, 
        help_text=_('Requerido. Use el correo al que se envió la invitación.')
    )
    first_name = forms.CharField(required=False, label=_("Nombres"))
    last_name = forms.CharField(required=False, label=_("Apellidos"))
    invite_code = forms.CharField(
        label=_("Código de Invitación"),
        help_text=_("Ingrese el código de invitación que recibió.")
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # You can remove the manual labeling from __init__ as it's now handled above
        self.fields['username'].label = _("Nombre de Usuario")

    # The rest of your form (clean and save methods) remains the same.
    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get('invite_code')
        email = cleaned_data.get('email')

        if code and email: 
            try:
                invite = RegistrationInvite.objects.get(code=code)
                if invite.email.lower() != email.lower():
                    self.add_error('invite_code', _("Este código de invitación no es válido para este correo electrónico."))
                if invite.is_used:
                    self.add_error('invite_code', _("Este código de invitación ya ha sido utilizado."))
            except (RegistrationInvite.DoesNotExist, ValueError):
                self.add_error('invite_code', _("Código de invitación no válido o no encontrado."))
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            code = self.cleaned_data.get('invite_code')
            invite = RegistrationInvite.objects.get(code=code)
            invite.is_used = True
            invite.save()
        return user

class IndicatorDataUploadForm(forms.Form):
    data_file = forms.FileField(
        label=_("Archivo de Datos (Excel .xlsx/.xls)"), 
        help_text=_("Suba el archivo Excel con la pestaña 'Datos'."),
        widget=forms.ClearableFileInput(attrs={'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-text hover:file:bg-primary-hover', 'accept': '.xlsx,.xls'})
    )
    year = forms.IntegerField(
        label=_("Año de los Datos"),
        initial=datetime.date.today().year,
        widget=forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary text-sm'})
    )
    # Example choices for 'periodo', adjust as needed for your school's reporting periods
    PERIODO_CHOICES = [(i, f"Periodo {i}") for i in range(1, 7)] # e.g., 1 to 6
    periodo = forms.ChoiceField(
        label=_("Periodo de los Datos"),
        choices=PERIODO_CHOICES,
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary text-sm'})
    )

class RAATFilterForm(forms.Form):
    current_year = datetime.date.today().year
    YEAR_CHOICES = [(str(y), str(y)) for y in range(current_year - 3, current_year + 2)] 
    
    PERIODO_CHOICES = [('', _("Todos"))] + [(str(i), _(f"P{i}")) for i in range(1, 7)]
    CICLO_CHOICES = [
        ('', _("Todos C.")),
        ('PRE', _('PRE')), ('PRO', _('PRO')), ('EXP', _('EXP')),
    ]
    GRADO_CHOICES_INITIAL = [('', _("Todos los Grados"))] 

    year = forms.ChoiceField(
        choices=YEAR_CHOICES, 
        required=True, 
        label=_("Año"),
        initial=str(current_year),
        widget=forms.Select(attrs={'class': 'filter-select text-xs p-1.5 h-8'}) # Base classes applied in __init__
    )
    periodo = forms.ChoiceField(
        choices=PERIODO_CHOICES, 
        required=False, 
        label=_("Periodo"),
        widget=forms.Select(attrs={'class': 'filter-select text-xs p-1.5 h-8'})
    )
    ciclo_local = forms.ChoiceField( 
        choices=CICLO_CHOICES,
        required=False, 
        label=_("Ciclo"),
        widget=forms.Select(attrs={'class': 'filter-select-local text-xs p-1.5 h-8', 'id': 'id_raat_ciclo_slicer_local'})
    )
    grado_local = forms.ChoiceField( 
        choices=GRADO_CHOICES_INITIAL, 
        required=False, 
        label=_("Grado"),
        widget=forms.Select(attrs={'class': 'filter-select-local text-xs p-1.5 h-8', 'id': 'id_raat_grado_slicer_local'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply common Tailwind classes to all select widgets
        # Adding 'appearance-none' and then a custom arrow usually needed for full control
        # For now, let's rely on browser default arrows with Tailwind form styling
        base_select_classes = 'w-full border border-gray-300 rounded-md shadow-sm focus:ring-primary focus:border-primary bg-white'
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                current_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{base_select_classes} {current_classes}'.strip()