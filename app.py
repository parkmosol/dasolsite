import streamlit as st
from database import init_db
from views.home import render_category_selection, render_intro
from views.media import render_media_page
from views.running import render_running_page

# 페이지 기본 설정
st.set_page_config(
    page_title="DASOL",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 데이터베이스 초기화
init_db()

# 공통 스타일 설정
st.markdown(
    """
    <style>
    footer, #MainMenu { display: none !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }

    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"], .stApp {
        background-color: #F7F5F0;
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
        color: #2C2A29;
        line-height: 1.5;
    }
    h1, h2, h3, h4, p, span, div, button, input, textarea, select, label {
        font-family: 'Pretendard', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E6E2DD;
        border-radius: 8px;
        padding: 12px 16px;
    }

    .stButton>button {
        background-color: #2C2A29;
        color: #F7F5F0;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        padding: 6px 14px;
        font-size: 14px;
    }
    .stButton>button:hover {
        background-color: #4A4745;
        color: #FFFFFF;
    }

    input, textarea, select {
        background-color: #FFFFFF !important;
        border: 1px solid #D6D0C7 !important;
        border-radius: 6px !important;
    }

    .safe-text-block {
        word-break: break-all;
        overflow-wrap: break-word;
    }

    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #FBFAF7 !important;
        border-right: 1px solid #E6E2DD;
    }

    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {
        position: relative !important;
        width: 40px !important;
        height: 40px !important;
        font-size: 0 !important;
        color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    [data-testid="collapsedControl"] button *,
    [data-testid="stSidebarCollapseButton"] button * {
        font-size: 0 !important;
        color: transparent !important;
    }
    [data-testid="collapsedControl"] button::after,
    [data-testid="stSidebarCollapseButton"] button::after {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        color: #2C2A29;
    }
    [data-testid="collapsedControl"] button::after { content: "☰"; }
    [data-testid="stSidebarCollapseButton"] button::after { content: "✕"; font-size: 16px; }

    [data-testid="stFileUploaderDropzone"] button {
        position: relative !important;
        font-size: 0 !important;
        color: transparent !important;
        background: #2C2A29 !important;
        border: none !important;
        min-width: 110px !important;
        min-height: 36px !important;
        border-radius: 6px !important;
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
        font-size: 13px;
        color: #F7F5F0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 세션 상태 초기화
if "current_page" not in st.session_state:
    st.session_state.current_page = None

# 0. 인트로 화면 처리
render_intro()

# ==========================================
# 사이드바 구성
# ==========================================
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
            color: #2C2A29 !important;
            margin: 0 !important;
        }
        .st-key-side_logo button p:last-child {
            font-size: 0.6rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.3em !important;
            color: #8C8680 !important;
            margin: 2px 0 0 0 !important;
        }
        .st-key-side_run_wrap button,
        .st-key-side_media_wrap button {
            background: #FFFFFF !important;
            color: #2C2A29 !important;
            border: 1px solid #E6E2DD !important;
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
        .st-key-side_media_wrap button:hover {
            border-color: #2C2A29 !important;
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

# ==========================================
# 페이지 라우팅
# ==========================================
if st.session_state.current_page is None:
    render_category_selection()
elif st.session_state.current_page == "러닝 일기":
    render_running_page()
elif st.session_state.current_page == "미디어 보관함":
    render_media_page()