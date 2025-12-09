# 🧪 **CHAT MEMORY TEST GUIDE**

## **🎯 QUICK START**

### **1. Refresh Browser**
```
Ctrl + Shift + R
```
Hard refresh to clear JavaScript cache!

### **2. Open Developer Console**
```
F12 → Console tab
```
You'll see debug logs showing context building.

### **3. Navigate to Chat Tab**
```
Click: 💬 Chat (RAG)
```

---

## **✅ TEST SCENARIO 1: FIRST MESSAGE (No Context)**

### **Input:**
```
VPN bağlantı sorunu yaşıyorum
```

### **Expected Console Output:**
```javascript
🔍 Step follow-up detected: false in: VPN bağlantı sorunu yaşıyorum
📝 Contextual query built: {
  historyMessages: 0,
  isStepFollowUp: false,
  totalLength: 34,
  preview: "VPN bağlantı sorunu yaşıyorum"
}
🚀 Sending query to backend: {
  originalInput: "VPN bağlantı sorunu yaşıyorum",
  contextualQuery: "VPN bağlantı sorunu yaşıyorum",
  hasContext: false  ← CRITICAL: Should be FALSE!
}
```

### **Expected Response:**
✅ Multi-step VPN troubleshooting answer
✅ Should contain: "Adım 1:", "Adım 2:", "Adım 3:"
✅ Should mention: VPN istemcisi, ayarlar, bağlantı
✅ Confidence: ~60-80%
✅ Sources: VPN-related tickets

### **❌ FAIL If:**
- Console shows `hasContext: true` (means context was added to first message!)
- Response is about Outlook or unrelated topic
- No steps in response

---

## **✅ TEST SCENARIO 2: STEP FOLLOW-UP (Full Context)**

### **Input:**
```
2. adımı anlamadım
```

### **Expected Console Output:**
```javascript
🔍 Step follow-up detected: true in: 2. adımı anlamadım  ← CRITICAL!
📝 Contextual query built: {
  historyMessages: 2,
  isStepFollowUp: true,  ← CRITICAL!
  totalLength: 850,  ← Should be ~700-900 (includes full steps)
  preview: "Önceki konuşma:\nKullanıcı: VPN bağlantı sorunu yaşıyorum\nAsistan: Sorununuz: VPN bağlantı sorunu yaşıyorsunuz.\n\n**Adım 1: VPN İstemcisini Kontrol Edin**..."
}
🚀 Sending query to backend: {
  originalInput: "2. adımı anlamadım",
  contextualQuery: "Önceki konuşma:\nKullanıcı: VPN bağlantı...",  ← Long context!
  hasContext: true  ← CRITICAL: Should be TRUE!
}
```

### **Expected Response:**
✅ Detailed explanation of **Step 2** from VPN answer
✅ Should mention: "Bağlantı ayarları", "VPN istemcisini açın", "sunucu adresi"
✅ Should NOT switch topics to Outlook or other unrelated content
✅ Confidence: ~60-80%

### **❌ FAIL If:**
- Console shows `isStepFollowUp: false` (pattern not detected!)
- `totalLength < 400` (assistant context was truncated!)
- Response switches topic (e.g., talks about Outlook instead of VPN)
- Response says "Cevap bulunamadı" or has very low confidence

---

## **✅ TEST SCENARIO 3: GENERAL FOLLOW-UP**

### **Input:**
```
Teşekkürler, anladım
```

### **Expected Console Output:**
```javascript
🔍 Step follow-up detected: false in: Teşekkürler, anladım
📝 Contextual query built: {
  historyMessages: 2-4,
  isStepFollowUp: false,
  totalLength: 200-400,  ← Shorter than step follow-up
  preview: "Önceki konuşma:\nKullanıcı: VPN bağlantı sorunu yaşıyorum\nAsistan: Sorununuz: VPN..."
}
🚀 Sending query to backend: {
  originalInput: "Teşekkürler, anladım",
  hasContext: true
}
```

### **Expected Response:**
✅ Polite acknowledgment
✅ Should mention VPN or previous topic
✅ Something like: "Rica ederim!", "Başka bir sorunuz varsa..."

---

## **✅ TEST SCENARIO 4: NEW TOPIC (With Brief Context)**

### **Input:**
```
Outlook şifremi nasıl değiştiririm?
```

### **Expected Console Output:**
```javascript
🔍 Step follow-up detected: false in: Outlook şifremi nasıl değiştiririm?
📝 Contextual query built: {
  historyMessages: 2-4,
  isStepFollowUp: false,
  totalLength: 250-500,
  preview: "Önceki konuşma:\nKullanıcı: VPN bağlantı sorunu yaşıyorum\nAsistan: Sorununuz: VPN...\nKullanıcı: 2. adımı...\nAsistan: Tabii, 2. adım...\n\nYeni sorum: Outlook şifremi nasıl değiştiririm?"
}
```

### **Expected Response:**
✅ Multi-step Outlook password change instructions
✅ Should contain: Outlook, şifre, değiştirme
✅ Should NOT be confused with VPN topic
✅ RAG should find Outlook-related tickets

---

## **✅ TEST SCENARIO 5: ANOTHER STEP FOLLOW-UP**

### **Input:**
```
birinci adımı tekrar anlatır mısın?
```

### **Expected Console Output:**
```javascript
🔍 Step follow-up detected: true in: birinci adımı tekrar anlatır mısın?  ← Word "birinci" detected!
📝 Contextual query built: {
  isStepFollowUp: true,
  totalLength: 700-900
}
```

### **Expected Response:**
✅ Detailed explanation of Step 1 from the Outlook answer
✅ Should be about **Outlook password**, NOT VPN

---

## **🎨 UI VERIFICATION**

### **Chat History Should Show:**

```
┌─────────────────────────────────────────┐
│  [User bubble - right side]             │
│  VPN bağlantı sorunu yaşıyorum          │
│  15:30                                  │
│                                         │
│  [Assistant bubble - left side]         │
│  Sorununuz: VPN bağlantı...             │
│  **Adım 1:** ...                        │
│  **Adım 2:** ...                        │
│  **Adım 3:** ...                        │
│  [Güven: 67%] [✅ Cevap Bulundu] [TR]   │
│  📚 Kaynaklar: 1. VPN bağlantısı...     │
│  15:30                                  │
│                                         │
│  [User bubble - right side]             │
│  2. adımı anlamadım                     │
│  15:31                                  │
│                                         │
│  [Assistant bubble - left side]         │
│  Tabii, 2. adımı daha detaylı...        │
│  1. **VPN İstemcisini Açma:**           │
│  2. **Sunucu Adresi Girişi:**           │
│  ...                                    │
│  [Güven: 72%] [✅ Cevap Bulundu] [TR]   │
│  15:31                                  │
└─────────────────────────────────────────┘
```

### **Check:**
- ✅ All messages visible
- ✅ User messages purple/blue (right)
- ✅ Assistant messages white (left)
- ✅ Bold formatting works (`**text**` → **text**)
- ✅ Line breaks preserved
- ✅ Confidence badges show
- ✅ Sources listed
- ✅ Auto-scroll to bottom
- ✅ Timestamps visible

---

## **❌ COMMON ISSUES & FIXES**

### **Issue 1: First message has context**
**Symptom:** Console shows `hasContext: true` for first message

**Fix:** Hard refresh (Ctrl+Shift+R) - browser cached old JS

---

### **Issue 2: Step follow-ups don't work**
**Symptom:** Console shows `isStepFollowUp: false` for "2. adımı anlamadım"

**Check:**
1. Browser console for detection log
2. Pattern should match Turkish numbers
3. Try: `"2. adım"`, `"ikinci adımı"`, `"3. adımda"`

---

### **Issue 3: Context too short**
**Symptom:** Step follow-up has `totalLength < 400`

**Check:** Assistant messages should be ~600 chars for step follow-ups

**Console:** Should show `isStepFollowUp: true`

---

### **Issue 4: Wrong topic in follow-up**
**Symptom:** Ask about "2. adım" but response talks about different topic

**Possible causes:**
- Context not including full assistant answer
- RAG finding wrong tickets (check sources)
- LLM hallucinating (check confidence)

**Debug:**
1. Check console `preview` - should show all steps
2. Check `totalLength` - should be ~700-900 for step follow-ups
3. Check backend logs - what query was received?

---

## **🔧 DEBUGGING COMMANDS**

### **Clear Chat History:**
Open browser console:
```javascript
clearSession();
```
This will reset the chat and start fresh.

### **Check Current Messages:**
```javascript
console.log(chatMessages);
```
See all messages in memory.

### **Check Session ID:**
```javascript
console.log(sessionId);
```

---

## **📊 SUCCESS CRITERIA**

### **✅ ALL TESTS PASS IF:**

1. **First Message:**
   - `hasContext: false` ✅
   - Plain query (no "Önceki konuşma:") ✅
   - Correct topic ✅

2. **Step Follow-Up:**
   - `isStepFollowUp: true` ✅
   - `totalLength: 700-900` ✅
   - Full assistant context (all steps visible in preview) ✅
   - Response elaborates on correct step ✅
   - Same topic maintained ✅

3. **General Follow-Up:**
   - `isStepFollowUp: false` ✅
   - `totalLength: 200-500` ✅
   - Brief assistant context ✅
   - Topic maintained ✅

4. **UI:**
   - All messages visible ✅
   - Proper formatting ✅
   - Auto-scroll works ✅

5. **Anomaly:**
   - Anomaly tab still works ✅
   - No errors in console ✅

---

## **🚀 FINAL CHECK**

Run this complete conversation:

```
1. "VPN bağlantı sorunu yaşıyorum"
   → Check: hasContext: false ✅
   → Check: Multi-step VPN answer ✅

2. "2. adımı anlamadım"
   → Check: isStepFollowUp: true ✅
   → Check: totalLength > 600 ✅
   → Check: Detailed step 2 about VPN ✅

3. "Teşekkürler"
   → Check: Polite response ✅

4. "Outlook şifremi unuttum"
   → Check: Outlook answer (NEW topic) ✅

5. "3. adımı tekrar söyler misin?"
   → Check: isStepFollowUp: true ✅
   → Check: Detailed step 3 about OUTLOOK (not VPN!) ✅
```

If ALL checks pass: **✅ CHAT MEMORY WORKING PERFECTLY!**

---

**Ready to test? Refresh browser and start typing!** 🎉

