#!/usr/bin/env python3
"""
End-to-End Scenario Testing for BT Support Assistant Chat Endpoint

This script tests typical IT support questions against the /api/v1/chat endpoint
to verify that the RAG pipeline returns reasonable answers with acceptable confidence.

Usage:
    1. Start the server: python scripts/run_server.py
    2. Run this script: python scripts/run_chat_scenarios.py

The script will:
- Send predefined questions to the chat endpoint
- Check if answers contain expected keywords
- Verify minimum confidence thresholds
- Print a detailed report with pass/fail status
"""

import sys
import requests
from typing import List, Dict, Any
from dataclasses import dataclass
from colorama import init, Fore, Style

# Initialize colorama for colored terminal output
init(autoreset=True)

# ============================================
# CONFIGURATION
# ============================================

API_BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/v1/chat"
REQUEST_TIMEOUT = 30  # seconds


# ============================================
# SCENARIO DEFINITIONS
# ============================================

@dataclass
class ChatScenario:
    """Represents a test scenario for the chat endpoint"""
    name: str
    question: str
    expected_keywords: List[str]  # Keywords that should appear in answer (case-insensitive)
    min_confidence: float
    language: str = "tr"
    
    def __str__(self):
        return f"[{self.name}] {self.question}"


# Define test scenarios
SCENARIOS = [
    ChatScenario(
        name="Outlook Şifre Sıfırlama",
        question="Outlook şifremi unuttum, nasıl sıfırlarım?",
        expected_keywords=["outlook", "parola", "şifre", "sıfırlama", "bağlantı"],
        min_confidence=0.4,
    ),
    
    ChatScenario(
        name="VPN Bağlantı Sorunu",
        question="VPN'e bağlanamıyorum, ne yapmalıyım?",
        expected_keywords=["vpn", "bağlantı", "ayar", "istemci", "kimlik"],
        min_confidence=0.4,
    ),
    
    ChatScenario(
        name="Yazıcı Yazdırmıyor",
        question="Yazıcı yazdırmıyor, nasıl düzeltebilirim?",
        expected_keywords=["yazıcı", "sürücü", "bağlantı", "ayar"],
        min_confidence=0.3,
    ),
    
    ChatScenario(
        name="Laptop Yavaş Çalışıyor",
        question="Laptop çok yavaş çalışıyor, ne yapmalıyım?",
        expected_keywords=["performans", "disk", "bellek", "güncelleme", "temizlik"],
        min_confidence=0.3,
    ),
    
    ChatScenario(
        name="Email Gönderemiyorum",
        question="Email gönderemiyorum, hata veriyor",
        expected_keywords=["email", "mail", "gönder", "ayar", "sunucu"],
        min_confidence=0.3,
    ),
    
    ChatScenario(
        name="Disk Dolu Hatası",
        question="Disk alanı doldu hatası alıyorum",
        expected_keywords=["disk", "alan", "temizlik", "dosya", "silme"],
        min_confidence=0.35,
    ),
]


# ============================================
# TEST EXECUTION
# ============================================

def check_server_health() -> bool:
    """Check if the server is running and healthy"""
    try:
        health_url = f"{API_BASE_URL}/api/v1/health"
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def send_chat_request(scenario: ChatScenario) -> Dict[str, Any]:
    """Send a chat request to the API endpoint"""
    payload = {
        "query": scenario.question,
        "language": scenario.language,
    }
    
    response = requests.post(
        CHAT_ENDPOINT,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    
    response.raise_for_status()
    return response.json()


def check_keywords_in_text(text: str, keywords: List[str]) -> Dict[str, bool]:
    """Check which keywords appear in the text (case-insensitive)"""
    text_lower = text.lower()
    return {keyword: keyword.lower() in text_lower for keyword in keywords}


def evaluate_scenario(scenario: ChatScenario, response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate if the response meets the scenario expectations"""
    answer = response_data.get("answer", "")
    confidence = response_data.get("confidence", 0.0)
    sources = response_data.get("sources", [])
    
    # Check keywords
    keyword_results = check_keywords_in_text(answer, scenario.expected_keywords)
    keywords_found = sum(keyword_results.values())
    keywords_total = len(scenario.expected_keywords)
    keyword_ratio = keywords_found / keywords_total if keywords_total > 0 else 0
    
    # Check confidence
    confidence_ok = confidence >= scenario.min_confidence
    
    # Check keyword threshold (at least 50% of expected keywords)
    keywords_ok = keyword_ratio >= 0.5
    
    # Overall pass/fail
    passed = confidence_ok and keywords_ok
    
    return {
        "passed": passed,
        "confidence": confidence,
        "confidence_ok": confidence_ok,
        "keyword_results": keyword_results,
        "keywords_found": keywords_found,
        "keywords_total": keywords_total,
        "keyword_ratio": keyword_ratio,
        "keywords_ok": keywords_ok,
        "num_sources": len(sources),
        "answer_length": len(answer),
    }


def print_scenario_result(scenario: ChatScenario, evaluation: Dict[str, Any]):
    """Print a formatted result for a single scenario"""
    # Header
    status_icon = "✅" if evaluation["passed"] else "❌"
    status_color = Fore.GREEN if evaluation["passed"] else Fore.RED
    
    print(f"\n{status_color}{status_icon} {scenario.name}{Style.RESET_ALL}")
    print(f"   Question: {Fore.CYAN}{scenario.question}{Style.RESET_ALL}")
    
    # Confidence
    conf = evaluation["confidence"]
    min_conf = scenario.min_confidence
    conf_status = "✓" if evaluation["confidence_ok"] else "✗"
    conf_color = Fore.GREEN if evaluation["confidence_ok"] else Fore.YELLOW
    print(f"   Confidence: {conf_color}{conf:.2f}{Style.RESET_ALL} (threshold: {min_conf:.2f}) {conf_status}")
    
    # Keywords
    kw_found = evaluation["keywords_found"]
    kw_total = evaluation["keywords_total"]
    kw_ratio = evaluation["keyword_ratio"]
    kw_status = "✓" if evaluation["keywords_ok"] else "✗"
    kw_color = Fore.GREEN if evaluation["keywords_ok"] else Fore.YELLOW
    print(f"   Keywords: {kw_color}{kw_found}/{kw_total} ({kw_ratio:.0%}){Style.RESET_ALL} {kw_status}")
    
    # Individual keyword results
    keyword_results = evaluation["keyword_results"]
    keyword_strs = []
    for keyword, found in keyword_results.items():
        if found:
            keyword_strs.append(f"{Fore.GREEN}{keyword} ✓{Style.RESET_ALL}")
        else:
            keyword_strs.append(f"{Fore.RED}{keyword} ✗{Style.RESET_ALL}")
    print(f"             {', '.join(keyword_strs)}")
    
    # Sources
    print(f"   Sources: {evaluation['num_sources']} documents")
    print(f"   Answer length: {evaluation['answer_length']} chars")


def print_summary(results: List[Dict[str, Any]]):
    """Print overall summary"""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    pass_rate = passed / total if total > 0 else 0
    
    print("\n" + "=" * 70)
    print(f"{Fore.CYAN}SUMMARY{Style.RESET_ALL}")
    print("=" * 70)
    print(f"Total scenarios: {total}")
    print(f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
    print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
    print(f"Pass rate: {pass_rate:.0%}")
    
    if pass_rate >= 0.8:
        print(f"\n{Fore.GREEN}✅ Overall status: GOOD - Most scenarios passed{Style.RESET_ALL}")
    elif pass_rate >= 0.5:
        print(f"\n{Fore.YELLOW}⚠️  Overall status: ACCEPTABLE - Some scenarios need attention{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}❌ Overall status: POOR - Many scenarios failing{Style.RESET_ALL}")


def run_all_scenarios():
    """Run all predefined scenarios and print results"""
    print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  BT Support Assistant - End-to-End Scenario Tests               ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    
    # Check server health
    print(f"\n{Fore.YELLOW}🔍 Checking server health...{Style.RESET_ALL}")
    if not check_server_health():
        print(f"{Fore.RED}❌ ERROR: Server is not responding at {API_BASE_URL}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Please start the server first:{Style.RESET_ALL}")
        print(f"   python scripts/run_server.py")
        sys.exit(1)
    
    print(f"{Fore.GREEN}✅ Server is running{Style.RESET_ALL}")
    
    # Run scenarios
    print(f"\n{Fore.YELLOW}🚀 Running {len(SCENARIOS)} scenarios...{Style.RESET_ALL}")
    
    results = []
    
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n{Fore.CYAN}[{i}/{len(SCENARIOS)}] Testing: {scenario.name}...{Style.RESET_ALL}")
        
        try:
            response_data = send_chat_request(scenario)
            evaluation = evaluate_scenario(scenario, response_data)
            results.append(evaluation)
            print_scenario_result(scenario, evaluation)
            
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}❌ Request failed: {e}{Style.RESET_ALL}")
            results.append({
                "passed": False,
                "confidence": 0.0,
                "confidence_ok": False,
                "keywords_found": 0,
                "keywords_total": len(scenario.expected_keywords),
                "keyword_ratio": 0.0,
                "keywords_ok": False,
                "num_sources": 0,
                "answer_length": 0,
            })
        except Exception as e:
            print(f"{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
            results.append({
                "passed": False,
                "confidence": 0.0,
                "confidence_ok": False,
                "keywords_found": 0,
                "keywords_total": len(scenario.expected_keywords),
                "keyword_ratio": 0.0,
                "keywords_ok": False,
                "num_sources": 0,
                "answer_length": 0,
            })
    
    # Print summary
    print_summary(results)
    
    # Exit code
    failed_count = sum(1 for r in results if not r["passed"])
    sys.exit(0 if failed_count == 0 else 1)


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    try:
        run_all_scenarios()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Test interrupted by user{Style.RESET_ALL}")
        sys.exit(130)



