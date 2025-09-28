import streamlit as st
import pandas as pd
import datetime
from streamlit_js_eval import get_geolocation
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# Google Sheets setup
# ----------------------------
SHEET_ID = "1OQg0xPkaHa-ZaSN9T0eTDKV5O_NnC7ZIRJWbgRqTuI0"

scopes = ["https://www.googleapis.com/auth/spreadsheets"]

service_account_info = st.secrets["gcp_service_account"]
credentials = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(credentials)
worksheet = gc.open_by_key(SHEET_ID).sheet1

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

st.title("⛳ GPS Shot Logger")

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
        st.session_state.round_info = {"date": str(date), "course": course, "player": player}
        st.session_state.shots = []
        st.session_state.round_active = True
        st.success(f"✅ Round started: {player} at {course} on {date}")

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
        get_gps = st.checkbox("Get GPS")
        submit_shot = st.form_submit_button("Log Shot")

    if get_gps:
        location = get_geolocation()
        if location and "coords" in location:
            st.session_state.lat = location["coords"]["latitude"]
            st.session_state.lon = location["coords"]["longitude"]
            st.success(f"GPS captured: {st.session_state.lat:.6f}, {st.session_state.lon:.6f}")
        else:
            st.warning("Could not fetch GPS coordinates.")

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
            st.warning("No GPS yet. Tap 'Get GPS' first.")

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
            worksheet.append_rows(df.values.tolist(), value_input_option="USER_ENTERED")
            st.success("🏁 Round pushed to Google Sheet!")
        # Reset session state
        st.session_state.round_active = False
        st.session_state.shots = []
        st.session_state.round_info = None
        st.success("🏁 Round ended.")
