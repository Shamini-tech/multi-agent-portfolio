import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import app

if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) or "Why agentic AI needs typed tool calls"
    print("## Starting Content Pipeline ##  topic:", topic)
    final = app.invoke({"topic": topic, "loops": 0})
    print("\nDONE. score=%.2f loops=%d" % (final["score"], final["loops"]))
    print("Saved to:", final["published_path"])
    if final.get("flagged"):
        print("NOTE:", final["flagged"])
