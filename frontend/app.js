/**
 * PHASE 10: Chat Interface - Message History
 * Converts single-turn Q&A into a chat-like interface with message history
 * Backend API remains unchanged - only frontend is modified
 */

// ============================================
// CONFIGURATION
// ============================================

const API_BASE_URL = 'http://localhost:8000';

const API_ENDPOINTS = {
    chat: `${API_BASE_URL}/api/v1/chat`,
    anomalyStats: `${API_BASE_URL}/api/v1/anomaly/stats`,
    anomalyDetect: `${API_BASE_URL}/api/v1/anomaly/detect`
};

// ============================================
// STATE MANAGEMENT
// ============================================

/**
 * Message history state
 * Each message has: { role, text, timestamp, confidence?, sources? }
 */
let chatMessages = [];

/**
 * Session ID for conversation tracking
 * Persists across page loads via localStorage
 */
let sessionId = null;

// ============================================
// SESSION MANAGEMENT
// ============================================

/**
 * Get or create a session ID for conversation tracking.
 */
function getOrCreateSessionId() {
    if (sessionId) {
        return sessionId;
    }
    
    sessionId = localStorage.getItem('bt_support_session_id');
    
    if (!sessionId) {
        // Create unique session ID: timestamp + random
        sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
        localStorage.setItem('bt_support_session_id', sessionId);
        console.log('🆕 New session created:', sessionId);
    } else {
        console.log('🔄 Existing session loaded:', sessionId);
    }
    
    return sessionId;
}

/**
 * Clear session (for testing or manual reset).
 */
function clearSession() {
    localStorage.removeItem('bt_support_session_id');
    sessionId = null;
    chatMessages = [];
    renderChatMessages();
    console.log('🗑️ Session cleared');
}

// ============================================
// CHAT MESSAGE RENDERING
// ============================================

/**
 * Render all chat messages to the DOM
 */
function renderChatMessages() {
    const messagesContainer = document.getElementById('chat-messages');
    
    if (chatMessages.length === 0) {
        // Show empty state
        messagesContainer.innerHTML = `
            <div class="chat-empty-state">
                <div class="chat-empty-state-icon">💬</div>
                <div class="chat-empty-state-text">Henüz mesaj yok</div>
                <div class="chat-empty-state-hint">Aşağıdaki kutuya sorunuzu yazarak başlayın</div>
            </div>
        `;
        return;
    }
    
    // Render all messages
    messagesContainer.innerHTML = '';
    
    chatMessages.forEach(message => {
        const messageEl = createMessageElement(message);
        messagesContainer.appendChild(messageEl);
    });
    
    // Auto-scroll to bottom
    scrollToBottom();
}

/**
 * Create a DOM element for a single message
 */
function createMessageElement(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.role}`;
    
    if (message.role === 'user') {
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-content">${escapeHtml(message.text)}</div>
                <div class="message-timestamp">${formatTimestamp(message.timestamp)}</div>
            </div>
        `;
    } else if (message.role === 'assistant') {
        const confidenceBadgeHtml = message.confidence !== undefined 
            ? `<span class="confidence-badge ${getConfidenceClass(message.confidence)}">
                 Güven: ${Math.round(message.confidence * 100)}%
               </span>`
            : '';
        
        const languageBadge = message.language 
            ? `<span class="message-badge">🌐 ${message.language.toUpperCase()}</span>`
            : '';
        
        const hasAnswerBadge = message.has_answer !== undefined
            ? `<span class="message-badge">${message.has_answer ? '✅ Cevap Bulundu' : '❌ Cevap Bulunamadı'}</span>`
            : '';
        
        const sourcesHtml = message.sources && message.sources.length > 0
            ? `<div class="message-sources">
                 <div class="message-sources-title">📚 Kaynaklar:</div>
                 ${message.sources.map((source, idx) => `
                   <div class="message-source-item">
                     <span class="message-source-title">${idx + 1}. ${source.title || source.doc_id}</span>
                     <span class="message-source-score">${(source.relevance_score * 100).toFixed(0)}%</span>
                   </div>
                 `).join('')}
               </div>`
            : '';
        
        // Debug info HTML (retrieval details)
        const debugHtml = message.debug_info
            ? `<div class="message-debug-info">
                 <div class="message-debug-title">🔍 Arama Detayları:</div>
                 <div class="message-debug-content">
                   <div class="debug-item">
                     <span class="debug-label">Dinamik Alpha:</span>
                     <span class="debug-value">${message.debug_info.alpha_used !== null && message.debug_info.alpha_used !== undefined ? message.debug_info.alpha_used.toFixed(2) : 'N/A'}</span>
                     <span class="debug-hint">${message.debug_info.alpha_used < 0.4 ? '(Embedding ağırlıklı)' : message.debug_info.alpha_used > 0.6 ? '(BM25 ağırlıklı)' : '(Dengeli)'}</span>
                   </div>
                   <div class="debug-item">
                     <span class="debug-label">Sorgu Tipi:</span>
                     <span class="debug-value">${message.debug_info.query_type || 'N/A'}</span>
                   </div>
                   <div class="debug-item">
                     <span class="debug-label">BM25 Sonuçları:</span>
                     <span class="debug-value">${message.debug_info.bm25_results_count || 0}</span>
                   </div>
                   <div class="debug-item">
                     <span class="debug-label">Embedding Sonuçları:</span>
                     <span class="debug-value">${message.debug_info.embedding_results_count || 0}</span>
                   </div>
                   <div class="debug-item">
                     <span class="debug-label">Hibrit Sonuçlar:</span>
                     <span class="debug-value">${message.debug_info.hybrid_results_count || 0}</span>
                   </div>
                 </div>
               </div>`
            : '';
        
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-content">${formatAssistantMessage(message.text)}</div>
                <div class="message-metadata">
                    ${confidenceBadgeHtml}
                    ${hasAnswerBadge}
                    ${languageBadge}
                </div>
                ${sourcesHtml}
                ${debugHtml}
                <div class="message-timestamp">${formatTimestamp(message.timestamp)}</div>
            </div>
        `;
    } else if (message.role === 'error') {
        messageDiv.className = 'message error';
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-content">❌ ${escapeHtml(message.text)}</div>
                <div class="message-timestamp">${formatTimestamp(message.timestamp)}</div>
            </div>
        `;
    }
    
    return messageDiv;
}

/**
 * Format assistant message with markdown-like formatting
 */
function formatAssistantMessage(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
        .replace(/\n/g, '<br>');  // Line breaks
}

/**
 * Get CSS class for confidence level
 */
function getConfidenceClass(confidence) {
    if (confidence >= 0.7) return 'confidence-high';
    if (confidence >= 0.4) return 'confidence-medium';
    return 'confidence-low';
}

/**
 * Format timestamp (HH:MM)
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Auto-scroll to bottom of chat
 */
function scrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ============================================
// CONTEXTUAL QUERY BUILDING
// ============================================

/**
 * Build a contextual query string from recent message history.
 * This allows the backend to understand follow-up questions without
 * changing the backend API.
 * 
 * Strategy:
 * - Take last N messages (e.g., 4 messages = 2 turns)
 * - Format as: "Önceki konuşma:\nKullanıcı: ...\nAsistan: ...\n\nYeni sorum: ..."
 * - If no history, return plain input
 * - Special handling for step-number follow-ups ("2. adımı anlamadım")
 * 
 * @param {Array} messages - Array of message objects { role, text, ... }
 * @param {string} currentInput - Current user input
 * @returns {string} - Contextual query string for backend
 */
function buildContextualQuery(messages, currentInput) {
    // Configuration
    const MAX_CONTEXT_MESSAGES = 4;      // Last 4 messages (2 turns: user+assistant, user+assistant)
    const MAX_USER_MESSAGE_LENGTH = 150; // User messages can be longer
    const MAX_ASSISTANT_BRIEF = 120;     // Brief assistant summary
    const MAX_ASSISTANT_FULL = 600;      // Full assistant text for step follow-ups
    const MAX_TOTAL_LENGTH = 1200;       // Total context character limit
    
    // If no history, return plain input (first message in conversation)
    if (!messages || messages.length === 0) {
        return currentInput;
    }
    
    // Get recent messages (excluding error messages)
    const recentMessages = messages
        .filter(msg => msg.role !== 'error')
        .slice(-MAX_CONTEXT_MESSAGES);
    
    // If no valid history, return plain input
    if (recentMessages.length === 0) {
        return currentInput;
    }
    
    // Detect if current input is asking about a specific step
    // Pattern: "2. adım", "3. adımı", "birinci adımda", etc.
    const stepPattern = /(\d+|birinci|ikinci|üçüncü|dördüncü|beşinci)\s*\.?\s*adım/i;
    const isStepFollowUp = stepPattern.test(currentInput);
    
    console.log('🔍 Step follow-up detected:', isStepFollowUp, 'in:', currentInput);
    
    // Build context lines
    const contextLines = [];
    let totalLength = 0;
    
    for (let i = 0; i < recentMessages.length; i++) {
        const msg = recentMessages[i];
        const roleLabel = msg.role === 'user' ? 'Kullanıcı' : 'Asistan';
        
        let msgText = msg.text;
        
        // Determine max length for this message
        let maxLen;
        if (msg.role === 'user') {
            maxLen = MAX_USER_MESSAGE_LENGTH;
        } else if (msg.role === 'assistant') {
            // If current input references steps AND this is the most recent assistant message,
            // include more context so the LLM can see all steps
            const isLastAssistant = (i === recentMessages.length - 1) || 
                                    (i === recentMessages.length - 2 && recentMessages[recentMessages.length - 1].role === 'user');
            
            if (isStepFollowUp && isLastAssistant) {
                maxLen = MAX_ASSISTANT_FULL;
            } else {
                maxLen = MAX_ASSISTANT_BRIEF;
            }
        }
        
        // Truncate if needed
        if (msgText.length > maxLen) {
            msgText = msgText.substring(0, maxLen) + '...';
        }
        
        // Clean up whitespace but preserve structure for multi-step answers
        msgText = msgText.replace(/\n{3,}/g, '\n\n').trim();
        
        const contextLine = `${roleLabel}: ${msgText}`;
        
        // Check total length limit
        if (totalLength + contextLine.length + currentInput.length + 100 > MAX_TOTAL_LENGTH) {
            // If we're about to exceed limit, stop adding earlier messages
            // but try to keep at least the last assistant message for step follow-ups
            if (isStepFollowUp && msg.role === 'assistant' && contextLines.length === 0) {
                // Force include this assistant message even if it's long
                contextLines.push(contextLine);
            }
            break;
        }
        
        contextLines.push(contextLine);
        totalLength += contextLine.length;
    }
    
    // If no context was built, return plain input
    if (contextLines.length === 0) {
        return currentInput;
    }
    
    // Build final contextual query
    let contextualQuery;
    
    if (isStepFollowUp) {
        // For step follow-ups, be more explicit
        contextualQuery = 
            "Önceki konuşma:\n" +
            contextLines.join("\n") +
            "\n\nKullanıcı şimdi yukarıdaki adımlardan biri hakkında soru soruyor: " + currentInput +
            "\n\nLütfen ilgili adımı daha detaylı açıkla.";
    } else {
        // Standard contextual query
        contextualQuery = 
            "Önceki konuşma:\n" +
            contextLines.join("\n") +
            "\n\nYeni sorum: " + currentInput;
    }
    
    console.log('📝 Contextual query built:', {
        historyMessages: contextLines.length,
        isStepFollowUp: isStepFollowUp,
        totalLength: contextualQuery.length,
        preview: contextualQuery.substring(0, 250) + '...'
    });
    
    return contextualQuery;
}

// ============================================
// CHAT SUBMISSION
// ============================================

/**
 * Submit chat query to backend
 */
async function submitChatQuery() {
    const queryInput = document.getElementById('query-input');
    const languageSelect = document.getElementById('language-select');
    const submitBtn = document.getElementById('chat-submit-btn');
    const sendBtnText = document.getElementById('send-btn-text');

    const query = queryInput.value.trim();
    const language = languageSelect.value;

    if (!query) {
        return; // Don't submit empty messages
    }

    // Disable input while processing
    submitBtn.disabled = true;
    queryInput.disabled = true;
    sendBtnText.textContent = '⏳ Gönderiliyor...';
    
    // Show loading indicator
    showLoading(true);

    // Clear input immediately
    queryInput.value = '';

    // Build contextual query BEFORE adding user message to history
    // This way the first message won't have "Önceki konuşma:" prefix
    const contextualQuery = buildContextualQuery(chatMessages, query);

    // NOW add user message to history for display
    const userMessage = {
        role: 'user',
        text: query,  // Store original query, not contextual
        timestamp: Date.now()
    };
    chatMessages.push(userMessage);
    renderChatMessages();

    try {
        // Get session ID for conversation tracking
        const currentSessionId = getOrCreateSessionId();
        
        console.log('🚀 Sending query to backend:', {
            originalInput: query,
            contextualQuery: contextualQuery.substring(0, 150) + '...',
            hasContext: contextualQuery !== query
        });
        
        // POST to /api/v1/chat (API unchanged - still just a query string!)
        const response = await fetch(API_ENDPOINTS.chat, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                query: contextualQuery,  // ← Now includes context!
                language: language,
                session_id: currentSessionId
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Chat response:', data);

        // Add assistant message to history
        const assistantMessage = {
            role: 'assistant',
            text: data.answer,
            timestamp: Date.now(),
            confidence: data.confidence,
            has_answer: data.has_answer,
            language: data.language,
            sources: data.sources || [],
            debug_info: data.debug_info || null  // Include debug info
        };
        chatMessages.push(assistantMessage);
        renderChatMessages();

    } catch (error) {
        console.error('Chat error:', error);
        
        // Add error message to chat
        const errorMessage = {
            role: 'error',
            text: `Bir hata oluştu: ${error.message}. Lütfen tekrar deneyin.`,
            timestamp: Date.now()
        };
        chatMessages.push(errorMessage);
        renderChatMessages();
    } finally {
        // Re-enable input
        submitBtn.disabled = false;
        queryInput.disabled = false;
        sendBtnText.textContent = '🚀 Gönder';
        showLoading(false);
        
        // Focus back to input
        queryInput.focus();
    }
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    const loadingDiv = document.getElementById('chat-loading');
    if (show) {
        loadingDiv.classList.remove('hidden');
    } else {
        loadingDiv.classList.add('hidden');
    }
}

// ============================================
// TAB NAVIGATION
// ============================================

function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const panels = document.querySelectorAll('.panel');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;

            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update active panel
            panels.forEach(panel => {
                if (panel.id === `${targetTab}-panel`) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
        });
    });
}

// ============================================
// ANOMALY PANEL - STATISTICS
// ============================================

async function loadAnomalyStats() {
    const loadBtn = document.getElementById('load-stats-btn');

    // Show loading state
    showAnomalyLoading('stats', true);
    hideAnomalyError('stats');
    hideAnomalyResult('stats');
    loadBtn.disabled = true;

    try {
        const response = await fetch(`${API_ENDPOINTS.anomalyStats}?days=7`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('Anomaly stats:', data);

        displayAnomalyStats(data);

    } catch (error) {
        console.error('Stats error:', error);
        showAnomalyError('stats', `Hata: ${error.message}`);
    } finally {
        showAnomalyLoading('stats', false);
        loadBtn.disabled = false;
    }
}

function displayAnomalyStats(data) {
    const resultDiv = document.getElementById('stats-result');
    resultDiv.classList.remove('hidden');

    // Summary
    const summaryDiv = document.getElementById('stats-summary');
    summaryDiv.innerHTML = `
        <div class="summary-item">
            <div class="summary-label">Toplam Window</div>
            <div class="summary-value">${data.summary.total_windows}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Toplam Ticket</div>
            <div class="summary-value">${data.summary.total_tickets}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Anomali Windows</div>
            <div class="summary-value">${data.summary.anomalous_windows}</div>
        </div>
    `;

    // Table of windows + drift scores
    const tableContainer = document.getElementById('stats-table-container');
    
    if (data.windows.length === 0) {
        tableContainer.innerHTML = '<p>Henüz window verisi yok.</p>';
        return;
    }

    let tableHTML = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Window Başlangıç</th>
                        <th>Ticket Sayısı</th>
                        <th>Volume Z-Score</th>
                        <th>Category Div</th>
                        <th>Embedding Shift</th>
                        <th>Combined Score</th>
                    </tr>
                </thead>
                <tbody>
    `;

    // Merge windows with drift_scores
    data.windows.forEach((window, idx) => {
        const drift = data.drift_scores[idx] || {};
        const windowDate = new Date(window.window_start).toLocaleDateString('tr-TR');

        tableHTML += `
            <tr>
                <td>${windowDate}</td>
                <td>${window.total_tickets}</td>
                <td>${(drift.volume_zscore || 0).toFixed(2)}</td>
                <td>${(drift.category_divergence || 0).toFixed(3)}</td>
                <td>${(drift.embedding_shift || 0).toFixed(3)}</td>
                <td><strong>${(drift.combined_score || 0).toFixed(3)}</strong></td>
            </tr>
        `;
    });

    tableHTML += `
                </tbody>
            </table>
        </div>
    `;

    tableContainer.innerHTML = tableHTML;
}

// ============================================
// ANOMALY PANEL - EVENTS
// ============================================

async function loadAnomalyEvents() {
    const loadBtn = document.getElementById('load-events-btn');

    // Show loading state
    showAnomalyLoading('events', true);
    hideAnomalyError('events');
    hideAnomalyResult('events');
    loadBtn.disabled = true;

    try {
        const response = await fetch(`${API_ENDPOINTS.anomalyDetect}?min_severity=info`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('Anomaly events:', data);

        displayAnomalyEvents(data);

    } catch (error) {
        console.error('Events error:', error);
        showAnomalyError('events', `Hata: ${error.message}`);
    } finally {
        showAnomalyLoading('events', false);
        loadBtn.disabled = false;
    }
}

function displayAnomalyEvents(data) {
    const resultDiv = document.getElementById('events-result');
    resultDiv.classList.remove('hidden');

    // Summary
    const summaryDiv = document.getElementById('events-summary');
    
    const sevDist = data.severity_distribution || {};
    summaryDiv.innerHTML = `
        <div class="summary-item">
            <div class="summary-label">Toplam Windows</div>
            <div class="summary-value">${data.total_windows}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Anomalous</div>
            <div class="summary-value">${data.anomalous_windows}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Info</div>
            <div class="summary-value" style="color: #4299e1;">${sevDist.info || 0}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Warning</div>
            <div class="summary-value" style="color: #ed8936;">${sevDist.warning || 0}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Critical</div>
            <div class="summary-value" style="color: #e53e3e;">${sevDist.critical || 0}</div>
        </div>
    `;

    // Events list
    const eventsList = document.getElementById('events-list');
    
    if (data.events.length === 0) {
        eventsList.innerHTML = '<p>Anomali event bulunmadı.</p>';
        return;
    }

    eventsList.innerHTML = '';

    data.events.forEach(event => {
        const eventItem = document.createElement('div');
        eventItem.className = `event-item severity-${event.severity}`;

        const windowStart = new Date(event.window_start).toLocaleDateString('tr-TR');
        const windowEnd = new Date(event.window_end).toLocaleDateString('tr-TR');

        const reasonsHTML = event.reasons.map(r => `<li>${r}</li>`).join('');

        eventItem.innerHTML = `
            <div class="event-header">
                <span class="event-time">${windowStart} - ${windowEnd}</span>
                <span class="severity-badge severity-${event.severity}">${event.severity}</span>
            </div>
            <div class="event-score">Combined Score: ${event.score.toFixed(3)}</div>
            <ul class="event-reasons">
                ${reasonsHTML}
            </ul>
        `;

        eventsList.appendChild(eventItem);
    });
}

// ============================================
// ANOMALY UTILITY FUNCTIONS
// ============================================

function showAnomalyLoading(section, show) {
    const loadingDiv = document.getElementById(`${section}-loading`);
    if (loadingDiv) {
        if (show) {
            loadingDiv.classList.remove('hidden');
        } else {
            loadingDiv.classList.add('hidden');
        }
    }
}

function showAnomalyError(section, message) {
    const errorDiv = document.getElementById(`${section}-error`);
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }
}

function hideAnomalyError(section) {
    const errorDiv = document.getElementById(`${section}-error`);
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
}

function hideAnomalyResult(section) {
    const resultDiv = document.getElementById(`${section}-result`);
    if (resultDiv) {
        resultDiv.classList.add('hidden');
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 BT Destek Asistanı - Chat Interface initialized');
    console.log('API Base URL:', API_BASE_URL);

    // Initialize tabs
    initTabs();

    // Initialize session
    getOrCreateSessionId();

    // Render initial empty chat
    renderChatMessages();

    // Chat submit button
    const chatSubmitBtn = document.getElementById('chat-submit-btn');
    chatSubmitBtn.addEventListener('click', submitChatQuery);

    // Enter key in query input (Shift+Enter for new line)
    const queryInput = document.getElementById('query-input');
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitChatQuery();
        }
    });

    // Anomaly buttons
    const loadStatsBtn = document.getElementById('load-stats-btn');
    loadStatsBtn.addEventListener('click', loadAnomalyStats);

    const loadEventsBtn = document.getElementById('load-events-btn');
    loadEventsBtn.addEventListener('click', loadAnomalyEvents);

    console.log('✅ Event listeners registered');
    console.log('💬 Chat interface ready - Start typing your question!');
});
