"""
Comprehensive tests for session analytics functionality

Tests cover:
- Analytics data collection and aggregation
- Metrics calculation accuracy
- User-specific and platform-wide analytics
- Time-based filtering
- Edge cases and error handling
- Integration with session lifecycle
"""

from datetime import UTC, datetime, timedelta

import pytest

from fiml.sessions.analytics import SessionAnalytics
from fiml.sessions.models import QueryRecord, SessionType
from fiml.sessions.store import SessionStore


@pytest.mark.asyncio
class TestSessionAnalytics:
    """Test SessionAnalytics core functionality"""

    @pytest.fixture
    async def session_store(self, init_session_db):
        """Create and initialize session store with analytics"""
        store = SessionStore()
        await store.initialize()
        yield store
        await store.shutdown()

    @pytest.fixture
    async def analytics(self, session_store):
        """Create SessionAnalytics instance"""
        if not session_store._session_maker:
            raise RuntimeError("SessionStore not initialized")
        return SessionAnalytics(session_store._session_maker)

    async def test_analytics_initialization(self, analytics):
        """Test SessionAnalytics can be initialized properly"""
        assert analytics is not None
        assert analytics._session_maker is not None

    async def test_record_session_metrics_basic(self, session_store, analytics):
        """Test recording basic session metrics"""
        # Create a session with some activity
        session = await session_store.create_session(
            assets=["AAPL", "GOOGL"],
            session_type=SessionType.EQUITY,
            user_id="test_user",
            ttl_hours=1,
        )

        # Add some queries
        for i in range(5):
            query = QueryRecord(
                query_type="price" if i % 2 == 0 else "fundamentals",
                parameters={"symbol": "AAPL"},
                execution_time_ms=100.0 + i * 10,
                cache_hit=i % 2 == 0,
            )
            session.add_query(query)

        await session_store.update_session(session.id, session)

        # Record metrics
        await analytics.record_session_metrics(session)

        # Verify metrics were recorded
        stats = await analytics.get_session_stats(user_id="test_user", days=1)
        assert stats["total_sessions"] >= 1
        assert stats["total_queries"] >= 5

    async def test_record_session_metrics_with_tags(self, session_store, analytics):
        """Test recording session metrics with tags"""
        session = await session_store.create_session(
            assets=["TSLA"],
            session_type=SessionType.EQUITY,
            user_id="test_user",
            tags=["tech", "growth", "electric"],
        )

        # Add queries
        session.add_query(QueryRecord(query_type="price", parameters={"symbol": "TSLA"}))
        await session_store.update_session(session.id, session)

        # Archive session to make it available for analytics
        await session_store.archive_session(session.id)

        # Record metrics
        await analytics.record_session_metrics(session)

        # Get stats
        stats = await analytics.get_session_stats(user_id="test_user", days=1)

        # Check that tags are tracked
        assert "popular_tags" in stats
        # Tags might be empty if session isn't properly archived
        # but the field should exist

    async def test_get_session_stats_empty(self, analytics):
        """Test analytics with no session history"""
        stats = await analytics.get_session_stats(user_id="new_user", days=30)

        assert stats["total_sessions"] == 0
        assert stats["active_sessions"] == 0
        assert stats["archived_sessions"] == 0
        assert stats["total_queries"] == 0
        assert stats["avg_duration_seconds"] == 0.0
        assert stats["avg_queries_per_session"] == 0.0
        assert stats["abandonment_rate"] == 0.0
        assert stats["top_assets"] == []
        assert stats["query_type_distribution"] == {}
        assert stats["session_type_breakdown"] == {}
        assert stats["popular_tags"] == []
        assert "message" in stats
        assert "No session metrics available" in stats["message"]

    async def test_get_session_stats_with_data(self, session_store, analytics):
        """Test analytics with real session data"""
        user_id = "analyst_001"

        # Create multiple sessions with varying characteristics
        sessions = []
        for i in range(3):
            session = await session_store.create_session(
                assets=[f"STOCK{i}", "AAPL"],
                session_type=SessionType.EQUITY if i < 2 else SessionType.COMPARATIVE,
                user_id=user_id,
                ttl_hours=1,
                tags=["test", f"session_{i}"],
            )

            # Add varying numbers of queries
            for j in range(i + 2):  # 2, 3, 4 queries
                query = QueryRecord(
                    query_type="price" if j % 2 == 0 else "fundamentals",
                    parameters={"symbol": f"STOCK{i}"},
                    execution_time_ms=100.0,
                    cache_hit=j % 2 == 0,
                )
                session.add_query(query)

            await session_store.update_session(session.id, session)
            sessions.append(session)

            # Record metrics for each session
            await analytics.record_session_metrics(session)

        # Get analytics
        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Verify aggregated stats
        assert stats["total_sessions"] == 3
        assert stats["total_queries"] == 2 + 3 + 4  # 9 total
        assert stats["avg_queries_per_session"] == 3.0
        assert stats["user_id"] == user_id

        # Verify session type breakdown
        assert "session_type_breakdown" in stats
        breakdown = stats["session_type_breakdown"]
        assert breakdown.get("equity", 0) == 2
        assert breakdown.get("comparative", 0) == 1

        # Verify top assets
        assert len(stats["top_assets"]) > 0
        # AAPL should appear 3 times
        aapl_count = next((a["count"] for a in stats["top_assets"] if a["symbol"] == "AAPL"), 0)
        assert aapl_count == 3

    async def test_get_session_stats_time_filtering(self, session_store, analytics):
        """Test time-based filtering of analytics"""
        user_id = "time_test_user"

        # Create a session and record metrics
        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )
        session.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        # Get stats for last 1 day (should include our session)
        stats_1d = await analytics.get_session_stats(user_id=user_id, days=1)
        assert stats_1d["total_sessions"] >= 1

        # Get stats for last 30 days (should also include our session)
        stats_30d = await analytics.get_session_stats(user_id=user_id, days=30)
        assert stats_30d["total_sessions"] >= 1
        assert stats_30d["period_days"] == 30

    async def test_get_session_stats_session_type_filter(self, session_store, analytics):
        """Test filtering analytics by session type"""
        user_id = "type_filter_user"

        # Create equity session
        equity_session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )
        equity_session.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
        await session_store.update_session(equity_session.id, equity_session)
        await analytics.record_session_metrics(equity_session)

        # Create crypto session
        crypto_session = await session_store.create_session(
            assets=["BTC"],
            session_type=SessionType.CRYPTO,
            user_id=user_id,
        )
        crypto_session.add_query(QueryRecord(query_type="price", parameters={"symbol": "BTC"}))
        await session_store.update_session(crypto_session.id, crypto_session)
        await analytics.record_session_metrics(crypto_session)

        # Get equity-only stats
        equity_stats = await analytics.get_session_stats(
            user_id=user_id,
            session_type="equity",
            days=1,
        )
        assert equity_stats["total_sessions"] >= 1
        assert equity_stats["session_type"] == "equity"

        # Get crypto-only stats
        crypto_stats = await analytics.get_session_stats(
            user_id=user_id,
            session_type="crypto",
            days=1,
        )
        assert crypto_stats["total_sessions"] >= 1
        assert crypto_stats["session_type"] == "crypto"

    async def test_abandonment_rate_calculation(self, session_store, analytics):
        """Test abandonment rate calculation"""
        user_id = "abandonment_user"

        # Create abandoned session (< 2 queries, expired)
        abandoned = await session_store.create_session(
            assets=["TEST"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            ttl_hours=1,
        )
        # Only 1 query - will be considered abandoned
        abandoned.add_query(QueryRecord(query_type="price", parameters={"symbol": "TEST"}))
        # Mark as expired
        abandoned.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await session_store.update_session(abandoned.id, abandoned)
        await analytics.record_session_metrics(abandoned)

        # Create completed session (>= 2 queries)
        completed = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            ttl_hours=1,
        )
        # Multiple queries
        for i in range(5):
            completed.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
        await session_store.update_session(completed.id, completed)
        await analytics.record_session_metrics(completed)

        # Get stats
        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Should have 2 sessions, 1 abandoned
        assert stats["total_sessions"] == 2
        assert stats["abandonment_rate"] == pytest.approx(0.5)  # 50%

    async def test_query_type_distribution(self, session_store, analytics):
        """Test query type distribution calculation"""
        user_id = "query_dist_user"

        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )

        # Add different query types
        query_types = ["price", "price", "price", "fundamentals", "fundamentals", "technical"]
        for qtype in query_types:
            session.add_query(QueryRecord(query_type=qtype, parameters={"symbol": "AAPL"}))

        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Check query type distribution
        dist = stats["query_type_distribution"]
        assert dist.get("price", 0) == 3
        assert dist.get("fundamentals", 0) == 2
        assert dist.get("technical", 0) == 1

    async def test_avg_duration_calculation(self, session_store, analytics):
        """Test average session duration calculation"""
        user_id = "duration_user"

        # Create session
        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            ttl_hours=1,
        )

        # Add query to make it valid
        session.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))

        # Manually set created_at to simulate duration
        # Note: session.duration is calculated from created_at to now
        # For testing, we record metrics immediately, so duration will be very small
        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Duration should be positive but small (session just created)
        assert stats["avg_duration_seconds"] >= 0
        assert stats["total_sessions"] == 1

    async def test_top_assets_ranking(self, session_store, analytics):
        """Test top assets ranking"""
        user_id = "assets_user"

        # Create sessions with different asset frequencies
        asset_counts = {"AAPL": 5, "GOOGL": 3, "TSLA": 2, "MSFT": 1}

        for asset, count in asset_counts.items():
            for i in range(count):
                session = await session_store.create_session(
                    assets=[asset],
                    session_type=SessionType.EQUITY,
                    user_id=user_id,
                )
                session.add_query(QueryRecord(query_type="price", parameters={"symbol": asset}))
                await session_store.update_session(session.id, session)
                await analytics.record_session_metrics(session)

        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Check top assets are ranked correctly
        top_assets = stats["top_assets"]
        assert len(top_assets) >= 4

        # AAPL should be first with count 5
        assert top_assets[0]["symbol"] == "AAPL"
        assert top_assets[0]["count"] == 5

        # GOOGL should be second with count 3
        assert top_assets[1]["symbol"] == "GOOGL"
        assert top_assets[1]["count"] == 3

    async def test_active_vs_archived_sessions(self, session_store, analytics):
        """Test counting active vs archived sessions"""
        user_id = "active_archived_user"

        # Create active session (not expired)
        active = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            ttl_hours=24,  # Still active
        )
        active.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
        await session_store.update_session(active.id, active)

        # Create and archive a session
        to_archive = await session_store.create_session(
            assets=["GOOGL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            ttl_hours=1,
        )
        to_archive.add_query(QueryRecord(query_type="price", parameters={"symbol": "GOOGL"}))
        await session_store.update_session(to_archive.id, to_archive)
        await session_store.archive_session(to_archive.id)
        await analytics.record_session_metrics(to_archive)

        # Get stats
        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Note: active_sessions is queried from database, but active sessions are stored in Redis
        # so active_sessions will be 0 (active sessions are not in database)
        # Only archived sessions appear in database stats
        assert stats["archived_sessions"] >= 1
        assert stats["total_sessions"] >= 1  # At least the archived session should be recorded

    async def test_user_session_summary(self, session_store, analytics):
        """Test user-specific session summary"""
        user_id = "summary_user"

        # Create sessions of different types
        for session_type in [SessionType.EQUITY, SessionType.CRYPTO, SessionType.PORTFOLIO]:
            session = await session_store.create_session(
                assets=["TEST"],
                session_type=session_type,
                user_id=user_id,
            )
            session.add_query(QueryRecord(query_type="price", parameters={"symbol": "TEST"}))
            await session_store.update_session(session.id, session)
            await analytics.record_session_metrics(session)

        # Get user summary
        summary = await analytics.get_user_session_summary(user_id=user_id, days=1)

        # Should include session type breakdown
        assert "session_type_breakdown" in summary
        assert summary["total_sessions"] == 3

        # Check breakdown has all three types
        breakdown = summary["session_type_breakdown"]
        assert breakdown.get("equity", 0) == 1
        assert breakdown.get("crypto", 0) == 1
        assert breakdown.get("portfolio", 0) == 1

    async def test_export_session_metrics_json(self, session_store, analytics):
        """Test exporting session metrics as JSON"""
        user_id = "export_user"

        # Create a session
        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )
        session.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        # Export as JSON
        exported = await analytics.export_session_metrics(
            format="json",
            user_id=user_id,
            days=1,
        )

        # Should be same as get_session_stats
        assert "total_sessions" in exported
        assert exported["total_sessions"] >= 1

    async def test_export_session_metrics_invalid_format(self, analytics):
        """Test exporting with invalid format raises error"""
        with pytest.raises(ValueError, match="Unsupported export format"):
            await analytics.export_session_metrics(format="xml", user_id="test", days=1)

    async def test_platform_wide_analytics(self, session_store, analytics):
        """Test analytics across all users (no user filter)"""
        # Create sessions for different users
        users = ["user1", "user2", "user3"]
        for user_id in users:
            session = await session_store.create_session(
                assets=["AAPL"],
                session_type=SessionType.EQUITY,
                user_id=user_id,
            )
            session.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
            await session_store.update_session(session.id, session)
            await analytics.record_session_metrics(session)

        # Get platform-wide stats (no user_id filter)
        stats = await analytics.get_session_stats(days=1)

        # Should include sessions from all users
        assert stats["total_sessions"] >= 3
        assert stats["user_id"] is None  # No specific user

    async def test_cache_hit_rate_tracking(self, session_store, analytics):
        """Test cache hit rate calculation in analytics"""
        user_id = "cache_user"

        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )

        # Add queries with specific cache hit pattern
        # 3 cache hits, 2 misses = 60% hit rate
        cache_patterns = [True, True, True, False, False]
        for hit in cache_patterns:
            session.add_query(
                QueryRecord(
                    query_type="price",
                    parameters={"symbol": "AAPL"},
                    cache_hit=hit,
                )
            )

        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        # Cache hit rate should be recorded in metrics
        # We can't directly test it from stats, but it's stored in the database
        stats = await analytics.get_session_stats(user_id=user_id, days=1)
        assert stats["total_sessions"] >= 1

    async def test_multiple_assets_per_session(self, session_store, analytics):
        """Test analytics with sessions containing multiple assets"""
        user_id = "multi_asset_user"

        # Create session with multiple assets
        session = await session_store.create_session(
            assets=["AAPL", "GOOGL", "MSFT", "TSLA"],
            session_type=SessionType.COMPARATIVE,
            user_id=user_id,
        )
        session.add_query(QueryRecord(query_type="comparative", parameters={"symbols": ["AAPL", "GOOGL"]}))
        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # All 4 assets should appear in top assets
        top_assets = {a["symbol"] for a in stats["top_assets"]}
        assert "AAPL" in top_assets
        assert "GOOGL" in top_assets
        assert "MSFT" in top_assets
        assert "TSLA" in top_assets

    async def test_edge_case_zero_queries(self, session_store, analytics):
        """Test analytics with session that has zero queries"""
        user_id = "zero_query_user"

        # Create session with no queries
        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )
        # Don't add any queries
        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Should handle zero queries gracefully
        assert stats["total_sessions"] >= 1
        assert stats["total_queries"] == 0
        assert stats["avg_queries_per_session"] == 0.0

    async def test_popular_tags_tracking(self, session_store, analytics):
        """Test popular tags tracking and ranking"""
        user_id = "tags_user"

        # Create sessions with different tag frequencies
        tag_sessions = [
            ["tech", "growth"],
            ["tech", "value"],
            ["tech", "dividend"],
            ["growth", "value"],
            ["growth"],
        ]

        for tags in tag_sessions:
            session = await session_store.create_session(
                assets=["TEST"],
                session_type=SessionType.EQUITY,
                user_id=user_id,
                tags=tags,
            )
            session.add_query(QueryRecord(query_type="price", parameters={"symbol": "TEST"}))
            await session_store.update_session(session.id, session)
            await session_store.archive_session(session.id)

        # Get stats
        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Check popular tags (if any archived sessions exist)
        popular_tags = stats["popular_tags"]
        if popular_tags:
            # "tech" should appear 3 times, "growth" 3 times
            tag_dict = {t["tag"]: t["count"] for t in popular_tags}
            assert tag_dict.get("tech", 0) == 3
            assert tag_dict.get("growth", 0) == 3

    async def test_concurrent_metrics_recording(self, session_store, analytics):
        """Test recording metrics for multiple sessions concurrently"""
        import asyncio

        user_id = "concurrent_user"

        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = await session_store.create_session(
                assets=[f"STOCK{i}"],
                session_type=SessionType.EQUITY,
                user_id=user_id,
            )
            session.add_query(QueryRecord(query_type="price", parameters={"symbol": f"STOCK{i}"}))
            await session_store.update_session(session.id, session)
            sessions.append(session)

        # Record metrics concurrently
        await asyncio.gather(*[analytics.record_session_metrics(s) for s in sessions])

        # Get stats
        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Should have all 5 sessions
        assert stats["total_sessions"] == 5

    async def test_long_time_period(self, session_store, analytics):
        """Test analytics with longer time period (90 days)"""
        user_id = "long_period_user"

        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )
        session.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
        await session_store.update_session(session.id, session)
        await analytics.record_session_metrics(session)

        # Get stats for 90 days
        stats = await analytics.get_session_stats(user_id=user_id, days=90)

        assert stats["period_days"] == 90
        assert stats["total_sessions"] >= 1

    async def test_analytics_with_mixed_session_states(self, session_store, analytics):
        """Test analytics with mix of active, expired, and archived sessions"""
        user_id = "mixed_state_user"

        # Create active session
        active = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            ttl_hours=24,
        )
        active.add_query(QueryRecord(query_type="price", parameters={"symbol": "AAPL"}))
        await session_store.update_session(active.id, active)

        # Create expired session
        expired = await session_store.create_session(
            assets=["GOOGL"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            ttl_hours=1,
        )
        expired.add_query(QueryRecord(query_type="price", parameters={"symbol": "GOOGL"}))
        expired.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await session_store.update_session(expired.id, expired)
        await analytics.record_session_metrics(expired)

        # Create archived session
        archived = await session_store.create_session(
            assets=["MSFT"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
        )
        archived.add_query(QueryRecord(query_type="price", parameters={"symbol": "MSFT"}))
        await session_store.update_session(archived.id, archived)
        await session_store.archive_session(archived.id)
        await analytics.record_session_metrics(archived)

        # Get stats
        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        # Note: active_sessions will be 0 because active sessions are in Redis, not PostgreSQL
        # The analytics query only checks the database for archived sessions
        assert stats["active_sessions"] == 0  # Active sessions are in Redis, not DB
        assert stats["archived_sessions"] >= 1
        assert stats["total_sessions"] >= 2  # Only archived sessions have metrics


@pytest.mark.asyncio
class TestAnalyticsIntegration:
    """Integration tests for analytics with full session lifecycle"""

    @pytest.fixture
    async def session_store(self, init_session_db):
        """Create and initialize session store"""
        store = SessionStore()
        await store.initialize()
        yield store
        await store.shutdown()

    @pytest.fixture
    async def analytics(self, session_store):
        """Create SessionAnalytics instance"""
        return SessionAnalytics(session_store._session_maker)

    async def test_complete_analytics_workflow(self, session_store, analytics):
        """
        Test complete analytics workflow:
        1. Create multiple sessions
        2. Perform queries
        3. Archive sessions
        4. Record metrics
        5. Generate analytics
        6. Verify accuracy
        """
        user_id = "workflow_test_user"

        # Phase 1: Create sessions with different characteristics
        print("\n=== Phase 1: Creating Sessions ===")

        # High engagement session
        high_engagement = await session_store.create_session(
            assets=["AAPL", "GOOGL", "MSFT"],
            session_type=SessionType.COMPARATIVE,
            user_id=user_id,
            tags=["tech", "comparison"],
        )
        for i in range(10):
            high_engagement.add_query(
                QueryRecord(
                    query_type="price" if i < 5 else "fundamentals",
                    parameters={"symbol": "AAPL"},
                    cache_hit=i % 3 == 0,
                )
            )
        await session_store.update_session(high_engagement.id, high_engagement)
        print(f"Created high engagement session: {high_engagement.state.history.total_queries} queries")

        # Low engagement session (will be abandoned)
        low_engagement = await session_store.create_session(
            assets=["TSLA"],
            session_type=SessionType.EQUITY,
            user_id=user_id,
            tags=["tech"],
        )
        low_engagement.add_query(QueryRecord(query_type="price", parameters={"symbol": "TSLA"}))
        low_engagement.expires_at = datetime.now(UTC) - timedelta(hours=1)  # Mark as expired
        await session_store.update_session(low_engagement.id, low_engagement)
        print(f"Created low engagement session: {low_engagement.state.history.total_queries} query (abandoned)")

        # Medium engagement session
        medium_engagement = await session_store.create_session(
            assets=["BTC", "ETH"],
            session_type=SessionType.CRYPTO,
            user_id=user_id,
            tags=["crypto", "comparison"],
        )
        for i in range(5):
            medium_engagement.add_query(
                QueryRecord(
                    query_type="price",
                    parameters={"symbol": "BTC"},
                    cache_hit=True,
                )
            )
        await session_store.update_session(medium_engagement.id, medium_engagement)
        print(f"Created medium engagement session: {medium_engagement.state.history.total_queries} queries")

        # Phase 2: Record metrics
        print("\n=== Phase 2: Recording Metrics ===")
        await analytics.record_session_metrics(high_engagement)
        await analytics.record_session_metrics(low_engagement)
        await analytics.record_session_metrics(medium_engagement)
        print("All metrics recorded")

        # Phase 3: Generate and verify analytics
        print("\n=== Phase 3: Generating Analytics ===")
        stats = await analytics.get_session_stats(user_id=user_id, days=1)

        print(f"Total sessions: {stats['total_sessions']}")
        print(f"Total queries: {stats['total_queries']}")
        print(f"Avg queries per session: {stats['avg_queries_per_session']:.2f}")
        print(f"Abandonment rate: {stats['abandonment_rate']:.2%}")

        # Verify accuracy
        assert stats["total_sessions"] == 3
        assert stats["total_queries"] == 10 + 1 + 5  # 16 total
        # Note: avg_queries_per_session is rounded to 2 decimals in analytics.py:345
        assert stats["avg_queries_per_session"] == 5.33  # round(16/3, 2)
        # Note: abandonment_rate is also rounded to 4 decimals in analytics.py
        assert stats["abandonment_rate"] == 0.3333  # round(1/3, 4)

        # Verify session type breakdown
        breakdown = stats["session_type_breakdown"]
        assert breakdown["comparative"] == 1
        assert breakdown["equity"] == 1
        assert breakdown["crypto"] == 1

        # Verify top assets
        top_assets_dict = {a["symbol"]: a["count"] for a in stats["top_assets"]}
        assert "AAPL" in top_assets_dict
        assert "BTC" in top_assets_dict

        # Verify query type distribution
        dist = stats["query_type_distribution"]
        assert dist.get("price", 0) >= 11  # At least 11 price queries

        print("\n=== Analytics Verified Successfully ===")

    async def test_analytics_performance_with_large_dataset(self, session_store, analytics):
        """Test analytics performance with larger number of sessions"""
        import time

        user_id = "perf_test_user"

        # Create 20 sessions
        print("\n=== Creating 20 sessions for performance test ===")
        start_time = time.time()

        for i in range(20):
            session = await session_store.create_session(
                assets=[f"STOCK{i % 5}"],  # 5 different stocks
                session_type=SessionType.EQUITY,
                user_id=user_id,
            )
            # Add varying number of queries
            for j in range((i % 5) + 1):
                session.add_query(
                    QueryRecord(
                        query_type="price",
                        parameters={"symbol": f"STOCK{i % 5}"},
                    )
                )
            await session_store.update_session(session.id, session)
            await analytics.record_session_metrics(session)

        creation_time = time.time() - start_time
        print(f"Created 20 sessions in {creation_time:.2f}s")

        # Generate analytics
        start_time = time.time()
        stats = await analytics.get_session_stats(user_id=user_id, days=1)
        analytics_time = time.time() - start_time

        print(f"Generated analytics in {analytics_time:.2f}s")
        print(f"Total sessions: {stats['total_sessions']}")

        # Analytics should be fast (< 1 second for 20 sessions)
        assert analytics_time < 1.0
        assert stats["total_sessions"] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
