"""
Serverless Telegram Career Coach Assistant.

Runs as a single Google Cloud Function (2nd gen, HTTP trigger). Telegram
delivers every update to this function via webhook; the function replies by
calling the Telegram Bot API directly with `requests`.

Design notes
------------
* No database. Per-chat state (pending /optimize_bullet input, mock-interview
  progress) lives in a process-local dict. Deploy with --max-instances=1 so
  every update reaches the same instance. State is lost when the instance is
  recycled (cold start after idling); the bot tells users to /mock_interview
  again in that case.
* No LLM. Bullet optimisation and interview critiques are rule-based and
  deterministic, so the function is cheap, fast and has no API keys besides
  the bot token.
* Security. Telegram's `secret_token` (set via setWebhook) is sent in the
  X-Telegram-Bot-Api-Secret-Token header and compared in constant time.
  /check_portfolio refuses private, loopback and link-local addresses so the
  function cannot be used to probe Google's internal network (SSRF).

Environment variables
---------------------
TELEGRAM_BOT_TOKEN  Bot token from @BotFather (required).
WEBHOOK_SECRET      Same value passed as `secret_token` to setWebhook (required).
PORTFOLIO_URL       Optional default URL for /check_portfolio with no argument.
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import os
import re
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import functions_framework
import requests
from flask import Request
from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("career_coach")

TELEGRAM_API_BASE = "https://api.telegram.org"
# Telegram rejects messages longer than 4096 characters; leave headroom.
TELEGRAM_MAX_MESSAGE_CHARS = 4000
# (connect timeout, read timeout) for every outbound HTTP call.
HTTP_TIMEOUT = (3.05, 10)
# Chats with no activity for this long are evicted from memory.
SESSION_TTL_SECONDS = 2 * 60 * 60
# Answers shorter than this are bounced back instead of being graded.
MIN_ANSWER_WORDS = 15
MAX_PORTFOLIO_REDIRECTS = 5


# ---------------------------------------------------------------------------
# Telegram update models (only the fields this bot reads)
# ---------------------------------------------------------------------------

class TelegramUser(BaseModel):
    id: int
    first_name: str = ""


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    message_id: int
    chat: TelegramChat
    # "from" is a Python keyword, hence the alias.
    from_user: Optional[TelegramUser] = Field(default=None, alias="from")
    text: Optional[str] = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None


# ---------------------------------------------------------------------------
# In-memory chat state
# ---------------------------------------------------------------------------

@dataclass
class QuestionResult:
    """Grades for one answered (or skipped) interview question."""
    question_index: int
    skipped: bool
    scores: dict[str, int] = field(default_factory=dict)
    overall: float = 0.0


@dataclass
class ChatState:
    awaiting_bullet: bool = False
    interview_active: bool = False
    question_index: int = 0
    results: list[QuestionResult] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)


_states: dict[int, ChatState] = {}
_states_lock = threading.Lock()

# Telegram retries an update if it does not get a 2xx in time; remember recent
# update_ids so a retry is not processed (and answered) twice.
_recent_update_ids: deque[int] = deque(maxlen=500)
_recent_update_ids_set: set[int] = set()
_recent_lock = threading.Lock()


def _get_state(chat_id: int) -> ChatState:
    """Return the chat's state, creating it and evicting stale chats."""
    now = time.time()
    with _states_lock:
        stale = [cid for cid, st in _states.items() if now - st.last_seen > SESSION_TTL_SECONDS]
        for cid in stale:
            del _states[cid]
        state = _states.setdefault(chat_id, ChatState())
        state.last_seen = now
        return state


def _is_duplicate_update(update_id: int) -> bool:
    with _recent_lock:
        if update_id in _recent_update_ids_set:
            return True
        if len(_recent_update_ids) == _recent_update_ids.maxlen:
            _recent_update_ids_set.discard(_recent_update_ids[0])
        _recent_update_ids.append(update_id)
        _recent_update_ids_set.add(update_id)
        return False


# ---------------------------------------------------------------------------
# Telegram Bot API client
# ---------------------------------------------------------------------------

def _bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def _redact(text: str) -> str:
    """Strip the bot token from strings before they reach the logs.

    requests' exception messages include the request path, and the Bot API
    puts the token in the path.
    """
    token = _bot_token()
    return text.replace(token, "<redacted>") if token else text


def _split_message(text: str, limit: int = TELEGRAM_MAX_MESSAGE_CHARS) -> list[str]:
    """Split text into Telegram-sized chunks, preferring paragraph then line breaks."""
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n\n", 0, limit)
        if cut <= 0:
            cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip("\n")
    if remaining.strip():
        chunks.append(remaining)
    return chunks


def send_message(chat_id: int, text: str) -> None:
    """Send plain text (no parse_mode, so user input never breaks formatting)."""
    token = _bot_token()
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set; cannot reply to chat %s", chat_id)
        return
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    for chunk in _split_message(text):
        try:
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
                timeout=HTTP_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.error("sendMessage failed: HTTP %s %s", resp.status_code, _redact(resp.text[:300]))
                return
        except requests.RequestException as exc:
            logger.error("sendMessage error: %s: %s", type(exc).__name__, _redact(str(exc)))
            return


# ---------------------------------------------------------------------------
# Shared text-analysis vocabulary
# ---------------------------------------------------------------------------

# Each pattern detects one kind of quantified evidence. Recruiters and
# interviewers look for at least one of these in every bullet / story.
METRIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "percentage": re.compile(r"\b\d+(?:\.\d+)?\s?%", re.I),
    "multiplier": re.compile(r"\b\d+(?:\.\d+)?\s?x\b", re.I),
    "currency": re.compile(
        r"[$€£]\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|b|million|billion|thousand)?\b", re.I
    ),
    "duration": re.compile(
        r"\b\d+(?:\.\d+)?\s?(?:ms|milliseconds?|seconds?|secs?|s|minutes?|mins?|hours?|hrs?"
        r"|days?|weeks?|months?|quarters?)\b",
        re.I,
    ),
    "scale": re.compile(
        r"\b\d[\d,]*(?:\.\d+)?\s?(?:k|m|b|million|billion|thousand)?\+?\s?"
        r"(?:users|customers|requests|rps|qps|tps|events|records|rows|transactions|services"
        r"|microservices|engineers|developers|teams|servers|nodes|pods|clusters|deployments"
        r"|deploys|tickets|calls|messages|queries|repositories|repos|endpoints|tb|gb|pb"
        r"|countries|regions|markets|partners|stakeholders|incidents|pages|alerts)\b",
        re.I,
    ),
    "before_after": re.compile(r"\bfrom\s+[$€£]?\d[\d,.]*\s?\w*\s+to\s+[$€£]?\d[\d,.]*", re.I),
    "percentile": re.compile(r"\bp(?:50|75|90|95|99|999)\b", re.I),
}

# Words that sound like impact but carry no number. Flagged so the user
# replaces them with evidence.
VAGUE_QUANTIFIERS = [
    "significantly", "a lot", "lots of", "many", "huge", "massive", "greatly",
    "much faster", "much better", "substantially", "dramatically", "tons of",
    "considerably", "vastly", "drastically", "improved performance", "various",
]

# Canonical spelling for technologies. Matching is case-insensitive except
# for entries in CASE_SENSITIVE_TECH, which collide with ordinary words.
TECH_TERMS = [
    "Python", "Golang", "Java", "Kotlin", "TypeScript", "JavaScript", "Rust", "C++", "C#",
    "Scala", "SQL", "PostgreSQL", "Postgres", "MySQL", "Redis", "Memcached", "Kafka",
    "Spark", "Flink", "Airflow", "dbt", "Kubernetes", "K8s", "Docker", "Terraform",
    "Ansible", "Helm", "Istio", "Envoy", "AWS", "GCP", "Azure", "Lambda", "Cloud Run",
    "BigQuery", "Snowflake", "Redshift", "DynamoDB", "Cassandra", "MongoDB",
    "Elasticsearch", "OpenSearch", "RabbitMQ", "Pub/Sub", "SQS", "gRPC", "GraphQL",
    "REST", "React", "Next.js", "Node.js", "Django", "FastAPI", "Flask", "Spring Boot",
    "CI/CD", "Jenkins", "GitHub Actions", "ArgoCD", "Prometheus", "Grafana", "Datadog",
    "OpenTelemetry", "Nginx", "Linux", "TensorFlow", "PyTorch", "microservices",
    "event-driven", "serverless",
]
CASE_SENSITIVE_TECH = {"REST", "SQL", "dbt"}

# Engineering-depth vocabulary that is not a product name.
DEPTH_TERMS = [
    "latency", "throughput", "p99", "p95", "slo", "sla", "sli", "idempoten*", "consisten*",
    "availability", "durability", "replica*", "partition*", "shard*", "cache", "caching",
    "queue", "backpressure", "retry", "retries", "circuit breaker", "rate limit*",
    "load balanc*", "autoscal*", "observability", "tracing", "metrics", "dashboard*",
    "alert*", "trade-off*", "tradeoff*", "bottleneck*", "profil*", "benchmark*",
    "schema", "index*", "concurrency", "deadlock*", "race condition*", "failover",
    "canary", "feature flag*", "rollback", "blue-green", "postmortem", "root cause",
    "design doc*", "rfc", "api contract*", "backward compatib*",
]


def _keyword_regex(keyword: str) -> re.Pattern[str]:
    """Build a word-bounded regex. A trailing '*' means "this prefix + any suffix"."""
    if keyword.endswith("*"):
        return re.compile(r"(?<!\w)" + re.escape(keyword[:-1]) + r"\w*", re.I)
    return re.compile(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", re.I)


_TECH_REGEXES = [
    (term, re.compile(r"(?<![\w.])" + re.escape(term) + r"(?![\w+#])",
                      0 if term in CASE_SENSITIVE_TECH else re.I))
    for term in TECH_TERMS
]
_DEPTH_REGEXES = [(term.rstrip("*"), _keyword_regex(term)) for term in DEPTH_TERMS]
_VAGUE_REGEXES = [(term, _keyword_regex(term)) for term in VAGUE_QUANTIFIERS]


def find_metrics(text: str) -> dict[str, list[str]]:
    """Return {metric_type: [matched strings]} for every metric type present."""
    found: dict[str, list[str]] = {}
    for kind, pattern in METRIC_PATTERNS.items():
        matches = [m.group(0).strip() for m in pattern.finditer(text)]
        if matches:
            found[kind] = matches
    return found


def find_tech(text: str) -> list[str]:
    return [term for term, rx in _TECH_REGEXES if rx.search(text)]


def find_depth_terms(text: str) -> list[str]:
    return [term for term, rx in _DEPTH_REGEXES if rx.search(text)]


def find_vague(text: str) -> list[str]:
    return [term for term, rx in _VAGUE_REGEXES if rx.search(text)]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


# ---------------------------------------------------------------------------
# /optimize_bullet: rule-based resume bullet rewriter
# ---------------------------------------------------------------------------

# (present, past, gerund, category). Past tense is the resume convention;
# the gerund is needed for the impact-first rewrite ("Reduced X by migrating Y").
STRONG_VERBS: list[tuple[str, str, str, str]] = [
    # Leadership and ownership
    ("lead", "Led", "leading", "leadership"),
    ("spearhead", "Spearheaded", "spearheading", "leadership"),
    ("direct", "Directed", "directing", "leadership"),
    ("mentor", "Mentored", "mentoring", "leadership"),
    ("champion", "Championed", "championing", "leadership"),
    ("drive", "Drove", "driving", "leadership"),
    ("orchestrate", "Orchestrated", "orchestrating", "leadership"),
    ("own", "Owned", "owning", "leadership"),
    ("coordinate", "Coordinated", "coordinating", "leadership"),
    # Building
    ("build", "Built", "building", "build"),
    ("architect", "Architected", "architecting", "build"),
    ("design", "Designed", "designing", "build"),
    ("engineer", "Engineered", "engineering", "build"),
    ("develop", "Developed", "developing", "build"),
    ("implement", "Implemented", "implementing", "build"),
    ("launch", "Launched", "launching", "build"),
    ("ship", "Shipped", "shipping", "build"),
    ("create", "Created", "creating", "build"),
    ("deliver", "Delivered", "delivering", "build"),
    ("prototype", "Prototyped", "prototyping", "build"),
    ("write", "Wrote", "writing", "build"),
    # Performance and cost
    ("optimize", "Optimized", "optimizing", "performance"),
    ("reduce", "Reduced", "reducing", "performance"),
    ("accelerate", "Accelerated", "accelerating", "performance"),
    ("improve", "Improved", "improving", "performance"),
    ("streamline", "Streamlined", "streamlining", "performance"),
    ("cut", "Cut", "cutting", "performance"),
    ("eliminate", "Eliminated", "eliminating", "performance"),
    ("boost", "Boosted", "boosting", "performance"),
    ("increase", "Increased", "increasing", "performance"),
    ("scale", "Scaled", "scaling", "performance"),
    ("tune", "Tuned", "tuning", "performance"),
    # Migration and modernisation
    ("migrate", "Migrated", "migrating", "migration"),
    ("modernize", "Modernized", "modernizing", "migration"),
    ("refactor", "Refactored", "refactoring", "migration"),
    ("consolidate", "Consolidated", "consolidating", "migration"),
    ("rewrite", "Rewrote", "rewriting", "migration"),
    ("upgrade", "Upgraded", "upgrading", "migration"),
    # Automation and integration
    ("automate", "Automated", "automating", "automation"),
    ("instrument", "Instrumented", "instrumenting", "automation"),
    ("integrate", "Integrated", "integrating", "automation"),
    ("deploy", "Deployed", "deploying", "automation"),
    ("containerize", "Containerized", "containerizing", "automation"),
    # Reliability, analysis and security
    ("analyze", "Analyzed", "analyzing", "reliability"),
    ("diagnose", "Diagnosed", "diagnosing", "reliability"),
    ("resolve", "Resolved", "resolving", "reliability"),
    ("debug", "Debugged", "debugging", "reliability"),
    ("investigate", "Investigated", "investigating", "reliability"),
    ("secure", "Secured", "securing", "reliability"),
    ("harden", "Hardened", "hardening", "reliability"),
    ("stabilize", "Stabilized", "stabilizing", "reliability"),
]

_VERB_BY_PRESENT = {v[0]: v for v in STRONG_VERBS}
_VERB_BY_PAST = {v[1].lower(): v for v in STRONG_VERBS}
_VERB_BY_GERUND = {v[2]: v for v in STRONG_VERBS}

# Weak openers, longest first so "was responsible for" wins over "responsible for".
# Value is the replacement used when the remainder is a noun phrase; when the
# remainder starts with a verb ("responsible for building X") that verb is used.
WEAK_OPENERS: list[tuple[str, str]] = [
    ("was responsible for", "Owned"),
    ("responsible for", "Owned"),
    ("was in charge of", "Owned"),
    ("in charge of", "Owned"),
    ("was tasked with", "Owned"),
    ("tasked with", "Owned"),
    ("was involved in", "Contributed to"),
    ("involved in", "Contributed to"),
    ("participated in", "Contributed to"),
    ("was part of", "Contributed to"),
    ("part of", "Contributed to"),
    ("contributed to", "Contributed to"),
    ("worked on", "Engineered"),
    ("working on", "Engineered"),
    ("worked with", "Collaborated with"),
    ("helped to", "Partnered on"),
    ("helped with", "Partnered on"),
    ("helped", "Partnered on"),
    ("assisted with", "Partnered on"),
    ("assisted in", "Partnered on"),
    ("assisted", "Partnered on"),
    ("utilized", "Leveraged"),
    ("used", "Leveraged"),
    ("handled", "Managed"),
    ("made", "Built"),
    ("did", "Executed"),
    ("got", "Achieved"),
]

# Openers after which a following verb should be kept but prefixed, because
# the user did not do it alone ("helped migrate X" -> "Partnered to migrate X").
COLLABORATIVE_OPENERS = {"helped to", "helped with", "helped", "assisted with", "assisted in", "assisted"}

# Keyword stems used to pick a verb when the bullet starts with a bare noun phrase.
CATEGORY_HINTS: list[tuple[str, list[str]]] = [
    ("performance", ["latency", "performance", "faster", "speed", "slow", "optimiz", "cost",
                     "p99", "throughput", "memory", "cpu", "load time"]),
    ("migration", ["migrat", "legacy", "monolith", "upgrade", "modernize", "deprecat"]),
    ("automation", ["automat", "pipeline", "ci/cd", "script", "workflow", "deploy", "tooling"]),
    ("leadership", ["team", "mentor", "hiring", "cross-functional", "roadmap", "stakeholder"]),
    ("reliability", ["outage", "incident", "reliab", "uptime", "on-call", "sla", "slo", "bug"]),
]
DEFAULT_VERB_BY_CATEGORY = {
    "performance": "Optimized",
    "migration": "Migrated",
    "automation": "Automated",
    "leadership": "Led",
    "reliability": "Hardened",
    "build": "Engineered",
}

# Filler that adds length without information.
FILLER_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsuccessfully\s+", re.I), ""),
    (re.compile(r"\bvery\s+", re.I), ""),
    (re.compile(r"\breally\s+", re.I), ""),
    (re.compile(r"\bbasically\s+", re.I), ""),
    (re.compile(r"\bactually\s+", re.I), ""),
    (re.compile(r"\bin order to\b", re.I), "to"),
    (re.compile(r"\ba lot of\b", re.I), "extensive"),
    (re.compile(r"\blots of\b", re.I), "extensive"),
    (re.compile(r"\butilizing\b", re.I), "using"),
    (re.compile(r"\butilize[sd]?\b", re.I), "use"),
    (re.compile(r"\s{2,}"), " "),
]

# Clauses that introduce the outcome. Value is the normalised connector and
# the past-tense verb used to lead with impact in the alternative rewrite.
RESULT_CONNECTORS: list[tuple[str, str, str]] = [
    ("which resulted in", "resulting in", "Delivered"),
    ("that resulted in", "resulting in", "Delivered"),
    ("and resulted in", "resulting in", "Delivered"),
    ("resulting in", "resulting in", "Delivered"),
    ("which led to", "driving", "Drove"),
    ("that led to", "driving", "Drove"),
    ("leading to", "driving", "Drove"),
    ("and reduced", "reducing", "Reduced"),
    ("and increased", "increasing", "Increased"),
    ("and improved", "improving", "Improved"),
    ("and cut", "cutting", "Cut"),
    ("and saved", "saving", "Saved"),
    ("and boosted", "boosting", "Boosted"),
    ("which reduced", "reducing", "Reduced"),
    ("which increased", "increasing", "Increased"),
    ("which improved", "improving", "Improved"),
    ("which cut", "cutting", "Cut"),
    ("which saved", "saving", "Saved"),
    ("reducing", "reducing", "Reduced"),
    ("increasing", "increasing", "Increased"),
    ("improving", "improving", "Improved"),
    ("cutting", "cutting", "Cut"),
    ("saving", "saving", "Saved"),
    ("boosting", "boosting", "Boosted"),
    ("achieving", "achieving", "Achieved"),
    ("enabling", "enabling", "Enabled"),
]

# Questions that prompt the user to dig up the number they left out.
METRIC_PROMPTS_BY_CATEGORY = {
    "performance": [
        "Latency before → after (e.g. p99 820ms → 310ms)?",
        "Throughput change (requests/sec, jobs/hour)?",
        "Infrastructure cost saved per month or year?",
    ],
    "migration": [
        "How many services, tables or users were migrated?",
        "Downtime during cutover (ideally zero) and how long the migration took?",
        "What did it unlock: cost saved, deploy frequency, incidents avoided?",
    ],
    "automation": [
        "Hours of manual work removed per week?",
        "Deploy frequency or lead time before → after?",
        "Error rate of the manual process vs. the automated one?",
    ],
    "leadership": [
        "Team size and number of partner teams involved?",
        "Delivery date hit or pulled in by how much?",
        "Business result: revenue, adoption, retention, promotions of mentees?",
    ],
    "reliability": [
        "Availability before → after (e.g. 99.5% → 99.95%)?",
        "Incidents or pages per month before → after?",
        "MTTR / MTTD reduction?",
    ],
    "build": [
        "How many users, requests or teams use what you built?",
        "Revenue, conversion or engagement it drove?",
        "Time-to-market vs. the estimate or the previous approach?",
    ],
}

SCOPE_WORDS = re.compile(
    r"\b(users|customers|teams?|engineers|org|company-wide|global|production|enterprise"
    r"|platform|services|regions|million|billion|cross-functional)\b",
    re.I,
)


def _infer_category(text: str) -> str:
    lower = text.lower()
    best, best_hits = "build", 0
    for category, stems in CATEGORY_HINTS:
        hits = sum(1 for stem in stems if stem in lower)
        if hits > best_hits:
            best, best_hits = category, hits
    return best


def _lookup_verb(word: str) -> Optional[tuple[str, str, str, str]]:
    """Match a word in any tense (present, past, gerund) to a strong verb."""
    w = word.lower().strip(",.;:")
    if w in _VERB_BY_PRESENT:
        return _VERB_BY_PRESENT[w]
    if w in _VERB_BY_PAST:
        return _VERB_BY_PAST[w]
    if w in _VERB_BY_GERUND:
        return _VERB_BY_GERUND[w]
    # Third-person present ("builds", "optimizes").
    if w.endswith("es") and w[:-2] in _VERB_BY_PRESENT:
        return _VERB_BY_PRESENT[w[:-2]]
    if w.endswith("s") and w[:-1] in _VERB_BY_PRESENT:
        return _VERB_BY_PRESENT[w[:-1]]
    return None


def _clean_bullet(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^[\s\-•*·–—>]+", "", text)          # leading bullet glyphs
    text = re.sub(r"^(?:i|we)\s+(?=\w)", "", text, flags=re.I)  # resumes omit pronouns
    for pattern, replacement in FILLER_REWRITES:
        text = pattern.sub(replacement, text)
    return text.strip().rstrip(".;")


def _rewrite_opening(text: str) -> tuple[str, str, Optional[str]]:
    """Return (lead_verb_phrase, remainder, gerund_of_lead_verb).

    The gerund is None when the lead phrase cannot be turned into "by <gerund>"
    cleanly (e.g. "Contributed to").
    """
    lower = text.lower()
    for opener, fallback in WEAK_OPENERS:
        if lower.startswith(opener + " "):
            remainder = text[len(opener):].strip()
            first, _, rest = remainder.partition(" ")
            verb = _lookup_verb(first)
            if verb and opener in COLLABORATIVE_OPENERS:
                return f"Partnered to {verb[0]}", rest, f"partnering to {verb[0]}"
            if verb:
                return verb[1], rest, verb[2]
            gerund = _VERB_BY_PAST.get(fallback.lower(), (None, None, None))[2]
            return fallback, remainder, gerund

    first, _, rest = text.partition(" ")
    verb = _lookup_verb(first)
    if verb:
        return verb[1], rest, verb[2]

    # No verb at all: pick one from the subject matter.
    lead = DEFAULT_VERB_BY_CATEGORY[_infer_category(text)]
    gerund = _VERB_BY_PAST[lead.lower()][2]
    return lead, text, gerund


def _split_result(body: str) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Split "<action>, <connector> <result>" -> (action, connector, impact_verb, result)."""
    lower = body.lower()
    earliest: Optional[tuple[int, str, str, str]] = None
    for phrase, connector, impact_verb in RESULT_CONNECTORS:
        match = re.search(r"(?:,\s*|\s+)" + re.escape(phrase) + r"\s+", lower)
        if match and (earliest is None or match.start() < earliest[0]):
            earliest = (match.start(), connector, impact_verb, body[match.end():])
    if earliest is None:
        return body, None, None, None
    start, connector, impact_verb, result = earliest
    return body[:start].strip(" ,"), connector, impact_verb, result.strip()


def score_bullet(text: str) -> tuple[int, list[tuple[str, bool, str]]]:
    """Score 0-100 and return a checklist of (criterion, passed, hint)."""
    first_word = text.split(" ", 1)[0] if text else ""
    starts_strong = _lookup_verb(first_word) is not None and not any(
        text.lower().startswith(op + " ") for op, _ in WEAK_OPENERS
    )
    metrics = find_metrics(text)
    tech = find_tech(text)
    has_result = any(re.search(r"\b" + re.escape(p) + r"\b", text, re.I) for p, _, _ in RESULT_CONNECTORS) \
        or bool(metrics)
    has_scope = bool(SCOPE_WORDS.search(text))
    words = word_count(text)
    good_length = 12 <= words <= 35
    vague = find_vague(text)

    checks = [
        ("Opens with a strong past-tense action verb", starts_strong, "Lead with what YOU did: Led, Built, Cut…"),
        ("Contains a hard metric", bool(metrics), "Add a %, $, time, or scale number."),
        ("Names specific technology", bool(tech), "Name the stack (e.g. Kafka, Kubernetes, PostgreSQL)."),
        ("States an outcome", has_result, "Say what changed because of the work."),
        ("Shows scope / scale", has_scope, "Mention users, teams, services or traffic affected."),
        ("12–35 words", good_length, f"Currently {words} words."),
        ("No vague quantifiers", not vague, f"Replace: {', '.join(vague)}" if vague else ""),
    ]
    weights = [20, 30, 15, 15, 10, 5, 5]
    score = sum(w for w, (_, passed, _) in zip(weights, checks) if passed)
    return score, checks


def optimize_bullet(raw: str) -> str:
    """Rewrite a raw achievement into a resume bullet and explain the changes."""
    cleaned = _clean_bullet(raw)
    if word_count(cleaned) < 4:
        return ("That's too short to optimise. Describe what you did, with what technology, "
                "and what changed. Example:\n/optimize_bullet worked on the checkout service, "
                "moved it to Kubernetes and reduced deploy time from 40 minutes to 6 minutes")

    lead, body, lead_gerund = _rewrite_opening(cleaned)
    action, connector, impact_verb, result = _split_result(body)

    if connector and result:
        rewritten = f"{lead} {action}, {connector} {result}"
    else:
        rewritten = f"{lead} {body}"
    rewritten = re.sub(r"\s{2,}", " ", rewritten).strip()

    # Impact-first variant (Google's "Accomplished X, as measured by Y, by doing Z")
    # only when the outcome is quantified; leading with an unquantified result is weaker.
    impact_first = None
    # A comma in the action means a list of clauses that won't read well after "by".
    if connector and result and lead_gerund and find_metrics(result) and "," not in action:
        impact_first = f"{impact_verb} {result} by {lead_gerund} {action}"
        impact_first = re.sub(r"\s{2,}", " ", impact_first).strip()

    before_score, _ = score_bullet(cleaned)
    after_score, checks = score_bullet(rewritten)
    category = _infer_category(cleaned)

    lines = [
        "✍️ Bullet optimiser",
        "",
        "Original:",
        f"• {raw.strip()}",
        "",
        "Rewritten:",
        f"• {rewritten}",
    ]
    if impact_first:
        lines += ["", "Impact-first variant:", f"• {impact_first}"]
    lines += ["", f"Impact score: {before_score}/100 → {after_score}/100", ""]
    for label, passed, hint in checks:
        mark = "✅" if passed else "❌"
        lines.append(f"{mark} {label}" + ("" if passed or not hint else f" — {hint}"))

    if not find_metrics(rewritten):
        lines += ["", "This bullet still has no number. Answer one of these and resend it:"]
        lines += [f"  • {q}" for q in METRIC_PROMPTS_BY_CATEGORY[category]]
    if lead in ("Contributed to", "Partnered on") or lead.startswith("Partnered to"):
        lines += ["", "Ownership tip: say which part was yours (e.g. \"Designed the retry layer of…\") "
                      "rather than describing team-wide participation."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# /check_portfolio: uptime probe with SSRF protection
# ---------------------------------------------------------------------------

class UnsafeTargetError(ValueError):
    """Raised when a URL resolves to a non-public address."""


def _assert_public_host(hostname: str, port: int) -> None:
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeTargetError(f"DNS lookup failed for {hostname}: {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise UnsafeTargetError(f"{hostname} resolves to a non-public address ({ip}).")


def _normalise_url(raw: str) -> str:
    url = raw.strip().strip("<>")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeTargetError("Only http:// and https:// URLs can be checked.")
    if not parsed.hostname:
        raise UnsafeTargetError("That doesn't look like a valid URL.")
    return url


def check_portfolio(raw_url: str) -> str:
    """Probe a site, following redirects manually so every hop is validated."""
    try:
        url = _normalise_url(raw_url)
    except UnsafeTargetError as exc:
        return f"❌ {exc}"

    hops: list[str] = []
    started = time.perf_counter()
    try:
        for _ in range(MAX_PORTFOLIO_REDIRECTS + 1):
            parsed = urlparse(url)
            _assert_public_host(parsed.hostname or "", parsed.port or (443 if parsed.scheme == "https" else 80))
            resp = requests.get(
                url,
                timeout=HTTP_TIMEOUT,
                allow_redirects=False,
                stream=True,  # status + headers only; never download a large body
                headers={"User-Agent": "CareerCoachBot-UptimeCheck/1.0"},
            )
            resp.close()
            if resp.is_redirect and resp.headers.get("Location"):
                hops.append(f"{resp.status_code} → {resp.headers['Location']}")
                url = _normalise_url(urljoin(url, resp.headers["Location"]))
                continue
            break
        else:
            return f"❌ DOWN — more than {MAX_PORTFOLIO_REDIRECTS} redirects (possible redirect loop)."
    except UnsafeTargetError as exc:
        return f"❌ Refused: {exc}"
    except requests.exceptions.SSLError:
        return f"❌ DOWN — TLS/SSL handshake failed for {url}. Check the certificate is valid and not expired."
    except requests.exceptions.ConnectTimeout:
        return f"❌ DOWN — connection to {url} timed out after {HTTP_TIMEOUT[0]}s."
    except requests.exceptions.ReadTimeout:
        return f"⚠️ DEGRADED — {url} accepted the connection but didn't respond within {HTTP_TIMEOUT[1]}s."
    except requests.exceptions.ConnectionError:
        return f"❌ DOWN — could not connect to {url} (DNS, refused connection or network error)."
    except requests.RequestException as exc:
        return f"❌ DOWN — request failed: {type(exc).__name__}."

    elapsed_ms = (time.perf_counter() - started) * 1000
    status = resp.status_code
    if 200 <= status < 300:
        verdict = "✅ UP"
    elif status in (401, 403):
        verdict = "⚠️ REACHABLE but access-restricted — recruiters may not be able to see it"
    elif 400 <= status < 500:
        verdict = "❌ BROKEN — client error (wrong URL or missing page)"
    else:
        verdict = "❌ DOWN — server error"

    lines = [
        "🌐 Portfolio uptime check",
        "",
        verdict,
        f"Final URL: {url}",
        f"HTTP status: {status} {resp.reason or ''}".rstrip(),
        f"Total response time: {elapsed_ms:.0f} ms",
        f"HTTPS: {'yes' if url.startswith('https://') else 'NO — serve over HTTPS; browsers flag HTTP as not secure'}",
    ]
    if hops:
        lines.append(f"Redirects ({len(hops)}):")
        lines += [f"  {hop}" for hop in hops]
    if 200 <= status < 300 and elapsed_ms > 2500:
        lines.append("⚠️ Slow first response (>2.5s). A recruiter may bounce; consider a CDN or static hosting.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# /mock_interview: question bank
# ---------------------------------------------------------------------------

# Each question carries:
#   category   – shown to the user and used in the final summary
#   question   – the prompt
#   look_for   – what a strong (hire-level) answer contains, shown after grading
#   keywords   – domain vocabulary that signals depth for THIS question
#                (trailing * = prefix match)
INTERVIEW_QUESTIONS: list[dict] = [
    {
        "category": "Situational — Incident Response",
        "question": (
            "Tell me about a time a production system you owned failed at scale. "
            "Walk me through how it was detected, how you mitigated customer impact, "
            "how you found the root cause, and what you changed permanently so it could not recur."
        ),
        "look_for": [
            "Clear blast radius: users/requests affected and for how long",
            "Mitigation before root-causing (rollback, feature-flag off, failover)",
            "A specific root cause, not 'a bug' — the mechanism",
            "Time to detect and time to mitigate, in minutes",
            "Durable fixes: alerting, tests, guardrails, runbooks — and who owned them",
        ],
        "keywords": [
            "alert*", "on-call", "pager*", "rollback", "rolled back", "root cause", "postmortem",
            "slo", "error rate", "latency", "mitigat*", "runbook", "dashboard*",
            "blast radius", "incident commander", "mttr", "mttd", "feature flag*", "failover",
        ],
    },
    {
        "category": "Architecture — Distributed System Design",
        "question": (
            "Describe the most complex distributed system you designed end to end. "
            "What consistency, availability and partition-tolerance trade-offs did you make, "
            "what alternatives did you reject, and how did you validate the design under real load?"
        ),
        "look_for": [
            "The requirements that drove the design (QPS, data size, latency budget, durability)",
            "At least one explicitly rejected alternative and why",
            "Consistency model chosen and how failures/partitions are handled",
            "Validation: load tests, chaos/failure injection, shadow traffic",
            "Numbers on the result: p99, availability, cost",
        ],
        "keywords": [
            "consisten*", "eventual*", "strong consistency", "replica*", "partition*", "cap",
            "quorum", "idempoten*", "shard*", "cache", "queue", "throughput", "p99", "latency",
            "leader election", "consensus", "raft", "paxos", "exactly-once", "at-least-once",
            "load test*", "chaos", "trade-off*", "tradeoff*", "alternative*",
        ],
    },
    {
        "category": "Architecture — Scaling",
        "question": (
            "Tell me about a time you had to scale a service by 10x or more. "
            "Where were the bottlenecks, how did you find them with data rather than guesses, "
            "and what did you change in the architecture?"
        ),
        "look_for": [
            "Starting and target load with units (e.g. 2k → 25k RPS)",
            "Profiling/observability evidence that located the bottleneck",
            "Changes at the right layer: caching, sharding, async, connection pooling, indexes",
            "Load-test results proving headroom before launch",
            "Cost implications of the new architecture",
        ],
        "keywords": [
            "profil*", "bottleneck*", "horizontal*", "vertical*", "shard*", "cache", "caching",
            "load test*", "autoscal*", "connection pool*", "index*", "throughput", "latency",
            "rps", "qps", "cpu", "memory", "async*", "batch*", "read replica*", "cdn", "headroom",
        ],
    },
    {
        "category": "Architecture — Zero-Downtime Migration",
        "question": (
            "Walk me through a large migration you led — monolith to services, on-prem to cloud, "
            "or one datastore to another. How did you de-risk it, keep it zero-downtime, "
            "and prove data parity before the final cutover?"
        ),
        "look_for": [
            "A phased plan with explicit rollback at each phase",
            "Dual writes / CDC / backfill strategy and how drift was detected",
            "Shadow reads or traffic mirroring to compare behaviour",
            "Percent-based rollout with success criteria for each step",
            "Timeline, team size, and what was decommissioned at the end",
        ],
        "keywords": [
            "dual write*", "dual-write*", "shadow*", "feature flag*", "canary", "backfill*",
            "rollback", "cutover", "parity", "phase*", "cdc", "change data capture", "strangler",
            "mirror*", "reconcil*", "decommission*", "percent*", "rollout",
        ],
    },
    {
        "category": "Cross-functional — Conflict Resolution",
        "question": (
            "Tell me about a time you strongly disagreed with a product manager or another team's "
            "tech lead on a critical decision. How did you make your case, how was it resolved, "
            "and what happened as a result?"
        ),
        "look_for": [
            "The other side's position stated fairly — you understood their goals",
            "Data or a prototype used to argue, not seniority or opinion",
            "A mechanism: design doc, decision record, experiment, escalation path",
            "Disagree-and-commit if you lost, and how you supported the decision",
            "The measurable outcome and the relationship afterwards",
        ],
        "keywords": [
            "data", "trade-off*", "tradeoff*", "align*", "stakeholder*", "compromis*", "escalat*",
            "design doc*", "rfc", "disagree and commit", "experiment*", "a/b", "prototype",
            "their perspective", "customer", "decision record", "adr", "1:1", "one-on-one",
        ],
    },
    {
        "category": "Leadership — Influence Without Authority",
        "question": (
            "Describe a time you had to get several teams that did not report to you to change "
            "their roadmap for a technical initiative you believed in. How did you build buy-in "
            "and keep momentum?"
        ),
        "look_for": [
            "Why it mattered to THEM, not just to you (incentives, their pain)",
            "A written proposal and how feedback changed it",
            "Lowering adoption cost: tooling, migration guides, doing the first one yourself",
            "Tracking adoption with a metric and a cadence",
            "Final adoption numbers and business impact",
        ],
        "keywords": [
            "roadmap", "align*", "rfc", "proposal", "buy-in", "stakeholder*", "dependenc*",
            "incentive*", "okr*", "adoption", "sponsor*", "executive*", "working group",
            "office hours", "migration guide*", "tooling", "cadence", "feedback",
        ],
    },
    {
        "category": "Situational — Ambiguity and Deadlines",
        "question": (
            "Describe a project where requirements were ambiguous but the deadline was fixed. "
            "How did you decide what to build, what to cut, and how did you communicate risk "
            "to stakeholders along the way?"
        ),
        "look_for": [
            "How you reduced ambiguity: customer conversations, data, spikes",
            "An explicit MVP and an explicit cut list",
            "Milestones and early-warning signals for schedule risk",
            "Proactive communication with dates — not surprises at the end",
            "Shipped scope vs. original ask and the outcome",
        ],
        "keywords": [
            "mvp", "scope", "prioriti*", "milestone*", "risk*", "stakeholder*", "cut", "trade-off*",
            "tradeoff*", "iterat*", "spike", "assumption*", "customer*", "status update*",
            "deadline", "descop*", "phase*",
        ],
    },
    {
        "category": "Leadership — Raising the Engineering Bar",
        "question": (
            "Tell me about a time you measurably raised the engineering bar of your team — "
            "through mentorship, code-review culture, testing standards or architecture reviews. "
            "How did you measure that it worked?"
        ),
        "look_for": [
            "A baseline problem with evidence (defect rate, review time, onboarding time)",
            "A concrete mechanism you introduced, not just 'I led by example'",
            "How you brought people along rather than mandating",
            "A before → after metric (e.g. DORA metrics, escaped defects)",
            "People outcomes: mentees promoted, new owners of systems",
        ],
        "keywords": [
            "mentor*", "code review*", "standard*", "onboarding", "documentation", "promot*",
            "velocity", "defect*", "dora", "lead time", "change failure rate", "deploy frequency",
            "test coverage", "linting", "guideline*", "brown bag", "pairing", "architecture review*",
        ],
    },
    {
        "category": "Situational — Owning a Wrong Decision",
        "question": (
            "Tell me about a significant technical decision you made that turned out to be wrong. "
            "How did you discover it, what did it cost, and what did you do about it?"
        ),
        "look_for": [
            "A real mistake with real cost — not a humble-brag",
            "The signal that revealed it and how quickly you acted",
            "Taking ownership publicly",
            "The correction and how you limited further damage",
            "What you now do differently, with an example of applying it since",
        ],
        "keywords": [
            "assumption*", "data", "rollback", "learn*", "postmortem", "revisit*", "cost",
            "retrospective", "mistake", "ownership", "own it", "signal*", "metric*", "revert*",
            "reversible", "one-way door", "two-way door", "since then",
        ],
    },
    {
        "category": "Architecture — Cost and Performance Optimisation",
        "question": (
            "Describe a time you significantly reduced the cost or latency of a system. "
            "How did you identify the opportunity, how did you make the change safely, "
            "and how did you verify the savings in production?"
        ),
        "look_for": [
            "How the opportunity was found (profiling, billing breakdown, traces)",
            "The specific technical change and why it worked",
            "Safety: benchmarks, canary, guarding against regressions",
            "Verified before → after numbers in production, not estimates",
            "Annualised dollar or user-facing impact",
        ],
        "keywords": [
            "profil*", "benchmark*", "p99", "p95", "cost", "rightsiz*", "caching", "cache",
            "batch*", "observability", "dashboard*", "a/b", "canary", "flame graph*", "trac*",
            "billing", "reserved instance*", "spot", "autoscal*", "compression", "query plan*",
            "index*", "regression*",
        ],
    },
]


# ---------------------------------------------------------------------------
# /mock_interview: grading rubric
# ---------------------------------------------------------------------------

# Phrases that signal each STAR component. Hits are counted; 0 = missing,
# 1 = present but thin, 2+ = clearly present.
STAR_SIGNALS: dict[str, list[re.Pattern[str]]] = {
    "Situation": [re.compile(p, re.I) for p in [
        r"\bat my (?:previous|last|current) (?:company|job|role|team)\b", r"\bwhen i was\b",
        r"\bour (?:team|system|service|platform|company)\b", r"\bthe situation\b", r"\bcontext\b",
        r"\bwe were\b", r"\bat the time\b", r"\bthere was\b", r"\bbackground\b", r"\bback in\b",
        r"\bin (?:19|20)\d\d\b", r"\bat [A-Z]\w+\b",
    ]],
    "Task": [re.compile(p, re.I) for p in [
        r"\bmy (?:goal|task|job|responsibility|role) was\b", r"\bi was (?:responsible|asked|tasked)\b",
        r"\bi needed to\b", r"\bi had to\b", r"\bthe (?:goal|objective|challenge|problem) was\b",
        r"\bi owned\b", r"\bwe needed to\b", r"\bthe requirement\b", r"\bdeadline\b",
        r"\bsuccess (?:criteria|metric)\b",
    ]],
    "Action": [re.compile(p, re.I) for p in [
        r"\bi (?:\w+ed|built|led|wrote|drove|ran|made|set up|took|chose|began|sought|brought|found"
        r"|spoke|met|split|cut|shipped|rewrote|sat down|reached out)\b",
        r"\bfirst,?\b", r"\bthen\b", r"\bnext,?\b", r"\bafter that\b", r"\bfinally\b",
        r"\bmy approach\b", r"\bi decided\b", r"\bi proposed\b",
    ]],
    "Result": [re.compile(p, re.I) for p in [
        r"\bas a result\b", r"\bresult(?:ed|ing)? in\b", r"\boutcome\b", r"\bin the end\b",
        r"\bultimately\b", r"\bwhich led to\b", r"\b(?:reduced|increased|improved|saved|cut|decreased"
        r"|eliminated|grew|doubled|tripled)\b", r"\d\s?%", r"\bwe (?:shipped|launched|delivered)\b",
        r"\bsince then\b", r"\bi learned\b", r"\blesson\b",
    ]],
}

DIMENSIONS = ["STAR structure", "Metric validation", "Technical depth", "Ownership", "Delivery"]
DIMENSION_WEIGHTS = {
    "STAR structure": 0.30,
    "Metric validation": 0.25,
    "Technical depth": 0.25,
    "Ownership": 0.10,
    "Delivery": 0.10,
}

# Coaching text per dimension for low scores (≤2) and middling scores (3).
DIMENSION_COACHING = {
    "STAR structure": {
        "low": "Structure every answer as: 1–2 sentences of Situation, 1 sentence of Task (your goal), "
               "60% of your time on Actions YOU took, and a Result with numbers.",
        "mid": "One STAR component is thin. Interviewers grade the Action and Result hardest — "
               "make sure each is explicit.",
    },
    "Metric validation": {
        "low": "No numbers means the interviewer cannot verify impact. Bring at least two: "
               "scale (users/RPS), a before → after, and money or time saved.",
        "mid": "You have a number — add a before → after comparison so the delta is unambiguous.",
    },
    "Technical depth": {
        "low": "The answer stays at the surface. Name the components, the failure modes, and the "
               "trade-offs you rejected. Senior bars expect 'why this and not that'.",
        "mid": "Good start. Go one layer deeper on the hardest technical decision and its alternatives.",
    },
    "Ownership": {
        "low": "Too much 'we'. The interviewer is hiring you — say 'I' for what you personally decided and did.",
        "mid": "Separate team context ('we') from your own decisions ('I') more clearly.",
    },
    "Delivery": {
        "low": "Aim for roughly 2–3 minutes spoken (≈250–400 words). Too short lacks evidence; "
               "too long loses the interviewer.",
        "mid": "Length is close — tighten the Situation and expand the Actions.",
    },
}

VERDICTS = [
    (4.3, "Strong Hire"),
    (3.6, "Hire"),
    (3.0, "Lean Hire"),
    (2.3, "Lean No Hire"),
    (0.0, "No Hire"),
]


def _verdict(score: float) -> str:
    return next(label for threshold, label in VERDICTS if score >= threshold)


def _grade_star(answer: str) -> tuple[int, dict[str, int]]:
    hits = {component: sum(len(p.findall(answer)) for p in patterns)
            for component, patterns in STAR_SIGNALS.items()}
    raw = sum(min(h, 2) for h in hits.values())  # 0..8
    return 1 + round(raw / 8 * 4), hits


def _grade_metrics(answer: str) -> tuple[int, dict[str, list[str]], list[str]]:
    metrics = find_metrics(answer)
    vague = find_vague(answer)
    total = sum(len(v) for v in metrics.values())
    distinct = len(metrics)
    if total == 0:
        score = 1
    elif total == 1:
        score = 2
    elif distinct == 1:
        score = 3
    elif distinct == 2:
        score = 4
    else:
        score = 5
    if len(vague) >= 2:
        score = max(1, score - 1)
    return score, metrics, vague


def _grade_depth(answer: str, question: dict) -> tuple[int, list[str], list[str]]:
    covered = [kw.rstrip("*") for kw in question["keywords"] if _keyword_regex(kw).search(answer)]
    missing = [kw.rstrip("*") for kw in question["keywords"] if kw.rstrip("*") not in covered]
    general = set(find_tech(answer)) | set(find_depth_terms(answer))
    general -= set(covered)
    points = len(covered) * 2 + len(general)
    if points == 0:
        score = 1
    elif points <= 2:
        score = 2
    elif points <= 4:
        score = 3
    elif points <= 7:
        score = 4
    else:
        score = 5
    return score, covered + sorted(general), missing


def _grade_ownership(answer: str) -> tuple[int, int, int]:
    i_count = len(re.findall(r"\b(?:i|i'm|i've|i'd|my|me|myself)\b", answer, re.I))
    we_count = len(re.findall(r"\b(?:we|we're|we've|we'd|our|us)\b", answer, re.I))
    if i_count + we_count == 0:
        return 2, i_count, we_count
    ratio = i_count / (i_count + we_count)
    if ratio >= 0.6:
        score = 5
    elif ratio >= 0.45:
        score = 4
    elif ratio >= 0.3:
        score = 3
    elif ratio >= 0.15:
        score = 2
    else:
        score = 1
    return score, i_count, we_count


def _grade_delivery(words: int) -> int:
    if 200 <= words <= 450:
        return 5
    if 120 <= words < 200 or 450 < words <= 550:
        return 4
    if 80 <= words < 120 or 550 < words <= 700:
        return 3
    return 2


def _coaching_line(dimension: str, score: int) -> Optional[str]:
    if score <= 2:
        return DIMENSION_COACHING[dimension]["low"]
    if score == 3:
        return DIMENSION_COACHING[dimension]["mid"]
    return None


def evaluate_answer(answer: str, question_index: int) -> tuple[QuestionResult, str]:
    """Grade an answer on five dimensions and return the result plus a critique."""
    question = INTERVIEW_QUESTIONS[question_index]
    words = word_count(answer)

    star_score, star_hits = _grade_star(answer)
    metric_score, metrics, vague = _grade_metrics(answer)
    depth_score, covered, missing = _grade_depth(answer, question)
    own_score, i_count, we_count = _grade_ownership(answer)
    delivery_score = _grade_delivery(words)

    scores = {
        "STAR structure": star_score,
        "Metric validation": metric_score,
        "Technical depth": depth_score,
        "Ownership": own_score,
        "Delivery": delivery_score,
    }
    overall = sum(scores[d] * DIMENSION_WEIGHTS[d] for d in DIMENSIONS)
    result = QuestionResult(question_index=question_index, skipped=False, scores=scores, overall=overall)

    total = len(INTERVIEW_QUESTIONS)
    lines = [
        f"📋 Feedback — Question {question_index + 1}/{total} ({question['category']})",
        f"Overall: {overall:.1f}/5 → {_verdict(overall)}",
        "",
        f"1) STAR structure: {star_score}/5",
    ]
    for component in ("Situation", "Task", "Action", "Result"):
        h = star_hits[component]
        if h >= 2:
            lines.append(f"   ✅ {component} — clearly present")
        elif h == 1:
            lines.append(f"   ⚠️ {component} — present but thin")
        else:
            lines.append(f"   ❌ {component} — missing")
    if star_hits["Result"] and not metrics:
        lines.append("   ⚠️ Your Result has no number attached.")

    lines += ["", f"2) Metric validation: {metric_score}/5"]
    if metrics:
        shown = [f"{kind}: {', '.join(dict.fromkeys(vals))}" for kind, vals in metrics.items()]
        lines += [f"   Found — {s}" for s in shown]
    else:
        lines.append("   No quantified evidence found.")
    if vague:
        lines.append(f"   Vague claims to replace with numbers: {', '.join(vague)}")

    lines += ["", f"3) Technical depth: {depth_score}/5"]
    if covered:
        lines.append(f"   Covered: {', '.join(covered[:12])}")
    if missing:
        lines.append(f"   Worth addressing: {', '.join(missing[:6])}")

    lines += [
        "",
        f"4) Ownership: {own_score}/5 — \"I\" ×{i_count} vs \"we\" ×{we_count}",
        "",
        f"5) Delivery: {delivery_score}/5 — {words} words (~{max(1, round(words / 150))} min spoken)",
    ]

    coaching = [c for d in DIMENSIONS if (c := _coaching_line(d, scores[d]))]
    if coaching:
        lines += ["", "🎯 Coaching:"]
        lines += [f"   • {c}" for c in coaching]

    lines += ["", "What a hire-level answer includes:"]
    lines += [f"   • {item}" for item in question["look_for"]]
    return result, "\n".join(lines)


def _question_prompt(index: int) -> str:
    q = INTERVIEW_QUESTIONS[index]
    return (f"❓ Question {index + 1}/{len(INTERVIEW_QUESTIONS)} — {q['category']}\n\n"
            f"{q['question']}\n\n"
            "Answer in one message using STAR. /skip to skip, /end_interview to stop.")


def interview_summary(results: list[QuestionResult]) -> str:
    answered = [r for r in results if not r.skipped]
    skipped = len(results) - len(answered)
    if not answered:
        return "🏁 Interview ended. No answers were graded — run /mock_interview when you're ready."

    averages = {d: sum(r.scores[d] for r in answered) / len(answered) for d in DIMENSIONS}
    overall = sum(r.overall for r in answered) / len(answered)
    # Up to two lowest dimensions, ignoring any already at hire level (≥ 4).
    weakest = [d for d in sorted(DIMENSIONS, key=lambda d: averages[d]) if averages[d] < 4][:2]

    lines = [
        "🏁 Mock interview complete",
        f"Answered: {len(answered)}  Skipped: {skipped}",
        f"Overall: {overall:.1f}/5 → {_verdict(overall)}",
        "",
        "Per question:",
    ]
    for r in results:
        q = INTERVIEW_QUESTIONS[r.question_index]
        if r.skipped:
            lines.append(f"   Q{r.question_index + 1} {q['category']}: skipped")
        else:
            lines.append(f"   Q{r.question_index + 1} {q['category']}: {r.overall:.1f} ({_verdict(r.overall)})")
    lines += ["", "Average by dimension:"]
    lines += [f"   {d}: {averages[d]:.1f}/5" for d in DIMENSIONS]
    if weakest:
        lines += ["", "Focus your practice on:"]
    else:
        lines += ["", "Every dimension is at hire level — practise new stories to build range."]
    for d in weakest:
        lines.append(f"   • {d} — {DIMENSION_COACHING[d]['low' if averages[d] < 3 else 'mid']}")
    lines += ["", "Run /mock_interview to go again."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

HELP_TEXT = (
    "🧭 FAANG Career Coach — commands\n\n"
    "/check_portfolio <url> — check your portfolio site is up, fast and on HTTPS\n"
    "/optimize_bullet <text> — turn a raw achievement into a high-impact resume bullet "
    "(or send the command alone, then the text)\n"
    "/mock_interview — 10-question behavioural + architecture interview with STAR critiques\n"
    "/skip — skip the current interview question\n"
    "/end_interview — stop and get your summary\n"
    "/help — this message"
)


def handle_start(chat_id: int, first_name: str) -> None:
    name = f", {first_name}" if first_name else ""
    send_message(chat_id, f"👋 Hi{name}! I'm your career coach for senior/FAANG engineering loops.\n\n{HELP_TEXT}")


def handle_check_portfolio(chat_id: int, args: str) -> None:
    target = args or os.environ.get("PORTFOLIO_URL", "")
    if not target:
        send_message(chat_id, "Usage: /check_portfolio https://your-portfolio.dev")
        return
    send_message(chat_id, check_portfolio(target))


def handle_optimize_bullet(chat_id: int, args: str, state: ChatState) -> None:
    if not args:
        state.awaiting_bullet = True
        send_message(chat_id, "Send me the achievement in your own words — what you did, the tech, and what changed.")
        return
    state.awaiting_bullet = False
    send_message(chat_id, optimize_bullet(args))


def handle_mock_interview(chat_id: int, state: ChatState) -> None:
    state.interview_active = True
    state.question_index = 0
    state.results = []
    state.awaiting_bullet = False
    send_message(
        chat_id,
        "🎤 Mock interview started: 10 questions across incident response, system design, "
        "migrations, cross-functional conflict and leadership.\n\n"
        "Each answer is graded on STAR structure, metric validation, technical depth, ownership "
        "and delivery. Write like you'd speak — about 250–400 words per answer.",
    )
    send_message(chat_id, _question_prompt(0))


def _advance_interview(chat_id: int, state: ChatState) -> None:
    state.question_index += 1
    if state.question_index >= len(INTERVIEW_QUESTIONS):
        state.interview_active = False
        send_message(chat_id, interview_summary(state.results))
        state.results = []
    else:
        send_message(chat_id, _question_prompt(state.question_index))


def handle_skip(chat_id: int, state: ChatState) -> None:
    if not state.interview_active:
        send_message(chat_id, "No interview in progress. Start one with /mock_interview.")
        return
    state.results.append(QuestionResult(question_index=state.question_index, skipped=True))
    _advance_interview(chat_id, state)


def handle_end_interview(chat_id: int, state: ChatState) -> None:
    if not state.interview_active:
        send_message(chat_id, "No interview in progress. Start one with /mock_interview.")
        return
    state.interview_active = False
    send_message(chat_id, interview_summary(state.results))
    state.results = []


def handle_interview_answer(chat_id: int, text: str, state: ChatState) -> None:
    words = word_count(text)
    if words < MIN_ANSWER_WORDS:
        send_message(chat_id, f"That's only {words} words — interviewers need the full story. "
                              "Reply with a complete STAR answer, or /skip.")
        return
    result, critique = evaluate_answer(text, state.question_index)
    state.results.append(result)
    send_message(chat_id, critique)
    _advance_interview(chat_id, state)


def handle_update(update: TelegramUpdate) -> None:
    message = update.message
    if message is None:
        return  # edited messages, channel posts, etc. are ignored
    chat_id = message.chat.id
    state = _get_state(chat_id)

    text = (message.text or "").strip()
    if not text:
        send_message(chat_id, "I can only read text messages. Try /help.")
        return

    if text.startswith("/"):
        command_token, _, args = text.partition(" ")
        command = command_token.split("@", 1)[0].lower()  # "/help@MyBot" in groups
        args = args.strip()
        first_name = message.from_user.first_name if message.from_user else ""

        if command == "/start":
            handle_start(chat_id, first_name)
        elif command == "/help":
            send_message(chat_id, HELP_TEXT)
        elif command == "/check_portfolio":
            handle_check_portfolio(chat_id, args)
        elif command == "/optimize_bullet":
            handle_optimize_bullet(chat_id, args, state)
        elif command == "/mock_interview":
            handle_mock_interview(chat_id, state)
        elif command == "/skip":
            handle_skip(chat_id, state)
        elif command in ("/end_interview", "/end", "/stop"):
            handle_end_interview(chat_id, state)
        else:
            send_message(chat_id, f"Unknown command {command}. See /help.")
        return

    if state.awaiting_bullet:
        state.awaiting_bullet = False
        send_message(chat_id, optimize_bullet(text))
    elif state.interview_active:
        handle_interview_answer(chat_id, text, state)
    else:
        send_message(chat_id, "Not sure what to do with that. If you were mid-interview, the session "
                              "may have expired — start again with /mock_interview. See /help.")


# ---------------------------------------------------------------------------
# Cloud Function entry point
# ---------------------------------------------------------------------------

@functions_framework.http
def telegram_webhook(request: Request):
    """HTTP entry point registered as --entry-point=telegram_webhook."""
    if request.method != "POST":
        return ("Method Not Allowed", 405)

    expected_secret = os.environ.get("WEBHOOK_SECRET", "")
    if not expected_secret:
        logger.error("WEBHOOK_SECRET is not set; refusing all requests")
        return ("Server misconfigured", 500)
    provided_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(provided_secret.encode(), expected_secret.encode()):
        logger.warning("Rejected request with missing or invalid secret token")
        return ("Forbidden", 403)

    payload = request.get_json(silent=True)
    if payload is None:
        return ("Bad Request", 400)

    try:
        update = TelegramUpdate.model_validate(payload)
    except ValidationError as exc:
        # Acknowledge anyway: a non-2xx makes Telegram retry the same bad payload forever.
        logger.warning("Ignoring unparseable update: %s", exc.errors()[:3])
        return ("OK", 200)

    if _is_duplicate_update(update.update_id):
        logger.info("Skipping duplicate update %s", update.update_id)
        return ("OK", 200)

    try:
        handle_update(update)
    except Exception:  # noqa: BLE001 — never let one bad update block the webhook
        logger.exception("Unhandled error while processing update %s", update.update_id)
    return ("OK", 200)
