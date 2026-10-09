from decimal import Decimal

from qq.models import BarangayServiceConfiguration


def service_configuration_map(barangay):
    return {
        item.service_id: item
        for item in BarangayServiceConfiguration.objects.filter(barangay=barangay)
    }


def effective_service_duration(barangay, service):
    configuration = BarangayServiceConfiguration.objects.filter(
        barangay=barangay, service=service
    ).only("estimated_duration").first()
    return configuration.estimated_duration if configuration else service.estimated_duration


def effective_service_fee(barangay, service):
    configuration = BarangayServiceConfiguration.objects.filter(
        barangay=barangay, service=service
    ).only("fee").first()
    return configuration.fee if configuration else Decimal("0.00")
