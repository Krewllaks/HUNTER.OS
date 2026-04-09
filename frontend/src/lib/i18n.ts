/**
 * HUNTER.OS - i18n (Turkish / English)
 * Lightweight translation system with React integration.
 */

export type Locale = "tr" | "en" | "de" | "fr" | "es";

export const LOCALE_LABELS: Record<Locale, string> = {
  tr: "Türkçe",
  en: "English",
  de: "Deutsch",
  fr: "Français",
  es: "Español",
};

const translations: Record<string, Partial<Record<Locale, string>>> = {
  // ── Navigation ───────────────────────────────────
  "nav.dashboard": { tr: "Panel", en: "Dashboard", de: "Dashboard", fr: "Tableau de bord", es: "Panel" },
  "nav.products": { tr: "Ürünler", en: "Products", de: "Produkte", fr: "Produits", es: "Productos" },
  "nav.hunt": { tr: "Av", en: "Hunt", de: "Suche", fr: "Chasse", es: "Caza" },
  "nav.leads": { tr: "Potansiyel Müşteriler", en: "Leads", de: "Leads", fr: "Prospects", es: "Prospectos" },
  "nav.campaigns": { tr: "Kampanyalar", en: "Campaigns", de: "Kampagnen", fr: "Campagnes", es: "Campañas" },
  "nav.inbox": { tr: "Gelen Kutusu", en: "Inbox", de: "Posteingang", fr: "Boîte de réception", es: "Bandeja" },
  "nav.analytics": { tr: "Analitik", en: "Analytics", de: "Analytik", fr: "Analytique", es: "Analítica" },
  "nav.accounts": { tr: "Hesaplar", en: "Accounts", de: "Konten", fr: "Comptes", es: "Cuentas" },
  "nav.settings": { tr: "Ayarlar", en: "Settings", de: "Einstellungen", fr: "Paramètres", es: "Ajustes" },
  "nav.pricing": { tr: "Fiyatlandırma", en: "Pricing", de: "Preise", fr: "Tarifs", es: "Precios" },

  // ── Common ───────────────────────────────────────
  "common.save": { tr: "Kaydet", en: "Save", de: "Speichern", fr: "Enregistrer", es: "Guardar" },
  "common.cancel": { tr: "İptal", en: "Cancel", de: "Abbrechen", fr: "Annuler", es: "Cancelar" },
  "common.delete": { tr: "Sil", en: "Delete", de: "Löschen", fr: "Supprimer", es: "Eliminar" },
  "common.edit": { tr: "Düzenle", en: "Edit", de: "Bearbeiten", fr: "Modifier", es: "Editar" },
  "common.create": { tr: "Oluştur", en: "Create", de: "Erstellen", fr: "Créer", es: "Crear" },
  "common.search": { tr: "Ara...", en: "Search...", de: "Suche...", fr: "Rechercher...", es: "Buscar..." },
  "common.loading": { tr: "Yükleniyor...", en: "Loading...", de: "Laden...", fr: "Chargement...", es: "Cargando..." },
  "common.noData": { tr: "Veri bulunamadı", en: "No data found", de: "Keine Daten", fr: "Aucune donnée", es: "Sin datos" },
  "common.actions": { tr: "İşlemler", en: "Actions", de: "Aktionen", fr: "Actions", es: "Acciones" },
  "common.status": { tr: "Durum", en: "Status", de: "Status", fr: "Statut", es: "Estado" },
  "common.name": { tr: "İsim", en: "Name", de: "Name", fr: "Nom", es: "Nombre" },
  "common.email": { tr: "E-posta", en: "Email", de: "E-Mail", fr: "E-mail", es: "Correo" },
  "common.company": { tr: "Şirket", en: "Company", de: "Unternehmen", fr: "Entreprise", es: "Empresa" },
  "common.score": { tr: "Puan", en: "Score", de: "Punktzahl", fr: "Score", es: "Puntuación" },
  "common.logout": { tr: "Çıkış Yap", en: "Logout", de: "Abmelden", fr: "Déconnexion", es: "Cerrar sesión" },
  "common.free": { tr: "Ücretsiz", en: "Free", de: "Kostenlos", fr: "Gratuit", es: "Gratis" },

  // ── Auth ──────────────────────────────────────────
  "auth.login": { tr: "Giriş Yap", en: "Sign In", de: "Anmelden", fr: "Se connecter", es: "Iniciar sesión" },
  "auth.register": { tr: "Kayıt Ol", en: "Sign Up", de: "Registrieren", fr: "S'inscrire", es: "Registrarse" },
  "auth.email": { tr: "E-POSTA", en: "EMAIL", de: "E-MAIL", fr: "E-MAIL", es: "CORREO" },
  "auth.password": { tr: "ŞİFRE", en: "PASSWORD", de: "PASSWORT", fr: "MOT DE PASSE", es: "CONTRASEÑA" },
  "auth.fullName": { tr: "AD SOYAD", en: "FULL NAME", de: "VOLLSTÄNDIGER NAME", fr: "NOM COMPLET", es: "NOMBRE COMPLETO" },
  "auth.noAccount": { tr: "Hesabınız yok mu?", en: "Don't have an account?", de: "Noch kein Konto?", fr: "Pas encore de compte?", es: "¿No tienes cuenta?" },
  "auth.hasAccount": { tr: "Zaten hesabınız var mı?", en: "Already have an account?", de: "Bereits ein Konto?", fr: "Déjà un compte?", es: "¿Ya tienes cuenta?" },
  "auth.createOne": { tr: "Oluşturun", en: "Create one", de: "Erstellen", fr: "Créer un", es: "Crear una" },
  "auth.signingIn": { tr: "Giriş yapılıyor...", en: "Signing in...", de: "Anmeldung...", fr: "Connexion...", es: "Iniciando sesión..." },

  // ── Dashboard ────────────────────────────────────
  "dashboard.title": { tr: "Komuta Merkezi", en: "Command Center" },
  "dashboard.totalLeads": { tr: "Toplam Lead", en: "Total Leads" },
  "dashboard.contacted": { tr: "Ulaşılan", en: "Contacted" },
  "dashboard.replied": { tr: "Cevaplayan", en: "Replied" },
  "dashboard.meetings": { tr: "Toplantı", en: "Meetings" },
  "dashboard.replyRate": { tr: "Cevap Oranı", en: "Reply Rate" },
  "dashboard.activeCampaigns": { tr: "Aktif Kampanya", en: "Active Campaigns" },
  "dashboard.hotLeads": { tr: "Sıcak Lead'ler", en: "Hot Leads" },
  "dashboard.quickActions": { tr: "Hızlı İşlemler", en: "Quick Actions" },
  "dashboard.startHunt": { tr: "Yeni Av Başlat", en: "Start New Hunt" },
  "dashboard.createCampaign": { tr: "Kampanya Oluştur", en: "Create Campaign" },

  // ── Products ─────────────────────────────────────
  "products.title": { tr: "Ürünleriniz", en: "Your Products" },
  "products.new": { tr: "Yeni Ürün Ekle", en: "Add New Product" },
  "products.describe": { tr: "Ürününüzü anlatın", en: "Describe your product" },
  "products.subtitle": { tr: "Ürününüzü tanımlayın, AI ideal müşterilerinizi bulsun.", en: "Define your product and let AI find your ideal customers." },
  "products.analyzing": { tr: "AI analiz ediyor...", en: "AI analyzing..." },
  "products.startHunt": { tr: "Avı Başlat", en: "Start Hunting" },
  "products.hunting": { tr: "Av devam ediyor...", en: "Hunting in progress..." },
  "products.nameLabel": { tr: "Ürün Adı", en: "Product Name" },
  "products.namePlaceholder": { tr: "Ürün veya hizmet adı", en: "Product or service name" },
  "products.descLabel": { tr: "Detaylı Açıklama", en: "Detailed Description" },
  "products.descPlaceholder": { tr: "Ürününüzü mümkün olduğunca detaylı anlatın...", en: "Describe your product in as much detail as possible..." },
  "products.analyzeBtn": { tr: "AI ile Analiz Et", en: "Analyze with AI" },
  "products.draft": { tr: "TASLAK", en: "DRAFT" },
  "products.analyzed": { tr: "ANALİZ EDİLDİ", en: "ANALYZED" },
  "products.huntingStatus": { tr: "AV DEVAM EDİYOR", en: "HUNTING" },

  // ── Leads ────────────────────────────────────────
  "leads.title": { tr: "Potansiyel Müşteriler", en: "Leads" },
  "leads.generateMessage": { tr: "Mesaj Oluştur", en: "Generate Message" },
  "leads.batchGenerate": { tr: "Toplu Mesaj Oluştur", en: "Bulk Generate" },
  "leads.viewProfile": { tr: "Profili Gör", en: "View Profile" },
  "leads.intentScore": { tr: "Niyet Puanı", en: "Intent Score" },
  "leads.source": { tr: "Kaynak", en: "Source" },

  // ── Campaigns ────────────────────────────────────
  "campaigns.title": { tr: "Kampanyalar", en: "Campaigns" },
  "campaigns.subtitle": { tr: "Çok kanallı ulaşım iş akışlarını yönetin", en: "Manage omnichannel outreach workflows" },
  "campaigns.new": { tr: "Yeni Kampanya", en: "New Campaign" },
  "campaigns.activate": { tr: "Aktifleştir", en: "Activate" },
  "campaigns.pause": { tr: "Duraklat", en: "Pause" },
  "campaigns.workflow": { tr: "İş Akışı", en: "Workflow" },
  "campaigns.noData": { tr: "Henüz kampanya yok", en: "No campaigns yet" },
  "campaigns.noDataDesc": { tr: "İlk kampanyanızı oluşturup lead'lere ulaşmaya başlayın.", en: "Create your first campaign and start reaching out to leads." },
  "campaigns.leads": { tr: "LEAD", en: "LEADS" },
  "campaigns.contacted": { tr: "ULAŞILAN", en: "CONTACTED" },
  "campaigns.replied": { tr: "CEVAPLAYAN", en: "REPLIED" },
  "campaigns.meetings": { tr: "TOPLANTI", en: "MEETINGS" },
  "campaigns.replyRate": { tr: "CEVAP ORANI", en: "REPLY RATE" },
  "campaigns.name": { tr: "Kampanya Adı", en: "Campaign Name" },
  "campaigns.namePlaceholder": { tr: "Örn: Q1 Ajans Ulaşımı", en: "E.g. Q1 Agency Outreach" },
  "campaigns.description": { tr: "Açıklama", en: "Description" },
  "campaigns.descPlaceholder": { tr: "Kampanyanızı kısaca açıklayın...", en: "Briefly describe your campaign..." },
  "campaigns.tags": { tr: "Etiketler (virgülle ayırın)", en: "Tags (comma separated)" },
  "campaigns.tagsPlaceholder": { tr: "ajans, saas, marketing", en: "agency, saas, marketing" },
  "campaigns.createBtn": { tr: "Kampanya Oluştur", en: "Create Campaign" },

  // ── Inbox ────────────────────────────────────────
  "inbox.title": { tr: "Gelen Kutusu", en: "Inbox" },
  "inbox.all": { tr: "Tümü", en: "All" },
  "inbox.unread": { tr: "Okunmamış", en: "Unread" },
  "inbox.inbound": { tr: "Gelen", en: "Inbound" },
  "inbox.reply": { tr: "Cevapla", en: "Reply" },

  // ── Billing ──────────────────────────────────────
  "billing.trial": { tr: "Deneme", en: "Trial" },
  "billing.pro": { tr: "Profesyonel", en: "Pro" },
  "billing.enterprise": { tr: "Kurumsal", en: "Enterprise" },
  "billing.upgrade": { tr: "Planı Yükselt", en: "Upgrade Plan" },
  "billing.trialEnds": { tr: "Deneme süreniz bitiyor", en: "Trial ending" },
  "billing.daysLeft": { tr: "gün kaldı", en: "days left" },
  "billing.limitReached": { tr: "Limit aşıldı", en: "Limit reached" },
  "billing.perMonth": { tr: "/ay", en: "/mo" },
  "billing.unlimited": { tr: "Sınırsız", en: "Unlimited" },
  "billing.currentPlan": { tr: "Mevcut Plan", en: "Current Plan" },
  "billing.missedLeads": { tr: "Kaçırdığınız potansiyel müşteriler", en: "Leads you're missing" },
  "billing.title": { tr: "Fiyatlandırma", en: "Pricing" },
  "billing.subtitle": { tr: "Deneme ile başlayın, büyüdükçe ölçekleyin.", en: "Start with trial, scale as you grow." },
  "billing.mostPopular": { tr: "EN POPÜLER", en: "MOST POPULAR" },
  "billing.startFree": { tr: "Başla", en: "Start Free" },
  "billing.upgradeBtn": { tr: "Yükselt", en: "Upgrade" },
  "billing.featureComparison": { tr: "Özellik Karşılaştırması", en: "Feature Comparison" },
  "billing.feature": { tr: "Özellik", en: "Feature" },
  "billing.leadDiscovery": { tr: "Lead Keşfi", en: "Lead Discovery" },
  "billing.personalizedMsg": { tr: "Kişiselleştirilmiş Mesaj", en: "Personalized Messages" },
  "billing.productCount": { tr: "Ürün Sayısı", en: "Products" },
  "billing.linkedinAuto": { tr: "LinkedIn Otomasyon", en: "LinkedIn Automation" },
  "billing.emailSend": { tr: "Email Gönderim", en: "Email Sending" },
  "billing.analyticsLabel": { tr: "Analitik", en: "Analytics" },
  "billing.teamMembers": { tr: "Takım Üyeleri", en: "Team Members" },
  "billing.apiAccess": { tr: "API Erişimi", en: "API Access" },
  "billing.basic": { tr: "Temel", en: "Basic" },
  "billing.detailed": { tr: "Detaylı", en: "Detailed" },
  "billing.fullExport": { tr: "Tam + Export", en: "Full + Export" },
  "billing.person": { tr: "kişi", en: "members" },

  // ── Settings ─────────────────────────────────────
  "settings.title": { tr: "Ayarlar", en: "Settings" },
  "settings.language": { tr: "Dil", en: "Language" },
  "settings.profile": { tr: "Profil", en: "Profile" },
  "settings.apiKeys": { tr: "API Anahtarları", en: "API Keys" },
  "settings.notifications": { tr: "Bildirimler", en: "Notifications" },

  // ── Landing Page ────────────────────────────────
  "landing.hero.title1": { tr: "Otonom", en: "The Autonomous" },
  "landing.hero.title2": { tr: "Satış Avcısı.", en: "Sales Hunter." },
  "landing.hero.subtitle": {
    tr: "Potansiyel müşterileri keşfetmek, araştırmak, puanlamak ve kişiselleştirilmiş ulaşım yapmak için AI ajanları dağıtın.",
    en: "Deploy AI agents to discover, research, score, and personalize outreach at scale.",
  },
  "landing.hero.cta1": { tr: "İlk Ajanınızı Dağıtın", en: "Deploy Your First Agent" },
  "landing.hero.cta2": { tr: "Platform Demosunu İzle", en: "Watch Platform Demo" },
  "landing.ares.poweredBy": { tr: "DESTEKLEYEN", en: "POWERED BY" },
  "landing.ares.title": { tr: "ARES Motoru", en: "The ARES Engine" },
  "landing.ares.subtitle": {
    tr: "Dört otonom aşama, ham web verisini kişiselleştirilmiş, yüksek dönüşümlü ulaşıma dönüştürür.",
    en: "Four autonomous stages transform raw web data into personalized, high-converting outreach.",
  },
  "landing.ares.discovery": { tr: "Keşif", en: "Discovery" },
  "landing.ares.discoveryDesc": {
    tr: "AI ajanları gelişmiş arama stratejileri ve ICP eşleştirmesi kullanarak ideal müşterilerinizi web'de otonom olarak bulur.",
    en: "AI agents autonomously scan the web to find your ideal customers using advanced search strategies and ICP matching.",
  },
  "landing.ares.research": { tr: "Araştırma", en: "Research" },
  "landing.ares.researchDesc": {
    tr: "Her potansiyel müşteri için dijital ayak izlerinin derinlemesine analizi — sosyal paylaşımlar, işe alım sinyalleri, teknografik veriler.",
    en: "Deep analysis of digital footprints — social posts, hiring signals, technographics, and website activity for each prospect.",
  },
  "landing.ares.scoring": { tr: "Puanlama", en: "Scoring" },
  "landing.ares.scoringDesc": {
    tr: "Çok boyutlu niyet puanlama: ICP uyumu, etkileşim sinyalleri, zamanlama kalıpları ve satın alma komitesi analizi.",
    en: "Multi-dimensional intent scoring combines ICP fit, engagement signals, timing patterns, and buying committee analysis.",
  },
  "landing.ares.personalization": { tr: "Kişiselleştirme", en: "Personalization" },
  "landing.ares.personalizationDesc": {
    tr: "6 katmanlı kişiselleştirme motoru, her potansiyel müşterinin dijital varlığından gerçek bağlam referans alan insan kalitesinde mesajlar üretir.",
    en: "6-layer personalization engine crafts human-quality messages referencing real context from each prospect's digital presence.",
  },
  "landing.pricing.title": { tr: "Şeffaf Fiyatlandırma", en: "Transparent Pricing" },
  "landing.pricing.subtitle": {
    tr: "Otonom satış motorunuzu öngörülebilir şekilde ölçekleyin.",
    en: "Scale your autonomous sales engine predictably.",
  },
  "landing.footer.rights": {
    tr: "© 2026 HUNTER.OS Inc. Tüm hakları saklıdır.",
    en: "© 2026 HUNTER.OS Inc. All rights reserved.",
  },
  "landing.nav.workflow": { tr: "İş Akışı", en: "Workflow" },
  "landing.nav.requestDemo": { tr: "Demo Talep Et", en: "Request Demo" },

  // ── Precision Dashboard ─────────────────────────
  "precision.title": { tr: "Hassas Panel", en: "Precision Dashboard" },
  "precision.systemActive": { tr: "SİSTEM DURUMU: AKTİF", en: "SYSTEM STATUS: ACTIVE" },
  "precision.growthProfit": { tr: "BÜYÜME KÂRI", en: "GROWTH PROFIT" },
  "precision.leadCost": { tr: "LEAD MALİYETİ", en: "LEAD COST" },
  "precision.activeHunts": { tr: "AKTİF AVLAR", en: "ACTIVE HUNTS" },
  "precision.totalTargets": { tr: "TOPLAM HEDEF", en: "TOTAL TARGETS" },
  "precision.currentCampaigns": { tr: "AKTİF KAMPANYA", en: "CAMPAIGNS" },
  "precision.accuracy": { tr: "DOĞRULUK", en: "ACCURACY" },
  "precision.leadVelocity": { tr: "LEAD HIZI", en: "LEAD VELOCITY" },
  "precision.conversionFunnel": { tr: "DÖNÜŞÜM HUNİSİ", en: "CONVERSION FUNNEL" },
  "precision.discovery": { tr: "Keşif", en: "Discovery" },
  "precision.research": { tr: "Araştırma", en: "Research" },
  "precision.outreach": { tr: "Ulaşım", en: "Outreach" },
  "precision.reply": { tr: "Cevap", en: "Reply" },
  "precision.growthAnalytics": { tr: "BÜYÜME ANALİTİĞİ", en: "GROWTH ANALYTICS" },
  "precision.growthDesc": { tr: "Son 12 aylık performans trendi", en: "Last 12 months performance trend" },
  "precision.hotLeads": { tr: "Sıcak Lead'ler & Duygu Analizi", en: "Hot Leads & Sentiment" },
  "precision.newCampaign": { tr: "Yeni Kampanya", en: "New Campaign" },

  // ── Pricing Page (New Model) ────────────────────
  "pricing.transparent": { tr: "Şeffaf Fiyatlandırma", en: "Transparent Pricing" },
  "pricing.scaleSubtitle": {
    tr: "Otonom satış motorunuzu öngörülebilir şekilde ölçekleyin.",
    en: "Scale your autonomous sales engine predictably.",
  },
  "pricing.annualPrepaid": { tr: "Yıllık Ön Ödeme %20 İNDİRİM", en: "Annual Prepaid 20% OFF" },
  "pricing.annualContract": { tr: "Yıllık Sözleşme", en: "Annual Contract" },
  "pricing.quarterly": { tr: "3 Aylık Fatura", en: "Quarterly Bill" },
  "pricing.growth": { tr: "BÜYÜME", en: "GROWTH" },
  "pricing.committedSpend": { tr: "TAHSİS EDİLEN HARCAMA", en: "COMMITTED SPEND" },
  "pricing.enterprise": { tr: "Kurumsal", en: "Enterprise" },
  "pricing.startPipeline": { tr: "Pipeline Oluşturmaya Başla", en: "Start Building Pipeline" },
  "pricing.contactSales": { tr: "Satış Ekibiyle İletişim", en: "Contact Sales" },
  "pricing.save": { tr: "Yılda $840 tasarruf", en: "Save $840/year" },
};

let currentLocale: Locale = "tr";

// Event system for reactive updates
type LocaleListener = (locale: Locale) => void;
const listeners: Set<LocaleListener> = new Set();

export function onLocaleChange(fn: LocaleListener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function setLocale(locale: Locale) {
  currentLocale = locale;
  if (typeof window !== "undefined") {
    localStorage.setItem("hunter_locale", locale);
  }
  // Notify all listeners
  listeners.forEach((fn) => fn(locale));
}

const VALID_LOCALES: Locale[] = ["tr", "en", "de", "fr", "es"];

export function getLocale(): Locale {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("hunter_locale") as Locale;
    if (VALID_LOCALES.includes(saved)) {
      currentLocale = saved;
    }
  }
  return currentLocale;
}

export function t(key: string): string {
  const entry = translations[key];
  if (!entry) return key;
  return entry[currentLocale] || entry["en"] || key;
}
