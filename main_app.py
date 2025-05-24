import streamlit as st
import os
import csv
import numpy as np
from datetime import datetime
import qrcode
import cv2
import time
from pyzbar.pyzbar import decode

# File paths
WHITELIST_PATH = "whitelist.txt"
CSV_LOG_PATH = "records.csv"
LOG_PATH = "log.txt"
QR_BASE_DIR = "qr_codes"

# Ensure files and folders exist
os.makedirs(QR_BASE_DIR, exist_ok=True)
if not os.path.exists(WHITELIST_PATH):
    open(WHITELIST_PATH, 'w', encoding='utf-8').close()
if not os.path.exists(CSV_LOG_PATH):
    with open(CSV_LOG_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "ID", "QR Filename", "Created At"])
if not os.path.exists(LOG_PATH):
    open(LOG_PATH, 'w', encoding='utf-8').close()

# Load whitelist
def load_whitelist():
    with open(WHITELIST_PATH, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

# Save to whitelist
def append_to_whitelist(data):
    with open(WHITELIST_PATH, 'a', encoding='utf-8') as f:
        f.write(data + "\n")

# QR generator logic
def generate_qr(name):
    name = name.strip()
    name_parts = name.split()
    initials = (name_parts[0][0].upper() + name_parts[1][0].upper()) if len(name_parts) >= 2 else (name_parts[0][0].upper() + "X")
    unique_id = initials + str(np.random.randint(10000, 99999))
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    message = f"Name: {name} | ID: {unique_id} | Your attendance has been taken successfully."

    today = datetime.now().strftime("%d-%m-%Y")
    qr_folder = os.path.join(QR_BASE_DIR, today)
    os.makedirs(qr_folder, exist_ok=True)

    qr_filename = f"{name.replace(' ', '_')}_{unique_id}_qr.png"
    qr_path = os.path.join(qr_folder, qr_filename)

    qr_img = qrcode.make(message)
    qr_img.save(qr_path)

    whitelist = load_whitelist()
    if message not in whitelist:
        append_to_whitelist(message)

    with open(CSV_LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([name, unique_id, qr_filename, timestamp])

    return qr_path, message

# QR scanner logic.
def start_scanner():
    authorized_users = load_whitelist()
    cap = cv2.VideoCapture(0)
    most_recent_access = {}
    LOG_INTERVAL = 5

    st.success("Scanner started. Press 'p' in the webcam window to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to capture frame.")
            break

        qr_codes = decode(frame)
        for qr in qr_codes:
            data = qr.data.decode('utf-8')
            rect = qr.rect
            polygon = qr.polygon

            if data in authorized_users:
                status = "ACCESS GRANTED"
                color = (0, 255, 0)

                now = time.time()
                if data not in most_recent_access or now - most_recent_access[data] > LOG_INTERVAL:
                    most_recent_access[data] = now
                    with open(LOG_PATH, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"{data},{datetime.now()}\n")
                    name_extracted = data.split("|")[0].replace("Name:", "").strip()
                    st.toast(f"Hello {name_extracted}, your attendance has been taken!")
            else:
                status = "ACCESS DENIED"
                color = (0, 0, 255)

            x, y, w, h = rect.left, rect.top, rect.width, rect.height
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, status, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("QR Attendance Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('p'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Streamlit UI
st.set_page_config(page_title="QR Attendance System", layout="centered")
st.title("QR-Based Attendance System")

tabs = st.tabs(["Generate QR", "Scan QR"])

# Tab 1: Generate QR
with tabs[0]:
    st.subheader("Generate QR Code")
    name_input = st.text_input("Enter Your Full Name")

    if st.button("Generate QR Code"):
        if name_input.strip() == "":
            st.warning("Please enter a valid name.")
        else:
            qr_path, message = generate_qr(name_input)
            st.image(qr_path, caption="Your QR Code")
            with open(qr_path, "rb") as f:
                st.download_button("Download QR Code", f, file_name=os.path.basename(qr_path), mime="image/png")

# Tab 2: Scan QR
with tabs[1]:
    st.subheader("Scan QR Code from Webcam")
    if st.button("Start Scanner", key="start_scanner_button"):
        start_scanner()
