# CorteQS Coolify Deploy Rehberi

Bu doküman, `CorteQS Intelligence Engine` projesini Coolify üzerinde üretim benzeri şekilde ayağa kaldırmak için hazırlanmıştır. Amaç yalnızca "deploy olsun" değil, aynı zamanda hangi servisin neden öyle konumlandığını, hangi environment variable'ın ne işe yaradığını, ilk açılışta neyin kontrol edilmesi gerektiğini ve olası hatalarda nereye bakılacağını netleştirmektir.

Bu rehber, repoda bulunan şu dosyalara dayanır:

- `docker-compose.coolify.yaml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `coolify.env.example`

## 1. Genel Mimari

Bu proje Coolify üzerinde iki servisli bir yapı ile çalışacak şekilde hazırlanmıştır:

- `frontend`
  React uygulaması build edilir ve Nginx üzerinden sunulur.
- `backend`
  FastAPI uygulaması `uvicorn` ile ayağa kalkar.

Önemli tasarım kararı şudur:

- Tarayıcı doğrudan yalnızca `frontend` servisine gider.
- `frontend`, `/api/*` isteklerini iç ağdaki `backend:8001` servisine proxy eder.

Bunun avantajları:

- Kullanıcı tarafında tek domain kullanılır.
- CORS karmaşıklığı azalır.
- Backend'i internete ayrı bir public servis olarak açmak zorunda kalmazsınız.
- Secret'lar frontend yerine backend tarafında kalır.

## 2. Mimari Diyagramı

```
                        ┌─────────────────────────────────────────────────┐
                        │                 Coolify Sunucusu                │
                        │                                                 │
  İnternet              │   ┌──────────────────┐    ┌─────────────────┐  │
  ──────────────►       │   │                  │    │                 │  │
  https://app.          │   │   frontend       │    │    backend      │  │
  example.com           │   │   (Nginx:80)     │───►│  (uvicorn:8001) │  │
                        │   │                  │    │                 │  │
                        │   │  /            ────┤    │  FastAPI v2.2.0 │  │
                        │   │  /api/*  ────────┘    │                 │  │
                        │   └──────────────────┘    └────────┬────────┘  │
                        │         ▲                          │           │
                        │    Public erişim          Internal ağ only     │
                        │                                      │           │
                        │                    ┌─────────────────┼───────┐  │
                        │                    │                 │       │  │
                        │                    ▼                 ▼       ▼  │
                        │            ┌────────────┐  ┌──────┐ ┌──────┐ │
                        │            │  Supabase   │  │Neo4j │ │Elast-│ │
                        │            │ (PostgreSQL)│  │Aura  │ │icsea-│ │
                        │            └────────────┘  └──────┘ │rch   │ │
                        │              (Harici)      (Harici) └──────┘ │
                        │                                       (Harici) │
                        └─────────────────────────────────────────────────┘

  Ağ yapısı:
  ├── public  → yalnızca frontend servisine açık
  └── internal → backend + frontend arasında; backend dış erişime kapalı
```

Akış özeti:

1. Tarayıcı `https://app.example.com` adresine istek gönderir.
2. Nginx, statik dosya isteklerini React SPA'dan sunar (`/`).
3. API istekleri (`/api/*`) Nginx tarafından `http://backend:8001/api/` adresine proxy edilir.
4. Backend, Supabase (PostgreSQL), Neo4j Aura ve Elasticsearch ile iletişim kurar.
5. Tüm dış servis bağlantıları backend üzerinden yürütülür; frontend doğrudan hiçbir dış servise erişmez.

## 3. Deploy Stratejisi

Coolify tarafında önerilen kurulum:

1. Yeni bir `Docker Compose` application oluşturun.
2. Kaynak olarak bu Git reposunu bağlayın.
3. Compose dosyası olarak `docker-compose.coolify.yaml` seçin.
4. Public erişimi yalnızca `frontend` servisine verin.
5. `backend` servisini Internal bırakın.

Bu yaklaşım, özellikle şu yapılandırma ile uyumludur:

- `frontend/nginx.conf`
  Burada `/api/` çağrıları `http://backend:8001/api/` adresine yönlendirilir.

## 4. Repodaki Deploy Dosyaları Ne İşe Yarıyor

### `docker-compose.coolify.yaml`

Ana orkestrasyon dosyasıdır. İki servisi tanımlar:

- `backend`
  Python image build eder, env alır, health check çalıştırır.
- `frontend`
  React build image oluşturur, Nginx ile yayınlar, backend sağlıklı olmadan ayağa kalkmaz.

### `backend/Dockerfile`

Backend container için:

- `python:3.12-slim` taban image kullanır
- `backend/requirements.txt` kurar
- `uvicorn server:app` ile servisi başlatır
- `/api/health` üstünden health check çalıştırır

### `frontend/Dockerfile`

Frontend container için:

- `node:22-alpine` ile build alır
- `react-scripts build` çalıştırır
- final image olarak `nginx:1.27-alpine` kullanır

### `frontend/nginx.conf`

İki görev yapar:

1. React SPA dosyalarını sunar
2. `/api/*` isteklerini backend'e proxy eder

Bu sayede frontend tarafında runtime sırasında backend URL'si çözme karmaşası minimumda kalır.

### `coolify.env.example`

Coolify içine girilecek environment variable'lar için örnek şablondur. Secret içermez, sadece alan adlarını gösterir.

## 5. Deploy Öncesi Gereksinimler

Deploy'a başlamadan önce elinizde aşağıdakiler bulunmalı:

- Coolify erişimi
- Repo erişimi
- Supabase proje URL'si
- Supabase service role key
- Neo4j Aura bilgileri
- Elasticsearch Cloud ID ve API key

Opsiyonel ama faydalı:

- `EMERGENT_LLM_KEY`
- `SLACK_BOT_TOKEN`
- `GITHUB_TOKEN`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

## 6. Zorunlu Environment Variable'lar

Coolify içine en az şu değerleri girmelisiniz:

- `CORS_ORIGINS`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`
- `ELASTICSEARCH_CLOUD_ID`
- `ELASTICSEARCH_API_KEY`

### Her birinin anlamı

`CORS_ORIGINS`

- Backend'in hangi origin'den gelen credential'lı istekleri kabul edeceğini belirler.
- Örnek:
  `https://app.sirketiniz.com`
- Birden fazla domain varsa virgülle ayırabilirsiniz.
- Örnek:
  `https://app.sirketiniz.com,https://staging.sirketiniz.com`

`SUPABASE_URL`

- Supabase projenizin URL'si
- Örnek:
  `https://xxxxx.supabase.co`

`SUPABASE_SERVICE_KEY`

- Backend'in Supabase tablolarına tam yetkili erişmesi için gereken service role key
- Bu değer gizli tutulmalıdır

`NEO4J_URI`

- Neo4j Aura bağlantı URI'si
- Örnek:
  `neo4j+s://xxxx.databases.neo4j.io`

`NEO4J_USER`

- Genellikle `neo4j`

`NEO4J_PASSWORD`

- Neo4j veritabanı şifresi

`NEO4J_DATABASE`

- Genellikle `neo4j`

`ELASTICSEARCH_CLOUD_ID`

- Elastic Cloud deployment ID

`ELASTICSEARCH_API_KEY`

- Elasticsearch API erişim anahtarı

## 7. Opsiyonel Environment Variable'lar

Şunlar boş bırakılabilir:

- `EMERGENT_LLM_KEY`
- `SLACK_BOT_TOKEN`
- `GITHUB_TOKEN`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

Not:

- `EMERGENT_LLM_KEY` yoksa chat ve document extraction endpoint'leri tamamen çökmez; fallback mesajı döner.
- Slack, GitHub ve Google Drive token'ları yoksa ilgili integration endpoint'leri `connected: false` benzeri yanıtlar verir ama ana sistem ayağa kalkar.

## 8. `REACT_APP_BACKEND_URL` Gerekiyor mu?

Bu projede frontend aynı origin'den servis edildiği ve `/api/*` isteklerini Nginx backend'e proxy ettiği için production ortamında çoğu durumda bu değeri boş bırakabilirsiniz.

Yine de şu durumlarda kullanılabilir:

- Frontend build sırasında sabit bir backend adresi enjekte etmek istiyorsanız
- Proxy yerine doğrudan farklı bir API domain'i hedeflenecekse

Normal Coolify kurulumunda öneri:

- `REACT_APP_BACKEND_URL` boş bırakılabilir
- ya da tamamen tanımlanmayabilir

## 9. Coolify Üzerinde Uygulama Oluşturma

### Adım 1: Yeni uygulama açın

Coolify panelinde:

1. `New Resource`
2. `Application`
3. Git kaynağını seçin
4. Repo'yu bağlayın

### Adım 2: Application türünü seçin

Burada klasik tek container yerine:

- `Docker Compose`

seçin.

### Adım 3: Compose dosyası yolunu girin

Şu dosyayı kullanın:

- `docker-compose.coolify.yaml`

### Adım 4: Branch seçin

Genellikle:

- `main`

veya deploy edeceğiniz release branch.

## 10. Staging vs Production Ortam Ayrımı

En iyi pratik olarak staging ve production için ayrı Coolify application'lar oluşturun. Bu, yanlışlıkla production verisine dokunmayı engeller ve güvenli test akışı sağlar.

### Staging Ortamı

```env
CORS_ORIGINS=https://staging.example.com
SUPABASE_URL=https://staging-project.supabase.co
SUPABASE_SERVICE_KEY=<staging-service-key>
NEO4J_URI=neo4j+s://staging-xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<staging-password>
NEO4J_DATABASE=neo4j
ELASTICSEARCH_CLOUD_ID=<staging-cloud-id>
ELASTICSEARCH_API_KEY=<staging-api-key>
TEST_USER_ID=user_test123456
TEST_EMAIL=test@corteqs.com
TEST_SESSION_TOKEN=test_session_corteqs
```

### Production Ortamı

```env
CORS_ORIGINS=https://app.example.com
SUPABASE_URL=https://prod-project.supabase.co
SUPABASE_SERVICE_KEY=<prod-service-key>
NEO4J_URI=neo4j+s://prod-xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<prod-password>
NEO4J_DATABASE=neo4j
ELASTICSEARCH_CLOUD_ID=<prod-cloud-id>
ELASTICSEARCH_API_KEY=<prod-api-key>
```

### Domain Naming Convention

| Ortam     | Domain                    | Açıklama                              |
|-----------|---------------------------|---------------------------------------|
| Staging   | `staging.example.com`     | Test ve QA erişimi                    |
| Production| `app.example.com`         | Son kullanıcı erişimi                 |

### Temel Farklar

- **Test kullanıcısı**: Staging'de `TEST_*` env'leri aktif, production'da devre dışı bırakılmalı veya güvenli değerlerle değiştirilmeli.
- **Supabase projeleri**: Kesinlikle ayrı projeler kullanın. Aynı proje paylaşımı veri kirliliğine yol açar.
- **Neo4j / Elasticsearch**: Mümkünse ayrı instance'lar kullanın; değilse en azından ayrı database/index prefix'leri ayarlayın.
- **LLM key**: Staging'de test key, production'da üretim key kullanın.

### Coolify'de Ayarlama

1. Staging application: `staging` branch'ini takip etsin, `staging.example.com` domain'ine bağlı olsun.
2. Production application: `main` branch'ini takip etsin, `app.example.com` domain'ine bağlı olsun.
3. Her iki application için ayrı env setleri Coolify'de tanımlı olmalı.

## 11. Coolify Environment Variable Girişi

`coolify.env.example` dosyasını referans alın.

Pratikte Coolify'de şunları tek tek ekleyin:

```env
CORS_ORIGINS=https://app.example.com
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=...
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j
ELASTICSEARCH_CLOUD_ID=...
ELASTICSEARCH_API_KEY=...
EMERGENT_LLM_KEY=
SLACK_BOT_TOKEN=
GITHUB_TOKEN=
GOOGLE_SERVICE_ACCOUNT_JSON=
TEST_USER_ID=user_test123456
TEST_EMAIL=test@corteqs.com
TEST_SESSION_TOKEN=test_session_corteqs
```

Önemli:

- Secret değerleri repo içine yazmayın
- Coolify'nin secret/env alanına girin
- Özellikle `SUPABASE_SERVICE_KEY`, `NEO4J_PASSWORD`, `ELASTICSEARCH_API_KEY` ve varsa `EMERGENT_LLM_KEY` hassastır

## 12. Domain ve SSL Yapılandırması

Önerilen public domain:

- yalnızca `frontend` servisine bağlanmalı

Örnek:

- `app.example.com` → `frontend`

`backend` için ayrıca public domain açmayın, gerçekten gerekmedikçe internal kalsın.

SSL tarafında:

- Coolify standart HTTPS/Let's Encrypt akışını kullanabilir
- SSL aktif olduktan sonra `CORS_ORIGINS` değeriniz de HTTPS domain ile birebir eşleşmeli

Örnek:

- Domain: `https://app.example.com`
- `CORS_ORIGINS=https://app.example.com`

## 13. CI/CD Pipeline Entegrasyonu

### Coolify Native Git Webhook

Coolify, Git reposundan otomatik deploy tetikleyebilir:

1. Coolify → Application → Configuration → `Deploy on Push` aktif edin.
2. Coolify bir webhook URL'si üretir; bu URL'yi GitHub/GitLab repository settings'te webhook olarak ekleyin.
3. Her push'ta Coolify otomatik build ve deploy başlatır.

### Branch Bazlı Auto-Deploy

| Branch   | Hedef Ortam    | Davranış                                  |
|----------|----------------|-------------------------------------------|
| `main`   | Production     | Her merge → otomatik deploy               |
| `staging`| Staging        | Her push → otomatik deploy                |
| `feat/*` | —              | Auto-deploy kapalı, manuel test           |

### GitHub Actions ile Coolify API Entegrasyonu

Coolify API üzerinden deploy tetiklemek için:

```yaml
name: Deploy to Coolify
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Coolify Deploy
        run: |
          curl -X POST "${{ secrets.COOLIFY_WEBHOOK_URL }}" \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"force": true}'
```

### Build Cache Stratejisi

- Coolify Docker layer cache'i otomatik kullanır; ilk build'ten sonraki build'ler daha hızlıdır.
- Backend'de `requirements.txt` değişmediği sürece pip layer cache hit alır.
- Frontend'de `package.json` değişmediği sürece npm install layer cache hit alır.
- Büyük değişikliklerde cache invalidate için Coolify → Application → `Clear Build Cache` kullanın.

### Deploy Notification

- Coolify → Application → Notifications bölümünden Slack webhook veya e-posta bildirimi ayarlayın.
- Deploy başarı/başarısızlık durumlarında otomatik bildirim alabilirsiniz.

## 14. Container Kaynak Limitleri

### Önerilen Kaynak Limitleri

| Servis    | CPU      | RAM   | Açıklama                                        |
|-----------|----------|-------|-------------------------------------------------|
| backend   | 1.0 core | 512MB | FastAPI + Supabase SDK + Neo4j driver + ES client|
| frontend  | 0.25 core| 128MB | Nginx statik dosya sunumu, proxy overhead       |

### Coolify'de Resource Limit Ayarlama

Coolify UI'da her servis için:

1. Application → Service → `Resource Limits` bölümüne gidin.
2. CPU ve Memory limitlerini yukarıdaki tabloya göre girin.

### docker-compose.coolify.yaml'a Deploy Constraints Örneği

Kaynak limitlerini compose dosyasına da ekleyebilirsiniz:

```yaml
services:
  backend:
    # ... mevcut konfigürasyon ...
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.5"
          memory: 256M

  frontend:
    # ... mevcut konfigürasyon ...
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 128M
        reservations:
          cpus: "0.1"
          memory: 64M
```

### Memory Pressure Durumunda Davranış

- Backend memory limit'i aşıldığında container OOM killer tarafından durdurulur ve Coolify otomatik restart dener.
- Backend'in memory kullanımı özellikle LLM isteği ve büyük payload'lar sırasında artar. 512MB yetersiz kalırsa 1GB'a çıkarın.
- Frontend (Nginx) çok düşük kaynak tüketir; 128MB çoğu senaryo için yeterlidir.

## 15. İlk Deploy Sonrası Kontrol Listesi

Deploy tamamlandıktan sonra şu sırayla kontrol edin:

1. Frontend açılıyor mu
2. `GET /api/health` `200` dönüyor mu
3. Login akışı ya da `auth/me` beklenen şekilde davranıyor mu
4. Supabase tabanlı CRUD akışları çalışıyor mu
5. Neo4j bağlantı durumu `connected` görünüyor mu
6. Elasticsearch `connected` görünüyor mu

## 16. Kritik Endpoint Doğrulamaları

Tarayıcı ya da `curl` ile şunları test edin.

### Health

```bash
curl -X GET "https://app.example.com/api/health"
```

Beklenen:

- HTTP `200`
- JSON içinde `status: healthy`

### Neo4j

```bash
curl -X GET "https://app.example.com/api/neo4j/status" \
  -H "Authorization: Bearer test_session_corteqs"
```

Beklenen:

- `connected: true`

### Elasticsearch

```bash
curl -X GET "https://app.example.com/api/elasticsearch/status" \
  -H "Authorization: Bearer test_session_corteqs"
```

Beklenen:

- `connected: true`

## 17. Monitoring ve Alerting

### Coolify Built-in Health Check Dashboard

Coolify, her container için health check durumunu UI'da gösterir:

- `Healthy` → yeşil
- `Unhealthy` → kırmızı
- `Starting` → sarı

Backend health check: `/api/health` endpoint'i 30 saniyede bir sorgulanır (compose dosyasındaki `interval: 30s`).

### Backend `/api/health` Endpoint'inin İzlenmesi

Health endpoint'i şunları döndürür:

- HTTP `200` + `status: healthy` → tüm servisler bağlı
- HTTP `503` veya düşük yanıt → bir veya daha fazla servis bağlantısız

Periyodik izleme için:

```bash
# Basit uptime monitoring
curl -sf "https://app.example.com/api/health" > /dev/null && echo "OK" || echo "DOWN"
```

### Log Aggregation Yaklaşımı

- Coolify UI'da her container'ın log'larını gerçek zamanlı görebilirsiniz.
- Uzun süreli log saklama için Coolify'nin log driver konfigürasyonunu `json-file` ile `max-size` ve `max-file` limitleri ayarlayın.
- Harici log aggregation (Loki, ELK, vb.) kullanıyorsanız Docker log driver olarak ilgili driver'ı yapılandırın.

### Kritik Metrikler

| Metrik                    | Kaynak             | Eşik Önerisi            | Açıklama                          |
|---------------------------|--------------------|--------------------------|------------------------------------|
| Health check durumu       | Coolify UI         | 3 üst üste fail          | Container restart tetiklenir       |
| Response time (`/api/health`)| curl / monitoring | > 5 saniye               | Backend performans sorunu           |
| HTTP 5xx rate             | Nginx log / Coolify| > %5                    | Backend hata oranı                  |
| Container memory          | Coolify metrics    | > %80 limit              | OOM riski                          |
| Container CPU             | Coolify metrics    | Sürekli > %80            | Scale gerekebilir                   |

### Slack/Email Notification Kurulumu (Coolify Native)

1. Coolify → Project → Notifications → `Add Notification`.
2. Tip seçin: Slack webhook veya Email.
3. `Deploy Success`, `Deploy Failed`, `Application Down` event'lerini aktif edin.

### External Monitoring Opsiyyonları

Ücretsiz external monitoring için:

- **UptimeRobot**: `https://app.example.com/api/health` endpoint'ini 5 dakikada bir sorgular.
- **Pingdom**: Benzer uptime monitoring, response time grafikleri.
- **Better Stack (Logtail)**: Log aggregation + uptime monitoring bir arada.

## 18. Test Kullanıcısı ve Seed Mantığı

Projede test user yaklaşımı destekleniyor:

- `TEST_USER_ID`
- `TEST_EMAIL`
- `TEST_SESSION_TOKEN`

Gerekirse deploy sonrası backend container içinde seed script çalıştırabilirsiniz:

- `backend/seed_test_user.py`

Ama üretim ortamında bu kullanıcıyı açık bırakmak istemiyorsanız:

- sadece staging'de kullanın
- production'da bu envleri daha kontrollü yönetin

## 19. Supabase Şema Gereksinimi

Bu backend, belirli Supabase tablolarını bekler. Eğer boş bir projeye deploy ediyorsanız deploy öncesi ya da hemen sonrası şu dosyadaki şemayı Supabase SQL Editor'de çalıştırmalısınız:

- `backend/sql/schema.sql`

Beklenen tablolar:

- `users`
- `user_sessions`
- `data_sources`
- `knowledge_nodes`
- `chat_messages`
- `activities`
- `documents`

Eğer şema yüklenmemişse:

- backend ayağa kalkabilir
- ama auth ve veri endpoint'leri runtime sırasında hata verir

## 20. Neo4j Hakkında Özel Not

Bu projede Neo4j sürücüsü deploy ortamında şu senaryo için güçlendirildi:

- `neo4j+s://` bazı ortamlarda Aura routing/TLS doğrulamasında takılabiliyor

Bu nedenle backend fallback dener:

- önce verdiğiniz URI
- gerekirse `neo4j+ssc://`
- gerekirse `bolt+ssc://`

Bu sayede bazı sertifika/routing farklılıklarında deploy boşa düşmez.

Yine de en doğrusu:

- Aura instance'ın gerçekten aktif olması
- kullanıcı/şifre bilgisinin doğru olması

## 21. Elasticsearch Hakkında Not

Elasticsearch tarafında başarılı bağlantı için tipik gereksinimler:

- doğru `ELASTICSEARCH_CLOUD_ID`
- doğru `ELASTICSEARCH_API_KEY`

Başarılı durumda backend başlangıcında cluster bilgisi log'larda görünür.

Sorun varsa:

- yanlış cloud id
- yanlış API key
- yetki problemi

olasılıklarını kontrol edin.

## 22. LLM / AI Özellikleri Hakkında Not

`EMERGENT_LLM_KEY` girmezseniz:

- deploy yine olur
- temel backend yine çalışır
- chat/document AI özellikleri fallback cevaplar üretebilir

Yani bu anahtar production için işlevsel olarak önemli olabilir ama container build'ini ya da servis start'ını zorunlu olarak bloklamaz.

## 23. Troubleshooting Karar Ağacı

Aşağıdaki karar ağacını izleyerek sorunu hızlıca izole edin:

```
Başlangıç: Sorun nedir?
│
├─► Frontend açılıyor mu?
│   │
│   ├─► HAYIR
│   │   ├── Coolify UI'da frontend container durumu nedir?
│   │   │   ├── Running → Nginx log'larını kontrol edin
│   │   │   ├── Exited → Container log'larında build hatası arayın
│   │   │   └── Unhealthy → Health check log'larını inceleyin
│   │   │
│   │   └── SSL sertifikası geçerli mi?
│   │       └── Coolify → SSL → sertifika durumunu kontrol edin
│   │
│   └─► EVET
│       │
│       ├─► /api/health yanıt veriyor mu?
│       │   │
│       │   ├─► HAYIR
│       │   │   ├── Backend container ayağa kalktı mı?
│       │   │   │   ├── Exited → Backend log'larında import/startup hatası
│       │   │   │   └── Running ama unhealthy → /api/health yanıt kontrolü
│       │   │   │
│       │   │   ├── Backend log'unda "SUPABASE_URL must be set" var mı?
│       │   │   │   └── EVET → SUPABASE_URL ve SUPABASE_SERVICE_KEY env'lerini kontrol edin
│       │   │   │       Bu değerler eksikse backend import aşamasında crash yapar.
│       │   │   │
│       │   │   └── "Application startup complete" log'u var mı?
│       │   │       └── YOK → Lifespan hatası: init_supabase / neo4j / elasticsearch
│       │   │           bağlantılarını sırayla kontrol edin
│       │   │
│       │   └─► EVET
│       │       │
│       │       ├─► HTTP status kodu ne?
│       │       │   ├── 200 → Backend sağlıklı, detaylı inceleme gerekli
│       │       │   ├── 503 → Bağlı servislerden biri down
│       │       │   │   └── Yanıt body'de hangi servis disconnected?
│       │       │   └── 500 → Beklenmeyen hata → Coolify log'larını inceleyin
│       │       │
│       │       └─► Detaylı servis kontrolleri:
│       │           │
│       │           ├─► Supabase bağlantısı var mı?
│       │           │   ├── curl /api/auth/me → 401/403 = bağlantı var, auth sorunu
│       │           │   └── curl /api/auth/me → 500 = bağlantı sorunu
│       │           │       └── SUPABASE_URL / SUPABASE_SERVICE_KEY doğruluğunu kontrol edin
│       │           │       Şema yüklü mü? → backend/sql/schema.sql
│       │           │
│       │           ├─► Neo4j bağlı mı?
│       │           │   └── curl /api/neo4j/status (Bearer token ile)
│       │           │       ├── connected: false → NEO4J_URI, NEO4J_PASSWORD kontrol edin
│       │           │       └── Aura instance aktif mi? → Neo4j console'dan kontrol
│       │           │
│       │           └─► Elasticsearch bağlı mı?
│       │               └── curl /api/elasticsearch/status (Bearer token ile)
│       │                   ├── connected: false → CLOUD_ID, API_KEY kontrol edin
│       │                   └── Elastic Cloud deployment aktif mi?
│       │
│       └─► CORS hatası alıyor musunuz?
│           ├── Browser console'da CORS error?
│           │   └── CORS_ORIGINS değerini kontrol edin:
│           │       - Tam domain eşleşmeli (http vs https farkı)
│           │       - Sonunda slash olmamalı
│           │       - Birden fazla domain varsa virgülle ayrılmalı
│           ├── 401 Unauthorized?
│           │   └── Bölüm 24'e bakın
│           └── 404 Not Found?
│               └── Nginx proxy konfigürasyonunu kontrol edin
│                   frontend/nginx.conf dosyası doğru mount edildi mi?
```

### Hızlı Teşhis Komutları

```bash
# Frontend erişilebilirlik
curl -sf "https://app.example.com/" > /dev/null && echo "Frontend: OK" || echo "Frontend: DOWN"

# Backend health
curl -sf "https://app.example.com/api/health" | python -m json.tool

# Neo4j durum
curl -s "https://app.example.com/api/neo4j/status" -H "Authorization: Bearer $TOKEN"

# Elasticsearch durum
curl -s "https://app.example.com/api/elasticsearch/status" -H "Authorization: Bearer $TOKEN"
```

## 24. Olası Hatalar ve Hızlı Teşhis

> Bu bölüm yaygın hata senaryolarını listeler. Adım adım karar ağacı için Bölüm 23'e bakın.

### Sorun: Frontend açılıyor ama API çalışmıyor

Kontrol edin:

- `frontend/nginx.conf` deploy edildi mi
- `backend` healthy mi
- `frontend` servisi `backend:8001` adresine erişebiliyor mu

### Sorun: `401 Unauthorized`

Kontrol edin:

- Supabase şeması yüklü mü
- `user_sessions` tablosunda test session var mı
- auth cookie / bearer token akışı doğru mu

### Sorun: `500 Internal Server Error`

Kontrol edin:

- Coolify log'ları
- `SUPABASE_SERVICE_KEY` doğru mu
- Neo4j / Elasticsearch envleri doğru mu

### Sorun: CORS hatası

Kontrol edin:

- `CORS_ORIGINS` tam doğru domain mi
- protokol doğru mu (`http` yerine `https`)
- virgülle yazılan origin listesinde boşluk/typo var mı

### Sorun: Backend deploy oluyor ama healthy olmuyor

Kontrol edin:

- `/api/health` yanıt veriyor mu
- container log'larında import hatası var mı
- Supabase envleri eksik mi (`database.py` import zamanında `RuntimeError` fırlatır)

### Sorun: Backend container crash loop

Nedenleri:

- `SUPABASE_URL` veya `SUPABASE_SERVICE_KEY` tanımlı değilse `database.py` import aşamasında `RuntimeError` fırlatır; container hiç start almaz.
- Çözüm: Bu iki env'in Coolify'de tanımlı olduğundan emin olun.

## 25. Backup Stratejisi

### Supabase Otomatik Backup (Native)

- Supabase Pro plan ve üzeri otomatik günlük backup alır.
- Backup'lar 7 gün (Pro) veya 30 gün (Enterprise) saklanır.
- Supabase Dashboard → Database → Backups bölümünden yedekleri görüntüleyin ve geri yükleyin.
- Free plan'da otomatik backup yoktur; manuel SQL dump almanız gerekir.

### Neo4j Aura Backup Prosedürü

- Neo4j Aura otomatik backup alır (cloud-native).
- Geri yükleme için Neo4j Support ile iletişime geçin veya Aura Console'dan restore başlatın.
- Enterprise plan'da self-service backup/restore mevcuttur.

### Elasticsearch Snapshot Yaklaşımı

- Elastic Cloud otomatik snapshot alır (every 30 min, retained 3 days).
- Manuel snapshot için:

```bash
curl -X PUT "https://<cluster>.elastic-cloud.com/_snapshot/my-backup" \
  -H "Authorization: ApiKey <ELASTICSEARCH_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"type": "url", "settings": {"url": "s3://my-bucket/snapshots"}}'
```

### Coolify Volume Backup

- Coolify container'ları stateless olduğundan volume backup gereksizdir.
- Tek kalıcı veri: Coolify konfigürasyonu. Coolify kendi backup mekanizmasını sağlar.

### Environment Variable'ların Yedeklenmesi

- Tüm env variable'ları güvenli bir yerde (şifreli password manager, vs.) saklanmalıdır.
- Coolify env export özelliğini kullanarak periyodik olarak env setini dışa aktarın.

### Disaster Recovery: RTO/RPO Hedefleri

| Servis          | RPO              | RTO              | Backup Yöntemi         |
|-----------------|------------------|------------------|------------------------|
| Supabase        | 24 saat          | ~1 saat          | Supabase native backup |
| Neo4j Aura      | ~1 saat          | ~2 saat          | Aura native backup     |
| Elasticsearch   | 30 dakika        | ~1 saat          | Elastic Cloud snapshot |
| Coolify Config  | Manuel           | ~30 dakika       | Env export + repo      |
| Frontend (statik)| 0 (repo'dan rebuild) | ~10 dakika  | Git repo               |

## 26. Scaling ve Performans

### Horizontal Scaling Stratejisi (Backend Replicas)

Backend stateless olduğundan horizontal scaling mümkündür:

```yaml
services:
  backend:
    # ... mevcut konfigürasyon ...
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
```

Coolify UI'dan da replica sayısını artırabilirsiniz: Service → Scale.

### Nginx Rate Limiting Konfigürasyonu

Production'da abuse önlemek için `frontend/nginx.conf`'a rate limiting ekleyin:

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

    server {
        location /api/ {
            limit_req zone=api burst=10 nodelay;
            proxy_pass http://backend:8001/api/;
            # ... mevcut proxy_set_header direktifleri ...
        }
    }
}
```

### Connection Pooling

| Servis         | Strateji                                       |
|----------------|-------------------------------------------------|
| Supabase       | AsyncClient zaten connection pool kullanır      |
| Neo4j          | Driver built-in connection pool; `max_connection_pool_size` ayarlanabilir |
| Elasticsearch  | Async client connection pool kullanır            |

### Static Asset Caching (Nginx)

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### Coolify Load Balancer Entegrasyonu

- Coolify, birden fazla container'ı otomatik load balance eder.
- Backend replica sayısı > 1 ise Coolify dahili load balancer'ı kullanır.

### Replicas ile Session Affinity Konusu

- Backend stateless tasarlandığından session affinity gerekmez.
- Auth state Supabase `user_sessions` tablosunda tutulur; herhangi bir backend replica isteği işleyebilir.

## 27. Coolify Log'larda Neye Bakılmalı

Deploy sonrası log incelemesinde şu sinyaller önemli:

- FastAPI startup tamamlandı mı
- Supabase init hata veriyor mu
- Neo4j bağlandı mı
- Elasticsearch bağlandı mı
- `frontend` Nginx doğru ayağa kalktı mı

İyi log örnekleri:

- `Application startup complete`
- `Neo4j connected successfully`
- `Elasticsearch connected`

## 28. Güncelleme Süreci

Yeni release deploy ederken önerilen sıra:

1. Önce local regression test
2. Ardından git push
3. Coolify auto-deploy ya da manual deploy
4. Deploy sonrası `/api/health`
5. Kritik auth/CRUD testleri

Bu projede backend regression testi daha önce doğrulanmıştır; deploy öncesi aynı yaklaşımı korumak iyi olur.

### Detaylı Güncelleme Akışı

1. **Staging'de test edin**: Değişiklikleri `staging` branch'ine push edin, staging ortamında doğrulayın.
2. **Production merge**: Staging doğrulandıktan sonra `main` branch'ine merge edin.
3. **Deploy sonrası health check**: `/api/health` endpoint'ini kontrol edin.
4. **Smoke test**: Kritik kullanıcı akışlarını (login, CRUD, search) doğrulayın.

## 29. Rollback Yaklaşımı

Deploy sonrası kritik hata varsa:

1. Son çalışan commit'i belirleyin
2. Coolify'de önceki sürüme dönün ya da eski commit'i yeniden deploy edin
3. Env değişikliği yapıldıysa en son çalışan env setini geri yükleyin

Özellikle şu tip değişikliklerde rollback hızlı düşünülmelidir:

- Supabase schema değişimi
- auth akışı
- nginx proxy değişikliği
- CORS değişikliği

### Rollback Senaryoları

| Senaryo                       | Rollback Yöntemi                                     |
|-------------------------------|------------------------------------------------------|
| Kod hatası (son deploy)       | Coolify → Previous Deploy → Redeploy                |
| Env değişikliği hatası        | Coolify env alanından önceki değerleri geri yükle    |
| Schema migration hatası       | Supabase → SQL Editor → rollback migration çalıştır  |
| SSL sertifika sorunu          | Coolify → SSL → force renew                          |

## 30. Güvenlik Hardening

### `CORS_ORIGINS = *` Yasağı

- Production'da `CORS_ORIGINS` asla `*` olmamalıdır.
- Yalnızca frontend domain'ini belirtin: `https://app.example.com`
- Wildcard kullanımı credential saldırı vektörü açar.

### Secret Yönetimi En İyi Pratikler

- Tüm secret'lar Coolify env alanında tutulmalı; repo içine asla commitlenmemeli.
- `.env` dosyaları `.gitignore`'da olmalı.
- Secret rotation: `SUPABASE_SERVICE_KEY`, `NEO4J_PASSWORD`, `ELASTICSEARCH_API_KEY` periyodik olarak döndürülmeli.
- Her ortam (staging/production) için ayrı secret setleri kullanın.

### Nginx Security Headers

`frontend/nginx.conf`'a şu header'ları ekleyin:

```nginx
server {
    # ... mevcut konfigürasyon ...

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

    # HSTS (HTTPS zorunlu ise)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### Backend Rate Limiting

FastAPI tarafında rate limiting için `slowapi` veya benzeri middleware kullanın:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

### Docker Image Security Scanning

- Backend image'ını düzenli olarak tarayın:

```bash
docker scout cves corteqs-backend:latest
# veya
trivy image corteqs-backend:latest
```

- Base image'leri güncel tutun: `python:3.12-slim`, `nginx:1.27-alpine`.
- Dependabot veya Renovate ile dependency vulnerability takibi yapın.

### Coolify Network Isolation

- Backend servisine dış erişim vermeyin; yalnızca internal ağda iletişim kurmalı.
- Coolify'de `backend` servisinin `expose` port'ları public değil, internal olmalı.
- Mevcut compose dosyası zaten `expose` (port publish değil) kullanır; bu doğrudur.

### Supabase RLS Kuralları

- Backend service role key kullandığından RLS kuralları bypass edilir.
- Frontend'den doğrudan Supabase erişimi varsa (anon key), RLS kuralları mutlaka tanımlanmalı.
- `users`, `user_sessions`, `data_sources`, `knowledge_nodes`, `chat_messages`, `activities`, `documents` tabloları için RLS policy'leri Supabase Dashboard'dan yapılandırın.

### SSL/TLS Sertifika Yenileme Otomasyonu

- Coolify, Let's Encrypt sertifikalarını otomatik olarak yeniler.
- Sertifika süresi yaklaştığında Coolify notification gönderir.
- Manuel müdahale gerekmez; ancak Coolify'nin 80/443 port erişiminin açık olduğundan emin olun.

## 31. Production İçin Ek Tavsiyeler

- `CORS_ORIGINS` değerini asla `*` bırakmayın
- `SUPABASE_SERVICE_KEY` yalnızca backend'de kalsın
- frontend'e secret env taşımayın
- production ve staging için ayrı env setleri kullanın
- mümkünse staging domain'i ile önce dry-run deploy yapın
- backend version `2.2.0` — sağlık kontrolü yanıtında bu versiyon görünebilir

## 32. Önerilen Minimum Deploy Konfigürasyonu

Eğer yalnızca sistemi ayağa kaldırmak istiyorsanız minimum çalışan set şu olur:

```env
CORS_ORIGINS=https://app.example.com
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=...
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j
ELASTICSEARCH_CLOUD_ID=...
ELASTICSEARCH_API_KEY=...
```

Bunun üstüne ihtiyaç oldukça şu entegrasyonları eklersiniz:

- Slack
- GitHub
- Google Drive
- LLM

## 33. Sonuç

Bu repo artık Coolify üzerinde iki servisli compose yapısı ile deploy edilmeye hazır durumdadır. Temel yaklaşım şudur:

- public trafik `frontend`'e gelir
- `frontend`, `/api` çağrılarını internal `backend`'e yollar
- backend Supabase, Neo4j ve Elasticsearch ile konuşur

Deploy sırasında en kritik üç alan:

1. doğru env girişi
2. doğru domain/CORS eşleşmesi
3. Supabase şemasının hazır olması

Kısa özetle:

- Compose dosyası hazır
- Dockerfile'lar hazır
- proxy hazır
- env şablonu hazır
- deploy sonrası kontrol noktaları tanımlı

## 34. Hızlı Referans Kartı

### Tüm Endpoint'ler

| Endpoint                    | Method | Auth  | Açıklama                     |
|-----------------------------|--------|-------|------------------------------|
| `/api/health`               | GET    | Hayır| Sistem sağlık kontrolü       |
| `/api/auth/me`              | GET    | Evet | Mevcut kullanıcı bilgisi     |
| `/api/neo4j/status`         | GET    | Evet | Neo4j bağlantı durumu        |
| `/api/elasticsearch/status` | GET    | Evet | Elasticsearch bağlantı durumu|
| `/api/data-sources`         | GET    | Evet | Veri kaynakları listesi      |
| `/api/knowledge`            | GET    | Evet | Knowledge node'ları          |
| `/api/chat`                 | POST   | Evet | Chat mesajı gönderme         |
| `/api/search`               | GET    | Evet | Arama                        |
| `/api/analytics`            | GET    | Evet | Analitik verileri            |
| `/api/integrations`         | GET    | Evet | Entegrasyon durumları        |
| `/api/graph`                | GET    | Evet | Graf verileri                |
| `/api/documents`            | GET    | Evet | Belge listesi                |

### Environment Variable Özet Tablosu

| Variable                       | Zorunlu | Varsayılan               | Açıklama                            |
|--------------------------------|---------|--------------------------|--------------------------------------|
| `CORS_ORIGINS`                 | Evet    | —                        | İzin verilen origin'ler (virgülle)  |
| `SUPABASE_URL`                 | Evet    | —                        | Supabase proje URL'si               |
| `SUPABASE_SERVICE_KEY`         | Evet    | —                        | Service role key (gizli)            |
| `NEO4J_URI`                    | Evet    | —                        | Neo4j Aura URI                      |
| `NEO4J_USER`                   | Hayır   | `neo4j`                  | Neo4j kullanıcı adı                 |
| `NEO4J_PASSWORD`               | Evet    | —                        | Neo4j şifre (gizli)                 |
| `NEO4J_DATABASE`               | Hayır   | `neo4j`                  | Neo4j veritabanı adı                |
| `ELASTICSEARCH_CLOUD_ID`       | Evet    | —                        | Elastic Cloud deployment ID         |
| `ELASTICSEARCH_API_KEY`        | Evet    | —                        | Elasticsearch API key (gizli)       |
| `EMERGENT_LLM_KEY`             | Hayır   | —                        | LLM API key                         |
| `SLACK_BOT_TOKEN`              | Hayır   | —                        | Slack integration token             |
| `GITHUB_TOKEN`                 | Hayır   | —                        | GitHub integration token            |
| `GOOGLE_SERVICE_ACCOUNT_JSON`  | Hayır   | —                        | Google Drive service account        |
| `REACT_APP_BACKEND_URL`        | Hayır   | —                        | Frontend build-time backend URL     |
| `PORT`                         | Hayır   | `8001`                   | Backend dinleme portu               |
| `TEST_USER_ID`                 | Hayır   | `user_test123456`        | Test kullanıcı ID'si                |
| `TEST_EMAIL`                   | Hayır   | `test@corteqs.com`       | Test kullanıcı e-posta              |
| `TEST_SESSION_TOKEN`           | Hayır   | `test_session_corteqs`   | Test session token                  |

### Sık Kullanılan Komutlar

```bash
# Frontend erişim testi
curl -sf "https://app.example.com/" > /dev/null && echo "Frontend: OK" || echo "Frontend: DOWN"

# Backend health check
curl -sf "https://app.example.com/api/health" && echo "" || echo "Backend: DOWN"

# Detaylı health yanıtı
curl -s "https://app.example.com/api/health" | python -m json.tool

# Container log'larını izleme (Coolify sunucusunda)
docker logs -f <container-id> --tail 100

# Seed test user (staging)
docker exec <backend-container> python seed_test_user.py

# Supabase şema yükleme (local)
# → Supabase Dashboard → SQL Editor → backend/sql/schema.sql içeriğini yapıştır
```

### Log Okuma Hızlı Rehber

| Log Mesajı                          | Anlamı                              | Aksiyon                        |
|--------------------------------------|--------------------------------------|--------------------------------|
| `Application startup complete`       | Backend başarıyla start aldı          | —                              |
| `SUPABASE_URL must be set`           | Supabase env'leri eksik              | Env'leri kontrol edin          |
| `Neo4j connected successfully`       | Neo4j bağlantısı başarılı           | —                              |
| `Elasticsearch connected`            | ES bağlantısı başarılı              | —                              |
| `RuntimeError` (import zamanında)    | Kritik env eksik, container crash   | İlgili env'yi ekleyin          |
| `502 Bad Gateway`                    | Backend ayağa kalkmadı veya crash   | Backend log'larını kontrol edin|
| `Connection refused` (proxy log)     | Backend servisine erişilemiyor      | Backend health check yapın     |
