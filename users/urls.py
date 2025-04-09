from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.user_view, name='users'),
    path('<int:user_id>/', views.user_detail_view, name='user_detail'),
] 