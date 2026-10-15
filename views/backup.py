import hmac
from datetime import datetime

import streamlit as st

from backup_service import (
    build_backup_zip,
    preview_backup,
    restore_from_zip,
)


def _required_password():
    """st.secrets에 BACKUP_PASSWORD가 있을 때만 비밀번호를 요구한다."""
    try:
        value = st.secrets["BACKUP_PASSWORD"]
    except Exception:
        return None
    return str(value) if value else None


def _is_unlocked():
    expected = _required_password()
    if expected is None or st.session_state.get("backup_unlocked"):
        return True
    password = st.text_input("백업 비밀번호", type="password", key="backup_password_input")
    if st.button("확인", key="backup_unlock_button"):
        if hmac.compare_digest(password.encode("utf-8"), expected.encode("utf-8")):
            st.session_state.backup_unlocked = True
            st.rerun()
        st.error("비밀번호가 맞지 않습니다.")
    return False


def _render_backup_button():
    st.markdown("**백업 받기**")
    st.caption("버튼을 누를 때만 서버의 기록과 사진을 압축해서 PC에 바로 저장합니다.")
    
    # 버튼을 누를 때만 딱 한 번 작동하므로 서버에 부하를 주지 않습니다!
    if st.button("백업 받기 (PC에 저장)", type="primary", key="backup_action_button"):
        with st.spinner("백업 파일을 준비하는 중입니다..."):
            data = build_backup_zip()
        st.download_button(
            "📥 여기를 눌러서 다운로드 완료하기",
            data=data,
            file_name=f"dasol_backup_{datetime.now():%Y%m%d_%H%M%S}.zip",
            mime="application/zip",
            key="backup_download_button",
        )


def _render_restore():
    st.markdown("**백업으로 복구**")
    st.caption("다른 PC에서 받은 백업 zip을 올리고 복구 버튼을 누르면 그 내용으로 바뀝니다.")
    uploaded = st.file_uploader("백업 zip 올리기", type=["zip"], key="restore_zip_uploader")
    if uploaded is None:
        return

    data = uploaded.getvalue()
    try:
        manifest = preview_backup(data)
    except ValueError as error:
        st.error(str(error))
        return

    counts = manifest.get("counts", {})
    st.info(
        f"백업 시각: {manifest.get('created_at', '-')}\n\n"
        f"장소 {counts.get('place_archive', 0)}곳 · "
        f"여행 사진 {counts.get('place_archive_photos', 0)}장 · "
        f"사진관 {counts.get('photo_gallery', 0)}장 · "
        f"러닝 {counts.get('running_logs', 0)}건 · "
        f"미디어 {counts.get('media_logs', 0)}건"
    )
    st.warning(
        "복구하면 서버의 현재 기록과 사진이 이 백업 내용으로 바뀝니다. "
        "기존 데이터는 서버에 자동으로 남겨집니다."
    )
    if st.button("이 백업으로 복구", type="primary", key="restore_button"):
        try:
            with st.spinner("복구하는 중입니다..."):
                restore_from_zip(data)
        except ValueError as error:
            st.error(str(error))
            return
        st.cache_data.clear()
        st.success("복구가 끝났습니다. 브라우저에서 새로고침(F5)해 주세요.")


def render_backup_section():
    st.divider()
    st.subheader("백업 · 복구")
    if not _is_unlocked():
        return
    _render_backup_button()
    st.divider()
    _render_restore()