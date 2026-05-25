"""
RAG System — Embedding + ChromaDB Vector Index + Retrieval + Prompt Builder
Includes conversation history support for multi-turn memory.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from config import COURSE_REGISTRY
except ImportError:
    COURSE_REGISTRY = {}

MODIFIER_INSTRUCTIONS = {
    "normal":
        "Answer clearly and accurately. Use the verified course facts as your primary source. "
        "If the facts are sparse, supplement with general CS knowledge but stay on topic. "
        "Always include a short code example in the course language (Python for CSE1321, "
        "Python for CSE1300) when the question involves syntax, code, or how something works.",
    "scaffold":
        "The student is struggling. Simplify your explanation. "
        "Use a short real-world analogy first. Then break the answer into 2-3 numbered steps. "
        "Always end with a concrete code example showing the concept in action. "
        "Be encouraging and patient.",
    "advance":
        "The student already understands the basics. Go deeper — introduce nuance, "
        "edge cases, or connections to related concepts. "
        "Include a more complex code example that demonstrates a real use case.",
    "repeat_struggle":
        "The student has asked about this multiple times and is still confused. "
        "Use a COMPLETELY different explanation approach. "
        "Start fresh with a simple real-world analogy, then walk through a "
        "concrete step-by-step code example from scratch, line by line. "
        "Be patient and encouraging.",
}

LANGUAGE_TERMS = {
    "Java": ("java",),
    "C#": ("c#", "csharp", "c sharp"),
    "Python": ("python",),
    "JavaScript": ("javascript", "node.js", "nodejs"),
    "C++": ("c++", "cpp"),
}


def _detect_languages(text: str) -> list:
    found = []
    lowered = (text or "").lower()
    for language, terms in LANGUAGE_TERMS.items():
        if any(term in lowered for term in terms):
            found.append(language)
    return found


def _get_course_modules(course_id: str) -> list:
    if not course_id:
        return []
    return list(COURSE_REGISTRY.get(course_id, {}).get("modules", []))


class RAGSystem:

    def __init__(self, neo4j_client, chroma_path: str):
        self.kg          = neo4j_client
        self.chroma_path = chroma_path
        self._model      = None
        self._collection = None
        self._attempted_auto_rebuild = False

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print("Loading embedding model (first time only)...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[ok] Embedding model loaded")
        return self._model

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            client = chromadb.PersistentClient(path=self.chroma_path)
            self._collection = client.get_or_create_collection(
                name="kg_facts",
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    # -- BUILD INDEX --------------------------------------------------------
    def build_index(self) -> int:
        print("\n Building vector index from Neo4j facts...")
        facts = self.kg.get_all_facts()
        if not facts:
            print("No facts found in Neo4j — run ingestion first.")
            return 0

        model      = self._get_model()
        collection = self._get_collection()

        existing = collection.count()
        if existing > 0:
            print(f"   Clearing {existing} existing embeddings...")
            collection.delete(where={"source_file": {"$ne": ""}})

        documents, embeddings, metadatas, ids = [], [], [], []
        print(f"   Embedding {len(facts)} facts...")

        for i, fact in enumerate(facts):
            text = f"{fact['concept']}: {fact['claim']}"
            emb  = model.encode(text, show_progress_bar=False).tolist()
            documents.append(text)
            embeddings.append(emb)
            metadatas.append({
                "fact_id":         fact.get("fact_id", ""),
                "concept":         fact.get("concept", ""),
                "claim":           fact.get("claim", ""),
                "negation":        fact.get("negation", ""),
                "priority":        fact.get("priority", "MEDIUM"),
                "source_file":     fact.get("source_file", ""),
                "source_location": fact.get("source_location", ""),
            })
            ids.append(fact["fact_id"])
            if (i + 1) % 100 == 0:
                print(f"   ... {i+1}/{len(facts)} embedded")

        batch_size = 500
        for i in range(0, len(documents), batch_size):
            collection.add(
                documents=documents[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
                ids=ids[i:i+batch_size],
            )

        total = collection.count()
        print(f"[ok] Vector index built — {total} facts indexed in ChromaDB")
        return total

    # -- RETRIEVE CONTEXT ---------------------------------------------------
    def retrieve_context(self, query: str, top_k: int = 5) -> list:
        try:
            collection = self._get_collection()
        except Exception:
            return []

        if collection.count() == 0:
            return []

        model = self._get_model()

        query_emb = model.encode(query, show_progress_bar=False).tolist()
        results   = collection.query(
            query_embeddings=[query_emb],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        for i in range(len(results["documents"][0])):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i]
            retrieved.append({
                "text":            results["documents"][0][i],
                "fact_id":         meta["fact_id"],
                "concept":         meta["concept"],
                "claim":           meta["claim"],
                "negation":        meta["negation"],
                "priority":        meta["priority"],
                "source_file":     meta["source_file"],
                "source_location": meta["source_location"],
                "similarity":      round(1 - dist, 4),
            })
        return retrieved

    # -- BUILD PROMPT (with conversation history) ---------------------------
    def build_prompt(self, query: str, retrieved_facts: list,
                     context_modifier: str = "normal",
                     conversation_history: list = None,
                     course_name: str = None,
                     course_id: str = None,
                     prior_struggles: list = None) -> str:
        # Format KG facts
        if not retrieved_facts:
            context_block = "  No verified facts found for this specific query."
        else:
            lines = []
            for f in retrieved_facts:
                concept = f["concept"].upper()
                claim   = f["claim"]
                source  = f["source_file"]
                loc     = f["source_location"]
                lines.append(f"  [{concept}] {claim}  (Source: {source}, {loc})")
            context_block = "\n".join(lines)

        # Format conversation history
        history_block = ""
        if conversation_history:
            turns = []
            for msg in conversation_history[-6:]:
                role    = "Student"   if msg["role"] == "student"   else "Assistant"
                content = msg["content"][:300]
                turns.append(f"  {role}: {content}")
            if turns:
                history_block = "\nCONVERSATION HISTORY (most recent last):\n" + "\n".join(turns) + "\n"

        # Prior struggles from student profile
        struggle_block = ""
        if prior_struggles:
            struggle_block = (
                "\nSTUDENT PRIOR STRUGGLES (from previous sessions — give extra care on these): "
                + ", ".join(prior_struggles[:5])
                + "\n"
            )

        modifier_text = MODIFIER_INSTRUCTIONS.get(
            context_modifier, MODIFIER_INSTRUCTIONS["normal"]
        )

        # Build course context dynamically
        if course_name and course_id:
            course_ctx = f"{course_name} ({course_id})"
        elif course_id:
            course_ctx = course_id
        else:
            course_ctx = "this course"

        lang_instruction = ""
        course_language = COURSE_REGISTRY.get(course_id or "", {}).get("language", "") if course_id else ""

        if course_language:
            lang_instruction = (
                f"\n- Always use {course_language} for all code examples and syntax. "
                f"Do not use any other programming language unless the student explicitly asks about it."
            )
        elif course_id:
            _cid = (course_id or "").upper()
            if _cid == "CSE1321":
                # FIX: Changed from C# to Python for demo
                lang_instruction = (
                    "\n- This course uses Python. Always use Python for all code examples. "
                    "Never use C# or Java unless the student explicitly asks."
                )
            elif _cid == "CSE1300":
                lang_instruction = (
                    "\n- This course uses Python (introductory). Use Python for code examples. "
                    "Never switch to C# or Java unless the student explicitly asks."
                )
        else:
            language_signal = " ".join([query])
            detected_languages = _detect_languages(language_signal)
            if len(detected_languages) == 1:
                lang_instruction = (
                    f"\n- Use {detected_languages[0]} for all code examples unless the student asks otherwise."
                )

        # FIX: course_lang now Python for CSE1321
        course_lang = "Python" if (course_id or "").upper() in ("CSE1321", "CSE1300") else \
                      "the course language"

        return f"""You are a helpful educational assistant for {course_ctx}.
Your job is to help students learn the concepts covered in their lectures.

RULES:
- Use the verified course facts below as your PRIMARY source
- If course facts are sparse or missing, use your general CS knowledge — but stay on course topic
- Always include a practical code example in {course_lang} when the question involves code, syntax, or how something works
- If the student asks for an example specifically, always provide one — never refuse
- If the student makes an incorrect statement, gently correct them
- Be conversational — refer back to the conversation history when relevant
- Keep answers focused and concise (4-8 lines ideal){lang_instruction}
{history_block}
VERIFIED COURSE FACTS:
{context_block}

TEACHING STYLE: {modifier_text}{struggle_block}

STUDENT MESSAGE: {query}

RESPONSE:"""

    # -- TEST RETRIEVAL -----------------------------------------------------
    def test_retrieval(self, queries: list):
        print("\n-- RETRIEVAL TEST ---------------------------------------")
        for q in queries:
            print(f"\n  Query: '{q}'")
            results = self.retrieve_context(q, top_k=3)
            if not results:
                print("  No results.")
                continue
            for r in results:
                print(f"  [{r['similarity']:.3f}] [{r['concept']}] {r['claim'][:80]}")
        print()
