import pytest
from app.core.observability import system_monitor
from app.application.notification.services import NotificationService


def test_observability_telemetry():
    # 1. Record mock requests in SystemMonitor
    system_monitor.record_api_call(0.125)
    system_monitor.record_api_call(0.075)
    system_monitor.record_cache_hit()
    system_monitor.record_cache_miss()

    metrics = system_monitor.get_metrics()

    # 2. Check structure values
    assert "system" in metrics
    assert "cpu_utilization_percent" in metrics["system"]
    assert "memory_utilization_percent" in metrics["system"]

    assert metrics["api"]["total_requests"] >= 2
    assert metrics["api"]["average_response_latency_seconds"] > 0.0
    
    assert metrics["cache"]["hit_count"] >= 1
    assert metrics["cache"]["miss_count"] >= 1
    assert metrics["cache"]["hit_ratio"] == 0.5


@pytest.mark.asyncio
async def test_notification_alerting_pipeline(db_session):
    notif_service = NotificationService(db_session)

    # 1. Test profile quality check auto alert (triggers alert if score < 80)
    alert = await notif_service.check_dataset_and_alert(
        dataset_name="inconsistent_sales.csv",
        health_score=72
    )
    
    assert alert is not None
    assert alert.type == "warning"
    assert "inconsistent_sales.csv" in alert.message

    # 2. Retrieve unread notifications list
    unread_alerts = await notif_service.list_unread()
    assert len(unread_alerts) >= 1
    assert any(n.id == alert.id for n in unread_alerts)

    # 3. Dismiss notification
    dismissed = await notif_service.mark_read(str(alert.id))
    assert dismissed.is_read is True

    # 4. Assert list_unread drops dismissed records
    post_unread = await notif_service.list_unread()
    assert not any(n.id == alert.id for n in post_unread)
