from django.urls import path
from .views import GenerateSQLAPIView

urlpatterns = [
    path('generate-sql/', GenerateSQLAPIView.as_view()),
]