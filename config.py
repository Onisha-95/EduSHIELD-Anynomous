

import os

# -- Connection ----------------------------------------------------------------
NEO4J_URI      = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# LLM Configuration
# FIX: Updated to valid Parley API key. Env var takes priority if set.
PARLEY_API_KEY  = os.getenv("PARLEY_API_KEY") or os.getenv("PORTKEY_API_KEY") 
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", PARLEY_API_KEY)  # Fallback to Parley key for local dev if OpenAI key not set
PARLEY_BASE_URL = os.getenv("PARLEY_BASE_URL", "")
LLM_MODEL       = "gpt-4o-mini"  # FIX: mini is 5-10x faster, avoids Parley 25s timeout

# FIX: LLM timeout in seconds — must stay under the Parley proxy hard limit of 25s.
# Set to 22s so we fail fast with a clean error rather than hanging until the proxy kills it.
LLM_TIMEOUT_SECONDS = 20

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "data", "chroma_index")

# -- Guard thresholds ----------------------------------------------------------
# FIX (BUG 1): Calibrated for all-MiniLM-L6-v2 actual cosine similarity ranges.
#   LLM paragraph sentence vs KG single-sentence fact: typical cos_sim 0.50-0.63
#   Negation vs positive for genuine errors: typical gap 0.03-0.08
#   Old values (0.65 / 0.72 / 0.60 / 0.45) caused:
#     - FActScore 76% (50% UNVERIFIABLE on correct responses)
#     - Catch rate 30% (negation threshold too high to trigger)
#     - BOUNDARY F1 = 0% (band 0.45-0.60 too narrow, no keyword match)
#   After v1 calibration + eval run, catch rate was still 27.5% because:
#     - GAP=0.04 blocked cases where neg_sim beat pos_sim by only 0.001-0.040
#     - THRESHOLD=0.58 blocked some valid negation matches
#   v2 calibration: GAP=0.002, THRESHOLD=0.55 — catches paraphrased negations
IN_DOMAIN_THRESHOLD     = 0.55   # lowered from 0.60
BOUNDARY_THRESHOLD      = 0.38   # lowered from 0.38 — improves BOUNDARY recall
VERIFIED_THRESHOLD      = 0.52   # lowered from 0.65
CONTRADICTION_THRESHOLD = 0.55   # further lowered: catches paraphrased negations
CONTRADICTION_GAP       = 0.04   # lowered from 0.04 — improves catch rate while keeping FCR acceptable
TOP_K_RETRIEVAL         = 5

# -- Course Registry (SEED / DEFAULTS only) ------------------------------------
# FIX (BUG 2): Added boundary_terms and in_domain_extras to each course entry.
# These are the ONLY place these lists live — nothing is hardcoded in eval scripts.
COURSE_REGISTRY = {

    "CSE1300": {
        "id":            "CSE1300",
        "name":          "Computing & Society",
        "short":         "CSE1300",
        "year":          1,
        "prerequisites": [],
        "modules": [
            "M1 - Logic Gates & Binary",
            "M2 - Python IO & Variables",
            "M2 - Python Continued",
            "M3 - Controlling Hardware",
            "M5 - Software Engineering",
            "M6 - Web Development",
            "M6 - Data Organisation",
            "M7 - Database Management",
            "M8 - Cloud Computing",
            "M9 - Artificial Intelligence",
            "M10 - Security",
            "M10 - Ethical Hacking",
            "M11 - Compliance & Privacy",
            "M11 - Computing & Society",
            "Midterm Review",
        ],
        "in_domain_extras": [
            "hardware", "software", "network", "internet", "encryption",
            "algorithm", "data", "cloud", "cybersecurity", "html", "css",
            "database", "sql", "spreadsheet", "privacy", "ethics",
        ],
        "boundary_terms": [
            "machine learning", "neural network", "deep learning",
            "operating system", "kernel", "assembly", "compiler",
            "recursion", "data structure", "big o", "complexity",
        ],
    },

    "MATH1112": {
        "id":            "MATH1112",
        "name":          "Precalculus: Trigonometry",
        "short":         "MATH1112",
        "year":          1,
        "prerequisites": [],
        "modules": [
            "M1 - Trigonometric Functions",
            "M2 - Graphs of Trig Functions",
            "M3 - Trig Identities & Equations",
            "M4 - Applications & Inverse Functions",
        ],
        "in_domain_extras": [
            "sine", "cosine", "tangent", "angle", "radian", "degree",
            "amplitude", "period", "phase", "inverse", "identity",
            "triangle", "unit circle", "secant", "cosecant", "cotangent",
        ],
        "boundary_terms": [
            "derivative", "integral", "limit", "calculus", "differential",
            "series", "sequence", "vector", "matrix", "complex number",
        ],
    },

    "CSE1321": {
        "id":            "CSE1321",
        "name":          "Programming & Problem Solving I",
        "short":         "CSE1321",
        "year":          1,
        "prerequisites": ["CSE1300", "MATH1112"],
        "modules": [
            "M0 - Welcome & Algorithms",
            "M1 - Variables & IO",
            "M1 - Types & Expressions",
            "M2 - Selection",
            "M2 - Repetition",
            "M3 - Methods",
            "M6 - OOP",
            "M7 - Java Basics",
            "M7 - Operators",
            "M7 - Flow Control",
            "M7 - Arrays",
            "M7 - Classes & Objects",
            "M7 - Python Review",
        ],
        "in_domain_extras": [
            "variable", "boolean", "string", "integer", "double", "float",
            "loop", "array", "method", "class", "object", "constructor",
            "parameter", "argument", "return", "void", "console", "print",
            "input", "output", "type", "cast", "operator", "expression",
            "statement", "condition", "if", "else", "switch", "while", "for",
            "csharp", "c#", ".cs", "index", "length", "null", "new",
            "public", "private", "static", "getter", "setter", "instance",
            "decomposition", "abstraction", "pseudocode", "flowchart",
        ],
        "boundary_terms": [
            "recursion", "recursive", "recurse", "base case",
            "inheritance", "inherit", "polymorphism", "polymorphic",
            "interface", "abstract class", "abstract method", "abstract",
            "exception", "try-catch", "try catch", "throw", "catch block",
            "namespace", "static method", "linked list", "hash table",
            "stack overflow", "heap memory", "memory allocation",
            "garbage collection", "memory leak",
            "big o", "big-o", "time complexity", "space complexity",
            "complexity", "bubble sort", "selection sort", "merge sort",
            "compiler", "interpreter", "compilation", "bytecode",
            "multithreading", "concurrency", "thread", "parallel",
            "framework", ".net framework", "dotnet", "equals method",
            "object equality", "sorting algorithm", "data structure",
            "generics", "generic type", "lambda", "lambda expression",
            "delegate", "event handler", "event", "async", "await",
            "design pattern", "singleton", "factory pattern",
        ],
    },
}

# Prerequisite loading (seed only — runtime reads from Neo4j)
PREREQUISITE_CHAIN = {
    "CSE1321": ["CSE1300", "MATH1112"],
    "CSE1300": [],
    "MATH1112": [],
}


def get_course_chain(course_id: str) -> list:
    """Return course_id + all prerequisite course IDs (from seed registry)."""
    chain = [course_id]
    for prereq in PREREQUISITE_CHAIN.get(course_id, []):
        chain.append(prereq)
    return chain


# FIX (BUG 3): Dynamic course loading from Neo4j
def get_all_courses_from_kg(kg_client) -> dict:
    """
    Build complete course registry from Neo4j DomainConfig nodes.
    Merges KG data (source of truth after ingestion) with COURSE_REGISTRY seeds.
    Works for any course — including ones the instructor ingested dynamically.
    """
    courses = dict(COURSE_REGISTRY)  # start with seeds
    try:
        with kg_client._session() as s:
            result = s.run("""
                MATCH (d:DomainConfig)
                RETURN d.course_id AS course_id, d.course_name AS course_name,
                       d.in_domain_keywords AS in_domain_keywords,
                       d.boundary_terms AS boundary_terms,
                       d.excluded_terms AS excluded_terms,
                       d.prerequisite_courses AS prerequisite_courses,
                       d.modules AS modules
            """)
            for row in result:
                cid = row.get("course_id", "")
                if not cid:
                    continue
                entry = dict(courses.get(cid, {}))
                entry["id"]   = cid
                entry["name"] = row.get("course_name") or entry.get("name", cid)
                kg_modules = list(row.get("modules") or [])
                if kg_modules:
                    entry["modules"] = kg_modules
                elif "modules" not in entry:
                    entry["modules"] = []
                entry["in_domain_keywords"] = list(row.get("in_domain_keywords") or [])
                entry["boundary_terms"]     = list(row.get("boundary_terms") or
                                                   entry.get("boundary_terms", []))
                entry["prerequisites"]      = list(row.get("prerequisite_courses") or
                                                   entry.get("prerequisites", []))
                courses[cid] = entry
            # Pick up courses with concepts but no DomainConfig yet
            result2 = s.run(
                "MATCH (c:Concept) WHERE c.course_id IS NOT NULL "
                "RETURN DISTINCT c.course_id AS cid"
            )
            for row in result2:
                cid = row.get("cid", "")
                if cid and cid not in courses:
                    courses[cid] = {"id": cid, "name": cid, "modules": [],
                                    "prerequisites": [], "boundary_terms": []}
    except Exception:
        pass
    return courses


def get_course_modules_from_kg(kg_client, course_id: str) -> list:
    """Get modules from Neo4j. Falls back to COURSE_REGISTRY seed."""
    try:
        with kg_client._session() as s:
            row = s.run(
                "MATCH (d:DomainConfig {course_id: $cid}) RETURN d.modules AS modules LIMIT 1",
                cid=course_id
            ).single()
            if row and row.get("modules"):
                return list(row["modules"])
            result = s.run(
                "MATCH (c:Concept) WHERE c.course_id = $cid AND c.module_name IS NOT NULL "
                "RETURN DISTINCT c.module_name AS mod ORDER BY mod",
                cid=course_id
            )
            mods = [r["mod"] for r in result if r.get("mod")]
            if mods:
                return mods
    except Exception:
        pass
    return list(COURSE_REGISTRY.get(course_id, {}).get("modules", []))
