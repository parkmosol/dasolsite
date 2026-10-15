import base64
from pathlib import Path

import streamlit as st


@st.cache_data(show_spinner=False)
def _load_category_images():
    image_dir = Path(__file__).resolve().parents[1] / "assets" / "category"
    filenames = {
        "running": "running.jpg",
        "media_vault": "media_vault.jpg",
        "photo_gallery": "photo_gallery.jpg",
        "place_archive": "place_archive.jpg",
    }
    return {
        category: base64.b64encode((image_dir / filename).read_bytes()).decode("ascii")
        for category, filename in filenames.items()
    }


def render_intro():
    if "intro_passed" not in st.session_state:
        st.session_state.intro_passed = False
    if "enter" in st.query_params:
        st.session_state.intro_passed = st.query_params.get("enter") == "true"
        del st.query_params["enter"]

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
                background-color: var(--dasol-background);
                z-index: 99999;
                pointer-events: none;
            }
            .st-key-intro_logo {
                position: fixed;
                z-index: 100000;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: max-content;
            }
            .st-key-intro_logo button {
                width: max-content !important;
                min-width: 0 !important;
                padding: 0 !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                transition: transform 0.2s ease !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
            }
            .st-key-intro_logo button:hover {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                transform: scale(1.02);
            }
            .st-key-intro_logo button p:first-child {
                font-size: 4.5rem !important;
                font-weight: 800 !important;
                letter-spacing: 0.15em !important;
                margin: 0 -0.15em 0 0 !important;
                line-height: 1.1 !important;
                text-align: center !important;
                background: linear-gradient(
                    120deg,
                    var(--dasol-text) 30%,
                    #FFFFFF 45%,
                    var(--dasol-accent-soft) 50%,
                    #FFFFFF 55%,
                    var(--dasol-text) 70%
                );
                background-size: 250% auto;
                color: transparent;
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: shineSweepRightToLeft 6s infinite cubic-bezier(0.25, 1, 0.5, 1);
                text-shadow: 2px 3px 12px rgba(44, 42, 41, 0.12);
            }
            .st-key-intro_logo button p:last-child {
                font-size: 0.78rem !important;
                font-weight: 500 !important;
                letter-spacing: 0.38em !important;
                color: var(--dasol-muted) !important;
                margin: -2px -0.38em 0 0 !important;
                text-align: center !important;
                opacity: 0.85; text-transform: uppercase;
            }
            </style>

            <div class="intro-wrapper">
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key="intro_logo"):
            if st.button(
                "DASOL\n\nFIND A MOMENT", key="enter_logo", use_container_width=False
            ):
                st.session_state.intro_passed = True
                st.rerun()

    return st.session_state.intro_passed


def render_category_selection():
    st.markdown(
        """
        <style>
        .main-logo { text-align: center; margin-top: 6vh; }
        .main-logo .logo-title {
            font-size: 4rem; font-weight: 800; letter-spacing: 0.2em;
            color: var(--dasol-text); margin: 0 -0.2em 0 0; line-height: 1.05;
        }
        .main-logo .logo-sub {
            font-size: 0.9rem; font-weight: 500; letter-spacing: 0.4em;
            color: var(--dasol-muted); margin: 10px -0.4em 0 0; text-transform: uppercase;
        }
        .category-head {
            width: 100%; max-width: 900px;
            margin: 7vh auto 22px auto; text-align: center;
        }
        .category-head .category-line {
            width: 100%; height: 0; border-top: 0.5px solid var(--dasol-border);
        }
        .category-head .category-title {
            font-size: 1.1rem; font-weight: 700; letter-spacing: 0.7em;
            color: var(--dasol-accent); margin: 8px 0; padding-left: 0.7em;
            text-transform: uppercase;
        }
        .st-key-category_grid {
            width: 100%;
            max-width: 680px;
            margin-left: auto !important;
            margin-right: auto !important;
        }

        .st-key-card_run button,
        .st-key-card_media button,
        .st-key-card_photo button,
        .st-key-card_place_archive button {
            width: 100% !important;
            min-width: 0 !important;
            max-width: 100% !important;
            height: 160px !important;
            min-height: 160px !important;
            max-height: 160px !important;
            background-color: rgba(255, 255, 255, 0.76) !important;
            color: var(--dasol-text) !important;
            border: 1px solid var(--dasol-border) !important;
            border-radius: 10px !important;
            box-shadow: 0 3px 10px rgba(44, 42, 41, 0.03) !important;
            transition: all var(--dasol-motion) ease !important;
            padding: 12px 8px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            white-space: nowrap !important;
            position: relative !important;
            isolation: isolate;
            -webkit-backdrop-filter: blur(8px);
            backdrop-filter: blur(8px);
        }
        .st-key-card_run button::before,
        .st-key-card_media button::before,
        .st-key-card_photo button::before,
        .st-key-card_place_archive button::before {
            content: "";
            position: absolute;
            inset: -18%;
            z-index: 0;
            pointer-events: none;
            filter: blur(1px);
            opacity: 0.9;
            transition: opacity var(--dasol-motion) ease,
                        transform var(--dasol-motion) ease;
        }
        .st-key-card_run button > div,
        .st-key-card_media button > div,
        .st-key-card_photo button > div,
        .st-key-card_place_archive button > div {
            position: relative;
            z-index: 1;
        }
        .st-key-card_run button:hover::before,
        .st-key-card_media button:hover::before,
        .st-key-card_photo button:hover::before,
        .st-key-card_place_archive button:hover::before {
            opacity: 1;
            transform: scale(1.05);
        }
        .st-key-card_run button:hover,
        .st-key-card_media button:hover,
        .st-key-card_photo button:hover,
        .st-key-card_place_archive button:hover {
            border-color: #2C2A29 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(44, 42, 41, 0.08) !important;
        }
        .st-key-card_run button svg,
        .st-key-card_media button svg,
        .st-key-card_photo button svg,
        .st-key-card_place_archive button svg,
        .st-key-card_run button [data-testid="stIconMaterial"],
        .st-key-card_media button [data-testid="stIconMaterial"],
        .st-key-card_photo button [data-testid="stIconMaterial"],
        .st-key-card_place_archive button [data-testid="stIconMaterial"] {
            display: none !important;
        }
        .st-key-card_run button p:first-child,
        .st-key-card_media button p:first-child,
        .st-key-card_photo button p:first-child,
        .st-key-card_place_archive button p:first-child {
            font-size: 14px !important;
            font-weight: 700 !important;
            letter-spacing: 0.07em !important;
            color: var(--dasol-text) !important;
            text-shadow: 0 1px 3px rgba(255, 255, 255, 0.7);
            margin: 0 0 6px 0 !important;
            white-space: nowrap !important;
        }
        .st-key-card_run button p:last-child,
        .st-key-card_media button p:last-child,
        .st-key-card_photo button p:last-child,
        .st-key-card_place_archive button p:last-child {
            font-size: 10px !important;
            font-weight: 400 !important;
            color: var(--dasol-text) !important;
            text-shadow: 0 1px 3px rgba(255, 255, 255, 0.85);
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
    category_images = _load_category_images()
    st.markdown(
        f"""
        <style>
        .st-key-card_run button::before {{
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.25)),
                url("data:image/jpeg;base64,{category_images['running']}");
            background-position: center;
            background-size: cover;
        }}
        .st-key-card_media button::before {{
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.25)),
                url("data:image/jpeg;base64,{category_images['media_vault']}");
            background-position: center;
            background-size: cover;
        }}
        .st-key-card_photo button::before {{
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.25)),
                url("data:image/jpeg;base64,{category_images['photo_gallery']}");
            background-position: center;
            background-size: cover;
        }}
        .st-key-card_place_archive button::before {{
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.25)),
                url("data:image/jpeg;base64,{category_images['place_archive']}");
            background-position: center;
            background-size: cover;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="category_grid"):
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
        b3, b4 = st.columns(2, gap="medium")
        with b3:
            with st.container(key="card_photo"):
                if st.button(
                    "PHOTO GALLERY\n\n렌즈로 담은 아름다움",
                    key="btn_photo_card",
                    use_container_width=True,
                ):
                    st.session_state.current_page = "사진관"
                    st.rerun()
        with b4:
            with st.container(key="card_place_archive"):
                if st.button(
                    "PLACE ARCHIVE\n\n설렘으로 적고, 온기로 채우다",
                    key="btn_place_archive_card",
                    use_container_width=True,
                ):
                    st.session_state.current_page = "PLACE ARCHIVE"
                    st.rerun()