from django.urls import path
from . import views

urlpatterns = [
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("accept/", views.accept_terms, name="accept"),
]
