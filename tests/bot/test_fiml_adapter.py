"""
Tests for FIMLEducationalDataAdapter (Component 10)
Tests educational data formatting and FIML integration
"""
import pytest
from datetime import datetime
from fiml.bot.education.fiml_adapter import FIMLEducationalDataAdapter


class TestFIMLEducationalDataAdapter:
    """Test suite for FIML educational data adapter"""
    
    def test_init_adapter(self):
        """Test adapter initialization"""
        adapter = FIMLEducationalDataAdapter()
        assert adapter is not None
    
    def test_format_price_movement(self):
        """Test price movement interpretation"""
        adapter = FIMLEducationalDataAdapter()
        
        # Minimal movement (< 0.5%)
        explanation = adapter.explain_price_movement(100.0, 100.3, for_beginners=True)
        assert 'minimal' in explanation.lower() or 'small' in explanation.lower()
        
        # Moderate movement (0.5-2%)
        explanation = adapter.explain_price_movement(100.0, 101.5, for_beginners=True)
        assert 'moderate' in explanation.lower() or 'notable' in explanation.lower()
        
        # Significant movement (2-5%)
        explanation = adapter.explain_price_movement(100.0, 103.5, for_beginners=True)
        assert 'significant' in explanation.lower() or 'strong' in explanation.lower()
        
        # Exceptional movement (> 5%)
        explanation = adapter.explain_price_movement(100.0, 107.0, for_beginners=True)
        assert 'exceptional' in explanation.lower() or 'major' in explanation.lower()
    
    def test_format_volume_analysis(self):
        """Test volume analysis interpretation"""
        adapter = FIMLEducationalDataAdapter()
        
        # Low volume
        explanation = adapter.explain_volume(1000000, avg_volume=2000000)
        assert 'low' in explanation.lower()
        
        # Normal volume
        explanation = adapter.explain_volume(2000000, avg_volume=2000000)
        assert 'normal' in explanation.lower() or 'typical' in explanation.lower()
        
        # High volume
        explanation = adapter.explain_volume(5000000, avg_volume=2000000)
        assert 'high' in explanation.lower() or 'elevated' in explanation.lower()
    
    def test_format_pe_ratio(self):
        """Test P/E ratio explanation"""
        adapter = FIMLEducationalDataAdapter()
        
        # Low P/E (< 15)
        explanation = adapter.explain_pe_ratio(12.5)
        assert 'undervalued' in explanation.lower() or 'low' in explanation.lower()
        
        # Fair P/E (15-25)
        explanation = adapter.explain_pe_ratio(20.0)
        assert 'fair' in explanation.lower() or 'reasonable' in explanation.lower()
        
        # Growth P/E (25-40)
        explanation = adapter.explain_pe_ratio(32.0)
        assert 'growth' in explanation.lower()
        
        # High P/E (> 40)
        explanation = adapter.explain_pe_ratio(55.0)
        assert 'high' in explanation.lower() or 'expensive' in explanation.lower()
    
    def test_format_market_cap(self):
        """Test market cap classification"""
        adapter = FIMLEducationalDataAdapter()
        
        # Micro cap (< 300M)
        explanation = adapter.explain_market_cap(200_000_000)
        assert 'micro' in explanation.lower()
        
        # Small cap (300M - 2B)
        explanation = adapter.explain_market_cap(1_000_000_000)
        assert 'small' in explanation.lower()
        
        # Mid cap (2B - 10B)
        explanation = adapter.explain_market_cap(5_000_000_000)
        assert 'mid' in explanation.lower()
        
        # Large cap (10B - 200B)
        explanation = adapter.explain_market_cap(50_000_000_000)
        assert 'large' in explanation.lower()
        
        # Mega cap (> 200B)
        explanation = adapter.explain_market_cap(500_000_000_000)
        assert 'mega' in explanation.lower()
    
    def test_educational_snapshot_lesson_format(self):
        """Test educational snapshot for lesson context"""
        adapter = FIMLEducationalDataAdapter()
        
        snapshot = adapter.create_educational_snapshot(
            symbol="AAPL",
            price=175.0,
            volume=50_000_000,
            market_cap=2_800_000_000_000,
            pe_ratio=28.5,
            format_type="lesson"
        )
        
        assert snapshot is not None
        assert 'symbol' in snapshot or 'price' in str(snapshot).lower()
    
    def test_educational_snapshot_quiz_format(self):
        """Test educational snapshot for quiz context"""
        adapter = FIMLEducationalDataAdapter()
        
        snapshot = adapter.create_educational_snapshot(
            symbol="TSLA",
            price=250.0,
            volume=100_000_000,
            format_type="quiz"
        )
        
        assert snapshot is not None
        # Quiz format should be concise
        assert isinstance(snapshot, (dict, str))
    
    def test_educational_snapshot_mentor_format(self):
        """Test educational snapshot for AI mentor context"""
        adapter = FIMLEducationalDataAdapter()
        
        snapshot = adapter.create_educational_snapshot(
            symbol="GOOGL",
            price=140.0,
            format_type="mentor"
        )
        
        assert snapshot is not None
        # Mentor format should be conversational
        assert isinstance(snapshot, (dict, str))
    
    def test_chart_description(self):
        """Test chart description for text-based UI"""
        adapter = FIMLEducationalDataAdapter()
        
        price_data = [100, 102, 101, 105, 107, 106]
        description = adapter.describe_chart(price_data, chart_type="line")
        
        assert description is not None
        assert len(description) > 0
        # Should describe trend
        assert isinstance(description, str)
    
    def test_safe_datetime_handling(self):
        """Test type-safe datetime handling"""
        adapter = FIMLEducationalDataAdapter()
        
        # Should handle datetime objects
        now = datetime.now()
        freshness = adapter.calculate_data_freshness(now)
        assert freshness is not None
        
        # Should handle None gracefully
        freshness = adapter.calculate_data_freshness(None)
        assert freshness is not None or freshness == "unknown"
    
    def test_error_fallback(self):
        """Test graceful fallback on FIML errors"""
        adapter = FIMLEducationalDataAdapter()
        
        # Should handle missing data gracefully
        snapshot = adapter.create_educational_snapshot(
            symbol="INVALID",
            price=None,
            use_fallback=True
        )
        
        assert snapshot is not None
    
    def test_beginner_vs_advanced_language(self):
        """Test language adaptation for skill level"""
        adapter = FIMLEducationalDataAdapter()
        
        beginner = adapter.explain_price_movement(100, 105, for_beginners=True)
        advanced = adapter.explain_price_movement(100, 105, for_beginners=False)
        
        assert beginner is not None
        assert advanced is not None
        # Beginner should use simpler terms
        assert isinstance(beginner, str)
        assert isinstance(advanced, str)
    
    def test_multiple_metrics_explanation(self):
        """Test explaining multiple metrics together"""
        adapter = FIMLEducationalDataAdapter()
        
        explanation = adapter.explain_multiple_metrics({
            'price': 175.0,
            'volume': 50_000_000,
            'pe_ratio': 28.5,
            'market_cap': 2_800_000_000_000
        })
        
        assert explanation is not None
        assert isinstance(explanation, (str, dict))
