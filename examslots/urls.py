from django.urls import path
from . import views

urlpatterns = [
    path('available/', views.get_available_slots, name='get_available_slots'),
] 