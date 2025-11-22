import sqlite3
from database import get_conn_and_cursor
from enum import Enum
import pandas as pd
from hash_utils import verify_password, anonymize_contact, anonymize_name
from random import randint
from encryption_utils import encrypt, decrypt
from datetime import datetime, timedelta


class ActionsEnum(str, Enum):
    LOGIN = "LOGIN"
    SYNC = "SYNC"
    UPDATE = "UPDATE"
    ADD = "ADD"
    ANONYMIZE = "ANONYMIZE"


def log_action(conn, cursor, user_id: int, role, action, details=None):
    if not conn or not cursor:
        created_now = True
        conn, cursor = get_conn_and_cursor()
    else:
        created_now = False

    try:
        query = "insert into logs (user_id, role, action, details) values (?, ?, ?, ?)"
        cursor.execute(query, (user_id, role, action, details))
        if created_now:
            conn.commit()
            conn.close()
    except sqlite3.Error as e:
        print("\nSQLITE ERROR during logging:", e)
        if created_now:
            conn.rollback()
            conn.close()


def login(username: str, password: str):
    conn, cursor = get_conn_and_cursor()
    query = "select user_id, role, password from users where username = ?"

    # hashed_password = hash(password)
    cursor.execute(query, (username,))
    row = cursor.fetchone()

    if row is None:
        return None

    user_id, role, stored_password = row
    if verify_password(password, stored_password):
        log_action(conn, cursor, user_id, role, action=ActionsEnum.LOGIN)
        conn.close()
        return {"user_id": user_id, "role": role}

    return None


def get_patients(for_role: str):
    conn, cursor = get_conn_and_cursor()

    if for_role == "admin":
        cols = "*"
    elif for_role == "doctor":
        cols = "anonymized_name, anonymized_contact, patient_id, diagnosis, date_added"
    elif for_role == "receptionist":
        cols = "anonymized_name, anonymized_contact, patient_id, diagnosis, date_added"
    else:
        raise ValueError("Invalid role provided")

    query = f"select {cols} from patients"
    df = pd.read_sql_query(con=conn, sql=query)

    def decrypt_cell(enc_text):
        if enc_text:
            return decrypt(enc_text)
        else:
            return ""

    if for_role == "admin":
        df["name"] = df["name"].apply(decrypt_cell)
        df["contact"] = df["contact"].apply(decrypt_cell)

    conn.close()
    return df


def add_patient(added_by_user_id, added_by_role, name, contact, diagnosis):
    conn, cursor = get_conn_and_cursor()
    try:
        query = f"insert into patients (name, contact, diagnosis) values (?, ?, ?)"
        cursor.execute(query, (encrypt(name), encrypt(contact), diagnosis))
        log_action(conn, cursor, added_by_user_id, added_by_role, action=ActionsEnum.ADD)
        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
    finally:
        conn.close()

    return False


def update_patient(updated_by_user_id, updated_by_role, anonymized_name, name, contact, diagnosis):
    conn, cursor = get_conn_and_cursor()
    
    fields = []
    params = []

    if name:
        fields.append("name = ?")
        params.append(encrypt(name))
    if contact:
        fields.append("contact = ?")
        params.append(encrypt(contact))
    if diagnosis:
        fields.append("diagnosis = ?")
        params.append(diagnosis)
    params.append(anonymized_name)

    try:
        query = f"update patients set {", ".join(fields)} where anonymized_name = ?"
        cursor.execute(query, tuple(params))
        log_action(conn, cursor, updated_by_user_id, updated_by_role, action=ActionsEnum.UPDATE, details=f"Updated {len(params)} fields")
        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
    finally:
        conn.close()

    return False


def get_logs():
    conn, cursor = get_conn_and_cursor()

    query = f"select * from logs order by timestamp desc"
    df = pd.read_sql_query(con=conn, sql=query)

    conn.close()
    return df


def anonymize(user_id):
    conn, cursor = get_conn_and_cursor()

    try:
        cursor.execute(
            "select patient_id, contact from patients"
        )  # all, not only unencrypted ones, so that patients whose details got updated later also get encrypted

        rows = cursor.fetchall()

        multiplier = randint(11, 19)
        for patient_id, contact in rows:
            # print(
            #     (anonymize_name(id=patient_id, multiplier=multiplier), anonymize_contact(decrypt(contact)), patient_id),
            # )
            cursor.execute(
                "update patients set anonymized_name = ?, anonymized_contact = ? where patient_id = ?",
                (anonymize_name(id=patient_id, multiplier=multiplier), anonymize_contact(decrypt(contact)), patient_id),
            )

        log_action(conn, cursor, user_id, "admin", ActionsEnum.ANONYMIZE)
        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
    finally:
        conn.close()

    return False


def delete_old_data(days=365):
    conn, cursor = get_conn_and_cursor()

    try:
        old_date = datetime.now() - timedelta(days=days)

        cursor.execute("delete from patients where date_added < ?", (old_date,))
        count = cursor.rowcount

        cursor.execute("delete from logs where timestamp < ?", (old_date,))
        count += cursor.rowcount

        conn.commit()
        conn.close()
        return count
    except Exception as e:
        print(e)
        conn.rollback()
        conn.close()

    return -1
