import sys
from datetime import date
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm_utils import chat, chat_json  # noqa: E402

PASS_SCORE = 0.8
MAX_LOOPS = 3  # hard cap - an unbounded critique loop burns API credits


class ContentState(TypedDict, total=False):
    topic: str
    research: str
    draft: str
    score: float
    feedback: list
    loops: int
    flagged: str
    published_path: str


DRAFT_PROMPT = (
    "Write a ~500-word post from the research brief. On revision passes, you'll also "
    "receive prior feedback - address every point raised, don't just rewrite from scratch. "
    "Use markdown headers. Only state claims that are supported by the research brief."
)


def draft_content(state: ContentState) -> ContentState:
    loops = state.get("loops", 0) + 1
    user = f"Topic: {state['topic']}\n\nResearch brief:\n{state['research']}"
    if state.get("feedback"):
        fb = "\n".join(f"- {f}" for f in state["feedback"])
        user += f"\n\nYour previous draft:\n{state['draft']}\n\nCritique feedback to address:\n{fb}"
    draft = chat(DRAFT_PROMPT, user, temperature=0.4)
    print(f"[draft] pass {loops} written ({len(draft.split())} words)")
    return {"draft": draft, "loops": loops}


CRITIQUE_PROMPT = (
    "Score this draft 0-1 on: (a) every claim is traceable to the research, "
    "(b) tone matches a technical blog, (c) has a clear structure with headers. "
    'Return JSON: {"accuracy": 0.0, "tone": 0.0, "structure": 0.0, "feedback": ["specific, actionable point", ...]}. '
    "Feedback must be specific (quote the sentence or section to fix)."
)


def critique_draft(state: ContentState) -> ContentState:
    user = f"Research brief:\n{state['research']}\n\nDraft:\n{state['draft']}"
    try:
        out = chat_json(CRITIQUE_PROMPT, user)
        subs = [float(out.get(k, 0)) for k in ("accuracy", "tone", "structure")]
        score = sum(subs) / 3  # score is the average of the three sub-scores
        feedback = [str(f) for f in out.get("feedback", [])]
    except Exception as e:
        score, feedback = 0.0, [f"critique failed to parse ({e}); re-check structure and sourcing"]
    print(f"[critique] score={score:.2f} loops={state.get('loops', 0)}")
    return {"score": score, "feedback": feedback}


def should_revise(state: ContentState) -> str:
    return "draft" if state["score"] < PASS_SCORE and state["loops"] < MAX_LOOPS else "publish"


def publish_content(state: ContentState) -> ContentState:
    flagged = ""
    if state["score"] < PASS_SCORE:
        flagged = (f"Published after {state['loops']} passes with score {state['score']:.2f} "
                   f"(< {PASS_SCORE}). Needs human review.")
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    slug = "-".join(state["topic"].lower().split())[:50] or "post"
    path = out_dir / f"{date.today()}-{slug}.md"
    note = f"\n\n> ⚠️ {flagged}\n" if flagged else ""
    excerpt = state["draft"].strip().split("\n\n")[0][:160]
    front = (f"---\ntitle: {state['topic']}\ndate: {date.today()}\ntags: [agentic-ai, multi-agent]\n"
             f"excerpt: \"{excerpt.replace(chr(34), chr(39))}\"\nscore: {state['score']:.2f}\n"
             f"loops: {state['loops']}\n---\n\n")
    path.write_text(front + state["draft"] + note, encoding="utf-8")
    print(f"[publish] wrote {path}")
    return {"published_path": str(path), "flagged": flagged}
