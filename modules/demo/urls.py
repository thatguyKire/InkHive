from django.urls import path

from . import views

urlpatterns = [
    path("login/<str:role>/", views.demo_login, name="login"),
]
