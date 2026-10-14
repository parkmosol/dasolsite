import datetime as dt
import os
import streamlit as st
from database import get_db
from utils import get_mime

UPLOAD_DIR = "uploaded_media"
PHOTO_EXTENSIONS = ["jpg", "jpeg", "png", "jxl", "cr2", "nef", "arw", "dng", "raw"]
VIDEO_EXTENSIONS = ["mp4", "mov", "avi", "mkv"]
os.makedirs(os.path.join(UPLOAD_DIR, "before"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "after"), exist_ok=True)


def render_media_page():
    st.markdown(
        """
        <style>
        .media-title {
            font-size: 15px; font-weight: 800; letter-spacing: 0.3em;
            color: var(--dasol-accent); text-transform: uppercase;
            padding-bottom: 8px; border-bottom: 1px solid var(--dasol-text);
            margin-bottom: 14px;
        }
        .media-name {
            font-size: 13px; font-weight: 700; color: var(--dasol-text);
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            line-height: 1.3;
        }
        .media-meta {
            font-size: 11px; color: var(--dasol-muted);
        }
        div[data-testid="stImage"] img {
            width: 64px !important;
            height: 56px !important;
            object-fit: cover !important;
        }
        div[class*="st-key-del_"] button {
            min-width: 64px !important;
            padding-left: 6px !important;
            padding-right: 6px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 style='font-weight: 800; font-size: 26px; margin-top: 0;'>미디어 보관함</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #7A7570; font-size: 14px; margin-bottom: 25px;'>사진과 영상 보관함이 각각 분리되어 있습니다. 파일을 업로드하고 관리하세요.</p>",
        unsafe_allow_html=True,
    )

    selected_type = st.radio(
        "보관함 종류",
        ["사진 보관함", "영상 보관함"],
        horizontal=True,
        label_visibility="collapsed",
        key="media_vault_type",
    )
    media_type = "video" if selected_type == "영상 보관함" else "photo"
    allowed_extensions = VIDEO_EXTENSIONS if media_type == "video" else PHOTO_EXTENSIONS
    col_before, col_after = st.columns(2, gap="large")

    def render_media_box(box_title, sub_folder):
        with st.container(border=True):
            st.markdown(
                f"<div class='media-title'>{box_title}</div>",
                unsafe_allow_html=True,
            )

            upload_key = f"{sub_folder}_{media_type}"
            generation_key = f"media_upload_generation_{upload_key}"
            generation = st.session_state.get(generation_key, 0)
            uploaded_file = st.file_uploader(
                f"{box_title} {selected_type} 파일 선택",
                type=allowed_extensions,
                key=f"upl_{upload_key}_{generation}",
            )

            if uploaded_file is not None:
                orig_name = uploaded_file.name
                base_name, ext = os.path.splitext(orig_name)

                new_name = st.text_input(
                    "저장할 파일명",
                    value=base_name,
                    key=f"name_{upload_key}_{generation}",
                )
                if st.button(
                    "보관하기",
                    key=f"save_{upload_key}_{generation}",
                    type="primary",
                    use_container_width=True,
                ):
                    final_name = (new_name.strip() or base_name) + ext
                    save_path = os.path.join(
                        UPLOAD_DIR,
                        sub_folder,
                        f"{dt.datetime.now().timestamp()}_{final_name}",
                    )
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    conn = get_db()
                    conn.execute(
                        """
                        INSERT INTO media_logs(category, filename, saved_path, uploaded_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            f"{sub_folder}_{media_type}",
                            final_name,
                            save_path,
                            dt.datetime.now().isoformat(),
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.session_state[generation_key] = generation + 1
                    st.success("보관되었습니다.")
                    st.rerun()

            st.markdown(
                "<hr style='margin: 14px 0px; border:0.5px solid var(--dasol-border);'>",
                unsafe_allow_html=True,
            )

            conn = get_db()
            items = conn.execute(
                """
                SELECT * FROM media_logs
                WHERE category IN (?, ?, ?)
                ORDER BY id DESC
                """,
                (sub_folder, f"{sub_folder}_photo", f"{sub_folder}_video"),
            ).fetchall()
            conn.close()
            extensions = (
                {f".{extension}" for extension in VIDEO_EXTENSIONS}
                if media_type == "video"
                else {f".{extension}" for extension in PHOTO_EXTENSIONS}
            )
            items = [
                item
                for item in items
                if os.path.splitext(item["filename"])[1].lower() in extensions
            ]

            if not items:
                st.caption("보관된 파일이 없습니다.")
                return

            # Keep each file in a compact row for quick scanning.
            with st.container(height=520, border=False):
                for item in items:
                    exists = os.path.exists(item["saved_path"])
                    mime = get_mime(item["filename"])

                    with st.container(border=True):
                        preview_col, info_col, download_col, delete_col = st.columns(
                            [0.8, 2.4, 1.4, 1.4],
                            vertical_alignment="center",
                            gap="small",
                        )
                        with preview_col:
                            if exists and mime in ("image/jpeg", "image/png"):
                                st.image(item["saved_path"], width=64)
                            elif media_type == "video":
                                st.markdown("### 🎞")
                            else:
                                st.markdown("### 📁")
                        with info_col:
                            st.markdown(
                                f"<div class='media-name'>{item['filename']}</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"<div class='media-meta'>{item['uploaded_at'][:10]}</div>",
                                unsafe_allow_html=True,
                            )
                        with download_col:
                            if exists:
                                with open(item["saved_path"], "rb") as file_data:
                                    st.download_button(
                                        label="받기",
                                        data=file_data,
                                        file_name=item["filename"],
                                        mime=mime,
                                        key=f"dl_{item['id']}",
                                        use_container_width=True,
                                    )
                        with delete_col:
                            if st.button(
                                "삭제",
                                key=f"del_{item['id']}",
                                use_container_width=True,
                            ):
                                conn = get_db()
                                conn.execute(
                                    "DELETE FROM media_logs WHERE id = ?",
                                    (item["id"],),
                                )
                                conn.commit()
                                conn.close()
                                if exists:
                                    try:
                                        os.remove(item["saved_path"])
                                    except OSError:
                                        pass
                                st.rerun()

    with col_before:
        render_media_box("BEFORE", "before")

    with col_after:
        render_media_box("AFTER", "after")