from rest_framework import viewsets, permissions, filters as drf_filters
from django_filters import rest_framework as df_filters # Renamed to avoid clash
from .models import Indicator, Month, AcademicObjective, SGCObjective, User
from .serializers import (
    IndicatorSerializer, MonthSerializer, 
    AcademicObjectiveSerializer, SGCObjectiveSerializer, UserBasicSerializer
)

# Optional: Define a custom filter set for more complex filtering on the API
class IndicatorFilterSet(df_filters.FilterSet):
    # Example: filter by a specific review month number
    # review_month_number = df_filters.NumberFilter(field_name='review_months__number', lookup_expr='exact')
    # Example: filter by responsible person username
    # responsible_username = df_filters.CharFilter(field_name='responsible_persons__username', lookup_expr='icontains')

    # You can add more specific filters here if needed beyond what DRF's SearchFilter and OrderingFilter provide
    # For example, if you wanted to filter by a year part of a date, or more complex lookups.
    
    # Filter for review months (accepts multiple month numbers)
    review_months = df_filters.ModelMultipleChoiceFilter(
        field_name='review_months__number', # Filter on the 'number' field of the related Month model
        to_field_name='number',            # The field on the Month model to match against
        queryset=Month.objects.all(),
        label="Review Months (by number, e.g., ?review_months=1&review_months=5)"
    )

    class Meta:
        model = Indicator
        fields = { # Define fields available for exact match filtering, or use lookups
            'number': ['exact'],
            'shown_to_board': ['exact'],
            'academic_objective': ['exact'], # Filters by ID of academic_objective
            'sgc_objective': ['exact'],    # Filters by ID of sgc_objective
            'responsible_persons': ['exact'], # Filters by ID of responsible_persons (for M2M, checks if user ID is in the set)
            # 'name': ['icontains'], # Example if you want to allow ?name__icontains=...
        }


class IndicatorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows indicators to be viewed or edited.
    """
    queryset = Indicator.objects.select_related(
        'academic_objective', 'sgc_objective' # Only one responsible_person if it were FK
    ).prefetch_related(
        'review_months', 'responsible_persons' # For M2M
    ).all().order_by('number')
    serializer_class = IndicatorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Example: Read for anyone, Write for authenticated
    
    # Filtering, Searching, Ordering
    filterset_class = IndicatorFilterSet # Use our custom filter set
    search_fields = ['number', 'name', 'description', 'responsible_persons__username'] # Fields for ?search=...
    ordering_fields = ['number', 'name', 'date_updated'] # Fields for ?ordering=...
    ordering = ['number'] # Default ordering for the API

# Basic ViewSets for related models (mostly for lookup or if you need to manage them via API)
class MonthViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly as months are predefined
    queryset = Month.objects.all().order_by('number')
    serializer_class = MonthSerializer
    permission_classes = [permissions.AllowAny] # Months are public data

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_active=True).order_by('username')
    serializer_class = UserBasicSerializer
    permission_classes = [permissions.IsAuthenticated] # Only authenticated users can see user list

class AcademicObjectiveViewSet(viewsets.ModelViewSet):
    queryset = AcademicObjective.objects.all().order_by('name')
    serializer_class = AcademicObjectiveSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class SGCObjectiveViewSet(viewsets.ModelViewSet):
    queryset = SGCObjective.objects.all().order_by('name')
    serializer_class = SGCObjectiveSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]