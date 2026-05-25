"""
Session Manager — Student Session State

Tracks:
  - conversation_history  : full message log passed to LLM every turn
  - concepts_encountered  : per-concept struggle data
  - struggle_flags        : concepts where student is repeatedly failing
  - session_mastery_hints : human-readable mastery level per concept
  - query_history         : log of every query + Guard #2 classification

The session is created fresh per browser session and lives in memory.
It is never persisted to disk — each Streamlit session starts clean.
"""
import uuid
from datetime import datetime


def init_session(session_id: str = None) -> dict:
    """Create a fresh empty session."""
    return {
        "session_id":            session_id or str(uuid.uuid4()),
        "started_at":            datetime.now().isoformat(),
        "conversation_history":  [],   # {role, content, timestamp}
        "concepts_encountered":  {},   # concept -> {times_asked, verdicts[], struggle_score}
        "struggle_flags":        [],   # concepts with struggle_score >= 2
        "query_history":         [],   # {query, classification, context_flag, ts}
        "session_mastery_hints": {},   # concept -> NEW | STRUGGLING | LIKELY_UNDERSTOOD | ADVANCING
    }


def add_to_history(session: dict, role: str, content: str):
    """
    Append a message to conversation history.
    role must be 'student' or 'assistant'.
    Keeps last 20 messages to avoid overflowing LLM context window.
    """
    session["conversation_history"].append({
        "role":      role,
        "content":   content,
        "timestamp": datetime.now().isoformat(),
    })
    if len(session["conversation_history"]) > 20:
        session["conversation_history"] = session["conversation_history"][-20:]


def update_session(session: dict, concept: str, guard1_verdict: str):
    """
    Called after every Guard #1 verdict.
    Updates per-concept struggle tracking and mastery hints.

    Struggle score logic:
      CONTRADICTED or UNVERIFIABLE -> score +1  (student got something wrong/uncertain)
      VERIFIED                     -> score -1  (student engaged correctly, floor at 0)
    """
    if not concept:
        return

    concept = concept.lower().strip()

    # Initialise concept entry on first encounter
    if concept not in session["concepts_encountered"]:
        session["concepts_encountered"][concept] = {
            "times_asked":     0,
            "guard1_verdicts": [],
            "struggle_score":  0,
        }

    entry = session["concepts_encountered"][concept]
    entry["times_asked"]      += 1
    entry["guard1_verdicts"].append(guard1_verdict)

    if guard1_verdict in ("CONTRADICTED", "UNVERIFIABLE"):
        entry["struggle_score"] += 1
    elif guard1_verdict == "VERIFIED":
        entry["struggle_score"] = max(0, entry["struggle_score"] - 1)

    score = entry["struggle_score"]
    asked = entry["times_asked"]

    # Maintain struggle_flags list
    if score >= 2:
        if concept not in session["struggle_flags"]:
            session["struggle_flags"].append(concept)
    else:
        session["struggle_flags"] = [c for c in session["struggle_flags"] if c != concept]

    # Assign human-readable mastery hint
    if score >= 2:
        session["session_mastery_hints"][concept] = "STRUGGLING"
    elif score == 0 and asked >= 2:
        session["session_mastery_hints"][concept] = "LIKELY_UNDERSTOOD"
    elif asked >= 3 and score <= 1:
        session["session_mastery_hints"][concept] = "ADVANCING"
    else:
        session["session_mastery_hints"][concept] = "NEW"


def get_context_flag(session: dict, concept: str) -> tuple:
    """
    Returns (context_flag, llm_modifier) for a concept.
    Called by Guard #2 before each LLM call.

    The modifier is passed as a teaching style instruction inside the LLM prompt.
    The LLM never sees the struggle score directly — only the instruction.

    Returns:
      NORMAL         / "normal"         -> first time asking, no issues
      SCAFFOLD       / "scaffold"       -> one failed interaction, simplify
      ADVANCE        / "advance"        -> asked correctly multiple times, go deeper
      REPEAT_STRUGGLE/ "repeat_struggle"-> multiple failures, completely restart approach
    """
    if not concept:
        return "NORMAL", "normal"

    concept = concept.lower().strip()
    entry   = session["concepts_encountered"].get(concept, {})
    score   = entry.get("struggle_score", 0)
    asked   = entry.get("times_asked",    0)

    if score >= 2:
        return "REPEAT_STRUGGLE", "repeat_struggle"
    elif score >= 1:
        return "SCAFFOLD", "scaffold"
    elif asked >= 2 and score == 0:
        return "ADVANCE", "advance"
    else:
        return "NORMAL", "normal"
