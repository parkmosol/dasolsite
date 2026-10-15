import datetime as dt
import streamlit as st
from database import get_db
from utils import calc_pace, parse_km, parse_time_str

TODAY = dt.date.today()
MOODS = ["GREAT", "GOOD", "SO SO", "BAD", "TERRIBLE"]


def format_course_filter(option):
    if isinstance(option, str):
        return option
    course, distance = option
    return f"{course} / {distance:g} km" if distance else course


@st.dialog("러닝 기록 삭제")
def delete_running_log_dialog(log):
    distance = parse_km(log["course"], log["distance_km"])
    course_label = f"{log['course']} / {distance:g} km" if distance else log["course"]
    st.write(f"{log['date']} · {course_label} 기록을 삭제할까요?")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("삭제", type="primary", use_container_width=True):
            conn = get_db()
            conn.execute("DELETE FROM running_logs WHERE id = ?", (log["id"],))
            conn.commit()
            conn.close()
            st.session_state.pop("delete_running_id", None)
            st.session_state.pop("selected_running_id", None)
            st.success("기록이 삭제되었습니다.")
            st.rerun()
    with cancel_col:
        if st.button("취소", use_container_width=True):
            st.session_state.pop("delete_running_id", None)
            st.rerun()


def render_running_log_editor(log):
    total_minutes, seconds = divmod(log["time_sec"], 60)
    hours, minutes = divmod(total_minutes, 60)
    time_value = (
        f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        if hours
        else f"{minutes:02d}:{seconds:02d}"
    )

    with st.form(f"edit_run_form_{log['id']}"):
        st.markdown("#### 러닝 기록 편집")
        edit_date = st.date_input(
            "날짜",
            dt.date.fromisoformat(log["date"]),
            key=f"edit_run_date_{log['id']}",
        )
        course_col, distance_col = st.columns([3, 1])
        with course_col:
            edit_course = st.text_input(
                "코스명",
                log["course"],
                key=f"edit_run_course_{log['id']}",
            )
        with distance_col:
            saved_distance = parse_km(log["course"], log["distance_km"])
            edit_distance = st.number_input(
                "거리 (km)",
                min_value=0.01,
                max_value=999.99,
                value=max(saved_distance, 0.01),
                step=0.01,
                key=f"edit_run_distance_{log['id']}",
            )
        edit_mood = st.selectbox(
            "기분",
            MOODS,
            index=MOODS.index(log["mood"]) if log["mood"] in MOODS else 0,
            key=f"edit_run_mood_{log['id']}",
        )
        edit_time = st.text_input(
            "소요 시간", time_value, key=f"edit_run_time_{log['id']}"
        )
        edit_memo = st.text_area(
            "메모", log["memo"] or "", key=f"edit_run_memo_{log['id']}"
        )
        save_col, cancel_col = st.columns([1, 1], gap="small")
        with save_col:
            save_edit = st.form_submit_button(
                "변경 저장", type="primary", use_container_width=True
            )
        with cancel_col:
            cancel_edit = st.form_submit_button("취소", use_container_width=True)

    if save_edit:
        edit_seconds, _ = parse_time_str(edit_time)
        if edit_seconds is None:
            st.error("시간 형식이 올바르지 않습니다. (예: 00:44:39 또는 4439)")
        elif not edit_course.strip():
            st.error("코스명을 입력해 주세요.")
        else:
            conn = get_db()
            conn.execute(
                """
                UPDATE running_logs SET date = ?, mood = ?, course = ?,
                    distance_km = ?, time_sec = ?, pace = ?, memo = ?
                WHERE id = ?
                """,
                (
                    edit_date.isoformat(),
                    edit_mood,
                    edit_course.strip(),
                    edit_distance,
                    edit_seconds,
                    calc_pace(edit_course, edit_seconds, edit_distance),
                    edit_memo,
                    log["id"],
                ),
            )
            conn.commit()
            conn.close()
            st.session_state.pop("edit_running_id", None)
            st.session_state.pop("selected_running_id", None)
            st.success("기록이 수정되었습니다.")
            st.rerun()
    if cancel_edit:
        st.session_state.pop("edit_running_id", None)
        st.rerun()


def render_running_page():
    st.markdown(
        "<h1 style='font-weight: 800; font-size: 26px; margin-top: 0;'>RUNNING DIARY</h1>",
        unsafe_allow_html=True,
    )
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][TODAY.weekday()]
    st.markdown(
        f"<p style='color: #7A7570; font-size: 14px; margin-bottom: 20px;'>{TODAY.strftime('%Y.%m.%d')} ({weekday_str})</p>",
        unsafe_allow_html=True,
    )

    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM running_logs ORDER BY date DESC"
    ).fetchall()
    conn.close()

    prefix = TODAY.strftime("%Y-%m")

    month_logs = [it for it in logs if it["date"].startswith(prefix)]
    month_km = sum(parse_km(it["course"], it["distance_km"]) for it in month_logs)
    total_km = sum(parse_km(it["course"], it["distance_km"]) for it in logs)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("이번 달 누적 거리", f"{month_km:.1f} km")
    with c2:
        st.metric("이번 달 러닝", f"{len(month_logs)}회")
    with c3:
        st.metric("총 누적 거리", f"{total_km:.1f} km")
    with c4:
        st.metric("총 러닝", f"{len(logs)}회")

    st.markdown("<hr style='border:0.5px solid #E6E2DD;'>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        div[class*="st-key-run_cell_"] button {
            width: 100% !important;
            background: transparent !important;
            color: var(--dasol-text) !important;
            border: none !important;
            border-bottom: 1px solid var(--dasol-border) !important;
            border-radius: 0 !important;
            text-align: center !important;
            justify-content: center !important;
            padding: 6px 2px !important;
            box-shadow: none !important;
            font-size: 11px !important;
            white-space: nowrap !important;
            height: 40px !important;
            min-height: 40px !important;
        }
        div[class*="st-key-run_cell_"] button p {
            font-size: 11px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        div[class*="st-key-run_cell_"] button:hover {
            background: var(--dasol-accent-soft) !important;
            border-bottom-color: var(--dasol-accent) !important;
            color: var(--dasol-text) !important;
        }
        div[class*="st-key-run_cell_"][class*="_mood"] button {
            color: var(--mood-color) !important;
            font-weight: 700 !important;
        }
        .run-table-heading {
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 2px;
            border-bottom: 1px solid var(--dasol-border);
            color: var(--dasol-muted);
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    mood_colors = {
        "GREAT": "#1F8A5B",
        "GOOD": "#3E7FC4",
        "SO SO": "#B8860B",
        "BAD": "#D9782D",
        "TERRIBLE": "#C8443F",
    }
    mood_rules = "".join(
        f".st-key-run_cell_{it['id']}_mood button "
        f"{{ --mood-color: {mood_colors.get(it['mood'], 'var(--dasol-text)')}; }}"
        for it in logs
    )
    if mood_rules:
        st.markdown(f"<style>{mood_rules}</style>", unsafe_allow_html=True)

    course_options = sorted(
        {
            (it["course"], parse_km(it["course"], it["distance_km"]))
            for it in logs
        }
    )
    filter_options = ["전체 코스"] + course_options
    filter_course = st.selectbox(
        "코스 필터",
        filter_options,
        format_func=format_course_filter,
        label_visibility="collapsed",
    )
    add_col, _ = st.columns([1.5, 5])
    with add_col:
        if st.button("+ 기록 추가", use_container_width=True):
            st.session_state.show_add_modal = True

    if st.session_state.get("show_add_modal", False):
        with st.form("run_add_form"):
            st.markdown("### 새로운 러닝 기록")
            r_date = st.date_input("날짜", TODAY)
            course_col, distance_col = st.columns([3, 1])
            with course_col:
                r_course = st.text_input("코스명", placeholder="예: 판암파출소")
            with distance_col:
                r_distance = st.number_input(
                    "거리 (km)",
                    min_value=0.01,
                    max_value=999.99,
                    value=5.0,
                    step=0.01,
                )
            r_mood = st.selectbox(
                "기분", ["GREAT", "GOOD", "SO SO", "BAD", "TERRIBLE"]
            )
            r_time = st.text_input("소요 시간 (예: 00:44:39 또는 4439)")
            r_memo = st.text_area("메모")

            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button(
                    "저장하기", type="primary", use_container_width=True
                )
            with col_b:
                canceled = st.form_submit_button(
                    "취소", use_container_width=True
                )

            if submitted:
                sec, hms = parse_time_str(r_time)
                if sec is None:
                    st.error(
                        "시간 형식이 올바르지 않습니다. (예: 00:44:39 또는 4439)"
                    )
                elif not r_course.strip():
                    st.error("코스명을 입력해 주세요.")
                else:
                    pace = calc_pace(r_course, sec, r_distance)
                    conn = get_db()
                    conn.execute(
                        """
                        INSERT INTO running_logs(
                            date, mood, course, distance_km, time_sec, pace, memo
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r_date.isoformat(),
                            r_mood,
                            r_course.strip(),
                            r_distance,
                            sec,
                            pace,
                            r_memo,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.session_state.show_add_modal = False
                    st.success("저장되었습니다.")
                    st.rerun()
            if canceled:
                st.session_state.show_add_modal = False
                st.rerun()

    filtered_logs = [
        it
        for it in logs
        if filter_course == "전체 코스"
        or (
            it["course"],
            parse_km(it["course"], it["distance_km"]),
        )
        == filter_course
    ]
    filtered_logs.sort(key=lambda x: x["date"], reverse=True)

    if filtered_logs:
        header_columns = st.columns(
            [1.1, 2.2, 0.85, 1.05, 1.2, 1.8], gap="small"
        )
        for column, heading in zip(
            header_columns, ["날짜", "코스", "기분", "시간", "페이스", "메모"]
        ):
            with column:
                st.markdown(
                    f"<div class='run-table-heading'>{heading}</div>",
                    unsafe_allow_html=True,
                )

        for it in filtered_logs:
            m_sec, s_sec = divmod(it["time_sec"], 60)
            h_sec, m_sec = divmod(m_sec, 60)
            t_str = (
                f"{h_sec:02d}:{m_sec:02d}:{s_sec:02d}"
                if h_sec
                else f"{m_sec:02d}:{s_sec:02d}"
            )
            columns = st.columns([1.1, 2.2, 0.85, 1.05, 1.2, 1.8], gap="small")
            values = [
                ("date", it["date"]),
                (
                    "course",
                    f"{it['course']} / {parse_km(it['course'], it['distance_km']):g} km"
                    if parse_km(it["course"], it["distance_km"])
                    else it["course"],
                ),
                ("mood", it["mood"]),
                ("time", t_str),
                ("pace", it["pace"]),
                ("memo", it["memo"] or "-"),
            ]
            for column, (field, value) in zip(columns, values):
                with column:
                    with st.container(key=f"run_cell_{it['id']}_{field}"):
                        if st.button(
                            value,
                            key=f"run_value_{it['id']}_{field}",
                            use_container_width=True,
                        ):
                            if st.session_state.get("selected_running_id") == it["id"]:
                                st.session_state.pop("selected_running_id", None)
                                st.session_state.pop("edit_running_id", None)
                            else:
                                st.session_state.selected_running_id = it["id"]
                                st.session_state.pop("edit_running_id", None)
                            st.rerun()

            if st.session_state.get("selected_running_id") == it["id"]:
                action_columns = st.columns([0.65, 0.65, 6], gap="small")
                with action_columns[0]:
                    if st.button("편집", key=f"edit_run_{it['id']}"):
                        st.session_state.edit_running_id = it["id"]
                        st.rerun()
                with action_columns[1]:
                    if st.button("삭제", key=f"delete_run_{it['id']}"):
                        st.session_state.delete_running_id = it["id"]
                        st.rerun()
                if st.session_state.get("edit_running_id") == it["id"]:
                    render_running_log_editor(it)
    else:
        st.info("등록된 러닝 기록이 없습니다.")

    delete_id = st.session_state.get("delete_running_id")
    if delete_id is not None:
        delete_log = next((it for it in logs if it["id"] == delete_id), None)
        if delete_log is not None:
            delete_running_log_dialog(delete_log)