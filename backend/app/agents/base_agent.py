"""
HUNTER.OS / ARES - Base Agent (Gemini ReAct Pattern)
Reason & Act loop with full step history forwarding.
Includes LLM cost tracking and budget enforcement.
"""
import json
import logging
import asyncio
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_agent_output(raw_output, schema_class) -> dict:
    """Validate and parse agent output against a Pydantic schema.

    Accepts either a raw JSON string or an already-parsed dict/list.
    Returns a validated dict (via model_dump).
    Raises ValueError with details on validation failure.

    Usage:
        from app.schemas.agent_outputs import ICPAnalysis
        validated = validate_agent_output(gemini_response_text, ICPAnalysis)
    """
    import json as _json

    try:
        data = _json.loads(raw_output) if isinstance(raw_output, str) else raw_output
    except _json.JSONDecodeError as e:
        raise ValueError(f"Agent output is not valid JSON: {e}")

    if isinstance(data, dict):
        validated = schema_class.model_validate(data)
        return validated.model_dump()

    raise ValueError(f"Expected dict, got {type(data).__name__}")


@dataclass
class AgentAction:
    tool: str
    tool_input: dict
    reasoning: str


@dataclass
class AgentObservation:
    tool: str
    output: Any
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentStep:
    action: AgentAction
    observation: AgentObservation


def _extract_token_counts(response) -> tuple[int, int]:
    """
    Extract input/output token counts from a Gemini response.
    Returns (input_tokens, output_tokens). Falls back to (0, 0) if unavailable.
    """
    try:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return 0, 0
        input_tokens = getattr(meta, "prompt_token_count", 0) or 0
        output_tokens = getattr(meta, "candidates_token_count", 0) or 0
        return input_tokens, output_tokens
    except Exception:
        return 0, 0


def record_llm_usage(
    user_id: Optional[int],
    agent_name: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """
    Record LLM token usage for a user. Gracefully skips if user_id is None
    or if the tracker/DB is unavailable.
    """
    if user_id is None:
        return
    if input_tokens == 0 and output_tokens == 0:
        return
    try:
        from app.core.database import SessionLocal
        from app.services.llm_cost_tracker import llm_cost_tracker

        db = SessionLocal()
        try:
            llm_cost_tracker.record_usage(db, user_id, agent_name, input_tokens, output_tokens)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to record LLM usage: {e}")


def check_llm_budget_sync(user_id: Optional[int], plan: Optional[str]) -> None:
    """
    Synchronous budget check before an LLM call.
    Raises HTTPException 402 if budget is exhausted.
    Gracefully skips if user_id/plan is None.
    """
    if user_id is None or plan is None:
        return
    try:
        from app.core.database import SessionLocal
        from app.core.llm_budget_guard import check_llm_budget

        db = SessionLocal()
        try:
            check_llm_budget(user_id, plan, db)
        finally:
            db.close()
    except Exception as e:
        # Re-raise HTTP exceptions (budget exceeded), swallow others
        from fastapi import HTTPException
        if isinstance(e, HTTPException):
            raise
        logger.warning(f"Budget check failed (allowing call): {e}")


class ReActAgent:
    """
    Gemini-based ReAct Agent.

    Loop:
    1. THINK: Reason about what to do next
    2. ACT: Choose and execute a tool
    3. OBSERVE: Process the tool output
    4. REPEAT until FINISH

    Key fix: full step history is forwarded to Gemini on every turn
    so the agent remembers what it already did.
    """

    def __init__(
        self,
        system_prompt: str,
        tools: dict[str, Callable],
        max_steps: int = 10,
        model: Optional[str] = None,
        user_id: Optional[int] = None,
        user_plan: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_steps = max_steps
        self.user_id = user_id
        self.user_plan = user_plan
        self.agent_name = agent_name or self.__class__.__name__

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = model or settings.GEMINI_MODEL
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt,
        )
        self.steps: list[AgentStep] = []
        self.final_answer: Optional[str] = None

    def _compress_history(self, steps: list[AgentStep]) -> str:
        """Compress older steps into a summary to reduce token usage."""
        if len(steps) <= 3:
            return ""

        old_steps = steps[:-3]
        summaries = []
        for i, step in enumerate(old_steps):
            tool = step.action.tool
            thought = step.action.reasoning[:100]
            obs_str = str(step.observation.output)[:200]
            summaries.append(f"Step {i+1} [{tool}]: {thought}... → {obs_str}...")

        return "PREVIOUS RESEARCH SUMMARY (compressed):\n" + "\n".join(summaries)

    def _build_tool_descriptions(self) -> str:
        descriptions = []
        for name, func in self.tools.items():
            doc = func.__doc__ or "No description."
            descriptions.append(f"- {name}: {doc.strip()}")
        return "\n".join(descriptions)

    def _build_gemini_history(self, task: str) -> list[dict]:
        """
        Build Gemini-compatible message list with FULL step history.
        Each prior step becomes a user/model turn pair so the agent
        never forgets what it already discovered.
        """
        tool_desc = self._build_tool_descriptions()

        initial_prompt = f"""You are a ReAct agent. Solve the following task step by step.

## Available Tools:
{tool_desc}

## Response Format (strict JSON):
To use a tool:
{{"thought": "your reasoning", "action": "tool_name", "action_input": {{"param": "value"}}}}

To give the final answer:
{{"thought": "your reasoning", "action": "FINISH", "action_input": {{"answer": "your final structured answer"}}}}

## Task:
{task}"""

        history: list[dict] = []

        # First turn: user gives the task
        history.append({"role": "user", "parts": [initial_prompt]})

        if len(self.steps) > 4:
            # Compress older steps to reduce token usage
            summary = self._compress_history(self.steps)
            history.append({"role": "model", "parts": [json.dumps({
                "thought": "Reviewing previous research...",
                "action": "REVIEW",
                "action_input": {},
            }, ensure_ascii=False)]})
            history.append({"role": "user", "parts": [summary + "\n\nContinue with the next step."]})

            # Only replay last 3 steps in full
            recent_steps = self.steps[-3:]
        else:
            recent_steps = self.steps

        # Replay steps as model-response + user-observation
        for step in recent_steps:
            # Model's action
            model_json = json.dumps({
                "thought": step.action.reasoning,
                "action": step.action.tool,
                "action_input": step.action.tool_input,
            }, ensure_ascii=False)
            history.append({"role": "model", "parts": [model_json]})

            # User relays the observation
            obs_text = json.dumps(step.observation.output, default=str, ensure_ascii=False)
            history.append({"role": "user", "parts": [f"Observation from '{step.action.tool}':\n{obs_text}\n\nContinue with the next step."]})

        return history

    async def run(self, task: str) -> str:
        """Execute the ReAct loop."""
        logger.info(f"ARES agent starting: {task[:80]}...")

        for step_num in range(self.max_steps):
            # Budget check before each LLM call
            check_llm_budget_sync(self.user_id, self.user_plan)

            history = self._build_gemini_history(task)

            try:
                response = await self.model.generate_content_async(
                    history,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )

                # Track token usage
                input_tokens, output_tokens = _extract_token_counts(response)
                record_llm_usage(self.user_id, self.agent_name, input_tokens, output_tokens)

                raw_text = response.text.strip()
                parsed = json.loads(raw_text)

                thought = parsed.get("thought", "")
                action = parsed.get("action", "")
                action_input = parsed.get("action_input", {})

                logger.info(f"  Step {step_num + 1}: [{action}] {thought[:80]}")

                # FINISH → return the answer
                if action == "FINISH":
                    answer = action_input.get("answer", "")
                    # If answer is already a dict/list, re-serialize for downstream
                    if isinstance(answer, (dict, list)):
                        self.final_answer = json.dumps(answer, ensure_ascii=False)
                    else:
                        self.final_answer = str(answer)
                    return self.final_answer

                # Execute tool
                if action in self.tools:
                    tool_func = self.tools[action]
                    try:
                        if asyncio.iscoroutinefunction(tool_func):
                            result = await tool_func(**action_input)
                        else:
                            result = tool_func(**action_input)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"
                        logger.warning(f"  Tool '{action}' raised: {e}")
                else:
                    result = f"Unknown tool: {action}. Available: {list(self.tools.keys())}"

                # Record step
                self.steps.append(AgentStep(
                    action=AgentAction(tool=action, tool_input=action_input, reasoning=thought),
                    observation=AgentObservation(tool=action, output=result),
                ))

            except json.JSONDecodeError as e:
                logger.error(f"  JSON parse error at step {step_num + 1}: {e}")
                # Give the agent one more chance by recording the error
                self.steps.append(AgentStep(
                    action=AgentAction(tool="PARSE_ERROR", tool_input={}, reasoning="Failed to parse JSON"),
                    observation=AgentObservation(tool="PARSE_ERROR", output=f"Your last response was not valid JSON: {e}. Please respond with valid JSON only."),
                ))
            except Exception as e:
                # Re-raise HTTP 402 (budget exceeded) so callers see it
                from fastapi import HTTPException
                if isinstance(e, HTTPException):
                    raise
                logger.error(f"  Agent error at step {step_num + 1}: {e}")
                return json.dumps({"error": str(e)})

        return json.dumps({"error": "Agent reached maximum steps without finishing."})

    def get_trace(self) -> list[dict]:
        """Get full execution trace for debugging."""
        return [
            {
                "step": i + 1,
                "thought": s.action.reasoning,
                "action": s.action.tool,
                "input": s.action.tool_input,
                "observation": s.observation.output,
            }
            for i, s in enumerate(self.steps)
        ]
