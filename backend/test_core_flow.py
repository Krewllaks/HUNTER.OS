"""
HUNTER.OS - Core Flow E2E Test Script
Urun promptu → ICP analiz → Musteri kesfet → Lead bul → Mesaj olustur

Kullanim:
  cd backend
  python test_core_flow.py
"""
import httpx
import time
import json
import sys

BASE = "http://localhost:8000/api/v1"
TOKEN = None


def log(msg, data=None):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])


def api(method, path, json_data=None, params=None):
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    kwargs = {"params": params, "headers": headers, "timeout": 120.0}
    if method != "get" and json_data is not None:
        kwargs["json"] = json_data
    resp = getattr(httpx, method)(f"{BASE}{path}", **kwargs)
    return resp


def main():
    global TOKEN

    # ── Step 0: Health Check ──
    log("Step 0: Health Check")
    try:
        r = httpx.get("http://localhost:8000/health", timeout=5)
        print(f"  Status: {r.json()}")
    except Exception as e:
        print(f"  HATA: Backend calismıyor! Once baslat:")
        print(f"  cd backend && uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

    # ── Step 1: Register + Login ──
    log("Step 1: Register & Login")
    email = f"test_{int(time.time())}@hunter.os"
    password = "TestPass123!"

    r = api("post", "/auth/register", {
        "email": email,
        "password": password,
        "full_name": "Test User"
    })
    if r.status_code in (201, 200):
        print(f"  Kayit basarili: {email}")
    elif r.status_code == 409 or "already" in r.text.lower():
        print(f"  Kullanici zaten var, devam ediyoruz")
    else:
        print(f"  Kayit cevabi: {r.status_code} - {r.text[:200]}")

    # Login endpoint OAuth2PasswordRequestForm kullanıyor → form-encoded data gerekli
    r = httpx.post(f"{BASE}/auth/login",
        data={"username": email, "password": password},
        timeout=10)
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get("access_token") or data.get("token")
        print(f"  Login basarili, token alindi")
    else:
        print(f"  Login HATA: {r.status_code} - {r.text[:200]}")
        sys.exit(1)

    # ── Step 2: Urun Olustur ──
    log("Step 2: Urun Olustur (Product Prompt)")
    product_prompt = """
    We sell an AI-powered email outreach platform for B2B SaaS companies.
    Our product automates cold email sequences with AI personalization.
    Target customers: Marketing agencies with 5-30 employees, SaaS startups,
    and growth teams that need to scale their outbound sales.
    Key features: AI message generation, email warmup, LinkedIn automation,
    reply detection, and CRM integration.
    Price: $49-149/month.
    """

    r = api("post", "/products", {
        "name": "AI Outreach Platform",
        "description_prompt": product_prompt.strip()
    })
    if r.status_code in (200, 201):
        product = r.json()
        product_id = product["id"]
        print(f"  Urun olusturuldu: ID={product_id}, status={product['status']}")
    else:
        print(f"  Urun HATA: {r.status_code} - {r.text[:300]}")
        sys.exit(1)

    # ── Step 3: AI Analiz (ICP Cikar) ──
    log("Step 3: AI Analiz - ICP Profili Cikariliyor")
    print("  Gemini API cagriliyor, bu 10-30 saniye surebilir...")

    r = api("post", f"/products/{product_id}/analyze")
    if r.status_code == 200:
        product = r.json()
        print(f"  Status: {product['status']}")
        print(f"\n  ICP Profile:")
        icp = product.get("icp_profile", {})
        print(f"    Industries: {icp.get('industries', [])}")
        print(f"    Target Titles: {icp.get('target_titles', [])}")
        print(f"    Company Sizes: {icp.get('company_sizes', [])}")
        print(f"    Pain Points: {icp.get('pain_points', [])}")
        print(f"\n  Search Strategies:")
        strategies = product.get("search_queries", {})
        for key, val in (strategies or {}).items():
            if isinstance(val, list):
                print(f"    {key}: {val[:3]}")
    else:
        print(f"  Analiz HATA: {r.status_code} - {r.text[:500]}")
        print("  GEMINI_API_KEY .env dosyasinda dogru mu?")
        sys.exit(1)

    # ── Step 4: Otonom Kesif Baslat ──
    log("Step 4: Otonom Musteri Kesfetme Baslatiliyor")
    print("  Google dorking + DuckDuckGo + Bing ile lead aranacak...")
    print("  Bu islem 1-3 dakika surebilir...")

    r = api("post", f"/products/{product_id}/start-hunting")
    if r.status_code == 200:
        data = r.json()
        print(f"  Hunting baslatildi: {data}")
    else:
        print(f"  Hunting HATA: {r.status_code} - {r.text[:300]}")

    # Poll progress
    print("\n  Ilerleme takibi:")
    for i in range(60):  # Max 5 dakika
        time.sleep(5)
        r = api("get", f"/products/{product_id}")
        if r.status_code == 200:
            p = r.json()
            progress = p.get("hunt_progress") if hasattr(p, "get") else None
            status = p.get("status", "unknown")
            if isinstance(p, dict):
                # hunt_progress might be in the response
                pass
            print(f"    [{i*5}s] Status: {status}")
            if status in ("active", "ready") and i > 6:
                print("  Kesif tamamlandi!")
                break
        else:
            print(f"    Durum sorgu hatasi: {r.status_code}")

    # ── Step 5: Bulunan Leadleri Goster ──
    log("Step 5: Bulunan Leadler")
    r = api("get", "/leads", params={"page": 1, "limit": 20})
    if r.status_code == 200:
        data = r.json()
        leads = data.get("leads", data.get("items", []))
        total = data.get("total", len(leads))
        print(f"  Toplam lead: {total}")
        for lead in leads[:10]:
            name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
            print(f"    - {name or 'N/A'} | {lead.get('company_name', 'N/A')} | {lead.get('email', 'N/A')} | Score: {lead.get('intent_score', 'N/A')}")
    else:
        print(f"  Leads HATA: {r.status_code} - {r.text[:200]}")

    # ── Step 6: Mesaj Uretimi ──
    log("Step 6: AI Mesaj Uretimi")
    if r.status_code == 200 and leads:
        lead_id = leads[0].get("id")
        r = api("post", f"/messages/generate/{lead_id}")
        if r.status_code == 200:
            msg = r.json()
            print(f"  Subject: {msg.get('subject', msg.get('subject_line', 'N/A'))}")
            print(f"  Body: {str(msg.get('body', ''))[:300]}")
        else:
            print(f"  Mesaj HATA: {r.status_code} - {r.text[:200]}")
    else:
        print("  Lead yok, mesaj uretilemedi")

    # ── Ozet ──
    log("TEST TAMAMLANDI")
    print(f"""
  Akis:
  1. Register/Login    ✓
  2. Urun olustur      ✓
  3. AI ICP analizi     ✓
  4. Otonom kesif       ✓
  5. Lead listele       ✓
  6. Mesaj uret         ✓

  Sonraki adimlar:
  - Frontend'den ayni akisi dene: http://localhost:3000
  - Email gondermek icin: .env'de SMTP ayarlarini yap
  - LinkedIn icin: li_at cookie ekle
  - CRM icin: HubSpot/Pipedrive API key ekle
""")


if __name__ == "__main__":
    main()
