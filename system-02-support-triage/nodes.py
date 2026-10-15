import json
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_utils import chat, chat_json  # noqa: E402

CONFIDENCE_THRESHOLD = 0.6
ANGRY_WORDS = ("furious", "angry", "unacceptable", "terrible", "worst", "scam",
               "lawyer", "sue", "ridiculous", "disgusted", "fed up", "cancel everything")


class TicketState(TypedDict, total=False):
    ticket: str
    category: str      # billing / tech / general
    confidence: float
    reasoning: str
    sentiment: str     # angry / neutral
    route: str         # billing / tech / low_conf
    response: str
    status: str        # resolved / escalated
    handled_by: str


# ---------- mocked tools (swap for real APIs later) ----------
ORDERS = {
    "1001": {"item": "Pro plan (monthly)", "amount": 29.00, "charges": 2, "date": "2026-10-02"},
    "1002": {"item": "Annual plan", "amount": 240.00, "charges": 1, "date": "2026-09-15"},
}


def get_order(order_id: str) -> dict:
    """Look up an order. Example: get_order('1001') -> {'item': ..., 'amount': ...}"""
    return ORDERS.get(order_id, {})


def issue_refund(order_id: str, amount: float) -> dict:
    """Issue a refund (mock). Example: issue_refund('1001', 29.0)."""
    return {"order_id": order_id, "refunded": amount, "needs_manager": amount > 50}


KB = {
    "login": "1) Reset password via 'Forgot password'. 2) Clear browser cache/cookies. 3) Try incognito window. 4) Check the account email is verified.",
    "crash": "1) Update the app to the latest version. 2) Clear app cache. 3) Reinstall. 4) Send logs via Settings > Help > Export logs.",
    "slow": "1) Check status page. 2) Disable VPN/extensions. 3) Test on another network. 4) Clear cache.",
    "upload": "1) Check file is under 25 MB. 2) Supported formats: PDF, PNG, JPG, CSV. 3) Retry on another browser.",
}


def search_kb(query: str) -> str:
    """Keyword lookup in the knowledge base. Example: search_kb('cannot login')."""
    hits = [v for k, v in KB.items() if k in query.lower()]
    return "\n".join(hits) if hits else "No matching KB article."


# ---------- nodes ----------
CLASSIFY_PROMPT = (
    "Classify this support ticket into exactly one category: billing, tech, or general. "
    "Also return a confidence score 0-1. If confidence < 0.6, category must be 'general'. "
    'Respond as JSON: {"category": "...", "confidence": 0.0, "reasoning": "..."}.'
)


def classify_ticket(state: TicketState) -> TicketState:
    ticket = state["ticket"]
    sentiment = "angry" if any(w in ticket.lower() for w in ANGRY_WORDS) else "neutral"
    try:
        out = chat_json(CLASSIFY_PROMPT, ticket)
        category = str(out.get("category", "general")).lower().strip()
        confidence = float(out.get("confidence", 0))
        reasoning = str(out.get("reasoning", ""))
    except Exception as e:  # malformed output must never crash the router
        print(f"[classify] LLM error: {e}")
        category, confidence, reasoning = "general", 0.0, f"classifier failed: {e}"

    if category not in ("billing", "tech", "general"):
        category = "general"
    # Route is derived and validated in code so the conditional edge never KeyErrors.
    if sentiment == "angry" or category == "general" or confidence < CONFIDENCE_THRESHOLD:
        route = "low_conf"
    else:
        route = category
    print(f"[classify] category={category} conf={confidence:.2f} sentiment={sentiment} -> route={route}")
    return {"category": category, "confidence": confidence, "reasoning": reasoning,
            "sentiment": sentiment, "route": route}


def billing_agent(state: TicketState) -> TicketState:
    import re
    m = re.search(r"\b(\d{4})\b", state["ticket"])
    order_id = m.group(1) if m else "1001"
    order = get_order(order_id) or ORDERS["1001"]

    refund = None
    if order.get("charges", 1) > 1:  # duplicate charge -> refund ONE extra charge
        refund = issue_refund(order_id, order["amount"])

    facts = {"order": order, "refund_issued": refund}
    system = (
        "You handle billing tickets: refunds, invoices, plan changes. "
        "Use ONLY the facts provided; do not invent amounts. "
        "If refund_issued is present, tell the customer that exact amount was refunded. "
        "If refund_issued.needs_manager is true, say the refund needs manager approval. "
        "Be brief and polite."
    )
    user = f"Ticket: {state['ticket']}\nFacts: {json.dumps(facts)}"
    return {"response": chat(system, user), "status": "resolved", "handled_by": "billing_agent"}


def tech_agent(state: TicketState) -> TicketState:
    kb = search_kb(state["ticket"])
    system = (
        "You handle technical support tickets. Walk the user through the standard "
        "troubleshooting steps for their issue type before suggesting escalation. Be concrete - "
        "no 'have you tried restarting' without specifics."
    )
    user = f"Ticket: {state['ticket']}\nKnowledge base result:\n{kb}"
    return {"response": chat(system, user), "status": "resolved", "handled_by": "tech_agent"}


def human_escalation(state: TicketState) -> TicketState:
    summary = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "ticket": state["ticket"],
        "category": state.get("category"),
        "confidence": state.get("confidence"),
        "sentiment": state.get("sentiment"),
        "classifier_reasoning": state.get("reasoning"),
    }
    out = Path(__file__).parent / "escalations.jsonl"  # stand-in for a Slack channel / queue
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")
    print(f"[escalate] queued for a human -> {out.name}")
    return {
        "response": "Thanks for reaching out - a member of our team will contact you shortly.",
        "status": "escalated",
        "handled_by": "human_escalation",
    }