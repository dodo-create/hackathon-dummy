import streamlit as st

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
