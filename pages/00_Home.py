"""
00_Home.py — Student login / profile creation (shown in sidebar nav)
Redirects to My Profile dashboard if already logged in.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from core.student_profile import (
    create_profile, load_profile, save_profile,
    list_profiles, start_session,
    get_mastery_color, get_mastery_emoji, get_level_info,
)
from core.design_system import get_css, sidebar_profile_html

st.set_page_config(page_title="EduSHIELD — Login", page_icon="🛡", layout="wide", initial_sidebar_state="expanded")
st.markdown(get_css(), unsafe_allow_html=True)

agent = st.session_state.get("agent")
if not agent:
    st.warning("System not initialized yet.")
    st.info("Go to the Home page to connect the Knowledge Graph and load the guards first.")
    if st.button("← Go to Home"):
        st.switch_page("app.py")
    st.stop()

profile = st.session_state.get("student_profile")

with st.sidebar:
    st.markdown('<div class="sidebar-logo">🛡 <span>Edu</span>SHIELD</div>', unsafe_allow_html=True)
    if profile:
        st.markdown(sidebar_profile_html(profile), unsafe_allow_html=True)
        st.markdown("---")
    st.page_link("app.py",                        label="🏠  Home")
    st.page_link("pages/02_Student_Chat.py",       label="💬  Student Chat")
    st.page_link("pages/03_Guide_Mode.py",         label="🎓  Guide Mode")
    st.page_link("pages/04_My_Profile.py",         label="👤  My Profile")

# If already logged in, redirect to profile
if profile:
    st.switch_page("pages/04_My_Profile.py")
    st.stop()

# ── Login page ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="login-hero">
    <div class="login-logo">Edu<em>SHIELD</em></div>
  <div class="login-sub">Your AI tutor with a built-in fact-checker. Every answer verified against your course.</div>
</div>
""", unsafe_allow_html=True)

_, center, _ = st.columns([1, 2, 1])
with center:
    tab_login, tab_new = st.tabs(["Returning student", "New student"])

    with tab_login:
        all_profiles = list_profiles()
        if not all_profiles:
            st.info("No profiles yet. Create one in the 'New student' tab.")
        else:
            st.markdown('<div style="margin-bottom:12px;font-size:13px;color:#8892A4;">Select your profile to continue:</div>', unsafe_allow_html=True)
            for p in all_profiles:
                li = get_level_info(p.get("xp", 0))
                initial = p['name'][0].upper()
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;padding:8px 0;">
  <div style="width:36px;height:36px;border-radius:50%;background:rgba(99,102,241,0.12);
              border:1.5px solid #6366F1;display:flex;align-items:center;justify-content:center;
              font-family:'Syne',sans-serif;font-weight:800;color:#6366F1;font-size:14px;">{initial}</div>
  <div>
    <div style="font-weight:600;font-size:14px;color:#E8EAF0;">{p['name']}</div>
    <div style="font-size:11px;color:#8892A4;">Lv.{li['level_num']} {li['level_name']} · {p.get('xp',0)} XP · {p.get('total_lessons',0)} lessons</div>
  </div>
</div>""", unsafe_allow_html=True)
                with c2:
                    if st.button("Log in", key=f"login_{p['student_id']}", type="primary"):
                        start_session(p)
                        st.session_state["student_profile"] = p
                        agent.set_student_profile(p)
                        st.rerun()

            st.divider()
            sid_input = st.text_input("Or enter Student ID directly:", placeholder="e.g. 901234567", key="manual_sid")
            if st.button("Log in →", key="manual_login", use_container_width=True, type="primary"):
                if sid_input.strip():
                    found = load_profile(sid_input.strip())
                    if found:
                        start_session(found)
                        st.session_state["student_profile"] = found
                        agent.set_student_profile(found)
                        st.rerun()
                    else:
                        st.error(f"No profile found for '{sid_input}'.")

    with tab_new:
        n_name    = st.text_input("Full name", placeholder="e.g. Onisha Williams", key="new_name")
        n_sid     = st.text_input("Student ID", placeholder="e.g. 901234567", key="new_sid")
        n_courses = st.multiselect("Enrolled courses",
                                   ["CSE1300", "CSE1321", "MATH1112"],
                                   default=["CSE1321"], key="new_courses")
        if st.button("Create account →", type="primary", key="do_create", use_container_width=True):
            if not n_name.strip():
                st.error("Enter your name.")
            elif not n_sid.strip():
                st.error("Enter your student ID.")
            elif load_profile(n_sid.strip()):
                st.error(f"ID '{n_sid}' already exists. Use the Log in tab.")
            else:
                new_p = create_profile(n_name.strip(), n_sid.strip(), n_courses)
                start_session(new_p)
                st.session_state["student_profile"] = new_p
                agent.set_student_profile(new_p)
                st.success(f"Welcome, {n_name.strip()}!")
                st.rerun()
