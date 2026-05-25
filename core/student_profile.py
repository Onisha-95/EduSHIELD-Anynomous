"""
Student Profile Manager
- Persistent JSON profiles per student
- All helper functions used by every page
"""
import os, json
import uuid
from datetime import datetime, date

PROFILES_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "data", "student_profiles")

LEVEL_THRESHOLDS = [
    (0, "Beginner"), (50, "Explorer"), (150, "Learner"),
    (300, "Practitioner"), (500, "Advanced"), (750, "Expert"), (1000, "Master"),
]

def get_level_info(xp):
    level_num, level_name = 1, "Beginner"
    for i, (threshold, name) in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level_num, level_name = i + 1, name
    if level_num < len(LEVEL_THRESHOLDS):
        level_min = LEVEL_THRESHOLDS[level_num - 1][0]
        level_max = LEVEL_THRESHOLDS[level_num][0]
        xp_to_next = level_max - xp
        progress = (xp - level_min) / max(1, level_max - level_min)
    else:
        xp_to_next, progress = 0, 1.0
    return {"level_num": level_num, "level_name": level_name,
            "xp": xp, "xp_to_next": xp_to_next,
            "progress": min(1.0, max(0.0, progress))}

def _mastery_label(times_asked, struggle_score):
    if times_asked == 0: return "Not Started"
    if struggle_score >= 3: return "Struggling"
    if struggle_score >= 1: return "Learning"
    if times_asked >= 3: return "Confident"
    return "Seen"

def get_mastery_color(status):
    return {"Struggling":"red","Learning":"orange","Confident":"green","Seen":"blue"}.get(status,"gray")

def get_mastery_emoji(status):
    return {"Struggling":"🔴","Learning":"🟡","Confident":"✅","Seen":"👁","Not Started":"⬜"}.get(status,"⬜")

def _profiles_dir():
    d = PROFILES_DIR_DEFAULT
    os.makedirs(d, exist_ok=True)
    return d

def _path(student_id):
    d = _profiles_dir()
    safe = "".join(c for c in student_id if c.isalnum() or c in "-_")
    return os.path.join(d, f"{safe}.json")

def _empty(student_id, name="Student", courses=None):
    return {
        "student_id": student_id, "name": name,
        "courses": courses or ["CSE1321"],
        "created_at": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
        "xp": 0, "total_sessions": 0, "total_turns": 0,
        "total_lessons": 0, "correct_answers": 0,
        "streak_days": 0, "last_session_date": None,
        "concept_mastery": {},
        "mastery_summary": {},
        "struggle_flags": [],
        "lesson_history": [],
        "chat_history": [],  # Persistent chat history (last N turns)
    }

# ── Public API (all functions used by pages) ────────────────────────────────

def create_profile(name, student_id, courses=None):
    p = _empty(student_id, name, courses)
    save_profile(p)
    return p

def load_profile(student_id):
    path = _path(student_id)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_profile(profile):
    try:
        os.makedirs(_profiles_dir(), exist_ok=True)
        with open(_path(profile["student_id"]), "w") as f:
            json.dump(profile, f, indent=2)
    except Exception:
        pass

def list_profiles():
    try:
        result = []
        for fname in os.listdir(_profiles_dir()):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(_profiles_dir(), fname)) as f:
                        result.append(json.load(f))
                except Exception:
                    pass
        return result
    except Exception:
        return []

def start_session(profile):
    """Called when student logs in — update streak."""
    today = date.today().isoformat()
    yesterday = str(date.fromordinal(date.today().toordinal() - 1))
    if profile.get("last_session_date") == yesterday:
        profile["streak_days"] = profile.get("streak_days", 0) + 1
    elif profile.get("last_session_date") != today:
        profile["streak_days"] = 1
    profile["last_session_date"] = today
    profile["last_seen"] = datetime.now().isoformat()
    profile["total_sessions"] = profile.get("total_sessions", 0) + 1
    save_profile(profile)

def update_concept(profile, concept, verdict):
    """Called after each guard validation."""
    if not concept:
        return
    concept = concept.lower().strip()
    m = profile.setdefault("concept_mastery", {})
    entry = m.get(concept, {"times_asked": 0, "struggle_score": 0,
                             "last_seen": None, "verdict_history": []})
    entry["times_asked"] += 1
    entry["last_seen"] = datetime.now().isoformat()
    entry.setdefault("verdict_history", []).append(verdict)
    if verdict == "CONTRADICTED":
        entry["struggle_score"] = min(5, entry["struggle_score"] + 1)
    elif verdict == "VERIFIED":
        entry["struggle_score"] = max(0, entry["struggle_score"] - 1)
    m[concept] = entry
    # Update summary label
    profile.setdefault("mastery_summary", {})[concept] = _mastery_label(
        entry["times_asked"], entry["struggle_score"]
    )
    # Update struggle flags
    flags = profile.setdefault("struggle_flags", [])
    if entry["struggle_score"] >= 2 and concept not in flags:
        flags.append(concept)
    elif entry["struggle_score"] < 2 and concept in flags:
        flags.remove(concept)
    save_profile(profile)

def record_lesson(profile, topic, steps_done, verdicts, complete=True):
    """Save a completed or partial lesson."""
    verified_count = verdicts.count("VERIFIED")
    total_answers = max(len(verdicts), 1)
    xp = steps_done * 10 + (15 if complete and all(v == "VERIFIED" for v in verdicts) else 0)
    lesson_date = datetime.now().isoformat()

    profile.setdefault("lesson_history", []).append({
        "topic": topic,
        "steps_done": steps_done,
        "steps_completed": steps_done,
        "total_steps": 5,
        "verdicts": verdicts,
        "verified_count": verified_count,
        "total_answers": total_answers,
        "xp_earned": xp,
        "date": lesson_date,
        "complete": complete,
        "started_at": lesson_date,
        "completed_at": lesson_date if complete else None,
    })
    profile["lesson_history"] = profile["lesson_history"][-50:]
    profile["total_lessons"] = profile.get("total_lessons", 0) + (1 if complete else 0)
    profile["xp"] = profile.get("xp", 0) + xp
    profile["correct_answers"] = profile.get("correct_answers", 0) + verified_count
    profile["last_seen"] = lesson_date
    save_profile(profile)
    return xp


def record_turn(profile, concept, verdict):
    profile["total_turns"] = profile.get("total_turns", 0) + 1
    if verdict == "VERIFIED":
        profile["correct_answers"] = profile.get("correct_answers", 0) + 1
    update_concept(profile, concept, verdict)
    profile["last_seen"] = datetime.now().isoformat()
    save_profile(profile)


def start_lesson_record(profile, topic):
    lesson_id = str(uuid.uuid4())[:10]
    now = datetime.now().isoformat()
    lesson = {
        "lesson_id": lesson_id,
        "topic": topic,
        "steps_completed": 0,
        "total_steps": 5,
        "verified_count": 0,
        "total_answers": 0,
        "xp_earned": 0,
        "date": now,
        "started_at": now,
        "completed_at": None,
        "complete": False,
    }
    profile.setdefault("lesson_history", []).append(lesson)
    profile["lesson_history"] = profile["lesson_history"][-50:]
    profile["last_seen"] = now
    save_profile(profile)
    return lesson_id


def update_lesson_record(profile, lesson_id, step, verdict, complete=False):
    lessons = profile.setdefault("lesson_history", [])
    lesson = next((l for l in reversed(lessons) if l.get("lesson_id") == lesson_id), None)
    if not lesson:
        lesson = {
            "lesson_id": lesson_id,
            "topic": "Lesson",
            "steps_completed": 0,
            "total_steps": 5,
            "verified_count": 0,
            "total_answers": 0,
            "xp_earned": 0,
            "date": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "complete": False,
        }
        lessons.append(lesson)

    lesson["steps_completed"] = max(lesson.get("steps_completed", 0), int(step or 0))
    lesson["total_steps"] = lesson.get("total_steps", 5) or 5
    lesson["total_answers"] = lesson.get("total_answers", 0) + 1
    if verdict == "VERIFIED":
        lesson["verified_count"] = lesson.get("verified_count", 0) + 1

    if complete and not lesson.get("complete", False):
        lesson["complete"] = True
        lesson["completed_at"] = datetime.now().isoformat()
        base_xp = lesson.get("steps_completed", 0) * 10
        bonus_xp = 15 if (lesson.get("total_answers", 0) > 0 and lesson.get("verified_count", 0) == lesson.get("total_answers", 0)) else 0
        lesson["xp_earned"] = base_xp + bonus_xp
        profile["xp"] = profile.get("xp", 0) + lesson["xp_earned"]
        profile["total_lessons"] = profile.get("total_lessons", 0) + 1

    profile["correct_answers"] = profile.get("correct_answers", 0) + (1 if verdict == "VERIFIED" else 0)
    profile["last_seen"] = datetime.now().isoformat()
    profile["lesson_history"] = lessons[-50:]
    save_profile(profile)

# ── StudentProfileManager (used by Guide Mode / My Profile pages) ────────────
class StudentProfileManager:
    def __init__(self, profiles_dir=None):
        self.profiles_dir = profiles_dir or PROFILES_DIR_DEFAULT
        os.makedirs(self.profiles_dir, exist_ok=True)

    def _path(self, sid):
        safe = "".join(c for c in sid if c.isalnum() or c in "-_")
        return os.path.join(self.profiles_dir, f"{safe}.json")

    def load(self, student_id):
        path = self._path(student_id)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return _empty(student_id)

    def save(self, profile):
        try:
            with open(self._path(profile["student_id"]), "w") as f:
                json.dump(profile, f, indent=2)
        except Exception:
            pass

    def get_mastery_summary(self, profile):
        counts = {"Confident": 0, "Learning": 0, "Struggling": 0, "Seen": 0, "Not Started": 0}
        for d in profile.get("concept_mastery", {}).values():
            s = d.get("status", "Not Started")
            counts[s] = counts.get(s, 0) + 1
        return counts
