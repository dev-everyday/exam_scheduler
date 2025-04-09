from django.urls import path
from . import views

urlpatterns = [
    path('', views.reservation_view, name='reservation'),
    path('<int:reservation_id>/', views.reservation_detail_view, name='reservation_detail'),
    path('<int:reservation_id>/confirm/', views.confirm_reservation_view, name='confirm_reservation'),
]