import streamlit as st


def render_intro():
    if "intro_passed" not in st.session_state:
        st.session_state.intro_passed = False

    if not st.session_state.intro_passed:
        st.markdown(
            """
            <style>
            @keyframes shineSweepRightToLeft {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
            .intro-wrapper {
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                display: flex; flex-direction: column;
                align-items: center; justify-content: center;
                background-color: #F7F5F0;
                z-index: 99999;
            }
            .dasol-logo-box {
                display: flex; flex-direction: column;
                align-items: center; text-align: center;
            }
            .dasol-logo-link {
                font-size: 4.5rem !important;
                font-weight: 800 !important;
                letter-spacing: 0.15em !important;
                text-decoration: none !important;
                margin-bottom: 2px !important;
                display: inline-block;
                background: linear-gradient(120deg, #2C2A29 30%, #FFFFFF 45%, #E8DCC4 50%, #FFFFFF 55%, #2C2A29 70%);
                background-size: 250% auto;
                color: transparent;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: shineSweepRightToLeft 6.0s infinite cubic-bezier(0.25, 1, 0.5, 1);
                text-shadow: 2px 3px 12px rgba(44, 42, 41, 0.12);
            }
            .dasol-logo-link:hover {
                transform: scale(1.02);
                transition: transform 0.2s ease;
            }
            .dasol-sub-text {
                font-size: 0.78rem; font-weight: 500;
                letter-spacing: 0.38em; color: #8C8680;
                margin-right: -0.38em; margin-top: -4px;
                opacity: 0.85; text-transform: uppercase;
            }
            </style>

            <div class="intro-wrapper">
                <div class="dasol-logo-box">
                    <a href="?enter=true" class="dasol-logo-link">DASOL</a>
                    <div class="dasol-sub-text">FIND A MOMENT</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        query_params = st.query_params
        if "enter" in query_params:
            st.session_state.intro_passed = True
            st.query_params.clear()
            st.rerun()

        st.stop()


def render_category_selection():
    st.markdown(
        """
        <style>
        .main-logo { text-align: center; margin-top: 6vh; }
        .main-logo .logo-title {
            font-size: 4rem; font-weight: 800; letter-spacing: 0.2em;
            color: #2C2A29; margin: 0; line-height: 1.05;
        }
        .main-logo .logo-sub {
            font-size: 0.9rem; font-weight: 500; letter-spacing: 0.4em;
            color: #8C8680; margin: 10px 0 0 0; text-transform: uppercase;
        }
        .category-head {
            width: 100%; max-width: 900px;
            margin: 7vh auto 22px auto; text-align: center;
        }
        .category-head .category-line {
            width: 100%; height: 0; border-top: 0.5px solid #C9C2B8;
        }
        .category-head .category-title {
            font-size: 1.1rem; font-weight: 700; letter-spacing: 0.7em;
            color: #8B5E3C; margin: 8px 0; padding-left: 0.7em;
            text-transform: uppercase;
        }

        .st-key-card_run button,
        .st-key-card_media button {
            width: 400px !important;
            max-width: 100% !important;
            height: 120px !important;
            min-height: 120px !important;
            max-height: 120px !important;
            background-color: #FFFFFF !important;
            color: #2C2A29 !important;
            border: 1px solid #E6E2DD !important;
            border-radius: 10px !important;
            box-shadow: 0 3px 10px rgba(44, 42, 41, 0.03) !important;
            transition: all 0.25s ease !important;
            padding: 12px 16px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            white-space: nowrap !important;
        }
        .st-key-card_run button:hover,
        .st-key-card_media button:hover {
            border-color: #2C2A29 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(44, 42, 41, 0.08) !important;
        }
        .st-key-card_run button p:first-child,
        .st-key-card_media button p:first-child {
            font-size: 16px !important;
            font-weight: 700 !important;
            letter-spacing: 0.14em !important;
            color: #2C2A29 !important;
            margin: 0 0 6px 0 !important;
            white-space: nowrap !important;
        }
        .st-key-card_run button p:last-child,
        .st-key-card_media button p:last-child {
            font-size: 12px !important;
            font-weight: 400 !important;
            color: #8C8680 !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }
        </style>

        <div class="main-logo">
            <p class="logo-title">DASOL</p>
            <p class="logo-sub">FIND A MOMENT</p>
        </div>

        <div class="category-head">
            <div class="category-line"></div>
            <p class="category-title">CATEGORY</p>
            <div class="category-line"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        b1, b2 = st.columns(2, gap="medium")
        with b1:
            with st.container(key="card_run"):
                if st.button(
                    "RUNNING DIARY\n\n러닝 거리와 페이스 기록",
                    key="btn_run_card",
                    use_container_width=True,
                ):
                    st.session_state.current_page = "러닝 일기"
                    st.rerun()
        with b2:
            with st.container(key="card_media"):
                if st.button(
                    "MEDIA VAULT\n\n사진 및 영상 이동보관",
                    key="btn_media_card",
                    use_container_width=True,
                ):
                    st.session_state.current_page = "미디어 보관함"
                    st.rerun()