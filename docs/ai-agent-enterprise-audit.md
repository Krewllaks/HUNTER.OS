# HUNTER.OS AI Agent Enterprise Hardening Audit

**Date:** 2026-03-24
**Auditor:** AI/ML Engineer (ARES Engine Review)
**Scope:** All 6 AI agents, discovery pipeline, workflow engine, LLM provider strategy

---

## Executive Summary

### 3 Key Findings

1. **Hardcoded API key in config.py (CRITICAL SECURITY):** `GEMINI_API_KEY` is hardcoded as a string literal at `backend/app/core/config.py:29`. This must be moved to environment variables immediately before any enterprise deployment. No enterprise customer will accept source-committed API keys.

2. **No output validation or hallucination guard anywhere:** All 6 agents parse LLM JSON responses with bare `json.loads()` and trust every field. There is zero schema validation, no confidence thresholds that trigger human review, and no hallucination detection. For enterprise, fabricated lead names, fake emails, and invented "buying signals" will destroy credibility.

3. **Serial processing bottleneck and no caching:** ScoringAgent's `batch_score` iterates leads one-by-one with separate API calls. DiscoveryService analyzes results sequentially. There is no semantic or deterministic cache. At 1,000 leads, this means 1,000+ Gemini API calls with no reuse. Enterprise cost and latency will be unacceptable.

---

## I. Agent-by-Agent Analysis

### 1. BaseAgent (ReActAgent) - `base_agent.py`

| Metric | Value |
|--------|-------|
| Quality Score | 7/10 |
| Lines | 203 |
| Pattern | ReAct (Reason-Act-Observe loop) |
| Max Steps | 10 (configurable) |
| Temperature | 0.2 |

**Strengths:**
- Full step history forwarding prevents agent amnesia (line 79-121)
- JSON parse error recovery with self-correction (line 178-184)
- Supports both sync and async tool functions (line 162-165)
- Clean execution trace for debugging (line 191-202)

**Issues:**
- **No timeout on individual Gemini calls.** If Gemini hangs, the entire agent loop blocks forever. ProductAnalysisAgent has a 15s timeout but BaseAgent does not.
- **No token budget tracking.** Each step replays the FULL history, so token usage grows quadratically: step N sends all N-1 prior steps. At max_steps=10 with rich tool outputs, this can exceed 100K tokens.
- **Generic error catch at line 185-187** returns immediately on any non-JSON error. No retry, no fallback. A transient network error kills the entire agent run.
- **No output schema enforcement.** The agent trusts LLM to produce correct JSON keys. If it hallucinates a different structure, downstream code breaks silently.

**Token Estimation per Run (15 steps, ResearchAgent):**
- System prompt: ~400 tokens
- Per step (accumulated): ~800 tokens average (thought + action + observation)
- Step 15 input: 400 + (15 * 800) = ~12,400 tokens input
- Total across all steps: sum(400 + n*800 for n in 1..15) = ~96,000 input tokens
- Output per step: ~200 tokens x 15 = 3,000 tokens
- **Total per research run: ~99,000 tokens**

**Caching Opportunity:** HIGH - Tool observation results (website scrapes, news searches) can be cached. Same company researched for different products should reuse scrape data.

---

### 2. ProductAnalysisAgent - `product_agent.py`

| Metric | Value |
|--------|-------|
| Quality Score | 6/10 |
| Lines | 147 |
| Pattern | Single-shot Gemini call |
| Temperature | 0.3 |
| Timeout | 15 seconds |

**Strengths:**
- Has a timeout (15s) unlike other agents
- Has a fallback analysis when Gemini is unavailable (line 108-146)
- Clean JSON output schema definition in prompt

**Issues:**
- **Prompt lacks enterprise context.** The system prompt says "top-tier sales consultant" but gives no guidance on enterprise vs SMB targeting. For 500+ employee companies, ICP profiles need different dimensions: procurement cycles, compliance requirements, multi-stakeholder buying committees.
- **Fallback is too generic.** When Gemini fails, the fallback returns hardcoded "Technology, Marketing, E-commerce" industries and "CEO, Founder" titles regardless of input. Enterprise customers get SMB-quality fallback data.
- **No input sanitization.** Product description is injected directly into the prompt (line 45). A malicious or malformed description could cause prompt injection.
- **Single attempt, no retry on non-timeout errors.** Line 98-106 catches JSONDecodeError and generic Exception separately, but neither retries.

**Token Estimation per Call:**
- Input: system prompt (~150) + user prompt with schema (~600) + product description (~200) = ~950 tokens
- Output: full JSON structure = ~400 tokens
- **Total per product: ~1,350 tokens**

**Caching Opportunity:** VERY HIGH - Same product always generates the same ICP. This is a pure function of (product_name, description). Cache indefinitely until product is edited. This is the single highest-ROI cache in the system.

---

### 3. ResearchAgent - `research_agent.py`

| Metric | Value |
|--------|-------|
| Quality Score | 5/10 |
| Lines | 102 |
| Pattern | ReAct via BaseAgent |
| Max Steps | 15 |
| Tools | 5 (scrape_linkedin, scrape_company, analyze_website, search_news, compress_context) |

**Strengths:**
- Step-Back Prompting instruction for context compression (line 30-35)
- 7 intelligence priorities clearly defined
- Confidence scoring requirement in output

**Issues:**
- **`compress_context` tool is a sham.** Line 83-87 just truncates text at 3000 chars with a comment to "use Step-Back Prompting." It does not actually compress anything. The LLM is told to use it, but the tool does nothing useful. This wastes a tool call step.
- **No FINISH output schema.** The system prompt defines intelligence priorities and requires confidence scores, but never specifies the exact JSON schema the final answer should have. The agent decides its own output structure, which varies between runs.
- **max_steps=15 is expensive.** With full history replay, a 15-step research run can consume ~99K tokens (see BaseAgent analysis). Most of this is redundant re-sending of prior observations.
- **All tool errors return `{"error": str(e)}`.** The agent sees this and may retry the same failing tool repeatedly until max_steps.

**Token Estimation per Lead Research:**
- Best case (3-4 tools, 5 steps): ~25,000 tokens
- Average case (8-10 steps): ~60,000 tokens
- Worst case (15 steps, large scrapes): ~99,000+ tokens
- **Estimated average: ~55,000 tokens per lead**

**Caching Opportunity:** HIGH - Website analysis, company page data, news results are stable for 24-48 hours. LinkedIn profile data stable for 7 days. Cache tool outputs by (URL/domain, date).

---

### 4. ScoringAgent - `scoring_agent.py`

| Metric | Value |
|--------|-------|
| Quality Score | 6/10 |
| Lines | 130 |
| Pattern | Single-shot with CoT |
| Temperature | 0.2 |
| Weights | ICP 30%, Intent 35%, Accessibility 15%, Timing 20% |

**Strengths:**
- Clear 4-dimensional scoring with explicit weights
- Chain-of-Thought reasoning requirement
- Confidence score based on data completeness
- Server-side weighted score recalculation as safety net (line 99-107)

**Issues:**
- **Scoring bias: LLMs tend to score high.** Without calibration examples or anchoring, Gemini will cluster scores in the 60-85 range. Enterprise needs clear discrimination between leads. Need few-shot examples of low/medium/high scores.
- **`batch_score` is sequential.** Line 120-129 iterates leads one by one. For 100 leads, this is 100 serial API calls. Should batch 5-10 leads per prompt (the `_batch_score_leads` in discovery_service.py already does batches of 10 -- this agent should too).
- **No ICP normalization.** When `icp_criteria` is None, the prompt says "use general B2B criteria" which is meaningless. The LLM will hallucinate criteria.
- **Timing dimension is unanchored.** The prompt says "last 7 days = hot" but the lead data rarely includes timestamps. The LLM guesses timing with no real data.

**Token Estimation per Lead:**
- Input: system prompt (~350) + ICP criteria (~200) + lead data (~300-800) = ~850-1,350 tokens
- Output: CoT reasoning + scores = ~300 tokens
- **Total per lead: ~1,200-1,650 tokens**
- **For batch of 10 leads (DiscoveryService pattern): ~5,000 tokens**

**Caching Opportunity:** MEDIUM - Scores change as lead data updates. But for the same lead + same ICP, score is deterministic for ~24 hours. Cache by hash(lead_data + icp_criteria).

---

### 5. PersonalizationAgent - `personalization_agent.py`

| Metric | Value |
|--------|-------|
| Quality Score | 7/10 |
| Lines | 221 |
| Pattern | Single-shot (2 models: message + objection) |
| Temperature | 0.7 (messages), 0.8 (follow-ups), 0.5 (objections) |

**Strengths:**
- 6-layer personalization framework is well-structured
- Channel-specific rules (email 120 words, LinkedIn DM 80 words, connect 300 chars)
- Anti-generic rules ("NEVER use 'I hope this finds you well'")
- Follow-up explicitly avoids repeating previous angles
- Ghost Objection Handler with type-specific strategies

**Issues:**
- **Temperature 0.7-0.8 is too high for enterprise.** At this temperature, the LLM will occasionally produce off-brand, overly casual, or factually wrong personalization. Enterprise outreach needs 0.3-0.5 with strict brand guidelines.
- **No brand voice specification.** The prompt says "sound like a human" but gives no guidance on the sender's company brand, industry jargon level, or compliance requirements (e.g., financial services, healthcare).
- **`estimated_reply_probability` is pure hallucination.** Line 57 asks the LLM to output a reply probability. LLMs cannot estimate this. Enterprise customers will distrust AI-generated metrics.
- **No message length validation.** The prompt says "max 120 words" but there is no post-generation word count check. The LLM frequently exceeds limits.
- **Objection handler has no lead history context.** It receives current objection but not the full conversation thread. Response may contradict earlier claims.

**Token Estimation per Message:**
- Input: system prompt (~400) + channel rules (~50) + sender context (~100) + campaign goal (~50) + lead dossier (~500-1500) = ~1,100-2,100 tokens
- Output: message JSON = ~200-300 tokens
- **Total per message: ~1,400-2,400 tokens**

**Caching Opportunity:** LOW - Messages must be unique per lead. However, objection responses for common objection types (price, timing, not_interested) can be cached per objection_type + product combination and used as few-shot examples.

---

### 6. ContentAnalystAgent - `content_analyst_agent.py`

| Metric | Value |
|--------|-------|
| Quality Score | 6/10 |
| Lines | 173 |
| Pattern | Single-shot Gemini call |
| Temperature | 0.3 |

**Strengths:**
- 10-point extraction framework (communication style through best approach)
- Robust content gathering with type checking (lines 70-108 handle dict, list, str)
- Fallback profile when AI fails
- Confidence field in output

**Issues:**
- **Personality typing is pseudoscience for enterprise.** "analytical|driver|expressive|amiable" personality types (DISC model) may offend enterprise compliance teams. Replace with communication preference signals.
- **"If data is limited, infer what you can" encourages hallucination.** Line 132 explicitly tells the LLM to guess from job title and industry. For enterprise, fabricated personality traits will cause embarrassment.
- **No content freshness weighting.** Old posts (2+ years) are given equal weight to recent ones. A person's focus and style change significantly. Need timestamp-aware analysis.
- **`quotable_moments` creates IP risk.** Quoting someone's exact words in a sales outreach without context can feel invasive. Enterprise compliance may flag this.

**Token Estimation per Lead:**
- Input: system prompt (~350) + person info (~100) + digital content (~500-3000) + additional signals (~200) = ~1,150-3,650 tokens
- Output: profile JSON = ~400-600 tokens
- **Total per lead: ~1,550-4,250 tokens**

**Caching Opportunity:** HIGH - Content analysis for a person changes only when their content changes. Cache by hash(lead_id + content_hash) for 7-14 days.

---

## II. Token Usage Summary Table

### Per-Lead Full Pipeline (Discovery + Research + Score + Content + Message)

| Agent | Est. Input Tokens | Est. Output Tokens | Calls/Lead | Total Tokens/Lead |
|-------|------------------:|-------------------:|-----------:|------------------:|
| ProductAnalysisAgent | 950 | 400 | 0.05* | 68 |
| DiscoveryService (AI analyze) | 800 | 300 | 1 | 1,100 |
| DiscoveryService (AI dorks) | 600 | 200 | 0.125** | 100 |
| DiscoveryService (batch score) | 500 | 200 | 0.1*** | 70 |
| ResearchAgent (ReAct) | 55,000 | 3,000 | 1 | 58,000 |
| ScoringAgent | 1,200 | 300 | 1 | 1,500 |
| ContentAnalystAgent | 2,400 | 500 | 1 | 2,900 |
| PersonalizationAgent (message) | 1,800 | 250 | 1 | 2,050 |
| PersonalizationAgent (follow-up x2) | 2,000 | 250 | 2 | 4,500 |
| **TOTAL PER LEAD** | | | | **~70,288** |

*One product analysis per product, amortized across ~20 leads
**One AI dork generation per hunt, amortized across ~8 queries, ~20 leads
***Batch scoring is 10 leads per call, amortized

### Per 1,000 Leads Pipeline Cost

| Scenario | Total Tokens | Gemini 2.0 Flash | Claude 3.5 Haiku | GPT-4o-mini | Llama 3.1 8B (local) |
|----------|-------------|-------------------|-------------------|-------------|---------------------|
| Input tokens | 64.3M | $4.82 | $5.14 | $9.65 | $0 (compute) |
| Output tokens | 5.9M | $1.77 | $3.54 | $3.54 | $0 (compute) |
| **Total API cost** | **70.2M** | **$6.59** | **$8.68** | **$13.19** | **~$2-5 (GPU compute)** |
| ResearchAgent alone | 58M | $5.13 | $5.46 | $10.15 | $0 |
| Without Research | 12.2M | $1.46 | $1.74 | $3.04 | $0 |

**Key insight:** ResearchAgent consumes 82% of total tokens due to ReAct loop history accumulation. This is the number one optimization target.

---

## III. LLM Provider Comparison for Enterprise

| Criteria | Gemini 2.0 Flash (current) | Claude 3.5 Haiku | GPT-4o-mini | Llama 3.1 8B (local) |
|----------|---------------------------|-------------------|-------------|---------------------|
| **Input $/1M tokens** | $0.075 | $0.08 | $0.15 | $0 (compute only) |
| **Output $/1M tokens** | $0.30 | $0.60 | $0.60 | $0 (compute only) |
| **Cost/1K leads** | ~$6.59 | ~$8.68 | ~$13.19 | ~$2-5 GPU |
| **JSON mode** | Native (response_mime_type) | Tool use / JSON mode | json_object mode | Needs guidance |
| **Quality (ICP/scoring)** | Good | Very Good | Very Good | Acceptable for simple tasks |
| **Quality (personalization)** | Good | Excellent | Excellent | Poor (8B too small) |
| **Latency (p50)** | ~1-2s | ~1-3s | ~1-2s | ~2-5s (depends on GPU) |
| **Rate limits (free tier)** | 15 RPM | N/A (paid only) | N/A (paid only) | Unlimited |
| **Rate limits (paid)** | 1000 RPM | 4000 RPM | 10000 RPM | Unlimited |
| **Data privacy** | Google uses data for model improvement (unless enterprise agreement) | Anthropic does NOT use API data for training | OpenAI does NOT use API data for training (since March 2023) | Full on-premise, zero data leaves |
| **Enterprise SLA** | 99.9% (Vertex AI) | 99.5% (API) | 99.9% (Azure OpenAI) | Depends on infra |
| **SOC 2** | Yes (Google Cloud) | Yes | Yes (Azure) | N/A (self-hosted) |
| **HIPAA** | Yes (Vertex AI BAA) | Yes (with BAA) | Yes (Azure BAA) | Yes (on-premise) |
| **GDPR** | DPA available | DPA available | DPA available | Full compliance |
| **Enterprise agreement** | Google Cloud contract | Anthropic enterprise | Microsoft/OpenAI enterprise | N/A |
| **Structured output reliability** | 8/10 | 9/10 | 9/10 | 5/10 |
| **Hallucination rate (est.)** | Medium | Low | Medium | High |

### Recommendation: Two-Tier Model Strategy

| Tier | Use Cases | Recommended Model | Why |
|------|-----------|-------------------|-----|
| **Tier 1: Filtering** | Discovery relevance scoring, ICP matching, batch lead scoring | Gemini 2.0 Flash or Llama 3.1 8B (on-prem) | Cheap, fast, structured output. Acceptable quality for binary/numeric decisions. |
| **Tier 2: Generation** | Personalized messages, content analysis, objection handling | Claude 3.5 Haiku or GPT-4o-mini | Higher quality for human-facing text. Better at nuance, tone matching, enterprise language. |
| **Tier 3: On-Premise (optional)** | Data-sensitive enterprise customers | Llama 3.1 8B via Ollama | Zero data exposure. Use for PII-heavy analysis (name extraction, email parsing). |

**Cost with two-tier (1K leads):**
- Tier 1 (Gemini Flash): ~60M tokens at $0.075/$0.30 = ~$5.13
- Tier 2 (Claude Haiku for messages only): ~10M tokens at $0.08/$0.60 = ~$3.80
- **Blended total: ~$8.93** vs $6.59 all-Gemini, but significantly higher message quality

---

## IV. Prompt Engineering Improvements

### 4.1 ProductAnalysisAgent

**Current Problem:** Prompt produces SMB-oriented ICPs. No enterprise dimensions.

**Recommended additions to prompt:**
- Add enterprise-specific ICP fields: `procurement_process`, `compliance_requirements`, `buying_committee_size`, `typical_deal_cycle_days`, `budget_authority_level`
- Add negative constraints: "Do NOT suggest targeting individual contributors for enterprise deals. Target VP+ level."
- Add few-shot example of a good enterprise ICP vs a bad SMB ICP
- Add input length limit: truncate product description to 1000 chars max before injection

### 4.2 ResearchAgent

**Current Problem:** compress_context tool is fake. Token usage is quadratic.

**Recommended changes:**
- Replace `compress_context` with an actual LLM-powered summarization tool that calls a cheaper model (Gemini Flash) to compress large scrape results before they enter the history
- Add a `max_observation_length` parameter to tools -- truncate tool outputs to 1000 tokens before adding to history
- Reduce max_steps from 15 to 8 and add explicit "you have N steps remaining" in each turn
- Define the FINISH output schema explicitly in the system prompt with required fields

### 4.3 ScoringAgent

**Current Problem:** Score clustering, no calibration.

**Recommended changes:**
- Add 3 few-shot examples in the system prompt (one score 25, one score 55, one score 85) to anchor the scoring distribution
- Replace the "general B2B criteria" fallback with a mandatory ICP check: refuse to score without ICP
- Add a `data_completeness` check before scoring: count how many of the 7 intelligence signals are populated, set confidence ceiling based on that
- Implement batch scoring: send 5 leads per prompt with individual scores

### 4.4 PersonalizationAgent

**Current Problem:** High temperature, no brand voice, hallucinated reply probability.

**Recommended changes:**
- Lower temperature to 0.4 for initial messages, 0.5 for follow-ups
- Remove `estimated_reply_probability` from output schema entirely
- Add `brand_voice` parameter that injects company-specific tone/forbidden phrases
- Add `compliance_rules` parameter for regulated industries (no claims, no guarantees, required disclaimers)
- Add post-generation validation: word count check, forbidden phrase scan, PII leak detection
- Replace P.S. strategy with optional `closing_hook` that can be disabled for formal enterprise outreach

### 4.5 ContentAnalystAgent

**Current Problem:** Encourages hallucination, personality pseudoscience.

**Recommended changes:**
- Replace DISC personality types with evidence-based communication preferences: "data-driven" / "relationship-driven" / "action-oriented" / "detail-oriented"
- Change "infer what you can" to "if data is insufficient for a field, return null instead of guessing. Set confidence below 0.3"
- Add content recency weighting: "Weight content from the last 90 days 3x more than older content"
- Rename `quotable_moments` to `reference_points` and add instruction: "paraphrase, do not quote verbatim"

---

## V. Cost Optimization Strategies

### 5.1 Deterministic Caching (Highest ROI)

| Cache Target | Key | TTL | Estimated Savings |
|-------------|-----|-----|-------------------|
| ProductAnalysisAgent ICP | hash(product_name + description) | Until product edited | 95% (1 call vs 20/hunt) |
| DiscoveryService AI dorks | hash(product_id + icp_hash) | Until ICP changes | 87.5% (1 call per product) |
| Website analysis | domain + date_bucket(7d) | 7 days | 60-80% across products |
| News search | company_name + date_bucket(24h) | 24 hours | 40-60% |
| LinkedIn scrape | profile_url + date_bucket(7d) | 7 days | 50-70% |

**Implementation:** Redis with hash keys. Already have Redis in docker-compose for Celery. Add a `@cached_llm_call(key_fn, ttl)` decorator.

### 5.2 Semantic Caching (Medium ROI, Higher Complexity)

For similar but not identical leads:
- Embed lead profile summaries using a cheap embedding model (text-embedding-3-small at $0.02/1M tokens)
- Before calling ContentAnalystAgent or ScoringAgent, check if a semantically similar lead (cosine > 0.92) was recently processed
- Return cached result with adjusted confidence (-10%)

**Estimated savings:** 20-30% for ContentAnalyst, 15-25% for Scoring

### 5.3 Batch Processing (High ROI)

| Current | Proposed | Savings |
|---------|----------|---------|
| ScoringAgent: 1 lead per call | 5-10 leads per call | 70-80% token reduction (shared system prompt + ICP) |
| DiscoveryService AI analyze: 1 result per call | 3-5 results per call | 50-60% token reduction |
| ContentAnalystAgent: 1 lead per call | 2-3 similar leads per call | 30-40% (if same company/industry) |

### 5.4 Token Compression

| Technique | Where | Savings |
|-----------|-------|---------|
| Truncate tool observations to 1000 tokens | ResearchAgent | 40-50% of total budget |
| Remove redundant ICP fields from scoring prompt | ScoringAgent | 10-15% |
| Use abbreviated JSON keys in prompts | All agents | 5-10% |
| Compress lead_data before injection (remove nulls, empty arrays) | All agents | 10-20% |

### 5.5 Two-Tier Model Architecture

- **Tier 1 (cheap):** Lead relevance filtering, ICP matching, batch scoring, entity extraction
  - Model: Gemini 2.0 Flash ($0.075 input)
  - Use for: DiscoveryService._ai_analyze, ScoringAgent.batch_score, regex-failed entity extraction

- **Tier 2 (quality):** Message generation, content analysis, objection handling
  - Model: Claude 3.5 Haiku or GPT-4o-mini
  - Use for: PersonalizationAgent, ContentAnalystAgent, ResearchAgent final synthesis

**Net effect on 1K leads:**
- Current (all Gemini 2.0 Flash): ~$6.59
- With all optimizations (caching + batching + two-tier): estimated **~$2.50-3.50**
- **Savings: 45-60%**

---

## VI. Reliability & Quality for Enterprise

### 6.1 Structured Output Validation

**Current state:** All agents do `json.loads(response.text)` with no schema check.

**Required:**
- Add Pydantic models for every agent output schema
- Validate immediately after JSON parse
- On validation failure: retry once with error message appended to prompt
- On second failure: return fallback + log for human review

```
# Example schema (not to implement, reference only)
class ScoringOutput(BaseModel):
    chain_of_thought: str
    icp_match_score: int = Field(ge=0, le=100)
    intent_score: int = Field(ge=0, le=100)
    accessibility_score: int = Field(ge=0, le=100)
    timing_score: int = Field(ge=0, le=100)
    final_score: float = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    top_signals: list[str]
    recommended_approach: str
    urgency: Literal["low", "medium", "high"]
```

### 6.2 Hallucination Detection

| Pattern | Detection Method | Action |
|---------|-----------------|--------|
| Fabricated email addresses | Regex + MX record check | Flag, do not auto-send |
| Invented company names | Cross-reference with search result source data | Flag if not in source |
| Fake LinkedIn URLs | URL format validation + optional HTTP HEAD check | Remove if invalid |
| Hallucinated buying signals | Compare against actual tool observations (ResearchAgent trace) | Mark confidence=low |
| Invented quotes | Compare against actual content_pieces passed to ContentAnalyst | Remove if not found in input |
| Inflated scores | Statistical distribution check (>80% of scores above 70 = likely inflated) | Recalibrate batch |

### 6.3 Confidence-Based Human-in-the-Loop

| Confidence Range | Action | Enterprise Requirement |
|-----------------|--------|----------------------|
| 80-100 | Auto-proceed | Log for audit trail |
| 50-79 | Auto-proceed with flag | Highlight in dashboard for optional review |
| 30-49 | Queue for human review | Require approval before outreach |
| 0-29 | Block auto-outreach | Require manual verification of all data |

### 6.4 A/B Testing for Prompts

Current `ab_testing.py` handles campaign-level A/B tests. Need prompt-level A/B testing:
- Version prompts with IDs (e.g., `personalization_v2.3_enterprise`)
- Route 10% of traffic to experimental prompt variants
- Track downstream metrics: reply rate, meeting rate, positive sentiment rate
- Auto-promote winning variants after statistical significance (p < 0.05, n > 100)

### 6.5 Audit Trail

Enterprise customers require full traceability:
- Log every LLM call: prompt hash, model, temperature, token count, latency, response hash
- Store agent traces (BaseAgent.get_trace()) in database, linked to lead_id
- Provide "why was this message generated?" explainability endpoint
- Retention: 90 days minimum, configurable per enterprise customer

---

## VII. Priority List

### P0 - Critical (Block Enterprise Launch)

| # | Issue | File | Impact |
|---|-------|------|--------|
| 1 | Hardcoded GEMINI_API_KEY in source code | `config.py:29` | Security breach, enterprise deal-killer |
| 2 | No output schema validation on any agent | All agents | Silent data corruption, hallucinated data enters DB |
| 3 | No hallucination detection for emails/names | PersonalizationAgent, DiscoveryService | Sending emails to fabricated addresses = spam/reputation damage |
| 4 | ResearchAgent compress_context tool is fake | `research_agent.py:83-87` | Wastes tool steps, no actual compression |
| 5 | No per-call timeout in BaseAgent | `base_agent.py:131` | Hung Gemini calls block entire pipeline |

### P1 - High (Required for Enterprise Quality)

| # | Issue | File | Impact |
|---|-------|------|--------|
| 6 | ScoringAgent sequential batch processing | `scoring_agent.py:120-129` | 1000 leads = 1000 serial calls, unacceptable latency |
| 7 | No deterministic cache for ProductAnalysis | `product_agent.py` | Same product re-analyzed on every hunt |
| 8 | Temperature too high for PersonalizationAgent | `personalization_agent.py:141,180` | Off-brand, inconsistent enterprise messages |
| 9 | No brand voice / compliance parameter | `personalization_agent.py` | Cannot customize per enterprise customer |
| 10 | Scoring bias (score clustering) | `scoring_agent.py` | Poor lead discrimination |
| 11 | No audit trail / LLM call logging | All agents | Enterprise compliance failure |
| 12 | `estimated_reply_probability` is hallucinated | `personalization_agent.py:57` | Erodes trust in AI metrics |

### P2 - Medium (Significant Improvement)

| # | Issue | File | Impact |
|---|-------|------|--------|
| 13 | ReAct history grows quadratically | `base_agent.py:79-121` | Token waste at scale |
| 14 | No semantic caching | DiscoveryService | Redundant AI calls for similar leads |
| 15 | ContentAnalyst encourages hallucination | `content_analyst_agent.py:132` | Fabricated personality traits |
| 16 | No content freshness weighting | `content_analyst_agent.py` | Stale data weighted equally |
| 17 | Two-tier model strategy not implemented | All | Paying premium price for filtering tasks |
| 18 | No prompt versioning / A/B testing | All | Cannot iterate on prompt quality |
| 19 | ProductAnalysisAgent prompt lacks enterprise ICP fields | `product_agent.py:32-38` | SMB-oriented ICPs for enterprise targets |

### P3 - Low (Nice to Have)

| # | Issue | File | Impact |
|---|-------|------|--------|
| 20 | WorkflowEngine creates new event loop per action | `workflow_engine.py:211-214` | Performance overhead, potential loop leak |
| 21 | DISC personality types in ContentAnalyst | `content_analyst_agent.py` | Enterprise compliance concern |
| 22 | No input sanitization on product descriptions | `product_agent.py` | Prompt injection risk |
| 23 | Quotable moments IP risk | `content_analyst_agent.py:44` | Legal concern for enterprise |
| 24 | DiscoveryService verify=False on httpx | `discovery_service.py:399` | SSL bypass, security audit flag |

---

## VIII. Implementation Roadmap (Recommended Order)

**Week 1-2: P0 Security & Reliability**
- Move API key to env var
- Add Pydantic output validation to all agents
- Add timeout to BaseAgent Gemini calls
- Fix compress_context tool
- Add basic hallucination checks (email MX, URL validation)

**Week 3-4: P1 Enterprise Quality**
- Implement deterministic cache (Redis) for ProductAnalysis and DiscoveryService
- Add batch scoring to ScoringAgent
- Lower PersonalizationAgent temperature, add brand_voice parameter
- Add few-shot calibration examples to ScoringAgent
- Implement LLM call audit logging

**Week 5-6: P2 Cost Optimization**
- Implement observation truncation for ResearchAgent
- Add semantic caching layer
- Implement two-tier model routing
- Add prompt versioning system

**Week 7-8: P2/P3 Polish**
- Prompt A/B testing framework
- ContentAnalyst improvements (freshness, no hallucination encouragement)
- Enterprise ICP fields in ProductAnalysisAgent
- Full audit trail API endpoint

---

*End of audit. All findings based on code read from the repository at `C:\Users\bahti\Desktop\aipoweredsaleshunter` on 2026-03-24.*
