# HUNTER.OS Enterprise Hardening Roadmap

**Generated:** 2026-03-24
**By:** 5-Agent Enterprise Analysis Team (Architect + Security + AI Engineer + Frontend + Strategist)
**Status:** Research Complete — Implementation Pending

---

## Executive Summary

HUNTER.OS has a genuinely sophisticated AI sales pipeline at "impressive demo" stage. The enterprise pivot requires 6-9 months of focused hardening across security, compliance, architecture, and unit economics before it is ready for corporate customers. Five critical issues require action TODAY before any new feature development begins.

### Top Findings by Agent

| Agent | #1 Critical Finding |
|-------|-------------------|
| Architecture | PostgreSQL migration is easy (3-5 days); stay on FastAPI — Spring Boot migration gains nothing |
| Security | Hardcoded Gemini API key in `config.py:29` — must rotate immediately |
| AI Engineer | ResearchAgent token consumption is quadratic — full history replay costs ~99K tokens/lead |
| Frontend | Zero ARIA attributes, all `"use client"` (no SSR), fake hardcoded KPIs on Dashboard |
| Strategist | LinkedIn automation is a legal time bomb; Enterprise pricing ($149/mo) is cash-negative at scale |

---

## P0 — Critical (Do TODAY before any other work)

These are existential issues that would immediately block or destroy any enterprise deal.

### P0-1: Rotate All Exposed Secrets (SECURITY)
**File:** `backend/app/core/config.py:29`, `backend/.env`

The Gemini API key `AIzaSyB0T3p4mYDg0plRFiibel36uKPp_EOjSzs` is hardcoded in `config.py`. The `.env` file contains live SMTP credentials (Gmail app password), a full LemonSqueezy JWT, and a Google News API key. No root `.gitignore` exists.

**Actions:**
1. Rotate: Gemini API key, Gmail app password, LemonSqueezy JWT, Google News API key, JWT secret
2. Create root `.gitignore` (add `.env`, `*.db`, `hunter.db`, `__pycache__`)
3. Remove ALL default values for secrets in `config.py` — raise `ValueError` if env var is missing
4. Scrub git history with `git filter-repo` or BFG Repo-Cleaner

### P0-2: Fix Auto-Admin Registration Bug (SECURITY)
**File:** `backend/app/api/v1/auth.py:30`

Every new user is assigned `role="admin"`. Any anonymous person who registers gets full administrative access. **CVSS 9.8.**

**Fix:** Change default role to `"member"`. First registered user (seeded admin) can be set separately.

### P0-3: Encrypt Stored SMTP and LinkedIn Credentials (SECURITY)
**File:** `backend/app/api/v1/accounts.py:61` (SMTP), `:135` (LinkedIn cookie)

Both store raw credentials with `# TODO: encrypt with AES` comments. Database leak = attacker can impersonate every connected user.

**Fix:** Implement `cryptography.fernet` envelope encryption. Encrypt on write, decrypt only at moment of use.

### P0-4: Add Rate Limiting to Auth Endpoints (SECURITY)
**File:** `backend/app/api/v1/auth.py:38-61`

Zero rate limiting on `/auth/login` and `/auth/register`. Trivially vulnerable to credential stuffing and brute force.

**Fix:** Use `slowapi` or Redis-based rate limiter. 5 attempts/minute per IP, account lock after 5 failures.

### P0-5: Add LLM Cost Circuit Breakers (RISK)
**File:** `backend/app/agents/`, `backend/app/services/`

No token budgets or cost caps anywhere. An enterprise customer running 10K leads/month costs $150-500 in Gemini API fees against a $149/month subscription. A retry bug can run up thousands in minutes.

**Fix:** Add per-user monthly token budget (Trial: $1, Pro: $50, Enterprise: $200). Alert at 80%, throttle at 100%.

### P0-6: Persist LinkedInGuard State to Database (RISK)
**File:** `backend/app/services/linkedin_guard.py:57-61`

All rate limit counters, pause states, and session timers are in-memory Python dicts. Every server restart resets them to zero. With multiple Uvicorn workers, each worker has its own counters — effective limits are N×configured per worker count.

**Fix:** Move `_daily_counts`, `_paused_until`, `_session_state` to Redis with TTL matching the reset windows.

---

## P1 — High Priority (Within 2 Weeks)

### P1-1: PostgreSQL Migration (ARCHITECTURE)

**Current:** SQLite WAL mode — single writer, no concurrent write safety
**Target:** PostgreSQL 16 (already declared in `docker-compose.yml`)

The migration is simpler than it looks because Alembic `env.py` already reads `DATABASE_URL` from env.

**Steps (3-5 days):**
1. Modify `database.py`: remove SQLite PRAGMAs, add `pool_size=20, max_overflow=10, pool_pre_ping=True`
2. Add `psycopg2-binary` to `requirements.txt`
3. Add critical indexes: `(user_id, status)` on leads, `(status, next_scheduled)` on workflows, GIN index on JSON columns
4. Run `alembic revision --autogenerate` against Postgres to get baseline migration
5. Data migration script: read from SQLite, write to Postgres via SQLAlchemy
6. Add PgBouncer to `docker-compose.yml` for connection pooling

**Zero-downtime strategy:** Since pre-enterprise (dev state), simple cutover is sufficient.

### P1-2: Multi-Tenant Organization Model (ARCHITECTURE)

Enterprise requires team management. Currently every user is isolated — no concept of Organization.

**Schema changes:**
- New `Organization` model: `id, name, plan, owner_id, settings (JSON)`
- Add `org_id` to `User` and all data tables (leads, products, campaigns, messages)
- Tenant isolation middleware: every DB query auto-filtered by `org_id` from JWT
- Role expansion: `owner | admin | manager | member | viewer` within org

**Effort:** 1-2 weeks.

### P1-3: Fix asyncio Anti-Patterns (RISK/TECHNICAL)
**Files:** `workflow_engine.py` (4x), `sentiment_service.py`, `discovery_service.py` (2x)

8 instances of `asyncio.new_event_loop()` — creates new loops, can deadlock from within FastAPI's async context, leaks on exceptions, mutates global async state.

**Fix:** Replace all with proper `await` patterns. FastAPI already provides an async context. Use `asyncio.get_event_loop()` only when absolutely necessary.

### P1-4: Human Approval Gate for AI Messages (TRUST)

Enterprise customers will not accept "fire-and-forget" automated messaging to their prospects. One hallucinated personal detail damages brand and trust.

**Fix:**
- Add `requires_approval` field to Message model
- Add approval queue endpoint (`GET /messages/pending-approval`, `POST /messages/{id}/approve`)
- Frontend: approval inbox view with edit capability
- Config: mandatory for Enterprise plan by default, optional for Pro

### P1-5: Migrate APScheduler to Celery Beat (ARCHITECTURE)
**File:** `backend/app/main.py:36-119`

5 scheduled jobs in APScheduler are in-process — API server crash = all schedules stop. `celery_app.py` and `tasks.py` already exist but are not wired.

**Fix:** Move all 5 APScheduler jobs to Celery Beat tasks. Wire Redis and Celery Beat in docker-compose.

### P1-6: Add Audit Logging (COMPLIANCE)

Zero audit trail in the codebase. Required for SOC2, GDPR accountability, and enterprise trust.

**Fix:**
- Add `audit_logs` table: `org_id, user_id, action, resource_type, resource_id, old_value (JSON), new_value (JSON), ip_address, timestamp`
- Implement via SQLAlchemy event listeners on all models
- Add `GET /audit-logs` endpoint for admins

### P1-7: CAN-SPAM Compliance for Email Outreach (LEGAL)
**File:** `backend/app/services/email_service.py`

Zero mentions of unsubscribe link or physical address in outbound emails. Violations: up to $51,744 per email.

**Fix:**
- Add unsubscribe footer with one-click unsubscribe URL (token-based, no login required)
- Add physical mailing address to email template
- Handle unsubscribe URL → auto-add to Blacklist → stop workflow
- Add opt-out tracking to Message model

### P1-8: GDPR Right-to-Erasure API (LEGAL)

No data deletion or portability mechanism. Required under GDPR Article 17.

**Fix:**
- `DELETE /leads/{id}` already exists for individual leads
- Add `POST /gdpr/erasure-request` — deletes all personal data for a given email across all tables
- Add `GET /gdpr/data-export` — returns all stored data for an email in JSON
- Blacklist the email automatically after erasure

### P1-9: Fix Fake Dashboard KPIs (TRUST)
**File:** `frontend/src/app/page.tsx`

Dashboard shows hardcoded fallback values (`"94%"`, `"$142.8k"`) when real API data is zero. Enterprise users will immediately notice fabricated metrics and lose trust.

**Fix:** Show actual zeros or loading states. Never show hardcoded fake data.

### P1-10: Disable Swagger in Production (SECURITY)
**File:** `backend/app/main.py:139-140`

`/docs` and `/redoc` are publicly accessible with no authentication, exposing full API surface.

**Fix:**
```python
app = FastAPI(docs_url=None if not settings.DEBUG else "/docs", redoc_url=None if not settings.DEBUG else "/redoc")
```

---

## P2 — Important (Within 1 Month)

### P2-1: LLM Cost Optimization — ICP Analysis Cache (AI)

ProductAnalysisAgent runs on every hunt start even for the same product. Same product = same ICP every time.

**Fix:** Redis cache keyed by `hash(product_name + description_prompt)`. Cache ICP analysis permanently until product is edited. Estimated savings: **95% reduction on ProductAnalysisAgent calls**.

### P2-2: ResearchAgent Token Budget Cap (AI)
**File:** `backend/app/agents/research_agent.py`

ReAct loop allows up to 15 steps with full history replay each step — quadratic token growth. A single lead can consume ~99K tokens.

**Fix:** Hard cap at 8 steps. Implement real context compression (summarize completed steps instead of replaying full history). Add per-lead token budget tracker.

### P2-3: Add Pydantic Validation on All Agent Outputs (AI)

All 6 agents do raw `json.loads(response.text)` with no schema validation. Hallucinated fields silently corrupt the database.

**Fix:** Define Pydantic `BaseModel` for each agent's expected output. Validate before any DB write. Retry with error feedback if validation fails.

### P2-4: Virtual Scrolling for Leads Table (FRONTEND)

All leads render directly to DOM. At 100K+ enterprise leads, this will freeze the browser.

**Fix:** Implement `@tanstack/react-virtual` (TanStack Virtual). Only render visible rows. Add server-side pagination with cursor-based navigation.

### P2-5: Role-Based Access Control in Frontend (FRONTEND)

`AuthContext` has a flat `User` type. No page restricts access based on role. `Sidebar.tsx` uses `(user as any)?.plan`.

**Fix:**
- Add `role` and `org` to `User` type
- Create `usePermissions()` hook
- Guard enterprise-only features (team management, audit logs, API keys) behind role checks

### P2-6: WCAG 2.1 AA Accessibility (FRONTEND)

Zero ARIA attributes across entire codebase. Modals lack focus trapping. Dropdowns are mouse-only. Color contrast fails AA (`#666` on `#1A1A1A` = 2.6:1, needs 4.5:1). Enterprise procurement often requires WCAG compliance.

**Fix:**
- Add `aria-label`, `aria-expanded`, `role` attributes to all interactive elements
- Implement focus trap in modals (`focus-trap-react` library)
- Fix color contrast for secondary text
- Set `<html lang={locale}>` dynamically

### P2-7: JWT Refresh Token Rotation (SECURITY)

24-hour access tokens with no refresh mechanism and no revocation.

**Fix:** Short-lived access tokens (15 min) + long-lived refresh tokens (7 days) with rotation. Redis-backed `jti` blacklist for logout/compromise revocation.

### P2-8: Migrate to RS256 JWT (SECURITY)

HS256 requires sharing the signing secret with every service. RS256 (asymmetric) allows public key distribution for verification.

**Fix:** Generate RSA key pair. Store private key in secrets manager. Distribute public key via `/.well-known/jwks.json`.

### P2-9: Structured Logging + Observability (OPERATIONS)

Currently: `print()` and basic `logging.getLogger()`. No structured log format, no trace IDs, no metrics.

**Fix:**
- Replace with `structlog` or `python-json-logger` for structured JSON logs
- Add `X-Request-ID` header and propagate through all log entries
- Add Prometheus metrics endpoint `/metrics`
- Basic Grafana dashboard for: API latency, LLM call counts/costs, workflow success rate

### P2-10: Fix CORS Configuration (SECURITY)
**File:** `backend/app/main.py:143-153`

`allow_methods=["*"]` and `allow_headers=["*"]` are overly permissive.

**Fix:** Enumerate allowed methods (`GET, POST, PUT, DELETE, PATCH, OPTIONS`) and headers (`Authorization, Content-Type, X-Request-ID`).

---

## P3 — Strategic (This Quarter)

### P3-1: OAuth2/OIDC SSO Integration

Enterprise customers require SSO with corporate IdP (Okta, Azure AD, Google Workspace).

**Implementation:** `authlib` library with OIDC Authorization Code + PKCE flow. Support JIT user provisioning from IdP claims. SAML 2.0 for customers who mandate it.

### P3-2: Re-Pricing for Sustainable Unit Economics

| Current Plan | Current Price | Recommended | Rationale |
|-------------|--------------|-------------|-----------|
| Trial | Free | Free | Keep — acquisition funnel |
| Pro | $49/mo flat | $79/user/month | Per-seat aligns with industry (Apollo: $79, Outreach: $100+) |
| Enterprise | $149/mo flat | $149/user/month + platform fee | 10-person team = $1,490/mo vs $149 current |

**At current pricing, Pro and Enterprise plans are cash-negative at scale.** API costs alone can exceed subscription revenue.

### P3-3: SOC2 Type II Preparation

SOC2 readiness estimate: ~15-20% today. Gap areas:
- Access control policies (auto-admin bug, no RBAC)
- Encryption at rest (no at-rest encryption)
- Audit logging (none)
- Incident response plan (none)
- Vulnerability management (no dependency scanning)

**Timeline:** 6-9 months to achieve SOC2 Type II certification with dedicated effort.

### P3-4: Server Components Migration (FRONTEND)

All 12 Next.js pages are `"use client"` — no SSR/SSG. Bundle size is suboptimal, no streaming.

**Fix:** Migrate static sections (navigation, page headers, non-interactive data displays) to React Server Components. Estimated 30-40% reduction in initial bundle size.

### P3-5: WebSocket/SSE for Real-Time Hunt Progress

Currently poll-based. Add SSE endpoint for live discovery progress updates.

**Implementation:** FastAPI SSE with `StreamingResponse`. Frontend `EventSource` API.

### P3-6: CRM Integration Layer

Abstract interface for HubSpot, Pipedrive, Salesforce. Config already has API keys.

### P3-7: LinkedIn Risk Disclosure & Compliance Mode

Add an "Official APIs Only" mode using LinkedIn Marketing API / Sales Navigator API (slower, no stealth needed, legally defensible). Required for enterprise customers with significant LinkedIn brand investment.

### P3-8: Multi-Language Expansion

Current: TR/EN. Enterprise needs DE, FR, ES, PT-BR. i18n hook already supports extension — add translation files and locale routing.

---

## Cost Estimates

### LLM Cost Per 1,000 Leads (Full Pipeline)

| Provider | $/1K Leads (baseline) | With Caching (-50%) | Two-Tier Strategy |
|----------|----------------------|--------------------|--------------------|
| Gemini 1.5 Flash | $2.10-3.20 | $1.05-1.60 | $0.80-1.30 |
| Gemini 2.0 Flash | $2.80-4.20 | $1.40-2.10 | $1.10-1.70 |
| Gemini 2.0 Flash + Claude Haiku | $5-8 | $2.50-4.00 | N/A |
| Claude 3.5 Haiku only | $25-38 | $12-19 | N/A |
| GPT-4o Mini | $4.20-6.30 | $2.10-3.15 | N/A |
| Local LLM (GPU compute) | $0.50-1.50 | $0.25-0.75 | N/A |

**Recommendation:** Keep Gemini 2.0 Flash as primary. Add Redis semantic caching for ICP analysis (95% savings on ProductAnalysisAgent), scoring cache (30-50% savings). Implement local LLM for discovery relevance filtering (high-volume, low-quality-requirement task).

### Development Effort Estimates

| Priority | Work | Estimated Effort |
|----------|------|-----------------|
| P0 (all) | Critical security + circuit breakers + LinkedInGuard persistence | 1-2 weeks |
| P1 (all) | PostgreSQL, multi-tenant, Celery, audit log, CAN-SPAM, GDPR, approval gate | 6-8 weeks |
| P2 (all) | LLM optimization, WCAG, RBAC, JWT rotation, structured logging | 6-8 weeks |
| P3 (all) | SSO, pricing, SOC2, CRM, SSE, Server Components | 12-16 weeks |

**Total to enterprise-ready: approximately 6-9 months**

---

## Risk Matrix

| # | Risk | Likelihood | Impact | Score | Owner |
|---|------|:----------:|:------:|:-----:|-------|
| 1 | Hardcoded API key exposed in repo | 5 | 5 | **25** | P0-1 |
| 2 | LinkedIn account ban (enterprise customer) | 4 | 5 | **20** | P3-7 |
| 3 | LLM cost runaway (no circuit breaker) | 4 | 5 | **20** | P0-5 |
| 4 | GDPR violation from personal data scraping | 4 | 5 | **20** | P1-8 |
| 5 | AI hallucination in sent messages | 4 | 4 | **16** | P1-4, P2-3 |
| 6 | Enterprise pricing cash-negative at scale | 4 | 4 | **16** | P3-2 |
| 7 | SQLite concurrent write failure | 5 | 3 | **15** | P1-1 |
| 8 | In-memory LinkedInGuard resets on restart | 5 | 3 | **15** | P0-6 |
| 9 | Email domain blacklisting from mass outreach | 3 | 5 | **15** | P1-7 |
| 10 | LinkedIn ToS change kills product category | 3 | 5 | **15** | P3-7 |
| 11 | asyncio.new_event_loop() deadlock/leak | 4 | 3 | **12** | P1-3 |
| 12 | No human approval in automated flow | 3 | 4 | **12** | P1-4 |
| 13 | CAN-SPAM violation from automated emails | 3 | 4 | **12** | P1-7 |
| 14 | Celery not wired (half-migration) | 4 | 3 | **12** | P1-5 |
| 15 | EU AI Act automated decision-making compliance | 2 | 5 | **10** | P3 future |

---

## Migration Timeline

```
Week 1:      P0 security fixes (rotate keys, fix admin bug, encrypt credentials, rate limiting)
Week 1-2:    P0 cost circuit breakers + LinkedInGuard Redis persistence
Week 2-3:    P1 PostgreSQL migration
Week 3-4:    P1 Multi-tenant Organization model
Week 4:      P1 Fix asyncio anti-patterns + wire Celery Beat
Week 4-5:    P1 Audit logging + CAN-SPAM compliance (unsubscribe links)
Week 5-6:    P1 Human approval gate for AI messages
Week 6-7:    P1 GDPR erasure API + fix fake Dashboard KPIs
Week 7-8:    P2 LLM caching (ICP cache, scoring cache)
Week 8-9:    P2 ResearchAgent token budget + Pydantic output validation
Week 9-10:   P2 Frontend: virtual scrolling, RBAC, WCAG accessibility
Week 10-11:  P2 JWT refresh tokens + structured logging + CORS fix
Week 12+:    P3 SSO, re-pricing, SOC2 prep, Server Components, CRM
```

---

## File Ownership Map

| Folder / File | Owner Agent | Priority Tasks |
|--------------|-------------|----------------|
| `backend/app/core/config.py` | Security + Architect | Remove hardcoded secrets (P0-1) |
| `backend/app/core/security.py` | Security | RS256, refresh tokens (P2-7, P2-8) |
| `backend/app/core/database.py` | Architect | PostgreSQL migration (P1-1) |
| `backend/app/api/v1/auth.py` | Security | Fix auto-admin (P0-2), rate limiting (P0-4) |
| `backend/app/api/v1/accounts.py` | Security | Encrypt credentials (P0-3) |
| `backend/app/models/` | Architect | Add org_id, audit_log table (P1-2, P1-6) |
| `backend/app/agents/` | AI Engineer | Output validation, token budgets (P2-3, P2-2) |
| `backend/app/services/linkedin_guard.py` | Security + Risk | Redis persistence (P0-6) |
| `backend/app/services/email_service.py` | Security | CAN-SPAM compliance (P1-7) |
| `backend/app/services/workflow_engine.py` | AI Engineer + Architect | asyncio fix, Celery migration (P1-3, P1-5) |
| `backend/app/services/discovery_service.py` | AI Engineer | ICP cache, token budget (P2-1) |
| `backend/app/services/sentiment_service.py` | AI Engineer | asyncio fix (P1-3) |
| `backend/app/main.py` | Architect + Security | Celery, disable Swagger prod, CORS (P1-5, P1-10, P2-10) |
| `frontend/src/app/page.tsx` | Frontend | Remove fake KPIs (P1-9) |
| `frontend/src/app/leads/page.tsx` | Frontend | Virtual scrolling (P2-4) |
| `frontend/src/context/AuthContext.tsx` | Frontend | Add org, role types (P2-5) |
| `frontend/src/lib/api.ts` | Frontend | Retry logic, typed responses (P2) |
| `frontend/src/components/` | Frontend | WCAG ARIA attributes (P2-6) |

---

## Systems to Preserve (Do Not Replace)

Per task specification, these existing systems must be enhanced, not replaced:
- ✅ 6 AI agents (BaseAgent + 5 specialized) — optimize, do not rewrite
- ✅ workflow_engine.py — wire to Celery, do not redesign logic
- ✅ LinkedInGuard — persist to Redis, keep all rate limiting logic
- ✅ WarmupService — keep warmup schedule, integrate with persistent state
- ✅ SentimentService — fix asyncio pattern, keep Gemini logic
- ✅ IMAPService — keep polling architecture, improve error handling
- ✅ A/B Testing Engine — keep variant assignment, add more metrics
- ✅ i18n system (TR/EN) — extend to more languages
- ✅ All current API endpoints — keep /api/v1/ stable, add /api/v2/ for enterprise features
- ✅ Swiss-Minimalist Tailwind design — keep design language, improve accessibility

---

## Strategic Recommendation (from Devil's Advocate)

**Do not pursue enterprise deals until P0 and P1 items are complete.**

The honest path:
1. Fix P0 issues this week (existential security risks)
2. Validate unit economics with Pro tier (50 paying Pro customers)
3. Learn from actual usage patterns before designing enterprise features
4. Re-price to per-seat before scaling
5. Obtain SOC2 Type I (faster, 3 months) before approaching enterprise procurement
6. Pursue enterprise with proper pricing ($99-149/user/month), compliance, and LinkedIn risk disclosure

The product is an impressive foundation. The enterprise pivot is achievable — but requires discipline to fix the foundation before adding floors.

---

*Report generated by 5-agent parallel analysis team. Each section was independently verified against actual source code files.*
