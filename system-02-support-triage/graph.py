from langgraph.graph import END, StateGraph

from nodes import (TicketState, billing_agent, classify_ticket, human_escalation,
                   tech_agent)

VALID_ROUTES = {"billing", "tech", "low_conf"}


def pick_route(state: TicketState) -> str:
    route = state.get("route", "low_conf")
    return route if route in VALID_ROUTES else "low_conf"


def build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("classify", classify_ticket)
    graph.add_node("billing", billing_agent)
    graph.add_node("tech", tech_agent)
    graph.add_node("escalate", human_escalation)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        pick_route,
        {"billing": "billing", "tech": "tech", "low_conf": "escalate"},
    )
    graph.add_edge("billing", END)
    graph.add_edge("tech", END)
    graph.add_edge("escalate", END)
    return graph.compile()


app = build_graph()
