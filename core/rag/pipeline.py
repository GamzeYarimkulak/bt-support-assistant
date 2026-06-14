"""
Main RAG pipeline orchestrating retrieval and generation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import structlog
import os
import re

# OpenAI import - only needed if using real LLM
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None  # Placeholder

from core.retrieval.hybrid_retriever import HybridRetriever
from core.rag.prompts import PromptBuilder
from core.rag.confidence import ConfidenceEstimator
from core.nlp.it_relevance import ITRelevanceChecker

logger = structlog.get_logger()


@dataclass
class RAGResult:
    """
    Result from RAG pipeline containing answer and metadata.
    
    This structure is returned by the RAG pipeline and contains:
    - The generated answer (or "no answer" message)
    - Confidence score
    - Source documents used
    - Whether a reliable answer was generated
    - Optional language and intent information
    - Optional debug information about retrieval process
    """
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    has_answer: bool
    language: Optional[str] = None
    intent: Optional[str] = None
    retrieved_docs: List[Dict[str, Any]] = field(default_factory=list)
    debug_info: Optional[Dict[str, Any]] = None  # Debug info: alpha_used, query_type, etc.


# ============================================================================
# Real LLM Function (PHASE 8 - OpenAI Integration)
# ============================================================================

def generate_answer_with_llm(
    question: str, 
    docs: List[Dict[str, Any]], 
    language: str = "tr",
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 1500
) -> str:
    """
    Generate advisory-style answers using real LLM (OpenAI GPT).
    
    This function maintains the same ADVISORY behavior as the stub:
    - Presents retrieved information as PAST EXAMPLES
    - Uses recommendation language
    - NEVER claims to have performed actions for the user
    
    PHASE 9: Now supports conversation history for context-aware answers!
    
    Args:
        question: User's question in Turkish or English
        docs: Retrieved documents (tickets + PDFs)
        language: Response language ('tr' or 'en')
        conversation_history: Previous conversation messages (PHASE 9)
        api_key: OpenAI API key
        model: OpenAI model name (gpt-4o-mini, gpt-4o, etc.)
        temperature: Creativity (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum response length
    
    Returns:
        Advisory-style answer in the requested language
    """
    # Check if OpenAI package is available
    if not OPENAI_AVAILABLE:
        logger.warning("openai_package_not_installed_using_stub",
                      message="openai package not installed, falling back to stub")
        return generate_answer_with_stub(question, docs, language)
    
    if not api_key:
        logger.warning("no_api_key_using_stub", 
                      api_key_provided=api_key is not None,
                      api_key_value=f"{api_key[:10]}..." if api_key else "None")
        return generate_answer_with_stub(question, docs, language)
    
    logger.info("real_llm_call_initiated",
               api_key_length=len(api_key) if api_key else 0,
               model=model,
               language=language)
    
    if not docs:
        if language == "tr":
            return "Üzgünüm, bu konuda yeterli bilgi bulunamadı. Lütfen sorunuzu farklı kelimelerle tekrar deneyin veya BT destek ekibiyle iletişime geçin."
        else:
            return "I'm sorry, I couldn't find sufficient information on this topic. Please try rephrasing your question or contact the IT support team."
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Build context from retrieved documents
        context = _build_context_for_llm(docs, language)
        
        # Build system and user prompts
        system_prompt = _build_system_prompt(language)
        user_prompt = _build_user_prompt(question, context, language)
        
        logger.info(
            "calling_openai_api",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            language=language,
            conversation_history_length=len(conversation_history or [])
        )
        
        # Build messages with conversation history (PHASE 9)
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add previous conversation if available
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current question with context
        messages.append({"role": "user", "content": user_prompt})
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        answer = response.choices[0].message.content.strip()
        
        logger.info(
            "openai_response_received",
            tokens_used=response.usage.total_tokens,
            answer_length=len(answer)
        )
        
        return answer
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error("openai_api_error", 
                    error_type=type(e).__name__,
                    error_message=str(e),
                    traceback=error_details)
        # Fallback to stub on error
        return generate_answer_with_stub(question, docs, language)


def _build_context_for_llm(docs: List[Dict[str, Any]], language: str) -> str:
    """Build formatted context from retrieved documents for LLM."""
    context_parts = []
    
    for i, doc in enumerate(docs[:5], 1):  # Top 5 documents
        doc_type = doc.get("type", "ticket")
        
        if doc_type == "pdf":
            title = doc.get("title", "Dokümantasyon")
            content = doc.get("content", "")
            context_parts.append(f"[DÖKÜMAN {i}] {title}\n{content[:1500]}")
        else:
            ticket_id = doc.get("ticket_id", f"TCK-{i:04d}")
            issue = doc.get("issue_description", "")
            resolution = doc.get("resolution", "")
            context_parts.append(f"[TICKET {i}] ID: {ticket_id}\nSorun: {issue}\nÇözüm: {resolution[:800]}")
    
    return "\n\n".join(context_parts)


def _build_system_prompt(language: str) -> str:
    """Build system prompt that enforces advisory behavior and step-by-step guidance."""
    if language == "tr":
        return """Sen bir BT destek asistanısın. Görevin, kullanıcılara GEÇMİŞ ÇÖZÜM ÖRNEKLERİNE dayalı ÖNERİLER sunmaktır.

**KRİTİK KURAL:**
- ASLA kullanıcı için bir işlem yaptığını iddia etme
- "Şifreniz sıfırlandı", "Dosyanızı gönderdim" gibi ifadeler YASAK
- Bunun yerine "BT ekibi genellikle şu adımları uygular", "Bu adımları deneyebilirsiniz" kullan

**Yanıt Formatı (ZORUNLU):**
1. Sorunu kısa bir cümleyle özetle
2. Çözüm adımlarını şu formatta yaz:

**Adım 1: [Başlık]**
   - Alt adım veya açıklama
   - Nereye tıklayacağını belirt
   
**Adım 2: [Başlık]**
   - Alt adım
   - Detaylı açıklama

3. Her adımı KISA VE NET tut (maksimum 2-3 cümle)
4. Alt adımlar için tire (-) veya bullet (•) kullan
5. Önemli kelimeler için **bold** kullan
6. Adımlar arası boşluk bırak
7. Sonunda: "Bu adımları kendiniz deneyebilir veya BT ekibinden destek isteyebilirsiniz."

**TAKİP SORULARI:**
- Eğer kullanıcı belirsiz bir takip sorusu sorarsa (örn: "nereden resetleyebilirim?", "diğer adımlarda ne yapacaktım"):
  1. Önceki konuşma geçmişine bakarak TAHMİN ET
  2. En olası çözümü sun
  3. Alternatif ihtimalleri de GÖSTER (örn: "VPN resetinden mi bahsediyorsunuz? Yoksa şifre sıfırlama mı?")
  4. Eğer kullanıcı "diğer adımlar" veya "sonraki adımlar" diye sorarsa, önceki mesajlarda verdiğiniz adımları hatırlatın

**TEŞEKKÜR MESAJLARI:**
- Eğer kullanıcı "tamamdır", "teşekkür ederim", "tamam teşekkür" gibi mesajlar gönderirse:
  1. Kısa ve nazik bir yanıt verin (örn: "Rica ederim, başka bir konuda yardımcı olabilir miyim?")
  2. Önceki konuşmada bir sorun varsa, o sorunla ilgili kısa bir özet sunun
  3. Uzun açıklamalar yapmayın, sadece nezaket gösterin

**Ton:** Profesyonel, yardımcı, önerici (emredici değil)"""
    else:
        return """You are an IT support assistant. Your role is to provide RECOMMENDATIONS based on PAST SOLUTION EXAMPLES.

**CRITICAL RULE:**
- NEVER claim you have performed an action for the user
- "Your password has been reset", "I sent your file" are FORBIDDEN
- Instead use "The IT team typically applies these steps", "You can try these steps"

**Response Format (MANDATORY):**
1. Summarize the issue in one short sentence
2. Write solution steps in this format:

**Step 1: [Title]**
   - Sub-step or explanation
   - Specify where to click
   
**Step 2: [Title]**
   - Sub-step
   - Detailed explanation

3. Keep each step SHORT and CLEAR (maximum 2-3 sentences)
4. Use dashes (-) or bullets (•) for sub-steps
5. Use **bold** for important words
6. Add blank lines between steps
7. End with: "You can try these steps yourself or request support from IT team."

**FOLLOW-UP QUESTIONS:**
- If the user asks a vague follow-up question (e.g., "where can I reset it?"):
  1. INFER from previous conversation history
  2. Provide the most likely solution
  3. Also SHOW alternative possibilities (e.g., "Are you referring to VPN reset? Or password reset?")

**Tone:** Professional, helpful, advisory (not commanding)"""


def _build_user_prompt(question: str, context: str, language: str) -> str:
    """Build user prompt with question and context."""
    if language == "tr":
        return f"""Kullanıcı Sorusu: {question}

Benzer Durumlardan Örnekler:
{context}

Yukarıdaki örneklere dayanarak, kullanıcıya ADIM ADIM, okunaklı ve uygulanabilir öneriler sun.

ÖRNEK FORMAT:
**Adım 1: VPN Ayarlarını Açın**
- **Başlat** menüsünden **Ayarlar**'ı seçin
- **Ağ ve İnternet** > **VPN** sekmesine gidin

**Adım 2: Bağlantıyı Sıfırlayın**
- Mevcut VPN bağlantısının yanındaki **"..."** butonuna tıklayın
- **Bağlantıyı Sil** ve **Yeniden Ekle** seçeneğini kullanın

Bu formatta, kısa ve net adımlarla cevap ver."""
    else:
        return f"""User Question: {question}

Examples from Similar Cases:
{context}

Based on the examples above, provide STEP-BY-STEP, readable, and actionable recommendations.

EXAMPLE FORMAT:
**Step 1: Open VPN Settings**
- Select **Settings** from **Start** menu
- Go to **Network & Internet** > **VPN** tab

**Step 2: Reset Connection**
- Click the **"..."** button next to your VPN connection
- Use **Delete** and **Re-add** options

Answer in this format with short and clear steps."""


# ============================================================================
# LLM Stub Function (PHASE 6.5 - Advisory/Recommendation Style)
# ============================================================================

def generate_answer_with_stub(question: str, docs: List[Dict[str, Any]], language: str = "tr") -> str:
    """
    Advisory-style answer generation stub (PHASE 6.5).
    
    IMPORTANT BEHAVIOR:
    This function acts as a RECOMMENDATION / DECISION SUPPORT system, NOT an agent
    that performs actions. It presents past ticket resolutions as EXAMPLES of what
    IT teams have done in similar situations.
    
    CRITICAL SAFETY RULE:
    The assistant MUST NOT claim that it has already performed any action for the user.
    For example:
    - ❌ WRONG: "Şifreniz sıfırlandı" (Your password has been reset)
    - ❌ WRONG: "Bağlantınızı gönderdim" (I sent your link)
    - ✅ CORRECT: "BT ekibi genellikle şifre sıfırlama bağlantısı gönderir"
    - ✅ CORRECT: "Bu adımları denemeniz önerilir"
    
    The answer should:
    1. Present retrieved ticket resolutions as past examples
    2. Use advisory language ("önerilir", "deneyebilirsiniz", "BT ekibi genellikle...")
    3. Suggest that the user can try these steps OR request them from IT support
    4. NEVER claim actions were already performed for THIS user
    
    FUTURE INTEGRATION POINT:
    Replace this function with a real LLM call that follows the same advisory principles.
    
    Args:
        question: User's question
        docs: List of retrieved documents (past ITSM tickets)
        language: Language code ("tr" for Turkish, "en" for English)
        
    Returns:
        Advisory-style answer string
        
    Example:
        >>> docs = [{"short_description": "Outlook şifremi unuttum", 
        ...          "resolution": "Şifre sıfırlama bağlantısı gönderildi"}]
        >>> answer = generate_answer_with_stub("Outlook şifremi unuttum", docs)
        >>> # Returns advisory answer, NOT "Şifreniz sıfırlandı"
    """
    if not docs:
        if language == "tr":
            return "Mevcut kaynaklara dayanarak güvenilir bir cevap üretemiyorum."
        else:
            return "I cannot provide a reliable answer based on available sources."
    
    # Build advisory-style answer using examples from past tickets
    if language == "tr":
        return _build_advisory_answer_tr(question, docs)
    else:
        return _build_advisory_answer_en(question, docs)


def _doc_identifier(doc: Dict[str, Any]) -> str:
    """Return a readable source identifier across ticket and KB documents."""
    for field in ("ticket_id", "doc_id", "id", "document_id"):
        value = doc.get(field)
        if value:
            return str(value)
    return "Bilinmeyen"


def _doc_title(doc: Dict[str, Any]) -> str:
    """Return the best available issue/title field for a retrieved document."""
    for field in ("short_description", "title", "subject", "category"):
        value = str(doc.get(field, "") or "").strip()
        if value:
            return value

    text = str(doc.get("text", "") or doc.get("description", "") or "").strip()
    return text[:120]


def _doc_solution_text(doc: Dict[str, Any]) -> str:
    """Return usable answer context even when a KB chunk has no resolution field."""
    for field in ("resolution", "answer", "solution", "content", "text", "description"):
        value = str(doc.get(field, "") or "").strip()
        if value:
            return value
    return ""


def _source_label_tr(doc_type: str) -> str:
    normalized = str(doc_type or "").casefold()
    if normalized in {"kb", "document", "pdf"}:
        return "Bilgi dokümanı"
    return "Ticket"


def _source_label_en(doc_type: str) -> str:
    normalized = str(doc_type or "").casefold()
    if normalized in {"kb", "document", "pdf"}:
        return "Knowledge document"
    return "Ticket"


def _combined_doc_text(question: str, docs: List[Dict[str, Any]]) -> str:
    pieces = [question]
    for doc in docs[:3]:
        pieces.extend(
            [
                str(doc.get("category", "") or ""),
                str(doc.get("subcategory", "") or ""),
                _doc_title(doc),
                _doc_solution_text(doc),
            ]
        )
    return " ".join(piece.casefold() for piece in pieces if piece)


def _infer_support_scenario(question: str, docs: List[Dict[str, Any]]) -> str:
    text = _combined_doc_text(question, docs)

    if any(term in text for term in ("vpn", "forticlient", "remote access", "uzaktan erişim")):
        return "vpn"
    if any(term in text for term in ("mail", "e-posta", "outlook", "exchange", "posta kutusu", "kota")):
        return "mail"
    if any(term in text for term in ("mfa", "authenticator", "token", "şifre", "parola", "sso", "hesap kilit")):
        return "identity"
    if any(term in text for term in ("yazıcı", "printer", "çıktı", "toner", "tarama")):
        return "printer"
    if any(term in text for term in ("teams", "mikrofon", "kamera", "toplantı", "ses")):
        return "teams"
    return "generic"


def _action_steps_tr(question: str, docs: List[Dict[str, Any]]) -> List[str]:
    scenario = _infer_support_scenario(question, docs)

    if scenario == "vpn":
        return [
            "İnternet bağlantısını ve VPN dışında web erişiminin çalışıp çalışmadığını kontrol edin.",
            "FortiClient/VPN istemcisinde kullanıcı adı, parola, MFA bildirimi ve hata kodunu kontrol edin.",
            "Şirket içi kaynaklara erişim yoksa VPN profilini/gateway bilgisini yenileyip yeniden bağlanmayı deneyin.",
            "Sorun sürerse saat, hata kodu, ekran görüntüsü ve etkilenen kullanıcı bilgisini BT ekibine iletin.",
        ]
    if scenario == "mail":
        return [
            "Outlook Web veya farklı bir cihazdan mail gönderimini deneyerek sorunun istemci mi servis mi olduğunu ayırın.",
            "Posta kutusu kotasını ve ek boyutu limitlerini kontrol edin; kota doluysa eski/iri iletileri arşivleyin.",
            "Exchange bağlantısı, mail flow ve varsa NDR/hata kodu bilgisini not edin.",
            "Sorun devam ederse BT ekibinden kullanıcı mailbox, connector ve servis sağlığı kontrollerini istemek gerekir.",
        ]
    if scenario == "identity":
        return [
            "Parola süresi, hesap kilidi ve MFA cihaz kaydı durumunu kontrol edin.",
            "Self servis parola sıfırlama veya kurum kimlik portalı üzerinden oturumu yenilemeyi deneyin.",
            "Authenticator saat senkronu, push bildirimi ve alternatif doğrulama yöntemlerini kontrol edin.",
            "Şüpheli MFA isteği veya beklenmeyen oturum varsa parolayı değiştirip BT/SOC ekibine bildirin.",
        ]
    if scenario == "printer":
        return [
            "Yazıcının açık, ağda erişilebilir ve doğru kuyruk üzerinden seçili olduğunu kontrol edin.",
            "Yazdırma kuyruğunu temizleyip test sayfası göndermeyi deneyin.",
            "Sürücü, toner/kağıt durumu ve kullanıcı yetkisini kontrol edin.",
            "Sorun sürerse yazıcı adı, hata mesajı ve etkilenen kullanıcıları BT ekibine iletin.",
        ]
    if scenario == "teams":
        return [
            "Teams web/masaüstü ayrımı yaparak sorunun uygulama mı cihaz mı olduğunu kontrol edin.",
            "Mikrofon, kamera ve hoparlör aygıt seçimlerini doğrulayın.",
            "Oturumu kapatıp açın, Teams önbelleğini temizleyin ve test toplantısı yapın.",
            "Sorun devam ederse toplantı zamanı, cihaz modeli ve hata ekranını BT ekibine iletin.",
        ]

    return [
        "Hata mesajı, etkilenen uygulama, cihaz ve sorunun başladığı zamanı not edin.",
        "Aynı işlemi farklı tarayıcı/cihaz/ağ üzerinden deneyerek kapsamı daraltın.",
        "Benzer geçmiş kayıtların çözüm adımlarını güvenli olanlardan başlayarak uygulayın.",
        "İş kesintisi devam ederse bulgularla birlikte BT destek ekibine eskale edin.",
    ]


def _action_steps_en(question: str, docs: List[Dict[str, Any]]) -> List[str]:
    scenario = _infer_support_scenario(question, docs)

    if scenario == "vpn":
        return [
            "Check whether general internet access works outside the VPN.",
            "Verify VPN username, password, MFA prompt, client profile, and any error code.",
            "Reconnect after refreshing the VPN profile or gateway settings if internal resources are unreachable.",
            "If it continues, send the timestamp, error code, screenshot, and affected user details to IT.",
        ]
    if scenario == "mail":
        return [
            "Try sending from Outlook Web or another device to separate client-side and service-side issues.",
            "Check mailbox quota and attachment size limits; archive or remove large messages if needed.",
            "Record Exchange connectivity, mail-flow, and NDR/error-code details.",
            "If it continues, ask IT to check the mailbox, connector, and service health.",
        ]
    if scenario == "identity":
        return [
            "Check password expiry, account lockout, and MFA device registration.",
            "Retry through the self-service password or identity portal.",
            "Verify authenticator time sync, push notifications, and alternate verification methods.",
            "For suspicious MFA prompts, change the password and notify IT/SOC.",
        ]
    return [
        "Collect the exact error message, application/device, and start time.",
        "Try the same action from another browser, device, or network to narrow the scope.",
        "Apply the safest matching steps from similar historical tickets first.",
        "Escalate to IT support with the collected evidence if the interruption continues.",
    ]


def _message_content(message: Dict[str, Any]) -> str:
    return str(message.get("content") or message.get("text") or "").strip()


def _is_follow_up_question(question: str) -> bool:
    normalized = question.casefold()
    words = normalized.split()
    direct_follow_up_markers = (
        "olmadi",
        "olmadı",
        "devam",
        "bunlar",
        "bunu",
        "nereden",
        "nerde",
        "nasil",
        "nasıl",
        "adim",
        "adım",
        "soyledigin",
        "söylediğin",
        "uyguladim",
        "uyguladım",
        "sonra ne",
    )
    standalone_it_terms = (
        "vpn",
        "mail",
        "exchange",
        "outlook",
        "teams",
        "mfa",
        "sifre",
        "şifre",
        "parola",
        "yazici",
        "yazıcı",
        "printer",
        "internet",
        "wifi",
    )

    if any(marker in normalized for marker in direct_follow_up_markers):
        return True

    return len(words) <= 5 and not any(term in normalized for term in standalone_it_terms)

def _build_contextual_retrieval_query(
    question: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Use the previous user issue for short follow-up questions without changing the visible answer."""
    if not conversation_history or not _is_follow_up_question(question):
        return question

    previous_user_messages = [
        _message_content(message)
        for message in conversation_history
        if message.get("role") == "user" and _message_content(message)
    ]
    if not previous_user_messages:
        return question

    previous_issue = previous_user_messages[-1]
    if len(previous_issue) > 240:
        previous_issue = previous_issue[:240]

    return f"{previous_issue}\nTakip sorusu: {question}"


def _build_advisory_answer_tr(question: str, docs: List[Dict[str, Any]]) -> str:
    """
    Build Turkish advisory-style answer from past ticket examples.
    NOW WITH DETAILED STEP-BY-STEP FORMATTING (PHASE 7.5).
    
    Args:
        question: User's question
        docs: Retrieved documents (past tickets and PDF pages)
        
    Returns:
        Advisory answer in Turkish with detailed step-by-step instructions
    """
    answer_parts = [
        f"Sorunuz: {question}\n",
        "\nÖnerilen ilk kontroller:\n"
    ]

    for index, step in enumerate(_action_steps_tr(question, docs), 1):
        answer_parts.append(f"{index}. {step}\n")

    answer_parts.append("\nBenzer durumlarda BT ekibinin uyguladığı örnek çözümler:\n")
    
    # Show top 3 usable examples. Ticket documents use resolution; KB chunks use text/content.
    examples_rendered = 0
    for doc in docs:
        if examples_rendered >= 3:
            break

        ticket_id = _doc_identifier(doc)
        doc_type = doc.get("doc_type", "itsm_ticket")
        short_desc = _doc_title(doc)
        resolution = _doc_solution_text(doc)
        
        if short_desc and resolution:
            examples_rendered += 1
            # Header
            source_label = _source_label_tr(doc_type)
            answer_parts.append(f"\n{'='*70}")
            answer_parts.append(f"\n📖 Örnek {examples_rendered} ({source_label}: {ticket_id})")
            answer_parts.append(f"\n{'='*70}")
            answer_parts.append(f"\n**Durum:** {short_desc}\n")
            
            # Format resolution with better structure
            formatted_resolution = _format_resolution_text(resolution, doc_type)
            answer_parts.append(f"\n**Uygulanan Çözüm:**\n{formatted_resolution}\n")
    
    # Add advisory conclusion
    answer_parts.append("\n" + "="*70)
    answer_parts.append("\n💡 **Öneriler:**")
    answer_parts.append("\n" + "="*70)
    answer_parts.append(
        "\nBu örneklerden yola çıkarak:"
    )
    answer_parts.append(
        "\n✓ Benzer adımları kendiniz deneyebilirsiniz, VEYA"
    )
    answer_parts.append(
        "\n✓ BT destek ekibinden bu çözümleri uygulamalarını talep edebilirsiniz."
    )
    
    if len(docs) > examples_rendered:
        answer_parts.append(
            f"\n\n(Toplam {len(docs)} benzer durum bulundu)"
        )
    
    logger.debug("advisory_answer_generated_tr", 
                question=question[:50],
                num_docs=len(docs),
                num_examples=examples_rendered)
    
    return "".join(answer_parts)


def _format_resolution_text(text: str, doc_type: str) -> str:
    """
    Format resolution text to highlight step-by-step instructions.
    
    Args:
        text: Raw resolution text
        doc_type: Type of document (document for PDF, itsm_ticket for ticket)
        
    Returns:
        Formatted text with clear step-by-step structure
    """
    if not text or len(text) < 20:
        return text
    
    # For PDF documents, show more content (up to 1500 chars for detailed instructions)
    if doc_type == "document":
        max_length = 1500
    else:
        max_length = 800
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    # Split into lines
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect and format numbered steps
        if any(line.lower().startswith(f"{num}.") or line.lower().startswith(f"{num})") 
               for num in range(1, 20)):
            formatted_lines.append(f"   {line}")
        
        # Detect and format bullet points
        elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
            formatted_lines.append(f"   {line}")
        
        # Detect keywords for steps
        elif any(keyword in line.lower() for keyword in ['adım', 'işlem', 'kontrol edin', 'yapınız', 'tıklayın']):
            formatted_lines.append(f"   ▸ {line}")
        
        # Regular lines
        else:
            formatted_lines.append(f"   {line}")
    
    return '\n'.join(formatted_lines)


def _build_advisory_answer_en(question: str, docs: List[Dict[str, Any]]) -> str:
    """
    Build English advisory-style answer from past ticket examples.
    NOW WITH DETAILED STEP-BY-STEP FORMATTING (PHASE 7.5).
    
    Args:
        question: User's question
        docs: Retrieved documents (past tickets and PDF pages)
        
    Returns:
        Advisory answer in English with detailed step-by-step instructions
    """
    answer_parts = [
        f"Your question: {question}\n",
        "\nRecommended first checks:\n"
    ]

    for index, step in enumerate(_action_steps_en(question, docs), 1):
        answer_parts.append(f"{index}. {step}\n")

    answer_parts.append("\nExample solutions applied by the IT team in similar cases:\n")
    
    # Show top 3 usable examples. Ticket documents use resolution; KB chunks use text/content.
    examples_rendered = 0
    for doc in docs:
        if examples_rendered >= 3:
            break

        ticket_id = _doc_identifier(doc)
        doc_type = doc.get("doc_type", "itsm_ticket")
        short_desc = _doc_title(doc)
        resolution = _doc_solution_text(doc)
        
        if short_desc and resolution:
            examples_rendered += 1
            # Header
            source_label = _source_label_en(doc_type)
            answer_parts.append(f"\n{'='*70}")
            answer_parts.append(f"\n📖 Example {examples_rendered} ({source_label}: {ticket_id})")
            answer_parts.append(f"\n{'='*70}")
            answer_parts.append(f"\n**Issue:** {short_desc}\n")
            
            # Format resolution with better structure
            formatted_resolution = _format_resolution_text(resolution, doc_type)
            answer_parts.append(f"\n**Resolution Applied:**\n{formatted_resolution}\n")
    
    # Add advisory conclusion
    answer_parts.append("\n" + "="*70)
    answer_parts.append("\n💡 **Recommendations:**")
    answer_parts.append("\n" + "="*70)
    answer_parts.append(
        "\nBased on these examples:"
    )
    answer_parts.append(
        "\n✓ You can try these steps yourself, OR"
    )
    answer_parts.append(
        "\n✓ Request the IT support team to apply these solutions."
    )
    
    if len(docs) > examples_rendered:
        answer_parts.append(
            f"\n\n({len(docs)} similar cases found in total)"
        )
    
    logger.debug("advisory_answer_generated_en", 
                question=question[:50],
                num_docs=len(docs),
                num_examples=examples_rendered)
    
    return "".join(answer_parts)


class RAGPipeline:
    """
    Main RAG pipeline that coordinates retrieval and generation
    with strict "no source, no answer" policy.
    """
    
    def __init__(
        self,
        retriever: HybridRetriever,
        prompt_builder: Optional[PromptBuilder] = None,
        confidence_estimator: Optional[ConfidenceEstimator] = None,
        llm_model=None,  # Will be transformers model or API client
        max_context_length: int = 2048,
        confidence_threshold: float = 0.7,
        # PHASE 8: Real LLM settings
        use_real_llm: bool = False,
        openai_api_key: Optional[str] = None,
        llm_model_name: str = "gpt-4o-mini",
        llm_temperature: float = 0.3,
        llm_max_tokens: int = 1500
    ):
        """
        Initialize RAG pipeline.
        
        Args:
            retriever: Hybrid retriever for document retrieval
            prompt_builder: Prompt builder (creates default if None)
            confidence_estimator: Confidence estimator (creates default if None)
            llm_model: LLM model for generation
            max_context_length: Maximum context length for prompts
            confidence_threshold: Minimum confidence for answers
            use_real_llm: Whether to use real LLM (True) or stub (False)
            openai_api_key: OpenAI API key for real LLM
            llm_model_name: OpenAI model name (gpt-4o-mini, gpt-4o, etc.)
            llm_temperature: LLM temperature for generation
            llm_max_tokens: Maximum tokens for LLM response
        """
        self.retriever = retriever
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.confidence_estimator = confidence_estimator or ConfidenceEstimator(confidence_threshold)
        self.llm_model = llm_model
        self.max_context_length = max_context_length
        self.confidence_threshold = confidence_threshold
        
        # PHASE 8: Real LLM settings
        self.use_real_llm = use_real_llm
        self.openai_api_key = openai_api_key
        self.llm_model_name = llm_model_name
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

        if self.use_real_llm and not OPENAI_AVAILABLE:
            logger.warning(
                "real_llm_disabled_openai_package_missing",
                message="USE_REAL_LLM is true, but the openai package is not installed. Falling back to stub answers.",
            )
            self.use_real_llm = False
        elif self.use_real_llm and not self.openai_api_key:
            logger.warning(
                "real_llm_disabled_api_key_missing",
                message="USE_REAL_LLM is true, but OPENAI_API_KEY is missing. Falling back to stub answers.",
            )
            self.use_real_llm = False
        
        # IT relevance checker for filtering non-IT queries
        self.it_relevance_checker = ITRelevanceChecker()
        
        logger.info("rag_pipeline_initialized",
                   max_context_length=max_context_length,
                   confidence_threshold=confidence_threshold,
                   use_real_llm=self.use_real_llm,
                   llm_model=llm_model_name if self.use_real_llm else "stub")
    
    def answer(
        self,
        question: str,
        *,
        language: Optional[str] = None,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 5
    ) -> RAGResult:
        """
        Answer a question using the RAG pipeline (PHASE 4 implementation).
        
        This is the main entry point for the RAG system that:
        1. Retrieves relevant documents using HybridRetriever
        2. Computes retrieval confidence
        3. Applies "no source, no answer" policy
        4. Generates answer using LLM stub (or real LLM in production)
        5. Returns structured RAGResult
        
        PHASE 9: Now supports conversation history for context-aware answers!
        
        Args:
            question: User's question
            language: Language code (e.g., "tr", "en"), auto-detected if None
            session_id: Optional session ID for conversation tracking
            conversation_history: Previous messages for context (PHASE 9)
            top_k: Number of documents to retrieve
            
        Returns:
            RAGResult with answer, confidence, sources, and metadata
            
        Example:
            >>> pipeline = RAGPipeline(retriever, ...)
            >>> result = pipeline.answer("Outlook şifremi unuttum")
            >>> print(result.answer)
            >>> print(f"Confidence: {result.confidence}")
        """
        logger.info("rag_answer_request", 
                   question=question[:100],
                   language=language,
                   session_id=session_id)
        
        # Auto-detect language if not provided
        if language is None:
            language = self._detect_language(question)
        
        # Step 0.5: Handle thank you messages and acknowledgments
        question_lower = question.lower().strip()
        thank_you_patterns = [
            r'^(teşekkür|thanks|thank you)(\s+ederim|\s+ediyorum|\s+ediyoruz)?\.?$',
            r'^(tamam|ok|okay|anladım|tamamdır)(\s+teşekkür|\s+thanks)?(\s+ederim|\s+ediyorum)?\.?$',
            r'^(tamam|ok|okay|anladım|tamamdır)\.?$',
        ]
        for pattern in thank_you_patterns:
            if re.match(pattern, question_lower):
                # Thank you messages - return friendly acknowledgment
                if language == "tr":
                    answer = "Rica ederim! Başka bir konuda yardımcı olabilir miyim?"
                else:
                    answer = "You're welcome! Is there anything else I can help you with?"
                
                return RAGResult(
                    answer=answer,
                    confidence=0.0,
                    sources=[],
                    has_answer=False,
                    language=language,
                    intent="acknowledgment",
                    retrieved_docs=[],
                    debug_info={"rejection_reason": "thank_you_message"}
                )
        
        # Step 0: Check if query is IT-related (filter non-IT queries)
        # IMPORTANT: Check conversation history - if previous messages were IT-related,
        # Check if query should be rejected (non-IT)
        is_it, it_confidence = self.it_relevance_checker.is_it_related(question)
        should_reject = self.it_relevance_checker.should_reject_query(question)
        
        # If query is explicitly non-IT (high confidence, e.g., "şişe", "yemek"), 
        # reject immediately regardless of conversation history
        if should_reject and it_confidence >= 0.8:
            # Explicit non-IT keyword detected - reject immediately
            logger.info("query_rejected_explicit_non_it", 
                       question=question[:50],
                       confidence=it_confidence)
            # Return rejection immediately - don't process further
            if language == "tr":
                answer = "Üzgünüm, bu soru BT (Bilgi Teknolojileri) destek konularıyla ilgili değil. Lütfen bilgisayar, yazılım, ağ, güvenlik veya diğer BT konularıyla ilgili sorularınızı sorun."
            else:
                answer = "I'm sorry, this question is not related to IT (Information Technology) support topics. Please ask questions about computers, software, networks, security, or other IT-related topics."
            
            return RAGResult(
                answer=answer,
                confidence=0.0,
                sources=[],
                has_answer=False,
                language=language,
                intent=None,
                retrieved_docs=[],
                debug_info={"rejection_reason": "explicit_non_it_query", "confidence": it_confidence}
            )
        # If query seems non-IT but with lower confidence, check conversation history
        elif should_reject and conversation_history:
            # Check if any previous message in conversation was IT-related
            has_it_context = False
            for msg in conversation_history:
                if msg.get("role") in ["user", "assistant"]:
                    content = msg.get("content", "")
                    is_it_hist, _ = self.it_relevance_checker.is_it_related(content)
                    if is_it_hist:
                        has_it_context = True
                        logger.debug("it_context_found_in_history", 
                                   message_preview=content[:50])
                        break
            
            # If conversation has IT context, don't reject follow-up questions
            if has_it_context:
                should_reject = False
                logger.info("query_accepted_due_to_it_context", 
                           question=question[:50],
                           has_history=True)
        
        if should_reject:
            logger.info("query_rejected_non_it", question=question[:100])
            if language == "tr":
                answer = "Üzgünüm, bu soru BT (Bilgi Teknolojileri) destek konularıyla ilgili değil. Lütfen bilgisayar, yazılım, ağ, güvenlik veya diğer BT konularıyla ilgili sorularınızı sorun."
            else:
                answer = "I'm sorry, this question is not related to IT (Information Technology) support topics. Please ask questions about computers, software, networks, security, or other IT-related topics."
            
            return RAGResult(
                answer=answer,
                confidence=0.0,
                sources=[],
                has_answer=False,
                language=language,
                intent=None,
                retrieved_docs=[],
                debug_info={"rejection_reason": "non_it_query"}
            )
        
        # Step 1: Retrieve relevant documents
        retrieval_question = _build_contextual_retrieval_query(question, conversation_history)
        retrieved_docs = self.retriever.search(retrieval_question, top_k=top_k)
        
        # Collect debug info from retrieval
        debug_info = {}
        debug_info["used_conversation_context"] = retrieval_question != question
        if retrieved_docs:
            # Get alpha_used from first result (all should have same alpha)
            first_doc = retrieved_docs[0]
            debug_info["alpha_used"] = first_doc.get("alpha_used")
            
            # Get actual source counts from metadata (added by hybrid retriever)
            debug_info["bm25_results_count"] = first_doc.get("_bm25_source_count", 0)
            debug_info["embedding_results_count"] = first_doc.get("_embedding_source_count", 0)
            debug_info["hybrid_results_count"] = len(retrieved_docs)
            
            # Determine query type based on alpha
            alpha = debug_info.get("alpha_used", 0.5)
            if alpha < 0.4:
                debug_info["query_type"] = "short_technical"  # Embedding favored
            elif alpha < 0.6:
                debug_info["query_type"] = "medium"  # Balanced
            else:
                debug_info["query_type"] = "long_detailed"  # BM25 favored
        
        logger.debug("retrieval_completed", 
                    num_docs=len(retrieved_docs),
                    question=question[:50],
                    retrieval_question=retrieval_question[:120],
                    debug_info=debug_info)
        
        # Step 2: Check if we have any documents
        if not retrieved_docs:
            logger.warning("no_documents_retrieved", question=question[:100])
            return self._build_no_answer_result(
                language=language,
                reason="no_documents"
            )
        
        # Step 3: Compute retrieval confidence
        retrieval_scores = [doc.get("score", 0.0) for doc in retrieved_docs]
        top_score = max(retrieval_scores) if retrieval_scores else 0.0
        
        # If top score is too low, don't attempt to answer
        if top_score < 0.1:  # Very low threshold for retrieval
            logger.warning("low_retrieval_scores",
                         top_score=top_score,
                         question=question[:100])
            return self._build_no_answer_result(
                language=language,
                reason="low_scores",
                retrieved_docs=retrieved_docs
            )
        
        # Step 4: Generate answer using real LLM or stub (PHASE 8)
        try:
            if self.use_real_llm and self.openai_api_key:
                generated_answer = generate_answer_with_llm(
                    question=question,
                    docs=retrieved_docs,
                    language=language,
                    conversation_history=conversation_history or [],  # PHASE 9
                    api_key=self.openai_api_key,
                    model=self.llm_model_name,
                    temperature=self.llm_temperature,
                    max_tokens=self.llm_max_tokens
                )
            else:
                generated_answer = generate_answer_with_stub(
                    question=question,
                    docs=retrieved_docs,
                    language=language
                )
        except Exception as e:
            logger.error("answer_generation_failed", error=str(e))
            return self._build_no_answer_result(
                language=language,
                reason="generation_error"
            )
        
        # Step 5: Estimate confidence using the confidence estimator
        confidence, has_sufficient_confidence = self.confidence_estimator.estimate_confidence(
            answer=generated_answer,
            query=question,
            retrieved_docs=retrieved_docs,
            retrieval_scores=retrieval_scores
        )
        
        # Step 5.5: Adjust confidence threshold for conversation history
        # If this is a follow-up question in an IT-related conversation,
        # use a lower threshold to allow more lenient answers
        effective_threshold = self.confidence_threshold
        if conversation_history:
            # Check if conversation has IT context (already checked earlier)
            has_it_context = False
            for msg in conversation_history:
                if msg.get("role") in ["user", "assistant"]:
                    content = msg.get("content", "")
                    is_it, _ = self.it_relevance_checker.is_it_related(content)
                    if is_it:
                        has_it_context = True
                        break
            
            # Lower threshold for follow-up questions in IT conversations
            if has_it_context and not self.it_relevance_checker.is_it_related(question)[0]:
                # This is likely a follow-up question (e.g., "2. adımı anlamadım")
                effective_threshold = max(0.5, self.confidence_threshold - 0.15)  # Lower by 0.15, min 0.5
                logger.debug("confidence_threshold_adjusted_for_followup",
                           original_threshold=self.confidence_threshold,
                           effective_threshold=effective_threshold,
                           confidence=confidence)
        
        # Step 6: Apply "no source, no answer" policy with adjusted threshold
        has_sufficient_confidence = confidence >= effective_threshold
        if not has_sufficient_confidence:
            logger.info("answer_rejected_low_confidence",
                       confidence=confidence,
                       threshold=effective_threshold)
            return self._build_no_answer_result(
                language=language,
                reason="low_confidence",
                retrieved_docs=retrieved_docs,
                confidence=confidence,
                debug_info=debug_info
            )
        
        # Step 7: Build successful result
        sources = self._extract_sources(retrieved_docs)
        
        result = RAGResult(
            answer=generated_answer,
            confidence=confidence,
            sources=sources,
            has_answer=True,
            language=language,
            intent=None,  # Can be populated by NLP module if needed
            retrieved_docs=retrieved_docs,
            debug_info=debug_info  # Include debug info
        )
        
        logger.info("rag_answer_success",
                   confidence=confidence,
                   num_sources=len(sources),
                   has_answer=True)
        
        return result
    
    def _detect_language(self, text: str) -> str:
        """
        Detect language of input text.
        
        Args:
            text: Input text
            
        Returns:
            Language code (defaults to "tr" for Turkish)
        """
        # Simple heuristic: check for Turkish characters
        turkish_chars = set("ğüşıöçĞÜŞİÖÇ")
        if any(char in text for char in turkish_chars):
            return "tr"
        return "en"
    
    def _build_no_answer_result(
        self,
        language: str,
        reason: str,
        retrieved_docs: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 0.0,
        debug_info: Optional[Dict[str, Any]] = None
    ) -> RAGResult:
        """
        Build a RAGResult for cases where we cannot provide an answer.
        
        Args:
            language: Language code
            reason: Reason for no answer ("no_documents", "low_scores", etc.)
            retrieved_docs: Optional retrieved documents
            confidence: Confidence score (default: 0.0)
            debug_info: Optional debug information dictionary
            
        Returns:
            RAGResult with has_answer=False
        """
        if language == "tr":
            answer = "Mevcut kaynaklara dayanarak güvenilir bir cevap üretemiyorum."
        else:
            answer = "I cannot provide a reliable answer based on available sources."
        
        sources = self._extract_sources(retrieved_docs) if retrieved_docs else []
        
        # Use provided debug_info or collect from retrieved docs
        if debug_info is None and retrieved_docs:
            first_doc = retrieved_docs[0]
            debug_info = {
                "alpha_used": first_doc.get("alpha_used"),
                "bm25_results_count": first_doc.get("_bm25_source_count", 0),
                "embedding_results_count": first_doc.get("_embedding_source_count", 0),
                "hybrid_results_count": len(retrieved_docs),
                "query_type": None  # Not determined for no-answer cases
            }
        
        logger.debug("no_answer_result_built", 
                    reason=reason,
                    num_sources=len(sources))
        
        return RAGResult(
            answer=answer,
            confidence=confidence,
            sources=sources,
            has_answer=False,
            language=language,
            intent=None,
            retrieved_docs=retrieved_docs or [],
            debug_info=debug_info
        )
    
    def _extract_sources(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract source information from retrieved documents.
        
        Args:
            docs: Retrieved documents
            
        Returns:
            List of source dictionaries with essential fields
        """
        sources = []
        for doc in docs:
            source = {
                "doc_id": doc.get("ticket_id") or doc.get("id") or doc.get("doc_id", "unknown"),
                "doc_type": doc.get("doc_type", "ticket"),
                "title": doc.get("short_description", doc.get("title", ""))[:100],
                "snippet": doc.get("description", doc.get("text", ""))[:200],
                "relevance_score": float(doc.get("score", 0.0))
            }
            sources.append(source)
        
        return sources
    
    def answer_query(
        self,
        query: str,
        top_k: int = 10,
        return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Answer user query using RAG pipeline.
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            return_sources: Whether to return source documents
            
        Returns:
            Dictionary with answer, confidence, and optionally sources
            
        Process:
            1. Retrieve relevant documents
            2. Build prompt with context
            3. Generate answer (placeholder for now)
            4. Estimate confidence
            5. Apply "no source, no answer" policy
            6. Return result with sources
        """
        logger.info("rag_query_started", query=query, top_k=top_k)
        
        # 1. Retrieve relevant documents
        retrieved_docs = self.retriever.search(query, top_k=top_k)
        
        if not retrieved_docs:
            logger.warning("no_documents_retrieved", query=query)
            return self._build_no_answer_response(
                "No relevant documents found in the knowledge base.",
                []
            )
        
        # 2. Build prompt
        prompt = self.prompt_builder.build_prompt(
            query=query,
            documents=retrieved_docs,
            max_context_length=self.max_context_length
        )
        
        # 3. Generate answer
        # TODO: Implement actual LLM generation
        # For now, placeholder response
        if self.llm_model is None:
            answer = "LLM model not loaded. Please initialize the model."
            confidence = 0.0
            has_answer = False
        else:
            # Placeholder for actual generation
            answer = self._generate_answer(prompt)
            
            # 4. Estimate confidence
            retrieval_scores = [doc.get("score", 0.0) for doc in retrieved_docs]
            confidence, has_answer = self.confidence_estimator.estimate_confidence(
                answer=answer,
                query=query,
                retrieved_docs=retrieved_docs,
                retrieval_scores=retrieval_scores
            )
        
        # 5. Apply policy: if confidence too low, return explicit "I don't know"
        if not has_answer:
            logger.info("low_confidence_answer_rejected", 
                       confidence=confidence,
                       query=query)
            return self._build_no_answer_response(
                "I don't have enough information in the knowledge base to answer this question reliably.",
                retrieved_docs if return_sources else []
            )
        
        # 6. Build successful response
        response = {
            "answer": answer,
            "confidence": confidence,
            "has_answer": True,
            "num_sources": len(retrieved_docs)
        }
        
        if return_sources:
            response["sources"] = self.prompt_builder.extract_sources_from_context(retrieved_docs)
        
        logger.info("rag_query_completed",
                   query=query,
                   confidence=confidence,
                   num_sources=len(retrieved_docs))
        
        return response
    
    def _generate_answer(self, prompt: Dict[str, str]) -> str:
        """
        Generate answer using LLM.
        
        Args:
            prompt: Prompt dictionary with system and user messages
            
        Returns:
            Generated answer
        """
        # TODO: Implement actual LLM generation
        # This is a placeholder that should be replaced with:
        # - transformers pipeline for local models
        # - API calls for hosted models
        # - Proper error handling and generation parameters
        
        logger.warning("llm_generation_not_implemented")
        return "LLM generation not yet implemented. This is a placeholder response."
    
    def _build_no_answer_response(
        self,
        message: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build response for cases where we cannot answer.
        
        Args:
            message: Message explaining why we can't answer
            retrieved_docs: Retrieved documents (may be empty)
            
        Returns:
            Response dictionary
        """
        response = {
            "answer": message,
            "confidence": 0.0,
            "has_answer": False,
            "num_sources": len(retrieved_docs)
        }
        
        if retrieved_docs:
            response["sources"] = self.prompt_builder.extract_sources_from_context(retrieved_docs)
        else:
            response["sources"] = []
        
        return response
    
    def batch_answer(
        self,
        queries: List[str],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Answer multiple queries in batch.
        
        Args:
            queries: List of user queries
            top_k: Number of documents to retrieve per query
            
        Returns:
            List of response dictionaries
        """
        results = []
        for query in queries:
            result = self.answer_query(query, top_k=top_k, return_sources=True)
            results.append(result)
        
        return results


