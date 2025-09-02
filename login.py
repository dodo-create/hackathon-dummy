import streamlit as st
from firebase_admin import db

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
