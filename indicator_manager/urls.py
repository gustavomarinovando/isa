from django.urls import path
from . import views
from .views import SignUpView, IndicatorUpdateView, indicator_list_view

app_name = 'indicator_manager'

urlpatterns = [
    path('', indicator_list_view, name='dashboard'), 
    path('signup/', SignUpView.as_view(), name='signup'),
    path('indicator/<int:pk>/manage/', IndicatorUpdateView.as_view(), name='indicator_manage'),
    path('dashboard/raat/', views.raat_dashboard_view, name='raat_dashboard'),
]