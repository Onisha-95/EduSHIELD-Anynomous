"""
Instructor Panel — Upload slides, trigger ingestion, view KG stats.
"""
import streamlit as st
import sys, os, shutil, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from config import COURSE_REGISTRY
from core.design_system import get_css, render_sidebar

st.set_page_config(page_title="Instructor Panel — EduSHIELD", page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
st.markdown(get_css(), unsafe_allow_html=True)

profile = st.session_state.get("student_profile")
with st.sidebar:
    render_sidebar(profile, active_page="instructor")

# ── Simple Instructor Authentication ───────────────────────────────────────────
INSTRUCTOR_PASSWORD = "instructor123"  # TODO: Move to config

if "instructor_authenticated" not in st.session_state:
    st.session_state.instructor_authenticated = False

if not st.session_state.instructor_authenticated:
    st.markdown("""
<div style="padding:40px 20px;text-align:center;">
  <div style="font-size:32px;margin-bottom:20px;">🏫</div>
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:24px;font-weight:800;
              color:#0F172A;margin-bottom:10px;">Instructor Access</div>
  <div style="font-size:14px;color:#64748B;margin-bottom:30px;">
    Enter your instructor password to access the admin panel.
  </div>
</div>""", unsafe_allow_html=True)
    
    pwd = st.text_input("Password", type="password", placeholder="Enter instructor password")
    if st.button("Unlock Panel", type="primary", use_container_width=True):
        if pwd == INSTRUCTOR_PASSWORD:
            st.session_state.instructor_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    
    # Show hint for first-time setup
    with st.expander("🔑 Hint: Default Password"):
        st.info(f"**Default instructor password:** `{INSTRUCTOR_PASSWORD}`\n\n"
                f"For production, change this in `pages/01_Instructor_Panel.py` line 15 or move to environment variables.")
    
    st.stop()

agent = st.session_state.get("agent")
if not agent:
    st.error("System not initialized. Go to Home first.")
    if st.button("Go to Home"): st.switch_page("app.py")
    st.stop()

BASE        = os.path.dirname(os.path.dirname(__file__))
SLIDES_ROOT = os.path.join(BASE, "slides")

# ── Top bar ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-bar">
  <div class="top-title">🏫 Instructor Panel</div>
  <span class="top-tag" style="background:#F0FDF4;color:#16A34A;border:1px solid #86EFAC;">ADMIN</span>
</div>""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("← Back to Home", use_container_width=True):
        st.switch_page("app.py")
with col2:
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.instructor_authenticated = False
        if "student_profile" in st.session_state:
            del st.session_state["student_profile"]
        if "agent" in st.session_state:
            del st.session_state["agent"]
        st.rerun()

st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

# ── KG Stats ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1rem;font-weight:800;
            color:#0F172A;margin-bottom:12px;">📊 Knowledge Graph Status</div>""",
            unsafe_allow_html=True)

try:
    stats = agent.kg.get_stats()
    c1, c2, c3, c4 = st.columns(4)
    for col, label, key, color in [
        (c1, "Concepts",      "concepts",      "#2563EB"),
        (c2, "Facts",         "facts",         "#7C3AED"),
        (c3, "Relationships", "relationships", "#059669"),
        (c4, "Examples",      "examples",      "#D97706"),
    ]:
        val = stats.get(key, 0)
        col.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:16px;text-align:center;">
  <div style="font-size:26px;font-weight:800;color:{color};">{val:,}</div>
  <div style="font-size:11px;color:#64748B;font-weight:600;text-transform:uppercase;margin-top:2px;">{label}</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    if stats.get("concepts", 0) == 0:
        st.warning("⚠️ KG is empty — upload slides and run ingestion below.")
    else:
        st.success(f"✅ KG is populated and ready — {stats.get('concepts',0):,} concepts loaded.")
except Exception as e:
    st.warning(f"Could not load KG stats: {e}")

st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

# ── Upload Slides ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1rem;font-weight:800;
            color:#0F172A;margin-bottom:4px;">📤 Upload Course Materials</div>
<div style="font-size:13px;color:#64748B;margin-bottom:14px;">
  Upload PDF, PPTX, or DOCX files for any course. Files are saved to the
  <code>slides/</code> folder and ready for ingestion.
</div>""", unsafe_allow_html=True)

upload_course = st.selectbox(
    "Select course to upload for",
    options=list(COURSE_REGISTRY.keys()),
    format_func=lambda x: f"{x} — {COURSE_REGISTRY[x].get('name', x)}",
    key="upload_course_select"
)

uploaded_files = st.file_uploader(
    "Drop files here",
    type=["pdf", "pptx", "ppt", "docx", "doc"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    key="slide_uploader"
)

if uploaded_files:
    course_folder = os.path.join(SLIDES_ROOT, upload_course)
    os.makedirs(course_folder, exist_ok=True)

    saved = []
    for f in uploaded_files:
        dest = os.path.join(course_folder, f.name)
        with open(dest, "wb") as out:
            out.write(f.getbuffer())
        saved.append(f.name)

    st.success(f"✅ Saved {len(saved)} file(s) to `slides/{upload_course}/`:")
    for name in saved:
        st.markdown(f"&nbsp;&nbsp;• `{name}`", unsafe_allow_html=True)

    st.info("Now run the ingestion command below to add these to the Knowledge Graph.")

st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

# ── Current slide files ────────────────────────────────────────────────────────
st.markdown("""
<div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1rem;font-weight:800;
            color:#0F172A;margin-bottom:10px;">📁 Current Slide Files</div>""",
            unsafe_allow_html=True)

any_files = False
cols = st.columns(len(COURSE_REGISTRY))
for col, (cid, cdata) in zip(cols, COURSE_REGISTRY.items()):
    folder = os.path.join(SLIDES_ROOT, cid)
    files  = []
    if os.path.isdir(folder):
        files = [f for f in os.listdir(folder)
                 if f.lower().endswith((".pdf", ".pptx", ".ppt", ".docx", ".doc"))]
    with col:
        st.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:12px;">
  <div style="font-size:12px;font-weight:800;color:#0F172A;margin-bottom:2px;">{cid}</div>
  <div style="font-size:10px;color:#64748B;margin-bottom:8px;">{cdata.get('name','')}</div>
  <div style="font-size:11px;color:{'#16A34A' if files else '#94A3B8'};">
    {'<br>'.join(f'📄 {f}' for f in files) if files else '— no files yet —'}
  </div>
</div>""", unsafe_allow_html=True)
        if files:
            any_files = True

st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

# ── Ingestion Commands ─────────────────────────────────────────────────────────
st.markdown("""
<div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1rem;font-weight:800;
            color:#0F172A;margin-bottom:4px;">⚙️ Run Ingestion</div>
<div style="font-size:13px;color:#64748B;margin-bottom:14px;">
    Run these commands from your terminal inside the <code>EduSHIELD/</code> folder
  after uploading slides. Run all three, then rebuild the index.
</div>""", unsafe_allow_html=True)

for cid, cdata in COURSE_REGISTRY.items():
    folder_name = cid
    folder_path = os.path.join(SLIDES_ROOT, folder_name)
    cmd = f"python3 run_ingestion.py --course {cid} --folder slides/{folder_name} --auto-modules"
    with st.expander(f"**{cid}** — {cdata.get('name', '')}"):
        st.code(cmd, language="bash")
        files_exist = os.path.isdir(folder_path) and any(
            f.lower().endswith((".pdf",".pptx",".docx"))
            for f in os.listdir(folder_path)
        ) if os.path.isdir(folder_path) else False
        if files_exist:
            st.success("✅ Slides found — ready to ingest")
        else:
            st.warning("⚠️ No slides in this folder yet — upload files above first")

st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="font-size:13px;color:#64748B;margin-bottom:6px;">
  After all three ingestions complete, rebuild the vector index:
</div>""", unsafe_allow_html=True)
st.code("python3 build_rag_index.py", language="bash")

st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

# ── Browse KG Concepts ─────────────────────────────────────────────────────────
st.markdown("""
<div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1rem;font-weight:800;
            color:#0F172A;margin-bottom:10px;">🔍 Browse Knowledge Graph</div>""",
            unsafe_allow_html=True)

try:
    concepts = agent.kg.get_all_concepts(limit=200)

    # Filter to clean concepts only for display
    def is_display_clean(t):
        if not t or len(t) < 3 or not t.strip()[0].isalpha(): return False
        if any(c in t for c in set('()[]{}=<>!&|^~;\\/@$%#`')): return False
        if re.search(r'^\d', t.strip()): return False
        bad = [r'Cid:', r'redorblue', r'str\(', r'\.{2,}',
               r'\bvs\.?\b', r'\.gov|\.net']
        return not any(re.search(p, t, re.I) for p in bad)

    clean = [c for c in concepts if is_display_clean(c)]
    all_c = concepts  # keep all for full view

    tab_clean, tab_all = st.tabs([
        f"✅ Clean concepts ({len(clean)})",
        f"📋 All raw ({len(all_c)})"
    ])

    with tab_clean:
        search = st.text_input("Search", placeholder="e.g. loop", key="search_clean",
                               label_visibility="collapsed")
        filtered = [c for c in clean if not search or search.lower() in c.lower()]
        st.caption(f"{len(filtered)} concepts")
        cols = st.columns(4)
        for i, c in enumerate(filtered[:80]):
            cols[i % 4].markdown(
                f'<span style="font-size:12px;color:#334155;">• {c}</span>',
                unsafe_allow_html=True)

    with tab_all:
        search2 = st.text_input("Search all", placeholder="e.g. loop", key="search_all",
                                label_visibility="collapsed")
        filtered2 = [c for c in all_c if not search2 or search2.lower() in c.lower()]
        st.caption(f"{len(filtered2)} concepts (includes raw slide fragments)")
        cols2 = st.columns(4)
        for i, c in enumerate(filtered2[:100]):
            is_clean = is_display_clean(c)
            color = "#334155" if is_clean else "#EF4444"
            cols2[i % 4].markdown(
                f'<span style="font-size:11px;color:{color};">• {c}</span>',
                unsafe_allow_html=True)
        if not search2:
            st.caption("🔴 Red = raw fragment that will be filtered out in student UI")

except Exception as e:
    st.warning(f"Could not load concepts: {e}")
