# 💻 CMD Terminalinde Komutlar

## ⚠️ ÖNEMLİ: Conda Aktifleştirme

**YANLIŞ:**
```cmd
activate.bat base  ❌
```

**DOĞRU:**
```cmd
C:\Users\gamze.yarimkulak\AppData\Local\anaconda3\Scripts\activate.bat base  ✅
```

---

## 📋 Tam Komut Dizisi

### İndeks Oluşturma:

```cmd
cd /d C:\Users\gamze.yarimkulak\Desktop\bt-support-assistant
```

```cmd
C:\Users\gamze.yarimkulak\AppData\Local\anaconda3\Scripts\activate.bat base
```

```cmd
conda activate bt-support
```

```cmd
python scripts/build_and_test_index.py
```

---

### Server Başlatma:

```cmd
cd /d C:\Users\gamze.yarimkulak\Desktop\bt-support-assistant
```

```cmd
C:\Users\gamze.yarimkulak\AppData\Local\anaconda3\Scripts\activate.bat base
```

```cmd
conda activate bt-support
```

```cmd
python scripts/run_server.py
```

---

## 🔧 Sorun Giderme

### "conda: command not found"
```cmd
C:\Users\gamze.yarimkulak\AppData\Local\anaconda3\Scripts\conda.exe activate bt-support
```

### "ModuleNotFoundError"
```cmd
pip install -r requirements.txt
```

### "Indexes not found"
Önce indeksleri oluşturun (yukarıdaki komutlar).

---

## 💡 İpucu

Her yeni CMD penceresinde ortamı tekrar aktifleştirmeniz gerekir.
