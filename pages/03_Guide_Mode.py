"""
Guide Mode — 5-step Socratic lesson.
Topics pulled live from the KG. Content generated dynamically by LLM.
"""
import streamlit as st, sys, os, uuid, random, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.design_system import get_css, render_sidebar

st.set_page_config(page_title="Guide Mode", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
st.markdown(get_css(), unsafe_allow_html=True)
st.markdown("""<style>
#MainMenu,footer{visibility:hidden}
[data-testid="stHeader"]{visibility:hidden}
.block-container{padding-top:0!important}
[data-testid="stForm"]{border:none!important;padding:0!important;background:transparent!important}
:root{
  --bg2:#F4F6F9;--white:#FFFFFF;--border:#E2E6EE;
  --ink:#0F172A;--ink2:#334155;--ink3:#64748B;--ink4:#94A3B8;
  --blue:#2563EB;--blue-l:#EEF3FD;--blue-m:#BFCFFA;
  --teal:#0D9488;--teal-l:#ECFDF5;--teal-m:#99F6E4;
  --amber:#D97706;--amber-l:#FFFBEB;--amber-m:#FDE68A;
  --green:#16A34A;--green-l:#F0FDF4;--green-m:#86EFAC;
  --violet:#7C3AED;--violet-l:#F3EFFE;--violet-m:#C4B5FD;
  --shadow:0 1px 3px rgba(15,23,42,.08),0 4px 16px rgba(15,23,42,.04);
}
/* topic pills */
.topic-pill{display:inline-flex;align-items:center;gap:5px;padding:5px 13px;
  border:1.5px solid #E2E8F0;border-radius:20px;background:#fff;
  font-size:12px;color:#334155;margin:2px;transition:all .15s}
.topic-pill.on{background:#EEF3FD;border-color:#2563EB;color:#2563EB;font-weight:600}
/* plan card */
.plan-card{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;
           padding:16px 18px;margin:10px 0 16px}
.plan-row{display:flex;align-items:flex-start;gap:10px;padding:5px 0;
          border-bottom:1px solid #F1F5F9}
.plan-num{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
          min-width:18px;color:#94A3B8;padding-top:1px}
.plan-now-num{color:#2563EB!important}
.plan-title{font-size:12px;font-weight:600;color:#64748B}
.plan-title-now{color:#0F172A!important}
.plan-sub{font-size:11px;color:#94A3B8}
/* step bar */
.sbar{display:flex;align-items:flex-start;gap:0;padding:12px 0 8px;
      border-bottom:1px solid #E2E8F0;margin-bottom:12px}
.snode{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;
       justify-content:center;font-family:'JetBrains Mono',monospace;
       font-size:11px;font-weight:800;flex-shrink:0}
.s-done{background:#16A34A;color:#fff}
.s-now {background:#2563EB;color:#fff;box-shadow:0 0 0 4px rgba(37,99,235,.15)}
.s-todo{background:#F4F6F9;color:#94A3B8;border:2px solid #E2E8F0}
.sline{flex:1;height:3px;margin-top:13px}
.sl-done{background:#16A34A}.sl-todo{background:#E2E8F0}
/* chat bubbles in guide */
.gb-bot{background:#fff;border:1px solid #E2E8F0;border-radius:3px 12px 12px 12px;
        padding:13px 17px;font-size:13px;line-height:1.85;color:#334155;
        box-shadow:0 1px 3px rgba(15,23,42,.05);margin-bottom:8px}
.gb-user{background:#2563EB;color:#fff;border-radius:12px 12px 3px 12px;
         padding:10px 15px;font-size:13px;line-height:1.75;
         display:inline-block;max-width:70%;float:right;clear:both;margin-bottom:8px}
.gb-wrap-user{text-align:right;overflow:hidden;margin-bottom:6px}
.gb-from{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:1px;
         color:#94A3B8;text-transform:uppercase;margin-bottom:3px}
.verdict-chip{display:inline-flex;align-items:center;gap:4px;border-radius:20px;
  padding:2px 8px;font-size:8px;font-weight:700;
  font-family:'JetBrains Mono',monospace;margin-bottom:4px}
/* code block */
.code-wrap{background:#0F172A;border-radius:10px;padding:16px 18px;
           font-family:'JetBrains Mono',monospace;font-size:13px;
           line-height:2.0;margin:8px 0;overflow-x:auto}
/* token buttons */
.tok-revealed{background:rgba(255,255,255,.12)!important;border-radius:4px}
/* guard panel */
.gp-card{background:#fff;border:1px solid #E2E8F0;border-radius:10px;
         padding:11px 13px;margin-bottom:8px}
.gp-lbl{font-family:'JetBrains Mono',monospace;font-size:7px;letter-spacing:2px;
        color:#94A3B8;text-transform:uppercase;margin-bottom:6px}
.gp-row{display:flex;justify-content:space-between;font-size:11px;
        color:#64748B;padding:2px 0;border-bottom:1px solid #F4F6F9}
.gp-val{font-family:'JetBrains Mono',monospace;font-size:10px;
        color:#334155;font-weight:600}
/* module cards */
.mod-card{background:#fff;border:2px solid #E2E8F0;border-radius:14px;
          padding:14px;transition:border-color .15s;margin-bottom:4px}
</style>""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
agent = st.session_state.get("agent")
if not agent:
    st.error("Not connected — go Home first.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

profile   = st.session_state.get("student_profile") or {
    "student_id":"guest","name":"Guest","xp":0,"concept_mastery":{},"lesson_history":[]}
cname     = st.session_state.get("active_course_name", agent.active_course_name or "")
course_id = st.session_state.get("active_course_id","CSE1321")

with st.sidebar:
    render_sidebar(profile, active_page="guide")

# ── Module styles ─────────────────────────────────────────────────────────────
MOD_STYLES=[
    {"icon":"🚀","color":"#7C3AED","bg":"#F3EFFE","border":"#C4B5FD"},
    {"icon":"📦","color":"#2563EB","bg":"#EEF3FD","border":"#BFCFFA"},
    {"icon":"🔀","color":"#059669","bg":"#ECFDF5","border":"#6EE7B7"},
    {"icon":"⚙️","color":"#D97706","bg":"#FFFBEB","border":"#FDE68A"},
    {"icon":"🧩","color":"#DB2777","bg":"#FDF2F8","border":"#F9A8D4"},
    {"icon":"☕","color":"#B45309","bg":"#FEF3C7","border":"#FCD34D"},
    {"icon":"🔬","color":"#0891B2","bg":"#ECFEFF","border":"#A5F3FC"},
    {"icon":"🏗️","color":"#4338CA","bg":"#EEF2FF","border":"#C7D2FE"},
]

# ── Fetch topics from KG ──────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=600)
def fetch_kg_modules(course_filter=None):
    """Pull concepts grouped by module_name from Neo4j.
    If course_filter provided, filter to only that course's concepts."""
    BAD = re.compile(
        r'that is|and a|or a|of a|name and|given by|used to|'
        r'^(true|false|null|none|this|that|with|from|into|high|low|good|bad|'
        r'set|lot|way|end|top|suite|guide|radian|robot|modem|colon)$',
        re.IGNORECASE)

    def clean(t):
        s = re.sub(r'^(a|an|the)\s+', '', t.strip(), flags=re.IGNORECASE).strip()
        if not s or len(s)<3 or len(s)>45: return None
        if not s[0].isalpha(): return None
        if any(c in s for c in '()[]{}=<>!&|;\\/@$%#`'): return None
        if len(s.split())>4: return None
        if BAD.search(s): return None
        return s.title()

    try:
        from collections import defaultdict
        groups = defaultdict(set)
        with agent.kg._session() as sess:
            # Use course_id parameter if provided, otherwise get all concepts
            if course_filter:
                query = """
                    MATCH (c:Concept)
                    WHERE c.label IS NOT NULL AND c.course_id = $cid
                    RETURN c.label AS label, c.module_name AS mod, c.source_file AS sf
                    ORDER BY c.module_name, c.label LIMIT 3000
                """
                rows = sess.run(query, cid=course_filter)
            else:
                rows = sess.run("""
                    MATCH (c:Concept)
                    WHERE c.label IS NOT NULL
                    RETURN c.label AS label, c.module_name AS mod, c.source_file AS sf
                    ORDER BY c.module_name, c.label LIMIT 3000
                """)
            for r in rows:
                label = r.get("label","")
                mod   = r.get("mod") or r.get("sf") or "General"
                mod   = re.sub(r'_+',' ',mod)
                mod   = re.sub(r'\.pptx.*','',mod,flags=re.IGNORECASE).strip().title()
                mod   = re.sub(r'\s+',' ',mod).strip()
                c = clean(label)
                if c: groups[mod].add(c)

        # Use dynamic groups if we have real module diversity
        if groups:
            # If everything collapsed into one generic bucket, try to split by source_file too
            if len(groups) == 1 and "General" in groups:
                # Re-query grouping by source_file instead
                groups2 = defaultdict(set)
                with agent.kg._session() as sess2:
                    q2 = ("MATCH (c:Concept) WHERE c.label IS NOT NULL AND c.course_id = $cid "
                          "RETURN c.label AS label, c.source_file AS sf LIMIT 3000") if course_filter else \
                         "MATCH (c:Concept) WHERE c.label IS NOT NULL RETURN c.label AS label, c.source_file AS sf LIMIT 3000"
                    params2 = {"cid": course_filter} if course_filter else {}
                    for r in sess2.run(q2, **params2):
                        sf  = r.get("sf") or "General"
                        sf  = re.sub(r'_+', ' ', sf)
                        sf  = re.sub(r'\.pptx.*', '', sf, flags=re.IGNORECASE).strip().title()
                        sf  = re.sub(r'\s+', ' ', sf).strip() or "General"
                        c   = clean(r.get("label", ""))
                        if c: groups2[sf].add(c)
                if len(groups2) > 1:
                    groups = groups2
            mods = []
            for i, (name, topics) in enumerate(sorted(groups.items())):
                if not topics: continue
                s = MOD_STYLES[i % len(MOD_STYLES)]
                mods.append({"id": f"M{i}", "label": name, "icon": s["icon"],
                             "color": s["color"], "bg": s["bg"], "border": s["border"],
                             "topics": sorted(list(topics))})
            if mods:
                return mods
    except Exception:
        pass

    # ── Fallback: build from COURSE_REGISTRY modules + all KG concepts for that course ──
    from config import COURSE_REGISTRY
    cid_to_use = course_filter or ""
    cr = COURSE_REGISTRY.get(cid_to_use, {})
    registry_modules = cr.get("modules", [])

    # Try to load all concepts for this course from KG, grouped by module_name
    fallback_groups: dict = {}
    try:
        from collections import defaultdict as _dd
        fg = _dd(set)
        with agent.kg._session() as sess:
            params = {"cid": cid_to_use} if cid_to_use else {}
            q = ("MATCH (c:Concept) WHERE c.label IS NOT NULL AND c.course_id = $cid "
                 "RETURN c.label AS label, c.module_name AS mod, c.source_file AS sf LIMIT 5000") \
                if cid_to_use else \
                "MATCH (c:Concept) WHERE c.label IS NOT NULL " \
                "RETURN c.label AS label, c.module_name AS mod, c.source_file AS sf LIMIT 5000"
            for r in sess.run(q, **params):
                raw_mod = r.get("mod") or r.get("sf") or ""
                raw_mod = re.sub(r'_+', ' ', raw_mod)
                raw_mod = re.sub(r'\.pptx.*', '', raw_mod, flags=re.IGNORECASE).strip().title()
                raw_mod = re.sub(r'\s+', ' ', raw_mod).strip()
                # Map to registry module name if close enough
                matched_mod = raw_mod
                for rm in registry_modules:
                    rm_short = rm.split(" — ")[-1].strip().lower()
                    if rm_short and (rm_short in raw_mod.lower() or raw_mod.lower() in rm_short):
                        matched_mod = rm
                        break
                c = clean(r.get("label", ""))
                if c:
                    fg[matched_mod or "General"].add(c)
        fallback_groups = dict(fg)
    except Exception:
        pass

    if fallback_groups:
        mods = []
        # Sort modules in registry order where possible
        ordered_keys = []
        for rm in registry_modules:
            if rm in fallback_groups:
                ordered_keys.append(rm)
        for k in sorted(fallback_groups.keys()):
            if k not in ordered_keys:
                ordered_keys.append(k)
        for i, name in enumerate(ordered_keys):
            topics = fallback_groups.get(name)
            if not topics: continue
            s = MOD_STYLES[i % len(MOD_STYLES)]
            mods.append({"id": f"M{i}", "label": name, "icon": s["icon"],
                         "color": s["color"], "bg": s["bg"], "border": s["border"],
                         "topics": sorted(list(topics))})
        if mods:
            return mods

    # ── Final static fallback: use full registry module list with placeholder topics ──
    if registry_modules:
        mods = []
        for i, mod_name in enumerate(registry_modules):
            s = MOD_STYLES[i % len(MOD_STYLES)]
            short = mod_name.split(" — ")[-1].strip() if " — " in mod_name else mod_name.strip()
            mods.append({"id": f"M{i}", "label": mod_name, "icon": s["icon"],
                         "color": s["color"], "bg": s["bg"], "border": s["border"],
                         "topics": [short]})
        return mods

    # Absolute last resort — CSE1321 defaults
    return [
        {"id":"M0","label":"M0 — Welcome & Algorithms","icon":"🚀","color":"#7C3AED",
         "bg":"#F3EFFE","border":"#C4B5FD",
         "topics":["Algorithms","Abstraction","Pseudocode","Flowcharts","Problem Solving"]},
        {"id":"M1","label":"M1 — Variables & IO","icon":"📦","color":"#2563EB",
         "bg":"#EEF3FD","border":"#BFCFFA",
         "topics":["Variables","Data Types","Input And Output","Expressions","Operators","Type Casting"]},
        {"id":"M2","label":"M2 — Selection & Loops","icon":"🔀","color":"#059669",
         "bg":"#ECFDF5","border":"#6EE7B7",
         "topics":["If Statement","While Loop","For Loop","Nested Loop","Boolean Logic","Loop Counter","Break","Sentinel Value"]},
        {"id":"M3","label":"M3 — Methods","icon":"⚙️","color":"#D97706",
         "bg":"#FFFBEB","border":"#FDE68A",
         "topics":["Methods","Functions","Parameters","Return Values","Scope","Void Methods"]},
        {"id":"M6","label":"M6 — OOP","icon":"🧩","color":"#DB2777",
         "bg":"#FDF2F8","border":"#F9A8D4",
         "topics":["Classes","Objects","Attributes","Constructors","Encapsulation","Inheritance"]},
        {"id":"M7","label":"M7 — Java","icon":"☕","color":"#B45309",
         "bg":"#FEF3C7","border":"#FCD34D",
         "topics":["Java Basics","Arrays","Flow Control","Classes And Objects","Arraylists"]},
    ]

# ── KG fact retrieval for a topic (slide-grounded) ───────────────────────────
def _get_slide_facts(topic: str, course_id_filter: str = None, top_k: int = 12) -> str:
    """Retrieve all KG facts + RAG context for a topic and return as a formatted string."""
    lines = []

    # 1. Pull facts directly from Neo4j for this concept
    try:
        with agent.kg._session() as sess:
            params: dict = {"label": topic.lower().strip()}
            cypher = """
                MATCH (f:Fact)-[:DESCRIBES]->(c:Concept)
                WHERE toLower(c.label) CONTAINS toLower($label)
            """
            if course_id_filter:
                cypher += " AND c.course_id = $cid"
                params["cid"] = course_id_filter
            cypher += """
                RETURN f.claim AS claim, f.source_file AS src,
                       f.source_location AS loc, c.label AS concept
                ORDER BY f.priority DESC LIMIT 40
            """
            rows = sess.run(cypher, **params)
            for r in rows:
                claim = r.get("claim", "").strip()
                src   = r.get("src", "")
                loc   = r.get("loc", "")
                conc  = r.get("concept", "").title()
                if claim:
                    lines.append(f"[{conc}] {claim}  (slide: {src} {loc})")
    except Exception:
        pass

    # 2. Semantic RAG retrieval for broader context
    try:
        rag_hits = agent.rag.retrieve_context(topic, top_k=top_k)
        for h in rag_hits:
            if h.get("similarity", 0) > 0.30:
                claim = h.get("claim", "").strip()
                conc  = h.get("concept", "").title()
                src   = h.get("source_file", "")
                if claim and claim not in "\n".join(lines):
                    lines.append(f"[{conc}] {claim}  (slide: {src})")
    except Exception:
        pass

    # 3. Also get related concepts from KG graph
    try:
        with agent.kg._session() as sess:
            params2: dict = {"label": topic.lower().strip()}
            cypher2 = """
                MATCH (a:Concept)-[r]->(b:Concept)
                WHERE toLower(a.label) CONTAINS toLower($label)
            """
            if course_id_filter:
                cypher2 += " AND a.course_id = $cid"
                params2["cid"] = course_id_filter
            cypher2 += " RETURN type(r) AS rel, b.label AS related LIMIT 20"
            for r in sess.run(cypher2, **params2):
                rel     = r.get("rel", "").replace("_", " ").lower()
                related = r.get("related", "").title()
                if related:
                    lines.append(f"[Relationship] {topic.title()} {rel} {related}")
    except Exception:
        pass

    return "\n".join(lines[:60]) if lines else ""


# ── LLM lesson generator ──────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def generate_lesson(topic: str, course: str, course_id_filter: str = "") -> dict:
    """Generate a 5-step lesson grounded in actual slide facts from the KG."""

    slide_facts = _get_slide_facts(topic, course_id_filter or None)

    if slide_facts:
        facts_section = f"""VERIFIED SLIDE FACTS FOR "{topic.upper()}" FROM {course}:
{slide_facts}

IMPORTANT: Use ONLY the above slide facts as your primary source.
Do NOT invent information not present above.
All explanations, examples, and code must reflect the actual course content."""
    else:
        facts_section = f"""No specific slide facts found for "{topic}".
Generate pedagogically correct content for a first-year CS course."""

    prompt = f'''You are building a 5-step interactive lesson for "{topic}" in the course "{course}".

{facts_section}

Return ONLY valid JSON (no markdown fences) with this exact structure:
{{
  "slide_title": "short descriptive title from the slides",
  "slide_body": "2-3 sentence explanation grounded in slide content above. Use <strong> for key terms.",
  "starters": ["option 1", "option 2", "option 3", "No idea — show me"],
  "tokens": [
    {{"text":"keyword","color":"#F472B6","exp":"one sentence explanation from slides"}},
    {{"text":"token2","color":"#A78BFA","exp":"explanation"}},
    {{"text":"token3","color":"#60A5FA","exp":"explanation"}},
    {{"text":"token4","color":"#34D399","exp":"explanation"}},
    {{"text":"token5","color":"#FBBF24","exp":"explanation"}}
  ],
  "trace_code": ["line1", "    line2", "line3"],
  "trace_steps": [
    {{"active":0,"i":"val","out":[],"desc":"what happens"}},
    {{"active":1,"i":"val","out":["output"],"desc":"what happens"}},
    {{"active":-1,"i":"final","out":["output"],"desc":"Done."}}
  ],
  "recall": [
    {{"id":"r1","text":"first key step"}},
    {{"id":"r2","text":"second"}},
    {{"id":"r3","text":"third"}},
    {{"id":"r4","text":"fourth"}},
    {{"id":"r5","text":"fifth"}}
  ],
  "recall_order": ["r1","r2","r3","r4","r5"],
  "bug_question": "This code has a bug. Which line?",
  "bug_options": [
    {{"label":"A","code":"correct code","correct":false}},
    {{"label":"B","code":"buggy line","correct":true,"note":"why it is wrong"}},
    {{"label":"C","code":"correct code","correct":false}},
    {{"label":"D","code":"correct code","correct":false}}
  ],
  "bug_explain": "One sentence: what the bug is and how to fix it based on the slide content."
}}
Rules: tokens must be real keywords/syntax from the topic. trace_steps active is 0-based line index (-1=done). Return ONLY JSON.'''

    try:
        raw = agent._call_llm_large(prompt, max_tokens=1800)  # FIX BUG-3: was _call_llm (600 tokens) — JSON needs 1000-2000
        raw = re.sub(r'^```json\s*', '', raw.strip())
        raw = re.sub(r'^```\s*',      '', raw.strip())
        raw = re.sub(r'\s*```$',      '', raw.strip())
        data = json.loads(raw)
        required = ["slide_title", "slide_body", "starters", "tokens", "trace_code",
                    "trace_steps", "recall", "recall_order", "bug_question",
                    "bug_options", "bug_explain"]
        if all(k in data for k in required):
            return data
    except Exception:
        pass
    return None

# Hardcoded fallback for 4 key topics
FALLBACK = {
    "for loop":{"slide_title":"What is a For Loop?",
      "slide_body":"A <strong>for loop</strong> repeats code a fixed number of times — like printing 30 grade reports without writing print 30 times.<br><br><code>for i in range(5):</code> runs 5 times, giving i = 0,1,2,3,4.",
      "starters":["It repeats something","It runs code multiple times","It counts through numbers","No idea — show me"],
      "tokens":[{"text":"for","color":"#F472B6","exp":"Keyword that opens the loop."},{"text":"i","color":"#A78BFA","exp":"Loop variable — holds current value, updates automatically."},{"text":"in","color":"#F472B6","exp":"Connects variable to the sequence."},{"text":"range(1,6):","color":"#60A5FA","exp":"Generates 1,2,3,4,5. Stop value 6 is excluded."},{"text":"print(i)","color":"#34D399","exp":"Loop body — indented 4 spaces, runs once per value."}],
      "trace_code":["for i in range(1,4):","    print(i)"],
      "trace_steps":[{"active":0,"i":"1","out":[],"desc":"i=1, start."},{"active":1,"i":"1","out":["1"],"desc":"print(1)"},{"active":0,"i":"2","out":["1"],"desc":"i=2"},{"active":1,"i":"2","out":["1","2"],"desc":"print(2)"},{"active":0,"i":"3","out":["1","2"],"desc":"i=3"},{"active":1,"i":"3","out":["1","2","3"],"desc":"print(3)"},{"active":-1,"i":"—","out":["1","2","3"],"desc":"✓ i=4 > range end. Done."}],
      "recall":[{"id":"r1","text":"Set i to first value"},{"id":"r2","text":"Check i is in range"},{"id":"r3","text":"Run indented body"},{"id":"r4","text":"Advance i to next value"},{"id":"r5","text":"Exit when past range end"}],
      "recall_order":["r1","r2","r3","r4","r5"],
      "bug_question":"Should print 1–5. Which line has the bug?",
      "bug_options":[{"label":"A","code":"for i in range(1, 6):","correct":False},{"label":"B","code":"    print(i)","correct":False},{"label":"C","code":"for i in range(6):","correct":True,"note":"starts at 0, not 1!"},{"label":"D","code":"    print('hello')","correct":False}],
      "bug_explain":"range(6) gives 0–5. Use range(1,6) to start from 1."},
    "while loop":{"slide_title":"What is a While Loop?",
      "slide_body":"A <strong>while loop</strong> repeats as long as a condition is True. Unlike a for loop, you don't know in advance how many times it runs.<br><br><strong>Analogy:</strong> Keep stirring soup <em>while</em> it's not hot yet.",
      "starters":["It loops until condition is false","It repeats while something is true","Like for loop but flexible","No idea — show me"],
      "tokens":[{"text":"while","color":"#F472B6","exp":"Keyword — keep running while what follows is True."},{"text":"count < 3:","color":"#60A5FA","exp":"Condition — checked before every iteration."},{"text":"print(count)","color":"#34D399","exp":"Body line 1 — prints current value."},{"text":"count += 1","color":"#A78BFA","exp":"Must increment! Without this → infinite loop."}],
      "trace_code":["count = 0","while count < 2:","    print(count)","    count += 1"],
      "trace_steps":[{"active":0,"i":"0","out":[],"desc":"count=0"},{"active":1,"i":"0","out":[],"desc":"0<2? Yes"},{"active":2,"i":"0","out":["0"],"desc":"print(0)"},{"active":3,"i":"1","out":["0"],"desc":"count=1"},{"active":1,"i":"1","out":["0"],"desc":"1<2? Yes"},{"active":2,"i":"1","out":["0","1"],"desc":"print(1)"},{"active":3,"i":"2","out":["0","1"],"desc":"count=2"},{"active":1,"i":"2","out":["0","1"],"desc":"2<2? No → exit"},{"active":-1,"i":"2","out":["0","1"],"desc":"✓ Done."}],
      "recall":[{"id":"r1","text":"Check condition"},{"id":"r2","text":"If True, run body"},{"id":"r3","text":"Update loop variable"},{"id":"r4","text":"Go back, check again"},{"id":"r5","text":"If False, exit"}],
      "recall_order":["r1","r2","r3","r4","r5"],
      "bug_question":"Should print 1,2,3. What's wrong?",
      "bug_options":[{"label":"A","code":"count = 1","correct":False},{"label":"B","code":"while count < 4:","correct":False},{"label":"C","code":"    print(count)","correct":False},{"label":"D","code":"# count += 1 missing","correct":True,"note":"→ infinite loop!"}],
      "bug_explain":"Without count += 1, count never changes and the loop runs forever."},
    "variables":{"slide_title":"What is a Variable?",
      "slide_body":"A <strong>variable</strong> is a named storage box in memory.<br><br><strong>Analogy:</strong> Saving 'Alex' as a phone contact — the name is the variable, the number is the value.<br><br><code>age = 20</code> stores 20 in a box called age.",
      "starters":["A named storage box","It holds a value","Like a label on a container","No idea — show me"],
      "tokens":[{"text":"age","color":"#A78BFA","exp":"Variable name — you choose it. Be descriptive."},{"text":"=","color":"#F472B6","exp":"Assignment — stores right side into left name. NOT equals."},{"text":"20","color":"#60A5FA","exp":"The value stored. Integer. Can reassign: age = 21."},{"text":"name","color":"#A78BFA","exp":"Another variable. Case-sensitive: Name ≠ name."},{"text":'"Tasnim"',"color":"#34D399","exp":"String value — text in quotes."}],
      "trace_code":["x = 5","x = x + 1","print(x)"],
      "trace_steps":[{"active":0,"i":"5","out":[],"desc":"x created, value=5"},{"active":1,"i":"6","out":[],"desc":"x = 5+1 = 6"},{"active":2,"i":"6","out":["6"],"desc":"print → 6"},{"active":-1,"i":"6","out":["6"],"desc":"✓ Done."}],
      "recall":[{"id":"r1","text":"Pick a descriptive name"},{"id":"r2","text":"Use = to assign"},{"id":"r3","text":"Put value on the right"},{"id":"r4","text":"Python stores in memory"},{"id":"r5","text":"Reassign anytime"}],
      "recall_order":["r1","r2","r3","r4","r5"],
      "bug_question":"Should print 10. Spot the bug:",
      "bug_options":[{"label":"A","code":"number = 5","correct":False},{"label":"B","code":"number = number + 5","correct":False},{"label":"C","code":"print(Number)","correct":True,"note":"Number ≠ number"},{"label":"D","code":"# no bug","correct":False}],
      "bug_explain":"Python is case-sensitive. Number and number are different variables."},
    "if statement":{"slide_title":"What is an If Statement?",
      "slide_body":"An <strong>if statement</strong> makes decisions — runs code only when a condition is True.<br><br><strong>Analogy:</strong> <em>If it's raining → take umbrella. Else → wear sunglasses.</em>",
      "starters":["It checks if something is true","It makes a decision","Runs code only when condition is met","No idea — show me"],
      "tokens":[{"text":"if","color":"#F472B6","exp":"Keyword — what follows is the condition."},{"text":"temp > 30:","color":"#60A5FA","exp":"Condition — evaluates to True or False."},{"text":'print("Hot!")',"color":"#34D399","exp":"If-body — only runs when condition is True. Must indent."},{"text":"else:","color":"#F472B6","exp":"Optional — runs when condition is False."},{"text":'print("Cool.")',"color":"#A78BFA","exp":"Else-body — runs when temp ≤ 30."}],
      "trace_code":["temp = 35","if temp > 30:",'    print("Hot!")',"else:",'    print("Cool.")'],
      "trace_steps":[{"active":0,"i":"35","out":[],"desc":"temp=35"},{"active":1,"i":"35","out":[],"desc":"35>30? True"},{"active":2,"i":"35","out":["Hot!"],"desc":"print Hot!"},{"active":-1,"i":"35","out":["Hot!"],"desc":"✓ else skipped."}],
      "recall":[{"id":"r1","text":"Write if + condition"},{"id":"r2","text":"Add colon after condition"},{"id":"r3","text":"Indent body 4 spaces"},{"id":"r4","text":"Add optional else:"},{"id":"r5","text":"Python runs correct branch"}],
      "recall_order":["r1","r2","r3","r4","r5"],
      "bug_question":"Should print Pass when score >= 60. What's wrong?",
      "bug_options":[{"label":"A","code":"score = 75","correct":False},{"label":"B","code":"if score > 60","correct":True,"note":"Missing colon!"},{"label":"C","code":"    print('Pass')","correct":False},{"label":"D","code":"# no bug","correct":False}],
      "bug_explain":"Every if must end with a colon :  Without it Python raises SyntaxError."},
}

def get_lesson(topic):
    t = topic.lower().strip()
    for k,v in FALLBACK.items():
        if k==t or k in t or t in k: return v
    cache_key = f"lesson_{t}_{course_id}"
    if cache_key in st.session_state and st.session_state[cache_key]:
        return st.session_state[cache_key]
    gen = generate_lesson(t, cname, course_id)
    if gen:
        st.session_state[cache_key] = gen
        return gen
    # Minimal generic fallback
    return {"slide_title":f"What is {topic.title()}?",
      "slide_body":f"<strong>{topic.title()}</strong> is a key concept in {cname}. Understanding it helps you write better programs.",
      "starters":["I have some idea","I've seen this before","It might be related to code structure","No idea — show me"],
      "tokens":[{"text":topic.split()[0],"color":"#F472B6","exp":f"Core keyword for {topic}."},{"text":":","color":"#60A5FA","exp":"Colon ends the statement header."},{"text":"    body","color":"#34D399","exp":"Indented body runs as part of the structure."},{"text":"result","color":"#A78BFA","exp":"Output or result produced."},{"text":"end","color":"#FBBF24","exp":"Structure ends when indentation returns."}],
      "trace_code":[f"# {topic} example","# See course slides for details"],
      "trace_steps":[{"active":0,"i":"—","out":[],"desc":f"This demonstrates {topic}."},{"active":-1,"i":"—","out":["..."],"desc":"✓ Done."}],
      "recall":[{"id":"r1","text":f"Understand what {topic} solves"},{"id":"r2","text":"Learn the syntax"},{"id":"r3","text":"Write a simple example"},{"id":"r4","text":"Test with different inputs"},{"id":"r5","text":"Apply in a real program"}],
      "recall_order":["r1","r2","r3","r4","r5"],
      "bug_question":f"What is the most common mistake with {topic}?",
      "bug_options":[{"label":"A","code":"Wrong indentation (not 4 spaces)","correct":True,"note":"#1 Python error"},{"label":"B","code":"Wrong variable name","correct":False},{"label":"C","code":"Missing colon","correct":False},{"label":"D","code":"Forgetting to import","correct":False}],
      "bug_explain":"Wrong indentation is the #1 mistake. Always use 4 spaces."}

# ── Session ───────────────────────────────────────────────────────────────────
def _init():
    for k,v in {"gm_topic":None,"gm_step":0,"gm_xp":0,"gm_verdicts":[],
                "gm_sid":str(uuid.uuid4()),"gm_sel_mod":None,
                "gm_tokens_revealed":set(),"gm_trace_pos":0,
                "gm_recall_order":None,"gm_recall_done":False,
                "gm_recall_score":0,"gm_bug_answered":False,
        "gm_bug_correct":False,"gm_write_done":False,
        "gm_write_ok":False,"gm_write_feedback":"",
                "gm_step1_done":False}.items():
        if k not in st.session_state: st.session_state[k]=v

_init()

# Handle sidebar module click
if "gm_preselect_mod" in st.session_state:
    pm = st.session_state.pop("gm_preselect_mod")
    mods = fetch_kg_modules(course_id)
    m = next((x for x in mods if pm.lower() in x["label"].lower() or x["label"].lower() in pm.lower()),None)
    if m: st.session_state.gm_sel_mod = m["id"]
    st.session_state.gm_step = 0

topic  = st.session_state.gm_topic
step   = st.session_state.gm_step
XP     = 10

def award(n): st.session_state.gm_xp += n

def reset():
    for k in ["gm_topic","gm_step","gm_xp","gm_verdicts","gm_tokens_revealed",
              "gm_trace_pos","gm_recall_order","gm_recall_done","gm_recall_score",
        "gm_bug_answered","gm_bug_correct","gm_write_done","gm_write_ok",
        "gm_write_feedback","gm_step1_done"]:
        if k in st.session_state: del st.session_state[k]
    if "gm_saved" in st.session_state: del st.session_state["gm_saved"]
    _init()

STEPS=[("1","Plain words","Describe in your own words"),
       ("2","Code reading","Tap each part to explore"),
       ("3","Execution trace","Watch it run step by step"),
       ("4","Recall","Put the steps in order"),
       ("5","Write it","Spot the bug")]

def step_bar(cur):
    if cur<1: return
    html="<div class='sbar'>"
    for i,(n,title,_) in enumerate(STEPS):
        s=i+1
        cls="s-done" if s<cur else ("s-now" if s==cur else "s-todo")
        sym="✓" if s<cur else n
        html+=f"<div style='display:flex;flex-direction:column;align-items:center;gap:2px;'>"
        html+=f"<div class='snode {cls}'>{sym}</div>"
        html+=f"<div style='font-family:JetBrains Mono,monospace;font-size:8px;color:#94A3B8;text-transform:uppercase;letter-spacing:1px;margin-top:2px;white-space:nowrap;'>{title}</div></div>"
        if i<4:
            lc="sl-done" if s<cur else "sl-todo"
            html+=f"<div class='sline {lc}' style='margin-bottom:18px;'></div>"
    html+="</div>"
    st.markdown(html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TOPIC PICKER
# ══════════════════════════════════════════════════════════════════════════════
if step==0:
    # Header
    hc1,hc2 = st.columns([1,9])
    with hc1:
        if st.button("←", key="gm_home"): st.switch_page("app.py")
    with hc2:
        st.markdown(f"""
<div style="padding:8px 0 6px;display:flex;align-items:center;gap:10px;">
  <span style="font-size:22px;">🎓</span>
  <div>
    <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:16px;
                font-weight:800;color:#0F172A;">Guide Mode</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:#94A3B8;
                letter-spacing:1px;text-transform:uppercase;">
      Socratic Tutor · {cname}
    </div>
  </div>
  <div style="margin-left:auto;background:#EEF3FD;color:#2563EB;border:1px solid #BFCFFA;
    border-radius:20px;padding:3px 12px;font-family:'JetBrains Mono',monospace;
    font-size:9px;font-weight:700;">INTELLIGENT TUTOR</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:1px;background:#E2E8F0;margin-bottom:12px;"></div>', unsafe_allow_html=True)

    # ── Course Selector ────────────────────────────────────────────────────────
    if "gm_selected_course" not in st.session_state:
        st.session_state.gm_selected_course = course_id

    from config import COURSE_REGISTRY
    available_courses = sorted(COURSE_REGISTRY.keys())

    course_cols = st.columns(len(available_courses))
    for idx, course in enumerate(available_courses):
        with course_cols[idx]:
            is_selected = st.session_state.gm_selected_course == course
            if st.button(
                course,
                key=f"course_sel_{course}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.gm_selected_course = course
                st.session_state.gm_sel_mod = None
                st.rerun()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # Fetch modules for selected course
    modules = fetch_kg_modules(st.session_state.gm_selected_course)

    mastery = profile.get("concept_mastery",{})
    lessons = profile.get("lesson_history",[])
    done_tops = {l.get("topic","").lower() for l in lessons if l.get("steps_completed",0)>=5}
    sel_mod = st.session_state.gm_sel_mod

    main_c, hist_c = st.columns([3,1], gap="large")

    with hist_c:
        st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:8px;letter-spacing:2px;color:#94A3B8;text-transform:uppercase;margin:0 0 8px;">Recent</div>', unsafe_allow_html=True)
        recent = lessons[-4:][::-1] if lessons else []
        if recent:
            for l in recent:
                t=l.get("topic","—"); s=l.get("steps_completed",0)
                st.markdown(f"""
<div style="background:#fff;border:1px solid #E2E8F0;border-radius:8px;
            padding:7px 11px;margin-bottom:4px;">
  <div style="font-size:12px;font-weight:600;color:#0F172A;">{t.title()}</div>
  <div style="font-size:10px;color:#64748B;">{s}/5 {'✅' if s>=5 else '🔄'}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:11px;color:#94A3B8;padding:8px 0;">No lessons yet</div>', unsafe_allow_html=True)

    with main_c:
        if sel_mod is None:
            st.markdown("""
<div style="margin-bottom:12px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.2rem;font-weight:800;color:#0F172A;">
    Choose a topic to study
  </div>
  <div style="font-size:13px;color:#64748B;margin-top:3px;">
    I will <em>never give you the answer</em> — you reason it out. I only ask questions.
  </div>
</div>""", unsafe_allow_html=True)
            cols=st.columns(3)
            for i,mod in enumerate(modules):
                done_c=sum(1 for t in mod["topics"] if t.lower() in done_tops)
                pct=int(done_c/max(len(mod["topics"]),1)*100)
                with cols[i%3]:
                    st.markdown(f"""
<div style="background:{mod['bg']};border:2px solid {mod['border']};border-radius:14px;
            padding:13px;margin-bottom:2px;">
  <div style="font-size:22px;margin-bottom:5px;">{mod['icon']}</div>
  <div style="font-size:12px;font-weight:800;color:{mod['color']};margin-bottom:2px;">
    {mod['label'][:28]}
  </div>
  <div style="font-size:10px;color:#64748B;margin-bottom:7px;">
    {len(mod['topics'])} topics · {done_c} done
  </div>
  <div style="background:#E2E8F0;border-radius:2px;height:3px;">
    <div style="background:{mod['color']};border-radius:2px;height:3px;width:{pct}%;"></div>
  </div>
</div>""", unsafe_allow_html=True)
                    if st.button(f"Open {mod['id']}", key=f"om_{mod['id']}", use_container_width=True):
                        st.session_state.gm_sel_mod=mod["id"]; st.rerun()
        else:
            mod=next((m for m in modules if m["id"]==sel_mod),modules[0])
            bc,mc=st.columns([1,7])
            with bc:
                if st.button("← Back", key="bk_mod"):
                    st.session_state.gm_sel_mod=None; st.rerun()
            with mc:
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0 10px;">
  <span style="font-size:22px;">{mod['icon']}</span>
  <div>
    <div style="font-size:15px;font-weight:800;color:{mod['color']}">{mod['label']}</div>
    <div style="font-size:11px;color:#64748B;">{len(mod['topics'])} topics from your course slides</div>
  </div>
</div>""", unsafe_allow_html=True)

            # Topic pills — clicking starts lesson
            st.markdown('<div style="margin-bottom:6px;font-family:JetBrains Mono,monospace;font-size:8px;letter-spacing:2px;color:#94A3B8;text-transform:uppercase;">TOPICS</div>', unsafe_allow_html=True)
            tcols=st.columns(3)
            for j,t in enumerate(mod["topics"]):
                d=mastery.get(t.lower(),mastery.get(t,{}))
                score=d.get("struggle_score",0)
                done=t.lower() in done_tops
                if done:     bg,bdr,col,badge="#DCFCE7","#86EFAC","#15803D","✅"
                elif score>=2: bg,bdr,col,badge="#FEE2E2","#FCA5A5","#B91C1C","🔴"
                else:          bg,bdr,col,badge="#fff","#E2E8F0","#334155",""
                with tcols[j%3]:
                    st.markdown(f"""
<div style="background:{bg};border:1.5px solid {bdr};border-radius:9px;
            padding:9px 12px;margin-bottom:2px;">
  <div style="display:flex;align-items:center;justify-content:space-between;">
    <span style="font-size:12px;font-weight:600;color:{col};">{t}</span>
    <span style="font-size:11px;">{badge}</span>
  </div>
</div>""", unsafe_allow_html=True)
                    typ="primary" if score>=2 else "secondary"
                    if st.button(f"Study {t}", key=f"st_{t}_{j}", use_container_width=True, type=typ):
                        reset()
                        st.session_state.gm_topic=t
                        st.session_state.gm_sel_mod=sel_mod
                        st.session_state.gm_step=-1  # loading
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# LOADING STATE
# ══════════════════════════════════════════════════════════════════════════════
elif step==-1:
    tl=st.session_state.gm_topic
    st.markdown(f"""
<div style="text-align:center;padding:60px 20px;">
  <div style="font-size:36px;margin-bottom:14px;">🧠</div>
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.2rem;
    font-weight:800;color:#0F172A;margin-bottom:6px;">
    Building lesson on <em>{tl.title()}</em>…
  </div>
  <div style="font-size:12px;color:#64748B;">
    Pulling facts from your course Knowledge Graph · Generating 5 interactive steps
  </div>
</div>""", unsafe_allow_html=True)
    with st.spinner(""):
        _=get_lesson(tl)
    st.session_state.gm_step=1
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ACTIVE LESSON
# ══════════════════════════════════════════════════════════════════════════════
elif 1<=step<=5:
    kg=get_lesson(topic)

    # Top bar
    tc1,tc2,tc3=st.columns([1,1,7])
    with tc1:
        if st.button("✕ Exit",key="gm_x"): reset(); st.rerun()
    with tc2:
        if step>1:
            if st.button("← Back",key="gm_bk"):
                st.session_state.gm_step=max(1,step-1)
                if step==2: st.session_state.gm_tokens_revealed=set()
                elif step==3: st.session_state.gm_trace_pos=0
                elif step==4: st.session_state.gm_recall_done=False
                elif step==5: st.session_state.gm_bug_answered=False
                if st.session_state.gm_verdicts: st.session_state.gm_verdicts.pop()
                st.rerun()
    with tc3:
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;padding:6px 0;">
  <span style="font-family:'Bricolage Grotesque',sans-serif;font-size:16px;
    font-weight:800;color:#0F172A;">🎓 {topic.title()}</span>
  <span style="background:#EEF3FD;color:#2563EB;border:1px solid #BFCFFA;
    font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;
    padding:2px 9px;border-radius:20px;">GUIDE MODE</span>
  <span style="margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:9px;
    color:#D97706;background:#FFFBEB;border:1px solid #FDE68A;
    padding:2px 9px;border-radius:20px;">⚡ {st.session_state.gm_xp} XP</span>
</div>""", unsafe_allow_html=True)

    step_bar(step)

    main_c, rp_c = st.columns([3,1], gap="small")

    # Right panel
    with rp_c:
        vs=st.session_state.gm_verdicts
        st.markdown(f"""
<div class="gp-card">
  <div class="gp-lbl">Guard Activity</div>
  <div class="gp-row"><span>XP Earned</span><span class="gp-val">{st.session_state.gm_xp}</span></div>
  <div class="gp-row"><span>Steps done</span><span class="gp-val">{step-1}/5</span></div>
</div>""", unsafe_allow_html=True)
        if vs:
            rows="".join(f'<div class="gp-row"><span>Step {i+1}</span><span class="gp-val" style="color:{"#16A34A" if v=="CORRECT" else "#D97706" if v=="PARTIAL" else "#B91C1C"}">{v}</span></div>' for i,v in enumerate(vs))
            st.markdown(f'<div class="gp-card"><div class="gp-lbl">Step Results</div>{rows}</div>',unsafe_allow_html=True)
        mode_map={1:"📝 Plain Words",2:"👆 Code Reading",3:"▶ Execution Trace",4:"🔀 Recall",5:"✍ Write It"}
        state_map={1:"Ready — Step 1 of 5",2:"Guiding — Step 2",3:"Tracing — Step 3",4:"Recalling — Step 4",5:"Writing — Step 5"}
        st.markdown(f"""
<div class="gp-card">
  <div class="gp-lbl">Student State</div>
  <div style="font-size:11px;font-weight:600;color:#2563EB;">🎓 {state_map.get(step,"")}</div>
</div>""", unsafe_allow_html=True)

    with main_c:

        # ── STEP 1 ────────────────────────────────────────────────────────────
        if step==1 and not st.session_state.gm_step1_done:
            # Session plan
            rows_html=""
            for i,(n,title,sub) in enumerate(STEPS):
                nc="plan-now-num" if i==0 else ""
                tc="plan-title-now" if i==0 else ""
                badge='<span style="margin-left:auto;background:#EEF3FD;color:#2563EB;border:1px solid #BFCFFA;font-family:JetBrains Mono,monospace;font-size:8px;font-weight:700;padding:2px 8px;border-radius:20px;">NOW</span>' if i==0 else ""
                rows_html+=f'<div class="plan-row"><span class="plan-num {nc}">{n}</span><div><div class="plan-title {tc}">{title}</div><div class="plan-sub">{sub}</div></div>{badge}</div>'
            st.markdown(f'<div class="plan-card"><div style="font-family:JetBrains Mono,monospace;font-size:8px;letter-spacing:2px;color:#94A3B8;text-transform:uppercase;margin-bottom:8px;">Session Plan — 5 Steps</div>{rows_html}</div>', unsafe_allow_html=True)

            st.markdown(f"""
<div style="margin:4px 0 12px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.05rem;
    font-weight:800;color:#0F172A;">
    Step 1 — In plain words, what do you think a <em>{topic}</em> does?
  </div>
  <div style="font-size:12px;color:#64748B;margin-top:4px;">
    No code yet. Just describe the idea in your own words. Click a starter below, or type your own.
  </div>
</div>""", unsafe_allow_html=True)

            starters=kg.get("starters",["I have an idea","No idea — show me"])
            sc=st.columns(len(starters))
            for i,s in enumerate(starters):
                with sc[i]:
                    if st.button(s,key=f"str_{i}",use_container_width=True):
                        noidea="no idea" in s.lower() or "show me" in s.lower()
                        st.session_state.gm_verdicts.append("PARTIAL" if noidea else "CORRECT")
                        award(5 if noidea else XP)
                        st.session_state.gm_step1_done=True
                        st.session_state.gm_step=2; st.rerun()

            with st.form("s1f",clear_on_submit=True):
                a1=st.text_input("ans",placeholder="Type your answer…",label_visibility="collapsed")
                if st.form_submit_button("Submit →",type="primary",use_container_width=True) and a1.strip():
                    noi=any(p in a1.lower() for p in ["no idea","idk","don't know","not sure","no clue"])
                    st.session_state.gm_verdicts.append("PARTIAL" if noi else "CORRECT")
                    award(5 if noi else XP)
                    st.session_state.gm_step1_done=True
                    st.session_state.gm_step=2; st.rerun()

        # ── STEP 2: Annotated code ────────────────────────────────────────────
        elif step==2:
            st.markdown(f"""
<div style="margin:4px 0 12px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.05rem;font-weight:800;color:#0F172A;">
    Step 2 — Tap each highlighted part to discover what it does
  </div>
  <div style="font-size:12px;color:#64748B;margin-top:4px;">
    Real code from your course Knowledge Graph. Tap every colored word.
  </div>
</div>""", unsafe_allow_html=True)

            # Concept slide
            st.markdown(f"""
<div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;margin-bottom:10px;box-shadow:0 1px 3px rgba(15,23,42,.05);">
  <div style="background:linear-gradient(135deg,#2563EB,#1e40af);padding:8px 14px;display:flex;align-items:center;justify-content:space-between;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:8px;color:rgba(255,255,255,.8);letter-spacing:1px;">
      ✦ KG-Sourced · KG → Concept Node: "{topic}"
    </span>
  </div>
  <div style="padding:14px 16px;font-size:13px;line-height:1.85;color:#334155;">
    <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:14px;font-weight:800;color:#0F172A;margin-bottom:8px;">{kg['slide_title']}</div>
    {kg['slide_body']}
  </div>
</div>""", unsafe_allow_html=True)

            tokens=kg["tokens"]
            revealed=st.session_state.gm_tokens_revealed

            # Code block with colored tokens
            st.markdown("""
<div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;">
  <div style="background:#1E293B;padding:9px 14px;display:flex;align-items:center;justify-content:space-between;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#94A3B8;letter-spacing:1px;">
      CODE EXAMPLE — TAP EACH HIGHLIGHTED PART
    </span>
    <span style="font-size:11px;color:#60A5FA;">👆 Tap to reveal</span>
  </div>
  <div style="background:#0F172A;padding:16px 20px;font-family:'JetBrains Mono',monospace;font-size:14px;line-height:2.2;display:flex;flex-wrap:wrap;gap:4px;align-items:baseline;">""", unsafe_allow_html=True)

            tok_cols=st.columns(len(tokens))
            for i,tok in enumerate(tokens):
                with tok_cols[i]:
                    bg="rgba(255,255,255,.12);border-radius:4px;padding:1px 4px;" if i in revealed else ""
                    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:13px;color:{tok["color"]};{bg}text-align:center;">{tok["text"]}</div>',unsafe_allow_html=True)
                    if st.button("▼",key=f"tok_{i}",use_container_width=True,help=f"Reveal: {tok['text']}"):
                        st.session_state.gm_tokens_revealed.add(i); st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

            if revealed:
                li=max(revealed)
                st.markdown(f"""
<div style="padding:10px 14px;font-size:12px;color:#334155;background:#F0F9FF;
            border-top:1px solid #BAE6FD;line-height:1.7;border-radius:0 0 12px 12px;">
  💡 <strong>{tokens[li]['text']}</strong> — {tokens[li]['exp']}
</div>""", unsafe_allow_html=True)

            n_rev=len(revealed)
            pct=int(n_rev/len(tokens)*100)
            label=f"✓ All {len(tokens)} parts explored — you know every piece!" if n_rev==len(tokens) else f"{n_rev} / {len(tokens)} parts explored"
            lcolor="#059669" if n_rev==len(tokens) else "#64748B"
            st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 14px;border-top:1px solid #E2E8F0;margin-bottom:8px;">
  <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:{lcolor};">{label}</span>
  <div style="flex:1;height:4px;background:#E2E8F0;border-radius:2px;margin-left:12px;">
    <div style="height:4px;background:#059669;border-radius:2px;width:{pct}%;transition:width .3s;"></div>
  </div>
</div>""", unsafe_allow_html=True)

            if n_rev==len(tokens):
                if st.button("Continue to Step 3 →",type="primary",use_container_width=True,key="to3"):
                    st.session_state.gm_verdicts.append("CORRECT"); award(XP)
                    st.session_state.gm_step=3; st.rerun()
            else:
                st.info(f"Tap all {len(tokens)} colored parts to unlock Step 3.")

        # ── STEP 3: Execution trace ───────────────────────────────────────────
        elif step==3:
            st.markdown("""
<div style="margin:4px 0 12px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.05rem;font-weight:800;color:#0F172A;">
    Step 3 — Watch it run step by step
  </div>
  <div style="font-size:12px;color:#64748B;margin-top:4px;">
    Press Next Step and watch how each line executes.
  </div>
</div>""", unsafe_allow_html=True)

            ts=kg["trace_steps"]; tc=kg["trace_code"]
            pos=st.session_state.gm_trace_pos
            cur=ts[min(pos,len(ts)-1)]

            st.markdown('<div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;">', unsafe_allow_html=True)
            code_html='<div style="background:#0F172A;padding:14px 18px;font-family:JetBrains Mono,monospace;font-size:13px;line-height:2.2;">'
            for li,line in enumerate(tc):
                act=li==cur["active"]
                bg="background:rgba(37,99,235,.3);border-radius:4px;" if act else ""
                col="#BFDBFE" if act else "#94A3B8"
                arr="→ " if act else "   "
                indent="&nbsp;"*(len(line)-len(line.lstrip()))
                code=line.strip().replace("<","&lt;").replace(">","&gt;")
                code_html+=f'<div style="{bg}padding:1px 6px;"><span style="color:#475569;font-size:10px;margin-right:6px;">{arr}</span>{indent}<span style="color:{col};">{code}</span></div>'
            code_html+="</div>"
            st.markdown(code_html, unsafe_allow_html=True)

            out_str="  ".join(cur["out"]) if cur["out"] else "nothing yet"
            st.markdown(f"""
<div style="background:#F8FAFC;padding:12px 16px;display:flex;gap:24px;align-items:center;border-top:1px solid #E2E8F0;">
  <div style="text-align:center;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:7px;color:#94A3B8;letter-spacing:2px;text-transform:uppercase;margin-bottom:3px;">Variable</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:800;color:#2563EB;">{cur['i']}</div>
  </div>
  <div style="text-align:center;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:7px;color:#94A3B8;letter-spacing:2px;text-transform:uppercase;margin-bottom:3px;">Output</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:#059669;">{out_str}</div>
  </div>
  <div style="font-size:12px;color:#334155;line-height:1.6;flex:1;">{cur['desc']}</div>
</div>
</div>""", unsafe_allow_html=True)

            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
            done_t=pos>=len(ts)-1
            nc1,nc2=st.columns([4,1])
            with nc1:
                if not done_t:
                    if st.button("▶ Next Step",type="primary",use_container_width=True,key="tn"):
                        st.session_state.gm_trace_pos+=1; st.rerun()
                else:
                    st.success("✓ Trace complete!")
                    if st.button("Continue to Step 4 →",type="primary",use_container_width=True,key="to4"):
                        st.session_state.gm_verdicts.append("CORRECT"); award(XP)
                        st.session_state.gm_step=4; st.rerun()
            with nc2:
                if st.button("↺",key="tr",use_container_width=True):
                    st.session_state.gm_trace_pos=0; st.rerun()

        # ── STEP 4: Recall ────────────────────────────────────────────────────
        elif step==4:
            st.markdown(f"""
<div style="margin:4px 0 12px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.05rem;font-weight:800;color:#0F172A;">
    Step 4 — Put the steps in order from memory
  </div>
  <div style="font-size:12px;color:#64748B;margin-top:4px;">Number these 1–5 in the correct order for {topic}.</div>
</div>""", unsafe_allow_html=True)

            ri=kg["recall"]; ro=kg["recall_order"]
            if not st.session_state.gm_recall_done:
                if st.session_state.gm_recall_order is None:
                    sh=ri.copy(); random.shuffle(sh)
                    st.session_state.gm_recall_order=sh
                sh=st.session_state.gm_recall_order
                sels={}
                for item in sh:
                    c1,c2=st.columns([1,6])
                    with c1: num=st.selectbox("",["—","1","2","3","4","5"],key=f"rc_{item['id']}",label_visibility="collapsed")
                    with c2: st.markdown(f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:9px 13px;margin:2px 0;font-size:12px;color:#334155;">{item["text"]}</div>',unsafe_allow_html=True)
                    sels[item["id"]]=num
                if st.button("Check My Order →",type="primary",use_container_width=True,key="rc_chk"):
                    numbered={v:k for k,v in sels.items() if v!="—"}
                    submitted=[numbered.get(str(i)) for i in range(1,6)]
                    score=sum(1 for s,c in zip(submitted,ro) if s==c)
                    st.session_state.gm_recall_done=True
                    st.session_state.gm_recall_score=score; st.rerun()
            else:
                score=st.session_state.gm_recall_score
                v="CORRECT" if score>=4 else ("PARTIAL" if score>=2 else "INCORRECT")
                if score>=4: st.success(f"✅ {score}/5 correct!")
                elif score>=2: st.warning(f"🟡 {score}/5 — almost!")
                else: st.error(f"❌ {score}/5 — let's review")
                for i,rid in enumerate(ro):
                    item=next(r for r in ri if r["id"]==rid)
                    st.markdown(f'<div style="display:flex;align-items:center;gap:10px;background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;padding:8px 13px;margin:3px 0;"><span style="font-family:JetBrains Mono,monospace;font-size:12px;font-weight:800;color:#16A34A;">{i+1}</span><span style="font-size:12px;color:#334155;">{item["text"]}</span></div>',unsafe_allow_html=True)
                if st.button("Continue to Step 5 →",type="primary",use_container_width=True,key="to5"):
                    st.session_state.gm_verdicts.append(v)
                    award(XP if v=="CORRECT" else 5)
                    st.session_state.gm_step=5; st.rerun()

        # ── STEP 5: Bug + Write ───────────────────────────────────────────────
        elif step==5:
            st.markdown(f"""
<div style="margin:4px 0 12px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.05rem;font-weight:800;color:#0F172A;">
    Step 5 — Spot the bug, then write it yourself
  </div>
  <div style="font-size:12px;color:#64748B;margin-top:4px;">{kg['bug_question']}</div>
</div>""", unsafe_allow_html=True)

            if not st.session_state.gm_bug_answered:
                for opt in kg["bug_options"]:
                    if st.button(f"{opt['label']}.  {opt['code']}",key=f"bg_{opt['label']}",
                                 use_container_width=True,
                                 type="secondary"):
                        st.session_state.gm_bug_answered=True
                        st.session_state.gm_bug_correct=opt["correct"]; st.rerun()
            else:
                for opt in kg["bug_options"]:
                    bg="#DCFCE7" if opt["correct"] else "#FEF2F2"
                    bdr="#86EFAC" if opt["correct"] else "#FECACA"
                    col="#15803D" if opt["correct"] else "#991B1B"
                    note=opt.get("note","")
                    st.markdown(f'<div style="display:flex;align-items:center;gap:10px;background:{bg};border:1.5px solid {bdr};border-radius:8px;padding:10px 14px;margin:3px 0;font-family:JetBrains Mono,monospace;font-size:12px;color:{col};"><span style="font-weight:800;">{opt["label"]}.</span><span style="flex:1;">{opt["code"]}</span>{f"<span style=font-size:10px;>{note}</span>" if note else ""}</div>',unsafe_allow_html=True)
                st.markdown(f'<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:10px 14px;margin:8px 0;font-size:12px;color:#1E40AF;line-height:1.7;">💡 {kg["bug_explain"]}</div>',unsafe_allow_html=True)

                if not st.session_state.gm_write_done:
                    st.markdown(f'<div style="font-size:13px;font-weight:700;color:#0F172A;margin:12px 0 6px;">Now write a correct {topic} example yourself:</div>',unsafe_allow_html=True)
                    with st.form("wf",clear_on_submit=True):
                        code_in=st.text_area("code",placeholder=f"Write a simple {topic} example…",height=90,label_visibility="collapsed")
                        submitted = st.form_submit_button("Submit My Code →",type="primary",use_container_width=True)
                    if submitted:
                            kws={"for loop":["for","range"],"while loop":["while"],"variables":["="],"if statement":["if"]}
                            needed=kws.get(topic.lower(),[])
                            cleaned=code_in.strip()
                            ok=all(k in cleaned for k in needed) if needed else len(cleaned)>5
                            if not cleaned:
                                ok=False
                                st.session_state.gm_write_feedback="No code submitted."
                            elif ok:
                                st.session_state.gm_write_feedback="Looks great!"
                            else:
                                st.session_state.gm_write_feedback=f"Incorrect / incomplete for {topic}."
                            st.session_state.gm_write_done=True
                            st.session_state.gm_write_ok=ok; st.rerun()
                else:
                    if st.session_state.get("gm_write_ok"):
                        st.success("✅ Looks great!")
                    else:
                        st.error(f"❌ {st.session_state.get('gm_write_feedback') or 'Incorrect submission.'}")
                        st.markdown('<div style="font-size:12px;color:#334155;margin-top:6px;margin-bottom:6px;">Correct reference code:</div>', unsafe_allow_html=True)
                        st.code("\n".join(kg.get("trace_code", [])) or "# No reference code available")

                    if st.button("🎉 Complete Lesson!",type="primary",use_container_width=True,key="fin"):
                        bug_ok=bool(st.session_state.gm_bug_correct)
                        write_ok=bool(st.session_state.get("gm_write_ok"))
                        if bug_ok and write_ok:
                            v="CORRECT"
                        elif bug_ok or write_ok:
                            v="PARTIAL"
                        else:
                            v="INCORRECT"
                        st.session_state.gm_verdicts.append(v); award(XP if v=="CORRECT" else 5)
                        st.session_state.gm_step=99; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# COMPLETE
# ══════════════════════════════════════════════════════════════════════════════
elif step==99:
    vs=st.session_state.gm_verdicts
    correct=sum(1 for v in vs if v=="CORRECT")

    # ── Save lesson to profile (runs once when completion screen first shows) ──
    if not st.session_state.get("gm_saved"):
        st.session_state.gm_saved = True
        try:
            from core.student_profile import record_lesson, update_concept, save_profile as _sp
            _verdicts_mapped = ["VERIFIED" if v=="CORRECT" else "CONTRADICTED" for v in vs]
            record_lesson(
                profile,
                topic=topic or "Unknown",
                steps_done=5,
                verdicts=_verdicts_mapped,
                complete=True,
            )
            # Update concept mastery for the topic
            for v in _verdicts_mapped:
                update_concept(profile, topic, v)
            st.session_state["student_profile"] = profile
        except Exception as _e:
            pass  # Never crash the completion screen over a save error
    st.markdown(f"""
<div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;
            padding:24px;max-width:680px;margin:20px auto;text-align:center;">
  <div style="font-size:44px;margin-bottom:10px;">🎉</div>
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.6rem;
    font-weight:800;color:#0F172A;margin-bottom:4px;">Lesson Complete!</div>
  <div style="font-size:13px;color:#64748B;margin-bottom:18px;">
    You finished all 5 steps on <strong>{(topic or "").title()}</strong>
  </div>
  <div style="display:flex;justify-content:center;gap:28px;margin-bottom:18px;">
    <div><div style="font-family:'Bricolage Grotesque',sans-serif;font-size:2rem;
      font-weight:800;color:#D97706;">+{st.session_state.gm_xp} XP</div>
      <div style="font-size:10px;color:#94A3B8;">earned</div></div>
    <div><div style="font-family:'Bricolage Grotesque',sans-serif;font-size:2rem;
      font-weight:800;color:#16A34A;">{correct}/5</div>
      <div style="font-size:10px;color:#94A3B8;">steps correct</div></div>
  </div>
  <div style="background:#F8FAFC;border-radius:10px;padding:12px;text-align:left;">
    {"".join(f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;"><span style="color:#16A34A;font-size:13px;">✓</span><span style="font-size:12px;font-weight:600;color:#0F172A;">{m[1]}</span><span style="font-size:11px;color:#94A3B8;">— {m[2]}</span></div>' for m in STEPS)}
  </div>
</div>""", unsafe_allow_html=True)
    cc1,cc2=st.columns(2)
    with cc1:
        if st.button("🔄 Study Another Topic",type="primary",use_container_width=True): reset(); st.rerun()
    with cc2:
        if st.button("💬 Ask in Student Chat",use_container_width=True): st.switch_page("pages/02_Student_Chat.py")
