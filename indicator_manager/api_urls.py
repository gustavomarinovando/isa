from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views # Assuming your api views are in api_views.py

router = DefaultRouter()
router.register(r'indicators', api_views.IndicatorViewSet, basename='indicator')
router.register(r'months', api_views.MonthViewSet, basename='month')
router.register(r'users', api_views.UserViewSet, basename='user')
router.register(r'academic-objectives', api_views.AcademicObjectiveViewSet, basename='academicobjective')
router.register(r'sgc-objectives', api_views.SGCObjectiveViewSet, basename='sgcobjective')

urlpatterns = [
    path('', include(router.urls)),
]