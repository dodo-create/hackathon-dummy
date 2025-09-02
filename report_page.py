import streamlit as st
import re
import pandas as pd
from firebase_admin import db

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
