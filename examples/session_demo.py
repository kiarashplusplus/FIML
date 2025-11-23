"""
Session Management Demo

Demonstrates the session management system for multi-query analysis workflows.
"""

import asyncio

from fiml.sessions.models import SessionType
from fiml.sessions.store import get_session_store


async def demo_session_workflow():
    """
    Demonstrate a complete session-based analysis workflow
    """
    print("=" * 70)
    print("FIML Session Management Demo")
    print("=" * 70)

    # Initialize session store
    session_store = await get_session_store()

    # Step 1: Create a new analysis session
    print("\n[1] Creating new equity analysis session...")
    session = await session_store.create_session(
        assets=["AAPL", "MSFT", "GOOGL"],
        session_type=SessionType.COMPARATIVE,
        user_id="demo_user",
        ttl_hours=24,
        tags=["tech_stocks", "comparison", "demo"],
    )

    print(f"✓ Session created: {session.id}")
    print(f"  Type: {session.type.value}")
    print(f"  Assets: {', '.join(session.assets)}")
    print(f"  Expires: {session.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 2: Simulate multiple queries in the session
    print("\n[2] Executing queries within session...")

    from fiml.sessions.models import QueryRecord

    queries = [
        ("price", {"symbol": "AAPL"}, "AAPL: $175.43 (+2.3%)"),
        ("fundamentals", {"symbol": "AAPL"}, "P/E: 28.5, Market Cap: $2.7T"),
        ("price", {"symbol": "MSFT"}, "MSFT: $378.91 (+1.8%)"),
        ("fundamentals", {"symbol": "MSFT"}, "P/E: 35.2, Market Cap: $2.8T"),
        ("comparative", {"symbols": ["AAPL", "MSFT"]}, "MSFT outperforming AAPL"),
    ]

    for i, (qtype, params, summary) in enumerate(queries, 1):
        query = QueryRecord(
            query_type=qtype,
            parameters=params,
            result_summary=summary,
            execution_time_ms=150.0 + i * 20,
            cache_hit=(i % 2 == 0),
        )

        session.add_query(query)
        session.state.update_context(f"last_{qtype}", summary)

        await session_store.update_session(session.id, session)

        print(f"  Query {i}: {qtype.upper()} - {summary}")
        await asyncio.sleep(0.1)  # Simulate processing time

    # Step 3: Check session state
    print("\n[3] Session state summary...")
    refreshed = await session_store.get_session(session.id)

    print(f"  Total queries: {refreshed.state.history.total_queries}")
    print(f"  Cache hit rate: {refreshed.state.history.cache_hit_rate:.1%}")
    print(f"  Session duration: {refreshed.duration.total_seconds():.1f} seconds")

    query_types = refreshed.state.history.get_query_types_summary()
    print("  Query breakdown:")
    for qtype, count in query_types.items():
        print(f"    - {qtype}: {count}")

    # Step 4: Demonstrate context awareness
    print("\n[4] Demonstrating context awareness...")
    print("  Recent queries:")
    recent = refreshed.state.history.get_recent_queries(3)
    for q in recent:
        print(f"    - {q.timestamp.strftime('%H:%M:%S')} | {q.query_type}: {q.result_summary}")

    print("\n  Context data:")
    last_price = refreshed.state.get_context("last_price")
    last_comparative = refreshed.state.get_context("last_comparative")
    print(f"    - Last price query: {last_price}")
    print(f"    - Last comparative: {last_comparative}")

    # Step 5: Extend session
    print("\n[5] Extending session lifetime...")
    original_expiry = refreshed.expires_at
    await session_store.extend_session(session.id, hours=48)

    extended = await session_store.get_session(session.id)
    new_expiry = extended.expires_at
    print(f"  Original expiry: {original_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  New expiry: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Time remaining: {extended.time_remaining.total_seconds() / 3600:.1f} hours")

    # Step 6: List user sessions
    print("\n[6] Listing all sessions for user...")
    summaries = await session_store.list_user_sessions(
        user_id="demo_user",
        include_archived=False,
        limit=10,
    )

    print(f"  Found {len(summaries)} session(s):")
    for s in summaries:
        print(f"    - {s.id}")
        print(f"      Type: {s.type.value}, Assets: {', '.join(s.assets)}")
        print(f"      Queries: {s.total_queries}, Expired: {s.is_expired}")

    # Step 7: Session analytics
    print("\n[7] Generating session analytics...")
    if session_store._session_maker:
        from fiml.sessions.analytics import SessionAnalytics

        analytics = SessionAnalytics(session_store._session_maker)

        # Record metrics for this session
        await analytics.record_session_metrics(extended)
        print("  ✓ Metrics recorded")

        # Get statistics
        stats = await analytics.get_session_stats(
            user_id="demo_user",
            days=7,
        )

        print("  Statistics (last 7 days):")
        print(f"    - Total sessions: {stats['total_sessions']}")
        print(f"    - Total queries: {stats['total_queries']}")
        print(f"    - Avg queries/session: {stats['avg_queries_per_session']:.1f}")
        print(f"    - Avg duration: {stats['avg_duration_seconds']:.1f}s")

    # Step 8: Cleanup
    print("\n[8] Cleaning up demo session...")
    deleted = await session_store.delete_session(session.id)

    if deleted:
        print("  ✓ Session deleted")
    else:
        print("  ⚠ Session not found (may have been archived)")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


async def demo_mcp_tool_integration():
    """
    Demonstrate MCP tool integration with session tracking
    """
    print("\n" + "=" * 70)
    print("MCP Tool Integration with Sessions")
    print("=" * 70)

    from fiml.mcp.tools import (
        create_analysis_session,
        extend_session,
        get_session_info,
    )

    # Create session via MCP tool
    print("\n[1] Creating session via MCP tool...")
    result = await create_analysis_session(
        assets=["BTC", "ETH"],
        session_type="crypto",
        user_id="crypto_trader",
        ttl_hours=12,
        tags=["crypto", "trading"],
    )

    if result["status"] == "success":
        session_id = result["session_id"]
        print(f"✓ Session created: {session_id}")
        print(f"  Assets: {', '.join(result['assets'])}")
        print(f"  TTL: {result['ttl_hours']} hours")

        # Get session info
        print("\n[2] Getting session info...")
        info = await get_session_info(session_id)

        if info["status"] == "success":
            print(f"  Type: {info['type']}")
            print(f"  Total queries: {info['total_queries']}")
            print(f"  Time remaining: {info['time_remaining_hours']:.1f} hours")

        # Extend session
        print("\n[3] Extending session...")
        extend_result = await extend_session(session_id, hours=24)

        if extend_result["status"] == "success":
            print("✓ Session extended")
            print(f"  New time remaining: {extend_result['time_remaining_hours']:.1f} hours")

        # Cleanup
        from uuid import UUID

        from fiml.sessions.store import get_session_store

        session_store = await get_session_store()
        await session_store.delete_session(UUID(session_id))
        print("\n[4] ✓ Session cleaned up")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n🚀 Starting FIML Session Management Demo\n")

    # Run main workflow demo
    asyncio.run(demo_session_workflow())

    # Run MCP integration demo
    asyncio.run(demo_mcp_tool_integration())

    print("\n✨ All demos completed!\n")
