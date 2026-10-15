"""Wraps System 01's research crew as a single LangGraph node."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "system-01-research-crew"))  # reuse agents.py / tasks.py


def run_research_crew(state: dict) -> dict:
    from crewai import Crew, Process
    from agents import searcher, analyst, writer
    from tasks import search_task, analyze_task, write_task

    crew = Crew(
        agents=[searcher, analyst, writer],
        tasks=[search_task, analyze_task, write_task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff(inputs={"topic": state["topic"]})
    print(f"[research] crew finished ({len(str(result))} chars)")
    return {"research": str(result)}
