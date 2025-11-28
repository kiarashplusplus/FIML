"""
Tests for Alert Builder functionality

Tests cover:
- Alert creation and management
- Alert triggers
- Delivery methods (email, telegram, webhook)
- Alert API endpoints
"""

import pytest
from fastapi.testclient import TestClient

from fiml.alerts.builder import (AlertBuilder, AlertConfig, AlertTrigger,
                                 DeliveryMethod, EmailConfig, TelegramConfig,
                                 TriggerType, WebhookConfig)
from fiml.server import app
from fiml.watchdog.models import EventFilter, Severity


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def alert_builder():
    """Alert builder fixture"""
    return AlertBuilder()


@pytest.fixture
def sample_email_config():
    """Sample email configuration"""
    return EmailConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="test@example.com",
        smtp_password="password",
        from_email="alerts@example.com",
        to_emails=["user@example.com"],
    )


@pytest.fixture
def sample_telegram_config():
    """Sample telegram configuration"""
    return TelegramConfig(
        bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        chat_ids=["123456789"],
    )


@pytest.fixture
def sample_webhook_config():
    """Sample webhook configuration"""
    return WebhookConfig(
        url="https://example.com/webhook",
        method="POST",
        headers={"Content-Type": "application/json"},
    )


@pytest.fixture
def sample_alert_config(sample_email_config):
    """Sample alert configuration"""
    return AlertConfig(
        alert_id="test_alert_1",
        name="Test Alert",
        description="Test alert for unit tests",
        enabled=True,
        trigger=AlertTrigger(
            type=TriggerType.WATCHDOG_EVENT,
            event_filter=EventFilter(severities=[Severity.HIGH, Severity.CRITICAL]),
        ),
        delivery_methods=[DeliveryMethod.EMAIL],
        email_config=sample_email_config,
    )


class TestAlertBuilder:
    """Test AlertBuilder class"""

    @pytest.mark.asyncio
    async def test_initialize_alert_builder(self, alert_builder):
        """Test initializing alert builder"""
        await alert_builder.initialize()
        assert alert_builder._initialized is True

    def test_create_alert(self, alert_builder, sample_alert_config):
        """Test creating an alert"""
        created = alert_builder.create_alert(sample_alert_config)

        assert created.alert_id == sample_alert_config.alert_id
        assert created.name == sample_alert_config.name
        assert created.enabled is True

    def test_create_duplicate_alert(self, alert_builder, sample_alert_config):
        """Test creating a duplicate alert fails"""
        alert_builder.create_alert(sample_alert_config)

        with pytest.raises(ValueError, match="already exists"):
            alert_builder.create_alert(sample_alert_config)

    def test_get_alert(self, alert_builder, sample_alert_config):
        """Test retrieving an alert"""
        alert_builder.create_alert(sample_alert_config)

        retrieved = alert_builder.get_alert(sample_alert_config.alert_id)
        assert retrieved is not None
        assert retrieved.alert_id == sample_alert_config.alert_id

    def test_get_nonexistent_alert(self, alert_builder):
        """Test retrieving a non-existent alert"""
        retrieved = alert_builder.get_alert("nonexistent")
        assert retrieved is None

    def test_list_alerts(self, alert_builder, sample_alert_config):
        """Test listing alerts"""
        alert_builder.create_alert(sample_alert_config)

        alerts = alert_builder.list_alerts()
        assert len(alerts) == 1
        assert alerts[0].alert_id == sample_alert_config.alert_id

    def test_list_alerts_enabled_only(self, alert_builder, sample_alert_config):
        """Test listing only enabled alerts"""
        # Create enabled alert
        alert_builder.create_alert(sample_alert_config)

        # Create disabled alert
        disabled_config = sample_alert_config.model_copy(deep=True)
        disabled_config.alert_id = "disabled_alert"
        disabled_config.enabled = False
        alert_builder.create_alert(disabled_config)

        # List all
        all_alerts = alert_builder.list_alerts()
        assert len(all_alerts) == 2

        # List enabled only
        enabled_alerts = alert_builder.list_alerts(enabled_only=True)
        assert len(enabled_alerts) == 1
        assert enabled_alerts[0].enabled is True

    def test_update_alert(self, alert_builder, sample_alert_config):
        """Test updating an alert"""
        alert_builder.create_alert(sample_alert_config)

        # Update configuration
        updated_config = sample_alert_config.model_copy(deep=True)
        updated_config.name = "Updated Alert Name"

        updated = alert_builder.update_alert(sample_alert_config.alert_id, updated_config)

        assert updated.name == "Updated Alert Name"

    def test_update_nonexistent_alert(self, alert_builder, sample_alert_config):
        """Test updating a non-existent alert fails"""
        with pytest.raises(ValueError, match="not found"):
            alert_builder.update_alert("nonexistent", sample_alert_config)

    def test_delete_alert(self, alert_builder, sample_alert_config):
        """Test deleting an alert"""
        alert_builder.create_alert(sample_alert_config)

        success = alert_builder.delete_alert(sample_alert_config.alert_id)
        assert success is True

        # Verify deletion
        retrieved = alert_builder.get_alert(sample_alert_config.alert_id)
        assert retrieved is None

    def test_delete_nonexistent_alert(self, alert_builder):
        """Test deleting a non-existent alert"""
        success = alert_builder.delete_alert("nonexistent")
        assert success is False


class TestAlertAPI:
    """Test Alert REST API endpoints"""

    def test_create_alert_via_api(self, client, sample_alert_config):
        """Test creating an alert via API"""
        response = client.post("/api/alerts", json=sample_alert_config.model_dump(mode="json"))

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == sample_alert_config.alert_id
        assert data["name"] == sample_alert_config.name

    def test_list_alerts_via_api(self, client, sample_alert_config):
        """Test listing alerts via API"""
        # Create an alert first
        client.post("/api/alerts", json=sample_alert_config.model_dump(mode="json"))

        # List alerts
        response = client.get("/api/alerts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_alert_via_api(self, client, sample_alert_config):
        """Test getting a specific alert via API"""
        # Create an alert first
        client.post("/api/alerts", json=sample_alert_config.model_dump(mode="json"))

        # Get the alert
        response = client.get(f"/api/alerts/{sample_alert_config.alert_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == sample_alert_config.alert_id

    def test_get_nonexistent_alert_via_api(self, client):
        """Test getting a non-existent alert via API"""
        response = client.get("/api/alerts/nonexistent")
        assert response.status_code == 404

    def test_update_alert_via_api(self, client, sample_alert_config):
        """Test updating an alert via API"""
        # Create an alert first
        client.post("/api/alerts", json=sample_alert_config.model_dump(mode="json"))

        # Update the alert
        updated_config = sample_alert_config.model_copy(deep=True)
        updated_config.name = "Updated via API"

        response = client.put(
            f"/api/alerts/{sample_alert_config.alert_id}",
            json=updated_config.model_dump(mode="json"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated via API"

    def test_delete_alert_via_api(self, client, sample_alert_config):
        """Test deleting an alert via API"""
        # Create an alert first
        client.post("/api/alerts", json=sample_alert_config.model_dump(mode="json"))

        # Delete the alert
        response = client.delete(f"/api/alerts/{sample_alert_config.alert_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    def test_enable_alert_via_api(self, client, sample_alert_config):
        """Test enabling an alert via API"""
        # Create a disabled alert
        sample_alert_config.enabled = False
        client.post("/api/alerts", json=sample_alert_config.model_dump(mode="json"))

        # Enable the alert
        response = client.post(f"/api/alerts/{sample_alert_config.alert_id}/enable")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enabled"

    def test_disable_alert_via_api(self, client, sample_alert_config):
        """Test disabling an alert via API"""
        # Create an enabled alert
        client.post("/api/alerts", json=sample_alert_config.model_dump(mode="json"))

        # Disable the alert
        response = client.post(f"/api/alerts/{sample_alert_config.alert_id}/disable")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"


class TestAlertDeliveryConfigs:
    """Test different alert delivery configurations"""

    def test_email_config(self, sample_email_config):
        """Test email configuration"""
        assert sample_email_config.smtp_host == "smtp.example.com"
        assert sample_email_config.smtp_port == 587
        assert len(sample_email_config.to_emails) == 1

    def test_telegram_config(self, sample_telegram_config):
        """Test telegram configuration"""
        assert sample_telegram_config.bot_token is not None
        assert len(sample_telegram_config.chat_ids) == 1

    def test_webhook_config(self, sample_webhook_config):
        """Test webhook configuration"""
        assert str(sample_webhook_config.url) == "https://example.com/webhook"
        assert sample_webhook_config.method == "POST"

    def test_multi_delivery_alert(
        self, alert_builder, sample_alert_config, sample_telegram_config, sample_webhook_config
    ):
        """Test alert with multiple delivery methods"""
        # Configure multiple delivery methods
        sample_alert_config.delivery_methods = [
            DeliveryMethod.EMAIL,
            DeliveryMethod.TELEGRAM,
            DeliveryMethod.WEBHOOK,
        ]
        sample_alert_config.telegram_config = sample_telegram_config
        sample_alert_config.webhook_config = sample_webhook_config

        created = alert_builder.create_alert(sample_alert_config)

        assert len(created.delivery_methods) == 3
        assert DeliveryMethod.EMAIL in created.delivery_methods
        assert DeliveryMethod.TELEGRAM in created.delivery_methods
        assert DeliveryMethod.WEBHOOK in created.delivery_methods
