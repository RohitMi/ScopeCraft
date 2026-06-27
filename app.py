# app.py
# ScopeCraft — Streamlit entry point
# Chat interface + role tabs + sidebar info

import streamlit as st
from utils.state_manager import (
    init_state,
    reset_state,
    set_idea,
    get_idea,
    add_chat_message,
    get_chat_history,
    get_completeness_score,
    get_question_count,
    is_interview_complete,
    is_generation_done,
    get_brd,
    get_user_stories,
    get_conflict_flags,
)
from agents.interview_agent import start_interview, process_answer
from agents.conflict_agent import run_conflict_scan, handle_conflict_resolution
from agents.generator_agent import run_generation


# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ScopeCraft",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Init State ────────────────────────────────────────────────────────────────

init_state()


# ── Session flags (not in state_manager — UI only) ────────────────────────────

if "app_phase" not in st.session_state:
    # Phases: "landing" | "interview" | "conflict" | "done"
    st.session_state["app_phase"] = "landing"

if "awaiting_conflict_resolve" not in st.session_state:
    st.session_state["awaiting_conflict_resolve"] = False


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/telescope.png", width=64)
    st.title("🔭 ScopeCraft")
    st.caption("Agentic Requirements Engineering")
    st.markdown("---")
    st.markdown("""
**What ScopeCraft does:**

1. 💬 Interviews you about your product idea
2. 🔍 Detects conflicts in your requirements
3. 📄 Generates a professional BRD
4. 📋 Produces a MoSCoW User Story backlog

---
**How to use:**

- Describe your app idea in the text box
- Answer the Interview Agent's questions
- Review any flagged conflicts
- View generated documents in the tabs

---
**Built with:**
- 🦙 Llama 3.3 70B via Groq
- 🔗 LangChain
- ⚡ Streamlit
""")
    st.markdown("---")
    if st.session_state["app_phase"] != "landing":
        score = get_completeness_score()
        q_count = get_question_count()
        st.metric("Completeness", f"{score}%")
        st.metric("Questions Asked", f"{q_count} / 10")
        conflicts = get_conflict_flags()
        if conflicts:
            st.warning(f"⚠️ {len(conflicts)} conflict(s) flagged")
        else:
            if is_interview_complete():
                st.success("✅ No conflicts")


# ── Main Area ─────────────────────────────────────────────────────────────────

st.title("🔭 ScopeCraft")
st.caption("Turn your product idea into structured development artifacts — powered by AI agents.")
st.markdown("---")


# ── PHASE: LANDING ────────────────────────────────────────────────────────────

if st.session_state["app_phase"] == "landing":
    st.subheader("What's your product idea?")
    st.markdown(
        "Describe your app concept below — rough ideas welcome. "
        "ScopeCraft's Interview Agent will ask targeted questions to extract full requirements."
    )

    idea_input = st.text_area(
        label="Your idea",
        placeholder=(
            "e.g. I want to build a mobile app that helps freelancers track their invoices, "
            "send payment reminders, and generate monthly income reports..."
        ),
        height=180,
        key="idea_input_box",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        submit = st.button("🚀 Start", type="primary", use_container_width=True)

    if submit:
        if not idea_input.strip():
            st.warning("Please enter your product idea before continuing.")
        else:
            set_idea(idea_input.strip())
            add_chat_message("user", idea_input.strip())
            with st.spinner("Interview Agent thinking..."):
                response = start_interview()
            st.session_state["app_phase"] = "interview"
            st.rerun()


# ── PHASE: INTERVIEW + CONFLICT + DONE ───────────────────────────────────────

else:
    # ── Reset Button ──────────────────────────────────────────────────────────
    col_title, col_reset = st.columns([8, 1])
    with col_reset:
        if st.button("🔄 Reset", use_container_width=True):
            reset_state()
            st.session_state["app_phase"] = "landing"
            st.session_state["awaiting_conflict_resolve"] = False
            st.rerun()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_chat, tab_brd, tab_stories = st.tabs([
        "💬 Interview",
        "📄 BRD",
        "📋 User Stories",
    ])

    # ── TAB: CHAT ─────────────────────────────────────────────────────────────
    with tab_chat:

        # Progress bar during interview
        if st.session_state["app_phase"] == "interview":
            score = get_completeness_score()
            st.markdown(f"**Requirements Completeness: {score}%**")
            st.progress(score / 100)
            st.markdown("---")

        # Render chat history
        chat_history = get_chat_history()
        for msg in chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # ── Interview phase input ─────────────────────────────────────────────
        if st.session_state["app_phase"] == "interview":
            user_input = st.chat_input("Your answer...")
            if user_input:
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.spinner("Interview Agent thinking..."):
                    response, interview_done = process_answer(user_input)

                if interview_done:
                    # Move to conflict scan
                    with st.spinner("Conflict Agent scanning requirements..."):
                        conflict_msg, has_conflicts = run_conflict_scan()

                    if has_conflicts:
                        st.session_state["app_phase"] = "conflict"
                        st.session_state["awaiting_conflict_resolve"] = True
                    else:
                        # No conflicts — generate immediately
                        st.session_state["app_phase"] = "generating"
                        with st.spinner("Generating documents..."):
                            run_generation()
                        st.session_state["app_phase"] = "done"

                st.rerun()

        # ── Conflict resolution phase input ───────────────────────────────────
        elif st.session_state["app_phase"] == "conflict":
            user_input = st.chat_input("Resolve conflicts or type 'proceed' to continue...")
            if user_input:
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.spinner("Re-scanning conflicts..."):
                    response, ready = handle_conflict_resolution(user_input)

                if ready:
                    st.session_state["awaiting_conflict_resolve"] = False
                    with st.spinner("Generating documents..."):
                        run_generation()
                    st.session_state["app_phase"] = "done"

                st.rerun()

        # ── Done phase — no more input ────────────────────────────────────────
        elif st.session_state["app_phase"] == "done":
            st.success("✅ Documents ready — switch to BRD or User Stories tabs above.")

    # ── TAB: BRD ─────────────────────────────────────────────────────────────
    with tab_brd:
        if is_generation_done():
            brd = get_brd()
            if brd:
                col_brd, col_copy = st.columns([9, 1])
                with col_copy:
                    st.download_button(
                        label="⬇️ Download",
                        data=brd,
                        file_name="ScopeCraft_BRD.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                st.markdown(brd)
            else:
                st.info("BRD not yet generated.")
        else:
            st.info("Complete the interview to generate the BRD.")

    # ── TAB: USER STORIES ─────────────────────────────────────────────────────
    with tab_stories:
        if is_generation_done():
            stories = get_user_stories()
            if stories:
                col_st, col_dl = st.columns([9, 1])
                with col_dl:
                    st.download_button(
                        label="⬇️ Download",
                        data=stories,
                        file_name="ScopeCraft_UserStories.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                st.markdown(stories)
            else:
                st.info("User Stories not yet generated.")
        else:
            st.info("Complete the interview to generate User Stories.")