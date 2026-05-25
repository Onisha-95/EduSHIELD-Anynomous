"""
My Profile — Mastery dashboard with XP, concept grid, lesson history.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from core.design_system import get_css, render_sidebar
from core.student_profile import get_level_info

st.set_page_config(page_title="My Profile — EduSHIELD", page_icon="👤", layout="wide", initial_sidebar_state="expanded")
st.markdown(get_css(), unsafe_allow_html=True)

profile = st.session_state.get("student_profile")
if not profile:
    st.warning("Not logged in — go to Home first.")
    if st.button("← Home"): st.switch_page("app.py")
    st.stop()

with st.sidebar:
    render_sidebar(profile, active_page="profile")

name    = profile.get("name", "Student")
sid     = profile.get("student_id", "")
xp      = profile.get("xp", 0)
streak  = profile.get("streak_days", 0)
courses = profile.get("courses", [])
li      = get_level_info(xp)
initial = name[0].upper()

# ── Top bar ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-bar">
  <div class="top-title">👤 My Profile</div>
  <span class="top-tag tag-prof">DASHBOARD</span>
  <div style="margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:9px;color:#94A3B8;">
    {" · ".join(courses)}
  </div>
</div>""", unsafe_allow_html=True)

# ── Profile header ─────────────────────────────────────────────────────────────
xp_pct = min(100, (xp % 200) / 200 * 100)
st.markdown(f"""
<div style="padding:20px 0 12px;">
  <div style="display:flex;align-items:center;gap:16px;">
    <div style="width:56px;height:56px;border-radius:16px;
                background:linear-gradient(135deg,#2563EB,#7C3AED);
                display:flex;align-items:center;justify-content:center;
                font-family:'Bricolage Grotesque',sans-serif;font-size:24px;font-weight:800;color:white;">
      {initial}
    </div>
    <div>
      <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:22px;font-weight:800;color:#0F172A;">{name}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#94A3B8;margin-top:2px;">
        {li.get('name','Learner')} · {sid}
      </div>
    </div>
    <div style="margin-left:auto;text-align:right;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#94A3B8;letter-spacing:1px;text-transform:uppercase;">
        Total XP
      </div>
      <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:28px;font-weight:800;color:#D97706;">{xp}</div>
    </div>
  </div>
  <div style="margin-top:12px;">
    <div class="xp-bar-wrap">
      <div class="xp-bar-top">
        <span>{li.get('name','Learner')}</span>
        <span>{xp % 200}/200 XP to next level</span>
      </div>
      <div class="xp-bar"><div class="xp-fill" style="width:{xp_pct:.0f}%;"></div></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── Edit Profile Section ───────────────────────────────────────────────────────
with st.expander("✏️ Edit Profile", expanded=False):
    from config import COURSE_REGISTRY
    
    edit_name = st.text_input("Full Name", value=name, key="edit_name")
    edit_courses = st.multiselect(
        "Enrolled Courses",
        options=list(COURSE_REGISTRY.keys()),
        default=courses,
        key="edit_courses"
    )
    
    if st.button("Save Changes", type="primary", use_container_width=True):
        # Update profile
        profile["name"] = edit_name
        profile["courses"] = edit_courses
        from core.student_profile import save_profile
        save_profile(profile)
        # Update session state
        st.session_state["student_profile"] = profile
        st.success("Profile updated!")
        st.rerun()

# ── Stats row ──────────────────────────────────────────────────────────────────
lessons       = profile.get("lesson_history", [])
mastery       = profile.get("concept_mastery", {})
total_sessions = profile.get("total_sessions", len(lessons))
total_turns    = profile.get("total_turns", 0)
verified_count = sum(l.get("verified_count", 0) for l in lessons)
total_answers  = sum(l.get("total_answers", 0) for l in lessons)

stats = [
    ("SESSIONS", total_sessions, "#2563EB"),
    ("LESSONS",  len(lessons),   "#0D9488"),
    ("CORRECT",  verified_count, "#16A34A"),
    ("STREAK",   f"{streak}d",   "#D97706"),
    ("CONCEPTS", len(mastery),   "#7C3AED"),
]
scols = st.columns(5)
for col, (lbl, val, color) in zip(scols, stats):
    with col:
        st.markdown(f"""
<div class="stat-card">
  <div class="stat-card-val" style="color:{color};">{val}</div>
  <div class="stat-card-lbl">{lbl}</div>
</div>""", unsafe_allow_html=True)

st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

# ── Two columns: mastery | history ─────────────────────────────────────────────
left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    # Struggle warning
    struggling = [c for c, d in mastery.items() if d.get("struggle_score", 0) >= 2]
    if struggling:
        st.markdown(f"""
<div style="background:#FFF1F2;border:1px solid #FCA5A5;border-radius:10px;
            padding:12px 16px;margin-bottom:12px;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:1px;
              color:#E11D48;margin-bottom:5px;">⚠ NEEDS ATTENTION</div>
  <div style="font-size:12px;color:#334155;">
    Struggling with: {'  '.join(f'<span class="chip chip-rose">{c}</span>' for c in struggling[:6])}
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("""
<div style="font-family:'Bricolage Grotesque',sans-serif;font-size:13px;font-weight:800;
            color:#0F172A;margin-bottom:10px;">Concept Mastery</div>""", unsafe_allow_html=True)

    # Filter
    filt_options = ["All", "Struggling", "Learning", "Confident"]
    filt = st.selectbox("Filter", filt_options, key="mastery_filter", label_visibility="collapsed")

    if mastery:
        # Group by status
        groups = {
            "Struggling":  [(c, d) for c, d in mastery.items() if d.get("struggle_score", 0) >= 2],
            "Learning":    [(c, d) for c, d in mastery.items() if 0 < d.get("struggle_score", 0) < 2],
            "Confident":   [(c, d) for c, d in mastery.items() if d.get("struggle_score", 0) == 0 and d.get("times_asked", 0) > 0],
        }

        def show_group(label, items, chip_cls, icon):
            if not items: return
            if filt != "All" and filt != label: return
            st.markdown(f"""
<div class="topic-group-hdr">{icon} &nbsp;{label}</div>""", unsafe_allow_html=True)
            chips_html = "".join(
                f'<span class="mastery-chip {chip_cls}">{c} <span style="font-family:var(--mono);font-size:9px;">×{d.get("times_asked",0)}</span></span>'
                for c, d in items
            )
            st.markdown(f'<div style="margin-bottom:8px;">{chips_html}</div>', unsafe_allow_html=True)

        show_group("Struggling", groups["Struggling"], "mc-struggle", "🔴")
        show_group("Learning",   groups["Learning"],   "mc-learning",  "📖")
        show_group("Confident",  groups["Confident"],  "mc-confident", "✅")
    else:
        st.markdown("""
<div style="background:#F4F6F9;border:1px solid #E2E6EE;border-radius:12px;
            padding:24px;text-align:center;">
  <div style="font-size:28px;margin-bottom:8px;">🧠</div>
  <div style="font-size:13px;color:#64748B;">No concepts tracked yet.<br>Start a lesson in Guide Mode!</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    if st.button("🎓 Start a Guided Lesson", type="primary", use_container_width=True):
        st.switch_page("pages/03_Guide_Mode.py")


with right_col:
    st.markdown("""
<div style="font-family:'Bricolage Grotesque',sans-serif;font-size:13px;font-weight:800;
            color:#0F172A;margin-bottom:10px;">Lesson History</div>""", unsafe_allow_html=True)

    if lessons:
        for lesson in lessons[-10:][::-1]:
            topic_l  = lesson.get("topic", "Unknown")
            steps    = lesson.get("steps_completed", lesson.get("steps_done", 0))
            total_s  = lesson.get("total_steps", 5)
            verdicts = lesson.get("verdicts", [])
            verified = lesson.get("verified_count", verdicts.count("VERIFIED"))
            total_a  = max(lesson.get("total_answers", len(verdicts) if verdicts else 1), 1)
            acc      = int(verified / total_a * 100)
            xp_l     = lesson.get("xp_earned", lesson.get("xp", 0))
            date_raw = lesson.get("date") or lesson.get("completed_at") or lesson.get("started_at") or ""
            date_str = date_raw[:10] if date_raw else ""
            done     = steps >= total_s
            icon     = "✅" if done else "🔄"

            score_cls = "score-green" if acc >= 80 else ("score-amber" if acc >= 50 else "score-rose")

            st.markdown(f"""
<div class="lesson-card">
  <span style="font-size:20px;">{icon}</span>
  <div style="flex:1;min-width:0;">
    <div class="lesson-topic">{topic_l}</div>
    <div class="lesson-meta">{steps}/{total_s} steps · {date_str} · +{xp_l} XP</div>
  </div>
  <div class="lesson-score {score_cls}">{acc}%</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="background:#F4F6F9;border:1px solid #E2E6EE;border-radius:12px;
            padding:24px;text-align:center;">
  <div style="font-size:28px;margin-bottom:8px;">📚</div>
  <div style="font-size:13px;color:#64748B;">No lessons yet.<br>Pick a topic in Guide Mode!</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    if st.button("💬 Go to Student Chat", use_container_width=True):
        st.switch_page("pages/02_Student_Chat.py")

# ── Footer with logout ─────────────────────────────────────────────────────────
st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
logout_col1, logout_col2 = st.columns([1, 1])
with logout_col1:
    if st.button("🚪 Log Out", use_container_width=True):
        del st.session_state["student_profile"]
        if "agent" in st.session_state:
            del st.session_state["agent"]
        st.rerun()
