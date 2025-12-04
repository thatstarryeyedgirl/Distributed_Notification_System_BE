from django.urls import path
from .views import TemplateDetailView, TemplateListCreateView, TemplateSubstitutionView, health_check

urlpatterns = [
    path("templates/", TemplateListCreateView.as_view(), name="template-list-create"),
    path("templates/<str:template_code>/", TemplateDetailView.as_view(), name="template-detail"),
    path("templates/substitute/", TemplateSubstitutionView.as_view(), name="template-substitute"),
    path("health/", health_check, name="health"),
]

