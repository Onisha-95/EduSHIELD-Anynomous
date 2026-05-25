"""
EduSHIELD — Home & Initialization
Run: streamlit run app.py  (from the EduSHIELD/ directory)
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
                    CHROMA_PATH, PARLEY_API_KEY, LLM_MODEL, COURSE_REGISTRY)
from core.student_profile import load_profile, create_profile, save_profile, start_session, get_level_info
from core.design_system import get_css, render_sidebar

# FIX: Cache the Neo4j KG client so it's created once and reused across
# all page loads instead of reconnecting every time the home page renders.
@st.cache_resource
def _get_cached_kg():
    try:
        from core.neo4j_client import Neo4jKGClient
        kg = Neo4jKGClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
        return kg
    except Exception:
        return None

@st.cache_data(ttl=60)
def _get_all_courses_cached():
    """Cache the course list — rebuilds at most once per minute."""
    all_courses = dict(COURSE_REGISTRY)
    try:
        kg = _get_cached_kg()
        if kg:
            with kg._session() as s:
                rows = s.run(
                    "MATCH (c:Concept) WHERE c.course_id IS NOT NULL "
                    "RETURN DISTINCT c.course_id AS cid"
                )
                for row in rows:
                    cid = row.get("cid", "")
                    if cid and cid not in all_courses:
                        all_courses[cid] = {"id": cid, "name": cid, "modules": []}
    except Exception:
        pass
    return all_courses

@st.cache_resource
def _get_cached_agent(cid: str):
    """
    FIX: Cache the agent per course_id so it is created ONCE and reused.
    Without this, every Streamlit re-render (page nav, widget interaction)
    re-creates the agent, re-connects Neo4j, and re-warms the embedding model.
    """
    from core.educational_agent import SimpleEducationalAgent
    from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                        NEO4J_DATABASE, CHROMA_PATH, PARLEY_API_KEY,
                        LLM_MODEL, OPENAI_API_KEY)
    ag = SimpleEducationalAgent(
        NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE,
        CHROMA_PATH, PARLEY_API_KEY, LLM_MODEL, course_id=cid
    )
    ag.active_course_id = cid
    return ag

st.set_page_config(page_title="EduSHIELD", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
st.markdown(get_css(), unsafe_allow_html=True)

# ── Hide default Streamlit chrome ─────────────────────────────────────────────
st.markdown("""
<style>
  #MainMenu, footer { visibility: hidden; }
  [data-testid="stHeader"] { visibility: hidden; }
  .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
</style>""", unsafe_allow_html=True)

agent   = st.session_state.get("agent")
profile = st.session_state.get("student_profile")

# Initialize session state keys if not present
if "active_course_id" not in st.session_state:
    st.session_state["active_course_id"] = None
if "active_course_name" not in st.session_state:
    st.session_state["active_course_name"] = None

with st.sidebar:
    render_sidebar(profile, active_page="home")

# ═══════════════════════════════════════════════════════════════════════════════
# NOT CONNECTED — Login / Setup page
# ═══════════════════════════════════════════════════════════════════════════════
if not agent:

    col_main, col_features = st.columns([3, 2], gap="large")

    with col_main:
        # Hero
        st.markdown("""
<div style="margin-bottom:28px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:2.2rem;
              font-weight:800;color:#0F172A;letter-spacing:-0.03em;line-height:1.2;">
    Learn smarter.<br><span style="color:#2563EB;">Think deeper.</span>
  </div>
  <div style="font-size:14px;color:#64748B;line-height:1.75;max-width:480px;margin-top:10px;">
    EduSHIELD is your AI tutor with a built-in fact-checker. Every answer is
    grounded in your course slides — no hallucinations, no off-topic detours.
  </div>
</div>""", unsafe_allow_html=True)

        # ── Step 1: Profile ───────────────────────────────────────────────────
        st.markdown('<p style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Step 1 — Your Profile</p>', unsafe_allow_html=True)

        if profile is None:
            # Two cards instead of tabs for better UX
            login_col, create_col = st.columns([1, 1], gap="large")
            
            with login_col:
                st.markdown("""
<div style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:12px;padding:20px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:15px;font-weight:800;
              color:#0F172A;margin-bottom:14px;">👤 Returning Student</div>
  <div style="font-size:13px;color:#64748B;margin-bottom:12px;">
    Enter your student ID to log in to your existing account.
  </div>
</div>""", unsafe_allow_html=True)
                sid_in = st.text_input("Student ID", placeholder="e.g. 901234567",
                                       key="login_sid", label_visibility="collapsed")
                if st.button("Log in →", type="primary", key="do_login", use_container_width=True):
                    if sid_in.strip():
                        found = load_profile(sid_in.strip())
                        if found:
                            start_session(found)
                            st.session_state["student_profile"] = found
                            st.rerun()
                        else:
                            st.error(f"No profile found for '{sid_in}'. Create one below.")
                    else:
                        st.error("Enter your student ID.")

            with create_col:
                st.markdown("""
<div style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:12px;padding:20px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:15px;font-weight:800;
              color:#0F172A;margin-bottom:14px;">✨ New Student</div>
  <div style="font-size:13px;color:#64748B;margin-bottom:12px;">
    Create a new account to get started with EduSHIELD.
  </div>
</div>""", unsafe_allow_html=True)
                n_name    = st.text_input("Full name",  placeholder="e.g. Onisha Williams", key="new_name", label_visibility="collapsed")
                n_sid     = st.text_input("Student ID", placeholder="e.g. 901234567",       key="new_sid", label_visibility="collapsed")
                n_courses = st.multiselect("Enrolled courses",
                                           list(COURSE_REGISTRY.keys()),
                                           default=["CSE1321"], key="new_courses")
                if st.button("Create account →", type="primary", key="do_create", use_container_width=True):
                    if not n_name.strip():
                        st.error("Enter your name.")
                    elif not n_sid.strip():
                        st.error("Enter your student ID.")
                    elif load_profile(n_sid.strip()):
                        st.error(f"ID '{n_sid}' already exists — use Log in.")
                    else:
                        p = create_profile(n_name.strip(), n_sid.strip(), n_courses)
                        start_session(p)
                        st.session_state["student_profile"] = p
                        st.rerun()

        else:
            # Profile already loaded — show card
            li  = get_level_info(profile.get("xp", 0))
            xp  = profile.get("xp", 0)
            pct = min(100, (xp % 200) / 200 * 100)
            initial = profile["name"][0].upper()
            st.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:14px 16px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:40px;height:40px;border-radius:50%;
                background:linear-gradient(135deg,#2563EB,#7C3AED);
                display:flex;align-items:center;justify-content:center;
                font-weight:800;color:white;font-size:17px;flex-shrink:0;">{initial}</div>
    <div style="flex:1;">
      <div style="font-weight:800;color:#0F172A;font-size:15px;">{profile['name']}</div>
      <div style="font-size:10px;color:#94A3B8;font-family:'JetBrains Mono',monospace;">
        {li.get('name','Learner')} · {profile['student_id']}
      </div>
    </div>
    <div style="background:#FFFBEB;color:#D97706;border:1px solid #FDE68A;
                padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700;">
      {xp} XP
    </div>
  </div>
  <div style="margin-top:10px;height:5px;background:#E2E8F0;border-radius:3px;overflow:hidden;">
    <div style="height:100%;width:{pct:.0f}%;background:linear-gradient(90deg,#2563EB,#7C3AED);border-radius:3px;"></div>
  </div>
  <div style="font-size:9px;color:#94A3B8;text-align:right;margin-top:3px;font-family:'JetBrains Mono',monospace;">
    {xp % 200}/200 XP to next level
  </div>
</div>""", unsafe_allow_html=True)

            st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
            if st.button("Switch account", key="switch_acct", use_container_width=False):
                del st.session_state["student_profile"]
                st.rerun()

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

        # ── Step 2: Course ────────────────────────────────────────────────────
        if profile:
            st.markdown('<p style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Step 2 — Select Course</p>', unsafe_allow_html=True)

            # Build full course list using cached helper — no fresh Neo4j connection on each load
            all_courses = _get_all_courses_cached()

            enrolled  = profile.get("courses", list(all_courses.keys()))
            # Show ALL courses, not just enrolled ones — student can pick any
            available = list(all_courses.keys())
            
            # Get active course from session state or use first available
            current_active = st.session_state.get("active_course_id")
            if not current_active or current_active not in available:
                current_active = enrolled[0] if enrolled else (available[0] if available else None)
            
            active_c = current_active

            # Dropdown for course selection (scales to many courses)
            if available:
                course_labels = {cid: f"{cid} — {all_courses[cid].get('name', cid)}" for cid in available}
                
                # Ensure the active course exists in course_labels
                try:
                    default_index = list(course_labels.keys()).index(active_c) if active_c in course_labels else 0
                except (ValueError, IndexError):
                    default_index = 0
                
                selected_label = st.selectbox(
                    "Choose your course",
                    options=list(course_labels.values()),
                    index=default_index,
                    label_visibility="collapsed",
                    key="course_dropdown"
                )
                # Map back to course id
                selected_cid = next(cid for cid, lbl in course_labels.items() if lbl == selected_label)
                selected_info = all_courses.get(selected_cid, {})
                selected_name = selected_info.get("name", selected_cid)

                if selected_cid != active_c:
                    st.session_state["active_course_id"]   = selected_cid
                    st.session_state["active_course_name"] = selected_name
                    active_c = selected_cid
            else:
                st.error("❌ No courses available. Please contact your instructor to set up courses.")
                st.stop()

            # Show selected course card
            prereqs = selected_info.get("prerequisites", [])
            mods = selected_info.get("modules", [])

            st.markdown(f"""
<div style="background:#EEF3FD;border:2px solid #2563EB;border-radius:10px;
            padding:12px 16px;margin-top:6px;">
  <div style="display:flex;align-items:center;justify-content:space-between;">
    <div>
      <div style="font-size:9px;font-weight:700;color:#2563EB;text-transform:uppercase;
                  letter-spacing:1px;">{selected_cid}</div>
      <div style="font-size:13px;font-weight:800;color:#0F172A;margin-top:2px;">{selected_name}</div>
    </div>
    <div style="font-size:20px;">✓</div>
  </div>
</div>""", unsafe_allow_html=True)
            
            # Render prerequisites and module count as structured UI (not HTML strings)
            if prereqs:
                st.caption(f"Prerequisites: {', '.join(prereqs)}")
            if mods:
                st.caption(f"{len(mods)} modules")

            st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

            # ── Step 3: Connect ───────────────────────────────────────────────
            st.markdown('<p style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Step 3 — Connect</p>', unsafe_allow_html=True)

            if st.button("🔗  Connect & Start EduSHIELD", type="primary", use_container_width=True, key="connect_btn"):
                cid     = st.session_state.get("active_course_id", selected_cid)
                cname_s = all_courses.get(cid, {}).get("name", cid)
                
                # Validate course was selected
                if not cid:
                    st.error("❌ Please select a course first.")
                else:
                    with st.spinner("Connecting to Neo4j and loading Knowledge Graph…"):
                        try:
                            # FIX: Use cached agent -- created once, never re-initialised
                            ag = _get_cached_agent(cid)
                            ag.active_course_name = cname_s
                            if profile:
                                ag.set_student_profile(profile)
                            
                            st.session_state["agent"]              = ag
                            st.session_state["active_course_id"]   = cid
                            st.session_state["active_course_name"] = cname_s
                            st.success(f"✓ Connected! Ready to start learning {cname_s}.")
                            st.rerun()
                        except ImportError as ie:
                            st.error(f"❌ Import error: {str(ie)}\nPlease ensure all required packages are installed.")
                        except Exception as e:
                            st.error(f"❌ Connection failed: {str(e)}")
                            with st.expander("Error details"):
                                st.code(str(e))

    with col_features:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">What EduSHIELD does</p>', unsafe_allow_html=True)

        for icon, bg, color, border, title, desc in [
            ("🛡", "#EEF3FD", "#2563EB", "#BFCFFA",
             "Dual-Guard Safety",
             "Guard #2 blocks off-topic questions before the LLM. Guard #1 validates every sentence against your course KG."),
            ("📚", "#ECFDF5", "#0D9488", "#99F6E4",
             "Slide-Grounded Answers",
             "Every response is built from facts extracted from your instructor's PPTX and PDF slides — not the internet."),
            ("🎓", "#F3EFFE", "#7C3AED", "#C4B5FD",
             "Socratic Guide Mode",
             "5-step structured lessons: prior knowledge, guided discovery, code exploration, misconception check, synthesis."),
            ("📈", "#FFFBEB", "#D97706", "#FDE68A",
             "Persistent Student Model",
             "Your mastery and struggles follow you across sessions. The tutor adapts based on where you need help most."),
        ]:
            st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;
            padding:12px 14px;margin-bottom:8px;">
  <div style="font-size:18px;margin-bottom:4px;">{icon}</div>
  <div style="font-size:13px;font-weight:800;color:{color};margin-bottom:3px;">{title}</div>
  <div style="font-size:12px;color:#475569;line-height:1.6;">{desc}</div>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTED — Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
else:
    cid   = st.session_state.get("active_course_id",   agent.active_course_id or "")
    cname = st.session_state.get("active_course_name", agent.active_course_name or cid)
    name  = profile["name"].split()[0] if profile else "Student"

    # Header
    st.markdown(f"""
<div style="margin-bottom:20px;">
  <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:1.8rem;
              font-weight:800;color:#0F172A;letter-spacing:-0.02em;">
    Welcome back, {name} 👋
  </div>
  <div style="font-size:13px;color:#64748B;margin-top:4px;display:flex;align-items:center;gap:8px;">
    Active course: <strong>{cname}</strong>
    <span style="font-family:'JetBrains Mono',monospace;font-size:9px;
                 background:#DCFCE7;color:#16A34A;border:1px solid #86EFAC;
                 padding:1px 8px;border-radius:20px;">● CONNECTED</span>
  </div>
</div>""", unsafe_allow_html=True)

    # KG Stats row
    try:
        stats      = agent.kg.get_stats()
        n_concepts = stats.get("concepts", "—")
        n_facts    = stats.get("facts", "—")
        n_rels     = stats.get("relationships", "—")
    except Exception:
        n_concepts = n_facts = n_rels = "—"

    s1, s2, s3 = st.columns(3)
    for col, label, val, color in [
        (s1, "KG Concepts",   n_concepts, "#2563EB"),
        (s2, "KG Facts",      n_facts,    "#7C3AED"),
        (s3, "Relationships", n_rels,     "#059669"),
    ]:
        with col:
            val_text = f"{val:,}" if isinstance(val, (int, float)) else str(val)
            st.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
            padding:14px;text-align:center;">
  <div style="font-size:24px;font-weight:800;color:{color};">{val_text}</div>
  <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;
              letter-spacing:1px;margin-top:2px;">{label}</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

    # Navigation cards
    st.markdown('<p style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Where do you want to go?</p>', unsafe_allow_html=True)

    nc1, nc2, nc3 = st.columns(3)
    for col, icon, title, desc, page, btn_label in [
        (nc1, "💬", "Student Chat",    "Ask anything — answers grounded in your slides",          "pages/02_Student_Chat.py", "Open Chat →"),
        (nc2, "🎓", "Guide Mode",      "5-step Socratic lessons from your Knowledge Graph",       "pages/03_Guide_Mode.py",   "Start Lesson →"),
        (nc3, "👤", "My Profile",      "View XP, mastery scores, and lesson history",             "pages/04_My_Profile.py",   "View Profile →"),
    ]:
        with col:
            st.markdown(f"""
<div style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:12px;
            padding:18px;text-align:center;margin-bottom:6px;
            box-shadow:0 1px 3px rgba(15,23,42,0.06);">
  <div style="font-size:28px;margin-bottom:8px;">{icon}</div>
  <div style="font-size:14px;font-weight:800;color:#0F172A;margin-bottom:4px;">{title}</div>
  <div style="font-size:11px;color:#64748B;line-height:1.5;">{desc}</div>
</div>""", unsafe_allow_html=True)
            if st.button(btn_label, key=f"go_{title}", use_container_width=True, type="primary"):
                st.switch_page(page)

    # Struggle alerts
    if profile:
        mastery    = profile.get("concept_mastery", {})
        struggling = [c for c, d in mastery.items() if d.get("struggle_score", 0) >= 2]
        if struggling:
            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
            chips = "".join(f'<span style="background:#FEE2E2;color:#B91C1C;border:1px solid #FCA5A5;padding:2px 10px;border-radius:20px;font-size:11px;margin:2px;display:inline-block;">{c}</span>' for c in struggling[:6])
            st.markdown(f"""
<div style="background:#FFF1F2;border:1px solid #FCA5A5;border-radius:10px;padding:12px 16px;">
  <div style="font-size:10px;font-weight:700;color:#E11D48;text-transform:uppercase;
              letter-spacing:1px;margin-bottom:6px;">⚠ Needs Attention</div>
  <div style="font-size:12px;color:#334155;margin-bottom:6px;">
    You've been struggling with these topics — try Guide Mode to strengthen them:
  </div>
  {chips}
</div>""", unsafe_allow_html=True)
