import datetime as dt
import os
import streamlit as st
from database import get_db
from utils import get_mime

UPLOAD_DIR = "uploaded_media"
os.makedirs(os.path.join(UPLOAD_DIR, "before"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "after"), exist_ok=True)


def render_media_page():
    st.markdown(
        """
        <style>
        .media-title {
            font-size: 15px; font-weight: 800; letter-spacing: 0.3em;
            color: #8B5E3C; text-transform: uppercase;
            padding-bottom: 8px; border-bottom: 1px solid #2C2A29;
            margin-bottom: 14px;
        }
        .media-name {
            font-size: 11px; font-weight: 700; color: #2C2A29;
            word-break: break-all; line-height: 1.3;
        }
        .media-meta {
            font-size: 10px; color: #8C8680;
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
        "<p style='color: #7A7570; font-size: 14px; margin-bottom: 25px;'>파일을 고르고 이름을 확인한 뒤 보관하세요. 아래 목록에서 다운로드와 삭제를 할 수 있습니다.</p>",
        unsafe_allow_html=True,
    )

    col_before, col_after = st.columns(2, gap="large")

    def render_media_box(box_title, sub_folder):
        with st.container(border=True):
            st.markdown(
                f"<div class='media-title'>{box_title}</div>",
                unsafe_allow_html=True,
            )

            uploaded_file = st.file_uploader(
                f"{box_title} 파일 선택",
                key=f"upl_{sub_folder}",
                label_visibility="collapsed",
            )

            if uploaded_file is not None:
                orig_name = uploaded_file.name
                base_name, ext = os.path.splitext(orig_name)

                new_name = st.text_input(
                    "저장할 파일명",
                    value=base_name,
                    key=f"name_{sub_folder}",
                )
                if st.button(
                    "보관하기",
                    key=f"save_{sub_folder}",
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
                            sub_folder,
                            final_name,
                            save_path,
                            dt.datetime.now().isoformat(),
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success("보관되었습니다.")
                    st.rerun()

            st.markdown(
                "<hr style='margin: 14px 0px; border:0.5px solid #E6E2DD;'>",
                unsafe_allow_html=True,
            )

            conn = get_db()
            items = conn.execute(
                "SELECT * FROM media_logs WHERE category = ? ORDER BY id DESC",
                (sub_folder,),
            ).fetchall()
            conn.close()

            if not items:
                st.caption("보관된 파일이 없습니다.")
                return

            with st.container(height=520, border=False):
                cols = st.columns(3)
                for i, item in enumerate(items):
                    exists = os.path.exists(item["saved_path"])
                    mime = get_mime(item["filename"])
                    with cols[i % 3]:
                        with st.container(border=True):
                            if exists and mime in (
                                "image/jpeg",
                                "image/png",
                            ):
                                st.image(item["saved_path"], width=110)
                            elif exists and mime == "video/mp4":
                                st.markdown(
                                    "<div style='font-size:24px;'>🎞</div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    "<div style='font-size:24px;'>📁</div>",
                                    unsafe_allow_html=True,
                                )

                            st.markdown(
                                f"<div class='media-name'>{item['filename']}</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"<div class='media-meta'>{item['uploaded_at'][:10]}</div>",
                                unsafe_allow_html=True,
                            )
                            b1, b2 = st.columns(2)
                            with b1:
                                if exists:
                                    with open(
                                        item["saved_path"], "rb"
                                    ) as file_data:
                                        st.download_button(
                                            label="받기",
                                            data=file_data,
                                            file_name=item["filename"],
                                            mime=mime,
                                            key=f"dl_{item['id']}",
                                            use_container_width=True,
                                        )
                            with b2:
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