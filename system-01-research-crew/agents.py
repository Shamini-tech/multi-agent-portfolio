import os
from dotenv import load_dotenv
from crewai import Agent, LLM
from crewai_tools import SerperDevTool

load_dotenv()

# Free-tier LLM instead of OpenAI (your OpenAI account has no credits).
# Change LLM_MODEL in .env to switch provider, e.g. "groq/llama-3.3-70b-versatile"
llm = LLM(
    model=(os.getenv("LLM_MODEL") or "groq/openai/gpt-oss-20b").strip(),
    temperature=0.2,
    max_tokens=1500,  # keeps each request under Groq's free-tier tokens-per-minute limit
)

# --- Groq compatibility patch -------------------------------------------------
# CrewAI adds a "cache_breakpoint" field to messages (prompt caching). Groq rejects
# unknown fields, so strip it before the request is sent. Harmless for other providers.
import litellm

_orig_completion = litellm.completion


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k != "cache_breakpoint"}
    if isinstance(obj, list):
        return [_strip(x) for x in obj]
    return obj


def _completion_without_cache_breakpoint(*args, **kwargs):
    if kwargs.get("messages"):
        kwargs["messages"] = _strip(kwargs["messages"])
    return _orig_completion(*args, **kwargs)


litellm.completion = _completion_without_cache_breakpoint
# -------------------------------------------------------------------------------

# Initialize search tool (or use DuckDuckGo search tool)
web_search_tool = SerperDevTool(n_results=5)  # fewer results = smaller prompts

searcher = Agent(
    role="Senior Research Librarian",
    goal="Find 5-8 credible, recent sources on the given topic and return title, URL, and a 1-line relevance note for each.",
    backstory="You've spent 15 years finding primary sources for investigative journalists. You distrust SEO content farms and always prefer official docs, papers, or first-party blogs.",
    tools=[web_search_tool],
    allow_delegation=False,
    llm=llm,
)

analyst = Agent(
    role="Critical Research Analyst",
    goal="Extract the 3-5 strongest claims from the Search Agent's sources, each with the supporting evidence and source it came from.",
    backstory="You've reviewed thousands of papers for a research lab. You flag unsupported claims instead of repeating them, and you never merge two sources' claims into one without saying so.",
    tools=[],
    allow_delegation=False,
    llm=llm,
)

writer = Agent(
    role="Technical Report Writer",
    goal="Turn the Analyst's claims into a structured report: a 2-sentence summary, 3-5 headed sections, and a sources list.",
    backstory="You write for busy engineers. No filler intros, no restating the question—you open with the answer and back it with the evidence you were given.",
    tools=[],
    allow_delegation=False,
    llm=llm,
)