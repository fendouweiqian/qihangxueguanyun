from app.domain.catalog import Order, Platform, School, Tenant
from app.api.catalog import _camel_row


def test_catalog_bigint_ids_are_strings():
    assert Platform.model_validate({"platform_id": 1, "platform_name": "平台"}).platform_id == "1"
    assert School.model_validate({"school_id": 2, "platform_id": 1, "school_name": "学校", "access_type": 1, "school_state": 0}).school_id == "2"
    assert Order.model_validate({"order_id": 3, "tenant_id": "DEMO", "student_id": 4, "school_id": 2, "platform_id": 1, "order_type": 1, "status": 0}).student_id == "4"
    assert Tenant.model_validate({"tenant_id": "DEMO", "tenant_name": "测试租户", "status": 0, "balance_points": 0}).tenant_id == "DEMO"


def test_catalog_serialization_only_stringifies_ids_not_business_numbers():
    row = _camel_row({"order_id": 9000000000000000001, "cost_points": 0, "balance_points": 12})

    assert row == {
        "orderId": "9000000000000000001",
        "costPoints": 0,
        "balancePoints": 12,
    }
