from langgraph.graph import END, StateGraph

from crew_node import run_research_crew
from nodes import (ContentState, critique_draft, draft_content, publish_content,
                   should_revise)


def build_graph():
    graph = StateGraph(ContentState)
    graph.add_node("research", run_research_crew)  # calls CrewAI sub-crew
    graph.add_node("draft", draft_content)
    graph.add_node("critique", critique_draft)
    graph.add_node("publish", publish_content)

    graph.add_conditional_edges("critique", should_revise,
                                {"draft": "draft", "publish": "publish"})
    graph.set_entry_point("research")
    graph.add_edge("research", "draft")
    graph.add_edge("draft", "critique")
    graph.add_edge("publish", END)
    return graph.compile()


app = build_graph()
