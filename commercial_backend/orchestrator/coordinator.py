"""RX-Coordinator — routes user questions through Foundry prompt agents.

Flow: User Question -> RX-QueryEngine (Prompt Agent, returns DAX in markers)
                    -> Coordinator extracts DAX + executes against Power BI
                    -> RX-Analyst (Prompt Agent, interprets raw data)
                    -> Adaptive Card

Both agents are Foundry Prompt Agents created via the new Foundry portal
experience. They are invoked via the OpenAI Responses API with an
`agent_reference` (by display name). No tools; Coordinator does all deterministic
DAX extraction and execution between the two agents.
"""

import json
import os
import re
import httpx
import structlog
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient

from commercial_backend.bot.turn_state import ConversationState
from commercial_backend.bot.adaptive_cards import build_insight_card, build_error_card, build_greeting_card
from commercial_backend.orchestrator.response_formatter import parse_analyst_response
from commercial_backend.tools.pbi_execute_query import execute_dax_query

logger = structlog.get_logger(__name__)

# Foundry agent call timeouts — generous read timeout (agents can take 60-90s+
# to generate long DAX queries) but tight connect timeout to fail fast on
# network issues from outside-region clients.
_FOUNDRY_TIMEOUT = httpx.Timeout(timeout=600.0, connect=30.0)

# Marker-delimited DAX contract between RX-QueryEngine and the Coordinator.
DAX_START_MARKER = "=== DAX START ==="
DAX_END_MARKER = "=== DAX END ==="
CANNOT_ANSWER_SENTINEL = "CANNOT_ANSWER"

# Simple greeting patterns — answered immediately without calling any LLM.
_GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening|day)|"
    r"what'?s\s+up|sup|yo|salaam|مرحبا|اهلا)\W*\s*$",
    re.IGNORECASE,
)

_DAX_BLOCK_RE = re.compile(
    rf"{re.escape(DAX_START_MARKER)}\s*(.*?)\s*{re.escape(DAX_END_MARKER)}",
    re.DOTALL | re.IGNORECASE,
)

# ── Domain routing ───────────────────────────────────────────────────────
# Keyword fast-path — used before falling back to an LLM tiebreaker classifier.
# Matches are case-insensitive.
_GX_KEYWORDS_RE = re.compile(
    r"\b(satisf\w+|csat|nps|survey(s)?|sentiment|review(s)?|jamila|"
    r"guest(\s+experience)?|response\s+rate|cabin\s+rating|service\s+quality|"
    r"feedback|stars?\s+rating|complaint(s)?|net\s+promoter)\b",
    re.IGNORECASE,
)
_COMMERCIAL_KEYWORDS_RE = re.compile(
    r"\b(revenue|booking(s)?|load\s+factor|yield|rask|prask|fare(s)?|"
    r"ancillary|channel|distribution|forecast|capacity|asks|rpks|"
    r"market\s+share|pos\b|point\s+of\s+sale|sector\s+revenue|seat\s+sold)\b",
    re.IGNORECASE,
)

_DOMAIN_CLASSIFIER_PROMPT = (
    "You are a router for an airline analytics chatbot. Classify the user's "
    "question into exactly ONE of these domains and reply with only that single "
    "word (lowercase, no punctuation):\n"
    "  - commercial         (revenue, bookings, load factor, yield, fares, capacity)\n"
    "  - guest_experience   (satisfaction surveys, sentiment, reviews, CSAT, response rate)\n"
    "\nIf truly ambiguous, default to 'commercial'."
)


def _agent_reference(name: str) -> dict:
    """Build the extra_body payload for invoking a Foundry Prompt Agent by name."""
    return {"agent_reference": {"name": name, "type": "agent_reference"}}


class Coordinator:
    """Deterministic router — no LLM reasoning at this layer.

    1. Sends user question to RX-QueryEngine prompt agent.
    2. Parses DAX from `=== DAX START === / === DAX END ===` markers.
    3. Executes DAX against Power BI (with RLS via impersonatedUser).
    4. Feeds original question + DAX + raw result into RX-Analyst prompt agent.
    5. Parses Analyst output into an Adaptive Card.
    """

    def __init__(self) -> None:
        self.project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
        # Per-domain config: each entry maps to its own pair of Foundry Prompt
        # Agents and its own Power BI workspace + dataset. Add new domains here.
        self.domains = {
            "commercial": {
                "query_engine": os.environ["FOUNDRY_QUERY_ENGINE_AGENT_ID"],
                "analyst": os.environ["FOUNDRY_ANALYST_AGENT_ID"],
                "workspace_id": os.environ["PBI_WORKSPACE_ID"],
                "dataset_id": os.environ["PBI_DATASET_ID"],
                "cannot_answer_message": (
                    "The Routes Insights - Flyr model does not contain the data "
                    "needed to answer that question."
                ),
            },
            "guest_experience": {
                "query_engine": os.environ.get(
                    "FOUNDRY_GX_QUERY_ENGINE_AGENT_ID", "RX-GX-QEngine"
                ),
                "analyst": os.environ.get(
                    "FOUNDRY_GX_ANALYST_AGENT_ID", "RX-GX-Analyst"
                ),
                "workspace_id": os.environ.get("PBI_GX_WORKSPACE_ID", ""),
                "dataset_id": os.environ.get("PBI_GX_DATASET_ID", ""),
                "cannot_answer_message": (
                    "The RX Guest Experience model does not contain the data "
                    "needed to answer that question."
                ),
            },
        }
        # Back-compat aliases — kept so any existing tests/imports still work.
        self.query_engine_agent_name = self.domains["commercial"]["query_engine"]
        self.analyst_agent_name = self.domains["commercial"]["analyst"]

    async def _classify_domain(self, question: str, openai_client) -> str:
        """Decide which domain config (commercial vs guest_experience) to use.

        Two-stage:
          1. Keyword fast-path — deterministic, ~0ms.
          2. LLM tiebreaker     — only if both regexes miss or both hit.
        """
        gx_hit = bool(_GX_KEYWORDS_RE.search(question))
        comm_hit = bool(_COMMERCIAL_KEYWORDS_RE.search(question))

        if gx_hit and not comm_hit:
            logger.info("domain_classified", method="keyword", domain="guest_experience")
            return "guest_experience"
        if comm_hit and not gx_hit:
            logger.info("domain_classified", method="keyword", domain="commercial")
            return "commercial"

        # Ambiguous (both or neither) — fall back to a tiny LLM call.
        try:
            resp = await openai_client.responses.create(
                model="gpt-5.4-mini",
                input=f"{_DOMAIN_CLASSIFIER_PROMPT}\n\nQuestion: {question}",
                timeout=httpx.Timeout(timeout=15.0, connect=5.0),
            )
            answer = (resp.output_text or "").strip().lower()
            domain = "guest_experience" if "guest" in answer else "commercial"
            logger.info("domain_classified", method="llm", raw=answer[:40], domain=domain)
            return domain
        except Exception as e:
            # On any failure, default to commercial (the original, well-tested path).
            logger.warning("domain_classifier_failed", error=str(e), default="commercial")
            return "commercial"

    async def process(
        self,
        user_question: str,
        state: ConversationState,
        user_principal_name: str | None = None,
    ) -> dict:
        """Run the full pipeline and return a dict with 'card', 'dax', 'summary'."""
        credential = DefaultAzureCredential()

        # Short-circuit for greetings — no LLM call needed.
        if _GREETING_RE.match(user_question.strip()):
            logger.info("greeting_detected", question=user_question[:60])
            return {"card": build_greeting_card(), "dax": "", "summary": "", "data": []}

        # [DEBUG] tracks the active pipeline step for error attribution
        _step = "init"

        try:
            async with AIProjectClient(
                endpoint=self.project_endpoint,
                credential=credential,
            ) as project_client:
                openai_client = project_client.get_openai_client()

                # -- Step 0: classify domain (commercial vs guest_experience) --
                _step = "domain_classification"
                domain = await self._classify_domain(user_question, openai_client)
                cfg = self.domains[domain]

                # -- Step 1: QueryEngine (Prompt Agent -> DAX text) --
                _step = "query_engine"
                logger.info(
                    "invoking_query_engine",
                    domain=domain,
                    agent=cfg["query_engine"],
                    question=user_question[:100],
                )

                qe_resp = await openai_client.responses.create(
                    input=user_question,
                    extra_body=_agent_reference(cfg["query_engine"]),
                    timeout=_FOUNDRY_TIMEOUT,
                )
                qe_response = qe_resp.output_text or ""

                logger.info(
                    "query_engine_complete",
                    response_length=len(qe_response),
                )

                # -- Step 2: Parse + execute DAX --
                _step = "dax_extraction"
                dax = self._extract_dax_from_markers(qe_response)

                if dax.strip().upper() == CANNOT_ANSWER_SENTINEL:
                    reason = self._extract_reason(qe_response)
                    logger.info("query_engine_cannot_answer", domain=domain, reason=reason)
                    message = reason or cfg["cannot_answer_message"]
                    card = build_error_card(message)
                    return {"card": card, "dax": "", "summary": reason or ""}

                if not dax:
                    logger.error(
                        "query_engine_missing_dax_markers",
                        domain=domain,
                        response=qe_response[:500],
                    )
                    card = build_error_card(
                        "QueryEngine did not return DAX between the expected === DAX START === / === DAX END === markers."
                    )
                    return {"card": card, "dax": "", "summary": ""}

                _step = "pbi_execution"
                logger.info("executing_dax", domain=domain, dax=dax[:200])
                pbi_result = await execute_dax_query(
                    dax,
                    user_principal_name=user_principal_name,
                    workspace_id=cfg["workspace_id"] or None,
                    dataset_id=cfg["dataset_id"] or None,
                )

                # -- Step 3: Analyst (Prompt Agent -> domain-specific narrative) --
                _step = "analyst"
                logger.info("invoking_analyst", domain=domain, agent=cfg["analyst"])

                analyst_prompt = (
                    f"Original question: {user_question}\n\n"
                    f"DAX executed:\n```dax\n{dax}\n```\n\n"
                    f"Raw result (JSON):\n{json.dumps(pbi_result, default=str)}"
                )

                analyst_resp = await openai_client.responses.create(
                    input=analyst_prompt,
                    extra_body=_agent_reference(cfg["analyst"]),
                    timeout=_FOUNDRY_TIMEOUT,
                )
                analyst_response = analyst_resp.output_text or ""

                logger.info(
                    "analyst_complete",
                    response_length=len(analyst_response),
                )

                # -- Step 4: Format -> Adaptive Card --
                _step = "response_formatting"
                parsed = parse_analyst_response(analyst_response)

                card = build_insight_card(
                    question=user_question,
                    summary=parsed["summary"],
                    findings=parsed["findings"],
                    flags=parsed.get("flags"),
                    recommendation=parsed.get("recommendation"),
                    dax=dax,
                )

                return {
                    "card": card,
                    "dax": dax,
                    "summary": parsed["summary"],
                    # Raw PBI rows for the web frontend to draw charts/tables.
                    # Shape: list of {col: value, ...} dicts. May be empty.
                    "data": pbi_result.get("tables", []) if isinstance(pbi_result, dict) else [],
                }

        except Exception:
            # [DEBUG] re-raise with step context so chat.py can log it precisely
            logger.error("coordinator_step_failed", step=_step, exc_info=True)
            raise

        finally:
            await credential.close()

    def _extract_dax_from_markers(self, qe_response: str) -> str:
        """Extract DAX between === DAX START === / === DAX END === markers."""
        match = _DAX_BLOCK_RE.search(qe_response)
        if not match:
            return ""
        inner = match.group(1).strip()
        inner = re.sub(r"^```(?:dax)?\s*", "", inner, flags=re.IGNORECASE)
        inner = re.sub(r"\s*```$", "", inner)
        return inner.strip()

    def _extract_reason(self, qe_response: str) -> str:
        """Extract the `Reason: ...` line after a CANNOT_ANSWER block."""
        for line in qe_response.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("reason:"):
                return stripped[len("reason:"):].strip()
        return ""