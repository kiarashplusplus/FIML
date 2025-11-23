"""
Dashboard and Alert System Examples

This example demonstrates how to use the new dashboard and alert features.

Features demonstrated:
1. Real-time dashboard monitoring via WebSocket
2. Creating custom alerts with various triggers
3. Multi-asset monitoring
4. Alert delivery via email, Telegram, and webhooks
"""

import asyncio
import json

import aiohttp


async def monitor_dashboard():
    """
    Example: Monitor the dashboard in real-time via WebSocket
    
    Streams:
    - Watchdog events
    - System statistics
    - Health updates
    """
    print("=== Dashboard WebSocket Streaming ===\n")
    
    uri = "ws://localhost:8000/dashboard/stream"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(uri) as ws:
                print(f"✅ Connected to dashboard stream: {uri}\n")
                
                # Receive messages
                message_count = 0
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")
                        
                        if msg_type == "stats":
                            # System statistics
                            stats = data["data"]
                            print(f"📊 System Stats:")
                            print(f"   Total Events: {stats['total_events']}")
                            print(f"   Active Watchdogs: {stats['active_watchdogs']}")
                            print(f"   Healthy Watchdogs: {stats['healthy_watchdogs']}")
                            print()
                        
                        elif msg_type == "event":
                            # Watchdog event
                            event = data["data"]
                            print(f"🔔 New Event:")
                            print(f"   Type: {event['type']}")
                            print(f"   Severity: {event['severity']}")
                            print(f"   Description: {event['description']}")
                            if event.get('asset'):
                                print(f"   Asset: {event['asset']['symbol']}")
                            print()
                        
                        message_count += 1
                        if message_count >= 10:
                            print("Received 10 messages, disconnecting...")
                            break
                    
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"❌ WebSocket error: {ws.exception()}")
                        break
    
    except Exception as e:
        print(f"❌ Error connecting to dashboard: {e}")


async def get_dashboard_stats():
    """
    Example: Get current dashboard statistics via HTTP API
    """
    print("=== Dashboard Statistics API ===\n")
    
    uri = "http://localhost:8000/dashboard/stats"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(uri) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    print(f"📊 Dashboard Statistics:")
                    print(f"   Total Events: {data['total_events']}")
                    print(f"   Active Watchdogs: {data['active_watchdogs']}")
                    print(f"   Healthy Watchdogs: {data['healthy_watchdogs']}")
                    print(f"   Active Subscriptions: {data['active_subscriptions']}")
                    print(f"   Timestamp: {data['timestamp']}")
                    print()
                else:
                    print(f"❌ Error: HTTP {resp.status}")
    
    except Exception as e:
        print(f"❌ Error fetching stats: {e}")


async def monitor_multiple_assets():
    """
    Example: Monitor multiple assets in real-time
    """
    print("=== Multi-Asset Monitoring ===\n")
    
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    uri = f"http://localhost:8000/dashboard/assets/monitor"
    
    params = {
        "symbols": symbols,
        "asset_type": "equity",
        "market": "US"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(uri, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    print(f"📈 Monitoring {len(data)} assets:\n")
                    
                    for asset in data:
                        symbol = asset['symbol']
                        price = asset.get('price')
                        change = asset.get('change_percent')
                        
                        if price is not None:
                            change_indicator = "🟢" if change and change >= 0 else "🔴"
                            print(
                                f"{change_indicator} {symbol:6} "
                                f"${price:>8.2f} "
                                f"({change:>+6.2f}%)"
                            )
                        else:
                            print(f"⚠️  {symbol:6} No data available")
                    print()
                else:
                    print(f"❌ Error: HTTP {resp.status}")
    
    except Exception as e:
        print(f"❌ Error monitoring assets: {e}")


async def create_price_alert():
    """
    Example: Create a price alert that sends notifications
    
    This creates an alert that triggers when a high-severity
    price anomaly is detected.
    """
    print("=== Creating Price Alert ===\n")
    
    uri = "http://localhost:8000/api/alerts"
    
    # Alert configuration
    alert_config = {
        "alert_id": "price_spike_alert_1",
        "name": "Price Spike Alert",
        "description": "Alert when significant price movements are detected",
        "enabled": True,
        "trigger": {
            "type": "watchdog_event",
            "event_filter": {
                "event_types": ["price_anomaly"],
                "severities": ["high", "critical"]
            }
        },
        "delivery_methods": ["webhook"],  # Can be email, telegram, or webhook
        "webhook_config": {
            "url": "https://webhook.site/your-unique-id",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            }
        },
        "cooldown_seconds": 300  # 5 minutes between alerts
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(uri, json=alert_config) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    print(f"✅ Alert created successfully!")
                    print(f"   Alert ID: {data['alert_id']}")
                    print(f"   Name: {data['name']}")
                    print(f"   Enabled: {data['enabled']}")
                    print(f"   Delivery: {', '.join(data['delivery_methods'])}")
                    print()
                else:
                    error = await resp.text()
                    print(f"❌ Error creating alert: HTTP {resp.status}")
                    print(f"   {error}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def create_email_alert():
    """
    Example: Create an email alert for earnings anomalies
    """
    print("=== Creating Email Alert ===\n")
    
    uri = "http://localhost:8000/api/alerts"
    
    # Email alert configuration
    alert_config = {
        "alert_id": "earnings_alert_1",
        "name": "Earnings Surprise Alert",
        "description": "Email alert for significant earnings surprises",
        "enabled": True,
        "trigger": {
            "type": "watchdog_event",
            "event_filter": {
                "event_types": ["earnings_anomaly"],
                "severities": ["high", "critical"]
            }
        },
        "delivery_methods": ["email"],
        "email_config": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "your-email@gmail.com",
            "smtp_password": "your-app-password",
            "from_email": "alerts@yourcompany.com",
            "to_emails": ["analyst@yourcompany.com"],
            "use_tls": True
        },
        "cooldown_seconds": 600  # 10 minutes between alerts
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(uri, json=alert_config) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    print(f"✅ Email alert created!")
                    print(f"   Alert ID: {data['alert_id']}")
                    print(f"   Recipients: {', '.join(data['email_config']['to_emails'])}")
                    print()
                else:
                    error = await resp.text()
                    print(f"❌ Error: HTTP {resp.status}")
                    print(f"   {error}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def list_alerts():
    """
    Example: List all configured alerts
    """
    print("=== Listing All Alerts ===\n")
    
    uri = "http://localhost:8000/api/alerts"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(uri) as resp:
                if resp.status == 200:
                    alerts = await resp.json()
                    
                    print(f"📋 Found {len(alerts)} alert(s):\n")
                    
                    for alert in alerts:
                        status_icon = "✅" if alert['enabled'] else "⛔"
                        print(f"{status_icon} {alert['name']}")
                        print(f"   ID: {alert['alert_id']}")
                        print(f"   Description: {alert['description']}")
                        print(f"   Delivery: {', '.join(alert['delivery_methods'])}")
                        print(f"   Triggered: {alert['trigger_count']} times")
                        print()
                else:
                    print(f"❌ Error: HTTP {resp.status}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def manage_watchdogs():
    """
    Example: Manage watchdog status via dashboard API
    """
    print("=== Managing Watchdogs ===\n")
    
    base_uri = "http://localhost:8000/dashboard"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Get watchdog status
            async with session.get(f"{base_uri}/watchdogs") as resp:
                if resp.status == 200:
                    watchdogs = await resp.json()
                    
                    print(f"🔍 Found {len(watchdogs)} watchdog(s):\n")
                    
                    for wd in watchdogs[:3]:  # Show first 3
                        status_icon = {
                            "healthy": "✅",
                            "degraded": "⚠️",
                            "unhealthy": "❌"
                        }.get(wd['status'], "❓")
                        
                        print(f"{status_icon} {wd['name']}")
                        print(f"   Status: {wd['status']}")
                        print(f"   Enabled: {wd['enabled']}")
                        print(f"   Running: {wd['running']}")
                        print(f"   Total Checks: {wd['total_checks']}")
                        print()
                
                # Example: Restart a watchdog
                if watchdogs:
                    watchdog_name = watchdogs[0]['name']
                    print(f"♻️  Restarting watchdog: {watchdog_name}")
                    
                    async with session.post(
                        f"{base_uri}/watchdogs/{watchdog_name}/restart"
                    ) as restart_resp:
                        if restart_resp.status == 200:
                            result = await restart_resp.json()
                            print(f"   ✅ Status: {result['status']}\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all examples"""
    print("=" * 70)
    print("FIML Dashboard and Alert System Examples")
    print("=" * 70)
    print("\nMake sure the FIML server is running:")
    print("  uvicorn fiml.server:app --reload")
    print("\n" + "=" * 70 + "\n")
    
    # Run examples
    examples = [
        ("Dashboard Statistics", get_dashboard_stats),
        ("Multi-Asset Monitoring", monitor_multiple_assets),
        ("Watchdog Management", manage_watchdogs),
        ("Create Price Alert", create_price_alert),
        ("List Alerts", list_alerts),
        # ("Dashboard WebSocket", monitor_dashboard),  # This one runs longer
    ]
    
    for name, func in examples:
        print(f"\n{'=' * 70}")
        print(f"Example: {name}")
        print(f"{'=' * 70}\n")
        
        try:
            await func()
        except Exception as e:
            print(f"❌ Example failed: {e}\n")
        
        await asyncio.sleep(1)  # Brief pause between examples
    
    print("=" * 70)
    print("Examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
