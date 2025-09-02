import streamlit as st

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
