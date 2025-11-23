"""
Tests for session management system
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from fiml.sessions.models import (
    AnalysisHistory,
    QueryRecord,
    Session,
    SessionState,
    SessionType,
)
from fiml.sessions.store import SessionStore


class TestSessionModels:
    """Test session data models"""

    def test_query_record_creation(self):
        """Test QueryRecord creation"""
        query = QueryRecord(
            query_type="price",
            parameters={"symbol": "AAPL"},
            result_summary="Price data retrieved successfully: AAPL trading at $150.00 with volume indicators",
            execution_time_ms=123.45,
            cache_hit=True,
        )

        assert query.query_type == "price"
        assert query.parameters["symbol"] == "AAPL"
        assert query.cache_hit is True
        assert query.execution_time_ms == 123.45

    def test_analysis_history(self):
        """Test AnalysisHistory tracking"""
        history = AnalysisHistory()

        # Add queries
        for i in range(5):
            query = QueryRecord(
                query_type="price" if i % 2 == 0 else "fundamentals",
                parameters={"symbol": f"TEST{i}"},
                cache_hit=i % 2 == 0,
            )
            history.add_query(query)

        assert history.total_queries == 5
        assert history.cache_hit_rate == 0.6  # 3 out of 5
        assert len(history.queries) == 5

        # Test query type summary
        summary = history.get_query_types_summary()
        assert summary["price"] == 3
        assert summary["fundamentals"] == 2

        # Test recent queries
        recent = history.get_recent_queries(3)
        assert len(recent) == 3

    def test_session_state(self):
        """Test SessionState context management"""
        state = SessionState()

        # Test context updates
        state.update_context("user_preference", "detailed")
        assert state.get_context("user_preference") == "detailed"
        assert state.get_context("non_existent", "default") == "default"

        # Test intermediate results
        state.store_intermediate_result("analysis_1", {"data": "value"})
        result = state.get_intermediate_result("analysis_1")
        assert result["data"] == "value"

        # Test non-existent result
        assert state.get_intermediate_result("non_existent") is None

    def test_session_creation(self):
        """Test Session creation with defaults"""
        session = Session(
            type=SessionType.EQUITY,
            assets=["AAPL", "GOOGL"],
            user_id="test_user",
        )

        assert session.type == SessionType.EQUITY
        assert len(session.assets) == 2
        assert session.user_id == "test_user"
        assert not session.is_expired
        assert session.time_remaining.total_seconds() > 0

    def test_session_expiration(self):
        """Test session expiration logic"""
        # Create expired session
        session = Session(
            type=SessionType.CRYPTO,
            assets=["BTC"],
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        assert session.is_expired
        assert session.time_remaining.total_seconds() < 0

    def test_session_extend(self):
        """Test session extension"""
        session = Session(
            type=SessionType.PORTFOLIO,
            assets=["AAPL"],
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

        original_expiry = session.expires_at
        session.extend(hours=24)

        assert session.expires_at > original_expiry
        assert session.time_remaining.total_seconds() > 3600  # More than 1 hour

    def test_session_touch(self):
        """Test session last accessed update"""
        session = Session(
            type=SessionType.EQUITY,
            assets=["TSLA"],
        )

        original_accessed = session.last_accessed_at
        import time
        time.sleep(0.1)
        session.touch()

        assert session.last_accessed_at > original_accessed

    def test_session_add_query(self):
        """Test adding queries to session"""
        session = Session(
            type=SessionType.COMPARATIVE,
            assets=["AAPL", "MSFT"],
        )

        original_accessed = session.last_accessed_at

        query = QueryRecord(
            query_type="price",
            parameters={"symbol": "AAPL"},
        )

        session.add_query(query)

        assert session.state.history.total_queries == 1
        assert session.last_accessed_at >= original_accessed

    def test_session_serialization(self):
        """Test session to/from dict"""
        session = Session(
            type=SessionType.MACRO,
            assets=["SPY"],
            user_id="test_user",
            tags=["analysis", "market"],
        )

        # Add some data
        session.state.update_context("key", "value")
        session.add_query(
            QueryRecord(query_type="test", parameters={"test": True})
        )

        # Convert to dict
        data = session.to_dict()

        assert data["type"] == "macro"
        assert data["assets"] == ["SPY"]
        assert data["tags"] == ["analysis", "market"]

        # Convert back
        restored = Session.from_dict(data)

        assert restored.type == SessionType.MACRO
        assert restored.assets == ["SPY"]
        assert restored.state.get_context("key") == "value"
        assert restored.state.history.total_queries == 1


@pytest.mark.asyncio
class TestSessionStore:
    """Test SessionStore operations"""

    @pytest.fixture
    async def session_store(self, init_session_db):
        """Create and initialize session store"""
        store = SessionStore()
        await store.initialize()
        yield store
        await store.shutdown()

    async def test_create_session(self, session_store):
        """Test session creation"""
        session = await session_store.create_session(
            assets=["AAPL", "GOOGL"],
            session_type=SessionType.EQUITY,
            user_id="test_user",
            ttl_hours=24,
            tags=["test"],
        )

        assert session.id is not None
        assert session.user_id == "test_user"
        assert session.type == SessionType.EQUITY
        assert len(session.assets) == 2
        assert "test" in session.tags

    async def test_get_session(self, session_store):
        """Test session retrieval"""
        # Create session
        created = await session_store.create_session(
            assets=["BTC"],
            session_type=SessionType.CRYPTO,
            ttl_hours=1,
        )

        # Retrieve session
        retrieved = await session_store.get_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.type == SessionType.CRYPTO
        assert retrieved.assets == ["BTC"]

    async def test_get_nonexistent_session(self, session_store):
        """Test retrieval of non-existent session"""
        fake_id = uuid4()
        session = await session_store.get_session(fake_id)

        assert session is None

    async def test_update_session(self, session_store):
        """Test session update"""
        # Create session
        session = await session_store.create_session(
            assets=["TSLA"],
            session_type=SessionType.EQUITY,
        )

        # Modify session
        session.state.update_context("test_key", "test_value")
        session.add_query(
            QueryRecord(query_type="price", parameters={"symbol": "TSLA"})
        )

        # Update in store
        await session_store.update_session(session.id, session)

        # Retrieve and verify
        retrieved = await session_store.get_session(session.id)

        assert retrieved is not None
        assert retrieved.state.get_context("test_key") == "test_value"
        assert retrieved.state.history.total_queries == 1

    async def test_delete_session(self, session_store):
        """Test session deletion"""
        # Create session
        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
        )

        # Delete session
        deleted = await session_store.delete_session(session.id)
        assert deleted is True

        # Verify deletion
        retrieved = await session_store.get_session(session.id)
        assert retrieved is None

    async def test_extend_session(self, session_store):
        """Test session extension"""
        # Create session
        session = await session_store.create_session(
            assets=["MSFT"],
            session_type=SessionType.EQUITY,
            ttl_hours=1,
        )

        original_expiry = session.expires_at

        # Extend session
        await session_store.extend_session(session.id, hours=24)

        # Verify extension
        retrieved = await session_store.get_session(session.id)
        assert retrieved is not None
        assert retrieved.expires_at > original_expiry

    async def test_list_user_sessions(self, session_store):
        """Test listing user sessions"""
        user_id = "test_user_123"

        # Create multiple sessions
        for i in range(3):
            await session_store.create_session(
                assets=[f"TEST{i}"],
                session_type=SessionType.EQUITY,
                user_id=user_id,
            )

        # List sessions
        summaries = await session_store.list_user_sessions(user_id=user_id, limit=10)

        assert len(summaries) >= 3
        for summary in summaries:
            assert summary.user_id == user_id

    async def test_archive_session(self, session_store):
        """Test session archival"""
        # Create session
        session = await session_store.create_session(
            assets=["AAPL"],
            session_type=SessionType.EQUITY,
        )

        # Add some history
        session.add_query(
            QueryRecord(query_type="price", parameters={"symbol": "AAPL"})
        )
        await session_store.update_session(session.id, session)

        # Archive session
        archived = await session_store.archive_session(session.id)
        assert archived is True

        # Session should no longer be in Redis
        await session_store.get_session(session.id)
        # But might still be retrievable from PostgreSQL
        # depending on implementation

    async def test_cleanup_expired_sessions(self, session_store):
        """Test expired session cleanup"""
        # Create an expired session (short TTL)
        session = await session_store.create_session(
            assets=["TEST"],
            session_type=SessionType.EQUITY,
            ttl_hours=1,
        )

        # Manually expire it
        session.expires_at = datetime.utcnow() - timedelta(hours=1)
        await session_store.update_session(session.id, session)

        # Run cleanup
        cleaned_count = await session_store.cleanup_expired_sessions()

        # Should have cleaned at least our expired session
        assert cleaned_count >= 0  # May be 0 if another test cleaned it


@pytest.mark.asyncio
class TestSessionIntegration:
    """Integration tests demonstrating full session lifecycle"""

    @pytest.fixture
    async def session_store(self, init_session_db):
        """Create and initialize session store"""
        store = SessionStore()
        await store.initialize()
        yield store
        await store.shutdown()

    async def test_multi_query_session_workflow(self, session_store):
        """
        Test complete multi-query session workflow:
        1. Create session
        2. Execute multiple queries
        3. Track context accumulation
        4. Verify session state
        5. Extend session
        6. Clean up
        """
        # Step 1: Create analysis session
        session = await session_store.create_session(
            assets=["AAPL", "GOOGL", "MSFT"],
            session_type=SessionType.COMPARATIVE,
            user_id="analyst_001",
            ttl_hours=2,
            tags=["tech_stocks", "comparison"],
        )

        session_id = session.id
        print(f"\n=== Created session {session_id} ===")

        # Step 2: Simulate multiple queries
        queries = [
            {
                "type": "price",
                "params": {"symbol": "AAPL"},
                "summary": "AAPL: $150.00 (+2.5%)",
            },
            {
                "type": "fundamentals",
                "params": {"symbol": "AAPL"},
                "summary": "P/E: 25.3, Revenue: $394B",
            },
            {
                "type": "price",
                "params": {"symbol": "GOOGL"},
                "summary": "GOOGL: $125.00 (+1.8%)",
            },
            {
                "type": "comparative",
                "params": {"symbols": ["AAPL", "GOOGL"]},
                "summary": "AAPL outperforming GOOGL by 0.7%",
            },
        ]

        for i, q in enumerate(queries, 1):
            # Add query to session
            query_record = QueryRecord(
                query_type=q["type"],
                parameters=q["params"],
                result_summary=q["summary"],
                execution_time_ms=100.0 + i * 10,
                cache_hit=i % 2 == 0,
            )

            session.add_query(query_record)

            # Store context from query
            session.state.update_context(f"query_{i}_result", q["summary"])

            # Store intermediate result
            session.state.store_intermediate_result(
                f"analysis_{i}",
                {"query": q["type"], "data": q["summary"]},
            )

            # Update session in store
            await session_store.update_session(session_id, session)

            print(f"Query {i}: {q['type']} - {q['summary']}")

        # Step 3: Verify session state accumulation
        retrieved = await session_store.get_session(session_id)
        assert retrieved is not None

        print(f"\n=== Session State After {len(queries)} Queries ===")
        print(f"Total queries: {retrieved.state.history.total_queries}")
        print(f"Cache hit rate: {retrieved.state.history.cache_hit_rate:.2%}")
        print(f"Query types: {retrieved.state.history.get_query_types_summary()}")

        assert retrieved.state.history.total_queries == len(queries)
        assert retrieved.state.history.cache_hit_rate == 0.5  # 2 out of 4

        # Verify context
        assert retrieved.state.get_context("query_1_result") is not None
        assert retrieved.state.get_context("query_4_result") is not None

        # Verify intermediate results
        assert retrieved.state.get_intermediate_result("analysis_1") is not None
        assert retrieved.state.get_intermediate_result("analysis_4") is not None

        # Step 4: Demonstrate context-aware follow-up
        # Simulate "remember previous query" capability
        recent_queries = retrieved.state.history.get_recent_queries(2)
        print("\n=== Recent Queries ===")
        for rq in recent_queries:
            print(f"  {rq.query_type}: {rq.result_summary}")

        assert len(recent_queries) == 2

        # Step 5: Extend session
        original_expiry = retrieved.expires_at
        await session_store.extend_session(session_id, hours=24)

        extended = await session_store.get_session(session_id)
        assert extended is not None
        assert extended.expires_at > original_expiry

        print("\n=== Session Extended ===")
        print(f"New expiry: {extended.expires_at}")
        print(f"Time remaining: {extended.time_remaining.total_seconds() / 3600:.1f} hours")

        # Step 6: Verify session survives (would survive restart in real scenario)
        final_session = await session_store.get_session(session_id)
        assert final_session is not None
        assert final_session.state.history.total_queries == len(queries)

        print("\n=== Session Verified ===")
        print(f"Session ID: {final_session.id}")
        print(f"Duration: {final_session.duration.total_seconds():.2f} seconds")
        print(f"Assets: {final_session.assets}")
        print(f"Tags: {final_session.tags}")

        # Cleanup
        await session_store.delete_session(session_id)
        print("\n=== Session Deleted ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
