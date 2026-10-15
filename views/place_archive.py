import datetime as dt
import html
import os
import sqlite3
import uuid
from urllib.parse import urlencode

import pydeck as pdk
import streamlit as st
from PIL import Image, UnidentifiedImageError

from database import get_db

PLACE_PHOTO_DIR = os.path.join("uploaded_media", "place_archive")
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
os.makedirs(PLACE_PHOTO_DIR, exist_ok=True)

STATUS_LABELS = {"WANT": "가고 싶은 곳", "VISITED": "다녀온 곳"}
STATUS_COLORS = {
    "WANT": [183, 123, 67, 210],
    "VISITED": [78, 119, 92, 220],
}

_LOCATION_PICKER = st.components.v2.component(
    "dasol.place_location_picker",
    html="""
        <div class="place-location-picker">
            <div class="place-location-map"></div>
            <p class="place-location-hint">지도를 클릭해 장소 위치를 선택하세요.</p>
        </div>
    """,
    css="""
        .place-location-map {
            width: 100%;
            height: 320px;
            border: 1px solid var(--st-color-border);
            border-radius: 8px;
            overflow: hidden;
        }
        .place-location-hint {
            margin: 8px 0 0;
            color: var(--st-color-secondary);
            font-size: 0.85rem;
        }
        .place-location-picker .leaflet-container {
            font-family: inherit;
        }
    """,
    js="""
export default function (component) {
  const { data, parentElement, setStateValue } = component
  const mapElement = parentElement.querySelector(".place-location-map")
  const hint = parentElement.querySelector(".place-location-hint")
  if (!mapElement || !hint) return

  const doc = parentElement.ownerDocument
  const view = doc.defaultView
  if (!view.L) {
    if (!view.__dasolLeafletPromise) {
      const root = parentElement.getRootNode()
      const stylesheetReady = new Promise((resolve, reject) => {
        const stylesheet = doc.createElement("link")
        stylesheet.rel = "stylesheet"
        stylesheet.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        stylesheet.onload = resolve
        stylesheet.onerror = reject
        root.appendChild(stylesheet)
      })
      const scriptReady = new Promise((resolve, reject) => {
        const script = doc.createElement("script")
        script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        script.onload = () => resolve(view.L)
        script.onerror = reject
        doc.head.appendChild(script)
      })
      view.__dasolLeafletPromise = Promise.all([
        stylesheetReady,
        scriptReady,
      ]).then(([, leaflet]) => leaflet)
    }
    view.__dasolLeafletPromise.then(initialize).catch(() => {
      hint.textContent = "지도를 불러오지 못했습니다. 네트워크 연결을 확인해 주세요."
    })
  } else {
    initialize(view.L)
  }

  function initialize(L) {
    let map = mapElement.__dasolMap
    if (!map) {
      const hasInitialLocation =
        Number.isFinite(data.location?.latitude) &&
        Number.isFinite(data.location?.longitude)
      map = L.map(mapElement).setView(
        hasInitialLocation
          ? [data.location.latitude, data.location.longitude]
          : [20, 0],
        hasInitialLocation ? 5 : 2,
      )
      map.setMinZoom(1)
      map.setMaxBounds([[-85, -180], [85, 180]])
      map.options.maxBoundsViscosity = 1
      L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          maxZoom: 19,
          noWrap: true,
        },
      ).addTo(map)
      mapElement.__dasolMap = map
      map.on("click", event => {
        setStateValue("location", {
          latitude: Number(event.latlng.lat.toFixed(5)),
          longitude: Number(event.latlng.lng.toFixed(5)),
        })
      })
      mapElement.__dasolMarker = null
    }

    const hasLocation =
      Number.isFinite(data.location?.latitude) &&
      Number.isFinite(data.location?.longitude)
    if (hasLocation) {
      const location = [
        data.location.latitude,
        data.location.longitude,
      ]
      if (mapElement.__dasolMarker) {
        mapElement.__dasolMarker.setLatLng(location)
      } else {
        mapElement.__dasolMarker = L.circleMarker(location, {
          radius: 5,
          color: "#ffffff",
          weight: 1.5,
          fillColor: "#B77B43",
          fillOpacity: 1,
        }).addTo(map)
      }
      hint.textContent = "선택한 위치가 핀으로 표시됩니다. 다른 곳을 클릭해 변경할 수 있습니다."
    }
    view.setTimeout(() => map.invalidateSize(), 0)
  }
}
""",
)


def _set_selected_place(place_id, update_widget=True):
    st.session_state.selected_place_id = place_id
    if update_widget:
        st.session_state.place_archive_selection = place_id
    st.session_state.synced_place_archive_selection = place_id


def _read_places():
    conn = get_db()
    try:
        return conn.execute(
            """
            SELECT place_archive.*,
                (SELECT COUNT(*) FROM place_archive_photos
                 WHERE place_id = place_archive.id) AS photo_count
            FROM place_archive
            ORDER BY CASE status WHEN 'VISITED' THEN 0 ELSE 1 END,
                country COLLATE NOCASE, city COLLATE NOCASE, title COLLATE NOCASE
            """
        ).fetchall()
    finally:
        conn.close()


def _save_place_photos(photos):
    saved_files = []
    try:
        for photo in photos or []:
            extension = os.path.splitext(photo.name)[1].lower().lstrip(".")
            if extension not in PHOTO_EXTENSIONS:
                raise ValueError("JPG, PNG, WEBP 사진만 등록할 수 있습니다.")
            try:
                with Image.open(photo) as image:
                    image.verify()
            except (OSError, UnidentifiedImageError) as error:
                raise ValueError(
                    f"유효한 사진 파일이 아닙니다: {photo.name}"
                ) from error

            filename = f"{uuid.uuid4().hex}.{extension}"
            saved_path = os.path.join(PLACE_PHOTO_DIR, filename)
            with open(saved_path, "wb") as image_file:
                image_file.write(photo.getbuffer())
            saved_files.append((filename, saved_path))
    except ValueError:
        _remove_files([saved_path for _, saved_path in saved_files])
        raise
    return saved_files


def _remove_files(saved_files):
    for saved_file in saved_files:
        if os.path.exists(saved_file):
            os.remove(saved_file)


def _persist_place_photos(place_id, photos):
    saved_files = _save_place_photos(photos)
    if not saved_files:
        return
    conn = get_db()
    try:
        conn.executemany(
            """
            INSERT INTO place_archive_photos(place_id, filename, saved_path, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (place_id, filename, saved_path, dt.datetime.now().isoformat())
                for filename, saved_path in saved_files
            ],
        )
        conn.commit()
    except sqlite3.Error:
        _remove_files([saved_path for _, saved_path in saved_files])
        raise
    finally:
        conn.close()


def _render_place_form(place=None):
    editing = place is not None
    prefix = f"edit_place_{place['id']}" if editing else "new_place"
    status_options = list(STATUS_LABELS)
    default_status = place["status"] if editing else "WANT"
    status_index = status_options.index(default_status)
    status = st.selectbox(
        "여행 구분",
        status_options,
        index=status_index,
        format_func=lambda value: STATUS_LABELS[value],
        key=f"{prefix}_status",
    )
    location_state_key = f"{prefix}_location_picker"
    location_state = st.session_state.get(location_state_key, {})
    location = location_state.get("location", {})
    latitude = location.get(
        "latitude", float(place["latitude"]) if editing else None
    )
    longitude = location.get(
        "longitude", float(place["longitude"]) if editing else None
    )
    st.markdown("**지도에서 위치 선택**")
    _LOCATION_PICKER(
        key=location_state_key,
        data={"location": {"latitude": latitude, "longitude": longitude}},
        on_location_change=lambda: None,
        width="stretch",
        height=360,
    )
    with st.form(f"{prefix}_form"):
        country = st.text_input(
            "국가",
            place["country"] if editing else "",
            key=f"{prefix}_country",
        )
        city = st.text_input(
            "도시 / 지역",
            place["city"] or "" if editing else "",
            key=f"{prefix}_city",
        )
        description = st.text_area(
            "간단한 설명",
            place["description"] or "" if editing else "",
            key=f"{prefix}_description",
        )
        if status == "WANT":
            travel_goal = st.text_area(
                "여행 목표와 방문하고 싶은 이유",
                (
                    place["travel_goal"] or ""
                    if editing and place["status"] == "WANT"
                    else ""
                ),
                key=f"{prefix}_goal",
            )
            visit_date = None
            memory = ""
        else:
            travel_goal = ""
            saved_date = (
                place["visit_date"] or ""
                if editing and place["status"] == "VISITED"
                else ""
            )
            visit_date = st.text_input(
                "여행 날짜 (선택, YYYY-MM-DD)",
                saved_date,
                key=f"{prefix}_visit_date",
                placeholder="예: 2026-10-15",
            ).strip()
            memory = st.text_area(
                "여행의 추억",
                (
                    place["memory"] or ""
                    if editing and place["status"] == "VISITED"
                    else ""
                ),
                key=f"{prefix}_memory",
            )

        new_photos = st.file_uploader(
            "여행 사진 추가",
            type=sorted(PHOTO_EXTENSIONS),
            accept_multiple_files=True,
            key=f"{prefix}_photos",
        )
        save = st.form_submit_button(
            "변경 저장" if editing else "장소 등록",
            type="primary",
        )

    if not save:
        return
    if not country.strip():
        st.error("국가를 입력해 주세요.")
        return
    if (
        latitude is None
        or longitude is None
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        st.error("지도에서 장소 위치를 선택해 주세요.")
        return
    if visit_date:
        try:
            dt.date.fromisoformat(visit_date)
        except ValueError:
            st.error("여행 날짜는 YYYY-MM-DD 형식으로 입력해 주세요.")
            return
    if status == "WANT":
        visit_date = None

    uploaded_photos = []
    try:
        uploaded_photos = _save_place_photos(new_photos)
        conn = get_db()
        try:
            if editing:
                conn.execute(
                    """
                    UPDATE place_archive
                    SET status = ?, title = ?, country = ?, city = ?, latitude = ?,
                        longitude = ?, description = ?, travel_goal = ?,
                        visit_date = ?, memory = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        city.strip() or country.strip(),
                        country.strip(),
                        city.strip(),
                        latitude,
                        longitude,
                        description.strip(),
                        travel_goal.strip(),
                        visit_date or None,
                        memory.strip(),
                        place["id"],
                    ),
                )
                place_id = place["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO place_archive(
                        status, title, country, city, latitude, longitude,
                        description, travel_goal, visit_date, memory, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        status,
                        city.strip() or country.strip(),
                        country.strip(),
                        city.strip(),
                        latitude,
                        longitude,
                        description.strip(),
                        travel_goal.strip(),
                        visit_date or None,
                        memory.strip(),
                        dt.datetime.now().isoformat(),
                    ),
                )
                place_id = cursor.lastrowid

            conn.executemany(
                """
                INSERT INTO place_archive_photos(place_id, filename, saved_path, created_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (place_id, filename, saved_path, dt.datetime.now().isoformat())
                    for filename, saved_path in uploaded_photos
                ],
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        _remove_files([saved_path for _, saved_path in uploaded_photos])
        raise
    except ValueError as error:
        _remove_files([saved_path for _, saved_path in uploaded_photos])
        st.error(str(error))
        return

    st.session_state.show_new_place = False
    st.session_state.edit_place_id = None
    _set_selected_place(place_id, update_widget=not editing)
    st.success("장소가 저장되었습니다.")
    st.rerun()


def _delete_place(place_id):
    conn = get_db()
    try:
        photo_rows = conn.execute(
            "SELECT saved_path FROM place_archive_photos WHERE place_id = ?",
            (place_id,),
        ).fetchall()
        conn.execute("DELETE FROM place_archive_photos WHERE place_id = ?", (place_id,))
        conn.execute("DELETE FROM place_archive WHERE id = ?", (place_id,))
        conn.commit()
    finally:
        conn.close()
    _remove_files([photo["saved_path"] for photo in photo_rows])
    st.session_state.selected_place_id = None
    st.session_state.edit_place_id = None
    st.success("장소 기록을 삭제했습니다.")
    st.rerun()


def _build_map(places):
    map_data = [
        {
            "id": place["id"],
            "title": html.escape(place["city"] or place["country"]),
            "country": html.escape(place["country"]),
            "city": html.escape(place["city"] or ""),
            "status_label": STATUS_LABELS[place["status"]],
            "color": STATUS_COLORS[place["status"]],
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "radius": 35000,
        }
        for place in places
    ]
    points = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        id="place_archive_points",
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_line_color=[255, 255, 255, 235],
        get_line_width=1,
        stroked=True,
        get_radius="radius",
        radius_min_pixels=4,
        radius_max_pixels=8,
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )
    if places:
        latitude = sum(place["latitude"] for place in places) / len(places)
        longitude = sum(place["longitude"] for place in places) / len(places)
        zoom = 1.1 if len(places) > 1 else 2
    else:
        latitude, longitude, zoom = 18, 0, 0.8

    return pdk.Deck(
        layers=[points],
        views=[pdk.View(type="MapView", controller=True, repeat=False)],
        initial_view_state=pdk.ViewState(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
            min_zoom=0,
            max_zoom=16,
            pitch=0,
        ),
        map_provider="maplibre",
        map_style="https://tiles.openfreemap.org/styles/positron",
        tooltip={
            "html": (
                "<b>{title}</b><br/>{city}, {country}<br/>{status_label}"
            ),
            "style": {
                "backgroundColor": "#ffffff",
                "color": "#2C2A29",
                "fontFamily": "sans-serif",
                "borderRadius": "6px",
            },
        },
    )


def _render_map(places):
    chart = st.pydeck_chart(
        _build_map(places),
        key="place_archive_map",
        on_select="rerun",
        selection_mode="single-object",
        height=520,
        width="stretch",
        alt="세계 지도에 표시한 여행 희망지와 방문 장소",
    )
    selected_objects = (
        chart.get("selection", {}).get("objects", {})
        if chart is not None
        else {}
    )
    for layer_objects in selected_objects.values():
        if layer_objects:
            selected_id = layer_objects[0].get("id")
            if selected_id is not None:
                return int(selected_id)
    return None


def _render_place_photos(place):
    conn = get_db()
    try:
        photos = conn.execute(
            """
            SELECT * FROM place_archive_photos
            WHERE place_id = ? ORDER BY id
            """,
            (place["id"],),
        ).fetchall()
    finally:
        conn.close()

    if not photos:
        st.caption("등록된 여행 사진이 없습니다.")
        return
    photo_columns = st.columns(min(3, len(photos)), gap="medium")
    for index, photo in enumerate(photos):
        with photo_columns[index % len(photo_columns)]:
            if not os.path.exists(photo["saved_path"]):
                st.warning(f"사진 파일을 찾을 수 없습니다: {photo['filename']}")
                continue
            st.image(
                photo["saved_path"],
                alt=f"{place['city'] or place['country']} 여행 사진",
                width="stretch",
            )
            if st.button(
                "사진 크게 보기",
                key=f"view_place_photo_{photo['id']}",
                width="stretch",
            ):
                st.session_state.selected_place_photo_id = photo["id"]
                st.query_params["place_photo_id"] = str(photo["id"])
                st.rerun()
            if st.button(
                "사진 삭제",
                key=f"delete_place_photo_{photo['id']}",
                width="stretch",
            ):
                conn = get_db()
                try:
                    conn.execute(
                        "DELETE FROM place_archive_photos WHERE id = ? AND place_id = ?",
                        (photo["id"], place["id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()
                _remove_files([photo["saved_path"]])
                st.rerun()


def _render_photo_view(photo):
    if st.button(":material/arrow_back: 장소 기록으로 돌아가기", key="place_photo_back"):
        st.session_state.pop("selected_place_photo_id", None)
        if "place_photo_id" in st.query_params:
            del st.query_params["place_photo_id"]
        st.rerun()
    st.subheader(photo["filename"])
    if os.path.exists(photo["saved_path"]):
        with st.container(key="place_photo_viewer"):
            st.image(
                photo["saved_path"],
                alt=f"{photo['place_title']} 여행 사진",
                width="stretch",
            )
    else:
        st.error("사진 파일을 찾을 수 없습니다.")
    place_name = ", ".join(
        value for value in (photo["city"] or "", photo["country"]) if value
    )
    st.caption(f"{place_name}  ·  {photo['filename']}")


def _render_selected_place(places):
    selected_id = st.session_state.get("selected_place_id")
    place = next((item for item in places if item["id"] == selected_id), None)
    if place is None:
        st.caption("지도 핀이나 장소 목록을 선택하면 여행 기록이 여기에 표시됩니다.")
        return

    with st.container(key=f"place_archive_selected_{place['id']}", border=True):
        st.caption(STATUS_LABELS[place["status"]])
        st.subheader(
            ", ".join(
                value for value in (place["city"] or "", place["country"]) if value
            )
        )
        st.caption(f"{place['latitude']:.4f}, {place['longitude']:.4f}")
        if place["description"]:
            st.write(place["description"])
        if place["status"] == "WANT":
            st.markdown("**여행 목표와 방문하고 싶은 이유**")
            st.write(place["travel_goal"] or "아직 기록이 없습니다.")
        else:
            if place["visit_date"]:
                st.caption(f"여행 날짜 · {place['visit_date']}")
            st.markdown("**여행의 추억**")
            st.write(place["memory"] or "아직 기록이 없습니다.")
            _render_place_photos(place)

        edit_col, delete_col, _ = st.columns([1, 1, 4])
        with edit_col:
            if st.button("수정", key=f"edit_place_{place['id']}"):
                st.session_state.pop(
                    f"edit_place_{place['id']}_location_picker", None
                )
                st.session_state.edit_place_id = place["id"]
                st.session_state.show_new_place = False
                st.rerun()
        with delete_col:
            if st.button(
                "삭제",
                key=f"delete_place_{place['id']}",
                type="secondary",
            ):
                st.session_state.delete_place_id = place["id"]
                st.rerun()

    if st.session_state.get("edit_place_id") == place["id"]:
        _render_place_form(place)


def render_place_archive():
    st.markdown(
        """
        <style>
        @keyframes archiveEnter {
            from { opacity: 0.55; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        [class*="st-key-place_archive_selected_"] [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-place_photo_viewer [data-testid="stImage"] {
            animation: archiveEnter 260ms ease-out both;
        }
        .place-archive-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            color: var(--dasol-muted);
            font-size: 13px;
            margin: 8px 0 16px;
        }
        .place-archive-legend span {
            display: inline-flex;
            align-items: center;
            gap: 7px;
        }
        .place-archive-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            display: inline-block;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h1 style='font-weight:800;font-size:26px;margin-top:0;'>PLACE ARCHIVE</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:var(--dasol-muted);margin-top:-8px;'>"
        "가고 싶은 곳은 목표로, 다녀온 곳은 기억으로 남겨 보세요.</p>",
        unsafe_allow_html=True,
    )

    places = _read_places()
    visited_count = sum(place["status"] == "VISITED" for place in places)
    wish_count = len(places) - visited_count
    stat_visited, stat_wish, stat_total = st.columns(3)
    stat_visited.metric("다녀온 곳", visited_count)
    stat_wish.metric("가고 싶은 곳", wish_count)
    stat_total.metric("여행 기록", len(places))

    st.markdown(
        """
        <div class="place-archive-legend">
            <span><i class="place-archive-dot" style="background:#B77B43"></i>가고 싶은 곳</span>
            <span><i class="place-archive-dot" style="background:#4E775C"></i>다녀온 곳</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    photo_id = st.session_state.get("selected_place_photo_id")
    if photo_id is not None:
        conn = get_db()
        try:
            photo = conn.execute(
                """
                SELECT place_archive_photos.*, place_archive.title AS place_title,
                    place_archive.country, place_archive.city
                FROM place_archive_photos
                JOIN place_archive ON place_archive.id = place_archive_photos.place_id
                WHERE place_archive_photos.id = ?
                """,
                (photo_id,),
            ).fetchone()
        finally:
            conn.close()
        if photo is None:
            st.session_state.pop("selected_place_photo_id", None)
            if "place_photo_id" in st.query_params:
                del st.query_params["place_photo_id"]
            st.warning("선택한 여행 사진을 찾을 수 없습니다.")
        else:
            _render_photo_view(photo)
            return

    if st.button(
        "장소 등록 열기"
        if not st.session_state.get("show_new_place", False)
        else "등록 닫기",
        key="toggle_new_place",
    ):
        st.session_state.pop("new_place_location_picker", None)
        st.session_state.show_new_place = not st.session_state.get(
            "show_new_place", False
        )
        st.session_state.edit_place_id = None
        st.rerun()
    if st.session_state.get("show_new_place", False):
        _render_place_form()

    map_col, details_col = st.columns([1.55, 1], gap="large")
    with map_col:
        map_selected_id = _render_map(places)
        st.caption(
            "지도를 드래그해 이동하고 휠로 확대·축소하세요. 핀을 누르면 장소 정보를 확인할 수 있습니다."
        )
    with details_col:
        st.subheader("여행 기록")
        if places:
            place_options = {
                place["id"]: (
                    f"{'●' if place['status'] == 'VISITED' else '○'}  "
                    + ", ".join(
                        value
                        for value in (place["city"] or "", place["country"])
                        if value
                    )
                )
                for place in places
            }
            selected_id = st.session_state.get("selected_place_id")
            last_map_selected_id = st.session_state.get("last_map_selected_id")
            if map_selected_id != last_map_selected_id:
                st.session_state.last_map_selected_id = map_selected_id
                if map_selected_id in place_options:
                    selected_id = map_selected_id
                    _set_selected_place(selected_id)
            if selected_id not in place_options:
                selected_id = None
                if st.session_state.get("selected_place_id") is not None:
                    _set_selected_place(None)
            if (
                st.session_state.get("synced_place_archive_selection")
                != selected_id
                or "place_archive_selection" not in st.session_state
            ):
                _set_selected_place(selected_id)
            chosen_id = st.selectbox(
                "장소 선택",
                options=[None, *place_options],
                index=(
                    None
                    if "place_archive_selection" in st.session_state
                    else 0
                ),
                format_func=lambda value: (
                    "장소를 선택하세요" if value is None else place_options[value]
                ),
                key="place_archive_selection",
                label_visibility="collapsed",
            )
            st.session_state.selected_place_id = chosen_id
            st.session_state.synced_place_archive_selection = chosen_id
            if chosen_id is not None:
                _render_selected_place(places)
            else:
                st.caption("지도 핀이나 목록에서 장소를 선택해 기록을 확인하세요.")
        else:
            st.caption("장소를 등록하면 세계 지도 위에 여행 기록이 쌓입니다.")

    delete_id = st.session_state.get("delete_place_id")
    if delete_id is not None:
        place = next((item for item in places if item["id"] == delete_id), None)
        if place is not None:
            place_name = ", ".join(
                value for value in (place["city"] or "", place["country"]) if value
            )
            st.warning(f"'{place_name}' 장소와 사진을 삭제할까요?")
            confirm_col, cancel_col, _ = st.columns([1, 1, 4])
            with confirm_col:
                if st.button(
                    "삭제 확인",
                    key=f"confirm_delete_place_{delete_id}",
                    type="primary",
                ):
                    _delete_place(delete_id)
            with cancel_col:
                if st.button("취소", key="cancel_delete_place"):
                    st.session_state.delete_place_id = None
                    st.rerun()
