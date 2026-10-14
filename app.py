import streamlit as st
from database import init_db
from views.home import render_category_selection, render_intro
from views.media import render_media_page
from views.running import render_running_page
from views.settings import THEMES, render_settings

# 페이지 기본 설정
st.set_page_config(
    page_title="DASOL",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 데이터베이스 초기화
init_db()

# Keep the selected theme in the URL so it survives page changes and reconnects.
if "theme_name" not in st.session_state:
    requested_theme = st.query_params.get("theme_name", "웜 아이보리")
    st.session_state.theme_name = (
        requested_theme if requested_theme in THEMES else "웜 아이보리"
    )
if "motion_enabled" not in st.session_state:
    st.session_state.motion_enabled = True
theme = THEMES.get(st.session_state.theme_name, THEMES["웜 아이보리"])
motion_duration = "220ms" if st.session_state.motion_enabled else "0ms"

# 공통 스타일 설정
st.markdown(
    """
    <style>
    :root {
        --dasol-background: __BACKGROUND__;
        --dasol-surface: __SURFACE__;
        --dasol-sidebar: __SIDEBAR__;
        --dasol-text: __TEXT__;
        --dasol-muted: __MUTED__;
        --dasol-accent: __ACCENT__;
        --dasol-accent-soft: __ACCENT_SOFT__;
        --dasol-border: __BORDER__;
        --dasol-button: __BUTTON__;
        --dasol-motion: __MOTION__;
    }
    footer, #MainMenu { display: none !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }

    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"], .stApp {
        background-color: var(--dasol-background) !important;
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
        color: var(--dasol-text) !important;
        line-height: 1.5;
    }
    h1, h2, h3, h4, p, span, div, button, input, textarea, select, label {
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
    }

    div[data-testid="stMetric"] {
        background-color: var(--dasol-surface);
        border: 1px solid var(--dasol-border);
        border-radius: 9px;
        padding: 10px 13px;
        box-shadow: 0 2px 8px rgba(44, 42, 41, 0.025);
    }
    div[data-testid="stMetric"] label {
        font-size: 12px !important;
        line-height: 1.35 !important;
        color: var(--dasol-muted) !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 21px !important;
        line-height: 1.25 !important;
        color: var(--dasol-text) !important;
        font-weight: 700 !important;
    }

    .stButton>button {
        background-color: var(--dasol-button);
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        padding: 6px 14px;
        font-size: 14px;
        transition: background-color var(--dasol-motion) ease,
                    color var(--dasol-motion) ease,
                    border-color var(--dasol-motion) ease,
                    transform var(--dasol-motion) ease,
                    box-shadow var(--dasol-motion) ease;
    }
    .stButton>button [data-testid="stMarkdownContainer"] {
        color: inherit !important;
    }
    .stButton>button:hover {
        background-color: var(--dasol-accent);
        color: #FFFFFF;
    }
    .stDownloadButton>button {
        background-color: var(--dasol-surface) !important;
        color: var(--dasol-text) !important;
        border: 1px solid var(--dasol-border) !important;
        font-size: 13px !important;
        white-space: nowrap !important;
        min-width: 64px !important;
        padding-left: 6px !important;
        padding-right: 6px !important;
    }
    .stDownloadButton>button:hover {
        border-color: var(--dasol-accent) !important;
    }

    input, textarea, select {
        background-color: var(--dasol-surface) !important;
        border: 1px solid var(--dasol-border) !important;
        border-radius: 6px !important;
        color: var(--dasol-text) !important;
    }
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {
        background-color: var(--dasol-background) !important;
        color: var(--dasol-text) !important;
    }
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] *,
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label p,
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] label p {
        color: var(--dasol-text) !important;
        opacity: 1 !important;
    }
    [data-testid="stAlert"] {
        background-color: var(--dasol-accent-soft) !important;
        border: 1px solid var(--dasol-border) !important;
        color: var(--dasol-text) !important;
    }
    [data-testid="stAlert"] * {
        color: var(--dasol-text) !important;
    }
    [data-testid="stSidebar"] {
        background-color: var(--dasol-sidebar) !important;
        border-right: 1px solid var(--dasol-border);
    }
    [data-testid="stFileUploaderDropzone"] button {
        position: relative !important;
        min-width: 110px !important;
        min-height: 36px !important;
        font-size: 0 !important;
        color: transparent !important;
        background: var(--dasol-button) !important;
        border: none !important;
        border-radius: 6px !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: var(--dasol-accent-soft) !important;
    }
    [data-testid="stFileUploaderDropzone"] button * {
        font-size: 0 !important;
        color: transparent !important;
    }
    [data-testid="stFileUploaderDropzone"] button::after {
        content: "파일 선택";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Pretendard', 'Malgun Gothic', sans-serif !important;
        font-size: 13px;
        color: #FFFFFF;
    }
    @media (prefers-reduced-motion: no-preference) {
        [data-testid="stMetric"] {
            transition: background-color var(--dasol-motion) ease,
                        border-color var(--dasol-motion) ease;
        }
    }

    .safe-text-block {
        word-break: break-all;
        overflow-wrap: break-word;
    }

    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: var(--dasol-sidebar) !important;
        border-right: 1px solid var(--dasol-border);
    }

    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stHeader"] button[aria-label*="sidebar" i] {
        position: relative !important;
        width: 40px !important;
        height: 40px !important;
        min-width: 40px !important;
        font-size: 0 !important;
        color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    [data-testid="collapsedControl"] button *,
    [data-testid="stSidebarCollapseButton"] button *,
    [data-testid="stSidebarCollapsedControl"] button *,
    [data-testid="stHeader"] button[aria-label*="sidebar" i] * {
        font-size: 0 !important;
        color: transparent !important;
    }
    [data-testid="collapsedControl"] button::after,
    [data-testid="stSidebarCollapseButton"] button::after,
    [data-testid="stSidebarCollapsedControl"] button::after,
    [data-testid="stHeader"] button[aria-label*="sidebar" i]::after {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        color: var(--dasol-text);
    }
    [data-testid="collapsedControl"] button::after,
    [data-testid="stSidebarCollapsedControl"] button::after,
    [data-testid="stHeader"] button[aria-label*="sidebar" i]::after { content: "☰"; }
    [data-testid="stSidebarCollapseButton"] button::after { content: "✕"; font-size: 16px; }
    </style>
    """
    .replace("__BACKGROUND__", theme["background"])
    .replace("__SURFACE__", theme["surface"])
    .replace("__SIDEBAR__", theme["sidebar"])
    .replace("__TEXT__", theme["text"])
    .replace("__MUTED__", theme["muted"])
    .replace("__ACCENT__", theme["accent"])
    .replace("__ACCENT_SOFT__", theme["accent_soft"])
    .replace("__BORDER__", theme["border"])
    .replace("__BUTTON__", theme["button"])
    .replace("__MOTION__", motion_duration),
    unsafe_allow_html=True,
)

# 세션 상태 초기화
if "current_page" not in st.session_state:
    st.session_state.current_page = None

# 0. 인트로 화면 처리
intro_ready = render_intro()

# ==========================================
# 사이드바 구성
# ==========================================
if intro_ready:
    with st.sidebar:
        st.markdown(
            """
            <style>
            .st-key-side_logo button {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                width: 100% !important;
                height: auto !important;
                min-height: 0 !important;
                padding: 6px 0 14px 0 !important;
            }
            .st-key-side_logo button:hover { background: transparent !important; }
            .st-key-side_logo button p:first-child {
                font-size: 1.3rem !important;
                font-weight: 800 !important;
                letter-spacing: 0.15em !important;
                color: var(--dasol-text) !important;
                margin: 0 !important;
            }
            .st-key-side_logo button p:last-child {
                font-size: 0.6rem !important;
                font-weight: 500 !important;
                letter-spacing: 0.3em !important;
                color: var(--dasol-muted) !important;
                margin: 2px 0 0 0 !important;
            }
            .st-key-side_run_wrap button,
            .st-key-side_media_wrap button,
            .st-key-side_settings_wrap button {
                background: var(--dasol-surface) !important;
                color: var(--dasol-text) !important;
                border: 1px solid var(--dasol-border) !important;
                border-radius: 8px !important;
                text-align: left !important;
                justify-content: flex-start !important;
                padding: 10px 12px !important;
                width: 100% !important;
                box-shadow: none !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                letter-spacing: 0.1em !important;
            }
            .st-key-side_run_wrap button:hover,
            .st-key-side_media_wrap button:hover,
            .st-key-side_settings_wrap button:hover {
                border-color: var(--dasol-accent) !important;
                transform: translateX(2px);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="side_logo"):
            if st.button(
                "DASOL\n\nFIND A MOMENT", key="side_home_btn", use_container_width=True
            ):
                st.session_state.current_page = None
                st.rerun()

        st.markdown(
            "<hr style='margin: 6px 0px 14px 0px; border:0.5px solid #E6E2DD;'>",
            unsafe_allow_html=True,
        )

        side_items = [
            ("러닝 일기", "side_run", "RUNNING DIARY"),
            ("미디어 보관함", "side_media", "MEDIA VAULT"),
        ]
        for label, key, sub in side_items:
            with st.container(key=f"{key}_wrap"):
                if st.button(sub, key=key, use_container_width=True):
                    st.session_state.current_page = label
                    st.rerun()
        st.markdown(
            "<hr style='margin: 14px 0px 10px 0px; border:0.5px solid var(--dasol-border);'>",
            unsafe_allow_html=True,
        )
        with st.container(key="side_settings_wrap"):
            if st.button("⚙  설정", key="side_settings", use_container_width=True):
                st.session_state.current_page = "설정"
                st.rerun()

    # ==========================================
    # 페이지 라우팅
    # ==========================================
    if st.session_state.current_page is None:
        render_category_selection()
    elif st.session_state.current_page == "러닝 일기":
        render_running_page()
    elif st.session_state.current_page == "미디어 보관함":
        render_media_page()
    elif st.session_state.current_page == "설정":
        render_settings()