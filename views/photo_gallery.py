import base64
import datetime as dt
import hashlib
import html
import io
import os
import sqlite3
import uuid
from urllib.parse import urlencode

import streamlit as st
from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

from database import get_db

PHOTO_DIR = os.path.join("uploaded_media", "photo_gallery")
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
os.makedirs(PHOTO_DIR, exist_ok=True)


@st.cache_data(show_spinner=False, max_entries=128)
def _photo_preview_data(saved_path, modified_ns):
    with Image.open(saved_path) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            rgba_image = image.convert("RGBA")
            image = Image.new("RGB", rgba_image.size, "#F7F5F0")
            image.paste(rgba_image, mask=rgba_image.getchannel("A"))
        else:
            image = image.convert("RGB")
        preview = io.BytesIO()
        image.save(preview, format="JPEG", quality=94, optimize=True)
    return base64.b64encode(preview.getvalue()).decode("ascii")


def _gps_decimal(coordinates, reference):
    try:
        degrees, minutes, seconds = (float(part) for part in coordinates)
        decimal = degrees + minutes / 60 + seconds / 3600
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if reference in ("S", "W"):
        decimal = -decimal
    return decimal


def _extract_photo_metadata(uploaded_file):
    metadata = {
        "shot_date": dt.date.today(),
        "location": "",
        "iso": "",
        "shutter_speed": "",
        "aperture": "",
    }
    try:
        with Image.open(io.BytesIO(uploaded_file.getvalue())) as image:
            exif = image.getexif()
            tags = {
                ExifTags.TAGS.get(tag, tag): value
                for tag, value in exif.items()
            }
            exif_info = {
                ExifTags.TAGS.get(tag, tag): value
                for tag, value in exif.get_ifd(ExifTags.IFD.Exif).items()
            }
            tags.update(exif_info)
            date_value = (
                tags.get("DateTimeOriginal")
                or tags.get("DateTimeDigitized")
                or tags.get("DateTime")
            )
            if isinstance(date_value, bytes):
                date_value = date_value.decode("ascii", errors="replace")
            if date_value:
                try:
                    metadata["shot_date"] = dt.datetime.strptime(
                        str(date_value).strip("\x00"),
                        "%Y:%m:%d %H:%M:%S",
                    ).date()
                except ValueError:
                    pass

            iso_value = tags.get("ISOSpeedRatings", tags.get("PhotographicSensitivity"))
            if iso_value is not None:
                if isinstance(iso_value, (tuple, list)):
                    iso_value = iso_value[0] if iso_value else None
                if iso_value is not None:
                    metadata["iso"] = str(iso_value)

            exposure = tags.get("ExposureTime")
            if exposure is not None:
                numerator = getattr(exposure, "numerator", None)
                denominator = getattr(exposure, "denominator", None)
                if numerator and denominator and numerator < denominator:
                    metadata["shutter_speed"] = f"{numerator}/{denominator}s"
                else:
                    exposure_seconds = float(exposure)
                    metadata["shutter_speed"] = f"{exposure_seconds:g}s"

            f_number = tags.get("FNumber")
            if f_number is not None:
                metadata["aperture"] = f"f/{float(f_number):g}"

            gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)
            gps = {
                ExifTags.GPSTAGS.get(tag, tag): value
                for tag, value in gps_info.items()
            }
            latitude_reference = gps.get("GPSLatitudeRef")
            longitude_reference = gps.get("GPSLongitudeRef")
            if isinstance(latitude_reference, bytes):
                latitude_reference = latitude_reference.decode("ascii", errors="ignore")
            if isinstance(longitude_reference, bytes):
                longitude_reference = longitude_reference.decode("ascii", errors="ignore")
            latitude = _gps_decimal(
                gps.get("GPSLatitude"), latitude_reference
            )
            longitude = _gps_decimal(
                gps.get("GPSLongitude"), longitude_reference
            )
            if latitude is not None and longitude is not None:
                metadata["location"] = f"{latitude:.5f}, {longitude:.5f}"
    except (OSError, UnidentifiedImageError) as error:
        raise ValueError("유효한 사진 파일을 선택해 주세요.") from error
    return metadata


def _store_photo(uploaded_file):
    extension = os.path.splitext(uploaded_file.name)[1].lower().lstrip(".")
    if extension not in PHOTO_EXTENSIONS:
        raise ValueError("JPG, PNG, WEBP 형식의 사진만 등록할 수 있습니다.")
    try:
        with Image.open(io.BytesIO(uploaded_file.getvalue())) as image:
            image.verify()
    except (OSError, UnidentifiedImageError) as error:
        raise ValueError("유효한 사진 파일을 선택해 주세요.") from error
    filename = f"{uuid.uuid4().hex}.{extension}"
    saved_path = os.path.join(PHOTO_DIR, filename)
    with open(saved_path, "wb") as photo_file:
        photo_file.write(uploaded_file.getbuffer())
    return filename, saved_path


def _render_clickable_preview(photo):
    modified_ns = os.stat(photo["saved_path"]).st_mtime_ns
    preview_data = _photo_preview_data(photo["saved_path"], modified_ns)
    query_params = dict(st.query_params)
    query_params["photo_id"] = str(photo["id"])
    href = html.escape(f"?{urlencode(query_params)}", quote=True)
    alt = html.escape(photo["title"], quote=True)
    st.html(
        f"""
        <a href="{href}" aria-label="사진 보기: {alt}"
           style="display:block; cursor:zoom-in; overflow:hidden;">
            <img src="data:image/jpeg;base64,{preview_data}" alt="{alt}"
                 style="display:block; width:100%; height:auto; transition:transform 260ms ease, opacity 260ms ease;">
        </a>
        """,
        width="stretch",
    )


def _render_photo_editor(photo):
    with st.container(key=f"photo_editor_{photo['id']}"):
        with st.expander("사진 정보 수정"):
            with st.form(f"edit_photo_{photo['id']}"):
                title = st.text_input("제목", photo["title"])
                shot_date = st.date_input(
                    "촬영 날짜",
                    dt.date.fromisoformat(photo["shot_date"]),
                    key=f"edit_photo_date_{photo['id']}",
                )
                location = st.text_input(
                    "촬영 장소",
                    photo["location"] or "",
                    key=f"edit_photo_location_{photo['id']}",
                )
                description = st.text_area(
                    "사진 설명",
                    photo["description"] or "",
                    key=f"edit_photo_description_{photo['id']}",
                )
                iso_col, shutter_col, aperture_col = st.columns(3)
                with iso_col:
                    iso = st.text_input(
                        "ISO",
                        photo["iso"] or "",
                        key=f"edit_photo_iso_{photo['id']}",
                    )
                with shutter_col:
                    shutter_speed = st.text_input(
                        "셔터 스피드",
                        photo["shutter_speed"] or "",
                        key=f"edit_photo_shutter_{photo['id']}",
                        placeholder="예: 1/250s",
                    )
                with aperture_col:
                    aperture = st.text_input(
                        "조리개 값",
                        photo["aperture"] or "",
                        key=f"edit_photo_aperture_{photo['id']}",
                        placeholder="예: f/2.8",
                    )
                save = st.form_submit_button("변경 저장", type="primary")

        if save:
            if not title.strip():
                st.error("사진 제목을 입력해 주세요.")
                return

            conn = get_db()
            try:
                conn.execute(
                    """
                    UPDATE photo_gallery
                    SET title = ?, shot_date = ?, location = ?, description = ?,
                        iso = ?, shutter_speed = ?, aperture = ?
                    WHERE id = ?
                    """,
                    (
                        title.strip(),
                        shot_date.isoformat(),
                        location.strip(),
                        description.strip(),
                        iso.strip(),
                        shutter_speed.strip(),
                        aperture.strip(),
                        photo["id"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            st.success("사진 정보가 수정되었습니다.")
            st.rerun()


def _render_photo_view(photos, selected_index):
    photo = photos[selected_index]
    header_left, header_right = st.columns([1, 1], vertical_alignment="center")
    with header_left:
        if st.button("GALLERY", key="photo_gallery_back"):
            st.session_state.pop("selected_photo_id", None)
            if "photo_id" in st.query_params:
                del st.query_params["photo_id"]
            st.rerun()
    with header_right:
        st.markdown(
            (
                f"<p class='photo-view-index'>{selected_index + 1:02d}"
                f" <span>/ {len(photos):02d}</span></p>"
            ),
            unsafe_allow_html=True,
        )

    direction = st.session_state.get("photo_direction", "next")
    nav_previous, viewer, nav_next = st.columns(
        [1, 14, 1],
        gap="small",
        vertical_alignment="center",
    )
    with nav_previous:
        if st.button(
            "‹",
            key="photo_previous",
            disabled=selected_index == 0,
            width="stretch",
            help="이전 사진",
        ):
            st.session_state.photo_direction = "previous"
            st.session_state.selected_photo_id = photos[selected_index - 1]["id"]
            st.query_params["photo_id"] = str(photos[selected_index - 1]["id"])
            st.rerun()
    with viewer:
        with st.container(key=f"photo_view_slide_{direction}"):
            if os.path.exists(photo["saved_path"]):
                st.image(
                    photo["saved_path"],
                    alt=photo["title"],
                    width="stretch",
                )
            else:
                st.error("사진 파일을 찾을 수 없습니다.")
    with nav_next:
        if st.button(
            "›",
            key="photo_next",
            disabled=selected_index == len(photos) - 1,
            width="stretch",
            help="다음 사진",
        ):
            st.session_state.photo_direction = "next"
            st.session_state.selected_photo_id = photos[selected_index + 1]["id"]
            st.query_params["photo_id"] = str(photos[selected_index + 1]["id"])
            st.rerun()

    with st.container(key="photo_view_caption"):
        st.markdown(
            f"<h2 class='photo-view-title'>{html.escape(photo['title'])}</h2>",
            unsafe_allow_html=True,
        )
        caption = "  ·  ".join(
            value for value in (photo["shot_date"], photo["location"] or "") if value
        )
        if caption:
            st.markdown(
                f"<p class='photo-view-meta'>{html.escape(caption)}</p>",
                unsafe_allow_html=True,
            )
        if photo["description"]:
            st.markdown(
                f"<p class='photo-view-description'>"
                f"{html.escape(photo['description']).replace(chr(10), '<br>')}"
                "</p>",
                unsafe_allow_html=True,
            )
        exposure = [
            f"ISO {photo['iso']}" if photo["iso"] else None,
            photo["shutter_speed"] or None,
            photo["aperture"] or None,
        ]
        exposure = [value for value in exposure if value]
        if exposure:
            st.markdown(
                f"<p class='photo-view-exposure'>{html.escape(' · '.join(exposure))}</p>",
                unsafe_allow_html=True,
            )
    _render_photo_editor(photo)


def render_photo_gallery():
    st.markdown(
        """
        <style>
        .photo-gallery-tagline {
            color: var(--dasol-muted);
            font-size: 15px;
            letter-spacing: 0.08em;
            margin-top: -8px;
            margin-bottom: 24px;
        }
        @keyframes galleryEnterFromRight {
            from { opacity: 0.35; transform: translateX(3%); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes galleryEnterFromLeft {
            from { opacity: 0.35; transform: translateX(-3%); }
            to { opacity: 1; transform: translateX(0); }
        }
        .st-key-photo_view_slide_next [data-testid="stImage"] img {
            animation: galleryEnterFromRight var(--dasol-motion) ease-out both;
        }
        .st-key-photo_view_slide_previous [data-testid="stImage"] img {
            animation: galleryEnterFromLeft var(--dasol-motion) ease-out both;
        }
        .st-key-photo_previous button,
        .st-key-photo_next button {
            min-height: 3.25rem;
            padding: 0 !important;
            background: transparent !important;
            color: var(--dasol-text) !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        .st-key-photo_previous button p,
        .st-key-photo_next button p {
            margin: 0 !important;
            font-size: 2.5rem !important;
            font-weight: 400 !important;
            line-height: 1 !important;
        }
        .st-key-photo_previous button:hover,
        .st-key-photo_next button:hover {
            background: transparent !important;
            color: var(--dasol-accent) !important;
        }
        [class*="st-key-photo_editor_"] [data-testid="stIconMaterial"] {
            display: none !important;
        }
        [class*="st-key-gallery_card_"] a:hover img {
            opacity: 0.92;
            transform: scale(1.015);
        }
        .photo-view-index {
            margin: 0;
            text-align: right;
            font-size: 12px;
            letter-spacing: 0.14em;
            color: var(--dasol-text);
        }
        .photo-view-index span,
        .photo-view-meta,
        .photo-view-exposure {
            color: var(--dasol-muted);
        }
        .st-key-photo_view_slide_next [data-testid="stImage"],
        .st-key-photo_view_slide_previous [data-testid="stImage"] {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 45vh;
        }
        .st-key-photo_view_slide_next [data-testid="stImage"] img,
        .st-key-photo_view_slide_previous [data-testid="stImage"] img {
            width: auto !important;
            max-width: 100% !important;
            height: auto !important;
            max-height: 68vh !important;
            object-fit: contain !important;
            margin: 0 auto !important;
        }
        .st-key-photo_view_caption {
            max-width: 880px;
            margin: 16px auto 0;
            padding: 0 4px;
            border-top: 1px solid var(--dasol-border);
        }
        .photo-view-title {
            font-size: 24px;
            font-weight: 600;
            letter-spacing: 0.03em;
            margin: 14px 0 4px;
            color: var(--dasol-text);
        }
        .photo-view-meta {
            font-size: 12px;
            letter-spacing: 0.04em;
            margin: 0 0 10px;
        }
        .photo-view-description {
            max-width: 680px;
            color: var(--dasol-text);
            font-size: 14px;
            line-height: 1.8;
            margin: 12px 0;
            white-space: normal;
        }
        .photo-view-exposure {
            font-size: 11px;
            letter-spacing: 0.06em;
            margin: 14px 0;
        }
        @media (max-width: 640px) {
            .st-key-photo_view_slide_next [data-testid="stImage"],
            .st-key-photo_view_slide_previous [data-testid="stImage"] {
                min-height: 40vh;
            }
            .st-key-photo_view_slide_next [data-testid="stImage"] img,
            .st-key-photo_view_slide_previous [data-testid="stImage"] img {
                max-height: 58vh !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    selected_id = st.session_state.get("selected_photo_id")
    if selected_id is not None:
        conn = get_db()
        photos = conn.execute(
            "SELECT * FROM photo_gallery ORDER BY shot_date DESC, id DESC"
        ).fetchall()
        conn.close()
        photos = sorted(
            photos,
            key=lambda photo: (photo["shot_date"], photo["id"]),
            reverse=st.session_state.get("photo_sort_order", "최신순") != "오래된순",
        )
        selected_index = next(
            (index for index, photo in enumerate(photos) if photo["id"] == selected_id),
            None,
        )
        if selected_index is not None:
            _render_photo_view(photos, selected_index)
            return

    st.markdown(
        "<h1 style='font-weight:800;font-size:26px;margin-top:0;'>PHOTO GALLERY</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='photo-gallery-tagline'>렌즈로 담은 아름다움</p>",
        unsafe_allow_html=True,
    )

    if st.button(
        "사진 등록 열기" if not st.session_state.get("show_photo_upload", False) else "등록 닫기",
        key="toggle_photo_upload",
    ):
        st.session_state.show_photo_upload = not st.session_state.get(
            "show_photo_upload", False
        )
        for key in (
            "new_photo_upload",
            "new_photo_upload_fingerprint",
            "new_photo_title",
            "new_photo_shot_date",
            "new_photo_location",
            "new_photo_description",
            "new_photo_iso",
            "new_photo_shutter_speed",
            "new_photo_aperture",
        ):
            st.session_state.pop(key, None)
        st.rerun()

    if st.session_state.get("show_photo_upload", False):
        uploaded_photo = st.file_uploader(
            "사진 파일",
            type=sorted(PHOTO_EXTENSIONS),
            key="new_photo_upload",
        )
        upload_fingerprint = (
            hashlib.sha256(uploaded_photo.getvalue()).hexdigest()
            if uploaded_photo is not None
            else None
        )
        if (
            uploaded_photo is not None
            and upload_fingerprint
            != st.session_state.get("new_photo_upload_fingerprint")
        ):
            try:
                metadata = _extract_photo_metadata(uploaded_photo)
            except ValueError as error:
                st.error(str(error))
                metadata = None
            if metadata is not None:
                st.session_state.new_photo_upload_fingerprint = upload_fingerprint
                st.session_state.new_photo_title = os.path.splitext(
                    uploaded_photo.name
                )[0]
                st.session_state.new_photo_shot_date = metadata["shot_date"]
                st.session_state.new_photo_location = metadata["location"]
                st.session_state.new_photo_iso = metadata["iso"]
                st.session_state.new_photo_shutter_speed = metadata["shutter_speed"]
                st.session_state.new_photo_aperture = metadata["aperture"]
        st.session_state.setdefault(
            "new_photo_upload_fingerprint", upload_fingerprint
        )
        st.session_state.setdefault(
            "new_photo_title",
            os.path.splitext(uploaded_photo.name)[0]
            if uploaded_photo is not None
            else "",
        )
        st.session_state.setdefault("new_photo_shot_date", dt.date.today())
        st.session_state.setdefault("new_photo_location", "")
        st.session_state.setdefault("new_photo_iso", "")
        st.session_state.setdefault("new_photo_shutter_speed", "")
        st.session_state.setdefault("new_photo_aperture", "")
        with st.form("add_gallery_photo"):
            title = st.text_input("제목", key="new_photo_title")
            shot_date = st.date_input("촬영 날짜", key="new_photo_shot_date")
            location = st.text_input("촬영 장소", key="new_photo_location")
            description = st.text_area("사진 설명", key="new_photo_description")
            iso_col, shutter_col, aperture_col = st.columns(3)
            with iso_col:
                iso = st.text_input("ISO", key="new_photo_iso", placeholder="예: 100")
            with shutter_col:
                shutter_speed = st.text_input(
                    "셔터 스피드",
                    key="new_photo_shutter_speed",
                    placeholder="예: 1/250s",
                )
            with aperture_col:
                aperture = st.text_input(
                    "조리개 값",
                    key="new_photo_aperture",
                    placeholder="예: f/2.8",
                )
            save_photo = st.form_submit_button("사진 등록", type="primary")

        if save_photo:
            if uploaded_photo is None:
                st.error("등록할 사진 파일을 선택해 주세요.")
            elif not title.strip():
                st.error("사진 제목을 입력해 주세요.")
            else:
                try:
                    filename, saved_path = _store_photo(uploaded_photo)
                except ValueError as error:
                    st.error(str(error))
                else:
                    conn = get_db()
                    try:
                        conn.execute(
                            """
                            INSERT INTO photo_gallery(
                                filename, saved_path, title, shot_date, location,
                                description, iso, shutter_speed, aperture, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                filename,
                                saved_path,
                                title.strip(),
                                shot_date.isoformat(),
                                location.strip(),
                                description.strip(),
                                iso.strip(),
                                shutter_speed.strip(),
                                aperture.strip(),
                                dt.datetime.now().isoformat(),
                            ),
                        )
                        conn.commit()
                    except sqlite3.Error:
                        if os.path.exists(saved_path):
                            os.remove(saved_path)
                        raise
                    finally:
                        conn.close()
                    st.session_state.show_photo_upload = False
                    st.success("사진이 등록되었습니다.")
                    st.rerun()

    conn = get_db()
    photos = conn.execute(
        "SELECT * FROM photo_gallery ORDER BY shot_date DESC, id DESC"
    ).fetchall()
    conn.close()
    if not photos:
        if st.session_state.get("selected_photo_id") is not None:
            st.session_state.pop("selected_photo_id", None)
            if "photo_id" in st.query_params:
                del st.query_params["photo_id"]
            st.warning("선택한 사진을 찾을 수 없습니다.")
            return
        st.caption("전시할 사진이 아직 없습니다.")
        return

    sort_order = st.segmented_control(
        "촬영 날짜 정렬",
        options=["최신순", "오래된순"],
        default="최신순",
        key="photo_sort_order",
    )
    photos = sorted(
        photos,
        key=lambda photo: (photo["shot_date"], photo["id"]),
        reverse=sort_order != "오래된순",
    )

    selected_id = st.session_state.get("selected_photo_id")
    selected_index = next(
        (index for index, photo in enumerate(photos) if photo["id"] == selected_id),
        None,
    )
    if selected_index is not None:
        _render_photo_view(photos, selected_index)
        return
    if selected_id is not None:
        st.session_state.pop("selected_photo_id", None)
        if "photo_id" in st.query_params:
            del st.query_params["photo_id"]
        st.warning("선택한 사진을 찾을 수 없습니다.")

    columns = st.columns(min(3, len(photos)), gap="medium")
    for index, photo in enumerate(photos):
        with columns[index % len(columns)]:
            with st.container(key=f"gallery_card_{photo['id']}"):
                if os.path.exists(photo["saved_path"]):
                    _render_clickable_preview(photo)
                else:
                    st.error(f"사진 파일을 찾을 수 없습니다: {photo['filename']}")
