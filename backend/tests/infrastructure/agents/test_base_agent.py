"""Tests for base agent functionality."""

import pytest
from pathlib import Path

from backend.app.infrastructure.agents.base_agent import BaseAgent


class TestBaseAgent:
    """Test BaseAgent configuration and prompt loading."""

    @pytest.fixture
    def base_agent(self):
        """Create a base agent instance."""
        return BaseAgent(
            name="TestAgent",
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=500,
        )

    def test_agent_initialization(self, base_agent):
        """Test agent initialization."""
        assert base_agent.name == "TestAgent"
        assert base_agent.model == "gpt-4o-mini"
        assert base_agent.temperature == 0.3
        assert base_agent.max_tokens == 500

    def test_agent_has_openai_client(self, base_agent):
        """Test agent has initialized OpenAI client."""
        assert base_agent.client is not None
        assert hasattr(base_agent.client, "chat")

    def test_load_prompt_basic(self, base_agent):
        """Test loading basic summarization prompt."""
        prompt = base_agent._load_prompt("summarizer_basic")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "summarize" in prompt.lower() or "summary" in prompt.lower()

    def test_load_prompt_technical(self, base_agent):
        """Test loading technical prompt variant."""
        prompt = base_agent._load_prompt("summarizer_technical")
        assert isinstance(prompt, str)
        assert "technical" in prompt.lower()

    def test_load_prompt_business(self, base_agent):
        """Test loading business prompt variant."""
        prompt = base_agent._load_prompt("summarizer_business")
        assert isinstance(prompt, str)
        assert "business" in prompt.lower() or "market" in prompt.lower()

    def test_load_prompt_concise(self, base_agent):
        """Test loading concise prompt variant."""
        prompt = base_agent._load_prompt("summarizer_concise")
        assert isinstance(prompt, str)
        assert "sentence" in prompt.lower() or "30 words" in prompt

    def test_load_prompt_personalized(self, base_agent):
        """Test loading personalized prompt variant."""
        prompt = base_agent._load_prompt("summarizer_personalized")
        assert isinstance(prompt, str)
        assert "personali" in prompt.lower() or "user" in prompt.lower()

    def test_load_nonexistent_prompt(self, base_agent):
        """Test loading nonexistent prompt raises error."""
        with pytest.raises(FileNotFoundError):
            base_agent._load_prompt("nonexistent_prompt")

    def test_agent_model_configuration(self):
        """Test creating agents with different models."""
        agent_mini = BaseAgent("Test", model="gpt-4o-mini")
        agent_4o = BaseAgent("Test", model="gpt-4o")

        assert agent_mini.model == "gpt-4o-mini"
        assert agent_4o.model == "gpt-4o"

    def test_agent_temperature_range(self):
        """Test agent accepts various temperature values."""
        agent_deterministic = BaseAgent("Test", temperature=0.0)
        agent_balanced = BaseAgent("Test", temperature=0.5)
        agent_creative = BaseAgent("Test", temperature=1.0)

        assert agent_deterministic.temperature == 0.0
        assert agent_balanced.temperature == 0.5
        assert agent_creative.temperature == 1.0

    def test_agent_max_tokens_configuration(self):
        """Test agent accepts various max_tokens values."""
        agent_short = BaseAgent("Test", max_tokens=100)
        agent_medium = BaseAgent("Test", max_tokens=500)
        agent_long = BaseAgent("Test", max_tokens=2000)

        assert agent_short.max_tokens == 100
        assert agent_medium.max_tokens == 500
        assert agent_long.max_tokens == 2000

    def test_prompt_template_substitution(self, base_agent):
        """Test prompt template can be used for substitution."""
        # Load a real prompt
        prompt = base_agent._load_prompt("summarizer_basic")

        # Simulate article content
        article = "This is a test article about distributed systems."

        # Combine prompt and article
        full_input = f"{prompt}\n\nArticle:\n{article}"

        assert "Article:" in full_input
        assert article in full_input


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
