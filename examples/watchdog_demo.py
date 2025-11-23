"""
Watchdog System Example

Demonstrates the real-time event intelligence system in action.
"""

import asyncio

from fiml.watchdog import (
    EventFilter,
    EventType,
    Severity,
    WatchdogEvent,
    watchdog_manager,
)


async def handle_critical_event(event: WatchdogEvent):
    """Handle critical events with immediate action"""
    print(f"\n🚨 CRITICAL EVENT: {event.description}")
    print(f"   Asset: {event.asset.symbol if event.asset else 'N/A'}")
    print(f"   Type: {event.type.value}")
    print(f"   Time: {event.timestamp}")
    print(f"   Data: {event.data}")


async def handle_high_priority_event(event: WatchdogEvent):
    """Handle high-priority events"""
    print(f"\n⚠️  HIGH PRIORITY: {event.description}")
    print(f"   Asset: {event.asset.symbol if event.asset else 'N/A'}")


async def handle_all_events(event: WatchdogEvent):
    """Log all events"""
    severity_icons = {
        Severity.LOW: "ℹ️",
        Severity.MEDIUM: "📊",
        Severity.HIGH: "⚠️",
        Severity.CRITICAL: "🚨",
    }
    icon = severity_icons.get(event.severity, "•")
    print(f"{icon} [{event.watchdog}] {event.description}")


async def main():
    """
    Main example demonstrating watchdog system
    """
    print("=" * 70)
    print("FIML Watchdog Event Intelligence System")
    print("=" * 70)

    # Initialize the watchdog manager
    print("\n📡 Initializing watchdog system...")
    await watchdog_manager.initialize()

    # Subscribe to different event types
    print("\n📬 Setting up event subscriptions...")

    # Critical events
    watchdog_manager.subscribe_to_events(
        callback=handle_critical_event,
        event_filter=EventFilter(severities=[Severity.CRITICAL])
    )
    print("   ✓ Subscribed to CRITICAL events")

    # High-priority events
    watchdog_manager.subscribe_to_events(
        callback=handle_high_priority_event,
        event_filter=EventFilter(severities=[Severity.HIGH])
    )
    print("   ✓ Subscribed to HIGH priority events")

    # All events (for logging)
    watchdog_manager.subscribe_to_events(
        callback=handle_all_events,
    )
    print("   ✓ Subscribed to ALL events")

    # Price anomaly events only
    watchdog_manager.subscribe_to_events(
        callback=lambda e: print(f"💹 Price alert: {e.description}"),
        event_filter=EventFilter(
            event_types=[EventType.PRICE_ANOMALY, EventType.FLASH_CRASH]
        )
    )
    print("   ✓ Subscribed to PRICE ANOMALY events")

    # Show initial status
    print("\n📊 System Status:")
    status = watchdog_manager.get_status()
    print(f"   Total watchdogs: {status['total_watchdogs']}")
    print(f"   Enabled: {status['enabled_watchdogs']}")
    print(f"   Running: {status['running_watchdogs']}")

    # Show health
    print("\n🏥 Watchdog Health:")
    health = watchdog_manager.get_health()
    for name, h in health.items():
        status_icon = "✅" if h.status == "healthy" else "⚠️"
        print(f"   {status_icon} {name}: {h.status}")

    # Start monitoring
    print("\n🚀 Starting watchdog monitoring...")
    await watchdog_manager.start()

    print("\n👀 Watching for anomalies... (Ctrl+C to stop)")
    print("-" * 70)

    try:
        # Run for 60 seconds (or until interrupted)
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping...")

    # Show final statistics
    print("\n" + "=" * 70)
    print("Session Statistics")
    print("=" * 70)

    stats = watchdog_manager.get_event_stats()
    print(f"\nTotal events: {stats['total_events']}")

    if stats['events_by_type']:
        print("\nEvents by type:")
        for event_type, count in stats['events_by_type'].items():
            print(f"   {event_type}: {count}")

    if stats['events_by_severity']:
        print("\nEvents by severity:")
        for severity, count in stats['events_by_severity'].items():
            print(f"   {severity}: {count}")

    # Show recent events
    recent = watchdog_manager.get_recent_events(limit=10)
    if recent:
        print(f"\nLast {len(recent)} events:")
        for event in recent:
            print(f"   • {event.timestamp.strftime('%H:%M:%S')} - {event.description}")

    # Graceful shutdown
    print("\n🛑 Shutting down watchdog system...")
    await watchdog_manager.stop()

    print("✅ Shutdown complete\n")


if __name__ == "__main__":
    asyncio.run(main())
