"""
Tests for dynamic weighting functionality.
"""

import pytest
from core.retrieval.dynamic_weighting import DynamicWeightComputer


def test_short_technical_query():
    """Short technical queries should favor embeddings (lower alpha)."""
    computer = DynamicWeightComputer()

    alpha = computer.compute_alpha("VPN connection")
    assert alpha < 0.5, "Short technical queries should favor embeddings"
    assert 0.2 <= alpha <= 0.4, f"Alpha should be in semantic range, got {alpha}"


def test_long_technical_query():
    """Long technical queries should still favor embeddings when technical term density is high."""
    computer = DynamicWeightComputer()

    query = "Outlook email account login fails and the password reset link never arrives"
    alpha = computer.compute_alpha(query)
    assert alpha < 0.5, "Technical queries should favor embeddings even when descriptive"
    assert 0.2 <= alpha <= 0.4, f"Alpha should be in semantic range, got {alpha}"


def test_long_free_form_query():
    """Long non-technical free-form queries should favor BM25 (higher alpha)."""
    computer = DynamicWeightComputer()

    query = "I have a detailed question about the support process and would like a step by step explanation from the help desk"
    alpha = computer.compute_alpha(query)
    assert alpha > 0.5, "Long non-technical queries should favor BM25"
    assert 0.6 <= alpha <= 0.8, f"Alpha should be in keyword range, got {alpha}"


def test_medium_balanced_query():
    """Medium queries should be balanced."""
    computer = DynamicWeightComputer()

    query = "support request status update"
    alpha = computer.compute_alpha(query)
    assert 0.4 <= alpha <= 0.6, f"Medium queries should be balanced, got {alpha}"


def test_technical_term_detection():
    """Technical terms should be detected correctly."""
    computer = DynamicWeightComputer()

    query = "VPN connection error authentication failed"
    characteristics = computer.get_query_characteristics(query)

    assert characteristics["technical_term_count"] > 0
    assert characteristics["technical_ratio"] > 0.3
    assert characteristics["computed_alpha"] < 0.5


def test_query_characteristics():
    """Query characteristics should be computed correctly."""
    computer = DynamicWeightComputer()

    query = "Outlook password reset"
    chars = computer.get_query_characteristics(query)

    assert "word_count" in chars
    assert "char_count" in chars
    assert "technical_term_count" in chars
    assert "technical_ratio" in chars
    assert "is_short" in chars
    assert "is_long" in chars
    assert "computed_alpha" in chars
    assert 0.0 <= chars["computed_alpha"] <= 1.0


def test_alpha_bounds():
    """Alpha should always be within valid bounds."""
    computer = DynamicWeightComputer()

    test_queries = [
        "VPN",
        "Outlook password",
        "Printer cannot print how can this be fixed",
        "Email cannot be sent because the server connection fails and authentication is unsuccessful",
    ]

    for query in test_queries:
        alpha = computer.compute_alpha(query)
        assert 0.2 <= alpha <= 0.8, f"Alpha out of bounds for query '{query}': {alpha}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
