"""
Custom Alert Builder

Allows users to define custom alerts with various triggers and delivery methods.

Features:
- User-defined trigger conditions
- Email delivery
- Telegram delivery
- Webhook delivery
- Alert management (create, update, delete, list)
"""

import asyncio
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field, HttpUrl

from fiml.core.logging import get_logger
from fiml.watchdog.models import EventFilter, WatchdogEvent
from fiml.watchdog.orchestrator import watchdog_manager

logger = get_logger(__name__)


# Models
class DeliveryMethod(str, Enum):
    """Alert delivery methods"""
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"


class TriggerType(str, Enum):
    """Types of alert triggers"""
    WATCHDOG_EVENT = "watchdog_event"
    PRICE_THRESHOLD = "price_threshold"
    VOLUME_THRESHOLD = "volume_threshold"
    CUSTOM_CONDITION = "custom_condition"


class EmailConfig(BaseModel):
    """Email delivery configuration"""
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    from_email: str
    to_emails: List[str]
    use_tls: bool = True


class TelegramConfig(BaseModel):
    """Telegram delivery configuration"""
    bot_token: str
    chat_ids: List[str]


class WebhookConfig(BaseModel):
    """Webhook delivery configuration"""
    url: HttpUrl
    method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    auth_token: Optional[str] = None


class AlertTrigger(BaseModel):
    """Alert trigger configuration"""
    type: TriggerType
    event_filter: Optional[EventFilter] = None
    price_threshold: Optional[float] = None
    volume_threshold: Optional[float] = None
    symbol: Optional[str] = None
    condition: Optional[str] = None  # Python expression


class AlertConfig(BaseModel):
    """Complete alert configuration"""
    alert_id: str
    name: str
    description: str
    enabled: bool = True
    trigger: AlertTrigger
    delivery_methods: List[DeliveryMethod]

    # Delivery configurations
    email_config: Optional[EmailConfig] = None
    telegram_config: Optional[TelegramConfig] = None
    webhook_config: Optional[WebhookConfig] = None

    # Alert metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    # Rate limiting
    cooldown_seconds: int = 60  # Minimum time between alerts


class AlertBuilder:
    """
    Alert builder for creating and managing custom alerts

    Features:
    - Multiple trigger types
    - Multiple delivery methods
    - Alert state management
    - Rate limiting
    """

    def __init__(self) -> None:
        self._alerts: Dict[str, AlertConfig] = {}
        self._subscriptions: Dict[str, str] = {}  # alert_id -> subscription_id
        self._last_triggered: Dict[str, datetime] = {}

        # Default configurations from environment
        self._default_email_config: Optional[EmailConfig] = None
        self._default_telegram_config: Optional[TelegramConfig] = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize alert builder with default configurations"""
        if self._initialized:
            return

        # Load default configurations from settings
        from fiml.core.config import settings

        # Email config
        smtp_host = getattr(settings, 'smtp_host', None)
        if smtp_host:
            self._default_email_config = EmailConfig(
                smtp_host=smtp_host,
                smtp_port=getattr(settings, 'smtp_port', 587),
                smtp_user=getattr(settings, 'smtp_user', ''),
                smtp_password=getattr(settings, 'smtp_password', ''),
                from_email=getattr(settings, 'smtp_from_email', ''),
                to_emails=[],
            )

        # Telegram config
        telegram_token = getattr(settings, 'telegram_bot_token', None)
        if telegram_token:
            self._default_telegram_config = TelegramConfig(
                bot_token=telegram_token,
                chat_ids=[],
            )

        self._initialized = True
        logger.info("Alert builder initialized")

    def create_alert(self, config: AlertConfig) -> AlertConfig:
        """
        Create a new alert

        Args:
            config: Alert configuration

        Returns:
            Created alert configuration
        """
        if config.alert_id in self._alerts:
            raise ValueError(f"Alert with ID '{config.alert_id}' already exists")

        # Set default configs if not provided
        if DeliveryMethod.EMAIL in config.delivery_methods and not config.email_config:
            config.email_config = self._default_email_config

        if DeliveryMethod.TELEGRAM in config.delivery_methods and not config.telegram_config:
            config.telegram_config = self._default_telegram_config

        # Store alert
        self._alerts[config.alert_id] = config

        # Subscribe to events if needed
        if config.trigger.type == TriggerType.WATCHDOG_EVENT:
            self._subscribe_to_watchdog_events(config)

        logger.info(f"Created alert: {config.name} (ID: {config.alert_id})")
        return config

    def update_alert(self, alert_id: str, config: AlertConfig) -> AlertConfig:
        """
        Update an existing alert

        Args:
            alert_id: Alert ID to update
            config: New alert configuration

        Returns:
            Updated alert configuration
        """
        if alert_id not in self._alerts:
            raise ValueError(f"Alert with ID '{alert_id}' not found")

        # Unsubscribe from old events
        self._unsubscribe_from_events(alert_id)

        # Update configuration
        config.updated_at = datetime.now(timezone.utc)
        self._alerts[alert_id] = config

        # Re-subscribe if needed
        if config.enabled and config.trigger.type == TriggerType.WATCHDOG_EVENT:
            self._subscribe_to_watchdog_events(config)

        logger.info(f"Updated alert: {config.name} (ID: {alert_id})")
        return config

    def delete_alert(self, alert_id: str) -> bool:
        """
        Delete an alert

        Args:
            alert_id: Alert ID to delete

        Returns:
            True if deleted successfully
        """
        if alert_id not in self._alerts:
            return False

        # Unsubscribe from events
        self._unsubscribe_from_events(alert_id)

        # Remove alert
        del self._alerts[alert_id]

        logger.info(f"Deleted alert: {alert_id}")
        return True

    def get_alert(self, alert_id: str) -> Optional[AlertConfig]:
        """Get alert configuration by ID"""
        return self._alerts.get(alert_id)

    def list_alerts(self, enabled_only: bool = False) -> List[AlertConfig]:
        """
        List all alerts

        Args:
            enabled_only: Only return enabled alerts

        Returns:
            List of alert configurations
        """
        alerts = list(self._alerts.values())
        if enabled_only:
            alerts = [a for a in alerts if a.enabled]
        return alerts

    def _subscribe_to_watchdog_events(self, config: AlertConfig) -> None:
        """Subscribe to watchdog events for an alert"""
        def event_handler(event: WatchdogEvent) -> None:
            """Callback for watchdog events - creates async task"""
            asyncio.create_task(self._handle_event(config, event))

        subscription_id = watchdog_manager.subscribe_to_events(
            callback=event_handler,
            event_filter=config.trigger.event_filter,
        )

        self._subscriptions[config.alert_id] = subscription_id

    def _unsubscribe_from_events(self, alert_id: str) -> None:
        """Unsubscribe from watchdog events"""
        if alert_id in self._subscriptions:
            subscription_id = self._subscriptions[alert_id]
            watchdog_manager.unsubscribe_from_events(subscription_id)
            del self._subscriptions[alert_id]

    async def _handle_event(self, config: AlertConfig, event: WatchdogEvent) -> None:
        """
        Handle a triggered event

        Args:
            config: Alert configuration
            event: Watchdog event that triggered the alert
        """
        if not config.enabled:
            return

        # Check cooldown
        if config.alert_id in self._last_triggered:
            time_since_last = (
                datetime.now(timezone.utc) - self._last_triggered[config.alert_id]
            ).total_seconds()

            if time_since_last < config.cooldown_seconds:
                logger.debug(
                    f"Alert {config.name} in cooldown "
                    f"({time_since_last:.0f}s / {config.cooldown_seconds}s)"
                )
                return

        # Update trigger stats
        config.last_triggered = datetime.now(timezone.utc)
        config.trigger_count += 1
        self._last_triggered[config.alert_id] = config.last_triggered

        logger.info(
            f"Alert triggered: {config.name} "
            f"(event: {event.type.value}, severity: {event.severity.value})"
        )

        # Deliver via configured methods
        tasks = []

        if DeliveryMethod.EMAIL in config.delivery_methods and config.email_config:
            tasks.append(self._send_email(config, event))

        if DeliveryMethod.TELEGRAM in config.delivery_methods and config.telegram_config:
            tasks.append(self._send_telegram(config, event))

        if DeliveryMethod.WEBHOOK in config.delivery_methods and config.webhook_config:
            tasks.append(self._send_webhook(config, event))

        # Execute deliveries concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email(self, config: AlertConfig, event: WatchdogEvent) -> None:
        """Send alert via email"""
        if not config.email_config:
            return

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"FIML Alert: {config.name}"
            msg['From'] = config.email_config.from_email
            msg['To'] = ', '.join(config.email_config.to_emails)

            # Create HTML body
            html_body = f"""
            <html>
              <head></head>
              <body>
                <h2>Alert: {config.name}</h2>
                <p><strong>Description:</strong> {config.description}</p>
                <hr>
                <h3>Event Details</h3>
                <ul>
                  <li><strong>Type:</strong> {event.type.value}</li>
                  <li><strong>Severity:</strong> {event.severity.value}</li>
                  <li><strong>Description:</strong> {event.description}</li>
                  <li><strong>Asset:</strong> {event.asset.symbol if event.asset else 'N/A'}</li>
                  <li><strong>Time:</strong> {event.timestamp.isoformat()}</li>
                </ul>
                <hr>
                <p><small>This is an automated alert from FIML</small></p>
              </body>
            </html>
            """

            msg.attach(MIMEText(html_body, 'html'))

            # Capture config locally for closure safety
            email_config = config.email_config

            # Send email in thread to avoid blocking
            def send_smtp() -> None:
                with smtplib.SMTP(
                    email_config.smtp_host,
                    email_config.smtp_port
                ) as server:
                    if email_config.use_tls:
                        server.starttls()
                    server.login(
                        email_config.smtp_user,
                        email_config.smtp_password
                    )
                    server.send_message(msg)

            # Run SMTP in thread pool to avoid blocking
            await asyncio.to_thread(send_smtp)

            logger.info(f"Email sent for alert: {config.name}")

        except Exception as e:
            logger.error(f"Failed to send email for alert {config.name}: {e}")

    async def _send_telegram(self, config: AlertConfig, event: WatchdogEvent) -> None:
        """Send alert via Telegram"""
        if not config.telegram_config:
            return

        try:
            # Format message
            message = (
                f"🔔 *FIML Alert: {config.name}*\n\n"
                f"*Event:* {event.type.value}\n"
                f"*Severity:* {event.severity.value}\n"
                f"*Description:* {event.description}\n"
            )

            if event.asset:
                message += f"*Asset:* {event.asset.symbol}\n"

            message += f"*Time:* {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

            # Send to all configured chat IDs
            async with aiohttp.ClientSession() as session:
                for chat_id in config.telegram_config.chat_ids:
                    url = (
                        f"https://api.telegram.org/bot{config.telegram_config.bot_token}"
                        f"/sendMessage"
                    )

                    payload = {
                        'chat_id': chat_id,
                        'text': message,
                        'parse_mode': 'Markdown',
                    }

                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            logger.error(
                                f"Telegram API error: {resp.status} - {await resp.text()}"
                            )

            logger.info(f"Telegram message sent for alert: {config.name}")

        except Exception as e:
            logger.error(f"Failed to send Telegram message for alert {config.name}: {e}")

    async def _send_webhook(self, config: AlertConfig, event: WatchdogEvent) -> None:
        """Send alert via webhook"""
        if not config.webhook_config:
            return

        try:
            # Prepare payload
            payload = {
                'alert_id': config.alert_id,
                'alert_name': config.name,
                'event': event.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

            # Prepare headers
            headers = config.webhook_config.headers.copy()
            headers['Content-Type'] = 'application/json'

            if config.webhook_config.auth_token:
                headers['Authorization'] = f"Bearer {config.webhook_config.auth_token}"

            # Send webhook
            async with aiohttp.ClientSession() as session, session.request(
                method=config.webhook_config.method,
                url=str(config.webhook_config.url),
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status not in [200, 201, 202, 204]:
                    logger.error(
                        f"Webhook error: {resp.status} - {await resp.text()}"
                    )

            logger.info(f"Webhook sent for alert: {config.name}")

        except Exception as e:
            logger.error(f"Failed to send webhook for alert {config.name}: {e}")


# Global alert builder instance
alert_builder = AlertBuilder()
