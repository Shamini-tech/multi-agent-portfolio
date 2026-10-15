import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `graph`/`nodes` import cleanly
from graph import app

TEST_TICKETS = [
    "I was charged twice this month for order 1001, please refund me",
    "I can't login to my account, the password reset email never arrives",
    "This is unacceptable, your service is the worst, I want to speak to a manager!",
    "hello, do you have an office in Berlin?",
]

if __name__ == "__main__":
    tickets = sys.argv[1:] or TEST_TICKETS
    for t in tickets:
        print("\n" + "=" * 70)
        print("TICKET:", t)
        result = app.invoke({"ticket": t})
        print(f"STATUS: {result['status']}  (handled by {result['handled_by']})")
        print("RESPONSE:", result["response"])
