from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.user_view, name='users'),
    path('my/', views.user_detail_view, name='user_detail'),
    path('admin/', views.admin_user_view, name='user_admin'),
    path('admin/<int:user_id>/', views.admin_user_detail_view, name='user_admin_detail'),
] 