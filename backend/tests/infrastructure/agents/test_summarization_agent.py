"""Tests for summarization agent."""

import pytest

from app.infrastructure.agents.summarization_agent import (
    SummaryOutput,
    create_summarization_agent,
)


class TestSummarizationAgent:
    """Test summarization agent creation and configuration."""

    def test_create_basic_agent(self):
        """Test creating basic summarization agent."""
        agent = create_summarization_agent(prompt_type="basic")

        assert agent.name == "SummarizationAgent"
        assert agent.model == "gpt-4o-mini"
        assert agent.temperature == 0.3
        assert agent.max_tokens == 500

    def test_create_technical_agent(self):
        """Test creating technical variant agent."""
        agent = create_summarization_agent(prompt_type="technical")

        assert agent.name == "SummarizationAgent"
        assert hasattr(agent, "instructions")
        assert len(agent.instructions) > 0
        assert "technical" in agent.instructions.lower()

    def test_create_business_agent(self):
        """Test creating business variant agent."""
        agent = create_summarization_agent(prompt_type="business")

        assert agent.name == "SummarizationAgent"
        assert hasattr(agent, "instructions")
        assert "business" in agent.instructions.lower() or "market" in agent.instructions.lower()

    def test_create_concise_agent(self):
        """Test creating concise variant agent."""
        agent = create_summarization_agent(prompt_type="concise")

        assert agent.name == "SummarizationAgent"
        assert hasattr(agent, "instructions")
        assert len(agent.instructions) > 0

    def test_create_personalized_agent(self):
        """Test creating personalized variant agent."""
        agent = create_summarization_agent(prompt_type="personalized")

        assert agent.name == "SummarizationAgent"
        assert hasattr(agent, "instructions")
        assert len(agent.instructions) > 0

    def test_create_agent_with_custom_model(self):
        """Test creating agent with custom model."""
        agent = create_summarization_agent(
            prompt_type="basic", model="gpt-4o"
        )

        assert agent.model == "gpt-4o"

    def test_create_agent_fallback_to_basic(self):
        """Test creation falls back to basic if variant not found."""
        # This will try to load 'nonexistent' and fallback to 'basic'
        agent = create_summarization_agent(prompt_type="nonexistent")

        # Should fallback to basic
        assert agent.name == "SummarizationAgent"
        assert hasattr(agent, "instructions")
        # Instructions should be from basic prompt
        assert len(agent.instructions) > 0

    def test_summary_output_model(self):
        """Test SummaryOutput Pydantic model."""
        summary = SummaryOutput(
            summary="This is a test summary.",
            key_points=["Point 1", "Point 2"],
            technical_level="intermediate",
            confidence=0.85,
        )

        assert summary.summary == "This is a test summary."
        assert len(summary.key_points) == 2
        assert summary.technical_level == "intermediate"
        assert summary.confidence == 0.85

    def test_summary_output_defaults(self):
        """Test SummaryOutput defaults."""
        summary = SummaryOutput(summary="Test")

        assert summary.summary == "Test"
        assert summary.key_points == []
        assert summary.technical_level == "intermediate"
        assert summary.confidence == 0.8

    def test_summary_output_validation(self):
        """Test SummaryOutput type validation."""
        # Valid case
        summary = SummaryOutput(
            summary="Test",
            key_points=["point"],
            technical_level="advanced",
            confidence=0.9,
        )
        assert summary.technical_level == "advanced"

    def test_agent_temperature_for_consistency(self):
        """Test agent uses low temperature for consistent output."""
        agent = create_summarization_agent()
        # Low temperature (0.3) ensures consistent summaries
        assert agent.temperature < 0.5

    def test_agent_max_tokens_reasonable(self):
        """Test agent has reasonable max tokens for summaries."""
        agent = create_summarization_agent()
        # 500 tokens should be enough for 2-3 sentences
        assert agent.max_tokens >= 200
        assert agent.max_tokens <= 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
