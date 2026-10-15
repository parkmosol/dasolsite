import datetime as dt
import html
import os
import sqlite3
import uuid

import pydeck as pdk
import streamlit as st
from PIL import Image, UnidentifiedImageError

from database import get_db

PLACE_PHOTO_DIR = os.path.join("uploaded_media", "place_archive")
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/positron"
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
            <div class="place-location-search">
                <input
                    type="text"
                    class="place-location-input"
                    placeholder="장소 검색 (예: 삿포로, 일본)"
                />
                <button type="button" class="place-location-search-button">검색</button>
            </div>
            <div class="place-location-map"></div>
            <p class="place-location-hint">지도를 클릭해 장소 위치를 선택하세요.</p>
        </div>
    """,
    css="""
        .place-location-picker {
            box-sizing: border-box;
            width: 100%;
            padding: 4px 0;
        }
        .place-location-search {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }
        .place-location-input {
            flex: 1;
            box-sizing: border-box;
            min-width: 0;
            padding: 8px 12px;
            border: 1px solid var(--st-color-border);
            border-radius: 6px;
            font-size: 0.9rem;
            font-family: inherit;
            background: #ffffff;
            color: inherit;
        }
        .place-location-input:focus {
            outline: none;
            border-color: #B77B43;
        }
        .place-location-search-button {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            background: #3d3530;
            color: #ffffff;
            font-size: 0.9rem;
            font-family: inherit;
            cursor: pointer;
            white-space: nowrap;
        }
        .place-location-search-button:disabled {
            opacity: 0.6;
            cursor: default;
        }
        .place-location-map {
            box-sizing: border-box;
            width: 100%;
            height: 320px;
            min-height: 320px;
            border: 1px solid var(--st-color-border);
            border-radius: 8px;
            overflow: hidden;
            cursor: crosshair;
        }
        .place-location-hint {
            margin: 8px 0 0;
            color: var(--st-color-secondary);
            font-size: 0.85rem;
        }
    """,
    js="""
export default function (component) {
  const { data, parentElement, setStateValue } = component
  const mapElement = parentElement.querySelector(".place-location-map")
  const hint = parentElement.querySelector(".place-location-hint")
  const input = parentElement.querySelector(".place-location-input")
  const searchButton = parentElement.querySelector(".place-location-search-button")
  if (!mapElement || !hint || !input || !searchButton) return

  const doc = parentElement.ownerDocument
  const view = doc.defaultView
  const STYLE_URL = "https://tiles.openfreemap.org/styles/positron"
  const MAPLIBRE_CSS = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"
  const MAPLIBRE_JS = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"
  const SEARCH_URL = "https://nominatim.openstreetmap.org/search"
  const REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

  function loadCss() {
    return new Promise((resolve, reject) => {
      let link = doc.querySelector("link[data-dasol-maplibre]")
      if (link && link.sheet) return resolve()
      if (!link) {
        link = doc.createElement("link")
        link.rel = "stylesheet"
        link.href = MAPLIBRE_CSS
        link.setAttribute("data-dasol-maplibre", "")
        doc.head.appendChild(link)
      }
      link.addEventListener("load", () => resolve(), { once: true })
      link.addEventListener("error", reject, { once: true })
    })
  }

  function loadScript() {
    return new Promise((resolve, reject) => {
      if (view.maplibregl) return resolve(view.maplibregl)
      let script = doc.querySelector("script[data-dasol-maplibre]")
      if (!script) {
        script = doc.createElement("script")
        script.src = MAPLIBRE_JS
        script.setAttribute("data-dasol-maplibre", "")
        doc.head.appendChild(script)
      }
      script.addEventListener("load", () => resolve(view.maplibregl), { once: true })
      script.addEventListener("error", reject, { once: true })
    })
  }

  function loadMapLibre() {
    if (!view.__dasolMapLibrePromise) {
      view.__dasolMapLibrePromise = Promise.all([loadCss(), loadScript()])
        .then(([, maplibregl]) => maplibregl)
        .catch(error => {
          view.__dasolMapLibrePromise = null
          throw error
        })
    }
    return view.__dasolMapLibrePromise
  }

  function isValidLocation(location) {
    return (
      location &&
      Number.isFinite(location.latitude) &&
      Number.isFinite(location.longitude)
    )
  }

  function createMarker(maplibregl, map, lngLat) {
    if (!mapElement.__dasolMarker) {
      const element = doc.createElement("div")
      element.style.cssText =
        "width:12px;height:12px;border-radius:50%;background:#B77B43;" +
        "border:1.5px solid #ffffff;box-shadow:0 0 0 1px rgba(0,0,0,0.15);" +
        "pointer-events:none;"
      mapElement.__dasolMarker = new maplibregl.Marker({
        element,
        anchor: "center",
      })
    }
    mapElement.__dasolMarker.setLngLat(lngLat).addTo(map)
  }

  function setPicked(maplibregl, map, latitude, longitude) {
    mapElement.__dasolPicked = { latitude, longitude }
    createMarker(maplibregl, map, [longitude, latitude])
    hint.textContent = "선택한 위치가 핀으로 표시됩니다. 다른 곳을 클릭해 변경할 수 있습니다."
  }

  async function reverseGeocode(latitude, longitude) {
    try {
      const params = new URLSearchParams({
        lat: String(latitude),
        lon: String(longitude),
        format: "jsonv2",
        zoom: "10",
        "accept-language": "ko",
      })
      const response = await fetch(`${REVERSE_URL}?${params.toString()}`, {
        headers: { Accept: "application/json" },
      })
      if (!response.ok) throw new Error(`reverse failed: ${response.status}`)
      const result = await response.json()
      const address = result.address || {}
      const country = address.country || ""
      if (!country) return null
      const city =
        address.city ||
        address.town ||
        address.village ||
        address.county ||
        address.state ||
        address.province ||
        ""
      return { country, city }
    } catch (error) {
      console.error("DASOL reverse geocode failed.", error)
      return null
    }
  }

  async function searchPlace(map) {
    const query = input.value.trim()
    if (!query) return
    searchButton.disabled = true
    hint.textContent = "검색 중입니다..."
    try {
      const params = new URLSearchParams({
        q: query,
        format: "jsonv2",
        limit: "1",
        "accept-language": "ko",
      })
      const response = await fetch(`${SEARCH_URL}?${params.toString()}`, {
        headers: { Accept: "application/json" },
      })
      if (!response.ok) throw new Error(`search failed: ${response.status}`)
      const results = await response.json()
      if (!results.length) {
        hint.textContent = "검색 결과가 없습니다. 다른 이름으로 검색해 보세요."
        return
      }
      const place = results[0]
      if (place.boundingbox) {
        const [south, north, west, east] = place.boundingbox.map(Number)
        map.fitBounds(
          [[west, south], [east, north]],
          { padding: 40, maxZoom: 10, duration: 800 },
        )
      } else {
        map.flyTo({
          center: [Number(place.lon), Number(place.lat)],
          zoom: 9,
          duration: 800,
        })
      }
      hint.textContent = `"${place.display_name}" 위치로 이동했습니다. 지도를 클릭해 장소 위치를 찍어 주세요.`
    } catch (error) {
      console.error("DASOL place search failed.", error)
      hint.textContent = "검색하지 못했습니다. 네트워크 연결을 확인해 주세요."
    } finally {
      searchButton.disabled = false
    }
  }

  loadMapLibre()
    .then(maplibregl => {
      let map = mapElement.__dasolMap
      if (map) {
        if (map.loaded() && mapElement.__dasolPicked) {
          const { latitude, longitude } = mapElement.__dasolPicked
          createMarker(maplibregl, map, [longitude, latitude])
        }
        return
      }

      const initial = isValidLocation(data.location) ? data.location : null
      map = new maplibregl.Map({
        container: mapElement,
        style: STYLE_URL,
        center: initial
          ? [initial.longitude, initial.latitude]
          : [20, 10],
        zoom: initial ? 4 : 1.2,
        minZoom: 0.8,
        renderWorldCopies: false,
      })
      mapElement.__dasolMap = map

      map.on("load", () => {
        map.resize()
        if (initial) {
          setPicked(maplibregl, map, initial.latitude, initial.longitude)
        } else {
          hint.textContent = "지도를 클릭해 장소 위치를 선택하세요."
        }
      })

      map.on("click", async event => {
        const latitude = Number(event.lngLat.lat.toFixed(5))
        const longitude = Number(event.lngLat.lng.toFixed(5))
        setPicked(maplibregl, map, latitude, longitude)
        setStateValue("location", { latitude, longitude })

        const token = (mapElement.__dasolGeoToken || 0) + 1
        mapElement.__dasolGeoToken = token
        hint.textContent = "위치 정보를 확인하는 중입니다..."
        const names = await reverseGeocode(latitude, longitude)
        if (mapElement.__dasolGeoToken !== token) return
        hint.textContent = "선택한 위치가 핀으로 표시됩니다. 다른 곳을 클릭해 변경할 수 있습니다."
        if (names) {
          setStateValue("location", {
            latitude,
            longitude,
            country: names.country,
            city: names.city,
          })
        }
      })

      const observer = new view.ResizeObserver(() => {
        view.requestAnimationFrame(() => map.resize())
      })
      observer.observe(mapElement)
      mapElement.__dasolResizeObserver = observer

      searchButton.addEventListener("click", () => searchPlace(map))
      input.addEventListener("keydown", event => {
        if (event.key === "Enter") {
          event.preventDefault()
          searchPlace(map)
        }
      })
    })
    .catch(error => {
      console.error("DASOL place location map failed to initialize.", error)
      if (!mapElement.__dasolMap) {
        hint.textContent = "지도를 불러오지 못했습니다. 네트워크 연결을 확인해 주세요."
      }
    })
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
    auto_key = f"{prefix}_auto_location"
    country_key = f"{prefix}_country"
    city_key = f"{prefix}_city"

    location_state = st.session_state.get(location_state_key, {})
    location = location_state.get("location", {})
    latitude = location.get(
        "latitude", float(place["latitude"]) if editing else None
    )
    longitude = location.get(
        "longitude", float(place["longitude"]) if editing else None
    )

    st.session_state.setdefault(country_key, place["country"] if editing else "")
    st.session_state.setdefault(
        city_key, (place["city"] or "") if editing else ""
    )

    # 지도에서 새 위치를 찍었을 때만 국가·도시를 자동으로 채운다.
    if "country" in location:
        coordinate = (location.get("latitude"), location.get("longitude"))
        if st.session_state.get(auto_key) != coordinate:
            st.session_state[country_key] = location.get("country") or ""
            st.session_state[city_key] = location.get("city") or ""
            st.session_state[auto_key] = coordinate

    st.markdown("**지도에서 위치 선택**")
    _LOCATION_PICKER(
        key=location_state_key,
        data={"location": {"latitude": latitude, "longitude": longitude}},
        on_location_change=lambda: None,
        width="stretch",
        height=440,
    )
    st.caption("지도를 클릭하면 국가와 도시/지역이 자동으로 채워집니다. 필요하면 직접 수정하세요.")

    with st.form(f"{prefix}_form"):
        country = st.text_input("국가", key=country_key)
        city = st.text_input("도시 / 지역", key=city_key)
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
    st.session_state.delete_place_id = None
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
        map_style=MAP_STYLE_URL,
        tooltip={
            "html": (
                "<b>{title}</b><br/>{city}, {country}<br/>{status_label}"
            ),
            "style": {