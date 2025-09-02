import streamlit as st
import re
import pandas as pd

import firebase_admin
from firebase_admin import credentials, db
import cv2
import numpy as np
import pickle
import os

# -----------------------------
# Inlined Pages (Single-file App)
# -----------------------------

def login_page():
    st.title("🔑 Login / Sign Up")

    choice = st.radio("Select option", ["Login", "Sign Up"], horizontal=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if choice == "Sign Up":
        if st.button("Create Account"):
            if email and password:
                user_ref = db.reference("/users")
                existing = user_ref.order_by_child("email").equal_to(email).get()

                if existing:
                    st.error("⚠️ Email already registered")
                else:
                    user_ref.push({
                        "email": email,
                        "password": password  # ⚠️ Plain text, production me hashing karo!
                    })
                    st.success("✅ Account created successfully!")
            else:
                st.warning("Please fill all fields")

    elif choice == "Login":
        if st.button("Login"):
            if email and password:
                user_ref = db.reference("/users")
                users = user_ref.order_by_child("email").equal_to(email).get()

                if users:
                    for _, user in users.items():
                        if user["password"] == password:
                            st.session_state["logged_in"] = True
                            st.session_state["user_email"] = email
                            st.success("✅ Login successful!")
                            st.rerun()
                        else:
                            st.error("❌ Wrong password")
                else:
                    st.error("❌ No account found with this email")


def view_page(zones):
    st.subheader("Parking Zones")

    cols = st.columns(len(zones))
    for i, col in enumerate(cols):
        with col:
            status = st.session_state.statuses[zones[i]]
            color = "#d4edda" if "✅" in status else "#f8d7da"
            text_color = "#155724" if "✅" in status else "#721c24"

            st.markdown(
                f"""
                <div style="
                    border: 2px solid #4CAF50;
                    border-radius: 16px;
                    padding: 40px;
                    text-align: center;
                    font-size: 18px;
                    font-weight: bold;
                    background-color: {color};
                    color: {text_color};
                    box-shadow: 4px 4px 12px rgba(0,0,0,0.2);
                ">
                    {zones[i]} <br> {status}
                </div>
                """,
                unsafe_allow_html=True
            )


def status_page(zones):
    st.subheader("📊 Control Parking Status")

    cols = st.columns(len(zones))
    for i, col in enumerate(cols):
        with col:
            zone = zones[i]
            status = st.session_state.statuses[zone]
            color = "#d4edda" if "✅" in status else "#f8d7da"
            text_color = "#155724" if "✅" in status else "#721c24"

            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        border: 2px solid #4CAF50;
                        border-radius: 16px;
                        padding: 20px;
                        text-align: center;
                        font-size: 20px;
                        font-weight: bold;
                        background-color: {color};
                        color: {text_color};
                        box-shadow: 4px 4px 12px rgba(0,0,0,0.2);
                        margin-bottom: 10px;
                    ">
                        {zone} <br> {status}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])

                with btn_col1:
                    if st.button("✅", key=f"avail_{zone}"):
                        st.session_state.statuses[zone] = "✅ Available"
                        st.rerun()

                with btn_col2:
                    if st.button("❌", key=f"occ_{zone}"):
                        st.session_state.statuses[zone] = "❌ Occupied"
                        st.rerun()

                with btn_col3:
                    if st.button("📞", key=f"toggle_{zone}"):
                        st.session_state.active_contact = (
                            None if st.session_state.active_contact == zone else zone
                        )
                        st.rerun()

            if st.session_state.active_contact == zone:
                new_number = st.text_input(
                    f"Edit contact for {zone}",
                    value=st.session_state.contacts[zone],
                    key=f"contact_input_{zone}",
                    label_visibility="collapsed"
                )
                st.session_state.contacts[zone] = new_number

                if st.button("📞 Call", key=f"call_{zone}"):
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url=tel:{new_number}">',
                        unsafe_allow_html=True
                    )


def report_page():
    st.subheader("📝 Reports")
    reports_ref = db.reference("/reports")

    # 🚀 Report form
    with st.form("report_form"):
        vehicle_number = st.text_input("Enter Vehicle Number:").upper()
        vehicle_type = st.selectbox("Type of Vehicle", ["null", "4 wheeler", "2 wheeler"])
        submitted = st.form_submit_button("Submit Report")

    if submitted:
        if not vehicle_number or vehicle_type == "null":
            st.error("⚠ Please fill in both the vehicle number and vehicle type.")
        else:
            # ✅ Validate formats
            old_format_pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$"
            bharat_format_pattern = r"^[0-9]{2}BH[0-9]{4}[A-Z]{2}$"

            if len(vehicle_number) < 9:
                st.error("⚠ Vehicle number must be at least 9 characters long.")
            elif not (re.match(old_format_pattern, vehicle_number) or re.match(bharat_format_pattern, vehicle_number)):
                st.error("❌ Invalid format. Use GJ01AB1234 or 22BH1234AA.")
            else:
                vehicle_ref = reports_ref.child(vehicle_number)
                current_data = vehicle_ref.get()

                if current_data:
                    new_count = current_data.get("violations", 0) + 1
                    fine = current_data.get("fine", 0)

                    if new_count % 3 == 0:  # har 3rd violation pe ₹500 fine
                        fine += 500

                    vehicle_ref.update({
                        "vehicle_number": vehicle_number,
                        "type": vehicle_type,
                        "violations": new_count,
                        "fine": fine,
                        "status": current_data.get("status", "unpaid")
                    })
                else:
                    vehicle_ref.set({
                        "vehicle_number": vehicle_number,
                        "type": vehicle_type,
                        "violations": 1,
                        "fine": 0,
                        "status": "unpaid"
                    })

                st.success(f"✅ Reported: {vehicle_number} ({vehicle_type})")

    # 📋 Show table
    data = reports_ref.get()
    if data:
        table_data = []
        for v, d in data.items():
            table_data.append({
                "Vehicle": v,
                "Type": d.get("type", "N/A"),           # safe get
                "Violations": d.get("violations", 0),
                "Fine": d.get("fine", 0),
                "Status": d.get("status", "unpaid")
            })
        df = pd.DataFrame(table_data)
        st.table(df)

    # 🚨 Clear fine
    vehicle_to_clear = st.text_input("Enter vehicle number to clear fine:")
    if st.button("Clear Fine"):
        vehicle_to_clear = vehicle_to_clear.upper().strip()
        if not vehicle_to_clear:
            st.error("⚠ Please enter a valid vehicle number.")
        else:
            # Validate against allowed Firebase key pattern
            if re.match(r'^[A-Z0-9]+$', vehicle_to_clear):
                if reports_ref.child(vehicle_to_clear).get():
                    reports_ref.child(vehicle_to_clear).delete()
                    st.success(f"✅ Cleared & removed {vehicle_to_clear} from Firebase.")
                else:
                    st.warning(f"⚠ Vehicle {vehicle_to_clear} not found in reports.")
            else:
                st.error("❌ Invalid vehicle number. Only letters and numbers are allowed.")


# -----------------------------
# Headless detector integration for Zone 1 sync
# -----------------------------
def _load_positions(positions_candidates=("CarParkPos", "CarParkPos.unknown")):
    for path in positions_candidates:
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return pickle.load(f)
        except Exception:
            continue
    return []


def compute_available_from_video(video_path="carPark.mp4"):
    try:
        if not os.path.exists(video_path):
            return 0, 0
        pos_list = _load_positions()
        cap = cv2.VideoCapture(video_path)
        success, img = cap.read()
        cap.release()
        if not success or img is None or len(pos_list) == 0:
            return 0, len(pos_list)

        # Fixed params to avoid GUI trackbars
        block_size = 11
        c_value = 2
        blur_size = 3
        width, height = 103, 43

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if blur_size % 2 == 0:
            blur_size += 1
        gray = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        if block_size % 2 == 0:
            block_size += 1
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, block_size, c_value)

        available_count = 0
        for pos in pos_list:
            x, y = pos
            w, h = width, height
            space_crop = thresh[y:y+h, x:x+w]
            space_orig = img[y:y+h, x:x+w]
            if space_crop.size == 0 or space_orig.size == 0:
                continue
            occupancy_ratio = np.mean(space_crop > 0)
            gray_space = cv2.cvtColor(space_orig, cv2.COLOR_BGR2GRAY)
            gray_variance = np.var(gray_space)
            edges = cv2.Canny(gray_space, 30, 100)
            edge_density = np.mean(edges > 0)

            if occupancy_ratio < 0.5 and edge_density < 0.1 and gray_variance < 800:
                available_count += 1

        return available_count, len(pos_list)
    except Exception:
        return 0, 0

# -----------------------------
# Firebase Setup (Realtime DB)
# -----------------------------
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://smartparkingaihackathon-default-rtdb.firebaseio.com/"
        })
    db_ref = db.reference("/")  # root reference
except Exception as e:
    st.error(f"❌ Firebase initialization failed: {e}")
    db_ref = None

# -----------------------------
# Config & UI Setup
# -----------------------------
st.set_page_config(page_title="AI Parking App", layout="wide")

# -----------------------------
# Session State Defaults
# -----------------------------
zones = ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "role" not in st.session_state:
    st.session_state.role = None  # admin / student

if "statuses" not in st.session_state:
    st.session_state.statuses = {z: "❌ Occupied" for z in zones}

if "contacts" not in st.session_state:
    st.session_state.contacts = {
        "Zone 1": "+91-98982-81627",
        "Zone 2": "+91-93266-76211",
        "Zone 3": "+91-73593-18129",
        "Zone 4": "+91-97246-03166",
        "Zone 5": "+91-83206-02907",
    }

if "active_contact" not in st.session_state:
    st.session_state.active_contact = None

# -----------------------------
# 1) Show login page if not logged in
# -----------------------------
if not st.session_state.logged_in:
    login_page()

# -----------------------------
# 2) Fetch role from Firebase if logged in
# -----------------------------
if st.session_state.logged_in and st.session_state.role is None:
    if db_ref is None:
        st.error("❌ No Firebase DB connection. Cannot fetch role.")
    else:
        user_email = st.session_state.get("user_email")
        try:
            users_node = db_ref.child("users").get()
            role = "student"
            if users_node:
                for _, user_data in users_node.items():
                    if user_data.get("email") == user_email:
                        role = user_data.get("role", "student")
                        break
            st.session_state.role = role
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to fetch role from Firebase: {e}")
            st.session_state.role = "student"
            st.rerun()

# -----------------------------
# 3) Show app if logged in
# -----------------------------
if st.session_state.logged_in:
    st.title("🚗 AI Parking Space App")
    st.sidebar.info(f"👤 Role: {st.session_state.role}")

    role = st.session_state.role

    # Menu items based on role
    if role == "admin":
        menu_items = ["View", "Status", "Report"]
    else:
        menu_items = ["View"]

    menu = st.sidebar.radio("Navigation", menu_items)

    # Sync Zone 1 via detector
    with st.sidebar.expander("Sync Zone 1 from video"):
        if st.button("Detect now"):
            available, total = compute_available_from_video("carPark.mp4")
            # Simple mapping: if any spot is available, mark Zone 1 as available
            if total > 0 and available > 0:
                st.session_state.statuses["Zone 1"] = "✅ Available"
            else:
                st.session_state.statuses["Zone 1"] = "❌ Occupied"
            st.success(f"Video scan: {available}/{total} available")
            st.rerun()

    if menu == "View":
        view_page(zones)
    elif menu == "Status" and role == "admin":
        status_page(zones)
    elif menu == "Report" and role == "admin":
        report_page()

    # Firebase test write
    if db_ref is not None:
        try:
            test_ref = db_ref.child("test")
            test_ref.set({
                "name": st.session_state.get("user_email", "guest"),
                "status": "Connected successfully 🚀"
            })
            st.sidebar.success("✅ Firebase connected!")
        except Exception as e:
            st.sidebar.error(f"❌ Firebase test write failed: {e}")
    else:
        st.sidebar.warning("⚠ Firebase DB not initialized")

    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.session_state.role = None
        st.rerun()
else:
    st.info("Please log in to access the app.")
