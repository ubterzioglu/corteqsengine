# CorteQS Coolify Deploy Rehberi

Bu doküman, `CorteQS Intelligence Engine` projesini Coolify üzerinde üretim benzeri şekilde ayağa kaldırmak için hazırlanmıştır. Amaç yalnızca "deploy olsun" değil, aynı zamanda hangi servisin neden öyle konumlandığını, hangi environment variable'ın ne işe yaradığını, ilk açılışta neyin kontrol edilmesi gerektiğini ve olası hatalarda nereye bakılacağını netleştirmektir.

Bu rehber, repoda bulunan şu dosyalara dayanır:

- `docker-compose.coolify.yml`
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

## 2. Deploy Stratejisi

Coolify tarafında önerilen kurulum:

1. Yeni bir `Docker Compose` application oluşturun.
2. Kaynak olarak bu Git reposunu bağlayın.
3. Compose dosyası olarak `docker-compose.coolify.yml` seçin.
4. Public erişimi yalnızca `frontend` servisine verin.
5. `backend` servisini internal bırakın.

Bu yaklaşım, özellikle şu yapılandırma ile uyumludur:

- `frontend/nginx.conf`
  Burada `/api/` çağrıları `http://backend:8001/api/` adresine yönlendirilir.

## 3. Repodaki Deploy Dosyaları Ne İşe Yarıyor

### `docker-compose.coolify.yml`

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
- final image olarak `nginx:alpine` kullanır

### `frontend/nginx.conf`

İki görev yapar:

1. React SPA dosyalarını sunar
2. `/api/*` isteklerini backend'e proxy eder

Bu sayede frontend tarafında runtime sırasında backend URL'si çözme karmaşası minimumda kalır.

### `coolify.env.example`

Coolify içine girilecek environment variable'lar için örnek şablondur. Secret içermez, sadece alan adlarını gösterir.

## 4. Deploy Öncesi Gereksinimler

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

## 5. Zorunlu Environment Variable'lar

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

## 6. Opsiyonel Environment Variable'lar

Şunlar boş bırakılabilir:

- `EMERGENT_LLM_KEY`
- `SLACK_BOT_TOKEN`
- `GITHUB_TOKEN`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

Not:

- `EMERGENT_LLM_KEY` yoksa chat ve document extraction endpoint'leri tamamen çökmez; fallback mesajı döner.
- Slack, GitHub ve Google Drive token'ları yoksa ilgili integration endpoint'leri `connected: false` benzeri yanıtlar verir ama ana sistem ayağa kalkar.

## 7. `REACT_APP_BACKEND_URL` Gerekiyor mu?

Bu projede frontend aynı origin'den servis edildiği ve `/api/*` isteklerini Nginx backend'e proxy ettiği için production ortamında çoğu durumda bu değeri boş bırakabilirsiniz.

Yine de şu durumlarda kullanılabilir:

- Frontend build sırasında sabit bir backend adresi enjekte etmek istiyorsanız
- Proxy yerine doğrudan farklı bir API domain'i hedeflenecekse

Normal Coolify kurulumunda öneri:

- `REACT_APP_BACKEND_URL` boş bırakılabilir
- ya da tamamen tanımlanmayabilir

## 8. Coolify Üzerinde Uygulama Oluşturma

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

- `docker-compose.coolify.yml`

### Adım 4: Branch seçin

Genellikle:

- `main`

veya deploy edeceğiniz release branch.

## 9. Coolify Environment Variable Girişi

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

## 10. Domain ve SSL Yapılandırması

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

## 11. İlk Deploy Sonrası Kontrol Listesi

Deploy tamamlandıktan sonra şu sırayla kontrol edin:

1. Frontend açılıyor mu
2. `GET /api/health` `200` dönüyor mu
3. Login akışı ya da `auth/me` beklenen şekilde davranıyor mu
4. Supabase tabanlı CRUD akışları çalışıyor mu
5. Neo4j bağlantı durumu `connected` görünüyor mu
6. Elasticsearch `connected` görünüyor mu

## 12. Kritik Endpoint Doğrulamaları

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

## 13. Test Kullanıcısı ve Seed Mantığı

Projede test user yaklaşımı destekleniyor:

- `TEST_USER_ID`
- `TEST_EMAIL`
- `TEST_SESSION_TOKEN`

Gerekirse deploy sonrası backend container içinde seed script çalıştırabilirsiniz:

- `backend/seed_test_user.py`

Ama üretim ortamında bu kullanıcıyı açık bırakmak istemiyorsanız:

- sadece staging'de kullanın
- production'da bu envleri daha kontrollü yönetin

## 14. Supabase Şema Gereksinimi

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

## 15. Neo4j Hakkında Özel Not

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

## 16. Elasticsearch Hakkında Not

Elasticsearch tarafında başarılı bağlantı için tipik gereksinimler:

- doğru `ELASTICSEARCH_CLOUD_ID`
- doğru `ELASTICSEARCH_API_KEY`

Başarılı durumda backend başlangıcında cluster bilgisi log'larda görünür.

Sorun varsa:

- yanlış cloud id
- yanlış API key
- yetki problemi

olasılıklarını kontrol edin.

## 17. LLM / AI Özellikleri Hakkında Not

`EMERGENT_LLM_KEY` girmezseniz:

- deploy yine olur
- temel backend yine çalışır
- chat/document AI özellikleri fallback cevaplar üretebilir

Yani bu anahtar production için işlevsel olarak önemli olabilir ama container build'ini ya da servis start'ını zorunlu olarak bloklamaz.

## 18. Olası Hatalar ve Hızlı Teşhis

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
- Supabase envleri eksik mi

## 19. Coolify Log'larda Neye Bakılmalı

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

## 20. Güncelleme Süreci

Yeni release deploy ederken önerilen sıra:

1. Önce local regression test
2. Ardından git push
3. Coolify auto-deploy ya da manual deploy
4. Deploy sonrası `/api/health`
5. Kritik auth/CRUD testleri

Bu projede backend regression testi daha önce doğrulanmıştır; deploy öncesi aynı yaklaşımı korumak iyi olur.

## 21. Rollback Yaklaşımı

Deploy sonrası kritik hata varsa:

1. Son çalışan commit'i belirleyin
2. Coolify'de önceki sürüme dönün ya da eski commit'i yeniden deploy edin
3. Env değişikliği yapıldıysa en son çalışan env setini geri yükleyin

Özellikle şu tip değişikliklerde rollback hızlı düşünülmelidir:

- Supabase schema değişimi
- auth akışı
- nginx proxy değişikliği
- CORS değişikliği

## 22. Production İçin Ek Tavsiyeler

- `CORS_ORIGINS` değerini asla `*` bırakmayın
- `SUPABASE_SERVICE_KEY` yalnızca backend'de kalsın
- frontend'e secret env taşımayın
- production ve staging için ayrı env setleri kullanın
- mümkünse staging domain'i ile önce dry-run deploy yapın

## 23. Önerilen Minimum Deploy Konfigürasyonu

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

## 24. Sonuç

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

İstersen bir sonraki adımda bu rehberi daha da pratik hale getirip:

1. sadece production için kısaltılmış bir "hızlı kurulum" bölümü,
2. staging için ayrı bir örnek env seti,
3. Coolify ekran görüntüsü mantığında adım adım checklist

da ekleyebilirim.
