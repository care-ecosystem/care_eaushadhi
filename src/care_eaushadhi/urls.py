from django.conf import settings
from django.shortcuts import HttpResponse
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_eaushadhi.api.viewsets.institute_mapping import InstituteMappingViewSet
from care_eaushadhi.api.viewsets.inward_record import InwardRecordViewSet
from care_eaushadhi.api.viewsets.initiate_inward_fetch import InitiateInwardFetchViewSet
from care_eaushadhi.api.viewsets.product_mappings import ProductMappingViewSet
from care_eaushadhi.api.viewsets.record_item_delivery import RecordItemDeliveryViewSet


def healthy(request):
    return HttpResponse("OK")


router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register(
    "institute-mappings",
    InstituteMappingViewSet,
    basename="eaushadhi_institute_mappings"
)

router.register(
    "inward-records",
    InwardRecordViewSet,
    basename="eaushadhi_inward_records"
)

router.register(
    "initiate-inward-fetch",
    InitiateInwardFetchViewSet,
    basename="eaushadhi_initiate_inward_fetch"
)
router.register(
    "product-mappings",
    ProductMappingViewSet,
    basename="eaushadhi_product_mappings"
)

router.register(
    "record-item-deliveries",
    RecordItemDeliveryViewSet,
    basename="eaushadhi_record_item_deliveries"
)

urlpatterns = [
    path("health", healthy),
] + router.urls
