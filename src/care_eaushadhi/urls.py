from django.conf import settings
from django.shortcuts import HttpResponse
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_eaushadhi.api.viewsets.inward_record import InwardRecordViewSet


def healthy(request):
    return HttpResponse("OK")


router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("inward-records", InwardRecordViewSet, basename="eaushadhi_inward_records")

urlpatterns = [
    path("health", healthy),
] + router.urls
