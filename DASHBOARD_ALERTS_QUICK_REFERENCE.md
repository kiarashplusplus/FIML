# Dashboard and Alert System Quick Reference

## Overview

The FIML Dashboard and Alert System provides real-time monitoring and custom notification capabilities built on top of the existing WebSocket streaming and Watchdog event intelligence systems.

## Features

### 1. Real-time Dashboard (`fiml/web/dashboard.py`)

#### HTTP API Endpoints

**Get Dashboard Statistics**
```http
GET /dashboard/stats
```
Returns overall system statistics including total events, active watchdogs, and connection info.

**Get Watchdog Status**
```http
GET /dashboard/watchdogs
```
Returns detailed health information for all watchdogs.

**Get Recent Events**
```http
GET /dashboard/events?limit=100&severity=high&event_type=price_anomaly
```
Parameters:
- `limit` (1-1000): Maximum number of events to return
- `severity`: Filter by severity (low, medium, high, critical)
- `event_type`: Filter by event type

**Monitor Multiple Assets**
```http
GET /dashboard/assets/monitor?symbols=AAPL,GOOGL&asset_type=equity&market=US
```
Returns current data for specified assets.

**Watchdog Management**
```http
POST /dashboard/watchdogs/{name}/enable
POST /dashboard/watchdogs/{name}/disable
POST /dashboard/watchdogs/{name}/restart
```

#### WebSocket Endpoint

**Real-time Dashboard Stream**
```
ws://localhost:8000/dashboard/stream
```

Streams three types of messages:
- `"type": "event"` - Watchdog events as they occur
- `"type": "stats"` - Periodic system statistics
- `"type": "health"` - System health updates

Example message:
```json
{
  "type": "event",
  "data": {
    "event_id": "evt_1234567890",
    "type": "price_anomaly",
    "severity": "high",
    "description": "Price spike detected",
    "asset": {"symbol": "AAPL", "asset_type": "equity"},
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### 2. Custom Alert Builder (`fiml/alerts/builder.py`)

#### Alert Configuration

Alerts consist of:
- **Trigger**: Defines when the alert should fire
- **Delivery Methods**: Email, Telegram, and/or Webhook
- **Rate Limiting**: Cooldown period between alerts

#### HTTP API Endpoints

**Create Alert**
```http
POST /api/alerts
Content-Type: application/json

{
  "alert_id": "my_alert_1",
  "name": "Price Spike Alert",
  "description": "Alert on significant price movements",
  "enabled": true,
  "trigger": {
    "type": "watchdog_event",
    "event_filter": {
      "event_types": ["price_anomaly"],
      "severities": ["high", "critical"]
    }
  },
  "delivery_methods": ["email", "telegram", "webhook"],
  "email_config": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "alerts@example.com",
    "smtp_password": "your-password",
    "from_email": "alerts@example.com",
    "to_emails": ["user@example.com"]
  },
  "telegram_config": {
    "bot_token": "123456:ABC-DEF...",
    "chat_ids": ["123456789"]
  },
  "webhook_config": {
    "url": "https://webhook.site/your-id",
    "method": "POST",
    "headers": {"Content-Type": "application/json"}
  },
  "cooldown_seconds": 300
}
```

**List Alerts**
```http
GET /api/alerts?enabled_only=true
```

**Get Alert**
```http
GET /api/alerts/{alert_id}
```

**Update Alert**
```http
PUT /api/alerts/{alert_id}
Content-Type: application/json

{...alert configuration...}
```

**Delete Alert**
```http
DELETE /api/alerts/{alert_id}
```

**Enable/Disable Alert**
```http
POST /api/alerts/{alert_id}/enable
POST /api/alerts/{alert_id}/disable
```

#### Trigger Types

1. **Watchdog Event Trigger**
   - Fires when a watchdog event matches the filter
   - Filter by event type, severity, and asset

2. **Price Threshold Trigger** (planned)
   - Fires when price crosses a threshold

3. **Volume Threshold Trigger** (planned)
   - Fires when volume exceeds a threshold

4. **Custom Condition Trigger** (planned)
   - Fires when a custom expression evaluates to true

#### Delivery Methods

**Email**
- Uses SMTP to send formatted email alerts
- Supports TLS/SSL
- Configurable recipients

**Telegram**
- Sends messages via Telegram Bot API
- Supports multiple chat IDs
- Markdown formatted messages

**Webhook**
- HTTP POST/PUT requests to custom endpoints
- Configurable headers and authentication
- JSON payload with event data

## Configuration

Add these settings to your `.env` file:

```env
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=alerts@yourcompany.com

# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

## Usage Examples

### Python Client Example

```python
import aiohttp
import asyncio

async def create_alert():
    async with aiohttp.ClientSession() as session:
        alert_config = {
            "alert_id": "alert_1",
            "name": "High Priority Events",
            "description": "Alert on critical events",
            "enabled": True,
            "trigger": {
                "type": "watchdog_event",
                "event_filter": {
                    "severities": ["high", "critical"]
                }
            },
            "delivery_methods": ["webhook"],
            "webhook_config": {
                "url": "https://webhook.site/your-id",
                "method": "POST"
            },
            "cooldown_seconds": 60
        }
        
        async with session.post(
            "http://localhost:8000/api/alerts",
            json=alert_config
        ) as resp:
            result = await resp.json()
            print(f"Alert created: {result['alert_id']}")

asyncio.run(create_alert())
```

### WebSocket Dashboard Monitoring

```python
import aiohttp
import asyncio

async def monitor_dashboard():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect("ws://localhost:8000/dashboard/stream") as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.json()
                    
                    if data["type"] == "event":
                        event = data["data"]
                        print(f"Event: {event['type']} - {event['description']}")
                    
                    elif data["type"] == "stats":
                        stats = data["data"]
                        print(f"Active watchdogs: {stats['active_watchdogs']}")

asyncio.run(monitor_dashboard())
```

### cURL Examples

**Get dashboard stats:**
```bash
curl http://localhost:8000/dashboard/stats
```

**Create an alert:**
```bash
curl -X POST http://localhost:8000/api/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "test_alert",
    "name": "Test Alert",
    "description": "Test alert",
    "enabled": true,
    "trigger": {
      "type": "watchdog_event",
      "event_filter": {"severities": ["high"]}
    },
    "delivery_methods": ["webhook"],
    "webhook_config": {
      "url": "https://webhook.site/your-id",
      "method": "POST"
    },
    "cooldown_seconds": 60
  }'
```

**List all alerts:**
```bash
curl http://localhost:8000/api/alerts
```

**Monitor multiple assets:**
```bash
curl "http://localhost:8000/dashboard/assets/monitor?symbols=AAPL,GOOGL,MSFT&asset_type=equity&market=US"
```

## Integration with Existing Systems

The Dashboard and Alert systems integrate seamlessly with:

1. **WebSocket Manager** - Reuses existing WebSocket infrastructure for real-time streaming
2. **Watchdog Orchestrator** - Subscribes to watchdog events via the event stream
3. **Arbitration Engine** - Fetches multi-asset data for monitoring
4. **Provider System** - Uses the existing provider abstraction layer

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CLIENT APPLICATIONS                     │
│  Web Dashboard | Mobile Apps | Monitoring Tools         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  DASHBOARD API                           │
│  HTTP Endpoints | WebSocket Stream | Asset Monitor      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              ALERT BUILDER SYSTEM                        │
│  Trigger Engine | Delivery Manager | Rate Limiter       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         WATCHDOG EVENT INTELLIGENCE                      │
│  Event Stream | Orchestrator | 8 Specialized Watchdogs  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           DELIVERY CHANNELS                              │
│  Email (SMTP) | Telegram Bot | Webhooks                 │
└─────────────────────────────────────────────────────────┘
```

## Performance Considerations

- **WebSocket Connections**: Each dashboard connection subscribes to all watchdog events
- **Rate Limiting**: Alert cooldown prevents notification spam
- **Event Filtering**: Filters applied at subscription time for efficiency
- **Concurrent Delivery**: Email, Telegram, and webhook deliveries execute concurrently

## Security Notes

- SMTP credentials stored in environment variables
- Telegram bot tokens should be kept secure
- Webhook endpoints should validate incoming requests
- Consider implementing authentication for dashboard API endpoints in production

## Future Enhancements

- [ ] Alert persistence to database
- [ ] Alert analytics and reporting
- [ ] Custom trigger expressions with DSL
- [ ] SMS delivery via Twilio
- [ ] Slack/Discord integrations
- [ ] Alert templates and presets
- [ ] Alert grouping and deduplication
- [ ] Dashboard UI (React/Vue frontend)

## See Also

- [Watchdog Quick Reference](WATCHDOG_QUICK_REFERENCE.md)
- [WebSocket Streaming Examples](examples/websocket_streaming.py)
- [Dashboard and Alert Examples](examples/dashboard_alerts_demo.py)
