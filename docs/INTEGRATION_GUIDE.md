# CorteQS Intelligence Engine - Entegrasyon Rehberi

Bu döküman, CorteQS platformunun kullandığı tüm harici servisleri ve gerekli credentials'ları açıklar.

---

## 1. SLACK ENTEGRASYONU

### Ne İçin Kullanılıyor?
- Slack kanallarındaki mesajları çekme
- Kullanıcı bilgilerini alma
- Dosya ve attachment'ları indirme
- Knowledge Graph'e Slack verilerini ekleme

### Gerekli Credential
| Değişken | Açıklama |
|----------|----------|
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token (xoxb-... veya xoxe-... ile başlar) |

### Nasıl Alınır?
1. https://api.slack.com/apps adresine gidin
2. "Create New App" → "From scratch" seçin
3. App adı ve workspace seçin
4. Sol menüden "OAuth & Permissions" tıklayın
5. "Bot Token Scopes" altına şu izinleri ekleyin:
   - `channels:history` - Kanal mesajlarını okuma
   - `channels:read` - Kanal listesini görme
   - `users:read` - Kullanıcı bilgilerini okuma
   - `files:read` - Dosyaları okuma
6. "Install to Workspace" butonuna tıklayın
7. "Bot User OAuth Token" kopyalayın

### CorteQS'de Kullanımı
```
Slack kanalları → Mesajlar çekilir → Knowledge Graph'e "document" node olarak eklenir
Slack kullanıcıları → "person" node olarak eklenir
Mesaj içerikleri → AI tarafından analiz edilir, önemli konular "topic" olarak çıkarılır
```

---

## 2. GITHUB ENTEGRASYONU

### Ne İçin Kullanılıyor?
- Repository bilgilerini çekme
- Issue ve Pull Request'leri okuma
- Commit geçmişini analiz etme
- README ve dokümantasyon dosyalarını indirme
- Contributor bilgilerini alma

### Gerekli Credential
| Değişken | Açıklama |
|----------|----------|
| `GITHUB_TOKEN` | Personal Access Token (ghp_... veya github_pat_... ile başlar) |

### Nasıl Alınır?
1. https://github.com/settings/tokens adresine gidin
2. "Generate new token" → "Fine-grained tokens" seçin
3. Token adı ve süresini belirleyin
4. Repository access: "All repositories" veya spesifik repo'lar
5. Permissions altında şunları seçin:
   - `Contents: Read` - Dosya içeriklerini okuma
   - `Issues: Read` - Issue'ları okuma
   - `Pull requests: Read` - PR'ları okuma
   - `Metadata: Read` - Repo bilgilerini okuma
6. "Generate token" tıklayın ve kopyalayın

### CorteQS'de Kullanımı
```
Repositories → "project" node olarak eklenir
Issues/PRs → "document" node olarak eklenir
Contributors → "person" node olarak eklenir (Slack kullanıcılarıyla eşleştirilir)
Commit mesajları → AI analizi ile "topic" ve "event" çıkarılır
```

---

## 3. GOOGLE DRIVE ENTEGRASYONU

### Ne İçin Kullanılıyor?
- Drive'daki dosyaları listeleme
- Doküman içeriklerini okuma (Google Docs, Sheets, PDF, vb.)
- Dosya paylaşım bilgilerini alma
- Klasör yapısını analiz etme

### Gerekli Credentials
| Değişken | Açıklama |
|----------|----------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service Account credentials (JSON formatında) |

### Nasıl Alınır?
1. https://console.cloud.google.com adresine gidin
2. Yeni proje oluşturun veya mevcut projeyi seçin
3. "APIs & Services" → "Enable APIs" → "Google Drive API" etkinleştirin
4. "APIs & Services" → "Credentials" gidin
5. "Create Credentials" → "Service Account" seçin
6. Service account adı girin, oluşturun
7. Oluşturulan service account'a tıklayın
8. "Keys" sekmesi → "Add Key" → "Create new key" → JSON seçin
9. İndirilen JSON dosyasının içeriğini kopyalayın

### CorteQS'de Kullanımı
```
Google Docs → İçerik çekilir → "document" node olarak eklenir
Sheets → Tablo verileri analiz edilir → İlgili node'larla bağlantı kurulur
PDF/Dosyalar → OCR/AI ile içerik çıkarılır → Knowledge Graph'e eklenir
Paylaşım bilgileri → "person" node'ları arasında bağlantı kurulur
```

---

## 4. NEO4J AURA (GRAPH DATABASE)

### Ne İçin Kullanılıyor?
- Knowledge Graph'in asıl depolama yeri
- Node'lar arası ilişkilerin verimli sorgulanması
- Graf algoritmaları (PageRank, Community Detection, Shortest Path)
- Görselleştirme için optimized veri çekme

### Gerekli Credentials
| Değişken | Açıklama |
|----------|----------|
| `NEO4J_URI` | Bağlantı adresi (neo4j+s://xxxxx.databases.neo4j.io) |
| `NEO4J_USER` | Kullanıcı adı (genellikle "neo4j") |
| `NEO4J_PASSWORD` | Veritabanı şifresi |

### Nasıl Alınır?
1. https://neo4j.com/cloud/aura/ adresine gidin
2. Ücretsiz hesap oluşturun (Free tier mevcut)
3. "Create Database" tıklayın
4. Database adı girin, region seçin
5. Oluşturulduktan sonra "Connect" butonuna tıklayın
6. Connection URI, Username ve Password gösterilecek
7. **ÖNEMLİ:** Password sadece bir kez gösterilir, kaydedin!

### CorteQS'de Kullanımı
```
MongoDB → Temel veri depolama (users, sessions, activities)
Neo4j → Knowledge Graph node ve edge'leri
         → Graf sorguları (MATCH, MERGE, vb.)
         → İlişki analizi

Örnek Cypher sorgusu:
MATCH (p:Person)-[:WORKS_ON]->(proj:Project)
WHERE proj.name = 'CorteQS'
RETURN p.name, proj.name
```

---

## 5. ELASTICSEARCH CLOUD

### Ne İçin Kullanılıyor?
- Full-text arama (tüm içeriklerde hızlı arama)
- Fuzzy matching (yazım hatalarına toleranslı arama)
- Aggregation (istatistik ve gruplama)
- Autocomplete önerileri

### Gerekli Credentials
| Değişken | Açıklama |
|----------|----------|
| `ELASTICSEARCH_CLOUD_ID` | Cloud deployment ID |
| `ELASTICSEARCH_API_KEY` | API erişim anahtarı |

### Nasıl Alınır?
1. https://cloud.elastic.co adresine gidin
2. Ücretsiz hesap oluşturun (14 gün trial)
3. "Create Deployment" tıklayın
4. Deployment adı girin, region ve size seçin
5. Deployment oluştuktan sonra "Manage" tıklayın
6. **Cloud ID:** Deployment overview sayfasında görünür
7. **API Key:** Security → API Keys → Create API Key
   - Name girin
   - "Create API Key" tıklayın
   - Encoded key'i kopyalayın

### CorteQS'de Kullanımı
```
Knowledge node'ları → Elasticsearch'e index'lenir
Arama yapıldığında → Elasticsearch sorgulanır → Hızlı sonuç döner
Autocomplete → Kullanıcı yazarken öneri gösterir

Örnek:
"proje planı" araması →
  - "Proje Planlama Dokümanı" bulunur
  - "2024 Q1 Plan" bulunur
  - "Planning Meeting Notes" bulunur
```

---

## ÖZET: .env DOSYASI YAPISI

```env
# Mevcut (değişmeyecek)
MONGO_URL=mongodb://localhost:27017
DB_NAME=corteqs_engine
EMERGENT_LLM_KEY=sk-emergent-xxxxx

# Slack
SLACK_BOT_TOKEN=xoxb-xxxxx-xxxxx-xxxxx

# GitHub  
GITHUB_TOKEN=ghp_xxxxx veya github_pat_xxxxx

# Google Drive (JSON string olarak)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}

# Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxxxx

# Elasticsearch
ELASTICSEARCH_CLOUD_ID=deployment:xxxxx
ELASTICSEARCH_API_KEY=xxxxx
```

---

## VERİ AKIŞI DİYAGRAMI

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SLACK     │     │   GITHUB    │     │   GDRIVE    │
│  (mesajlar) │     │  (repo/PR)  │     │  (dosyalar) │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                 ┌─────────────────┐
                 │   DATA SYNC     │
                 │    SERVICE      │
                 │  (Backend API)  │
                 └────────┬────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │  MONGODB   │  │   NEO4J    │  │ELASTICSEARCH│
   │ (metadata) │  │  (graph)   │  │  (search)   │
   └────────────┘  └────────────┘  └────────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │    GEMINI AI    │
                 │  (Q&A, Analiz)  │
                 └─────────────────┘
```

---

## GÜVENLİK NOTLARI

⚠️ **Önemli:**
- Credentials'ları asla kod içinde hardcode etmeyin
- .env dosyasını .gitignore'a ekleyin
- Production'da environment variables kullanın
- API key'leri düzenli olarak rotate edin
- Minimum gerekli izinleri verin (principle of least privilege)

---

*Bu döküman CorteQS Intelligence Engine v1.0 için hazırlanmıştır.*
*Sorularınız için AI Assistant'ı kullanabilirsiniz.*
