"""
HUNTER.OS / ARES - Product Analysis Agent
Analyzes user's product description and generates ICP profile + search strategies.
Includes deterministic caching: same product name + description = skip Gemini call.
"""
import hashlib
import json
import logging

import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProductAnalysisAgent:
    """
    Takes a user's raw product description and outputs:
    - Value proposition summary
    - Target market segments
    - ICP profile (industries, titles, company sizes, pain points)
    - Search strategies for finding customers
    """

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=self._system_prompt(),
        )

    @staticmethod
    def _system_prompt() -> str:
        return """You are ARES, an expert sales strategist AI. Your job is to analyze a product/service description
and create a comprehensive Ideal Customer Profile (ICP) and customer discovery strategy.

You MUST respond with valid JSON only. No markdown, no explanation outside JSON.

Your analysis should be deep and actionable - think like a top-tier sales consultant who needs to
find the EXACT right people to sell this product to."""

    async def analyze(self, product_name: str, description: str) -> dict:
        """Analyze product and generate ICP + search strategies."""
        prompt = f"""Analyze this product/service and create a detailed customer acquisition strategy.

Product Name: {product_name}
Product Description: {description}

Respond with this exact JSON structure:
{{
    "value_proposition": {{
        "summary": "One paragraph summary of what the product does and why it matters",
        "core_benefit": "The single biggest benefit in one sentence",
        "differentiators": ["What makes this different from alternatives"]
    }},
    "target_market": {{
        "primary_segments": ["Segment 1", "Segment 2"],
        "market_size_estimate": "Small/Medium/Large",
        "urgency_level": "How urgently do these people need this? Low/Medium/High"
    }},
    "icp_profile": {{
        "industries": ["Industry 1", "Industry 2", "Industry 3"],
        "company_sizes": ["1-10", "11-50", "51-200"],
        "target_titles": ["CEO", "CTO", "VP Marketing"],
        "pain_points": ["Pain point 1", "Pain point 2", "Pain point 3"],
        "buying_signals": ["Signal that indicates they need this NOW"],
        "keywords": ["Keywords these people would use in their content"],
        "negative_signals": ["Signs this person is NOT a good fit"]
    }},
    "search_strategies": {{
        "linkedin_queries": ["LinkedIn search query 1", "LinkedIn search query 2"],
        "google_queries": ["Google search query to find target companies"],
        "content_topics": ["Topics these people write/talk about"],
        "competitor_products": ["Products they might currently use instead"],
        "communities": ["Online communities where these people hang out"]
    }},
    "outreach_angles": {{
        "primary_hook": "The main angle for the first message",
        "follow_up_angles": ["Alternative angles for follow-ups"],
        "objection_preempts": ["Common objections and how to address them"]
    }}
}}"""

        import asyncio

        try:
            response = await asyncio.wait_for(
                self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json",
                    ),
                ),
                timeout=15,  # 15 second max — don't let gRPC retry forever
            )
            result = json.loads(response.text.strip())
            logger.info(f"Product analysis completed for: {product_name}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in product analysis: {e}")
            return {"error": f"Failed to parse AI response: {str(e)}"}
        except asyncio.TimeoutError:
            logger.warning(f"Gemini timed out, using fallback for: {product_name}")
            return self._fallback_analysis(product_name, description)
        except Exception as e:
            logger.warning(f"Gemini error ({type(e).__name__}), using fallback for: {product_name}")
            return self._fallback_analysis(product_name, description)

    # ── ICP Refinement with User Answers ─────────────────

    async def generate_questions(self, product_name: str, description: str, initial_analysis: dict) -> list[dict]:
        """Generate 4-5 targeted clarifying questions based on initial AI analysis.

        Returns list of {id, question, type, options?, placeholder?} dicts.
        The questions help narrow the ICP before hunting.
        """
        icp = initial_analysis.get("icp_profile", {})
        prompt = f"""Based on this product analysis, generate 5 targeted questions to ask the user
to NARROW DOWN and VALIDATE the Ideal Customer Profile before we start searching.

PRODUCT: {product_name}
DESCRIPTION: {description[:500]}
INITIAL ICP:
- Industries: {icp.get('industries', [])}
- Titles: {icp.get('target_titles', [])}
- Company Sizes: {icp.get('company_sizes', [])}
- Pain Points: {icp.get('pain_points', [])}

RULES:
- Questions should help us understand WHO specifically to target
- Include geographic focus, industry specifics, decision-maker roles
- Each question should have pre-filled options from the analysis PLUS an "Other" option
- Question types: "multi_select" (pick multiple), "single_select" (pick one), "text" (free input)
- Keep questions SHORT and CLEAR
- Questions should be in the SAME LANGUAGE as the product description

Return JSON:
{{
    "questions": [
        {{
            "id": "target_geography",
            "question": "Which regions/countries do you want to target?",
            "type": "multi_select",
            "options": ["United States", "Europe", "Turkey", "Global", "Other"]
        }},
        {{
            "id": "target_industry",
            "question": "Which industries are your ideal customers in?",
            "type": "multi_select",
            "options": ["Industry1", "Industry2", "Industry3", "Other"]
        }},
        {{
            "id": "target_role",
            "question": "What job titles should we target?",
            "type": "multi_select",
            "options": ["Title1", "Title2", "Title3", "Other"]
        }},
        {{
            "id": "company_size",
            "question": "What size companies are you targeting?",
            "type": "single_select",
            "options": ["1-10", "11-50", "51-200", "201-1000", "1000+", "Any"]
        }},
        {{
            "id": "additional_context",
            "question": "Any specific companies, competitors, or details to help narrow the search?",
            "type": "text",
            "placeholder": "e.g. Companies like Acme Corp, or competitors of XYZ..."
        }}
    ]
}}"""

        import asyncio
        try:
            response = await asyncio.wait_for(
                self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.4,
                        response_mime_type="application/json",
                    ),
                ),
                timeout=15,
            )
            result = json.loads(response.text.strip())
            return result.get("questions", self._fallback_questions(icp))
        except Exception as e:
            logger.warning(f"Question generation failed ({type(e).__name__}), using fallback")
            return self._fallback_questions(icp)

    @staticmethod
    def _fallback_questions(icp: dict) -> list[dict]:
        """Fallback questions when Gemini is unavailable."""
        industries = icp.get("industries", ["Technology", "SaaS", "Marketing"])
        titles = icp.get("target_titles", ["CEO", "Founder", "CTO"])
        sizes = icp.get("company_sizes", ["1-10", "11-50", "51-200"])

        return [
            {
                "id": "target_geography",
                "question": "Which regions do you want to target?",
                "type": "multi_select",
                "options": ["United States", "Europe", "Turkey", "Asia", "Global", "Other"],
            },
            {
                "id": "target_industry",
                "question": "Which industries are your ideal customers in?",
                "type": "multi_select",
                "options": industries + ["Other"],
            },
            {
                "id": "target_role",
                "question": "What job titles should we target?",
                "type": "multi_select",
                "options": titles + ["Other"],
            },
            {
                "id": "company_size",
                "question": "What size companies are you targeting?",
                "type": "single_select",
                "options": sizes + ["Any"],
            },
            {
                "id": "additional_context",
                "question": "Any specific details to narrow the search?",
                "type": "text",
                "placeholder": "e.g. specific companies, competitors, geographic cities...",
            },
        ]

    async def refine_with_answers(self, product_name: str, description: str,
                                  initial_analysis: dict, user_answers: dict) -> dict:
        """Re-run ICP generation incorporating user's answers to clarifying questions.

        Args:
            user_answers: dict mapping question_id → answer (string or list of strings)
        """
        prompt = f"""You previously analyzed this product and generated an ICP. Now the user has answered
clarifying questions. Use their answers to generate a REFINED, MORE SPECIFIC ICP and search strategy.

PRODUCT: {product_name}
DESCRIPTION: {description[:500]}

PREVIOUS ICP:
{json.dumps(initial_analysis.get('icp_profile', {}), indent=2)}

USER'S ANSWERS TO CLARIFYING QUESTIONS:
{json.dumps(user_answers, indent=2, ensure_ascii=False)}

IMPORTANT RULES:
- The user's answers OVERRIDE the previous analysis where they conflict
- If user specified geography, add geographic terms to search queries
- If user specified specific industries, ONLY target those industries
- If user specified job titles, use THOSE titles (not generic ones)
- Generate MORE search queries (at least 8 linkedin + 8 google) for better coverage
- Search queries must be SPECIFIC enough to find REAL PEOPLE, not generic pages
- Include the user's additional context in query generation

Respond with this exact JSON structure:
{{
    "value_proposition": {{
        "summary": "Updated one paragraph summary",
        "core_benefit": "Updated single biggest benefit",
        "differentiators": ["Updated differentiators"]
    }},
    "target_market": {{
        "primary_segments": ["Refined segments"],
        "market_size_estimate": "Small/Medium/Large",
        "urgency_level": "Low/Medium/High"
    }},
    "icp_profile": {{
        "industries": ["ONLY industries from user's answer"],
        "company_sizes": ["ONLY sizes from user's answer"],
        "target_titles": ["ONLY titles from user's answer"],
        "pain_points": ["Refined pain points"],
        "buying_signals": ["Refined buying signals"],
        "keywords": ["Refined, industry-specific keywords"],
        "negative_signals": ["Refined negative signals"],
        "geography": ["From user's answer"]
    }},
    "search_strategies": {{
        "linkedin_queries": ["At least 8 specific LinkedIn search queries"],
        "google_queries": ["At least 8 specific Google dorking queries"],
        "content_topics": ["Relevant content topics"],
        "competitor_products": ["Known competitors"],
        "communities": ["Where these people hang out"]
    }},
    "outreach_angles": {{
        "primary_hook": "Refined main angle",
        "follow_up_angles": ["Alternative angles"],
        "objection_preempts": ["Common objections"]
    }}
}}"""

        import asyncio
        try:
            response = await asyncio.wait_for(
                self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json",
                    ),
                ),
                timeout=20,
            )
            result = json.loads(response.text.strip())
            logger.info(f"ICP refined with user answers for: {product_name}")
            return result
        except Exception as e:
            logger.warning(f"ICP refinement failed ({type(e).__name__}), merging answers manually")
            return self._manual_refine(initial_analysis, user_answers)

    @staticmethod
    def _manual_refine(initial_analysis: dict, user_answers: dict) -> dict:
        """Fallback: manually merge user answers into existing analysis."""
        result = {**initial_analysis}
        icp = {**result.get("icp_profile", {})}
        strategies = {**result.get("search_strategies", {})}

        if "target_industry" in user_answers:
            ans = user_answers["target_industry"]
            if isinstance(ans, list):
                icp["industries"] = [a for a in ans if a != "Other"]
            elif isinstance(ans, str) and ans != "Other":
                icp["industries"] = [ans]

        if "target_role" in user_answers:
            ans = user_answers["target_role"]
            if isinstance(ans, list):
                icp["target_titles"] = [a for a in ans if a != "Other"]
            elif isinstance(ans, str) and ans != "Other":
                icp["target_titles"] = [ans]

        if "company_size" in user_answers:
            ans = user_answers["company_size"]
            if isinstance(ans, list):
                icp["company_sizes"] = [a for a in ans if a != "Any"]
            elif isinstance(ans, str) and ans != "Any":
                icp["company_sizes"] = [ans]

        if "target_geography" in user_answers:
            ans = user_answers["target_geography"]
            if isinstance(ans, list):
                icp["geography"] = [a for a in ans if a != "Other"]
            elif isinstance(ans, str) and ans != "Other":
                icp["geography"] = [ans]

        # Rebuild search queries with refined ICP
        industries = icp.get("industries", ["Technology"])
        titles = icp.get("target_titles", ["CEO"])
        geography = icp.get("geography", [])
        geo_str = f' "{geography[0]}"' if geography else ""

        linkedin_queries = []
        google_queries = []
        for ind in industries[:3]:
            for title in titles[:3]:
                linkedin_queries.append(f'site:linkedin.com/in "{title}" "{ind}"{geo_str}')
                google_queries.append(f'"{title}" "{ind}" email contact{geo_str}')

        strategies["linkedin_queries"] = linkedin_queries
        strategies["google_queries"] = google_queries

        result["icp_profile"] = icp
        result["search_strategies"] = strategies
        result["_fallback"] = True
        return result

    # ── Caching ───────────────────────────────────────────

    @staticmethod
    def _cache_key(product_name: str, description: str) -> str:
        """Generate deterministic cache key from product name + description."""
        raw = f"{product_name}::{description}".strip().lower()
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def analyze_with_cache(self, product_name: str, description: str, db_product=None) -> dict:
        """Analyze product with caching. Skips Gemini if cached result exists and input unchanged.

        Args:
            product_name: Product name string.
            description: Raw product description from user.
            db_product: Optional SQLAlchemy Product instance for cache read/write.
                        Caller is responsible for db.commit() after this returns.

        Returns:
            Full analysis dict (same shape as analyze()).
        """
        cache_key = self._cache_key(product_name, description)

        # Check existing cache on the product row
        if db_product is not None and db_product.analysis_cache:
            cached = db_product.analysis_cache
            if isinstance(cached, dict) and cached.get("_cache_key") == cache_key:
                logger.info(f"ICP cache HIT for product '{product_name}' (key={cache_key})")
                return cached

        # Cache MISS — call Gemini
        logger.info(f"ICP cache MISS for product '{product_name}' (key={cache_key})")
        result = await self.analyze(product_name, description)

        # Stamp cache key into result for future validation
        result["_cache_key"] = cache_key

        # Persist full result to product.analysis_cache
        if db_product is not None:
            db_product.analysis_cache = result

        return result

    # ── Fallback ─────────────────────────────────────────

    @staticmethod
    def _fallback_analysis(product_name: str, description: str) -> dict:
        """Fallback when Gemini API is unavailable.

        Extracts meaningful keywords from description by filtering stopwords
        and short tokens, so dorking queries actually return results.
        """
        import re

        # Extract meaningful keywords (not stopwords)
        stopwords = {
            'we', 'sell', 'an', 'a', 'the', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'to',
            'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'between',
            'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'each', 'every', 'all', 'any', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'only', 'own', 'same', 'than', 'too',
            'very', 'just', 'because', 'if', 'when', 'while', 'how', 'what',
            'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'it', 'its',
            'our', 'your', 'their', 'my', 'his', 'her', 'our', 'they', 'them',
            'i', 'me', 'you', 'he', 'she', 'us', 'about', 'up', 'out', 'off',
            'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
            'also', 'need', 'like', 'get', 'make', 'many', 'much', 'well', 'way',
            'use', 'using', 'used', 'one', 'two', 'three', 'new', 'first', 'last',
        }
        raw_words = re.findall(r'[a-z][a-z-]+', description.lower())
        keywords = [w for w in raw_words if w not in stopwords and len(w) >= 4]
        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        keywords = unique_keywords[:10]

        # Detect industries and titles from description
        desc_lower = description.lower()
        detected_industries = []
        industry_map = {
            'saas': 'SaaS', 'b2b': 'B2B', 'marketing': 'Marketing',
            'e-commerce': 'E-commerce', 'ecommerce': 'E-commerce',
            'fintech': 'Fintech', 'healthcare': 'Healthcare',
            'real estate': 'Real Estate', 'education': 'Education',
            'technology': 'Technology', 'agency': 'Marketing Agency',
            'software': 'Software', 'retail': 'Retail',
        }
        for key, label in industry_map.items():
            if key in desc_lower and label not in detected_industries:
                detected_industries.append(label)
        if not detected_industries:
            detected_industries = ['Technology', 'Marketing', 'E-commerce']

        detected_titles = []
        title_signals = {
            'ceo': 'CEO', 'founder': 'Founder', 'cto': 'CTO', 'cmo': 'CMO',
            'marketing manager': 'Marketing Manager', 'sales': 'VP Sales',
            'growth': 'Head of Growth', 'operations': 'Operations Manager',
            'director': 'Marketing Director', 'owner': 'Business Owner',
            'head of': 'Department Head',
        }
        for key, label in title_signals.items():
            if key in desc_lower and label not in detected_titles:
                detected_titles.append(label)
        if not detected_titles:
            detected_titles = ['CEO', 'Founder', 'Marketing Manager']

        return {
            "value_proposition": {
                "summary": f"{product_name}: {description[:200]}",
                "core_benefit": f"{product_name} provides unique value to its target market",
                "differentiators": ["Unique approach", "Innovative solution"],
            },
            "target_market": {
                "primary_segments": ["Small businesses", "Startups"],
                "market_size_estimate": "Medium",
                "urgency_level": "Medium",
            },
            "icp_profile": {
                "industries": detected_industries[:5],
                "company_sizes": ["1-10", "11-50", "51-200"],
                "target_titles": detected_titles[:5],
                "pain_points": ["Efficiency", "Growth", "Cost reduction"],
                "buying_signals": ["Hiring", "Funding", "Expansion"],
                "keywords": keywords,
                "negative_signals": ["Enterprise only", "Government"],
            },
            "search_strategies": {
                "linkedin_queries": [
                    f'"{detected_titles[0]}" "{detected_industries[0]}"',
                    f'"{detected_titles[1] if len(detected_titles) > 1 else "Founder"}" "{keywords[0] if keywords else "software"}"',
                ],
                "google_queries": [
                    f'"{detected_industries[0]}" "{detected_titles[0]}" email OR contact',
                    f'site:linkedin.com/in "{detected_titles[0]}" "{keywords[0] if keywords else "software"}"',
                ],
                "content_topics": keywords[:3] if keywords else ["business growth", "efficiency"],
                "competitor_products": [],
                "communities": ["LinkedIn groups", "Reddit"],
            },
            "outreach_angles": {
                "primary_hook": f"Noticed your work in {detected_industries[0]} — {product_name} might help",
                "follow_up_angles": ["ROI focused", "Case study based"],
                "objection_preempts": ["Budget concerns", "Already have a solution"],
            },
            "_fallback": True,
            "_message": "AI analysis unavailable (rate limited). Basic analysis generated. Re-analyze when quota resets.",
        }
