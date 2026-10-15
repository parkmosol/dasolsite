import streamlit as st

THEMES = {
    "웜 아이보리": {
        "background": "#F7F5F0",
        "surface": "#FFFFFF",
        "sidebar": "#FBFAF7",
        "text": "#2C2A29",
        "muted": "#8C8680",
        "accent": "#8B5E3C",
        "accent_soft": "#EFE6DA",
        "border": "#E6E2DD",
        "button": "#3D342F",
    },
    "세이지 가든": {
        "background": "#F2F5F0",
        "surface": "#FFFFFF",
        "sidebar": "#F7F9F5",
        "text": "#28352D",
        "muted": "#748278",
        "accent": "#52745C",
        "accent_soft": "#E5EDE5",
        "border": "#DCE5DC",
        "button": "#405F49",
    },
    "오션 미스트": {
        "background": "#F0F5F8",
        "surface": "#FFFFFF",
        "sidebar": "#F7FAFC",
        "text": "#273640",
        "muted": "#748995",
        "accent": "#47788E",
        "accent_soft": "#E3EEF2",
        "border": "#DCE7EC",
        "button": "#365F73",
    },
    "로즈 쿼츠": {
        "background": "#FAF3F5",
        "surface": "#FFFFFF",
        "sidebar": "#FDF8F9",
        "text": "#3D2D34",
        "muted": "#927D86",
        "accent": "#9A5F75",
        "accent_soft": "#F3E5EA",
        "border": "#EEDDE4",
        "button": "#704454",
    },
    "미드나잇": {
        "background": "#171E2B",
        "surface": "#222C3D",
        "sidebar": "#1C2534",
        "text": "#EDF1F7",
        "muted": "#AAB5C5",
        "accent": "#B49AF2",
        "accent_soft": "#343148",
        "border": "#3A4658",
        "button": "#7561B4",
    },
}

DAILY_NOTES = [
    "오늘의 한 걸음도 충분히 멋져요.",
    "빠르기보다, 다시 나선 마음이 중요해요.",
    "나만의 페이스로 오늘을 채워 보세요.",
    "달린 거리만큼 좋은 순간도 쌓이고 있어요.",
    "완벽한 날보다 꾸준한 하루를 응원해요.",
]


def render_settings():
    st.markdown(
        "<h1 style='font-weight:800;font-size:26px;margin-top:0;'>SETTING</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "나에게 잘 어울리는 DASOL의 분위기를 골라 보세요.",
        help="테마와 모션 설정은 현재 브라우저 세션에 적용됩니다.",
    )

    st.markdown("### 화면 테마")
    st.selectbox(
        "테마 색상",
        options=list(THEMES),
        key="theme_name",
        bind="query-params",
        label_visibility="collapsed",
    )

    st.markdown(
        """
        <style>
        .theme-preview {
            display: flex; align-items: center; gap: 12px;
            padding: 16px; border: 1px solid var(--dasol-border);
            border-radius: 10px; background: var(--dasol-surface);
        }
        .theme-preview-swatch {
            width: 26px; height: 26px; border-radius: 50%;
            border: 1px solid var(--dasol-border);
        }
        .settings-note {
            color: var(--dasol-muted); font-size: 13px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    theme = THEMES[st.session_state.get("theme_name", "웜 아이보리")]
    st.markdown(
        f"""
        <div class="theme-preview">
            <span class="theme-preview-swatch" style="background:{theme['background']}"></span>
            <span class="theme-preview-swatch" style="background:{theme['accent']}"></span>
            <span class="theme-preview-swatch" style="background:{theme['button']}"></span>
            <span>{st.session_state.get('theme_name', '웜 아이보리')}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='settings-note'>선택한 색상은 이 브라우저 세션에 적용됩니다.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("### 모션 효과")
    st.toggle(
        "부드러운 화면 전환과 버튼 반응 사용",
        key="motion_enabled",
        help="움직임을 줄이고 싶을 때 끌 수 있습니다.",
    )

    st.markdown("### 오늘의 러닝 한마디")
    quote_index = st.session_state.get("daily_note_index", 0)
    st.info(DAILY_NOTES[quote_index % len(DAILY_NOTES)])
    if st.button("다른 한마디 보기", key="new_daily_note"):
        st.session_state.daily_note_index = (quote_index + 1) % len(DAILY_NOTES)
        st.rerun()