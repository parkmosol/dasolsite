import datetime as dt
import streamlit as st
from database import get_db
from utils import calc_pace, parse_km, parse_time_str

TODAY = dt.date.today()


@st.dialog("코스 관리")
def course_manager_dialog(courses_list):
    new_course_name = st.text_input("새 코스 이름 (예: 보문산 코스 (7km))")
    if st.button("코스 추가", use_container_width=True):
        if new_course_name.strip():
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO courses(name) VALUES (?)",
                    (new_course_name.strip(),),
                )
                conn.commit()
                conn.close()
                st.success("코스가 추가되었습니다.")
                st.rerun()
            except Exception:
                st.error("이미 존재하는 코스이거나 형식이 잘못되었습니다.")

    if courses_list:
        st.markdown(
            "<hr style='margin: 12px 0px; border:0.5px solid #E6E2DD;'>",
            unsafe_allow_html=True,
        )
        del_course = st.selectbox("삭제할 코스 선택", courses_list)
        if st.button("선택 코스 삭제", use_container_width=True):
            conn = get_db()
            conn.execute("DELETE FROM courses WHERE name = ?", (del_course,))
            conn.commit()
            conn.close()
            st.success("코스가 삭제되었습니다.")
            st.rerun()


def render_running_page():
    st.markdown(
        "<h1 style='font-weight: 800; font-size: 26px; margin-top: 0;'>러닝 일기</h1>",
        unsafe_allow_html=True,
    )
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][TODAY.weekday()]
    st.markdown(
        f"<p style='color: #7A7570; font-size: 14px; margin-bottom: 20px;'>{TODAY.strftime('%Y.%m.%d')} ({weekday_str})</p>",
        unsafe_allow_html=True,
    )

    conn = get_db()
    courses_row = conn.execute("SELECT * FROM courses").fetchall()
    courses_list = [r["name"] for r in courses_row]
    logs = conn.execute(
        "SELECT * FROM running_logs ORDER BY date DESC"
    ).fetchall()
    conn.close()

    mon = TODAY - dt.timedelta(days=TODAY.weekday())
    sun = mon + dt.timedelta(days=6)
    prefix = TODAY.strftime("%Y-%m")

    week_km = sum(
        parse_km(it["course"])
        for it in logs
        if mon <= dt.date.fromisoformat(it["date"]) <= sun
    )
    month_cnt = sum(1 for it in logs if it["date"].startswith(prefix))
    total_km = sum(parse_km(it["course"]) for it in logs)

    dates = {it["date"] for it in logs}
    cur_d = TODAY if TODAY.isoformat() in dates else TODAY - dt.timedelta(days=1)
    streak = 0
    while cur_d.isoformat() in dates:
        streak += 1
        cur_d -= dt.timedelta(days=1)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("이번 주 거리", f"{week_km:.1f} km")
    with c2:
        st.metric("이번 달 러닝", f"{month_cnt}회")
    with c3:
        st.metric("누적 거리", f"{total_km:.1f} km")
    with c4:
        st.metric("연속 러닝", f"{streak}일째")

    st.markdown("<hr style='border:0.5px solid #E6E2DD;'>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .st-key-course_gear button {
            width: 44px !important;
            min-width: 44px !important;
            height: 44px !important;
            padding: 0 !important;
            font-size: 24px !important;
            background: transparent !important;
            color: #2C2A29 !important;
            border: none !important;
            box-shadow: none !important;
        }
        .st-key-course_gear button:hover {
            background: transparent !important;
            color: #8B5E3C !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    t_col1, t_col2, t_col3, t_col4 = st.columns(
        [3, 0.5, 1.5, 0.01], vertical_alignment="center", gap="small"
    )
    with t_col1:
        filter_course = st.selectbox(
            "코스 필터", ["전체 코스"] + courses_list, label_visibility="collapsed"
        )
    with t_col2:
        with st.container(key="course_gear"):
            if st.button("⚙", key="btn_course_gear", help="코스 관리"):
                course_manager_dialog(courses_list)
    with t_col3:
        if st.button("+ 기록 추가", use_container_width=True):
            st.session_state.show_add_modal = True

    if st.session_state.get("show_add_modal", False):
        with st.form("run_add_form"):
            st.markdown("### 새로운 러닝 기록")
            r_date = st.date_input("날짜", TODAY)
            r_course = (
                st.selectbox("코스 선택", courses_list)
                if courses_list
                else st.text_input("코스 입력")
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
                else:
                    pace = calc_pace(r_course, sec)
                    conn = get_db()
                    conn.execute(
                        """
                        INSERT INTO running_logs(date, mood, course, time_sec, pace, memo)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r_date.isoformat(),
                            r_mood,
                            r_course,
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
        if filter_course == "전체 코스" or it["course"] == filter_course
    ]
    filtered_logs.sort(key=lambda x: x["date"], reverse=True)

    mood_colors = {
        "GREAT": "#1F8A5B",
        "GOOD": "#3E7FC4",
        "SO SO": "#B8860B",
        "BAD": "#D9782D",
        "TERRIBLE": "#C8443F",
    }

    if filtered_logs:
        st.markdown(
            """
            <div style='display:flex; justify-content:space-between; align-items:center; color:#7A7570; font-size:13px; font-weight:700; padding: 10px 0px; border-bottom: 1px solid #E6E2DD;'>
                <div style='width:15%; text-align:center;'>날짜</div>
                <div style='width:25%; text-align:center;'>코스</div>
                <div style='width:10%; text-align:center;'>기분</div>
                <div style='width:15%; text-align:center;'>시간</div>
                <div style='width:15%; text-align:center;'>페이스</div>
                <div style='width:20%; text-align:center;'>메모</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for it in filtered_logs:
            m_col = mood_colors.get(it["mood"], "#2C2A29")
            m_sec, s_sec = divmod(it["time_sec"], 60)
            h_sec, m_sec = divmod(m_sec, 60)
            t_str = (
                f"{h_sec:02d}:{m_sec:02d}:{s_sec:02d}"
                if h_sec
                else f"{m_sec:02d}:{s_sec:02d}"
            )
            memo_text = it["memo"] if it["memo"] else "-"

            st.markdown(
                f"""
                <div style='display:flex; justify-content:space-between; align-items:center; font-size:14px; padding: 12px 0px; border-bottom: 1px solid #EFECE6;'>
                    <div class='safe-text-block' style='width:15%; text-align:center;'>{it['date']}</div>
                    <div class='safe-text-block' style='width:25%; text-align:center;'>{it['course']}</div>
                    <div class='safe-text-block' style='width:10%; text-align:center; color:{m_col}; font-weight:700;'>{it['mood']}</div>
                    <div class='safe-text-block' style='width:15%; text-align:center;'>{t_str}</div>
                    <div class='safe-text-block' style='width:15%; text-align:center;'>{it['pace']}</div>
                    <div class='safe-text-block' style='width:20%; text-align:center; color:#7A7570;'>{memo_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("등록된 러닝 기록이 없습니다.")