"""
Socratic Engine — Guided lesson mode with step-by-step questioning.

For each topic the engine runs a 5-step Socratic sequence:
  Step 1 — Activate Prior Knowledge   : "What do you already know about X?"
  Step 2 — Guided Discovery           : Ask a question that leads student to the answer
  Step 3 — Example Exploration        : Walk through a concrete code example together
  Step 4 — Misconception Check        : Present a common wrong belief, ask if it's right
  Step 5 — Consolidation              : Student explains it back in their own words

Guard #1 validates every student response against the KG.
Guard #2 checks each student answer is on-topic.
Teaching style adapts per step based on struggle score.
"""
import time
from session_manager import get_context_flag


STEP_LABELS = [
    "Activate Prior Knowledge",
    "Guided Discovery",
    "Example Exploration",
    "Misconception Check",
    "Consolidation",
]

STEP_PROMPTS = {
    1: (
        "You are a Socratic tutor. Your ONLY job this turn is to ask the student "
        "what they already know about '{topic}'. Do NOT explain anything yet. "
        "Ask ONE open question like: 'Before we dive in — what do you already "
        "know about {topic}? Even a guess is fine.' Keep it warm and short."
    ),
    2: (
        "You are a Socratic tutor teaching '{topic}'. "
        "The student said: '{student_answer}'. "
        "Using only the verified facts below, ask ONE guiding question that "
        "nudges them toward understanding '{topic}' without giving the answer away. "
        "Acknowledge what they got right first. Be encouraging."
    ),
    3: (
        "You are a Socratic tutor teaching '{topic}'. "
        "Walk the student through a SHORT concrete code example of '{topic}' "
        "line by line. After showing the code, ask: 'What do you think happens "
        "on line X?' Pick the most interesting line. Use only verified facts."
    ),
    4: (
        "You are a Socratic tutor teaching '{topic}'. "
        "Present this common misconception to the student and ask if they think "
        "it is correct or not: '{misconception}'. "
        "Do NOT reveal the answer yet. Just ask them to evaluate it."
    ),
    5: (
        "You are a Socratic tutor finishing the lesson on '{topic}'. "
        "The student has been working through examples. "
        "Ask them to explain '{topic}' back to you in their own words, "
        "as if they were teaching a friend. Say: 'Now it is your turn — "
        "can you explain {topic} to me as if I have never heard of it?'"
    ),
}

# Common misconceptions per topic — used in Step 4
MISCONCEPTIONS = {
    "for loop":       "A for loop always needs a start and end number to work.",
    "while loop":     "A while loop always runs at least once before checking its condition.",
    "if statement":   "You must always have an else clause after an if statement.",
    "variable":       "You have to declare the type of a variable before using it in Python.",
    "function":       "A function always needs to return a value.",
    "list":           "Lists in Python can only hold one type of data.",
    "class":          "You can only create one object from a class.",
    "loop":           "A loop always needs a counter variable to work.",
    "default":        "This concept always behaves the same way regardless of input.",
}


class SocraticEngine:

    def __init__(self, rag_system, guard1, guard2, llm_caller):
        self.rag      = rag_system
        self.guard1   = guard1
        self.guard2   = guard2
        self.llm      = llm_caller   # callable(prompt) -> str

    def _get_misconception(self, topic: str, facts: list) -> str:
        """
        Get misconception for Step 4 from KG negation facts first,
        fall back to hardcoded dict, then generate a generic one.
        """
        # 1. Try KG: look for negation-flagged facts for this topic
        topic_lower = topic.lower()
        for fact in facts:
            neg = fact.get("negation", "")
            claim = fact.get("claim", "")
            # A negation fact IS the misconception (wrong belief to challenge)
            if neg and len(neg) > 15 and topic_lower in fact.get("concept","").lower():
                return neg
        # 2. Partial match on any negation in retrieved facts
        for fact in facts:
            neg = fact.get("negation", "")
            if neg and len(neg) > 15:
                return neg
        # 3. Hardcoded fallback for common topics
        hardcoded = MISCONCEPTIONS.get(topic_lower)
        if hardcoded:
            return hardcoded
        # 4. Generic fallback using a real claim from facts
        for fact in facts:
            claim = fact.get("claim", "")
            if claim and len(claim) > 20:
                # Invert it as a misconception
                return f"{topic.title()} always works like this: {claim[:80]}..."
        return f"Once you understand {topic}, there is nothing more to learn about it."

    def start_lesson(self, topic: str, session: dict) -> dict:
        """
        Begin a new Socratic lesson on a topic.
        Returns the Step 1 question to show the student.
        """
        # Retrieve KG facts for this topic
        facts = self.rag.retrieve_context(topic, top_k=8)

        # Build Step 1 prompt — just ask what student knows
        prompt = self._build_step_prompt(
            step=1, topic=topic,
            student_answer="", facts=facts
        )
        question = self.llm(prompt)

        # Get misconception — KG first, then fallback
        misconception = self._get_misconception(topic, facts)

        # Initialise lesson state in session
        session["socratic_lesson"] = {
            "topic":        topic,
            "current_step": 1,
            "step_history": [],
            "facts":        facts,
            "misconception": misconception,
            "complete":     False,
        }

        return {
            "step":          1,
            "step_label":    STEP_LABELS[0],
            "tutor_message": question,
            "topic":         topic,
            "complete":      False,
            "guard1":        None,
            "guard2":        None,
        }

    def advance(self, student_answer: str, session: dict) -> dict:
        """
        Student submitted an answer. Validate it, then advance to next step.
        Returns next tutor message + guard verdicts.
        """
        lesson  = session.get("socratic_lesson")
        if not lesson:
            return {"error": "No active lesson. Call start_lesson first."}

        topic   = lesson["topic"]
        step    = lesson["current_step"]
        facts   = lesson["facts"]

        # Guard #2 — is this answer on-topic?
        g2 = self.guard2.classify(student_answer, session)

        # Guard #1 — validate student's answer against KG
        g1 = self.guard1.validate(student_answer, facts, student_answer)

        # Record this step
        lesson["step_history"].append({
            "step":             step,
            "step_label":       STEP_LABELS[step - 1],
            "student_answer":   student_answer,
            "guard1_verdict":   g1["verdict"],
            "guard2_class":     g2["classification"],
        })

        # Update struggle tracking
        from session_manager import update_session
        update_session(session, topic, g1["verdict"])

        # Get teaching modifier for next step
        context_flag, modifier = get_context_flag(session, topic)

        # Move to next step
        next_step = step + 1
        complete  = next_step > 5

        if complete:
            lesson["complete"] = True
            tutor_msg = self._build_completion_message(topic, lesson, g1)
        else:
            lesson["current_step"] = next_step
            prompt = self._build_step_prompt(
                step=next_step, topic=topic,
                student_answer=student_answer,
                facts=facts,
                misconception=lesson["misconception"],
                modifier=modifier,
                guard1_verdict=g1["verdict"],
            )
            tutor_msg = self.llm(prompt)

        return {
            "step":          next_step if not complete else 5,
            "step_label":    STEP_LABELS[min(next_step, 5) - 1],
            "tutor_message": tutor_msg,
            "topic":         topic,
            "complete":      complete,
            "guard1":        g1,
            "guard2":        g2,
            "modifier":      modifier,
        }

    def _build_step_prompt(self, step: int, topic: str,
                           student_answer: str, facts: list,
                           misconception: str = "",
                           modifier: str = "normal",
                           guard1_verdict: str = "VERIFIED") -> str:
        # Format KG facts
        facts_block = "\n".join(
            f"  [{f['concept'].upper()}] {f['claim']}"
            for f in facts[:6] if f.get("claim")
        ) or "  No specific facts retrieved."

        # Get step instruction
        template = STEP_PROMPTS.get(step, STEP_PROMPTS[1])
        instruction = template.format(
            topic=topic,
            student_answer=student_answer or "(no answer yet)",
            misconception=misconception,
        )

        # Add modifier
        modifier_text = {
            "scaffold":       "The student is struggling. Simplify. Use a short analogy. Be encouraging.",
            "repeat_struggle":"Student is very confused. Use a completely different approach. Be extra patient.",
            "advance":        "Student understands basics. You can go slightly deeper.",
            "normal":         "Keep it clear and conversational.",
        }.get(modifier, "Keep it clear and conversational.")

        # Add correction context if guard1 flagged something
        correction_ctx = ""
        if guard1_verdict == "CONTRADICTED":
            correction_ctx = (
                "\nIMPORTANT: The student's previous answer contained an error. "
                "Gently acknowledge what they got right, then guide them toward "
                "the correct understanding using the facts. Do NOT just give the answer."
            )

        return (
            f"{instruction}\n\n"
            f"VERIFIED COURSE FACTS:\n{facts_block}\n\n"
            f"TEACHING STYLE: {modifier_text}"
            f"{correction_ctx}\n\n"
            f"YOUR RESPONSE (one short paragraph or question only):"
        )

    def _build_completion_message(self, topic: str,
                                  lesson: dict, last_g1: dict) -> str:
        history     = lesson["step_history"]
        struggles   = sum(1 for s in history if s["guard1_verdict"] != "VERIFIED")
        total_steps = len(history)

        if struggles == 0:
            opening = f"Excellent work! You've completed the lesson on **{topic}**."
            note    = "Your answers were consistently accurate."
        elif struggles <= 2:
            opening = f"Good effort on **{topic}**!"
            note    = f"You had {struggles} answer(s) that needed adjustment — that's completely normal when learning."
        else:
            opening = f"You've worked through the full lesson on **{topic}**."
            note    = "This was a challenging topic. Review the slides and try the practice exercises."

        prompt = (
            f"You are a Socratic tutor ending the lesson on '{topic}'. "
            f"The student completed all 5 steps. {opening} {note} "
            f"Give a warm 2-3 sentence closing that: (1) summarises the key insight "
            f"about {topic}, (2) encourages the student, (3) suggests one thing to "
            f"try next. Be specific to {topic}, not generic."
        )
        try:
            return self.llm(prompt)
        except Exception:
            return f"{opening} {note} Keep practising and review your course slides on {topic}!"
