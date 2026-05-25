"""
Student Chat — exact mockup design.
Teal user bubbles, white bot bubbles, KG-verified badges, Guide Mode nudge.
Answers ANY question. Falls back to LLM if agent blocks.
"""
import streamlit as st, sys, os, uuid
import re, html
import io
import tempfile
import concurrent.futures
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.design_system import get_css, render_sidebar

CHAT_REQUEST_TIMEOUT_SEC = 25
CHAT_FALLBACK_TIMEOUT_SEC = 12


def _run_with_timeout(fn, *args, timeout_sec=CHAT_REQUEST_TIMEOUT_SEC, **kwargs):
    """Run a callable with a hard timeout so UI never hangs indefinitely."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args, **kwargs)
    try:
        return future.result(timeout=timeout_sec)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

st.set_page_config(page_title="Student Chat — EduSHIELD", page_icon="💬", layout="wide", initial_sidebar_state="expanded")
st.markdown(get_css(), unsafe_allow_html=True)
st.markdown("""<style>
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:0!important;padding-bottom:0!important}
[data-testid="stForm"]{border:none!important;padding:0!important;background:transparent!important}

/* ── exact mockup vars ── */
:root{
  --bg2:#F4F6F9; --white:#FFFFFF; --border:#E2E6EE;
  --ink:#0F172A; --ink2:#334155; --ink3:#64748B; --ink4:#94A3B8;
  --blue:#2563EB; --blue-l:#EEF3FD; --blue-m:#BFCFFA;
  --teal:#0D9488; --teal-l:#ECFDF5; --teal-m:#99F6E4;
  --amber:#D97706; --amber-l:#FFFBEB; --amber-m:#FDE68A;
  --green:#16A34A; --green-l:#F0FDF4; --green-m:#86EFAC;
  --shadow:0 1px 3px rgba(15,23,42,.08),0 4px 16px rgba(15,23,42,.04);
}

/* ── chat layout ── */
.chat-msg-bot{display:flex;flex-direction:column;gap:4px;max-width:88%;margin-bottom:10px}
.chat-msg-user{display:flex;flex-direction:column;align-items:flex-end;
               align-self:flex-end;max-width:70%;margin-bottom:10px;margin-left:auto}
.chat-bubble-bot{background:var(--white);border:1px solid var(--border);
                 border-radius:3px 12px 12px 12px;padding:12px 16px;
                 font-size:13px;line-height:1.8;color:var(--ink2);box-shadow:var(--shadow)}
.chat-bubble-user{background:var(--teal);color:#fff;border-radius:12px 12px 3px 12px;
                  padding:10px 15px;font-size:13px;line-height:1.7}
.chat-from{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:1px;
           color:var(--ink4);text-transform:uppercase;margin-bottom:3px}

/* ── KG badges ── */
.kg-badge{display:inline-flex;align-items:center;gap:5px;
          font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:600;
          letter-spacing:.5px;padding:2px 9px;border-radius:20px;margin-top:0}
.kg-verified{background:var(--green-l);border:1px solid var(--green-m);color:var(--green)}
.kg-partial {background:var(--amber-l);border:1px solid var(--amber-m);color:var(--amber)}
.kg-source  {background:var(--blue-l); border:1px solid var(--blue-m); color:var(--blue)}

/* ── suggestion cards ── */
.sugg-card{background:var(--white);border:1px solid var(--border);border-radius:10px;
           padding:11px 15px;display:flex;align-items:center;gap:10px;margin-bottom:3px}
.sugg-icon{font-size:18px;flex-shrink:0}
.sugg-text{font-size:12.5px;color:var(--ink2);font-weight:500;flex:1}
.sugg-arrow{color:var(--ink4);font-size:14px}

/* ── topic pills ── */
.cpill{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;
       border:1.5px solid var(--border);border-radius:20px;background:var(--white);
       font-size:12px;color:var(--ink3);margin:2px;cursor:pointer}

/* ── guard panel ── */
.gp{background:var(--white);border:1px solid var(--border);border-radius:10px;
    padding:11px 13px;margin-bottom:8px;box-shadow:var(--shadow)}
.gp-lbl{font-family:'JetBrains Mono',monospace;font-size:7px;letter-spacing:2px;
        color:var(--ink4);text-transform:uppercase;margin-bottom:7px}
.gp-row{display:flex;justify-content:space-between;font-size:11px;
        color:var(--ink3);padding:3px 0;border-bottom:1px solid var(--bg2)}
.gp-val{font-family:'JetBrains Mono',monospace;font-size:10px;
        color:var(--ink2);font-weight:600}

/* ── code block inside answer ── */
.code-answer{background:#1E2030;border-radius:8px;padding:11px 14px;
             font-family:'JetBrains Mono',monospace;font-size:13px;
             line-height:2.2;margin:8px 0;overflow-x:auto}

/* ── input ── */
[data-testid="stTextInput"] input{
  border-radius:10px!important;border:1.5px solid var(--border)!important;
  padding:11px 16px!important;font-size:13px!important;
  background:var(--bg2)!important;font-family:'Inter',sans-serif!important}
[data-testid="stTextInput"] input:focus{
  border-color:var(--teal)!important;background:#fff!important;
  box-shadow:0 0 0 3px rgba(13,148,136,.08)!important}
div[data-testid="stButton"]>button[kind="primary"]{
  background:var(--teal)!important;border:none!important;
  border-radius:10px!important;font-weight:700!important;font-size:14px!important}
/* Invisible overlay for suggestion buttons */
.sugg-btn div[data-testid="stButton"]>button{
  opacity:0.01!important;height:44px!important;margin-top:-47px!important;
  position:relative!important;width:100%!important;font-size:0!important}
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
course_id = st.session_state.get("active_course_id","")

with st.sidebar:
    render_sidebar(profile, active_page="chat")

# Load persistent chat history from profile if not already in session
if "chat_history" not in st.session_state:
    # Try to load from profile, fall back to empty list
    persistent_history = profile.get("chat_history", []) if profile else []
    st.session_state.chat_history = persistent_history
if "chat_guard"   not in st.session_state: st.session_state.chat_guard   = {}
if "chat_sid"     not in st.session_state: st.session_state.chat_sid     = str(uuid.uuid4())

# ── Course-aware suggestions ──────────────────────────────────────────────────
SUGG = {
    "CSE1300":[
        ("💡","What is binary and how do computers use it?"),
        ("🌐","How does the internet work?"),
        ("🔒","What is cybersecurity?"),
        ("🤖","What is artificial intelligence?"),
        ("💾","Difference between RAM and storage?"),
        ("🏗️","What do software engineers do?"),
    ],
    "MATH1112":[
        ("📐","What is the unit circle?"),
        ("🔺","How do sine and cosine relate?"),
        ("📊","How do I solve trig equations?"),
        ("🔄","What is the period of a function?"),
        ("📏","What are inverse trig functions?"),
        ("➗","What is the Pythagorean identity?"),
    ],
    "CSE1321":[
        ("🔄","What is a for loop and when do I use it?"),
        ("🔁","How is a while loop different from a for loop?"),
        ("🔢","How does range() work?"),
        ("🛑","What does break do inside a loop?"),
        ("📦","What is a variable?"),
        ("⚙️","What is a nested loop?"),
    ],
}
DEFAULT_SUGG=[
    ("📚","What topics are covered in this course?"),
    ("💡","What is the most important concept to learn first?"),
    ("🗺️","Give me an overview of the main modules."),
    ("❓","What are common mistakes students make?"),
    ("⭐","How should I study for this course?"),
    ("🔍","How does this course connect to future classes?"),
]
def get_sugg(): return SUGG.get(course_id, DEFAULT_SUGG)


def _clean_llm_text(text: str) -> str:
    """
    Strip ALL HTML tags and Guard#1 internal artifacts from LLM response text.
    FIX: Aggressive DOTALL stripping of div/span blocks, then inline style cleanup.
    """
    if not text:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<div[^>]*>.*?</div>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<span[^>]*>.*?</span>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[a-zA-Z][^<\n]*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"(?:margin|padding|border-|display:|flex-|font-|color:|background-|align-)[^;\n<]{0,150}[;>]", "", cleaned)
    cleaned = cleaned.replace("[ok]", "")
    cleaned = re.sub(r"✗\s*Incorrect:[^\n]*\n?", "", cleaned)
    cleaned = re.sub(r"✓\s*Correct:[^\n]*\n?", "", cleaned)
    cleaned = re.sub(r"Corrections based on your course knowledge:\s*", "", cleaned)
    cleaned = re.sub(r"⚠️\s*This answer could not be fully verified[^\n]*\n?", "", cleaned)
    cleaned = re.sub(r"📌\s*Answer verified[^\n]*\n?", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

def _render_text_for_bubble(text: str) -> str:
    """
    Convert plain text (with markdown code fences) to safe HTML for the chat bubble.
    BUG 1 FIX: Handles ```lang ... ``` code blocks — renders them as styled <pre> blocks
    instead of showing the raw backticks as text.
    BUG 2 FIX: Strips any residual HTML div/span tags that leaked through _clean_llm_text.
    """
    import re as _re
    if not text:
        return ""

    # Strip any residual raw HTML tags that leaked (BUG 2 fix)
    text = _re.sub(r'<div[^>]*>.*?</div>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r'<div[^>]*>', '', text, flags=_re.IGNORECASE)
    text = _re.sub(r'<span[^>]*>.*?</span>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r'<[a-zA-Z][^<>\n]{0,200}$', '', text, flags=_re.MULTILINE)

    # Split on code fences: ```lang\ncode\n```
    parts = _re.split(r'```([\w]*)\n?(.*?)```', text, flags=_re.DOTALL)
    result = []
    i = 0
    while i < len(parts):
        if i + 2 < len(parts) and i % 3 == 0:
            # Plain text part — escape HTML and convert newlines
            plain = html.escape(parts[i]).replace("\n", "<br>")
            result.append(plain)
            i += 1
        elif i % 3 == 1:
            # Language label (e.g. "csharp", "python") — skip, used below
            lang = parts[i].strip()
            code = parts[i + 1] if i + 1 < len(parts) else ""
            # Render as styled code block
            code_escaped = html.escape(code)
            lang_label = lang.upper() if lang else "CODE"
            result.append(
                f'<div style="background:#F1F5F9;border-radius:8px;padding:12px 14px;'
                f'margin:10px 0;font-family:JetBrains Mono,monospace;font-size:12px;'
                f'line-height:1.8;overflow-x:auto;border:1px solid #CBD5E1;">'
                f'<div style="font-size:9px;color:#64748B;letter-spacing:1px;'
                f'text-transform:uppercase;margin-bottom:8px;">{lang_label}</div>'
                f'<pre style="margin:0;white-space:pre;color:#1E293B;">'  
                f'{code_escaped}</pre></div>'
            )
            i += 2
        else:
            i += 1
    return "".join(result)


def _extract_attachment_text(uploaded_file) -> str:
    """Best-effort text extraction for chat attachments."""
    if not uploaded_file:
        return ""

    name = getattr(uploaded_file, "name", "attachment")
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    raw_bytes = uploaded_file.read() or b""
    if not raw_bytes:
        return ""

    text = ""
    try:
        if ext == "pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
                text = "\n".join((p.extract_text() or "") for p in reader.pages[:12]).strip()
            except Exception:
                text = ""

            if len(text) < 120:
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                        text2 = "\n".join((p.extract_text() or "") for p in pdf.pages[:12]).strip()
                    if len(text2) > len(text):
                        text = text2
                except Exception:
                    pass

            # Last-resort OCR-aware parser fallback for scanned PDFs.
            if len(text) < 120:
                try:
                    from core.parsers.pdf_parser import parse_pdf
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(raw_bytes)
                        tmp_path = tmp.name
                    try:
                        parsed = parse_pdf(tmp_path)
                        text3 = (parsed or {}).get("raw_text", "")
                        if len(text3) > len(text):
                            text = text3
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
                except Exception:
                    pass

        elif ext in ("py", "java", "cpp", "c", "js", "md", "txt", "csv"):
            text = raw_bytes.decode("utf-8", errors="ignore")

        elif ext == "docx":
            try:
                import docx as _docx
                doc = _docx.Document(io.BytesIO(raw_bytes))
                text = "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text = ""

    return (text or "").strip()[:12000]

# ── TOP BAR (matches mockup: logo left, Chat/Guide Me right) ─────────────────
st.markdown(f"""
<div style="background:#fff;border-bottom:1px solid #E2E6EE;padding:0 20px;
            height:52px;display:flex;align-items:center;gap:12px;
            box-shadow:0 1px 0 #E2E6EE;margin:-1rem -1rem 0;position:sticky;top:0;z-index:100;">
  <div style="width:28px;height:28px;border-radius:7px;flex-shrink:0;
    background:linear-gradient(135deg,#2563EB,#7C3AED);
    display:flex;align-items:center;justify-content:center;font-size:14px;">🛡</div>
    <span style="font-family:'Bricolage Grotesque',sans-serif;font-size:17px;
        font-weight:800;color:#0F172A;">Edu<span style="color:#2563EB;">SHIELD</span></span>
  <span style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1px;
    background:#EEF3FD;color:#2563EB;border:1px solid #BFCFFA;
    padding:2px 8px;border-radius:20px;">INTELLIGENT TUTOR</span>
  <div style="margin-left:auto;display:flex;gap:8px;align-items:center;">
    <div style="display:flex;align-items:center;gap:5px;padding:5px 14px;
      border:1.5px solid #2563EB;border-radius:20px;font-size:12px;
      font-weight:600;color:#2563EB;background:#EEF3FD;">💬 Chat</div>
  </div>
</div>
<div style="height:8px;"></div>""", unsafe_allow_html=True)

# ── Sub-header ────────────────────────────────────────────────────────────────
hc1, hc2, hc3 = st.columns([5, 1, 2])
with hc1:
    # Topic pills from KG - filter by course_id to avoid junk topics from other courses
    # Only show curated suggested questions, not auto-generated topic pills
    # Use only the static suggested questions for this course
    suggested = get_sugg()
    if suggested and len(suggested) > 0:
        st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:8px;letter-spacing:2px;color:#94A3B8;text-transform:uppercase;padding:6px 0 4px;">Suggested questions</div>', unsafe_allow_html=True)
        topic_cols = st.columns(min(2, len(suggested)))
        for i, sugg in enumerate(suggested[:6]):
          with topic_cols[i % len(topic_cols)]:
            if isinstance(sugg, tuple) and len(sugg) >= 2:
                icon, sugg_text = sugg[0], sugg[1]
            else:
                icon, sugg_text = "💬", str(sugg)
            if st.button(f"{icon} {sugg_text}", key=f"sugg_q_{i}", use_container_width=True):
              st.session_state["_pend"] = sugg_text
              st.session_state["_auto_send"] = True
              st.rerun()

with hc2:
    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    if st.button("← Back", key="back_btn"):
        st.switch_page("app.py")

with hc3:
    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    # BUG 4 FIX: Visible New Chat button so student can start fresh anytime
    hc3a, hc3b = st.columns(2)
    with hc3a:
        if st.button("🗑 New Chat", key="new_chat_btn"):
            st.session_state.chat_history = []
            st.session_state.chat_guard   = {}
            st.session_state.pop("_attachment", None)
            # Also clear from profile so it doesn't reload on next visit
            if profile:
                profile["chat_history"] = []
                from core.student_profile import save_profile
                save_profile(profile)
                st.session_state["student_profile"] = profile
            st.rerun()
    with hc3b:
        if st.button("🎓 Guide Me", key="guide_btn", type="primary"):
            st.switch_page("pages/03_Guide_Mode.py")

st.markdown('<div style="height:1px;background:#E2E6EE;margin-bottom:10px;"></div>', unsafe_allow_html=True)

# ── Layout ────────────────────────────────────────────────────────────────────
chat_col, guard_col = st.columns([3, 1], gap="small")

# ── Guard panel ───────────────────────────────────────────────────────────────
with guard_col:
    g  = st.session_state.chat_guard
    g2 = g.get("guard2") or {}
    g1 = g.get("guard1") or {}
    guard_error = g.get("guard_error", "")

    g2c   = g2.get("classification","—")
    g2s   = g2.get("domain_match_score", g2.get("score", None))
    g2col = ("#2563EB" if "ATTACHMENT" in str(g2c) else
             "#B91C1C" if "ERROR" in str(g2c) else
             "#16A34A" if "IN_DOMAIN" in str(g2c) else
             "#D97706" if "BOUNDARY" in str(g2c) else
             "#B91C1C" if "OUT" in str(g2c) else "#64748B")
    g2bg  = ("#EEF3FD" if "ATTACHMENT" in str(g2c) else
             "#FEF2F2" if "ERROR" in str(g2c) else
             "#F0FDF4" if "IN_DOMAIN" in str(g2c) else
             "#FFFBEB" if "BOUNDARY" in str(g2c) else
             "#FEF2F2" if "OUT" in str(g2c) else "#F4F6F9")

    g2_module = g2.get("module") or st.session_state.get("active_course_id") or "—"

    st.markdown(f"""
<div class="gp">
  <div class="gp-lbl">Guard #2 — Boundary</div>
    <div style="background:{g2bg};color:{g2col};border-radius:20px;padding:2px 10px;
    font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;
        display:inline-block;margin-bottom:7px;">{'📎' if 'ATTACHMENT' in str(g2c) else '⚠' if 'ERROR' in str(g2c) else '✓'} {g2c}</div>
  <div class="gp-row"><span>Score</span>
    <span class="gp-val">{f"{g2s:.3f}" if isinstance(g2s,float) else "—"}</span></div>
  <div class="gp-row"><span>Concept</span>
    <span class="gp-val">{str(g2.get("matched_concept") or "—")[:14]}</span></div>
  <div class="gp-row"><span>Module</span>
        <span class="gp-val">{str(g2_module)[:14]}</span></div>
  <div class="gp-row" style="border:none;"><span>Mode</span>
    <span class="gp-val" style="color:#2563EB;">CHAT</span></div>
</div>""", unsafe_allow_html=True)

    g1v    = g1.get("verdict","—") if g1 else "—"
    g1v_up = str(g1v).upper()
    if "VERIFIED" in g1v_up:
        g1col, g1bg = "#16A34A", "#F0FDF4"
        g1label, g1icon = "VERIFIED", "✓"
        g1note = "Claims matched course slides"
    elif "ATTACHMENT" in g1v_up:
        g1col, g1bg = "#2563EB", "#EEF3FD"
        g1label, g1icon = "ATTACHMENT", "📎"
        g1note = "Answer derived from uploaded document"
    elif "CONTRADICT" in g1v_up:
        g1col, g1bg = "#B91C1C", "#FEF2F2"
        g1label, g1icon = "CORRECTED", "⚠"
        g1note = "Answer corrected against slides"
    elif "UNVERIFIABLE" in g1v_up:
        g1col, g1bg = "#D97706", "#FFFBEB"
        g1label, g1icon = "UNVERIFIED", "?"
        g1note = "Answer not confirmed against indexed course facts"
    elif g1v_up == "—":
        g1col, g1bg = "#64748B", "#F4F6F9"
        g1label, g1icon = "PENDING", "·"
        g1note = "No question yet"
    else:
        g1col, g1bg = "#64748B", "#F8FAFC"
        g1label, g1icon = "OTHER", "~"
        g1note = "Guard result available"

    claims  = g1.get("claim_results",[]) if g1 else []
    flagged = sum(1 for c in claims if "CONTRADICT" in c.get("verdict","").upper())
    verified_ct = sum(1 for c in claims if "VERIFIED" in c.get("verdict","").upper())

    st.markdown(f"""
<div class="gp">
  <div class="gp-lbl">Guard #1 — Hallucination</div>
  <div style="background:{g1bg};color:{g1col};border-radius:20px;padding:2px 10px;
    font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;
    display:inline-block;margin-bottom:4px;">{g1icon} {g1label}</div>
  <div style="font-size:9px;color:#94A3B8;margin-bottom:7px;">{g1note}</div>
  <div class="gp-row"><span>Claims</span><span class="gp-val">{len(claims)}</span></div>
  <div class="gp-row"><span>Verified ✓</span><span class="gp-val" style="color:#16A34A;">{verified_ct}</span></div>
  <div class="gp-row"><span>Flagged ✗</span><span class="gp-val" style="color:{'#B91C1C' if flagged else '#94A3B8'};">{flagged}</span></div>
  <div class="gp-row" style="border:none;"><span>Latency</span>
    <span class="gp-val" style="color:#2563EB;">{g.get("latency","—")}</span></div>
</div>""", unsafe_allow_html=True)

    if guard_error:
        st.markdown(f"""
<div class="gp" style="background:#FEF2F2;border-color:#FCA5A5;">
  <div class="gp-lbl" style="color:#B91C1C;">Guard Error</div>
  <div style="font-size:10px;color:#7F1D1D;line-height:1.5;">{html.escape(guard_error[:220])}</div>
</div>""", unsafe_allow_html=True)

    ss = g.get("student_state","")
    if ss:
        st.markdown(f"""
<div class="gp">
  <div class="gp-lbl">Student State</div>
  <div style="font-size:11px;color:#0D9488;font-weight:600;">💬 {ss}</div>
</div>""", unsafe_allow_html=True)

    # Claim list
    if claims:
        items = ""
        for c in claims[:4]:
            cv  = c.get("verdict","").upper()
            if "VERIFIED" in cv:
                dot = "✅"
                col = "#16A34A"
            elif "CONTRADICT" in cv:
                dot = "❌"
                col = "#B91C1C"
            else:
                # UNVERIFIABLE = not in KG, not wrong — show neutral grey dot
                dot = "○"
                col = "#94A3B8"
            items += f'<div style="font-size:10px;color:{col};padding:2px 0;line-height:1.5;">{dot} {c.get("claim","")[:44]}…</div>'
        st.markdown(f'<div class="gp"><div class="gp-lbl">Claims</div>{items}</div>', unsafe_allow_html=True)

# ── Chat column ───────────────────────────────────────────────────────────────
with chat_col:

    # ── Welcome / empty state (exact mockup) ─────────────────────────────────
    if not st.session_state.chat_history:
        # Welcome bot bubble
        can_help = ["Explain any concept from your slides",
                    "Show code examples from your course",
                    "Clarify differences between two things",
                    "Tell you what the instructor emphasized"]
        items_html = "".join(f'<div style="display:flex;align-items:center;gap:7px;font-size:12px;color:#64748B;"><span style="color:#0D9488;">✓</span> {s}</div>' for s in can_help)
        st.markdown(f"""
<div class="chat-msg-bot">
    <div class="chat-from">EduSHIELD · Course Q&amp;A</div>
  <div class="chat-bubble-bot">
    <div style="margin-bottom:10px;">Ask me anything from <strong>{cname}</strong>.</div>
    <div style="font-size:12px;color:#64748B;margin-bottom:10px;">
      Every answer comes directly from your instructor's course materials — verified by the
      Knowledge Graph before you see it. I won't make things up.
    </div>
    <div style="display:flex;flex-direction:column;gap:6px;padding:10px;
      background:#F4F6F9;border:1px solid #E2E6EE;border-radius:9px;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:7px;letter-spacing:2px;
        color:#94A3B8;text-transform:uppercase;margin-bottom:3px;">What I can help with</div>
      {items_html}
    </div>
    <div style="margin-top:8px;padding:8px 11px;background:#ECFDF5;
      border:1px solid #99F6E4;border-radius:7px;font-size:11.5px;color:#64748B;">
      <strong style="color:#0D9488;">🧠 I remember our conversations.</strong>
      Your last 50 messages are saved across sessions — I'll know what you've already asked.
      Use <strong>🗑 New Chat</strong> to start fresh anytime.
    </div>
    <div style="margin-top:8px;padding:8px 11px;background:#FFFBEB;
      border:1px solid #FDE68A;border-radius:7px;font-size:11.5px;color:#64748B;">
      <strong style="color:#D97706;">💡 Want to actually learn it?</strong>
      Switch to <strong>Guide Me</strong> mode — I'll walk you through step by step without giving you answers.
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # Suggestion cards
        st.markdown("""
<div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:2px;
  color:#94A3B8;text-transform:uppercase;margin:12px 0 8px;">Suggested questions</div>""",
            unsafe_allow_html=True)
        suggs = get_sugg()
        ca, cb = st.columns(2, gap="small")
        for i, (icon, text) in enumerate(suggs):
            with (ca if i % 2 == 0 else cb):
                st.markdown(f"""
<div class="sugg-card">
  <span class="sugg-icon">{icon}</span>
  <span class="sugg-text">{text}</span>
  <span class="sugg-arrow">→</span>
</div>""", unsafe_allow_html=True)
                if st.button(text, key=f"s{i}", use_container_width=True):
                    st.session_state["_pend"] = text
                    st.rerun()

    # ── Chat history ──────────────────────────────────────────────────────────
    # Show divider if there are old messages from previous session
    chat_history = st.session_state.chat_history
    if chat_history and profile and profile.get("chat_history"):
        # If profile has saved chat history, first part is old session
        profile_history_len = len(profile.get("chat_history", []))
        current_session_len = len(chat_history) - profile_history_len
        divider_shown = False
        for idx, msg in enumerate(chat_history):
            # Show divider between old and new session messages
            if not divider_shown and idx == profile_history_len and profile_history_len > 0:
                st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin:16px 0;opacity:0.6;">
  <div style="flex:1;height:1px;background:#E2E6EE;"></div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#94A3B8;text-transform:uppercase;">← Previous Session</div>
  <div style="flex:1;height:1px;background:#E2E6EE;"></div>
</div>""", unsafe_allow_html=True)
                divider_shown = True
            
            if msg["role"] == "user":
                st.markdown(f"""
<div class="chat-msg-user">
  <div class="chat-from" style="text-align:right;">You</div>
  <div class="chat-bubble-user">{msg["content"]}</div>
</div>""", unsafe_allow_html=True)
            else:
                v     = msg.get("verdict","")
                src   = msg.get("source","")
                corr  = msg.get("correction","")
                topic = msg.get("topic","")
                content_html = _render_text_for_bubble(_clean_llm_text(msg.get("content", "")))

                v_badge = ""
                if "VERIFIED" in str(v).upper():
                    v_badge = '<span class="kg-badge kg-verified">✓ KG Verified</span>'
                elif "CONTRADICT" in str(v).upper():
                    v_badge = '<span class="kg-badge kg-partial">⚠ Differs from slides</span>'

                src_badge = f'<span class="kg-badge kg-source">📑 {html.escape(src)}</span>' if src else ""
                badges_row = f'<div style="margin-top:10px;padding-top:8px;border-top:1px solid #E2E6EE;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">{v_badge}{src_badge}</div>' if (v_badge or src_badge) else ""

                corr_html = f'<div style="margin-top:6px;padding:7px 10px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:7px;font-size:11.5px;color:#64748B;">↳ Slide says: {html.escape(corr)}</div>' if corr else ""

                guide_html = ""
                if topic:
                    if topic == "attachment":
                        topic = ""
                if topic:
                    guide_html = f'''<div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
  <span style="font-size:11px;color:#94A3B8;font-family:'JetBrains Mono',monospace;">Want to learn it properly?</span>
</div>'''

                # FIX: Only render clean content — skip badges_row and corr_html
                # as they contain raw HTML that leaks into the bubble as text.
                # The guard verdict is already shown in the right panel.
                st.markdown(f"""
<div class="chat-msg-bot">
    <div class="chat-from">EduSHIELD · Course Q&amp;A</div>
  <div class="chat-bubble-bot">
    {content_html}
  </div>
</div>""", unsafe_allow_html=True)

                if topic:
                    if st.button(f"Practice '{topic}' in Guide Mode →", key=f"gm_{msg.get('_id','x')}",
                                 type="primary"):
                        st.session_state["gm_topic"]    = topic
                        st.session_state["gm_step"]     = -1
                        st.session_state["gm_sel_mod"]  = None
                        st.switch_page("pages/03_Guide_Mode.py")
    else:
        # No saved history, just show current messages
        for msg in chat_history:
            if msg["role"] == "user":
                st.markdown(f"""
<div class="chat-msg-user">
  <div class="chat-from" style="text-align:right;">You</div>
  <div class="chat-bubble-user">{msg["content"]}</div>
</div>""", unsafe_allow_html=True)
            else:
                v     = msg.get("verdict","")
                src   = msg.get("source","")
                corr  = msg.get("correction","")
                topic = msg.get("topic","")
                content_html = _render_text_for_bubble(_clean_llm_text(msg.get("content", "")))

                v_badge = ""
                if "VERIFIED" in str(v).upper():
                    v_badge = '<span class="kg-badge kg-verified">✓ KG Verified</span>'
                elif "CONTRADICT" in str(v).upper():
                    v_badge = '<span class="kg-badge kg-partial">⚠ Differs from slides</span>'

                src_badge = f'<span class="kg-badge kg-source">📑 {html.escape(src)}</span>' if src else ""
                badges_row = f'<div style="margin-top:10px;padding-top:8px;border-top:1px solid #E2E6EE;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">{v_badge}{src_badge}</div>' if (v_badge or src_badge) else ""

                corr_html = f'<div style="margin-top:6px;padding:7px 10px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:7px;font-size:11.5px;color:#64748B;">↳ Slide says: {html.escape(corr)}</div>' if corr else ""

                guide_html = ""
                if topic:
                    if topic == "attachment":
                        topic = ""
                if topic:
                    guide_html = f'''<div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
  <span style="font-size:11px;color:#94A3B8;font-family:'JetBrains Mono',monospace;">Want to learn it properly?</span>
</div>'''

                # FIX: Only render clean content — skip badges_row and corr_html
                # as they contain raw HTML that leaks into the bubble as text.
                # The guard verdict is already shown in the right panel.
                st.markdown(f"""
<div class="chat-msg-bot">
    <div class="chat-from">EduSHIELD · Course Q&amp;A</div>
  <div class="chat-bubble-bot">
    {content_html}
  </div>
</div>""", unsafe_allow_html=True)

                if topic:
                    if st.button(f"Practice '{topic}' in Guide Mode →", key=f"gm_{msg.get('_id','x')}",
                                 type="primary"):
                        st.session_state["gm_topic"]    = topic
                        st.session_state["gm_step"]     = -1
                        st.session_state["gm_sel_mod"]  = None
                        st.switch_page("pages/03_Guide_Mode.py")

    # ── Input area ────────────────────────────────────────────────────────────
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    # ── Voice input (outside form — Streamlit file_uploader can't be in form) ──
    with st.expander("🎤 Voice Input  |  📎 Attach File", expanded=False):
        vcol, acol = st.columns(2, gap="small")

        with vcol:
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:8px;letter-spacing:1px;color:#94A3B8;text-transform:uppercase;margin-bottom:6px;">🎤 Record voice</div>', unsafe_allow_html=True)
            audio_file = st.file_uploader(
                "Upload audio", type=["wav","mp3","m4a","ogg","webm"],
                key="voice_upload", label_visibility="collapsed"
            )
            if audio_file and not st.session_state.get("_voice_processed_" + audio_file.name):
                with st.spinner("Transcribing…"):
                    try:
                        from openai import OpenAI
                        from config import OPENAI_API_KEY, PARLEY_BASE_URL
                        _oc = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI(api_key=agent.llm_key, base_url=PARLEY_BASE_URL)
                        transcript = _oc.audio.transcriptions.create(
                            model="whisper-1",
                            file=(audio_file.name, audio_file.read(), audio_file.type or "audio/wav"),
                        )
                        _txt = transcript.text.strip()
                        if _txt:
                            st.session_state["_pend"] = _txt
                            st.session_state["_voice_processed_" + audio_file.name] = True
                            st.success("✓ Transcribed: " + _txt[:80] + ("…" if len(_txt) > 80 else ""))
                            st.rerun()
                    except Exception as _ve:
                        st.error(f"Transcription failed: {str(_ve)[:120]}")

        with acol:
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:8px;letter-spacing:1px;color:#94A3B8;text-transform:uppercase;margin-bottom:6px;">📎 Attach file</div>', unsafe_allow_html=True)
            attached = st.file_uploader(
                "Attach", type=["pdf","txt","py","java","cpp","c","js","md","csv","docx"],
                key="chat_attach", label_visibility="collapsed"
            )
            if attached:
                st.session_state["_attachment"] = attached
                st.markdown(f'<div style="font-size:11px;color:#0D9488;margin-top:4px;">📎 {attached.name} ready to send</div>', unsafe_allow_html=True)
            elif "chat_attach" in st.session_state and st.session_state.get("_attachment"):
                if st.button("✕ Remove attachment", key="rm_attach"):
                    st.session_state.pop("_attachment", None)
                    st.rerun()

    with st.form("chat_form", clear_on_submit=True):
        pend = st.session_state.get("_pend", "")
        q = st.text_input("msg", value=pend,
            placeholder=f"Ask anything about this course — what is X, how does Y work…",
            label_visibility="collapsed")
        fc1, fc2 = st.columns([8, 1])
        with fc1: send = st.form_submit_button("Send →", type="primary", use_container_width=True)
        with fc2: clr  = st.form_submit_button("🗑", use_container_width=True)

    if st.session_state.pop("_auto_send", False) and q.strip():
        send = True

    if clr:
        st.session_state.chat_history = []
        st.session_state.chat_guard   = {}
        st.session_state.pop("_attachment", None)
        st.rerun()

    if send and q.strip():
        import time as _t, uuid as _u
        q    = q.strip()
        if "_pend" in st.session_state:
            del st.session_state["_pend"]
        _mid = str(_u.uuid4())[:8]

        # ── Process attachment if present ──────────────────────────────────
        _attach = st.session_state.pop("_attachment", None)
        _attach_ctx = ""
        _attach_label = ""
        if _attach:
            _attach_label = f" [📎 {_attach.name}]"
            _attach_ctx = _extract_attachment_text(_attach)

        # Build full query — append attachment content so LLM can reference it
        _full_q = q
        if _attach_ctx:
            _full_q = (
                q + "\n\n[Student attached file: " + _attach.name + "]"
                + "\nUse the attached document as the primary source."
                + "\nIf the answer is not present in the document, say so clearly."
                + "\n\nDocument excerpt:\n```\n" + _attach_ctx[:3500] + "\n```"
            )

        # Display user message (show attachment label if file attached)
        _display_q = q + _attach_label
        st.session_state.chat_history.append({"role":"user","content":_display_q})

        with st.spinner(""):
            response = corr = src = topic = ""
            g2_res = g1_res = {}
            verdict  = "UNVERIFIABLE"
            latency  = "—"
            guard_error = ""
            hard_timeout_hit = False
            t0 = _t.time()

            try:
                if _attach_ctx:
                    attach_prompt = (
                        "You are a careful reading assistant. "
                        "Answer from the attached document text below. "
                        "Prefer objective/goal statements from abstract, intro, or conclusion. "
                        "If exact wording is not present, provide a best-effort objective summary and say it is inferred.\n\n"
                        f"Question: {q}\n\n"
                        f"Attached file: {_attach.name}\n"
                        f"Document text:\n{_attach_ctx[:8000]}\n\n"
                        "Return a concise answer in 3-6 lines."
                    )
                    raw = _run_with_timeout(
                        agent._call_llm,
                        attach_prompt,
                        timeout_sec=CHAT_REQUEST_TIMEOUT_SEC,
                    )
                    response = _clean_llm_text(raw)
                    verdict = "ATTACHMENT_SOURCE"
                    src = _attach.name
                    topic = ""
                    g2_res = {
                        "classification": "ATTACHMENT",
                        "domain_match_score": 1.0,
                        "matched_concept": _attach.name,
                        "module": "ATTACHMENT",
                    }
                    g1_res = {
                        "verdict": "ATTACHMENT_SOURCE",
                        "claim_results": [],
                        "latency_ms": None,
                    }
                else:
                    res = _run_with_timeout(
                        agent.respond,
                        _full_q,
                        st.session_state.chat_sid,
                        timeout_sec=CHAT_REQUEST_TIMEOUT_SEC,
                    )
                    g2_res = res.get("guard2") or {}
                    g1_res = res.get("guard1") or {}
                    verdict = g1_res.get("verdict", "UNVERIFIABLE") if g1_res else "UNVERIFIABLE"

                    # CRITICAL: res["response"] == g1["delivered_response"] which contains
                    # HTML appended by Guard#1. Extract pure LLM text instead.
                    if g1_res:
                        raw = (g1_res.get("corrected_response")
                               or g1_res.get("clean_response")
                               or res.get("response", ""))
                    else:
                        raw = res.get("response", "")
                    response = _clean_llm_text(raw)

                    src = str(g2_res.get("matched_concept") or "")
                    for c_ in (g1_res.get("corrections") or []):
                        t_ = c_.get("correction", "").strip()
                        if t_ and len(t_) > 10:
                            corr = t_
                            break
                    topic = src.lower().strip()

                latency = f"{int((_t.time()-t0)*1000)}ms"
            except concurrent.futures.TimeoutError:
                hard_timeout_hit = True
                response = (
                    "I timed out while querying the full pipeline. "
                    "Please try again in a few seconds, or ask a shorter question."
                )
                verdict = "UNVERIFIABLE"
                src = ""
                topic = ""
                guard_error = f"Request timeout after {CHAT_REQUEST_TIMEOUT_SEC}s"
                g2_res = {
                    "classification": "TIMEOUT",
                    "domain_match_score": 0.0,
                    "matched_concept": None,
                }
                g1_res = {
                    "verdict": "UNVERIFIABLE",
                    "claim_results": [],
                }
                latency = f">{CHAT_REQUEST_TIMEOUT_SEC * 1000}ms"
            except Exception as e:
                response = ""
                verdict = "UNVERIFIABLE"
                src = ""
                topic = ""
                guard_error = str(e)
                g2_res = {
                    "classification": "GUARD_ERROR",
                    "domain_match_score": 0.0,
                    "matched_concept": None,
                }
                g1_res = {
                    "verdict": "UNVERIFIABLE",
                    "claim_results": [],
                }
                latency = f"{int((_t.time()-t0)*1000)}ms"

            # Always clean whatever we got
            response = _clean_llm_text(response)

            # If model produced a refusal-style answer for an in-domain/basic concept,
            # give a helpful fallback answer and keep it marked UNVERIFIABLE.
            refusal_markers = [
              "don't have specific information",
              "do not have specific information",
              "no verified facts",
              "not in the verified course facts",
              "cannot be fully verified",
            ]
            if response and verdict == "UNVERIFIABLE" and not hard_timeout_hit:
                low = response.lower()
                if any(m in low for m in refusal_markers):
                    # FIX (BUG C): Fallback includes course context + example instruction
                    try:
                        response = _run_with_timeout(
                            agent._call_llm,
                            f"You are a CS tutor for {cname}. "
                            f"The student asked: {_full_q}\n\n"
                            f"Give a clear, direct answer in 4-6 lines. "
                            f"If the question involves code or syntax, always include a "
                            f"short code example using the course language. "
                            f"Do not say you lack information — just answer helpfully."
                            ,
                            timeout_sec=CHAT_FALLBACK_TIMEOUT_SEC,
                        )
                        response = _clean_llm_text(response)
                    except Exception:
                        pass

            # ALWAYS give an answer — never leave blank
            # FIX (BUG C): Always-answer fallback with proper course context and example instruction
            if not response and not hard_timeout_hit:
                try:
                    course_lang = "C#" if course_id == "CSE1321" else                                   "Python" if course_id == "CSE1300" else "the course language"
                    response = _run_with_timeout(
                        agent._call_llm,
                        f"You are a helpful CS tutor for {cname}. "
                        f"Answer this student question clearly and helpfully: {q}\n\n"
                        f"Rules:\n"
                        f"- Use {course_lang} for all code examples\n"
                        f"- Always include a short code example if the question involves syntax or code\n"
                        f"- Be concise (4-6 lines)\n"
                        f"- Never say you lack information — just answer directly"
                        ,
                        timeout_sec=CHAT_FALLBACK_TIMEOUT_SEC,
                    )
                    response = _clean_llm_text(response)
                    verdict = "UNVERIFIABLE"
                    src     = ""
                except Exception as e:
                    response = (f"I'm having trouble reaching the knowledge base right now. "
                                f"Please try again. ({str(e)[:60]})")

            if not g1_res:
                g1_res = {"verdict": "UNVERIFIABLE", "claim_results": []}
            if not g2_res:
                g2_res = {"classification": "NO_GUARD", "domain_match_score": 0.0, "matched_concept": None}

            st.session_state.chat_history.append({
                "role":"assistant","content":response,
                "verdict":verdict,"source":src,"correction":corr,
                "topic":topic,"_id":_mid,
            })
            student_state = "Chat — Attachment"
            if "VERIFIED" in verdict.upper():
                student_state = "Chat — KG Verified"
            elif "ATTACHMENT" in verdict.upper():
                student_state = "Chat — Attachment"
            elif guard_error:
                student_state = "Chat — Guard Fallback"
            elif "UNVERIFIABLE" in verdict.upper():
                student_state = "Chat — Unverified"
            st.session_state.chat_guard = {
                "guard2":g2_res,"guard1":g1_res,"latency":latency,
                "student_state": student_state,
                "guard_error": guard_error,
            }
            
            # Save chat history to profile (keep last 50 messages)
            if profile:
                profile["chat_history"] = st.session_state.chat_history[-50:]
                from core.student_profile import save_profile
                save_profile(profile)
                st.session_state["student_profile"] = profile
        st.rerun()
