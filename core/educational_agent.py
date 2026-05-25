"""
Simple Educational Agent — Full Pipeline Orchestrator.

Flow for each student message:
  1. Add student message to conversation history
  2. Guard #2 -> classify domain + get session context flag
  3. If OUT_OF_DOMAIN -> block, return refusal (still logged to history)
  4. RAG -> retrieve top-5 relevant KG facts
  5. Build grounded prompt WITH full conversation history
  6. Call LLM -> grounded, context-aware, memory-enabled response
  7. Guard #1 -> validate LLM response against KG facts
  8. Update session state (struggle scores, mastery hints)
  9. Add assistant response to conversation history
 10. Return full result dict to Streamlit UI
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from session_manager      import init_session, add_to_history, update_session
from guard2_boundary      import KnowledgeBoundaryAgent
from guard1_hallucination import HallucinationDetectionAgent
from rag_system           import RAGSystem
from neo4j_client         import Neo4jKGClient

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from config import COURSE_REGISTRY
except ImportError:
    COURSE_REGISTRY = {}


def _strip_html(text: str) -> str:
    """
    Strip ALL HTML tags and Guard#1 UI artifacts from LLM response text.
    FIX: Added DOTALL div/span removal to strip Guard #1 badge HTML.
    """
    if not text:
        return ""
    t = str(text)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.IGNORECASE)
    t = re.sub(r"<div[^>]*>.*?</div>", "", t, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r"<span[^>]*>.*?</span>", "", t, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r"<[^>]+>", "", t, flags=re.IGNORECASE)
    t = re.sub(r"<[a-zA-Z][^<\n]*$", "", t, flags=re.MULTILINE)
    t = t.replace("[ok]", "")
    t = re.sub(r"✗\s*Incorrect:[^\n]*\n?", "", t)
    t = re.sub(r"✓\s*Correct:[^\n]*\n?", "", t)
    t = re.sub(r"Corrections based on your course knowledge:\s*", "", t)
    t = re.sub(r"⚠️\s*This answer could not be fully verified[^\n]*\n?", "", t)
    t = re.sub(r"📌\s*Answer verified[^\n]*\n?", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

# FIX (BUG D): Removed hardcoded "Python" — now dynamically built per course in respond()
# Use _out_of_domain_msg(course_name) instead of this constant
OUT_OF_DOMAIN_RESPONSE = (
    "That question is outside the scope of this course. "
    "Please ask something related to the material covered in your lectures."
)

BOUNDARY_PREFIX = (
    "This topic is at the edge of our course scope. "
    "Here's what we've covered:\n\n"
)


def _out_of_domain_msg(course_name: str = None) -> str:
    """FIX (BUG D): Dynamic OOD message naming the actual course, not hardcoded Python."""
    course = course_name or "this course"
    return (
        f"That question is outside the scope of {course}. "
        f"Please ask something related to the material covered in your lectures. "
        f"I can help with concepts, code examples, and practice problems from {course}."
    )


def _inject_prior_mastery(session: dict, profile: dict):
    """
    Seed a fresh session with the student's historical mastery from their profile.
    This means Guard #2 and the LLM already know about past struggles on day 1
    of a new session — not just within the current session.
    """
    mastery = profile.get("concept_mastery", {})
    for concept, data in mastery.items():
        struggle = data.get("struggle_score", 0)
        asked    = data.get("times_asked", 0)
        if asked == 0:
            continue
        # Seed concepts_encountered so struggle tracking continues from history
        session["concepts_encountered"][concept] = {
            "times_asked":     asked,
            "guard1_verdicts": [],
            "struggle_score":  struggle,
        }
        # Seed mastery hints
        if struggle >= 2:
            session["session_mastery_hints"][concept] = "STRUGGLING"
            if concept not in session["struggle_flags"]:
                session["struggle_flags"].append(concept)
        elif asked >= 3 and struggle == 0:
            session["session_mastery_hints"][concept] = "LIKELY_UNDERSTOOD"
        elif asked >= 1:
            session["session_mastery_hints"][concept] = "NEW"


class SimpleEducationalAgent:

    def __init__(self, neo4j_uri, neo4j_user, neo4j_password,
                 neo4j_database, chroma_path, parley_api_key,
                 llm_model=None, course_id: str = None):
        # FIX BUG-1: Was hardcoded "gpt-4o". Now reads LLM_MODEL from config
        # (gpt-4o-mini = 5-10x faster, the critical fix for Parley 25s timeout).
        if llm_model is None:
            try:
                from config import LLM_MODEL
                llm_model = LLM_MODEL
            except ImportError:
                llm_model = "gpt-4o-mini"
        self.kg = Neo4jKGClient(
            uri=neo4j_uri, user=neo4j_user,
            password=neo4j_password, database=neo4j_database
        )
        self.rag     = RAGSystem(self.kg, chroma_path)
        # Fetch domain config for the specified course
        domain_config = self.kg.get_domain_config(course_id=course_id)
        self.guard2  = KnowledgeBoundaryAgent(self.kg, self.rag, domain_config)
        self.guard1  = HallucinationDetectionAgent(self.kg, self.rag)
        from socratic_engine import SocraticEngine
        self.socratic = SocraticEngine(
            rag_system=self.rag,
            guard1=self.guard1,
            guard2=self.guard2,
            llm_caller=self._call_llm,
        )
        self.llm_key    = parley_api_key
        self.llm_model  = llm_model
        self.sessions         = {}    # session_id -> session dict
        self._student_profile = None   # set via set_student_profile()
        self.active_course_id   = None   # set by app.py when student selects course
        self.active_course_name = None
        # FIX BUG-2: Pre-load sentence-transformer model at startup.
        # Without this, the FIRST student query triggers a 10-15s model download/load
        # mid-request, which pushes total latency over the 25s Parley proxy limit.
        print("  Warming up embedding model...")
        try:
            self.rag._get_model()
            print("  [ok] Embedding model warm")
        except Exception as _e:
            print(f"  [!] Embedding warmup failed (non-fatal): {_e}")
        print(f"[ok] SimpleEducationalAgent initialized (model={self.llm_model})")

    # -- INGEST MATERIAL ----------------------------------------------------
    def ingest_material(self, filepath: str,
                        course_id: str = None,
                        module_name: str = None) -> dict:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "parsers"))
        from parsers import parse_document
        from extraction_engine import KnowledgeExtractionEngine
        parsed = parse_document(filepath)
        # Attach course/module metadata so the KG builder can tag nodes
        if course_id:
            parsed["course_id"] = course_id
        if module_name:
            parsed["module_name"] = module_name
        engine = KnowledgeExtractionEngine(self.kg)
        return engine.extract_and_write(parsed)

    # -- MAIN RESPOND METHOD ------------------------------------------------
    def respond(self, query: str, session_id: str,
                inject_response: str = None) -> dict:
        """
        Full pipeline for one student message.
        Handles questions, statements, corrections — anything the student types.
        """
        # Get or create session
        if session_id not in self.sessions:
            self.sessions[session_id] = init_session(session_id)
            # Inject prior mastery from student profile into new session
            if hasattr(self, "_student_profile") and self._student_profile:
                _inject_prior_mastery(self.sessions[session_id], self._student_profile)
        session = self.sessions[session_id]
        if self._student_profile:
            session["student_profile"] = self._student_profile

        # Step 1 — Log student message to history
        add_to_history(session, "student", query)

        # Step 2 — Guard #2: boundary + session context
        g2 = self.guard2.classify(query, session)

        # Step 3 — Block if out of domain
        # FIX: Only hard-block if RAG actually found facts AND classified OOD.
        # If RAG index is empty (score=0.0, no concept matched), treat as IN_DOMAIN
        # with UNVERIFIABLE — don't block the student from getting any answer.
        rag_is_empty = (
            g2.get("domain_match_score", 0.0) == 0.0
            and not g2.get("matched_concept")
        )
        if g2["classification"] == "OUT_OF_DOMAIN" and not rag_is_empty:
            prereq_hint = g2.get("prereq_hint")
            if prereq_hint:
                ood_msg = (
                    f"That topic belongs to {prereq_hint}, which is a prerequisite "
                    f"for {self.active_course_name or self.active_course_id or 'this course'}. "
                    f"Make sure you have completed {prereq_hint} first, or switch to that course."
                )
            else:
                ood_msg = _out_of_domain_msg(self.active_course_name)
            add_to_history(session, "assistant", ood_msg)
            return {
                "query":    query,
                "response": ood_msg,
                "blocked":  True,
                "guard2":   g2,
                "guard1":   None,
                "session":  self._session_summary(session),
            }

        # Step 4 — RAG: retrieve relevant KG facts
        # Use last 2 conversation turns + current query for better retrieval
        retrieval_query = self._build_retrieval_query(query, session)
        retrieved_facts = self.rag.retrieve_context(retrieval_query, top_k=5)
        retrieved_facts = self._merge_registry_facts(query, retrieved_facts)

        # Step 5 — Build prompt with conversation history
        # Build list of concepts student historically struggles with
        prior_struggles = session.get("struggle_flags", [])

        prompt = self.rag.build_prompt(
            query=query,
            retrieved_facts=retrieved_facts,
            context_modifier=g2["llm_modifier"],
            conversation_history=session["conversation_history"][:-1],
            course_name=self.active_course_name,
            course_id=self.active_course_id,
            prior_struggles=prior_struggles if prior_struggles else None,
        )

        # Step 6 — LLM call (or inject for demo)
        if inject_response:
            llm_response = inject_response
        else:
            llm_response = self._call_llm(prompt)

        # Step 7 — Guard #1: validate response against KG
        g1 = self.guard1.validate(llm_response, retrieved_facts, query)

        # Step 8 — Update session struggle tracking
        update_session(session, g2["matched_concept"], g1["verdict"])

        # Step 8b — Update persistent student profile if logged in
        if session.get("student_profile"):
            from student_profile import record_turn
            record_turn(
                session["student_profile"],
                g2["matched_concept"],
                g1["verdict"],
            )

        # Step 9 — Build final response and log to history
        # Strip any HTML/UI artifacts Guard#1 may have appended to delivered_response
        # so ALL consumers (Student Chat, Guide Mode, future pages) get clean plain text.
        final_response = _strip_html(g1["delivered_response"])
        if g2["classification"] == "BOUNDARY":
            final_response = BOUNDARY_PREFIX + final_response

        add_to_history(session, "assistant", final_response)

        # Step 10 — Return full result
        # Also expose clean_response on g1 so UI can access it directly if needed
        g1["clean_response"] = final_response
        return {
            "query":    query,
            "response": final_response,
            "blocked":  False,
            "guard2":   g2,
            "guard1":   g1,
            "session":  self._session_summary(session),
        }

    def _merge_registry_facts(self, query: str, retrieved_facts: list) -> list:
        course = COURSE_REGISTRY.get(self.active_course_id or "", {})
        modules = list(course.get("modules", []))
        if not modules:
            return retrieved_facts

        query_lower = (query or "").lower()
        tokens = set(re.findall(r"[a-zA-Z+#]{3,}", query_lower))
        stop_words = {
            "what", "which", "where", "when", "teach", "about", "module",
            "modules", "learn", "please", "basics", "intro", "introduction",
            "show", "tell", "from", "this", "that", "with",
        }
        tokens = {token for token in tokens if token not in stop_words}

        matched_modules = []
        for module in modules:
            module_lower = module.lower()
            if any(token in module_lower for token in tokens):
                matched_modules.append(module)

        asks_about_structure = "module" in query_lower or any(
            language in query_lower for language in ("java", "c#", "csharp", "python", "javascript")
        )
        if asks_about_structure and not matched_modules:
            matched_modules = modules

        registry_facts = []
        for module in matched_modules[:10]:
            registry_facts.append({
                "fact_id": f"registry::{self.active_course_id or 'course'}::{module}",
                "claim": f"{self.active_course_id or 'This course'} includes the module '{module}'.",
                "negation": "",
                "concept": module.lower(),
                "priority": "HIGH",
                "source_file": "COURSE_REGISTRY",
                "source_location": "module_name",
                "similarity": 1.0,
            })

        if not registry_facts:
            return retrieved_facts

        existing_claims = {fact.get("claim", "") for fact in retrieved_facts}
        merged = list(retrieved_facts)
        for fact in registry_facts:
            if fact["claim"] not in existing_claims:
                merged.append(fact)
        return merged

    # -- RETRIEVAL QUERY BUILDER --------------------------------------------
    def _build_retrieval_query(self, query: str, session: dict) -> str:
        """
        Combine current query with recent context for better RAG retrieval.
        If student says "can you give an example?" we need prior context
        to know what topic to retrieve facts about.
        """
        history = session.get("conversation_history", [])
        # Get last student message before current one (for context)
        recent_student = [
            m["content"] for m in history[-4:]
            if m["role"] == "student"
        ]
        if len(recent_student) > 1:
            # Combine previous student message + current for richer retrieval
            return recent_student[-2] + " " + query
        return query

    # -- LLM CALL (Parley — OpenAI compatible) -----------------------------
    def _call_llm(self, prompt: str) -> str:
        """
        FIX: Added explicit timeout to both the OpenAI client and the
        completions call. The Parley proxy hard-kills requests at 25s,
        so we set our own limit to 22s to fail fast with a clean error
        message instead of hanging and getting a cryptic proxy timeout.
        """
        from openai import OpenAI
        from config import OPENAI_API_KEY, PARLEY_BASE_URL, LLM_TIMEOUT_SECONDS

        # Use OpenAI directly if API key is provided, otherwise use Parley
        if OPENAI_API_KEY:
            client = OpenAI(
                api_key=OPENAI_API_KEY,
                timeout=LLM_TIMEOUT_SECONDS,      # FIX: client-level timeout
            )
        else:
            client = OpenAI(
                api_key=self.llm_key,
                base_url=PARLEY_BASE_URL,
                timeout=LLM_TIMEOUT_SECONDS,      # FIX: client-level timeout
            )

        try:
            response = client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600,
                timeout=LLM_TIMEOUT_SECONDS,      # FIX: call-level timeout (belt + suspenders)
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "401" in low or "unauthorized" in low or "portkey" in low:
                raise RuntimeError(
                    "LLM authentication failed (401). "
                    "Check your PARLEY_API_KEY in config.py and restart Streamlit."
                )
            if "timeout" in low or "timed out" in low:
                raise RuntimeError(
                    f"LLM request timed out after {LLM_TIMEOUT_SECONDS}s. "
                    "The Parley API may be under load — please try again."
                )
            raise

    def _call_llm_large(self, prompt: str, max_tokens: int = 1800) -> str:
        """
        FIX BUG-3: Guide Mode was calling _call_llm (max_tokens=600) for the
        full lesson JSON that needs 1000-2000 tokens. The truncated response
        failed JSON parsing and silently fell back to hardcoded FALLBACK content,
        so Guide Mode appeared to work but never generated real course material.
        Use this method for any prompt that needs a long structured response.
        """
        from openai import OpenAI
        from config import OPENAI_API_KEY, PARLEY_BASE_URL, LLM_TIMEOUT_SECONDS
        if OPENAI_API_KEY:
            client = OpenAI(api_key=OPENAI_API_KEY, timeout=LLM_TIMEOUT_SECONDS)
        else:
            client = OpenAI(api_key=self.llm_key, base_url=PARLEY_BASE_URL,
                            timeout=LLM_TIMEOUT_SECONDS)
        try:
            response = client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=LLM_TIMEOUT_SECONDS,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "timeout" in low or "timed out" in low:
                raise RuntimeError(
                    f"LLM request timed out after {LLM_TIMEOUT_SECONDS}s. "
                    "Parley API may be under load — please try again."
                )
            raise

    # -- SESSION SUMMARY ----------------------------------------------------
    def _session_summary(self, session: dict) -> dict:
        return {
            "session_id":            session["session_id"],
            "concepts_encountered":  session["concepts_encountered"],
            "struggle_flags":        session["struggle_flags"],
            "session_mastery_hints": session["session_mastery_hints"],
            "turn_count":            len(session["conversation_history"]),
        }

    def start_lesson(self, topic: str, session_id: str) -> dict:
        import session_manager as sm
        if session_id not in self.sessions:
            self.sessions[session_id] = sm.init_session(session_id)
            if self._student_profile:
                _inject_prior_mastery(self.sessions[session_id], self._student_profile)
        if self._student_profile:
            self.sessions[session_id]["student_profile"] = self._student_profile
        result = self.socratic.start_lesson(topic, self.sessions[session_id])
        # Record lesson start in profile
        session = self.sessions[session_id]
        if session.get("student_profile"):
            from student_profile import start_lesson_record
            lid = start_lesson_record(session["student_profile"], topic)
            session["current_lesson_id"] = lid
        return result

    def advance_lesson(self, student_answer: str, session_id: str) -> dict:
        if session_id not in self.sessions:
            return {"error": "No session found."}
        session = self.sessions[session_id]
        result  = self.socratic.advance(student_answer, session)
        # Update lesson record in profile
        if session.get("student_profile") and session.get("current_lesson_id"):
            from student_profile import update_lesson_record
            g1_verdict = (result.get("guard1") or {}).get("verdict", "UNVERIFIABLE")
            update_lesson_record(
                session["student_profile"],
                session["current_lesson_id"],
                step=result.get("step", 1),
                verdict=g1_verdict,
                complete=result.get("complete", False),
            )
        return result

    def get_lesson_state(self, session_id: str) -> dict:
        session = self.sessions.get(session_id, {})
        return session.get("socratic_lesson", {})

    def set_student_profile(self, profile: dict):
        """
        Called by app.py when a student logs in.
        Stores profile so new sessions are seeded with prior mastery data.
        """
        self._student_profile = profile
        for session in self.sessions.values():
            session["student_profile"] = profile

    def close(self):
        self.kg.close()
