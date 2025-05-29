from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Month, AcademicObjective, SGCObjective, Indicator

class MonthSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_number_display', read_only=True)
    class Meta:
        model = Month
        fields = ['number', 'display_name']

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic User serializer for relationships."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name'] # Add more fields if needed by API consumers

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AcademicObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicObjective
        fields = ['id', 'name', 'description']

class SGCObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = SGCObjective
        fields = ['id', 'name', 'description']

class IndicatorSerializer(serializers.ModelSerializer):
    # To show related object details instead of just IDs:
    academic_objective = AcademicObjectiveSerializer(read_only=True)
    sgc_objective = SGCObjectiveSerializer(read_only=True)
    review_months = MonthSerializer(many=True, read_only=True) # For M2M, show list of month objects
    responsible_persons = UserBasicSerializer(many=True, read_only=True) # For M2M

    # Properties to include in API response
    review_months_display_str = serializers.CharField(source='review_months_display', read_only=True)
    next_or_current_review_month_display_str = serializers.CharField(source='next_or_current_review_month_display', read_only=True)
    has_dashboard_info = serializers.BooleanField(source='has_dashboard', read_only=True)
    dashboard_link = serializers.URLField(source='dashboard_url', read_only=True)
    
    # Writable fields for related objects (using PrimaryKeyRelatedField for updates)
    academic_objective_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicObjective.objects.all(), source='academic_objective', allow_null=True, required=False, write_only=True
    )
    sgc_objective_id = serializers.PrimaryKeyRelatedField(
        queryset=SGCObjective.objects.all(), source='sgc_objective', allow_null=True, required=False, write_only=True
    )
    review_month_ids = serializers.PrimaryKeyRelatedField(
        queryset=Month.objects.all(), source='review_months', many=True, required=False, write_only=True
    )
    responsible_person_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='responsible_persons', many=True, required=False, write_only=True
    )

    class Meta:
        model = Indicator
        fields = [
            'id', 'number', 'name', 'description', 'shown_to_board',
            'academic_objective', 'sgc_objective', 'review_months', 'responsible_persons', # Read-only nested
            'powerbi_url_token', 'local_dash_url', 'external_file_url',
            'review_months_display_str', 'data_ingestion_model_name',
            'next_or_current_review_month_display_str',
            'has_dashboard_info', 'dashboard_link',
            # Write-only fields for updates via ID
            'academic_objective_id', 'sgc_objective_id', 'review_month_ids', 'responsible_person_ids'
        ]

    # If you need custom create/update logic (e.g., for nested writes not handled by default),
    # you would override create() and update() methods here.
    # For now, PrimaryKeyRelatedField handles simple M2M/FK updates by ID.