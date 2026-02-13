"""Tests for token tracking functionality."""

from datetime import date
from decimal import Decimal

import pytest

from app.infrastructure.agents.token_tracker import TokenTracker, PRICING


class TestTokenTracker:
    """Test TokenTracker cost calculation and usage tracking."""

    @pytest.fixture
    def token_tracker(self):
        """Create token tracker without database (mock session)."""
        class MockDB:
            async def scalar(self, stmt):
                return None
            async def execute(self, stmt):
                pass
            async def scalars(self, stmt):
                return iter([])
            async def commit(self):
                pass
            def add(self, obj):
                pass

        return TokenTracker(MockDB())

    def test_calculate_cost_gpt4o_mini(self, token_tracker):
        """Test cost calculation for GPT-4o-mini."""
        # 1M input tokens at $0.15, 1M output tokens at $0.60
        cost = token_tracker.calculate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.75, rel=1e-2)

    def test_calculate_cost_gpt4o(self, token_tracker):
        """Test cost calculation for GPT-4o."""
        # 1M input tokens at $5.00, 1M output tokens at $15.00
        cost = token_tracker.calculate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost == pytest.approx(20.0, rel=1e-2)

    def test_calculate_cost_500_tokens(self, token_tracker):
        """Test cost calculation for typical usage."""
        # 150 input tokens + 350 output tokens (typical summary)
        cost = token_tracker.calculate_cost("gpt-4o-mini", 150, 350)
        expected = (150 / 1_000_000 * 0.15) + (350 / 1_000_000 * 0.60)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_zero_tokens(self, token_tracker):
        """Test cost calculation with zero tokens."""
        cost = token_tracker.calculate_cost("gpt-4o-mini", 0, 0)
        assert cost == 0.0

    def test_calculate_cost_unknown_model(self, token_tracker):
        """Test cost calculation for unknown model."""
        cost = token_tracker.calculate_cost("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_pricing_dictionary(self):
        """Test pricing dictionary contains expected models."""
        assert "gpt-4o-mini" in PRICING
        assert "gpt-4o" in PRICING
        assert PRICING["gpt-4o-mini"]["input"] == 0.150
        assert PRICING["gpt-4o-mini"]["output"] == 0.600

    def test_group_by_model(self, token_tracker):
        """Test grouping usage by model."""
        class MockUsage:
            def __init__(self, model, tokens, cost):
                self.model = model
                self.total_tokens = tokens
                self.cost_usd = Decimal(str(cost))
                self.request_count = 1

        records = [
            MockUsage("gpt-4o-mini", 500, 0.10),
            MockUsage("gpt-4o-mini", 600, 0.12),
            MockUsage("gpt-4o", 1000, 2.00),
        ]

        result = token_tracker._group_by_model(records)

        assert result["gpt-4o-mini"]["tokens"] == 1100
        assert result["gpt-4o-mini"]["cost"] == pytest.approx(0.22, rel=1e-2)
        assert result["gpt-4o-mini"]["requests"] == 2
        assert result["gpt-4o"]["tokens"] == 1000

    def test_group_by_date(self, token_tracker):
        """Test grouping usage by date."""
        class MockUsage:
            def __init__(self, date_val, tokens, cost):
                self.date = date_val
                self.total_tokens = tokens
                self.cost_usd = Decimal(str(cost))
                self.request_count = 1

        today = date.today()
        yesterday = date.fromordinal(today.toordinal() - 1)

        records = [
            MockUsage(today, 500, 0.10),
            MockUsage(today, 600, 0.12),
            MockUsage(yesterday, 1000, 0.20),
        ]

        result = token_tracker._group_by_date(records)

        assert result[str(today)]["tokens"] == 1100
        assert result[str(today)]["cost"] == pytest.approx(0.22, rel=1e-2)
        assert result[str(yesterday)]["tokens"] == 1000

    def test_realistic_summarization_cost(self, token_tracker):
        """Test cost calculation for realistic summarization operation."""
        # Typical: 150 input tokens (article), 350 output tokens (summary)
        # 200 posts per day
        daily_cost = 200 * token_tracker.calculate_cost(
            "gpt-4o-mini", 150, 350
        )
        # Should be roughly $0.03/day for 200 posts
        assert daily_cost < 0.05  # Conservative upper bound

    def test_cost_scaling(self, token_tracker):
        """Test cost scales linearly with token count."""
        cost_1000 = token_tracker.calculate_cost("gpt-4o-mini", 1000, 1000)
        cost_2000 = token_tracker.calculate_cost("gpt-4o-mini", 2000, 2000)

        assert cost_2000 == pytest.approx(cost_1000 * 2, rel=1e-6)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
