import streamlit as st
from utils import isLoggedIn
from services import get_patients, get_logs, log_action, ActionsEnum, anonymize, update_patient, add_patient, delete_old_data
import datetime
from home import ask_consent
import plotly.express as px
import pandas as pd

if not isLoggedIn(st.session_state):
    st.switch_page("pages/login.py")


# temp:
# st.session_state["role"] = "admin"
# st.session_state["user_id"] = 2
# st.session_state["username"] = "Mr_Bob"


st.set_page_config("Dashboard", page_icon=":material/dashboard:", initial_sidebar_state="collapsed")

ask_consent()

# header
left, right = st.columns([0.83, 0.17], vertical_alignment="center")
with left:
    st.title(":material/dashboard: Hospital Dashboard", width="stretch")
with right:
    logout_btn = st.button("Logout", width="stretch", type="primary", icon=":material/logout:")
    if logout_btn:
        st.session_state.clear()
        st.switch_page("pages/login.py")


role = st.session_state["role"]
user_id = st.session_state["user_id"]
username = st.session_state["username"]

left, right = st.columns([0.85, 0.15], vertical_alignment="center")
with left:
    st.markdown(f"### *Hey {username}!*")
with right:
    # badge color
    if role == "admin":
        color = "blue"
    elif role == "receptionist":
        color = "red"
    elif role == "doctor":
        color = "green"
    else:
        color = "yellow"
    st.badge(role.upper(), color=color, width="content")


now = datetime.datetime.now()


if role == "receptionist" or role == "admin":
    left, right = st.columns(2)

    with left:  # add form
        add_form = st.form("Add Patient")
        add_form.subheader("Add Patient")
        name = add_form.text_input("Name")
        contact = add_form.text_input("Contact")
        diagnosis = add_form.text_input("Diagnosis")
        add_form.title("")
        submit = add_form.form_submit_button("Add", icon=":material/add:", width="stretch")
        if submit:
            name = name.strip()
            contact = contact.strip()
            diagnosis = diagnosis.strip()
            if len(name) < 3 or len(contact) < 7 or len(diagnosis) < 1:
                add_form.error("Please provide correct data")
            else:
                if add_patient(user_id, role, name, contact, diagnosis):
                    add_form.success("Patient added successfully!")
                else:
                    add_form.error("There was an error adding the patient.")

    with right:  # edit form
        edit_form = st.form("Edit Patient (leave fields empty if no change)")
        edit_form.subheader("Edit Patient")
        anonymized_name = edit_form.text_input("Current Anonymized Name")
        name = edit_form.text_input("New Name")
        contact = edit_form.text_input("New Contact")
        diagnosis = edit_form.text_input("New Diagnosis")
        submit = edit_form.form_submit_button("Update", icon=":material/edit:", width="stretch")
        if submit:
            anonymized_name = anonymized_name.strip()
            name = name.strip()
            contact = contact.strip()
            diagnosis = diagnosis.strip()

            error = None

            if len(anonymized_name) == 0:
                anonymized_name = None
            elif len(anonymized_name) < 7:
                error = "Please provide correct anonymized name"

            if len(name) == 0:
                name = None
            elif len(name) < 3:
                error = "Please provide correct name"

            if len(contact) == 0:
                name = None
            elif len(contact) < 7:
                error = "Please provide correct contact"

            if len(diagnosis) == 0:
                diagnosis = None
            elif len(diagnosis) < 1:
                error = "Please provide correct diagnosis"

            if error:
                st.error(error)
            else:
                if update_patient(user_id, role, anonymized_name, name, contact, diagnosis):
                    edit_form.success("Patient updated successfully!")
                else:
                    edit_form.error("There was an error updating the patient.")


st.divider()


# tables
@st.fragment
def show_tables():
    global now
    now = datetime.datetime.now()

    log_action(None, None, action=ActionsEnum.SYNC, user_id=user_id, role=role)

    left, middle, right, _ = st.columns([0.7, 0.98, 2, 1])
    with left:
        sync_btn = st.button("Sync", icon=":material/refresh:")
        if sync_btn:
            st.rerun(scope="fragment")
    if role == "admin":
        with middle:
            if role == "admin":
                anonymize_btn = st.button("Anonymize", icon=":material/grid_3x3_off:")
                if anonymize_btn:
                    if anonymize(user_id):
                        st.rerun(scope="fragment")
                    else:
                        st.error("There was an error while anonymizing.")
        with right:
            if st.button("Delete Old Data", icon=":material/delete:"):
                row_count = delete_old_data()
                if row_count >= 0:
                    st.success(f"Deleted {row_count} rows totally")
                else:
                    st.error("There was an error deleting old data")

    patients = get_patients(role)
    st.subheader(":material/patient_list: Patients")
    st.dataframe(patients)

    if role == "admin":
        logs = get_logs()
        st.subheader(":material/call_received: Logs")
        st.dataframe(logs)

        # analytics
        st.subheader(":material/analytics: Analytics")
        logs["timestamp"] = pd.to_datetime(logs["timestamp"])  # convert to actual timestamp format
        date_part_only = logs["timestamp"].dt.date
        grouped = logs.groupby([date_part_only, "action"]).size().reset_index(name="count")
        # size() counts count for each group, reset_index() converts to dataframe
        grouped.rename(columns={"timestamp": "date"}, inplace=True)
        figure = px.bar(grouped, x="date", y="count", color="action", barmode="group", title="Activity per day")
        st.plotly_chart(figure)

    # last synchronized
    last_sync_time = "{day}/{month}/{year} {hour}:{minute}:{second}".format(
        day=now.day, month=now.month, year=now.year, hour=now.hour, minute=now.minute, second=now.second
    )
    st.info(f"Last synchronized: {last_sync_time}")


show_tables()
