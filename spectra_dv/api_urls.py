from django.urls import path

from regressions.api_views import ImportRunView

urlpatterns = [
    path("import/run/", ImportRunView.as_view(), name="api-import-run"),
]
