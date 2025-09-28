import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

# ----------------------------
# Session state setup
# ----------------------------
if "round_active" not in st.session_state:
    st.session_state.round_active = False
if "round_info" not in st.session_state:
    st.session_state.round_info = None
if "shots" not in st.session_state:
    st.session_state.shots = []
if "lat" not in st.session_state:
    st.session_state.lat = None
if "lon" not in st.session_state:
    st.session_state.lon = None

st.title("⛳ Golf Shot Logger")

# ----------------------------
# START ROUND
# ----------------------------
if not st.session_state.round_active:
    st.header("Start Round")
    with st.form("start_round_form"):
        date = st.date_input("Round Date", value=datetime.date.today())
        course = st.text_input("Course Name")
        player = st.text_input("Player Name")
        start = st.form_submit_button("Start Round")

    if start:
        st.session_state.round_info = {
            "date": str(date),
            "course": course,
            "player": player,
        }
        st.session_state.shots = []
        st.session_state.round_active = True

# ----------------------------
# ROUND INFO DISPLAY
# ----------------------------
if st.session_state.round_active:
    info = st.session_state.round_info
    st.info(f"Round Active: {info['player']} at {info['course']} ({info['date']})")

# ----------------------------
# LOG SHOTS
# ----------------------------
if st.session_state.round_active:
    st.header("Log Shots")

    with st.form("log_shot_form"):
        hole = st.number_input("Hole Number", min_value=1, max_value=18, step=1)
        lie = st.selectbox("Lie", ["Tee", "Fairway", "Rough", "Sand", "Green", "Holed"])
        submit_shot = st.form_submit_button("Log Shot")

    # Folium Map for shot location
    st.subheader("Click on the map to set shot location")
    map_center = [st.session_state.lat or 44.9969, st.session_state.lon or -93.4336]
    m = folium.Map(location=map_center, zoom_start=18, tiles=None)

    # Add ESRI Satellite
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)

    # Draw shots and lines grouped by hole
    shots_by_hole = {}
    for shot in st.session_state.shots:
        shots_by_hole.setdefault(shot["hole"], []).append(shot)

    for hole_num, shots in shots_by_hole.items():
        prev_shot = None
        for shot in shots:
            # Add a flag marker
            folium.Marker(
                location=[shot["lat"], shot["lon"]],
                popup=f"Hole {shot['hole']}: {shot['lie']} ({shot.get('distance', 0):.1f} yd)",
                icon=folium.Icon(color="red", icon="flag")
            ).add_to(m)
            # Draw line from previous shot in the same hole
            if prev_shot:
                folium.PolyLine(
                    locations=[[prev_shot["lat"], prev_shot["lon"]], [shot["lat"], shot["lon"]]],
                    color="blue", weight=2.5, opacity=0.7
                ).add_to(m)
            prev_shot = shot

    map_click = st_folium(m, width=600, height=400)

    # Update session state lat/lon if user clicked
    if map_click and map_click.get("last_clicked"):
        st.session_state.lat = map_click["last_clicked"]["lat"]
        st.session_state.lon = map_click["last_clicked"]["lng"]
        st.info(f"Selected coordinates: {st.session_state.lat:.6f}, {st.session_state.lon:.6f}")

    # Log shot
    if submit_shot:
        if st.session_state.lat and st.session_state.lon:
            shot = {
                "timestamp": datetime.datetime.now().isoformat(),
                "hole": hole,
                "lie": lie,
                "lat": st.session_state.lat,
                "lon": st.session_state.lon
            }
            st.session_state.shots.append(shot)
            st.success(f"✅ Shot logged for Hole {hole}: {lie}")
        else:
            st.warning("No shot location selected. Click on the map first.")

# Show all shots in round
if st.session_state.shots:
    df = pd.DataFrame(st.session_state.shots)
    st.write("### Shots This Round")
    st.dataframe(df)

# ----------------------------
# END ROUND
# ----------------------------
if st.session_state.round_active:
    st.header("End Round")
    if st.button("End Round"):
        if st.session_state.shots:
            df = pd.DataFrame(st.session_state.shots)
            # Add round info
            for k, v in st.session_state.round_info.items():
                df[k] = v
            # Push to Google Sheets
            service_account_info = st.secrets["gcp_service_account"]
            credentials = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
            SHEET_ID = "1OQg0xPkaHa-ZaSN9T0eTDKV5O_NnC7ZIRJWbgRqTuI0"

            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            gc = gspread.authorize(credentials)
            worksheet = gc.open_by_key(SHEET_ID).sheet1
            worksheet.append_rows(df.values.tolist(), value_input_option="USER_ENTERED")
            st.success("🏁 Round pushed to Google Sheet!")
        # Reset session state
        st.session_state.round_active = False
        st.session_state.shots = []
        st.session_state.round_info = None
        st.success("🏁 Round ended.")
