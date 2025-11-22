import streamlit as st

st.title(":material/local_hospital: Hospital Dashboard")

st.set_page_config("Home", initial_sidebar_state="collapsed", page_icon=":material/home:")


def ask_consent():
    if "consent_given" not in st.session_state:
        st.session_state.consent_given = False

    if not st.session_state.consent_given:

        st.warning("This website collects personal data and has data retention policy of 365 days. By continuing, you agree to our terms and policy.")
        if st.button("I Agree"):
            st.session_state["consent_given"] = True
            st.rerun()
        else:
            st.stop()


ask_consent()

if st.button(":material/dashboard: Go to Dashboard", width="stretch"):
    st.switch_page("pages/dashboard.py")


st.subheader("This project features:")
st.write(
"""- Fernet Encryption & Decryption         
- Hashing
- Masking
- GDPR
- Asking Consent
- Date Retention Policy
- Role-Based Access
- Action Logging
- Analytic Graph
- Adding/Editing Patients
- Navigation
- Login/Logout
"""
)

st.subheader("Made using:")
st.write("""
- Streamlit
- SQLite
- Python""")