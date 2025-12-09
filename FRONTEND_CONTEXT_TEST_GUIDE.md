# 🧪 FRONTEND CONTEXT - TEST EXAMPLES

## 📋 **TEST SCENARIO 1: VPN TROUBLESHOOTING**

### **Conversation:**

**Message 1 (User):**
```
VPN'e bağlanamıyorum
```

**Backend Receives:**
```json
{
    "query": "VPN'e bağlanamıyorum",
    "language": "tr",
    "session_id": "session_1234..."
}
```
✅ No context (first message)

---

**Message 2 (Assistant):**
```
VPN bağlantı sorunları için şu adımları deneyin:

1. **VPN istemcisini yeniden başlatın**
   - Uygulamayı tamamen kapatın
   - 10 saniye bekleyin
   - Yeniden açın

2. **Ağ bağlantınızı kontrol edin**
   - WiFi/Ethernet bağlantınızın aktif olduğundan emin olun
   
3. **Kimlik bilgilerinizi doğrulayın**
   - Kullanıcı adı ve şifrenizin doğru olduğunu kontrol edin
```

---

**Message 3 (User):**
```
3. adımı yapamadım, detaylandırır mısın?
```

**Backend Receives (WITH CONTEXT):**
```json
{
    "query": "Önceki konuşma:\nKullanıcı: VPN'e bağlanamıyorum\nAsistan: VPN bağlantı sorunları için şu adımları deneyin: 1. **VPN istemcisini yeniden başlatın** - Uygulamayı tamamen kapatın - 10 saniye bekleyin - Yeniden açın 2. **Ağ bağlantınızı kontrol edin** - WiFi/Ethernet bağlantınızın aktif olduğundan emin olun 3. **Kimlik bilgileri...\n\nYeni sorum: 3. adımı yapamadım, detaylandırır mısın?",
    "language": "tr",
    "session_id": "session_1234..."
}
```

✅ Backend now knows:
- Topic: VPN
- Which step: 3 (kimlik bilgileri)
- Context: Previous troubleshooting steps

**Result:** Bot can give detailed answer about step 3 (credentials) ✅

---

## 📋 **TEST SCENARIO 2: OUTLOOK PASSWORD RESET**

### **Conversation:**

**Message 1 (User):**
```
Outlook şifremi nasıl sıfırlarım?
```

**Backend Receives:**
```json
{
    "query": "Outlook şifremi nasıl sıfırlarım?",
    "language": "tr"
}
```

---

**Message 2 (Assistant):**
```
Outlook şifrenizi sıfırlamak için:

1. Self-service portal'a gidin (https://password.company.com)
2. "Şifremi Unuttum" butonuna tıklayın
3. Email adresinize gelen doğrulama kodunu girin
4. Yeni şifrenizi belirleyin
5. 15 dakika içinde Outlook'u yeniden başlatın
```

---

**Message 3 (User):**
```
Mail gelmiyor
```

**Backend Receives (WITH CONTEXT):**
```json
{
    "query": "Önceki konuşma:\nKullanıcı: Outlook şifremi nasıl sıfırlarım?\nAsistan: Outlook şifrenizi sıfırlamak için: 1. Self-service portal'a gidin (https://password.company.com) 2. \"Şifremi Unuttum\" butonuna tıklayın 3. Email adresinize gelen doğrulama kodunu girin...\n\nYeni sorum: Mail gelmiyor",
    "language": "tr"
}
```

✅ Backend understands:
- "Mail" = password reset verification email
- Not about general email issues
- Context: User is in middle of password reset process

---

**Message 4 (Assistant):**
```
Doğrulama maili gelmiyorsa:

1. Spam/Junk klasörünü kontrol edin
2. 5 dakika bekleyin (bazen gecikme olur)
3. "Kodu Tekrar Gönder" butonunu deneyin
4. Alternatif email adresinizi kullanın (varsa)
```

---

**Message 5 (User):**
```
Spam'de de yok, ne yapmalıyım?
```

**Backend Receives (WITH CONTEXT - Last 6 messages):**
```json
{
    "query": "Önceki konuşma:\nKullanıcı: Outlook şifremi nasıl sıfırlarım?\nAsistan: Outlook şifrenizi sıfırlamak için: 1. Self-service portal'a gidin...\nKullanıcı: Mail gelmiyor\nAsistan: Doğrulama maili gelmiyorsa: 1. Spam/Junk klasörünü kontrol edin 2. 5 dakika bekleyin 3. \"Kodu Tekrar Gönder\" butonunu deneyin...\n\nYeni sorum: Spam'de de yok, ne yapmalıyım?",
    "language": "tr"
}
```

✅ Full conversation context maintained
✅ Bot can escalate to IT support with proper context

---

## 📋 **TEST SCENARIO 3: HARDWARE ISSUE**

### **Conversation:**

**Message 1:**
```
Bilgisayarım çok yavaş
```

**Backend Receives:**
```
"Bilgisayarım çok yavaş"
```

---

**Message 2 (Assistant):**
```
Yavaşlık sorunları için:

1. Task Manager'da CPU/RAM kullanımını kontrol edin
2. Disk temizliği yapın
3. Startup programlarını azaltın
```

---

**Message 3:**
```
Nereden açıyorum?
```

**Backend Receives (WITH CONTEXT):**
```
"Önceki konuşma:\nKullanıcı: Bilgisayarım çok yavaş\nAsistan: Yavaşlık sorunları için: 1. Task Manager'da CPU/RAM kullanımını kontrol edin 2. Disk temizliği yapın 3. Startup programlarını azaltın\n\nYeni sorum: Nereden açıyorum?"
```

✅ Bot knows "nereden" refers to Task Manager
✅ Can provide specific instructions for opening Task Manager

---

## 🔍 **NETWORK TAB INSPECTION**

### **How to Verify in Browser DevTools:**

1. Open http://localhost:8000/ui/index.html
2. Open DevTools (F12)
3. Go to **Network** tab
4. Filter: XHR or Fetch
5. Send a follow-up message
6. Click on the request
7. Go to **Payload** or **Request** tab

**You should see:**

```json
{
    "query": "Önceki konuşma:\nKullanıcı: ...\nAsistan: ...\n\nYeni sorum: ...",
    "language": "tr",
    "session_id": "session_..."
}
```

**Key indicators context is working:**
- ✅ Query starts with "Önceki konuşma:"
- ✅ Contains "Kullanıcı:" and "Asistan:" labels
- ✅ Ends with "Yeni sorum: [current input]"
- ✅ Length > 200 chars (for follow-ups)

---

## 📊 **CONSOLE LOG EXAMPLES**

### **First Message (No Context):**
```
🚀 Sending query to backend: {
    originalInput: "VPN sorunu",
    contextualQuery: "VPN sorunu...",
    hasContext: false
}
```

### **Follow-up Message (With Context):**
```
📝 Contextual query built: {
    historyMessages: 2,
    totalLength: 287,
    preview: "Önceki konuşma:\nKullanıcı: VPN sorunu\nAsistan: VPN için şu adımları deneyin: 1) Bağlantıyı sıfırlayın 2) VPN istemcisini yeniden başlatın...\n\nYeni sorum: 3. adımı nasıl yaparım?..."
}

🚀 Sending query to backend: {
    originalInput: "3. adımı nasıl yaparım?",
    contextualQuery: "Önceki konuşma:\nKullanıcı: VPN sorunu\nAsistan: VPN için şu adımları deneyin...",
    hasContext: true
}
```

---

## ✅ **SUCCESS CRITERIA**

### **Test 1: First Message**
- [ ] Console shows `hasContext: false`
- [ ] Network payload has plain query
- [ ] No "Önceki konuşma:" in request

### **Test 2: Follow-up**
- [ ] Console shows `hasContext: true`
- [ ] Console shows `historyMessages: 2` (or more)
- [ ] Network payload includes "Önceki konuşma:"
- [ ] Network payload includes previous user/assistant messages
- [ ] Network payload ends with "Yeni sorum: [input]"

### **Test 3: Vague Follow-up**
- [ ] User asks "3. adımı yapamadım"
- [ ] Backend receives context about which steps
- [ ] Bot gives relevant answer (not confused)
- [ ] Answer refers to correct step

### **Test 4: Long Conversation**
- [ ] After 10+ messages, context still included
- [ ] Only last 6 messages in context (truncated)
- [ ] Total query length < 1500 chars
- [ ] No performance issues

---

## 🎯 **EXPECTED BEHAVIOR**

### **Before Implementation:**
```
User: "VPN sorunu"
Bot: [VPN troubleshooting steps]
User: "3. adımı yapamadım"
Bot: "Hangi 3. adımdan bahsediyorsunuz?" ❌ CONFUSED
```

### **After Implementation:**
```
User: "VPN sorunu"
Bot: [VPN troubleshooting steps]
User: "3. adımı yapamadım"
Bot: "VPN kimlik bilgilerini doğrulamak için..." ✅ UNDERSTANDS
```

---

## 🐛 **TROUBLESHOOTING**

### **Issue: Context Not Included**

**Symptom:**
- Network payload shows plain query (no "Önceki konuşma:")
- Console shows `hasContext: false`

**Possible Causes:**
1. `chatMessages` array is empty
2. All messages are errors (filtered out)
3. Function not called correctly

**Fix:**
- Check console: `console.log('chatMessages:', chatMessages)`
- Verify messages have `role` and `text` fields
- Ensure `buildContextualQuery()` is called before fetch

---

### **Issue: Query Too Long**

**Symptom:**
- Backend times out
- Retrieval is very slow

**Possible Causes:**
- `MAX_TOTAL_LENGTH` too high
- Very long assistant responses not truncated

**Fix:**
- Reduce `MAX_CONTEXT_MESSAGES` from 6 to 4
- Reduce `MAX_MESSAGE_LENGTH` from 300 to 200
- Reduce `MAX_TOTAL_LENGTH` from 1500 to 1000

---

### **Issue: Wrong Messages in Context**

**Symptom:**
- Irrelevant context included
- Old conversation topics mixed in

**Possible Causes:**
- `chatMessages` array not filtered properly
- Error messages included

**Fix:**
- Verify error filtering: `filter(msg => msg.role !== 'error')`
- Check `.slice(-MAX_CONTEXT_MESSAGES)` works correctly

---

## 🎉 **READY TO TEST!**

1. ✅ Start server: `python scripts/run_server.py`
2. ✅ Open: http://localhost:8000/ui/index.html
3. ✅ Open DevTools Network tab
4. ✅ Ask first question: "VPN sorunu"
5. ✅ Ask follow-up: "3. adımı nasıl yaparım?"
6. ✅ Check Network payload includes context
7. ✅ Verify bot understands follow-up

**Expected Result:** Bot perfectly understands vague follow-ups! 🎯



