# HUNTER.OS Enterprise Frontend Hardening - Research Findings

**Date:** 2026-03-24
**Author:** Frontend & Usability Engineer
**Scope:** Enterprise readiness assessment across UX, accessibility, performance, i18n, and API client

---

## Executive Summary

Three critical findings that gate the enterprise pivot:

1. **No role-based access control in the frontend.** The AuthContext carries a flat `User` type with a single `role` field that is never checked. Enterprise customers require admin/manager/member views, approval workflows for AI-generated messages, and audit trails. None of this exists today.

2. **The leads table will collapse at enterprise scale.** The current implementation renders all rows to the DOM with no virtualization. At 100K+ leads (normal for enterprise), the page will be unusable. Export only works on the current page's data (client-side CSV/JSON), not server-side bulk export.

3. **Accessibility is structurally absent.** Zero ARIA attributes across all pages. Modals have no focus trapping. Tables lack proper scope attributes. Color contrast on dark backgrounds (gray text on dark cards) fails WCAG AA. Enterprise procurement routinely requires WCAG compliance documentation.

---

## 1. Enterprise UX Gap Analysis

### 1.1 Current State (SMB-Oriented)

| Feature | Current | Enterprise Need |
|---------|---------|-----------------|
| User model | Single user, flat auth | Multi-user with roles (admin/manager/member/viewer) |
| Dashboard | Single-view, hardcoded KPIs ($142.8k, 94%) | Executive summary with drilldown, team activity, custom date ranges |
| Lead management | Search + single status filter, 20/page pagination | Advanced multi-filter (industry, score range, date range, assigned-to), saved views, bulk select + bulk actions |
| Message approval | Direct send, no review step | Approval workflow: draft -> manager review -> approve/reject -> send |
| Data export | Client-side CSV/JSON of current page only | Server-side export of full dataset, scheduled reports, Excel with formatting |
| Campaign management | Basic CRUD + activate/pause | Templates, A/B variant management UI, scheduling, team assignment |
| Audit trail | None | Who did what, when, on which record |
| Notifications | None in UI | In-app notification center, activity feed |

### 1.2 Missing Enterprise Features (Detailed)

**Bulk Operations (P0)**
- No checkbox column on the leads table for multi-select
- No "Select all across pages" pattern
- No bulk status change, bulk assign-to-campaign, bulk delete
- No bulk message approval/rejection

**Advanced Filtering (P0)**
- Only single status filter exists; no compound filters
- No score range slider
- No date range picker
- No industry/source/assigned-user filters
- No saved filter presets ("My Hot Leads", "Uncontacted This Week")

**Role-Based Views (P0)**
- Sidebar shows identical navigation for all users
- No admin panel for user management
- No permission checks before rendering actions (delete, send, etc.)
- The `userPlan` in Sidebar is cast with `as any` -- no type safety

**Approval Workflows (P1)**
- Messages go directly from generate to send
- Enterprise compliance requires: draft -> review queue -> manager approval -> send
- MessagePreviewModal exists but has no approval/rejection flow
- No audit log of who approved which message

**Team Management UI (P1)**
- No invite/remove team member UI
- No role assignment UI
- No team activity dashboard
- No "assigned to" field on leads or campaigns

### 1.3 Dashboard Gaps

The current dashboard (`dashboard/page.tsx`) has structural issues for enterprise:
- **Hardcoded fallback values:** Lines 129, 169-172 show hardcoded "94%", "2.4k", "1.1k", "482", "86" when real data is zero. Enterprise users will notice fake data instantly.
- **Lead Velocity section** (lines 139-143) is entirely hardcoded (+12%, +28%, -4%). Not connected to any API.
- **No date range selector** for KPI cards.
- **No drill-down capability** -- clicking a KPI card does nothing.
- **No team activity view** -- who sent how many messages, who booked meetings.

---

## 2. Accessibility Audit (WCAG 2.1 AA)

### 2.1 Critical Failures

**2.1.1 Keyboard Navigation (WCAG 2.1.1, 2.1.2)**
- Modals (`LeadDetailModal`, `CreateCampaignModal`, `CampaignAnalyticsModal`) have no focus trapping. Tab key moves behind the modal to page content.
- `ActionsDropdown` and `ExportDropdown` are mouse-only. No keyboard open/close (Enter/Space/Escape), no arrow key navigation between items.
- Leads table rows are `onClick` interactive `<tr>` elements but have no `role="button"`, no `tabIndex`, no keyboard event handlers.
- Sidebar navigation uses `<Link>` (good) but the "New Campaign" button and logout use `<button>` without visible focus indicators.

**2.1.2 ARIA & Semantics (WCAG 4.1.2)**
- Zero `aria-label` attributes found across entire codebase.
- Modals lack `role="dialog"`, `aria-modal="true"`, `aria-labelledby`.
- Dropdowns lack `role="menu"`, `role="menuitem"`, `aria-expanded`, `aria-haspopup`.
- Status badges and score badges convey meaning through color only -- no `aria-label` with text meaning.
- `<table>` headers lack `scope="col"`.
- Loading spinner (`Loader2`) has no `aria-label="Loading"` or live region announcement.

**2.1.3 Color Contrast (WCAG 1.4.3)**
- `text-[#666]` on `bg-[#1A1A1A]`: ratio approximately 2.6:1 (FAIL, needs 4.5:1 for normal text). Used extensively in dashboard, modals, campaign analytics.
- `text-[#9E9E9E]` on `bg-[#0D0D0D]`: ratio approximately 4.2:1 (FAIL for normal text < 14pt bold).
- `text-text-muted` (#9E9E9E) on `bg-background` (#E8E8E8): ratio approximately 2.8:1 (FAIL).
- Score badge colors (hot/warm/cool/cold) -- could not verify exact CSS but class names suggest color-only differentiation.

**2.1.4 Focus Management (WCAG 2.4.3, 2.4.7)**
- No visible focus outlines defined in Tailwind config or global CSS (no `ring` utilities used consistently).
- Modal open/close does not manage focus -- focus is not moved to modal on open, not returned to trigger on close.
- Page navigation does not announce route changes to screen readers.

### 2.2 Moderate Issues

- `<html lang="en">` is hardcoded even when locale is "tr". Should be dynamic.
- No skip navigation link ("Skip to main content").
- Images/icons (Lucide) are decorative but lack `aria-hidden="true"` explicitly.
- Form inputs in Settings page lack proper `<label>` association (using text above input, not `htmlFor`).
- `confirm()` dialog for delete (leads page line 345) is not accessible -- should use a custom modal.
- Landing page `<button onClick={() => scrollTo("ares")}>` -- smooth scroll but no focus management at target.

### 2.3 Enterprise Procurement Impact

Enterprise RFPs commonly require VPAT (Voluntary Product Accessibility Template) or equivalent documentation. Current state would fail any accessibility audit. Estimated remediation: 3-4 weeks of focused work.

---

## 3. Performance Assessment

### 3.1 Leads Table at Scale

**Current Implementation (leads/page.tsx):**
- Fetches 20 leads per page via API pagination -- OK for small datasets.
- Renders all 20 rows as standard `<tr>` elements -- fine at 20.
- **Problem at enterprise scale:** Users expect instant search across 100K+ leads, column sorting, and the ability to scroll through large result sets without pagination click fatigue.
- Export is client-side only (lines 143-175), limited to loaded page data. Exporting 100K leads is impossible.
- No debounce optimization for search -- uses `useEffect` with `setTimeout` 300ms which is correct but the `fetchLeads` dependency in `useEffect` creates a new function reference on every state change, potentially causing extra renders.

**Recommendations:**
- Virtual scrolling with `@tanstack/react-virtual` for large result sets
- Server-side export endpoint (stream CSV)
- Server-side sorting and multi-column filtering
- Consider cursor-based pagination instead of offset-based for large datasets

### 3.2 Bundle & Loading

**Current Dependencies (package.json):**
- `recharts` (2.14.1): ~280KB gzipped -- heavy, only used on dashboard/analytics. Should be dynamically imported.
- `lucide-react` (0.468.0): Tree-shakes well with named imports -- OK.
- `date-fns` (4.1.0): Tree-shakeable -- OK.
- `clsx` (2.1.1): Tiny -- OK.
- No `tailwind-merge` -- conditional class conflicts possible.

**Missing:**
- No `next/dynamic` usage detected for code splitting. Heavy components (Recharts, modals) should be lazy loaded.
- No `<Suspense>` boundaries anywhere.
- Every page is `"use client"` -- zero Server Components being used despite Next.js 15.
- No `loading.tsx` files in any route folder for streaming SSR.
- No `error.tsx` files for error boundaries.
- Google Fonts loaded via `<link>` in `<head>` (layout.tsx line 19-22) instead of `next/font` -- causes FOIT/FOUT and blocks rendering.

### 3.3 Server Components Opportunity

**Every single page file starts with `"use client"`**, including:
- Landing page (page.tsx) -- mostly static content, ideal for RSC
- Dashboard -- initial data fetch could be server-side
- Settings page -- mostly static form structure

**Impact:** The entire app is client-rendered. First paint requires downloading all JS, parsing, executing, then fetching data. With Server Components:
- Landing page could be fully server-rendered (zero JS)
- Dashboard layout could be server-rendered with client islands for interactive parts
- Estimated LCP improvement: 40-60%

### 3.4 Real-Time Progress

CLAUDE.md notes "WebSocket/SSE: real-time hunt progress" as future work. Currently `huntProgress` is a polling API (`api.products.huntProgress`). For enterprise with multiple concurrent hunts, this should be SSE at minimum.

---

## 4. Enterprise Features Required

### 4.1 Priority Matrix

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| Role-based UI (admin/manager/member views) | P0 | 2 weeks | Gate for enterprise sales |
| Bulk operations on leads table | P0 | 1 week | Enterprise workflow essential |
| Advanced multi-filter with saved presets | P0 | 1.5 weeks | Enterprise daily workflow |
| Message approval workflow UI | P0 | 1.5 weeks | Compliance requirement |
| Virtual scrolling for leads | P0 | 3 days | Breaks at scale without it |
| Server-side export (CSV/Excel) | P0 | 1 week | Backend + frontend |
| WCAG AA remediation | P0 | 3 weeks | Procurement gate |
| Team management UI | P1 | 1.5 weeks | Multi-user essential |
| Audit log viewer | P1 | 1 week | Compliance, debugging |
| SSO login flow (OIDC) | P1 | 1.5 weeks | Enterprise auth requirement |
| Advanced reporting / date range KPIs | P1 | 2 weeks | Executive stakeholder need |
| API key management UI | P1 | 3 days | Developer/integration need |
| Webhook configuration UI | P1 | 3 days | Integration need |
| White-labeling (custom logo, colors) | P2 | 1 week | Enterprise vanity |
| Server Components migration | P2 | 2 weeks | Performance, SEO |
| Real-time SSE for hunt progress | P2 | 1 week | UX improvement |
| Custom dashboard widgets | P3 | 2 weeks | Nice-to-have |

### 4.2 Feature Details

**SSO Login Flow:**
- Current auth is email/password with JWT stored in localStorage.
- Enterprise requires: SAML 2.0 or OIDC with corporate IdP (Azure AD, Okta, Google Workspace).
- Frontend needs: `/login/sso` route, IdP discovery, redirect flow, callback handler.
- localStorage JWT storage is a security concern for enterprise -- consider httpOnly cookies.

**Audit Log Viewer:**
- New page: `/audit` or `/settings/audit`
- Table: timestamp, user, action, resource, details
- Filterable by user, action type, date range
- Export capability

**API Key Management:**
- Settings sub-section
- Generate, revoke, list API keys
- Copy-to-clipboard, last-used-at display
- Scoped permissions per key

**Webhook Configuration:**
- Settings sub-section
- Add endpoint URL, select events (lead.created, message.sent, reply.received)
- Test webhook button
- Delivery log with retry status

---

## 5. i18n & Localization Assessment

### 5.1 Current Architecture

**Strengths:**
- Custom lightweight i18n system (`lib/i18n.ts` + `hooks/useI18n.ts`)
- ~120 translation keys covering major UI areas
- localStorage persistence
- Reactive updates via listener pattern

**Weaknesses:**

| Issue | Severity | Detail |
|-------|----------|--------|
| Hardcoded strings | HIGH | Settings page has "Ayarlar", "Profil", "Kaydedildi", "Degisiklikleri Kaydet" hardcoded in Turkish. Landing page has all English hardcoded. Dashboard has hardcoded "Last Action", "Interested/Not Interested" in English. |
| No pluralization | MEDIUM | "X leads in pipeline" -- no plural rules. Turkish and English have different plural rules. |
| No interpolation | MEDIUM | Cannot do `t("leads.count", { count: 42 })`. All dynamic text is concatenated. |
| Flat key structure | LOW | Single flat object will not scale to 500+ keys for 5+ languages. |
| `<html lang>` hardcoded | HIGH | `layout.tsx` has `<html lang="en">` -- should reflect current locale. |
| No number/date formatting | HIGH | `toLocaleDateString("tr-TR")` is hardcoded on leads page line 281. No locale-aware formatting system. |
| No currency formatting | HIGH | Dashboard shows "$142.8k" and "$12.40" -- no locale-aware currency. |
| Settings page reloads | LOW | `window.location.reload()` on language change (settings page line 35) instead of reactive update. |

### 5.2 Enterprise Expansion Needs

**Additional Languages:**
- DE, FR, ES, PT-BR are realistic for European/LATAM enterprise markets.
- Current system stores all translations in a single file -- at 120 keys x 6 languages, this becomes unmanageable.
- Recommend: Split to per-locale JSON files, lazy-load non-default locales.

**RTL Support:**
- Zero RTL considerations in current CSS.
- Tailwind has built-in RTL support (`rtl:` variant) but it is not configured.
- Layout uses `fixed left-0` for sidebar, `ml-sidebar` for content -- would need mirroring for RTL.
- Arabic and Hebrew markets are relevant for enterprise sales tools.
- Effort estimate: 1-2 weeks if done systematically with Tailwind RTL plugin.

**Date/Number/Currency Formatting:**
- Should use `Intl.DateTimeFormat`, `Intl.NumberFormat`, `Intl.RelativeTimeFormat`.
- Create utility functions in `lib/formatters.ts` that respect current locale.
- Timezone handling: Enterprise users span multiple timezones -- all timestamps should show user's local time.

### 5.3 Recommended Architecture

Replace current custom system with `next-intl` or similar:
- File-based translation loading (JSON per locale)
- Built-in pluralization, interpolation, date/number formatting
- Server Component compatible
- ICU MessageFormat support
- Type-safe translation keys

---

## 6. API Client Assessment (`lib/api.ts`)

### 6.1 Current State

The `ApiClient` class is well-structured with namespaced methods. Key observations:

**Strengths:**
- Clean namespace pattern (`api.leads.list()`, `api.campaigns.create()`)
- 401 auto-logout with redirect
- rawBody support for form-encoded auth
- 204 handling

**Weaknesses:**

| Issue | Severity | Detail |
|-------|----------|--------|
| No retry logic | HIGH | Single fetch call, no retry on network failure or 5xx. Enterprise users on flaky corporate networks need this. |
| No request deduplication | MEDIUM | Multiple components can fire the same request simultaneously (e.g., dashboard fetches analytics + leads in parallel, but if two components mount that share data, duplicate requests fire). |
| No request cancellation | MEDIUM | No AbortController usage. Navigating away during a long request leaves orphaned promises. The 401 handler with `window.location.href` can fire during cleanup. |
| No optimistic updates | LOW | All mutations are fire-and-forget. Campaign activate/pause waits for server round-trip before UI update. |
| No offline/degraded handling | HIGH | Network failure throws a generic error. No queuing, no retry, no user-facing "offline" state. |
| Token in localStorage | MEDIUM | XSS-vulnerable. Enterprise security audits flag this. Should migrate to httpOnly cookie or at minimum use in-memory + refresh token pattern. |
| No request/response interceptors | LOW | Cannot globally add request timing, error reporting, or analytics. |
| No typed responses | MEDIUM | Many methods return untyped `this.request(...)`. Leads list returns `any`, campaigns use `as any` casts. |
| Error messages from server | LOW | `error.detail` is the only field checked. Some APIs return `error.message` or arrays of validation errors. |
| No rate limiting awareness | MEDIUM | No 429 handling, no backoff. Enterprise usage with many team members could trigger rate limits. |

### 6.2 Recommended Improvements

1. **Retry with exponential backoff** for 5xx and network errors (max 3 retries).
2. **AbortController integration** -- cancel in-flight requests on component unmount.
3. **Request deduplication** -- same GET request within 100ms returns the same promise.
4. **Typed responses** -- every namespace method should have proper return types.
5. **Error normalization** -- parse various error formats into a standard `ApiError` type with `code`, `message`, `fieldErrors`.
6. **429 handling** -- respect `Retry-After` header, queue requests.
7. **Offline detection** -- `navigator.onLine` + `online`/`offline` events, queue mutations, show banner.
8. **Consider migrating to TanStack Query** for caching, deduplication, background refetching, and optimistic updates. This would replace most manual `useState` + `useEffect` + `useCallback` data fetching patterns currently duplicated across every page.

---

## 7. Additional Technical Findings

### 7.1 Type Safety Gaps

- `Campaign` type is `any` (campaigns page line 13): `type Campaign = any;`
- `userPlan` in Sidebar uses `(user as any)?.plan` (line 32)
- Settings page casts user with `as { plan?: string }` and `as unknown as { trial_ends_at?: string }`
- API client methods mostly return untyped promises
- These undermine TypeScript's value proposition and will cause runtime errors at scale

### 7.2 Component Architecture

- No shared component library (only 4 components in `/components/`)
- Modals are implemented inline in each page file (leads, campaigns) instead of a reusable Modal component
- Dropdown pattern is duplicated (`ActionsDropdown`, `ExportDropdown`) with identical click-outside logic
- No compound component patterns, no composition
- StatusBadge, ScoreBadge, SentimentBadge are similar but not unified

### 7.3 Error Handling

- Most `catch` blocks either `console.error` or silently swallow errors
- No global error boundary (`error.tsx`)
- No user-facing error toasts or notification system
- Delete uses `window.confirm()` instead of a custom confirmation modal
- No retry UI after failed operations

### 7.4 State Management

- All state is local `useState` in page components
- No shared state beyond AuthContext
- No caching -- navigating away and back refetches everything
- Dashboard and Leads page both fetch leads independently
- No global loading/error state management

---

## 8. Priority Roadmap

### P0 - Enterprise Gate (must have before first enterprise sale)

| Item | Effort | Files Impacted |
|------|--------|----------------|
| WCAG AA compliance (focus, ARIA, contrast, keyboard) | 3 weeks | All pages, all components |
| Role-based access control UI | 2 weeks | AuthContext, Sidebar, all pages |
| Leads table: bulk select, bulk actions, virtual scroll | 1.5 weeks | leads/page.tsx, new components |
| Advanced filtering with saved presets | 1.5 weeks | leads/page.tsx, new FilterPanel component |
| Message approval workflow | 1.5 weeks | New approval page, MessagePreviewModal |
| Server-side data export | 1 week | Backend endpoint + frontend trigger |
| API client: typed responses, retry, abort | 1 week | lib/api.ts |
| Type safety: eliminate all `any` types | 3 days | campaigns, sidebar, settings, api.ts |

**P0 Total: ~12 weeks**

### P1 - Enterprise Experience

| Item | Effort |
|------|--------|
| Team management UI (invite, roles, activity) | 1.5 weeks |
| SSO/OIDC login flow | 1.5 weeks |
| Audit log viewer | 1 week |
| Advanced reporting with date range | 2 weeks |
| API key management UI | 3 days |
| Webhook configuration UI | 3 days |
| i18n: interpolation, pluralization, locale-aware formatting | 1 week |
| Global error boundary + toast notifications | 3 days |

**P1 Total: ~8 weeks**

### P2 - Scale & Performance

| Item | Effort |
|------|--------|
| Server Components migration (landing, dashboard, settings) | 2 weeks |
| Reusable component library (Modal, Dropdown, Badge, DataTable) | 1.5 weeks |
| next/font migration (replace Google Fonts link) | 2 hours |
| Dynamic imports for Recharts | 2 hours |
| loading.tsx / error.tsx for all routes | 1 day |
| Real-time SSE for hunt progress | 1 week |
| TanStack Query migration | 1.5 weeks |
| White-labeling (theme customization) | 1 week |
| RTL support | 1.5 weeks |
| Additional languages (DE, FR, ES, PT-BR) | 1 week per language |

**P2 Total: ~10 weeks**

### P3 - Polish

| Item | Effort |
|------|--------|
| Custom dashboard widgets / drag-and-drop | 2 weeks |
| Keyboard shortcuts (Cmd+K command palette) | 3 days |
| Offline mode with queued mutations | 1 week |
| E2E test suite (Playwright) | 2 weeks |
| Performance monitoring (Web Vitals reporting) | 2 days |

---

## 9. Key Files Referenced

| File | Key Findings |
|------|-------------|
| `frontend/src/app/leads/page.tsx` | No virtualization, client-only export, no bulk ops, no ARIA |
| `frontend/src/app/dashboard/page.tsx` | Hardcoded KPI fallbacks, no date range, no drill-down |
| `frontend/src/app/campaigns/page.tsx` | `type Campaign = any`, duplicated modal patterns |
| `frontend/src/lib/api.ts` | No retry, no abort, no typed responses, token in localStorage |
| `frontend/src/lib/i18n.ts` | No pluralization, no interpolation, hardcoded strings elsewhere |
| `frontend/src/components/Sidebar.tsx` | No role-based nav, `as any` cast |
| `frontend/src/components/AppShell.tsx` | Uses `window.location.href` for redirect instead of Next.js router |
| `frontend/src/context/AuthContext.tsx` | No role checks, no permission system |
| `frontend/src/app/settings/page.tsx` | Hardcoded Turkish strings, no actual API save, `window.location.reload()` |
| `frontend/src/app/layout.tsx` | Hardcoded `lang="en"`, Google Fonts via `<link>` |
| `frontend/tailwind.config.ts` | Good design token foundation, no dark mode toggle, no RTL |
| `frontend/package.json` | Missing: tailwind-merge, tanstack/react-virtual, next-intl, tanstack/react-query |

---

*End of findings. No code was modified during this assessment.*
