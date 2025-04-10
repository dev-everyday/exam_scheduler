from django.urls import path
from . import views

urlpatterns = [
    path('', views.reservation_view, name='reservation'),
    path('my/', views.reservation_detail_view, name='reservation_detail'),
    path('admin/', views.admin_reservation_view, name='admin_reservation'),
    path('admin/<int:reservation_id>/', views.admin_reservation_detail_view, name='admin_reservation_detail'),
    path('admin/<int:reservation_id>/confirm/', views.admin_reservation_confirm_view, name='admin_reservation_confirm'),
]