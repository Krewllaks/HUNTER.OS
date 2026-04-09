# HUNTER.OS (ARES Engine v0.1) - Proje Bilgi Dokumani

> Son Guncelleme: 3 Nisan 2026
> Durum: Phase 1-10 Tamamlandi (Auth + Onboarding + Discovery + AI Agents + Email/LinkedIn + Sentiment + i18n + Deployment + Enterprise Hardening + Digital Footprint & Enrichment)

---

## 1. Proje Nedir?

HUNTER.OS, sirketler icin gelistirilen **tam otonom bir AI satis avcisi**dir. Kullanici urununu anlattigi anda sistem:

1. Urunu analiz eder ve Ideal Musteri Profili (ICP) cikarir
2. Potansiyel musterileri internetten **kendisi bulur** (Google, LinkedIn)
3. Buldugu kisilerin paylasimlari, blog yazilari ve dijital ayak izlerini analiz eder
4. Kisisellesmis mesajlar uretir (robot oldugu anlasilmayacak kalitede)
5. Coklu kanal uzerinden (Email + LinkedIn) otomatik ulasim gerceklestirir
6. Cevap geldiginde otomasyonu aninda durdurur

**Hedef Kitle:** 5-30 kisilik pazarlama ajanslari
**Fiyatlama Hedefi:** $49/ay
**Slogan:** "Hic uyumayan, maas istemeyen ve her saniye kisiye ozel satis yapan dijital avci."

---

## 2. Vizyon ve Felsefe

### 2.1 Temel Problem

- Bir satis temsilcisi (SDR) tek bir potansiyel musteri icin 15-20 dakika harcayor
- Genel/kopya-yapistir mesajlar spam filtresine takiliyor veya ciddiye alinmiyor
- Haberler, is ilanlari ve LinkedIn verileri farkli yerlerde dagitik duruyor

### 2.2 Cozum Yaklasimi

Sistem sadece "filtrele ve mesaj at" degil:
- **Kim olduklarini** degil, **su an neye ihtiyac duyduklarini** (satin alma sinyallerini) takip ediyor
- Teknoloji kullanimi, is ilanlari, web sitesi guncellemeleri ve sosyal medya etkilesimleri uzerinden **dogru zamaningi** yakaliyor
- Karsi tarafin karakterine ve dijital ayak izine (hobi, uslup, gorusler) burunerek mesajlar uretiyor

### 2.3 "Project Inception" Pazarlama Stratejisi

Urun, kendisiyle pazarlanacak (dogfooding). Ornek mail:

> "Bu maili size ben degil, kendi gelistirdigim bir AI Sales Hunter yazdi. Sizin [konu] hakkindaki fikrinizi LinkedIn'de buldu, analiz etti ve bu mesaji olusturup bana gonderdi. Eger bu mail dikkatinizi cekmeyi basardiysa, sistemimiz gorevini yapmis demektir."

**"Mat" Hamlesi:** "Eger robot oldugumu anlamadiyosaniz, musterileriniz de anlamayacak demektir."

---

## 3. Teknik Mimari

### 3.1 Teknoloji Yigini

| Katman | Teknoloji | Gorevi |
|--------|-----------|--------|
| Backend Framework | FastAPI (Python 3.12) | REST API, asenkron is akisi |
| LLM Engine | Google Gemini 1.5 Flash | Arastirma, puanlama, mesaj uretimi |
| Database | SQLite + SQLAlchemy 2.0 | Lead, kampanya, mesaj verilerinin depolanmasi |
| Task Scheduler | APScheduler | Zamanlanan isler (workflow, warmup, reset) |
| Web Scraping | Playwright (Chromium) + Stealth Mode | Gercek zamanli veri toplama |
| Frontend | Next.js 15 + React 19 + TypeScript | Kullanici arayuzu |
| UI Framework | Tailwind CSS 3.4 | Swiss-Minimalist tasarim sistemi |
| Charts | Recharts | Analitik grafikleri |
| Icons | Lucide React | Ikon seti |
| Auth | JWT (HS256) + bcrypt | Kimlik dogrulama |
| HTTP Client | httpx | Asenkron HTTP istekleri |

### 3.2 Klasor Yapisi

```
aipoweredsaleshunter/
  CLAUDE.md                      # Proje ruhu + kodlama standartlari
  hunterbilgi.md                 # Bu dosya - kapsamli proje dokumantasyonu
  docker-compose.yml             # Production Docker setup
  docker-compose.dev.yml         # Development Docker setup
  .github/workflows/ci.yml      # GitHub Actions CI pipeline

  backend/
    app/
      main.py                    # FastAPI giris noktasi, 5 scheduled job
      tasks.py                   # Celery async task tanimlari
      core/
        config.py                # Ayarlar (Pydantic BaseSettings)
        database.py              # SQLAlchemy engine + session (WAL mode)
        security.py              # JWT + bcrypt + get_current_user
        celery_app.py            # Celery + Redis yapilandirmasi
      models/
        user.py                  # Kullanici (plan, trial, subscription, usage)
        lead.py                  # Lead + BuyingCommittee + TimingPattern + ObjectionLog + profile_cache
        lead_product.py          # Junction table (lead <-> product, many-to-many)
        campaign.py              # Campaign + Workflow + CampaignAnalytics
        product.py               # Urun modeli (ICP, search strategies)
        account.py               # EmailAccount + LinkedInAccount + Blacklist
        message.py               # Message + Notification (tracking_id, sender_email)
      schemas/
        auth.py                  # Register, Login, Token schemalar
        lead.py                  # Lead CRUD + Hunt schemalar
        campaign.py              # Campaign + Workflow schemalar
        product.py               # Product CRUD schemalar
        account.py               # Account + Blacklist schemalar
        message.py               # Message + Inbox schemalar
        footprint.py             # Footprint scan + dossier schemalar
      api/v1/
        auth.py                  # /auth/register, /auth/login, /auth/me
        leads.py                 # /leads CRUD + committee
        hunt.py                  # /hunt/start + /hunt/stream/{id} (SSE)
        campaigns.py             # /campaigns CRUD + activate/pause/enqueue
        products.py              # /products CRUD + analyze + start-hunting
        messages.py              # /messages generate, approve, batch, drafts
        inbox.py                 # /inbox/unified, thread, compose, notifications
        accounts.py              # /accounts/health, email, linkedin, blacklist
        analytics.py             # /analytics/dashboard, autopsy, scoring
        billing.py               # /billing/usage, plans, checkout, webhook
        tracking.py              # /tracking/open (pixel), /tracking/click (redirect)
        footprint.py             # /footprint scan, bulk-scan, dossier, enrich
      agents/
        base_agent.py            # Abstract base class (async Gemini wrapper, retry + fallback)
        product_agent.py         # Urun analizi -> ICP cikarimi (429 fallback destekli)
        research_agent.py        # Web arastirma (7 sinyal, Step-Back Prompting)
        scoring_agent.py         # CoT puanlama (4 boyut)
        personalization_agent.py # 6 katmanli hiper-kisisellestirme mesaj uretimi
        content_analyst_agent.py # Dijital ayak izi analizi (posts, social, website)
      services/
        hunt_service.py          # Arastirma pipeline orkestrasyonu
        discovery_service.py     # Otonom musteri kesfetme (profile_cache + dedup)
        workflow_engine.py       # Kampanya workflow motoru (email + LinkedIn aksiyonlari)
        email_service.py         # SMTP gonderim + tracking pixel injection
        linkedin_service.py      # LinkedIn otomasyon (visit, connect, DM)
        linkedin_guard.py        # Anti-ban: limitler, warmup, fatigue, risk detection
        imap_service.py          # IMAP polling ile gelen mesaj tespiti
        sentiment_service.py     # Gemini-powered cevap duygu analizi
        plan_limiter.py          # Trial/Pro/Enterprise usage gating (HTTP 402)
        warmup_service.py        # Email + LinkedIn hesap isitma
        ab_testing.py            # A/B test motoru (variant assignment, winner)
        bridge_service.py        # Telegram/WhatsApp bildirim koprusu
        footprint_scanner.py     # Sherlock-style 121 platform tarama (async)
        enrichment_pipeline.py   # 4 adimli zenginlestirme orkestrasyonu
        lead_enrichment_api.py   # Harici API'ler (Hunter.io, Snov.io, FullContact, RocketReach, BuiltWith)
        event_bus.py             # Redis/in-memory SSE event bus
      data/
        sites.json               # 121 platform veritabani (Sherlock-style, URL pattern + detection type)
      scraping/
        stealth_browser.py       # Anti-detection Playwright browser
        linkedin_scraper.py      # LinkedIn profil/sirket scraping
        website_scraper.py       # Technographics + haber scraping
    alembic/
      env.py                     # Migration environment
      versions/                  # Schema migration dosyalari
    tests/
      conftest.py                # Pytest fixtures, in-memory SQLite + StaticPool
      test_auth.py               # Auth endpoint testleri
      test_auth_comprehensive.py # Kapsamli auth coverage
      test_products.py           # Product + ICP testleri
      test_leads.py              # Lead discovery + scoring testleri
      test_campaigns.py          # Campaign execution testleri
      test_billing.py            # Plan limit + usage testleri
      test_footprint_scanner.py  # Username extraction, scoring testleri
      test_enrichment_pipeline.py # Pipeline orchestration testleri
      test_health_endpoint.py    # Health check (DB + Redis) testleri
      test_hunt_service.py       # Hunt service testleri
      test_plan_limiter.py       # Plan limit testleri
      test_security.py           # Password hashing + JWT testleri
    requirements.txt             # Python bagimliliklari
    .env                         # Ortam degiskenleri
    hunter.db                    # SQLite veritabani (dev)

  frontend/
    src/
      app/
        layout.tsx               # Root layout (AuthProvider + AppShell)
        page.tsx                 # Dashboard (real API, i18n destekli)
        globals.css              # Swiss-Minimalist stilleri
        login/page.tsx           # Giris sayfasi
        register/page.tsx        # Kayit sayfasi
        onboarding/page.tsx      # Urun tanimlama wizard
        hunt/page.tsx            # Av baslat
        leads/page.tsx           # Lead yonetimi (real API)
        campaigns/page.tsx       # Kampanya yonetimi (real API)
        inbox/page.tsx           # Birlesmis gelen kutusu
        accounts/page.tsx        # Hesap yonetimi
        analytics/page.tsx       # Analitik
        settings/page.tsx        # Kullanici ayarlari + dil secimi
        pricing/page.tsx         # Plan karsilastirma (Trial/Pro/Enterprise)
        leads/[id]/footprint/page.tsx  # Digital Dossier sayfasi (scan + enrich)
      components/
        Sidebar.tsx              # Sol navigasyon + dil toggle + pricing link
        AppShell.tsx             # Auth korumali layout wrapper
        MessagePreviewModal.tsx  # Mesaj onizleme + onay + edit
        UpgradeModal.tsx         # Plan yukseltme + FOMO hook
      context/
        AuthContext.tsx           # Auth state yonetimi
      hooks/
        useI18n.ts               # i18n hook (TR/EN, localStorage persist)
        useHuntStream.ts         # SSE real-time hunt progress hook
      lib/
        api.ts                   # API client (auth, leads, products, messages, billing, campaigns, footprint, enrich)
        i18n.ts                  # Ceviri sistemi (~80 key, TR/EN)
    package.json
    tailwind.config.ts
    tsconfig.json
    next.config.ts
```

---

## 4. Veritabani Modelleri (13 Tablo)

### 4.1 User (Kullanicilar)
| Alan | Tip | Aciklama |
|------|-----|----------|
| id | Integer PK | |
| email | String(255), unique | |
| hashed_password | String(255) | bcrypt hash |
| full_name | String(255) | |
| role | String(50) | admin / manager / member |
| plan | String(50) | trial / pro / enterprise |
| trial_started_at | DateTime | Trial baslangic |
| trial_ends_at | DateTime | Trial bitis (14 gun) |
| subscription_id | String(255) | LemonSqueezy subscription ID |
| usage_this_month | JSON | {"leads": 5, "messages": 3} |
| usage_reset_at | DateTime | Ayin 1'inde sifirlanir |
| is_active | Boolean | |
| created_at, updated_at | DateTime | |

### 4.2 Product (Urunler) - YENl
| Alan | Tip | Aciklama |
|------|-----|----------|
| id | Integer PK | |
| user_id | FK -> users | |
| name | String(255) | Urun adi |
| description_prompt | Text | Kullanicinin yazdigi urun aciklamasi |
| ai_analysis | JSON | AI'nin cikardigi deger onerisi, hedef pazar |
| icp_profile | JSON | Ideal Musteri Profili (sektorler, unvanlar, sorunlar) |
| search_queries | JSON | AI'nin olusturdugu arama stratejileri |
| target_industries | JSON | ["SaaS", "E-commerce", ...] |
| target_titles | JSON | ["CEO", "CTO", "VP Marketing", ...] |
| target_company_sizes | JSON | ["1-10", "11-50", ...] |
| status | String(50) | draft / analyzing / ready / hunting / active |

### 4.3 Lead (Potansiyel Musteriler)
| Alan Grubu | Alanlar | Aciklama |
|-----------|---------|----------|
| Kimlik | first_name, last_name, email, linkedin_url, phone, photo_url | Kisi bilgileri |
| Sirket | company_name, company_domain, company_size, industry, company_location | Sirket bilgileri |
| Istihbarat Sinyalleri | last_4_posts, technographics, recent_news, hiring_signals, website_changes, social_engagement, content_intent | Tumu JSON - AI'nin topladigi sinyaller |
| Kisisellestirme | communication_style, hobbies, common_ground, media_quotes, review_highlights | Mesaj uretimi icin kullanilan veriler |
| Puanlama | intent_score (0-100), confidence (0-100), icp_match_score (0-100) | AI puanlama sonuclari |
| Dijital Ayak Izi | social_profiles (JSON), digital_footprint_score (0-100), footprint_scanned_at | Sherlock scan sonuclari |
| Durum | status, sentiment, objection_type, is_blacklisted, do_not_contact | Lead durumu |
| Soft Delete | is_deleted (indexed), deleted_at | Geri alinabilir silme |
| Meta | source, campaign_id, tags, notes, created_at, updated_at | Kaynak ve etiketler |
| Composite Indexes | (user_id, status), (user_id, created_at), (user_id, intent_score) | Performans |

### 4.3b LeadProduct (Lead-Urun Iliskisi - Junction Table)
| Alan | Tip | Aciklama |
|------|-----|----------|
| id | Integer PK | |
| lead_id | FK -> leads | |
| product_id | FK -> products | |
| status | String(50) | matched / contacted / rejected / won |
| fit_score | Integer | Urun-lead uyum puani (0-100) |
| outreach_count | Integer | Bu urun icin yapilan ulasim sayisi |
| last_contacted_at | DateTime | Son ulasim zamani |
| rejection_reason | Text | Neden reddedildi |
| outreach_history | JSON | Ulasim gecmisi |
- **UniqueConstraint:** (lead_id, product_id) - ayni lead ayni urunle 1 kez iliskilendirilir
- **Capraz Kullanim:** Urun A icin RED → Urun B uygunsa profile_cache ile direkt ulas

### 4.4 BuyingCommittee (Satin Alma Komitesi)
Bir lead'in sirketindeki birden fazla karar vericiyi takip eder.
- lead_id, name, role, email, linkedin_url, personalization_angle, communication_style, status

### 4.5 Campaign (Kampanyalar)
- ICP kriterleri (JSON), workflow adimlari (JSON), A/B varyantlari (JSON)
- Analitik: total_leads, total_contacted, total_replied, total_meetings, reply_rate, meeting_rate

### 4.6 Workflow (Kampanya Is Akisi)
- Lead'in kampanya icindeki pozisyonunu takip eder
- current_step, status (active/paused/completed/stopped_reply)
- next_scheduled: sonraki adimin zamani
- event_log: tum islemlerin kaydi

### 4.7 EmailAccount & LinkedInAccount
- SMTP/IMAP yapilandirmasi, warm-up durumu, gunluk limitler
- Saglik metrikleri: bounce_rate, spam_complaint_rate, health_score
- SPF/DKIM/DMARC dogrulama durumlari

### 4.8 Message (Mesajlar - Birlesmis Gelen Kutusu)
- direction: inbound / outbound
- channel: email / linkedin_dm / linkedin_connect
- AI metaveri: ai_generated, personalization_data, sentiment_label, sentiment_confidence
- Takip: opened_at, clicked_at, replied_at

### 4.9 Notification (Bildirimler)
- Telegram/WhatsApp koprusu icin bildirim kayitlari

### 4.10 Diger Tablolar
- **TimingPattern**: Lead basina optimal gonderim zamanlari
- **ObjectionLog**: Itirazlar ve AI karsi-argumanlari
- **CampaignAnalytics**: Gunluk/varyant bazli detayli analitik
- **Blacklist**: GDPR/CAN-SPAM uyumlu engelleme listesi

---

## 5. AI Agent Mimarisi

Sistem 6 farkli AI agent kullanir, hepsi Google Gemini uzerinde calisir:

### 5.1 BaseAgent (Abstract Base + Retry/Fallback)
- **Dosya:** `agents/base_agent.py`
- **Desen:** Async Gemini wrapper, retry mekanizmasi, fallback profil
- **Ozellikler:**
  - Gemini 429 (rate limit) durumunda otomatik fallback ICP profili uretir
  - JSON structured output (response_mime_type="application/json")
  - Temperature tuning (0.3 analiz, 0.7 mesaj uretimi)
  - Hata yakalama ve loglama

### 5.2 ProductAnalysisAgent
- **Dosya:** `agents/product_agent.py`
- **Girdi:** Kullanicinin yazdigi urun aciklamasi
- **Cikti (JSON):**
  - `value_proposition`: ozet, temel fayda, farkliliklar
  - `target_market`: birincil segmentler, pazar buyuklugu, aciliyet seviyesi
  - `icp_profile`: sektorler, sirket buyukleri, hedef unvanlar, sorunlar, satin alma sinyalleri, anahtar kelimeler, olumsuz sinyaller
  - `search_strategies`: LinkedIn sorgulari, Google sorgulari, icerik konulari, rakip urunler, topluluklar
  - `outreach_angles`: birincil kanca, takip acilari, itiraz onlemleri

### 5.3 ResearchAgent (ReAct + Step-Back Prompting)
- **Dosya:** `agents/research_agent.py`
- **7 Istihbarat Onceligi:**
  1. Technographics (teknoloji yigini tespiti)
  2. Hiring Intent (is ilani sinyalleri)
  3. News & Funding (haberler ve yatirimlar)
  4. Website Changes (site degisiklikleri)
  5. Content Intent (CEO postlari/podcastleri)
  6. Social Engagement (LinkedIn etkilesimleri)
  7. Competitive Displacement (rakip sikayetleri)
- **Araclar:** scrape_linkedin_profile, scrape_company_page, analyze_website, search_news, compress_context
- **Step-Back Prompting:** Buyuk verileri 2-3 cumlelik ozetlere sikistirir

### 5.4 ScoringAgent (Chain-of-Thought)
- **Dosya:** `agents/scoring_agent.py`
- **4 Puanlama Boyutu (Agirlikli):**
  - ICP Uyumu (%30) - Sirket ideal musteri profiline uyuyor mu?
  - Niyet Sinyalleri (%35) - Kac satin alma sinyali tespit edildi?
  - Erisilebilirlik (%15) - Email/LinkedIn mevcut mu? Satin alma komitesi var mi?
  - Zamanlama (%20) - Sinyaller ne kadar taze?
- **Cikti:** final_score (0-100), confidence (0-100), chain_of_thought, top_signals, recommended_approach, urgency

### 5.5 PersonalizationAgent
- **Dosya:** `agents/personalization_agent.py`
- **6 Kisisellestirme Katmani:**
  1. Style & Tone Matching - LinkedIn postlarindan resmiyet seviyesini analiz et
  2. Common Ground - Universite, sehir, ortak baglanti
  3. Content Intent - Blog yazisi veya podcast'ten spesifik alinti
  4. Signal-Based Hook - Is ilani, tech stack, yatirim haberi
  5. Review & Feedback - Google/G2 yorumlarina referans
  6. P.S. Strategy - Is disi kisisel doknus (hobi, maraton vb.)
- **Kanal Kurallari:**
  - Email: Maksimum 120 kelime
  - LinkedIn DM: Maksimum 80 kelime
  - Connection Request: Maksimum 300 karakter
- **Kesin Kurallar:**
  - Asla "I hope this finds you well" kullanma
  - Ilk cumle MUTLAKA kisisellesmis olmali
  - TEK bir net CTA (Call-to-Action) icermeli
- **Metodlar:**
  - `generate_message()` - Ilk mesaj uretimi
  - `generate_follow_up()` - Onceki mesajlardan farkli acili takip
  - `generate_objection_response()` - 5 itiraz tipine stratejik yanit (fiyat, zamanlama, rakip, yetki, ilgisizlik)

### 5.6 ContentAnalystAgent
- **Dosya:** `agents/content_analyst_agent.py`
- **Girdi:** Lead'in dijital ayak izi (posts, articles, social engagement)
- **Cikti (JSON):**
  - `communication_style`: resmi/yarim-resmi/gunluk
  - `topics`: ilgilendigi konular
  - `pain_points`: tespit edilen sorunlar
  - `interests`: ilgi alanlari
  - `tone`: yazim tonu
  - `personality_type`: kisilik tipi
  - `quotable_moments`: alintilanabilir anlar
  - `best_approach`: onerilen iletisim yaklasimi
- **Fallback:** Gemini hata verirse varsayilan profil uretir

---

## 6. Servisler (Is Mantigi)

### 6.1 DiscoveryService - YENl (Otonom Musteri Kesfetme)
- **Dosya:** `services/discovery_service.py`
- **Pipeline:**
  1. ICP profilinden arama sorgulari uret (Gemini)
  2. Google'da ara (Playwright ile)
  3. Sonuclari domain'e gore tekrar ayikla
  4. Her sonucu Gemini ile analiz et (alakalilik puani)
  5. Puan >= 50 olan sonuclari Lead olarak kaydet
  6. Urun durumunu "active" olarak guncelle

### 6.2 HuntService (Arastirma Orkestrasyonu)
- **Dosya:** `services/hunt_service.py`
- **Pipeline:** Research (ReAct) -> Score (CoT) -> Personalize -> Enqueue
- Hedef domain'leri ve LinkedIn URL'lerini isler
- Lead istihbarat dosyalari olusturur

### 6.3 WorkflowEngine (Kampanya Workflow Motoru)
- **Dosya:** `services/workflow_engine.py`
- **Desteklenen Aksiyonlar:** linkedin_visit, email, linkedin_connect, linkedin_dm
- **Kosullu Dallanma:** email_opened, email_clicked, replied
- **Otomatik Durdurma (KRITIK):** Cevap geldiginde TUM aktif workflow'lari aninda durdurur
- **Zamanlama:** Her 5 dakikada bir due workflow adimlarini isler

### 6.4 WarmupService (Hesap Koruma)
- **Dosya:** `services/warmup_service.py`
- **Isitma Protokolu:**
  - Gun 1-3: 5 email/gun
  - Gun 4-7: +3/gun artis
  - Gun 8-14: +5/gun artis
  - Gun 15+: Tam kapasite (50/gun)
- **Hesap Rotasyonu:** Birden fazla hesap arasinda yuku dagitir
- **Otomatik Durdurma:** Bounce rate > %5 veya spam > %0.1 ise hesabi duraklat
- **Gunluk Sifirlama:** Gece yarisi tum sayaclari sifirla

### 6.5 EmailService (Email Gonderim + Tracking)
- **Dosya:** `services/email_service.py`
- **SMTP Gonderim:** MIME multipart (plain + HTML)
- **Tracking Pixel:** UUID tracking_id ile 1x1 transparent GIF injection
- **Click Tracking:** Link'leri redirect URL'e cevirerek tiklama takibi
- Gonderim sonrasi Message.tracking_id ve status guncelleme

### 6.6 LinkedInService (LinkedIn Otomasyon)
- **Dosya:** `services/linkedin_service.py`
- **Aksiyonlar:** visit_profile, send_connection, send_dm
- LinkedInGuard.can_perform() kontrolu ile anti-ban koruma
- visit_profile → connect (insan davranisi simulasyonu)
- StealthBrowser + li_at cookie ile oturum yonetimi

### 6.7 LinkedInGuard (Anti-Ban Koruma)
- **Dosya:** `services/linkedin_guard.py`
- **Gunluk Limitler:** profile_view=50, connect=25, dm=20, search=30
- **Warmup Schedule:** Hafta 1=%30, Hafta 2=%60, Hafta 3=%80, Hafta 4+=%100
- **Gecikme Formulu:** base_delay + random_jitter + (session_actions * 50ms fatigue)
- **Session Yonetimi:** 45dk aktif → 15-30dk mola
- **Risk Tespiti:** HTTP 429→6 saat, CAPTCHA→24 saat, unusual→48 saat pause
- **Insan Simulasyonu:** 2-5sn bekleme, %30-70 scroll, rastgele element hover

### 6.8 SentimentService (Duygu Analizi)
- **Dosya:** `services/sentiment_service.py`
- **Gemini-powered** cevap siniflandirma
- **Cikti:** sentiment, confidence, intent, should_stop_automation, suggested_action, urgency
- **process_reply():** analiz → Message guncelle → Lead status guncelle → workflow durdur
- **Intent Tipleri:** interested, not_interested, meeting_request, objection, question, auto_reply

### 6.9 IMAPService (Gelen Mesaj Tespiti)
- **Dosya:** `services/imap_service.py`
- 2 dakikada bir IMAP4_SSL baglantisi
- UNSEEN filtreleme, sender→Lead eslestirme
- Gelen mesaji Message olarak kaydet → SentimentService tetikle

### 6.10 PlanLimiter (Monetizasyon Gating)
- **Dosya:** `services/plan_limiter.py`
- **Plan Limitleri:**
  - Trial: 10 lead/ay, 5 mesaj/ay, 1 urun
  - Pro: sinirsiz lead + mesaj, 3 urun, LinkedIn + email
  - Enterprise: sinirsiz her sey, 10 urun, takim, API
- **Metodlar:** check_limit(), increment_usage(), require_limit() (HTTP 402)

### 6.11 A/B Testing Engine
- **Dosya:** `services/ab_testing.py`
- Variant assignment (A/B/C varyantlari)
- Istatistiksel anlamlilik testi
- Otomatik winner secimi

### 6.12 BridgeService (Bildirim Koprusu)
- **Dosya:** `services/bridge_service.py`
- Telegram Bot API ve WhatsApp API entegrasyonu
- Bildirimleri mesajlasma platformlarina yonlendirir

### 6.13 DigitalFootprintScanner (Sherlock-Style Tarama) - YENl
- **Dosya:** `services/footprint_scanner.py`
- **121 platform** uzerinde async username tarama (aiohttp + semaphore)
- **3 tespit yontemi:** status_code (HTTP 200/404), message (hata mesaji arama), response_url (redirect kontrolu)
- **Username cikarma:** email prefix, LinkedIn slug, isim kombinasyonlari (dot, dash, nosep)
- **Concurrency:** 20 paralel istek, 10sn timeout, proxy pool destegi
- **Footprint Score:** base (relevance*10) + category diversity bonus + high-value platform bonus (max 100)
- **Kategoriler:** developer, professional, social, content, design, startup, business, marketing, finance, security, data_science, ai_ml, creator, streaming, gaming, academic, ecommerce, news, recruiting, messaging
- **Site DB:** `data/sites.json` — her platform icin URL template, errorType, category, sales_relevance, regexCheck

### 6.14 EnrichmentPipeline (4 Adimli Zenginlestirme) - YENl
- **Dosya:** `services/enrichment_pipeline.py`
- **Pipeline:**
  1. **Footprint Scan** → 121 platformda social profile kesfet
  2. **API Enrichment** → Hunter.io, Snov.io, RocketReach, FullContact, BuiltWith (waterfall)
  3. **Social Proof Scoring** → LinkedIn +5, Twitter +3, GitHub +3, Medium +3, breadth bonus +5 (max 25 puan boost)
  4. **Content Analysis** → ContentAnalystAgent ile enriched context analizi
- API enrichment'ta bulunan email, title, company otomatik lead'e yazilir
- FullContact'tan gelen social profile'lar footprint sonuclarina merge edilir
- BuiltWith'ten gelen technographics lead.technographics alanina yazilir

### 6.15 LeadEnrichmentAPI (Harici API Entegrasyonlari) - YENl
- **Dosya:** `services/lead_enrichment_api.py`
- **5 Provider (Waterfall Pattern):**

| Provider | API | Ne Yapar | .env Degiskeni |
|----------|-----|----------|----------------|
| Hunter.io | Email Finder | Domain + isimden email bul | HUNTER_IO_API_KEY |
| Snov.io | Email Finder | OAuth token + email lookup | SNOV_IO_CLIENT_ID, SNOV_IO_CLIENT_SECRET |
| RocketReach | Person Lookup | Isim + sirket → email + title | ROCKETREACH_API_KEY |
| FullContact | Person Enrich | Email → ad, title, bio, social profiles | FULLCONTACT_API_KEY |
| BuiltWith | Technographics | Domain → tech stack listesi | BUILTWITH_API_KEY |

- **Email Bulma Waterfall:** Hunter.io → Snov.io → RocketReach (ilk bulan kazanir)
- **full_enrich():** Tum provider'lari tek cagriyla calistir, sonuclari merge et
- **Rate Limit Handling:** 429 loglanir, bir sonraki provider'a gecilir

### 6.16 EventBus (SSE Event Dagitim) - YENl
- **Dosya:** `services/event_bus.py`
- Redis pub/sub veya in-memory fallback
- Kanal bazli subscribe/publish (`hunt:{user_id}:{product_id}`)
- SSE formatinda event stream (text/event-stream)

---

## 7. Web Scraping Altyapisi

### 7.1 StealthBrowser (Anti-Detection)
- **Dosya:** `scraping/stealth_browser.py`
- **Bot Korumalari:**
  - webdriver flag'i gizleme
  - Sahte plugin ve dil bilgileri
  - Chrome runtime spoofing
  - Rastgele viewport ve user-agent
- **Insan-Benzeri Davranislar:**
  - `human_type()`: Rastgele tuslanma gecikmeleri
  - `human_click()`: Merkez-disi tiklama
  - `human_scroll()`: Degisken hizda kaydirma
  - `random_mouse_movement()`: Fare titresmesi
- Proxy destegi, oturum cookie'si kaliciligi

### 7.2 LinkedInScraper
- **Dosya:** `scraping/linkedin_scraper.py`
- `scrape_profile()`: Ad, unvan, hakkinda, son 4 post, etkilesim verileri
- `scrape_company_page()`: Sirket bilgileri, sektorler, is ilanlari
- `visit_profile()`: Sessiz profil ziyareti (LinkedIn bildirimini tetikler)

### 7.3 WebsiteScraper & NewsScraper
- **Dosya:** `scraping/website_scraper.py`
- **Technographics Tespiti:** Shopify, WordPress, HubSpot, Stripe, Next.js
- **Haber Taramasi:** Google News'ten yatirim, ise alim, lansman haberleri

---

## 8. API Endpoint'leri (60+ Endpoint)

### 8.1 Auth (/api/v1/auth)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| POST | /auth/register | Yeni kullanici kaydi |
| POST | /auth/login | JWT token ile giris (OAuth2 uyumlu) |
| GET | /auth/me | Mevcut kullanici profili |

### 8.2 Products (/api/v1/products) - YENl
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| POST | /products | Yeni urun olustur |
| GET | /products | Kullanicinin urunlerini listele |
| GET | /products/{id} | Urun detayi (AI analiz sonuclariyla) |
| PATCH | /products/{id} | Urun bilgilerini guncelle |
| POST | /products/{id}/analyze | AI analizi baslat (ICP + strateji) |
| POST | /products/{id}/start-hunting | Otonom musteri kesfini baslat |

### 8.3 Leads (/api/v1/leads)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| GET | /leads | Filtreleme, arama, siralama ile listele |
| GET | /leads/{id} | Tam istihbarat detayi |
| POST | /leads | Manuel lead olusturma |
| PATCH | /leads/{id} | Lead guncelleme |
| DELETE | /leads/{id} | Lead silme |
| GET | /leads/{id}/committee | Satin alma komitesi |
| POST | /leads/{id}/committee | Komite uyesi ekle |

### 8.4 Hunt (/api/v1/hunt)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| POST | /hunt/start | AI arastirma pipeline'ini baslat |
| GET | /hunt/stream/{product_id} | SSE real-time progress (EventSource, ?token= auth) |

### 8.5 Campaigns (/api/v1/campaigns)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| GET | /campaigns | Kampanyalari listele |
| POST | /campaigns | Yeni kampanya olustur |
| GET | /campaigns/{id} | Kampanya detayi |
| PATCH | /campaigns/{id} | Kampanya guncelle |
| POST | /campaigns/{id}/activate | Kampanyayi baslat |
| POST | /campaigns/{id}/pause | Kampanyayi duraklat |
| POST | /campaigns/{id}/enqueue/{lead_id} | Lead'i workflow'a ekle |

### 8.6 Inbox (/api/v1/inbox)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| GET | /inbox/unified | Tum kanallardan mesajlar (filtreli) |
| GET | /inbox/thread/{id} | Konusma dizisi |
| POST | /inbox/{id}/read | Okundu isaretle |
| POST | /inbox/compose | Manuel mesaj yaz ve gonder |
| GET | /inbox/notifications | Bildirimleri getir |
| POST | /inbox/bridge/telegram-whatsapp | Bildirim koprusu |

### 8.7 Accounts (/api/v1/accounts)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| GET | /accounts/health | Teslimat sagligi paneli |
| POST | /accounts/email | Email hesabi bagla |
| GET | /accounts/email | Email hesaplarini listele |
| POST | /accounts/email/{id}/pause | Hesabi duraklat |
| POST | /accounts/email/{id}/resume | Hesabi devam ettir |
| POST | /accounts/linkedin | LinkedIn hesabi bagla |
| GET | /accounts/linkedin | LinkedIn hesaplarini listele |
| GET | /accounts/blacklist | Engel listesini gor |
| POST | /accounts/blacklist | Engel listesine ekle |
| DELETE | /accounts/blacklist/{id} | Engel listesinden cikar |

### 8.8 Analytics (/api/v1/analytics)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| GET | /analytics/dashboard | Ana panel: KPI'lar, istatistikler |
| GET | /analytics/campaigns/{id}/autopsy | Kampanya performans analizi |
| GET | /analytics/leads/scoring-distribution | Puanlama dagilimi |

### 8.9 Messages (/api/v1/messages)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| POST | /messages/{lead_id}/generate | AI mesaj uret (ContentAnalyst + Personalization) |
| POST | /messages/{lead_id}/approve | Mesaji onayla ve gonderim kuyuguna ekle |
| POST | /messages/batch-generate | Toplu mesaj uretimi (arka plan gorevi) |
| GET | /messages/{lead_id}/drafts | Lead icin taslak mesajlari getir |

### 8.10 Billing (/api/v1/billing)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| GET | /billing/usage | Mevcut plan + kullanim istatistikleri |
| GET | /billing/plans | Mevcut planlari listele |
| POST | /billing/checkout | LemonSqueezy checkout session olustur |
| POST | /billing/webhook | LemonSqueezy webhook (subscription events) |

### 8.11 Tracking (/api/v1/tracking)
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| GET | /tracking/open/{tracking_id} | Email acilma takibi (1x1 GIF pixel) |
| GET | /tracking/click/{tracking_id} | Link tiklama takibi (redirect) |

### 8.12 Footprint & Enrichment (/api/v1/footprint) - YENl
| Method | Endpoint | Aciklama |
|--------|----------|----------|
| POST | /footprint/scan/{lead_id} | Dijital ayak izi taramasi baslat (121 platform) |
| POST | /footprint/bulk-scan | Toplu tarama (Enterprise only) |
| GET | /footprint/{lead_id} | Cached tarama sonuclarini getir |
| GET | /footprint/{lead_id}/dossier | Tam dijital dosya (insights + profiles) |
| POST | /footprint/enrich/{lead_id} | Full enrichment pipeline (scan + API + score + content) |
| POST | /footprint/enrich-batch | Toplu enrichment (Enterprise only) |

---

## 9. Frontend Sayfalar

### 9.1 Auth Sayfalari
- **Login** (`/login`): Email + sifre formu, "goz" ikonu ile sifre gostergeci
- **Register** (`/register`): Ad, email, sifre formu

### 9.2 Dashboard (`/`)
- 6 KPI karti: Total Leads, Contacted, Replied, Meetings, Reply Rate, Active Campaigns
- Hot Leads tablosu (en yuksek puanli 5 lead)
- Hizli aksiyon butonlari: Start Hunt, Create Campaign, View Inbox
- **Real API'ye bagli** (`api.analytics.dashboard()` + `api.leads.list()`)

### 9.3 Products / Onboarding (`/onboarding`) - YENl
- **Urun Listesi:** Mevcut urunleri kartlar halinde goster
- **Urun Wizard (3 Adim):**
  1. "Urununuzu Anlatin" - Buyuk textarea ile urun aciklamasi
  2. "AI Analiz Sonuclari" - ICP profili, hedef sektorler, arama stratejileri
  3. "Avi Baslat" - Otonom kesfetmeyi tetikle
- AI analizi: ProductAnalysisAgent ile Gemini cagrisii
- Av baslat: DiscoveryService ile arka plan gorevi

### 9.4 Leads (`/leads`)
- Arama, durum filtresi, puanlama siralamasi
- Sayfalama (20 lead/sayfa)
- Lead detaylari: isim, sirket, puan, durum, kaynak, notlar
- **Real API'ye bagli** (`api.leads.list()`)

### 9.5 Campaigns (`/campaigns`)
- Kampanya listesi (real API)
- "Yeni Kampanya" modal: isim, urun secimi, kanal, adim tanimlama
- Kampanya durum yonetimi: activate, pause
- **Real API'ye bagli** (`api.campaigns.*`)

### 9.6 Pricing (`/pricing`)
- 3 plan karti: Trial (Ucretsiz) / Pro ($49/ay) / Enterprise ($149/ay)
- Ozellik karsilastirma tablosu
- Checkout butonu (LemonSqueezy entegrasyonu)
- Mevcut plan gostergeci

### 9.7 Digital Dossier (`/leads/[id]/footprint`) - YENl
- Footprint score + bulunan platform sayisi + kategori sayisi
- Profile type badge'leri: Tech / Creator / General
- Primary platform vurgusu (en yuksek sales_relevance)
- Kesfedilen profillerin grid gorunumu (ikon + link + kategori rengi)
- "Scan Footprint" / "Re-scan" + "Enrich" butonlari
- 402 handling (plan limiti)
- Enrichment sonuc gostergesi (provider sayisi, skor)

### 9.8 Diger Sayfalar
- **Hunt** (`/hunt`): Av baslat + SSE real-time progress (useHuntStream hook)
- **Inbox** (`/inbox`): Birlesmis gelen kutusu
- **Accounts** (`/accounts`): Hesap yonetimi ve saglik paneli
- **Analytics** (`/analytics`): Kampanya performans grafikleri
- **Settings** (`/settings`): Kullanici ayarlari + dil secimi (TR/EN)

### 9.9 Yeni Komponentler
- **MessagePreviewModal**: Mesaj onizleme, edit modu, personalization tag'leri, approve & send
- **UpgradeModal**: Plan yukseltme promptu, FOMO hook ("Son 7 gunde kacardiginiz X lead!")
- **Sidebar**: Dil toggle (TR/EN), pricing linki, navigasyon

### 9.10 i18n (Cok Dilli Destek)
- **useI18n hook**: React state ile locale yonetimi
- **~80 ceviri key'i**: nav, common, auth, dashboard, products, leads, campaigns, inbox, billing, settings
- **localStorage persist**: Dil tercihi sayfa yenilemede korunur
- **Desteklenen Diller:** Turkce (TR), English (EN)

### 9.11 Tasarim Sistemi
- **Swiss-Minimalist** tasarim dili
- Renkler: Arka plan #E8E8E8, Yusey #FFFFFF, Primary #FF5722 (turuncu), Metin #2E2E2E
- 8px baseline grid sistemi
- Stagger animasyonlari (kaskatli giris efektleri)
- Ozel bilesenler: kpi-card, score-badge (hot/warm/cool/cold), status-badge, table-container

---

## 10. Guvenlik

### 10.1 Kimlik Dogrulama
- JWT token (HS256) - 24 saat gecerlilik
- bcrypt ile sifre hashleme
- OAuth2PasswordBearer (Swagger entegrasyonu)
- RBAC: admin, manager, member rolleri

### 10.2 Hesap Guvenligi
- Email warm-up protokolu (spam korunmasi)
- Hesap rotasyonu (risk dagitimi)
- Otomatik duraklama (yuksek bounce/spam oraninda)
- Blacklist (GDPR/CAN-SPAM uyumlulufu)

### 10.3 Scraping Guvenligi
- Stealth browser (bot tespiti onleme)
- Proxy destegi
- Insan-benzeri davranislar (gecikme, fare hareketi)
- User-agent ve viewport randomizasyonu

### 10.4 Cozulen Guvenlik Sorunlari ✅
- ~~SMTP sifresi duz metin~~ → Fernet AES-128 sifreleme (Phase 9)
- ~~LinkedIn session cookie duz metin~~ → Fernet sifreleme (Phase 9)
- ~~Gemini API key hardcoded~~ → .env'den okuyor (Phase 9)
- ~~Rate limiting yok~~ → Redis-backed + in-memory fallback (Phase 10)
- ~~Hard delete~~ → Soft delete (is_deleted + deleted_at) (Phase 10)

---

## 11. Arkaplan Gorevleri (APScheduler - 5 Job)

| Gorev | Zamanlama | Aciklama |
|-------|-----------|----------|
| _run_scheduled_workflows | Her 5 dakika | Due workflow adimlarini isle |
| _run_scheduled_warmup | Her gun saat 06:00 | Email + LinkedIn hesap isitma |
| _run_daily_reset | Her gun gece yarisi | Gunluk sayaclari sifirla |
| _run_reply_check | Her 2 dakika | IMAP ile gelen mesaj kontrolu |
| _run_monthly_usage_reset | Ayin 1'i saat 00:00 | Aylik kullanim sayaclarini sifirla |

---

## 12. Mevcut Durum ve Yol Haritasi

### 12.1 Tamamlanan Ozellikler (Phase 1-10)

**Phase 1 - MVP Temel (TAMAMLANDI):**
- 14 veritabani tablosu
- 60+ API endpoint
- JWT auth + RBAC
- Urun onboarding akisi (3 adimli wizard)
- Otonom musteri kesfetme (Google + Playwright)
- Dashboard + Leads sayfasi (real API)

**Phase 2 - Icerik Analizi & Mesaj Uretimi (TAMAMLANDI):**
- ContentAnalystAgent: dijital ayak izi analizi
- PersonalizationAgent: 6 katmanli kisisellestirme
- Messages API: generate, approve, batch, drafts
- MessagePreviewModal: onizleme, edit, approve & send

**Phase 2.5 - Lead Havuzu & Capraz Urun (TAMAMLANDI):**
- LeadProduct junction table (many-to-many)
- profile_cache + 30 gun gecerlilik
- Triple dedup: email + linkedin_url + domain

**Phase 3 - Email & Monetizasyon (TAMAMLANDI):**
- EmailService: SMTP + tracking pixel injection
- Tracking API: open pixel (1x1 GIF) + click redirect
- PlanLimiter: trial/pro/enterprise (HTTP 402)
- Billing API: usage, plans, checkout, LemonSqueezy webhook
- WarmupService: email + LinkedIn hesap isitma

**Phase 4 - Frontend & i18n (TAMAMLANDI):**
- i18n sistemi: TR/EN, useI18n hook, ~80 ceviri key'i
- Campaigns sayfasi: liste + yeni kampanya modal
- Pricing sayfasi: plan karsilastirma
- UpgradeModal: FOMO hook
- Sidebar: dil toggle + pricing link

**Phase 5 - LinkedIn Otomasyon & Anti-Ban (TAMAMLANDI):**
- LinkedInGuard: limitler, warmup (4 hafta), fatigue
- LinkedInService: visit, connect, DM
- Risk detection: 429→6h, CAPTCHA→24h, unusual→48h
- Session yonetimi: 45dk aktif → 15-30dk mola

**Phase 6 - Sentiment & Reply Detection (TAMAMLANDI):**
- SentimentService: Gemini-powered siniflandirma
- IMAPService: 2dk IMAP polling
- Oto-stop: insan cevabi → workflow durur
- Intent: interested/not_interested/meeting/objection/question

**Phase 7 - Testing & A/B (TAMAMLANDI):**
- Pytest: conftest, auth, products, leads, campaigns, billing
- A/B Testing Engine: variant assignment, winner detection

**Phase 8 - Deployment (TAMAMLANDI):**
- Dockerfile + docker-compose (prod + dev)
- GitHub Actions CI
- Celery + Redis async tasks
- Alembic migration setup

**Phase 9 - Enterprise Hardening (TAMAMLANDI):**
- Fernet credential encryption (SMTP + LinkedIn cookie)
- Redis-backed rate limiter + login tracker
- LLM budget guard, structured logging, request ID middleware
- Refresh token rotation, audit logging, GDPR endpoints
- CRM integration (HubSpot + Pipedrive), RBAC frontend
- CAN-SPAM compliance, agent output validation
- AsyncIO fixes (8 yer), workflow engine bug fixes (3 kritik)

**Phase 10 - Digital Footprint & Enrichment (TAMAMLANDI):**
- Sherlock-style 121 platform tarama (async, 3 detection method)
- 5 harici API entegrasyonu (Hunter.io, Snov.io, RocketReach, FullContact, BuiltWith)
- 4 adimli enrichment pipeline (scan → API → score → content)
- Digital Dossier frontend sayfasi (scan + enrich butonlari)
- SSE real-time hunt progress (EventSource + useHuntStream hook)
- Redis connection pool + graceful fallback
- Soft delete (is_deleted + deleted_at) + composite indexes
- Health endpoint (/health, DB + Redis check)
- 159 test (13 dosya), 0 TypeScript hatasi

### 12.2 Kalan Isler / Gelecek

- PostgreSQL migration (prod icin, simdilik SQLite dev'de)
- Viral loop: "Powered by HUNTER.OS" footer
- Multi-tenant: takim yonetimi (Enterprise plan)
- WebSocket: SSE'nin yanina iki yonlu iletisim (scan iptal, canli chat)
- Gelismis A/B test dashboardu (frontend'de)
- Lead scoring kalibrasyonu (musteri geri bildirimine gore agirlik ayarlama)

---

## 13. Calistirma Talimatlari

### 13.1 Backend
```bash
cd ~/Desktop/aipoweredsaleshunter/backend
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### 13.2 Frontend
```bash
cd ~/Desktop/aipoweredsaleshunter/frontend
npm install
npm run dev
```
- UI: http://localhost:3000

### 13.3 Ortam Degiskenleri (.env)
```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-flash-latest
PLAYWRIGHT_HEADLESS=true
SECRET_KEY=change-this-in-production
```

---

## 14. Onemli Teknik Detaylar

### 14.1 Workflow Adim Yapisi (JSON)
```json
{
  "step": 1,
  "channel": "email",
  "delay_hours": 0,
  "template_id": "intro_a",
  "condition": null
}
```
Kosullu dallanma ornegi:
```json
{
  "step": 2,
  "channel": "linkedin_visit",
  "delay_hours": 24,
  "condition": {"type": "email_opened", "value": true}
}
```

### 14.2 Lead Puanlama Formulu
```
final_score = (icp_match * 0.30) + (intent * 0.35) + (accessibility * 0.15) + (timing * 0.20)
confidence = quality_of_data_factor * signal_freshness
```

### 14.3 Warm-up Ilerleme Tablosu
| Gun | Gunluk Limit | Toplam |
|-----|-------------|--------|
| 1-3 | 5 | 15 |
| 4 | 8 | 23 |
| 5 | 11 | 34 |
| 6 | 14 | 48 |
| 7 | 17 | 65 |
| 8 | 22 | 87 |
| 9 | 27 | 114 |
| 10 | 32 | 146 |
| 11 | 37 | 183 |
| 12 | 42 | 225 |
| 13 | 47 | 272 |
| 14 | 50 (max) | 322 |

### 14.4 API Client Yapisi (Frontend)
Tum API istekleri `frontend/src/lib/api.ts` icindeki `ApiClient` sinifi uzerinden yapilir:
- JWT token localStorage'da "hunter_token" olarak saklanir
- 401 hatasinda otomatik login'e yonlendirir
- Namespace'li metodlar: `api.auth.login()`, `api.leads.list()`, `api.products.analyze()` vb.
- Login: OAuth2 uyumlu `application/x-www-form-urlencoded` format

---

## 15. 60 Gunluk Savas Plani (PRD'den)

| Donem | Gun | Hedef |
|-------|-----|-------|
| Validation | 1-10 | 150 ajansla konus, ihtiyaci dogrula |
| MVP Build | 11-35 | Urun onboarding + AI kesfetme + mesaj uretimi |
| First Revenue | 36-50 | Pilot kullanicilardan ilk $49'i al |
| Growth | 51-60 | Hunter'i kendi satisimiz icin calistir (Project Inception) |

---

## 16. Bagimlilikllar

### Backend (requirements.txt)
```
fastapi==0.115.6
uvicorn==0.34.0
sqlalchemy==2.0.36
pydantic==2.10.3
pydantic-settings==2.7.0
python-jose==3.3.0
bcrypt==4.2.1
google-generativeai==0.8.3
playwright==1.49.1
httpx==0.28.1
apscheduler==3.10.4
aiofiles==24.1.0
python-dotenv==1.0.1
python-multipart==0.0.20
jinja2==3.1.5
pypdf2==3.0.1
scikit-learn==1.6.0
numpy==2.2.1
```

### Frontend (package.json)
```
next: 15.1.0
react: 19.0.0
recharts: 2.14.1
lucide-react: 0.468.0
tailwindcss: 3.4.17
typescript: 5.7.2
clsx: 2.1.1
date-fns: 4.1.0
```

---

## 17. Yeni Eklenen Ozellikler (Phase 2-8 Ozet)

### Monetizasyon Modeli
| Plan | Fiyat | Lead | Mesaj | Urun | LinkedIn | Email |
|------|-------|------|-------|------|----------|-------|
| Trial | Ucretsiz (14 gun) | 10/ay | 5/ay | 1 | X | X |
| Pro | $49/ay | Sinirsiz | Sinirsiz | 3 | ✓ | ✓ |
| Enterprise | $149/ay | Sinirsiz | Sinirsiz | Sinirsiz | ✓ | ✓ |

- LemonSqueezy (Turkiye uyumlu MoR) ile odeme
- HTTP 402 ile limit enforcement
- FOMO: trial sonrasi "kacardiginiz X lead" goster

### Anti-Ban Sistemi (LinkedInGuard)
- 4 haftalik warmup: %30 → %60 → %80 → %100
- Fatigue factor: her aksiyon +50ms gecikme ekler
- Risk sinyalleri: HTTP 429, CAPTCHA, unusual activity
- Insan simulasyonu: scroll, hover, rastgele beklemeler

### Duygu Analizi Pipeline
```
Gelen Email → IMAP Polling (2dk) → Sender→Lead Eslestirme
→ SentimentService (Gemini) → Intent Siniflandirma
→ should_stop=true ise → Workflow Durdur + Lead Status Guncelle
```

### i18n Sistemi
- useI18n React hook
- ~120+ ceviri key'i (TR/EN/DE/FR/ES)
- localStorage ile dil tercihi persist
- Sidebar'da dil toggle butonu

---

## Phase 9: Enterprise Hardening (26 Mart 2026) ✅

### 9.1 Guvenlik Katmanlari (P0-P1)

| Ozellik | Dosya | Detay |
|---------|-------|-------|
| Credential Encryption | `core/encryption.py` | Fernet AES-128 ile SMTP sifreleri, LinkedIn cookie'leri sifreleme |
| Rate Limiter | `core/rate_limiter.py` | Token-bucket rate limiter + LoginAttemptTracker (5 hata → 15dk kilit) |
| LLM Budget Guard | `core/llm_budget_guard.py` | Her AI cagrisi oncesi token butcesi kontrolu (HTTP 402) |
| Structured Logging | `core/logging_config.py` | JSON structured logging (prod), request_id ContextVar |
| Request ID Middleware | `core/middleware.py` | Her istege X-Request-ID header, request suresi loglama |
| Refresh Token Rotation | `core/security.py` | SHA-256 hash, reuse detection (tum token'lar iptal) |
| Audit Logging | `models/audit_log.py` + `services/audit_service.py` | login/register/password_change/gdpr islemleri kayit |
| GDPR Endpoints | `api/v1/gdpr.py` | Right to erasure + data export (JSON download) |
| Secrets Protection | `SECRET_KEY` ve `GEMINI_API_KEY` artik ZORUNLU (default yok) |
| Swagger Gizleme | DEBUG=False iken /docs ve /redoc kapali |

### 9.2 Altyapi Guclenmeleri (P2-P3)

| Ozellik | Dosya | Detay |
|---------|-------|-------|
| Agent Output Validation | `schemas/agent_outputs.py` | 8 Pydantic v2 schema (ICPAnalysis, LeadScore, PersonalizedMessage vb.) |
| Agent Context Compression | `agents/base_agent.py` | _compress_history() ile token tasarrufu, LLM cost tracking |
| LinkedInGuard DB Persistence | `models/linkedin_guard_state.py` | Warmup ve rate limit state'i DB'ye yaziliyor |
| AsyncIO Fix (8 yer) | workflow_engine, discovery, sentiment, messages | asyncio.run() + ThreadPoolExecutor pattern |
| WorkflowEngine Bug Fixes | `services/workflow_engine.py` | 3 critical bug duzeltildi: email send, LinkedIn cookie, DM argument order |
| Dual DB Support | `core/database.py` | SQLite (dev) + PostgreSQL (prod) otomatik tanimla |
| CAN-SPAM Compliance | `services/email_service.py` | Unsubscribe footer + List-Unsubscribe header |
| CRM Integration | `services/crm_service.py` + `api/v1/crm.py` | HubSpot + Pipedrive (strategy pattern) |
| RBAC Frontend | `hooks/usePermissions.ts` + `PermissionGate.tsx` | admin>manager>member>viewer role hierarchy |
| SSE Hunt Stream | `hooks/useHuntStream.ts` | Real-time discovery progress via EventSource |
| i18n 5 Dil | `lib/i18n.ts` | TR/EN/DE/FR/ES tam destek |

### 9.3 WorkflowEngine Bug Fix Detaylari

3 kritik bug duzeltildi:

**Bug 1 (Email Send):** `send_email(message, sender)` → ORM objeleri yerine dogru string field'lari cikartildi:
```python
email_service.send_email(
    to_email=lead.email, subject=message.subject, body=message.body,
    from_email=sender.email, message_id=message.id,
    smtp_host=sender.smtp_host, smtp_port=sender.smtp_port,
    smtp_user=sender.smtp_user, smtp_password=decrypt_value(sender.smtp_password_encrypted),
)
```

**Bug 2+3 (LinkedIn Cookie):** `lead.user_id` (int) yerine `LinkedInAccount.session_cookie` (decrypted) kullanildi:
```python
cookie = _get_linkedin_cookie(self.db, lead.user_id)  # DB'den cookie bul + decrypt
service.visit_profile(lead.linkedin_url, cookie)
service.send_connection(lead.linkedin_url, cookie, note)
service.send_dm(lead.linkedin_url, cookie, message)
```

### 9.4 Cozulen Guvenlik Sorunlari
- ✅ SMTP sifresi artik Fernet AES-128 ile sifreleniyor (`core/encryption.py`)
- ✅ LinkedIn session cookie sifreleniyor
- ✅ Gemini API key .env'den okuyor (hardcode kaldirildi)
- ✅ Redis-backed rate limiter eklendi (in-memory fallback ile)
- ✅ Soft delete (is_deleted + deleted_at) ile geri alinabilir silme
- ✅ Health endpoint: DB + Redis saglik kontrolu (/health)

### 9.5 Landing Page

Kova/Slade stilinde grainy gradient tasarim:
- Hawk logosu (SVG)
- Cinematic gradient background
- Feature showcase (3 kart)
- Social proof section
- Dark theme, premium his

---

## Calistirma Talimatlari

### Backend Baslat
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # .env'yi duzenle (GEMINI_API_KEY, SECRET_KEY zorunlu)
uvicorn app.main:app --reload --port 8000
```

### Frontend Baslat
```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

### Core Flow Test (E2E)
```bash
cd backend
python test_core_flow.py
# Register → Login → Urun olustur → AI ICP analiz → Google dorking → Lead bul → Mesaj uret
```

### Gerekli Dis Servisler

| Servis | Ne Icin | Zorunlu? | .env Degiskeni |
|--------|---------|----------|----------------|
| Google Gemini API | AI analiz, ICP, mesaj uretimi | EVET | GEMINI_API_KEY |
| SMTP (Gmail/Outlook) | Email gonderimi | EVET (outreach icin) | SMTP_HOST, SMTP_USER, SMTP_PASSWORD |
| IMAP | Gelen email tespiti | EVET (reply detection) | IMAP_HOST, IMAP_USER, IMAP_PASSWORD |
| LinkedIn li_at Cookie | LinkedIn otomasyon | Opsiyonel | DB'de encrypted |
| HubSpot API Key | CRM export | Opsiyonel | HUBSPOT_API_KEY |
| Pipedrive API Key | CRM export | Opsiyonel | PIPEDRIVE_API_KEY |
| LemonSqueezy | Odeme | Opsiyonel (prod) | LEMONSQUEEZY_API_KEY, LEMONSQUEEZY_WEBHOOK_SECRET |
| Proxy/VPN | Google ban onleme | Onerilen (prod) | HTTP_PROXY |
| Hunter.io | Email finder | Opsiyonel | HUNTER_IO_API_KEY |
| Snov.io | Email finder | Opsiyonel | SNOV_IO_CLIENT_ID, SNOV_IO_CLIENT_SECRET |
| RocketReach | Person lookup | Opsiyonel | ROCKETREACH_API_KEY |
| FullContact | Person enrichment | Opsiyonel | FULLCONTACT_API_KEY |
| BuiltWith | Technographics | Opsiyonel | BUILTWITH_API_KEY |
| Redis | Rate limiting + SSE | Opsiyonel | REDIS_URL |

### Kurumsal Satis Icin Gerekli Minimum

1. **GEMINI_API_KEY** — AI beyni (zorunlu)
2. **SMTP** — Email gonderim altyapisi (zorunlu)
3. **IMAP** — Reply detection (zorunlu)
4. **SECRET_KEY** — JWT guvenligi (zorunlu, `openssl rand -hex 32`)
5. **ENCRYPTION_KEY** — Credential sifreleme (zorunlu, `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
6. **PostgreSQL** — Production DB (SQLite sadece dev icin)


---

## Phase 10: Digital Footprint & Enrichment (3 Nisan 2026) ✅

### 10.1 Neden Yapildi?

Onceki surumde lead kesfediliyordu ama sadece Google/LinkedIn verileriyle sinirli kaliyordu. Lead hakkinda "bu kisi kimdir?" sorusuna derinlemesine yanit veremiyorduk. Phase 10 ile lead bir kez kesfedildikten sonra 121 platformda dijital ayak izi taranip, harici API'lerle zenginlestirilip, scoring'i guncelleniyor.

### 10.2 Onceki Surum vs Yeni Surum

| Ozellik | Onceki (Phase 1-9) | Yeni (Phase 10+) |
|---------|-------------------|-------------------|
| Lead kesfetme | Google + LinkedIn scraping | Ayni + 121 platform tarama |
| Email bulma | Sadece scraping ile | Hunter.io → Snov.io → RocketReach waterfall |
| Kisi bilgisi | Sadece LinkedIn'den | FullContact API ile (bio, title, avatar, social) |
| Technographics | Website scraping ile | BuiltWith API ile (detayli tech stack) |
| Social profiles | LinkedIn + manual | Otomatik 121 platform (GitHub, Twitter, Medium, ProductHunt...) |
| Footprint score | Yok | 0-100 skor (platform sayisi + diversity + high-value bonus) |
| Enrichment | Yok (tek adim) | 4 adimli pipeline (scan → API → score boost → content) |
| Hunt progress | Sadece background task | SSE real-time stream (EventSource) |
| Lead silme | Hard delete | Soft delete (is_deleted, geri alinabilir) |
| Health check | Yok | /health endpoint (DB + Redis durum) |
| Rate limiting | In-memory | Redis-backed (multi-process safe) + fallback |
| Test sayisi | ~50 | 159 test (13 dosya) |
| API endpoint sayisi | ~60 | ~70 (footprint/enrich eklendi) |

### 10.3 Nasil Calistirilir?

#### Temel Calistirma (Oncekiyle Ayni)
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

#### Yeni Ozellikler Icin Ek Yapilandirma

**1. Footprint Scanner (Ek kurulum GEREKMEZ):**
- 121 platform tarama kutunun disinda calisir
- Ekstra API key gerekmez — sadece HTTP istekleri ile platform kontrol eder
- Kullanim: Leads sayfasindan lead sec → "Digital Dossier" → "Scan Footprint"

**2. Harici Enrichment API'leri (OPSIYONEL ama onerilen):**
`.env` dosyasina ekle:
```bash
# Email Finder (en az birini ekle - waterfall olarak calisir)
HUNTER_IO_API_KEY=your-key           # hunter.io/api
SNOV_IO_CLIENT_ID=your-id            # snov.io/knowledgebase
SNOV_IO_CLIENT_SECRET=your-secret
ROCKETREACH_API_KEY=your-key         # rocketreach.co/api

# Person Enrichment
FULLCONTACT_API_KEY=your-key         # fullcontact.com

# Company Technographics
BUILTWITH_API_KEY=your-key           # builtwith.com/api
```
- **Hicbiri olmasa da calisir** — sadece footprint scan + internal scoring ile devam eder
- Her provider'in free tier'i var, baslangic icin yeterli

**3. Redis (OPSIYONEL):**
```bash
# .env'ye ekle (yoksa in-memory fallback calisir)
REDIS_URL=redis://localhost:6379/0
```

**4. SSE Hunt Stream:**
- Otomatik calisir, ek yapilandirma gerekmez
- Frontend'de `/hunt` sayfasindan av baslatinca real-time progress gorursun
- Teknik: `EventSource(/api/v1/hunt/stream/{product_id}?token=jwt)`

#### Yeni Kullanici Akisi

```
1. Login → Dashboard
2. Onboarding'de urun anlat → AI ICP analiz
3. /hunt sayfasindan av baslat → SSE ile canli progress gor
4. /leads sayfasinda bulunan lead'lere tıkla
5. Lead detayinda "Digital Dossier" linki → /leads/{id}/footprint
6. "Scan Footprint" → 121 platformda tarama (10-30 sn)
7. Sonuclari gor: hangi platformlarda var, footprint score, kategori
8. "Enrich" butonu → Harici API'lerle zenginlestir (email, title, technographics)
9. Zenginlestirilmis lead → Mesaj uret → Kampanyaya ekle
```

### 10.4 Yeni Dosyalar Ozeti

| Dosya | Satir | Aciklama |
|-------|-------|----------|
| `services/footprint_scanner.py` | ~340 | Async 121 platform tarama motoru |
| `services/lead_enrichment_api.py` | ~270 | 5 harici API entegrasyonu |
| `services/enrichment_pipeline.py` | ~215 | 4 adimli orchestration |
| `services/event_bus.py` | ~80 | Redis/in-memory SSE event bus |
| `api/v1/footprint.py` | ~300 | 6 API endpoint |
| `schemas/footprint.py` | ~60 | Pydantic schemalar |
| `data/sites.json` | ~850 | 121 platform veritabani |
| `core/redis.py` | ~50 | Redis connection pool |
| `core/rate_limiter.py` | ~200 | Redis-backed rate limiter |
| `hooks/useHuntStream.ts` | ~160 | SSE React hook |
| `leads/[id]/footprint/page.tsx` | ~320 | Digital Dossier UI |
| `tests/test_footprint_scanner.py` | ~80 | Scanner testleri |
| `tests/test_enrichment_pipeline.py` | ~90 | Pipeline testleri |
| `tests/test_health_endpoint.py` | ~60 | Health check testleri |

### 10.5 Test Durumu

```
159 test PASSED (13 dosya, 70 saniye)
Frontend build: BASARILI (0 TypeScript hatasi)
```

---

alınan notlar:
springboot (web tabanlı kurumsal projeler)
teknik mimari araştırılacak, backend framework için security en uygunu, llm modelinde en uygun, database postgrsql, webscraping için cloudflarein teknolojisi araştır, frontend için öncelik görüntü değil kullanım kolaylığı, security bizim için önemli çünkü bu uygulamayı pazarlamak için ilk hedefimiz kurumsal şirketler olacağından uygulama kurumsal olmalı, tailwind kalıyor, auth kısmı için jwt token, daha güvenlisi varsa öner. maliyeti göz önünde bulundurarak, mesela normalde api ile bi model çekip bu işleri ona mı yaptırmak mantıklı, yoksa bir modeli gömüp uygulamayla onun öyle mi çalışması mı mantıklı. kurumsallığı göz önünde bulundur. uygulamanın patlamamsı için sınırlamalar,