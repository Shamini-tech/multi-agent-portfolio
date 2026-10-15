from pathlib import Path

from dotenv import load_dotenv
from crewai import Crew, Process
from agents import searcher, analyst, writer
from tasks import search_task, analyze_task, write_task

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

research_crew = Crew(
    agents=[searcher, analyst, writer],
    tasks=[search_task, analyze_task, write_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("## Starting Research Crew Pipeline ##")
    result = research_crew.kickoff(inputs={"topic": "State of agentic AI, 2026"})
    print("\n\n## FINAL REPORT OUTPUT ##\n")
    print(result)
    out = Path(__file__).parent / "report.md"
    out.write_text(str(result), encoding="utf-8")
    print(f"\nSaved report to {out}")
