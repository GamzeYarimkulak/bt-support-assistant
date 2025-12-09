"""
Integration tests for chat scenarios.

These tests verify that the /api/v1/chat endpoint returns reasonable
answers for typical IT support questions.

Run with:
    pytest tests/test_chat_scenarios.py -v
    pytest tests/test_chat_scenarios.py -v -m integration

Note: Requires the FastAPI server to be running at http://localhost:8000
"""

import pytest
import requests
from typing import List, Dict, Any


# ============================================
# CONFIGURATION
# ============================================

API_BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/v1/chat"
REQUEST_TIMEOUT = 30


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(scope="module")
def server_available():
    """Check if the server is running before running tests"""
    try:
        health_url = f"{API_BASE_URL}/api/v1/health"
        response = requests.get(health_url, timeout=5)
        if response.status_code != 200:
            pytest.skip(f"Server not healthy at {API_BASE_URL}")
        return True
    except Exception as e:
        pytest.skip(f"Server not available at {API_BASE_URL}: {e}")


# ============================================
# SCENARIO DEFINITIONS
# ============================================

SCENARIOS = [
    {
        "name": "outlook_password_reset",
        "question": "Outlook şifremi unuttum, nasıl sıfırlarım?",
        "expected_keywords": ["outlook", "parola", "şifre", "sıfırlama", "bağlantı"],
        "min_confidence": 0.4,
        "language": "tr",
    },
    {
        "name": "vpn_connection_issue",
        "question": "VPN'e bağlanamıyorum, ne yapmalıyım?",
        "expected_keywords": ["vpn", "bağlantı", "ayar", "istemci", "kimlik"],
        "min_confidence": 0.4,
        "language": "tr",
    },
    {
        "name": "printer_not_working",
        "question": "Yazıcı yazdırmıyor, nasıl düzeltebilirim?",
        "expected_keywords": ["yazıcı", "sürücü", "bağlantı", "ayar"],
        "min_confidence": 0.3,
        "language": "tr",
    },
    {
        "name": "slow_laptop",
        "question": "Laptop çok yavaş çalışıyor, ne yapmalıyım?",
        "expected_keywords": ["performans", "disk", "bellek", "güncelleme", "temizlik"],
        "min_confidence": 0.3,
        "language": "tr",
    },
    {
        "name": "cannot_send_email",
        "question": "Email gönderemiyorum, hata veriyor",
        "expected_keywords": ["email", "mail", "gönder", "ayar", "sunucu"],
        "min_confidence": 0.3,
        "language": "tr",
    },
    {
        "name": "disk_full_error",
        "question": "Disk alanı doldu hatası alıyorum",
        "expected_keywords": ["disk", "alan", "temizlik", "dosya", "silme"],
        "min_confidence": 0.35,
        "language": "tr",
    },
]


# ============================================
# HELPER FUNCTIONS
# ============================================

def send_chat_request(question: str, language: str = "tr") -> Dict[str, Any]:
    """Send a chat request to the API endpoint"""
    payload = {
        "query": question,
        "language": language,
    }
    
    response = requests.post(
        CHAT_ENDPOINT,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    
    response.raise_for_status()
    return response.json()


def count_keywords_in_text(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in the text (case-insensitive)"""
    text_lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in text_lower)


# ============================================
# TEST CASES
# ============================================

@pytest.mark.integration
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
def test_chat_scenario(server_available, scenario):
    """
    Test that the chat endpoint returns reasonable answers for typical questions.
    
    This is an integration test that:
    - Sends a predefined question to /api/v1/chat
    - Checks that confidence meets the minimum threshold
    - Verifies that at least half of expected keywords appear in the answer
    
    These tests are not meant to be super strict - they just ensure
    that basic functionality works and future changes don't break
    typical use cases.
    """
    # Send request
    response_data = send_chat_request(
        question=scenario["question"],
        language=scenario["language"]
    )
    
    # Extract response fields
    answer = response_data.get("answer", "")
    confidence = response_data.get("confidence", 0.0)
    sources = response_data.get("sources", [])
    
    # Check confidence threshold
    assert confidence >= scenario["min_confidence"], (
        f"Confidence {confidence:.2f} is below minimum {scenario['min_confidence']:.2f}"
    )
    
    # Check keywords
    keywords_found = count_keywords_in_text(answer, scenario["expected_keywords"])
    keywords_total = len(scenario["expected_keywords"])
    keyword_ratio = keywords_found / keywords_total if keywords_total > 0 else 0
    
    # At least 50% of expected keywords should be present
    assert keyword_ratio >= 0.5, (
        f"Only {keywords_found}/{keywords_total} ({keyword_ratio:.0%}) "
        f"expected keywords found in answer. Expected at least 50%."
    )
    
    # Sanity checks
    assert len(answer) > 50, "Answer is too short (< 50 chars)"
    assert len(sources) > 0, "No sources returned (should have at least 1)"
    
    # Log success info (visible with -v flag)
    print(f"\n  ✓ Confidence: {confidence:.2f}")
    print(f"  ✓ Keywords: {keywords_found}/{keywords_total} ({keyword_ratio:.0%})")
    print(f"  ✓ Sources: {len(sources)}")
    print(f"  ✓ Answer length: {len(answer)} chars")


@pytest.mark.integration
def test_chat_endpoint_basic(server_available):
    """
    Basic smoke test for the chat endpoint.
    
    Verifies that:
    - The endpoint is accessible
    - Returns expected JSON structure
    - Handles a simple question
    """
    response_data = send_chat_request("Merhaba", language="tr")
    
    # Check response structure
    assert "answer" in response_data, "Response missing 'answer' field"
    assert "confidence" in response_data, "Response missing 'confidence' field"
    assert "has_answer" in response_data, "Response missing 'has_answer' field"
    assert "sources" in response_data, "Response missing 'sources' field"
    assert "language" in response_data, "Response missing 'language' field"
    
    # Check types
    assert isinstance(response_data["answer"], str)
    assert isinstance(response_data["confidence"], (int, float))
    assert isinstance(response_data["has_answer"], bool)
    assert isinstance(response_data["sources"], list)
    assert isinstance(response_data["language"], str)
    
    # Check bounds
    assert 0.0 <= response_data["confidence"] <= 1.0, "Confidence out of range [0, 1]"


@pytest.mark.integration
def test_chat_endpoint_invalid_language(server_available):
    """Test that endpoint handles invalid language gracefully"""
    # This should either work (fallback to default) or return proper error
    try:
        response_data = send_chat_request("test", language="invalid")
        # If it works, language should be normalized
        assert response_data["language"] in ["tr", "en"]
    except requests.exceptions.HTTPError as e:
        # Or it should return 400/422 error
        assert e.response.status_code in [400, 422]


# ============================================
# TEST SUMMARY
# ============================================

def test_scenarios_summary(server_available):
    """
    Run all scenarios and print a summary.
    
    This is useful for getting an overview of all test results at once.
    """
    print("\n" + "=" * 70)
    print("CHAT SCENARIO TEST SUMMARY")
    print("=" * 70)
    
    results = []
    
    for scenario in SCENARIOS:
        try:
            response_data = send_chat_request(
                question=scenario["question"],
                language=scenario["language"]
            )
            
            answer = response_data.get("answer", "")
            confidence = response_data.get("confidence", 0.0)
            
            keywords_found = count_keywords_in_text(answer, scenario["expected_keywords"])
            keywords_total = len(scenario["expected_keywords"])
            keyword_ratio = keywords_found / keywords_total if keywords_total > 0 else 0
            
            passed = (
                confidence >= scenario["min_confidence"] and
                keyword_ratio >= 0.5
            )
            
            results.append({
                "name": scenario["name"],
                "passed": passed,
                "confidence": confidence,
                "keyword_ratio": keyword_ratio,
            })
            
        except Exception as e:
            results.append({
                "name": scenario["name"],
                "passed": False,
                "confidence": 0.0,
                "keyword_ratio": 0.0,
            })
    
    # Print results
    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} | {result['name']:30s} | "
              f"Conf: {result['confidence']:.2f} | "
              f"Keywords: {result['keyword_ratio']:.0%}")
    
    print("=" * 70)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    pass_rate = passed_count / total_count if total_count > 0 else 0
    
    print(f"Passed: {passed_count}/{total_count} ({pass_rate:.0%})")
    
    # This test passes if at least 70% of scenarios pass
    assert pass_rate >= 0.7, (
        f"Too many scenarios failing: only {pass_rate:.0%} passed "
        f"(expected at least 70%)"
    )



