"""
EduSHIELD Design System — matches the HTML mockup exactly.
Light theme: white cards, clean borders, blue accent.
"""

FONTS = """
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300;400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
"""

CSS = """
<style>
[data-testid="stAppViewContainer"] { background: #FAFAFA !important; }
[data-testid="stSidebar"] {
  background: #FFFFFF !important;
  border-right: 1px solid #E2E6EE !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarNavItems"] { display: none !important; }
[data-testid="stSidebarNav"] ul { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
.stDeployButton, #MainMenu, footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
:root {
  --bg:#FAFAFA; --bg2:#F4F6F9; --bg3:#EEF1F6; --white:#FFFFFF;
  --border:#E2E6EE; --border2:#CDD3DF;
  --ink:#0F172A; --ink2:#334155; --ink3:#64748B; --ink4:#94A3B8;
  --blue:#2563EB; --blue-l:#EEF3FD; --blue-m:#BFCFFA;
  --teal:#0D9488; --teal-l:#ECFDF5; --teal-m:#99F6E4;
  --violet:#7C3AED; --violet-l:#F3EFFE; --violet-m:#C4B5FD;
  --amber:#D97706; --amber-l:#FFFBEB; --amber-m:#FDE68A;
  --rose:#E11D48; --rose-l:#FFF1F2; --green:#16A34A;
  --green-l:#F0FDF4; --green-m:#86EFAC;
  --shadow:0 1px 3px rgba(15,23,42,0.08),0 4px 16px rgba(15,23,42,0.04);
  --shadow2:0 2px 8px rgba(15,23,42,0.10),0 8px 32px rgba(15,23,42,0.06);
  --mono:'JetBrains Mono',monospace;
  --sans:'Bricolage Grotesque',sans-serif;
  --body:'Inter',sans-serif;
}
html,body,[class*="css"] { font-family:var(--body) !important; color:var(--ink) !important; background:#FAFAFA !important; }

/* Hide Streamlit auto-generated page nav */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarNavItems"] { display: none !important; }
[data-testid="stSidebarNavSeparator"] { display: none !important; }
section[data-testid="stSidebar"] ul { display: none !important; }

/* Sidebar */
.sb-logo { padding:14px 16px 10px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:8px; }
.sb-logo-mark { width:28px; height:28px; border-radius:8px; background:linear-gradient(135deg,#2563EB 0%,#7C3AED 100%); display:flex; align-items:center; justify-content:center; font-size:13px; flex-shrink:0; }
.sb-logo-text { font-family:var(--sans); font-size:16px; font-weight:800; color:var(--ink); letter-spacing:-0.3px; }
.sb-logo-text span { color:var(--blue); }
.sb-logo-tag { font-family:var(--mono); font-size:8px; letter-spacing:1px; background:var(--blue-l); color:var(--blue); border:1px solid var(--blue-m); padding:1px 7px; border-radius:20px; margin-left:auto; }
.sb-section { padding:10px 16px 5px; font-family:var(--mono); font-size:7px; letter-spacing:2px; color:var(--ink4); text-transform:uppercase; }
.sb-divider { height:1px; background:var(--border); }
.sb-profile { padding:10px 14px; display:flex; align-items:center; gap:10px; border-top:1px solid var(--border); }
.sb-avatar { width:32px; height:32px; border-radius:10px; flex-shrink:0; background:linear-gradient(135deg,var(--blue) 0%,var(--violet) 100%); display:flex; align-items:center; justify-content:center; font-family:var(--sans); font-size:14px; font-weight:800; color:white; }
.sb-pname { font-family:var(--sans); font-size:12px; font-weight:700; color:var(--ink); }
.sb-pmeta { font-family:var(--mono); font-size:8px; color:var(--ink4); }
.sb-pxp { margin-left:auto; font-family:var(--mono); font-size:9px; background:var(--amber-l); color:var(--amber); border:1px solid var(--amber-m); padding:2px 7px; border-radius:20px; }
.sb-course { margin:8px; padding:10px 12px; background:var(--bg2); border:1px solid var(--border); border-radius:10px; }
.sb-course-name { font-family:var(--sans); font-size:12px; font-weight:700; color:var(--ink); }
.sb-course-id { font-family:var(--mono); font-size:8px; color:var(--ink4); letter-spacing:1px; }
.chip { font-family:var(--mono); font-size:8px; padding:2px 7px; border-radius:20px; background:var(--white); border:1px solid var(--border2); color:var(--ink3); }
.chip-blue { background:var(--blue-l); border-color:var(--blue-m); color:var(--blue); }
.chip-green { background:var(--green-l); border-color:var(--green-m); color:var(--green); }
.chip-rose { background:var(--rose-l); border-color:#FCA5A5; color:var(--rose); }
.chip-amber { background:var(--amber-l); border-color:var(--amber-m); color:var(--amber); }

/* Top bar */
.top-bar { background:var(--white); border-bottom:1px solid var(--border); padding:9px 18px; display:flex; align-items:center; gap:10px; }
.top-title { font-family:var(--sans); font-size:15px; font-weight:800; color:var(--ink); }
.top-tag { font-family:var(--mono); font-size:8px; padding:2px 9px; border-radius:20px; border:1px solid; letter-spacing:0.5px; font-weight:600; }
.tag-guide { background:var(--teal-l); border-color:var(--teal-m); color:var(--teal); }
.tag-chat  { background:var(--blue-l); border-color:var(--blue-m); color:var(--blue); }
.tag-prof  { background:var(--violet-l); border-color:var(--violet-m); color:var(--violet); }
.tag-ok    { background:var(--green-l); border-color:var(--green-m); color:var(--green); }
.tag-wrong { background:var(--rose-l); border-color:#FCA5A5; color:var(--rose); }
.tag-build { background:var(--violet-l); border-color:var(--violet-m); color:var(--violet); }
.tag-lost  { background:var(--amber-l); border-color:var(--amber-m); color:var(--amber); }
.tag-slide { background:var(--blue-l); border-color:var(--blue-m); color:var(--blue); }

/* Topic bar */
.topic-bar { padding:8px 16px; border-bottom:1px solid var(--border); background:var(--white); display:flex; align-items:center; gap:10px; }
.topic-bar-label { font-family:var(--mono); font-size:7px; letter-spacing:1.5px; color:var(--ink4); text-transform:uppercase; white-space:nowrap; flex-shrink:0; }
.topics-scroll { display:flex; gap:5px; overflow-x:auto; }
.topics-scroll::-webkit-scrollbar { display:none; }
.topic-pill { padding:4px 12px; border:1px solid var(--border); border-radius:20px; background:var(--white); font-size:11px; font-weight:600; color:var(--ink3); white-space:nowrap; }
.topic-pill.active { border-color:var(--blue); color:var(--blue); background:var(--blue-l); }

/* Step progress */
.step-track { display:flex; align-items:center; gap:0; padding:8px 16px; background:var(--white); border-bottom:1px solid var(--border); }
.step-dot { width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-family:var(--mono); font-size:9px; font-weight:700; border:2px solid var(--border); background:var(--white); color:var(--ink4); flex-shrink:0; }
.step-dot.done { background:var(--green); border-color:var(--green); color:white; }
.step-dot.curr { background:var(--blue); border-color:var(--blue); color:white; }
.step-seg { flex:1; height:2px; background:var(--border); }
.step-seg.done { background:var(--green); }
.step-seg.curr { background:var(--blue); }
.step-label { font-family:var(--mono); font-size:9px; color:var(--blue); font-weight:600; letter-spacing:0.5px; margin-left:10px; white-space:nowrap; }

/* Chat */
.chat-wrap { padding:16px 18px; display:flex; flex-direction:column; gap:10px; }
.msg-row { display:flex; gap:10px; max-width:88%; }
.msg-row.user-row { margin-left:auto; flex-direction:row-reverse; }
.avatar { width:28px; height:28px; border-radius:8px; flex-shrink:0; display:flex; align-items:center; justify-content:center; font-family:var(--sans); font-size:12px; font-weight:800; }
.avatar-bot { background:linear-gradient(135deg,#2563EB,#7C3AED); color:white; }
.avatar-user { background:var(--bg3); color:var(--ink3); }
.msg-col { display:flex; flex-direction:column; gap:3px; min-width:0; }
.msg-from { font-family:var(--mono); font-size:7px; letter-spacing:1px; color:var(--ink4); text-transform:uppercase; }
.msg-tag { display:inline-flex; align-items:center; gap:4px; font-family:var(--mono); font-size:8px; padding:2px 8px; border-radius:20px; font-weight:600; letter-spacing:0.5px; margin-bottom:2px; width:fit-content; }
.bubble { padding:10px 14px; border-radius:12px; font-size:13px; line-height:1.75; font-family:var(--body); word-break:break-word; }
.bubble-bot { background:var(--white); border:1px solid var(--border); border-radius:3px 12px 12px 12px; box-shadow:var(--shadow); color:var(--ink2); }
.bubble-user { background:var(--blue); color:white; border-radius:12px 12px 3px 12px; }
.bubble-ok    { background:var(--green-l);  border:1px solid var(--green-m);  border-radius:3px 12px 12px 12px; color:var(--ink2); }
.bubble-wrong { background:var(--rose-l);   border:1px solid #FCA5A5;         border-radius:3px 12px 12px 12px; color:var(--ink2); }
.bubble-lost  { background:var(--amber-l);  border:1px solid var(--amber-m);  border-radius:3px 12px 12px 12px; color:var(--ink2); }
.bubble-build { background:var(--violet-l); border:1px solid var(--violet-m); border-radius:3px 12px 12px 12px; color:var(--ink2); }
.step-pill { font-family:var(--mono); font-size:7px; font-weight:600; background:var(--blue-l); color:var(--blue); border:1px solid var(--blue-m); padding:1px 7px; border-radius:20px; letter-spacing:0.5px; display:inline-block; margin-bottom:3px; }
.correction-note { font-size:11px; color:var(--rose); margin-top:4px; }
.step-dots { display:flex; align-items:center; gap:3px; margin-top:5px; }
.step-dots-label { font-family:var(--mono); font-size:7px; color:var(--ink4); margin-right:2px; letter-spacing:1px; }
.dot { width:20px; height:3px; border-radius:2px; }
.dot-done { background:var(--green); }
.dot-curr { background:var(--blue); }
.dot-todo { background:var(--border2); }

/* Right panel */
.rp-hdr { padding:9px 14px; border-bottom:1px solid var(--border); font-family:var(--mono); font-size:8px; letter-spacing:2px; color:var(--ink4); text-transform:uppercase; background:var(--bg2); }
.rp-sec { padding:10px 14px; border-bottom:1px solid var(--border); }
.rp-label { font-family:var(--mono); font-size:7px; letter-spacing:2px; color:var(--ink4); text-transform:uppercase; margin-bottom:6px; }
.verdict-badge { display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:20px; font-family:var(--mono); font-size:9px; font-weight:700; }
.verdict-ok   { background:var(--green-l); border:1px solid var(--green-m); color:var(--green); }
.verdict-warn { background:var(--amber-l); border:1px solid var(--amber-m); color:var(--amber); }
.verdict-bad  { background:var(--rose-l);  border:1px solid #FCA5A5;        color:var(--rose); }
.verdict-gray { background:var(--bg2); border:1px solid var(--border); color:var(--ink4); }
.stat-row { display:flex; justify-content:space-between; align-items:center; padding:2px 0; font-size:11px; color:var(--ink3); }
.stat-val { font-family:var(--mono); font-size:10px; color:var(--ink); font-weight:600; }
.claim-row { display:flex; align-items:center; gap:6px; margin-bottom:4px; font-size:11px; color:var(--ink3); }
.claim-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.claim-dot-ok   { background:var(--green); }
.claim-dot-bad  { background:var(--rose); }
.claim-dot-warn { background:var(--amber); }
.claim-dot-gray { background:var(--ink4); }
.state-badge { display:flex; align-items:center; gap:6px; font-family:var(--mono); font-size:9px; font-weight:700; padding:6px 10px; border-radius:8px; margin-top:6px; }
.state-guide  { background:var(--teal-l);   border:1px solid var(--teal-m);   color:var(--teal); }
.state-ok     { background:var(--green-l);  border:1px solid var(--green-m);  color:var(--green); }
.state-lost   { background:var(--amber-l);  border:1px solid var(--amber-m);  color:var(--amber); }
.state-build  { background:var(--violet-l); border:1px solid var(--violet-m); color:var(--violet); }

/* Cards */
.dg-card { background:var(--white); border:1px solid var(--border); border-radius:12px; padding:18px 20px; box-shadow:var(--shadow); margin-bottom:12px; }
.dg-card-title { font-family:var(--sans); font-size:13px; font-weight:800; color:var(--ink); margin-bottom:12px; }

/* Course cards */
.course-card { background:var(--white); border:1.5px solid var(--border); border-radius:12px; padding:16px 18px; box-shadow:var(--shadow); transition:all .2s; }
.course-card.active { border-color:var(--blue); background:var(--blue-l); }
.course-name { font-family:var(--sans); font-size:14px; font-weight:800; color:var(--ink); margin:4px 0; }
.course-tag { font-family:var(--mono); font-size:8px; letter-spacing:1px; text-transform:uppercase; }

/* Mastery chips */
.mastery-chip { display:inline-flex; align-items:center; gap:5px; padding:5px 12px; border-radius:8px; border:1px solid; font-size:12px; font-weight:500; margin:3px; }
.mc-confident { background:var(--green-l); border-color:var(--green-m); color:var(--green); }
.mc-learning  { background:var(--blue-l);  border-color:var(--blue-m);  color:var(--blue); }
.mc-struggle  { background:var(--rose-l);  border-color:#FCA5A5;        color:var(--rose); }
.mc-seen      { background:var(--bg2);     border-color:var(--border);  color:var(--ink3); }

/* Lesson cards */
.lesson-card { background:var(--white); border:1px solid var(--border); border-radius:10px; padding:12px 14px; margin-bottom:8px; display:flex; align-items:center; gap:12px; box-shadow:var(--shadow); }
.lesson-topic { font-family:var(--sans); font-size:13px; font-weight:700; color:var(--ink); }
.lesson-meta { font-family:var(--mono); font-size:9px; color:var(--ink4); margin-top:2px; }
.lesson-score { margin-left:auto; font-family:var(--mono); font-size:13px; font-weight:700; padding:4px 12px; border-radius:8px; }
.score-green { background:var(--green-l); color:var(--green); border:1px solid var(--green-m); }
.score-amber { background:var(--amber-l); color:var(--amber); border:1px solid var(--amber-m); }
.score-rose  { background:var(--rose-l);  color:var(--rose);  border:1px solid #FCA5A5; }

/* XP bar */
.xp-bar-wrap { margin:6px 0; }
.xp-bar-top { display:flex; justify-content:space-between; font-family:var(--mono); font-size:8px; color:var(--ink4); margin-bottom:3px; }
.xp-bar { height:4px; background:var(--bg3); border-radius:3px; overflow:hidden; }
.xp-fill { height:100%; background:linear-gradient(90deg,var(--blue),var(--violet)); border-radius:3px; }

/* Stat card */
.stat-card { background:var(--white); border:1px solid var(--border); border-radius:10px; padding:14px 16px; text-align:center; box-shadow:var(--shadow); }
.stat-card-val { font-family:var(--sans); font-size:24px; font-weight:800; color:var(--ink); }
.stat-card-lbl { font-family:var(--mono); font-size:8px; color:var(--ink4); letter-spacing:1px; text-transform:uppercase; margin-top:2px; }

/* Hint box */
.hint-box { background:var(--amber-l); border:1px solid var(--amber-m); border-radius:8px; padding:10px 14px; font-size:12px; color:var(--ink2); line-height:1.6; margin-top:8px; }
.hint-label { font-family:var(--mono); font-size:8px; color:var(--amber); letter-spacing:1px; margin-bottom:4px; }

/* Completion card */
.completion-card { background:var(--white); border:1px solid var(--border); border-radius:16px; padding:32px 24px; text-align:center; box-shadow:var(--shadow2); max-width:480px; margin:20px auto; }
.completion-icon { font-size:48px; margin-bottom:12px; }
.completion-title { font-family:var(--sans); font-size:22px; font-weight:800; color:var(--ink); }
.completion-score { font-family:var(--sans); font-size:48px; font-weight:800; margin:12px 0; }
.score-perfect { color:var(--green); }
.score-partial { color:var(--amber); }
.score-low     { color:var(--rose); }

/* KG card */
.kg-card { background:linear-gradient(135deg,#1E3A8A 0%,#2563EB 100%); border-radius:12px; padding:14px 16px; margin-bottom:10px; color:white; }
.kg-card-badge { font-family:var(--mono); font-size:8px; letter-spacing:1px; background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25); padding:2px 8px; border-radius:20px; color:rgba(255,255,255,0.85); display:inline-block; margin-bottom:8px; }
.kg-card-title { font-family:var(--sans); font-size:15px; font-weight:800; color:white; margin-bottom:6px; }
.kg-card-fact { font-size:12px; color:rgba(255,255,255,0.85); line-height:1.6; }

/* Topic group */
.topic-group-hdr { font-family:var(--mono); font-size:8px; letter-spacing:2px; color:var(--ink4); text-transform:uppercase; padding:12px 0 6px; }

/* Streamlit overrides */
.stButton > button { font-family:var(--body) !important; border-radius:8px !important; }
.stButton > button[kind="primary"] { background:var(--blue) !important; border:none !important; color:white !important; font-weight:700 !important; }
.stButton > button[kind="primary"]:hover { background:#1d4ed8 !important; }
.stTextInput > div > div > input { background:var(--bg2) !important; border:1.5px solid var(--border) !important; border-radius:10px !important; color:var(--ink) !important; font-family:var(--body) !important; font-size:13px !important; }
.stTextInput > div > div > input:focus { border-color:var(--blue) !important; background:var(--white) !important; box-shadow:0 0 0 3px rgba(37,99,235,0.08) !important; }
.stTabs [data-baseweb="tab-list"] { background:var(--bg2) !important; border:1px solid var(--border) !important; border-radius:10px !important; padding:3px !important; gap:2px !important; }
.stTabs [data-baseweb="tab"] { background:transparent !important; border-radius:7px !important; color:var(--ink3) !important; font-size:11px !important; font-weight:600 !important; }
.stTabs [aria-selected="true"] { background:var(--white) !important; color:var(--ink) !important; box-shadow:0 1px 4px rgba(15,23,42,0.1) !important; }
.stTabs [data-baseweb="tab-panel"] { padding:0 !important; }
.stAlert { border-radius:10px !important; }
[data-testid="metric-container"] { background:var(--white) !important; border:1px solid var(--border) !important; border-radius:10px !important; padding:12px 16px !important; box-shadow:var(--shadow) !important; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }
</style>
"""


def get_css() -> str:
    return FONTS + CSS



def render_sidebar(profile: dict, active_page: str = ""):
    import streamlit as st

    name    = profile.get("name", "Student") if profile else "Guest"
    sid     = profile.get("student_id", "") if profile else ""
    xp      = profile.get("xp", 0) if profile else 0
    initial = name[0].upper() if name else "S"
    mastery = profile.get("concept_mastery", {}) if profile else {}
    lessons = profile.get("lesson_history",  []) if profile else []

    try:
        from core.student_profile import get_level_info
        li = get_level_info(xp)
    except Exception:
        li = {"name": "Learner"}

    try:
        from config import COURSE_REGISTRY, PREREQUISITE_CHAIN
    except Exception:
        COURSE_REGISTRY = {}
        PREREQUISITE_CHAIN = {}

    course_id   = st.session_state.get("active_course_id", "")
    course_name = st.session_state.get("active_course_name", "")

    # ── Logo ──────────────────────────────────────────────────────────────────
    st.markdown("""
<div class="sb-logo">
  <div class="sb-logo-mark">&#x1F6E1;</div>
  <div class="sb-logo-text">Edu<span>SHIELD</span></div>
  <div class="sb-logo-tag">KSU</div>
</div>""", unsafe_allow_html=True)

    # ── Active course ─────────────────────────────────────────────────────────
    if course_name:
        st.markdown(f"""
<div style="margin:8px 10px 2px;">
  <div style="background:#EEF3FD;border:1px solid #BFCFFA;border-radius:8px;padding:8px 12px;">
    <div style="font-size:11px;font-weight:800;color:#0F172A;">{course_name}</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#2563EB;margin-top:1px;">{course_id}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown("""
<div style="padding:10px 12px 4px;font-family:'JetBrains Mono',monospace;
            font-size:7px;letter-spacing:2px;color:#94A3B8;text-transform:uppercase;">
  Navigation
</div>""", unsafe_allow_html=True)

    nav_items = [
      ("home",       "app.py",                        "🏠", "Home"),
      ("chat",       "pages/02_Student_Chat.py",      "💬", "Student Chat"),
      ("guide",      "pages/03_Guide_Mode.py",        "🎓", "Guide Mode"),
      ("profile",    "pages/04_My_Profile.py",        "👤", "My Profile"),
      ("instructor", "pages/01_Instructor_Panel.py",  "🏫", "Instructor Panel"),
    ]
    for page_key, page_path, icon, label in nav_items:
        is_active = active_page == page_key
        if is_active:
            st.markdown(f"""
  <div style="margin:2px 8px;padding:7px 12px;border-radius:8px;
            background:#EEF3FD;border:1px solid #BFCFFA;margin-bottom:2px;">
    <span style="font-size:13px;">{icon}</span>
    <span style="font-size:13px;font-weight:800;color:#2563EB;margin-left:6px;">{label}</span>
  </div>""", unsafe_allow_html=True)
        else:
            st.page_link(page_path, label=f"{icon}  {label}")

    # ── Prerequisites (clickable expanders) ───────────────────────────────────
    prereqs = PREREQUISITE_CHAIN.get(course_id, [])
    if prereqs:
        studied_courses = {l.get("course_id", "").upper() for l in lessons}

        st.markdown("""
<div style="padding:10px 12px 4px;font-family:'JetBrains Mono',monospace;
            font-size:7px;letter-spacing:2px;color:#94A3B8;text-transform:uppercase;">
  Prerequisites
</div>""", unsafe_allow_html=True)

        for p in prereqs:
            pdata     = COURSE_REGISTRY.get(p, {})
            pname     = pdata.get("name", p)
            pmodules  = pdata.get("modules", [])
            completed = p.upper() in studied_courses
            status    = "✅ Completed" if completed else "⚠️ Recommended first"
            color     = "#16A34A" if completed else "#D97706"
            bg        = "#F0FDF4" if completed else "#FFFBEB"
            border    = "#86EFAC" if completed else "#FDE68A"

            with st.expander(f"{p} — {pname}", expanded=False):
                st.markdown(f"""
<div style="padding:4px 0 8px;">
  <div style="font-size:11px;font-weight:700;color:{color};margin-bottom:6px;">{status}</div>
  <div style="font-size:11px;color:#334155;margin-bottom:8px;">
    This course covers the foundations needed for {course_id}.
  </div>
</div>""", unsafe_allow_html=True)
                if pmodules:
                    st.markdown('<div style="font-size:10px;font-weight:600;color:#64748B;margin-bottom:4px;">Modules:</div>', unsafe_allow_html=True)
                    for mod in pmodules:
                        st.markdown(f'<div style="font-size:10px;color:#475569;padding:2px 0;">· {mod}</div>', unsafe_allow_html=True)
                if not completed:
                    if st.button(f"Study {p} first →", key=f"goto_{p}", use_container_width=True):
                        st.session_state["active_course_id"]   = p
                        st.session_state["active_course_name"] = pname
                        st.switch_page("pages/02_Student_Chat.py")

        if not any(p.upper() in studied_courses for p in prereqs):
            st.markdown(f"""
<div style="margin:4px 10px 2px;padding:7px 10px;background:#FFF7ED;
            border:1px solid #FED7AA;border-radius:8px;font-size:10px;color:#C2410C;">
  &#x26A0; You can access {course_id}, but studying prerequisites first will help.
</div>""", unsafe_allow_html=True)

    # ── Module progress (collapsible) ─────────────────────────────────────────
    if course_id and COURSE_REGISTRY.get(course_id):
        modules   = COURSE_REGISTRY[course_id].get("modules", [])
        done_tops = {l.get("topic", "").lower() for l in lessons
                     if l.get("steps_completed", 0) >= l.get("total_steps", 5)}

        if modules:
            done_count = sum(
                1 for m in modules
                if any(m.lower() in t or t in m.lower() for t in done_tops)
            )
            pct = int(done_count / max(len(modules), 1) * 100)

            # Progress bar — always visible
            st.markdown(f"""
<div style="padding:10px 12px 6px;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:7px;letter-spacing:2px;
              color:#94A3B8;text-transform:uppercase;margin-bottom:5px;">Modules</div>
  <div style="display:flex;justify-content:space-between;font-size:10px;
              color:#64748B;margin-bottom:4px;">
    <span>{done_count}/{len(modules)} completed</span>
    <span style="color:#4F46E5;font-weight:600;">{pct}%</span>
  </div>
  <div style="background:#E2E8F0;border-radius:3px;height:6px;">
    <div style="background:linear-gradient(90deg,#4F46E5,#7C3AED);
                border-radius:3px;height:6px;width:{pct}%;"></div>
  </div>
</div>""", unsafe_allow_html=True)

            # Collapsible module list — each item is a clickable button → Guide Mode
            with st.expander(f"View all {len(modules)} modules", expanded=False):
                for mod in modules:
                    done = any(mod.lower() in t or t in mod.lower() for t in done_tops)
                    struggling = any(
                        d.get("struggle_score", 0) >= 2
                        for k, d in mastery.items()
                        if mod.lower() in k or k in mod.lower()
                    )
                    if done:       icon2, bg2, bdr = "✓", "#DCFCE7", "#86EFAC"
                    elif struggling: icon2, bg2, bdr = "!", "#FEE2E2", "#FCA5A5"
                    else:          icon2, bg2, bdr = "·", "#F8FAFC", "#E2E8F0"

                    # Render styled label above the button
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:6px;padding:3px 6px;margin:1px 0;
            background:{bg2};border:1px solid {bdr};border-radius:6px;pointer-events:none;">
  <span style="font-size:10px;font-weight:800;">{icon2}</span>
  <span style="font-size:10px;color:#334155;">{mod}</span>
</div>""", unsafe_allow_html=True)
                    # Invisible button overlaid — navigates to Guide Mode with this module pre-selected
                    safe_key = f"mod_nav_{''.join(c for c in mod if c.isalnum())[:20]}"
                    if st.button(f"→ {mod}", key=safe_key, use_container_width=True):
                        import streamlit as _st
                        _st.session_state["gm_preselect_mod"] = mod
                        _st.session_state["gm_topic"] = None
                        _st.session_state["gm_step"]  = 0
                        _st.switch_page("pages/03_Guide_Mode.py")

    # ── Mastery summary ───────────────────────────────────────────────────────
    if mastery:
        confident  = sum(1 for d in mastery.values()
                         if d.get("struggle_score", 0) == 0 and d.get("times_asked", 0) > 0)
        struggling = sum(1 for d in mastery.values() if d.get("struggle_score", 0) >= 2)
        learning   = len(mastery) - confident - struggling
        st.markdown(f"""
<div style="padding:6px 10px 8px;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:7px;letter-spacing:2px;
              color:#94A3B8;text-transform:uppercase;margin-bottom:6px;">Mastery</div>
  <div style="display:flex;gap:5px;">
    <div style="flex:1;text-align:center;background:#DCFCE7;border:1px solid #86EFAC;
                border-radius:7px;padding:5px 3px;">
      <div style="font-size:15px;font-weight:800;color:#15803D;">{confident}</div>
      <div style="font-size:8px;color:#16A34A;font-weight:600;">GOT IT</div>
    </div>
    <div style="flex:1;text-align:center;background:#FEF9C3;border:1px solid #FDE047;
                border-radius:7px;padding:5px 3px;">
      <div style="font-size:15px;font-weight:800;color:#A16207;">{learning}</div>
      <div style="font-size:8px;color:#CA8A04;font-weight:600;">LEARNING</div>
    </div>
    <div style="flex:1;text-align:center;background:#FEE2E2;border:1px solid #FCA5A5;
                border-radius:7px;padding:5px 3px;">
      <div style="font-size:15px;font-weight:800;color:#B91C1C;">{struggling}</div>
      <div style="font-size:8px;color:#DC2626;font-weight:600;">HARD</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Student card ──────────────────────────────────────────────────────────
    if profile:
        st.markdown(f"""
<div style="border-top:1px solid #E2E8F0;padding:10px 12px;
            display:flex;align-items:center;gap:10px;margin-top:4px;">
  <div style="width:32px;height:32px;border-radius:8px;flex-shrink:0;
              background:linear-gradient(135deg,#2563EB,#7C3AED);
              display:flex;align-items:center;justify-content:center;
              font-weight:800;color:white;font-size:14px;">{initial}</div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:12px;font-weight:700;color:#0F172A;
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:#94A3B8;">
      {li.get("name","Learner")} &middot; {sid}
    </div>
  </div>
  <div style="background:#FFFBEB;color:#D97706;border:1px solid #FDE68A;
              padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;
              white-space:nowrap;">{xp} XP</div>
</div>""", unsafe_allow_html=True)
        # Make profile card clickable
        if st.button("👤 View Profile", key="sidebar_profile_btn", use_container_width=True):
            st.switch_page("pages/04_My_Profile.py")
        # Add logout button
        if st.button("🚪 Log Out", key="sidebar_logout_btn", use_container_width=True):
            del st.session_state["student_profile"]
            if "agent" in st.session_state:
                del st.session_state["agent"]
            st.rerun()

def verdict_badge(verdict: str) -> str:
    v = (verdict or "").upper()
    if "VERIFIED" in v or v == "OK":
        return '<span class="msg-tag tag-ok">✓ VERIFIED</span>'
    elif "CONTRADICT" in v or "WRONG" in v:
        return '<span class="msg-tag tag-wrong">✗ INCORRECT</span>'
    elif "BOUNDARY" in v:
        return '<span class="msg-tag tag-lost">⚠ BOUNDARY</span>'
    elif "DOMAIN" in v:
        return '<span class="msg-tag tag-wrong">✗ OUT OF SCOPE</span>'
    elif "UNVERIFIABLE" in v:
        return '<span class="msg-tag tag-lost">? UNVERIFIED</span>'
    return ""


def guard_color(verdict: str) -> str:
    v = (verdict or "").upper()
    if "VERIFIED" in v: return "ok"
    if "CONTRADICT" in v: return "bad"
    return "warn"


def sidebar_profile_html(profile: dict) -> str:
    """Legacy compat — returns empty string, use render_sidebar() instead."""
    return ""
