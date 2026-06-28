import streamlit as st
from utils.db_manager import init_db, list_sessions, delete_session
from utils.state_manager import (
    init_state, reset_state,
    get_phase, set_phase,
    get_idea, set_idea,
    get_chat_history, set_chat_history,
    get_qa_pairs, set_qa_pairs,
    get_conflict_flags, set_conflict_flags,
    get_brd, get_user_stories,
    get_question_count, set_question_count,
    get_completeness, set_completeness,
    is_generation_done, set_generation_done,
    is_conflict_done, set_conflict_done,
    get_session_id, get_session_name,
    save_current_session, load_session_into_state,
    set_session_name
)
from agents.interview_agent import start_interview, process_answer
from agents.conflict_agent import run_conflict_scan, handle_conflict_resolution
from agents.generator_agent import run_generation
from utils.error_handler import has_error, get_last_error, clear_error
from utils.validators import validate_idea, validate_session_name, validate_answer, validate_conflict_input

# ── Error Banner ──────────────────────────────────────────────────────────────
def render_error_banner():
    if has_error():
        st.error(f"⚠️ **Agent Error:** {get_last_error()}")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔄 Retry", type="primary"):
                clear_error()
                st.rerun()
        with col2:
            st.caption("Error may be a temporary LLM timeout. Retry usually fixes it.")

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
init_state()

st.set_page_config(page_title="ScopeCraft", page_icon="🔭", layout="wide")
st.title("🔭 ScopeCraft")
st.caption("Agentic Requirements Engineering")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Session Info")
    sid = get_session_id()
    sname = get_session_name()
    if sid:
        st.success(f"**{sname}**")
        st.caption(f"Session ID: {sid}")
        if st.button("💾 Save Now"):
            save_current_session()
            st.success("Saved!")
    else:
        st.info("No active session")

    st.divider()
    st.subheader("Metrics")
    st.metric("Questions Asked", get_question_count())
    st.metric("Completeness", f"{get_completeness()}%")
    st.metric("Q&A Pairs", len(get_qa_pairs()))

    st.divider()
    if st.button("🔄 Reset / New Session"):
        reset_state()
        st.rerun()

# ── PHASE: LANDING ────────────────────────────────────────────────────────────
if get_phase() == 'landing':
    render_error_banner()

    sessions = list_sessions()
    if sessions:
        st.subheader("📂 Resume a Previous Session")
        cols = st.columns([3, 1, 1])
        cols[0].markdown("**Session Name**")
        cols[1].markdown("**Last Updated**")
        cols[2].markdown("**Actions**")

        for s in sessions:
            c0, c1, c2 = st.columns([3, 1, 1])
            idea_preview = (s['idea'][:60] + '...') if s['idea'] and len(s['idea']) > 60 else s['idea']
            c0.markdown(f"**{s['name']}**  \n_{idea_preview}_")
            c1.caption(s['updated_at'][:16].replace('T', ' '))
            with c2:
                bcol1, bcol2 = st.columns(2)
                if bcol1.button("▶ Resume", key=f"resume_{s['id']}"):
                    if load_session_into_state(s['id']):
                        st.rerun()
                if bcol2.button("🗑", key=f"del_{s['id']}"):
                    delete_session(s['id'])
                    st.rerun()

        st.divider()

    st.subheader("🆕 Start New Session")
    session_name_input = st.text_input(
        "Session name",
        placeholder="e.g. Food Delivery App — v1",
        key="session_name_input"
    )
    idea_input = st.text_area(
        "Describe your app idea",
        placeholder="e.g. I want to build a marketplace where freelancers can offer services...",
        height=150,
        key="idea_input"
    )

    if st.button("🚀 Start Requirements Interview", type="primary"):
        name_valid, name_err = validate_session_name(session_name_input)
        idea_valid, idea_err = validate_idea(idea_input)

        if not name_valid:
            st.warning(f"⚠️ {name_err}")
        elif not idea_valid:
            st.warning(f"⚠️ {idea_err}")
        else:
            set_idea(idea_input.strip())
            set_session_name(session_name_input.strip())
            clear_error()

            with st.spinner("Interview Agent starting..."):
                try:
                    first_q = start_interview(idea_input.strip())
                    history = [{'role': 'assistant', 'content': first_q}]
                    set_chat_history(history)
                    set_question_count(1)
                    set_phase('interview')
                    save_current_session(session_name_input.strip())
                except Exception:
                    st.rerun()
            st.rerun()

# ── PHASE: INTERVIEW ──────────────────────────────────────────────────────────
elif get_phase() == 'interview':
    render_error_banner()

    st.subheader("💬 Requirements Interview")
    completeness = get_completeness()
    st.progress(completeness / 100, text=f"Completeness: {completeness}%")

    for msg in get_chat_history():
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])

    user_input = st.chat_input("Your answer...")
    if user_input:
        answer_valid, answer_err = validate_answer(user_input)
        if not answer_valid:
            st.warning(f"⚠️ {answer_err}")
            st.stop()

        history = get_chat_history()
        history.append({'role': 'user', 'content': user_input})
        set_chat_history(history)
        clear_error()

        with st.spinner("Interview Agent thinking..."):
            try:
                result = process_answer(user_input)
                history.append({'role': 'assistant', 'content': result['message']})
                set_chat_history(history)
                set_completeness(result['completeness'])
                set_question_count(get_question_count() + 1)

                if result.get('qa_pair'):
                    qa = get_qa_pairs()
                    qa.append(result['qa_pair'])
                    set_qa_pairs(qa)

                save_current_session()

                if result.get('done'):
                    with st.spinner("Conflict Agent scanning..."):
                        flags = run_conflict_scan(get_qa_pairs())
                        set_conflict_flags(flags)
                    save_current_session()

                    if flags:
                        set_phase('conflict')
                    else:
                        set_conflict_done(True)
                        with st.spinner("Generator Agent — Building BRD (call 1 of 2)..."):
                            run_generation(get_idea(), get_qa_pairs(), [])
                        set_generation_done(True)
                        set_phase('done')
                        save_current_session()

            except Exception:
                pass

        st.rerun()

# ── PHASE: CONFLICT ───────────────────────────────────────────────────────────
elif get_phase() == 'conflict':
    render_error_banner()

    st.subheader("⚠️ Conflicts Detected")
    st.info("Review each conflict below. Clarify in chat or click Proceed when ready.")

    flags = get_conflict_flags()
    for i, flag in enumerate(flags):
        with st.expander(f"⚠️ {flag.get('title', f'Conflict {i+1}')}", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**📌 Source A:**\n\n_{flag.get('source_a', '')}_")
                st.markdown(f"**📌 Source B:**\n\n_{flag.get('source_b', '')}_")
            with col_b:
                st.markdown(f"**❗ Issue:**\n\n{flag.get('explanation', '')}")
                st.markdown(f"**💡 Suggestion:**\n\n{flag.get('suggestion', '')}")

            if st.button("✅ Mark Resolved", key=f"resolve_{i}"):
                remaining = [f for j, f in enumerate(flags) if j != i]
                set_conflict_flags(remaining)
                history = get_chat_history()
                history.append({
                    'role': 'assistant',
                    'content': f"✅ Conflict **{flag.get('title', f'Conflict {i+1}')}** marked as resolved."
                })
                set_chat_history(history)
                save_current_session()
                st.rerun()

    st.divider()

    for msg in get_chat_history():
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])

    st.markdown("**Resolve via chat or proceed directly:**")
    col_chat, col_proceed = st.columns([3, 1])

    with col_chat:
        clarification = st.chat_input("Clarify a conflict...")

    with col_proceed:
        remaining_count = len(get_conflict_flags())
        btn_label = (
            "✅ Proceed to Generation"
            if remaining_count == 0
            else f"⚠️ Proceed Anyway ({remaining_count} unresolved)"
        )
        btn_type = "primary" if remaining_count == 0 else "secondary"
        if st.button(btn_label, type=btn_type, key="proceed_btn"):
            clear_error()
            set_conflict_done(True)
            with st.spinner("Generator Agent — Building BRD then Stories (2 LLM calls)..."):
                try:
                    run_generation(get_idea(), get_qa_pairs(), get_conflict_flags())
                    set_generation_done(True)
                    set_phase('done')
                    save_current_session()
                except Exception:
                    pass
            st.rerun()

    if clarification:
        conflict_valid, conflict_err = validate_conflict_input(clarification)
        if not conflict_valid:
            st.warning(f"⚠️ {conflict_err}")
            st.stop()

        history = get_chat_history()
        history.append({'role': 'user', 'content': clarification})
        set_chat_history(history)
        clear_error()

        with st.spinner("Re-scanning conflicts..."):
            try:
                result = handle_conflict_resolution(clarification, get_qa_pairs())
                history.append({'role': 'assistant', 'content': result['message']})
                set_chat_history(history)

                if result.get('resolved'):
                    set_conflict_flags(result.get('remaining_flags', []))
                    if not result.get('remaining_flags'):
                        set_conflict_done(True)
                        with st.spinner("Generator Agent — Building BRD then Stories (2 LLM calls)..."):
                            run_generation(get_idea(), get_qa_pairs(), [])
                        set_generation_done(True)
                        set_phase('done')

                save_current_session()
            except Exception:
                pass

        st.rerun()

# ── PHASE: DONE ───────────────────────────────────────────────────────────────
elif get_phase() == 'done':
    render_error_banner()

    st.subheader("✅ Documents Ready")
    st.success(f"Session: **{get_session_name()}** — saved to DB.")

    tab_ba, tab_dev, tab_qa, tab_hld = st.tabs([
        "📋 BA View — BRD",
        "👨‍💻 Dev View — User Stories",
        "🧪 QA View — Acceptance Tests",
        "🏗️ Architect View — HLD"
    ])

    with tab_ba:
        brd = get_brd()
        if brd:
            st.markdown(brd)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Download BRD (.md)",
                    data=brd,
                    file_name=f"{get_session_name().replace(' ', '_')}_BRD.md",
                    mime="text/markdown"
                )
            with col2:
                try:
                    from utils.export_manager import export_brd_to_docx
                    docx_bytes = export_brd_to_docx(brd, get_session_name())
                    st.download_button(
                        "⬇️ Download BRD (.docx)",
                        data=docx_bytes,
                        file_name=f"{get_session_name().replace(' ', '_')}_BRD.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.warning(f"DOCX export error: {e}")
        else:
            st.warning("BRD not generated.")

    with tab_dev:
        stories = get_user_stories()
        if stories:
            st.markdown(stories)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Download User Stories (.md)",
                    data=stories,
                    file_name=f"{get_session_name().replace(' ', '_')}_UserStories.md",
                    mime="text/markdown"
                )
            with col2:
                try:
                    from utils.export_manager import export_stories_to_docx
                    docx_bytes = export_stories_to_docx(stories, get_session_name())
                    st.download_button(
                        "⬇️ Download User Stories (.docx)",
                        data=docx_bytes,
                        file_name=f"{get_session_name().replace(' ', '_')}_UserStories.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.warning(f"DOCX export error: {e}")
        else:
            st.warning("User Stories not generated.")

    with tab_qa:
        st.markdown("### 🧪 Acceptance Test Scenarios")
        st.caption("Gherkin scenarios generated from your User Stories.")

        if not st.session_state.get('acceptance_tests'):
            if st.button("⚙️ Generate Acceptance Tests", type="primary"):
                with st.spinner("Test Agent generating Gherkin scenarios..."):
                    try:
                        from agents.test_agent import run_test_generation
                        tests = run_test_generation()
                        st.session_state['acceptance_tests'] = tests
                        st.rerun()
                    except Exception as e:
                        st.error(f"Test generation error: {e}")
        else:
            tests = st.session_state['acceptance_tests']
            st.markdown(tests)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Download Tests (.md)",
                    data=tests,
                    file_name=f"{get_session_name().replace(' ', '_')}_AcceptanceTests.md",
                    mime="text/markdown"
                )
            with col2:
                if st.button("🔄 Regenerate Tests"):
                    del st.session_state['acceptance_tests']
                    st.rerun()

    with tab_hld:
        st.markdown("### 🏗️ High Level Design")
        st.caption("Architecture diagram + tech stack + design decisions.")

        if not st.session_state.get('hld'):
            if st.button("⚙️ Generate HLD", type="primary"):
                with st.spinner("HLD Agent generating architecture diagrams..."):
                    try:
                        from agents.hld_agent import run_hld_generation
                        hld = run_hld_generation()
                        st.session_state['hld'] = hld
                        st.rerun()
                    except Exception as e:
                        st.error(f"HLD generation error: {e}")
        else:
            hld = st.session_state['hld']
            st.markdown(hld)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Download HLD (.md)",
                    data=hld,
                    file_name=f"{get_session_name().replace(' ', '_')}_HLD.md",
                    mime="text/markdown"
                )
            with col2:
                if st.button("🔄 Regenerate HLD"):
                    del st.session_state['hld']
                    st.rerun()