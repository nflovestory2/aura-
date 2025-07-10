import os
import io
import time
import base64
import json
import sqlite3
import threading
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename
from gtts import gTTS
import numpy as np
import cv2
from cryptography.fernet import Fernet
from PIL import Image
import pytesseract
import face_recognition
from deepface import DeepFace
import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS
from googletrans import Translator
from difflib import get_close_matches
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import credentials, storage
from googleapiclient.http import MediaFileUpload
import firebase_admin
from firebase_admin import credentials, firestore
from TTS.api import TTS  
# For WiFi control (Linux example, adjust for your platform)
import subprocess

app = Flask(__name__)
CORS(app) 

schedule.every().day.at("23:59").do(backup_to_drive) 
while True:
    schedule.run_pending()
    time.sleep(1)
DB_PATH = 'memory.db'
# 🗂️ ফোল্ডার তৈরি
os.makedirs("audio", exist_ok=True)

app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.secret_key = 'your_secret_key_here'  # সিক্রেট কী সেট করুন
app.config['SESSION_TYPE'] = 'filesystem'  # সেশন ফাইল সিস্টেমে সেভ হবে
Session(app)

# প্রাইভেট PIN (আপনি চাইলে ডাটাবেজ থেকে নিতে পারেন)
PRIVATE_PIN = "1234"

# Face cascade লোড
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Directories
UPLOAD_FOLDER = "uploads"
AUDIO_FOLDER = "audio"
MEMORY_IMG_FOLDER = "memory_images"
FIRMWARE_FOLDER = "static"

for folder in [UPLOAD_FOLDER, AUDIO_FOLDER, MEMORY_IMG_FOLDER, FIRMWARE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Globals
face_db = {}
current_emotion = "neutral"
# Dummy data (পরবর্তীতে DB বা মেমোরি থেকে আসবে)
face_logs = [
    {"name": "Joy", "time": "2025-06-27 12:30"},
    {"name": "Anika", "time": "2025-06-27 13:00"}
]
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-bucket.appspot.com'
})
memory_timeline = [
    {"timestamp": "2025-06-26 18:00", "text": "Joy came home"},
    {"timestamp": "2025-06-27 10:00", "text": "Anika asked about weather"}
]

# পরিচিত মুখের এনকোডিং ও নাম লোড/সেভ করার ফোল্ডার
KNOWN_FACES_DIR = "./known_faces"
known_face_encodings = []
known_face_names = []
wifi_profiles = [
    {"ssid": "HomeWiFi", "status": "Connected"},
    {"ssid": "OfficeWiFi", "status": "Saved"}
]
# Load face_db from file if exists
SECRET_KEY = os.getenv("FACE_DB_KEY")
if not SECRET_KEY:
    # ডেভেলপমেন্টে এই কী ব্যাবহার হবে (৩২ বাইট length & base64 encoded)
    SECRET_KEY = base64.urlsafe_b64encode(b'my_super_secret_key_1234_32bytes!')

fernet = Fernet(SECRET_KEY)
def translate_text(text, dest_language='en'):
    result = translator.translate(text, dest=dest_language)
    return result.text
def upload_to_firebase(local_path, remote_name):
    bucket = storage.bucket()
    blob = bucket.blob(remote_name)
    blob.upload_from_filename(local_path)
    print(f"✅ Firebase Uploaded: {remote_name}")

def translate_to_bengali(text):
    return translate_text(text, dest_language='bn')
def save_face_db_encrypted(face_db, filename="face_db.json.enc"):
    try:
        json_data = json.dumps(face_db).encode('utf-8')
        encrypted = fernet.encrypt(json_data)
        with open(filename, "wb") as f:
            f.write(encrypted)
        print("Face DB saved encrypted successfully.")
    except Exception as e:
        print(f"Error saving encrypted face DB: {e}")
def load_known_faces():
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            path = os.path.join(KNOWN_FACES_DIR, filename)
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_face_encodings.append(encodings[0])
                name = os.path.splitext(filename)[0]
                known_face_names.append(name)
    print(f"Loaded faces: {known_face_names}")
def query_memories():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT text FROM memories WHERE private=0")
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]
def init_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

drive = init_drive()

def backup_to_drive():
    folder_name = datetime.now().strftime("Backup_%Y%m%d_%H%M%S")
    
    # Google Drive-এ ফোল্ডার বানাও
    folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    folder_id = folder['id']
    
    files_to_upload = [
        ('memory.db', 'memory.db'),
        ('audio/memory/', 'audio_files'),
        ('memory_images/', 'images')
    ]
    
    for path, name in files_to_upload:
        if os.path.isfile(path):
            f = drive.CreateFile({'title': name, 'parents':[{'id': folder_id}]})
            f.SetContentFile(path)
            f.Upload()
            print(f"✅ Uploaded file: {name}")
        elif os.path.isdir(path):
            for file in os.listdir(path):
                full_path = os.path.join(path, file)
                if os.path.isfile(full_path):
                    f = drive.CreateFile({'title': file, 'parents':[{'id': folder_id}]})
                    f.SetContentFile(full_path)
                    f.Upload()
                    print(f"📁 Uploaded: {file}")
def load_face_db_encrypted(filename="face_db.json.enc"):
    try:
        with open(filename, "rb") as f:
            encrypted = f.read()
        decrypted = fernet.decrypt(encrypted)
        face_db = json.loads(decrypted.decode('utf-8'))
        print("Face DB loaded decrypted successfully.")
        return face_db
    except Exception as e:
        print(f"Error loading encrypted face DB: {e}")
        return {}
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            text TEXT,
            private INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def load_face_db():
    global face_db
    face_db = load_face_db_encrypted()

def save_face_db():
    save_face_db_encrypted(face_db)

def load_face_database():
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    
    if not os.path.exists("faces"):
        os.makedirs("faces")
        return
    
    for filename in os.listdir("faces"):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            name = filename.rsplit('.', 1)[0]
            image_path = os.path.join("faces", filename)
            image = face_recognition.load_image_file(image_path)
            encoding = face_recognition.face_encodings(image)
            if encoding:
                known_face_encodings.append(encoding[0])
                known_face_names.append(name)

load_face_database()
# ✅ ফোল্ডারের সাইজ গণনা ফাংশন
def get_folder_size(path):
    if not os.path.exists(path):
        return 0
    return sum(
        os.path.getsize(os.path.join(path, f))
        for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f))
    )
 #... Memory. db
def create_image_memory_table():
    conn = sqlite3.connect("memory.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS image_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        desc TEXT,
        path TEXT
    );
    """)
    conn.commit()
    conn.close()
    print("✅ image_memory টেবিল তৈরি হয়েছে")

# একবার রান করানো
create_image_memory_table()
    
# Initialize SQLite  DBs 
def init_databases():
    with sqlite3.connect("face_memory.db") as conn:
        rows = conn.execute("SELECT name, encoding FROM faces").fetchall()

    with sqlite3.connect("memory.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS memories (time TEXT, question TEXT, answer TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS image_memory (desc TEXT, path TEXT)")
    with sqlite3.connect("aura.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS surveillance (filename TEXT, timestamp TEXT)")

init_databases()

# Utility Functions
def execute_shell_command(cmd):
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        return result
    except subprocess.CalledProcessError as e:
        return str(e.output)

def get_stored_pin():
    return os.getenv("AURA_PIN", "1234") 
def read_all_sensors():
    # Placeholder sensor data
    return {
        "temperature": 25.3,
        "humidity": 60,
        "light": 120,
        "motion": False,
    }
    
def get_notifications():
    return [
        {"title": "System Online", "time": datetime.now().isoformat()},
        {"title": "Memory Updated", "time": datetime.now().isoformat()}
    ]
def get_usage_statistics():
    return {"uptime_hours": 123, "commands_processed": 456}
def get_system_status():
    return {
        "cpu_usage": 45,
        "memory_usage": 67,
        "disk_usage": 23,
        "temperature": 42,
        "status": "online"
    }
def save_schedule(time_str, task):
    with open("schedule.txt", "a") as f:
        f.write(f"{time_str} | {task}\n")

def speak(text):
    tts = TTS("tts_models/multilingual/multi-dataset/your_model", gpu=False)
    path = "output.wav"
    tts.tts_to_file(text=text, file_path=path)
    play_audio_file(path)

def load_all_memories():
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT time, question, answer FROM memories ORDER BY time DESC")
    rows = c.fetchall()
    conn.close()
    return [{"time": r[0], "question": r[1], "answer": r[2]} for r in rows]

def load_private_memories():
    # Example: you can add access control here
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT time, question, answer FROM memories WHERE question LIKE '%private%' ORDER BY time DESC")
    rows = c.fetchall()
    conn.close()
    return [{"time": r[0], "question": r[1], "answer": r[2]} for r in rows]

def load_emotion_log():
  
    # Could read from a log file or DB, here simple placeholder
    return [{"time": datetime.now().isoformat(), "emotion": current_emotion}]

def search_memory_by_question(query):
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT question, answer FROM memories")
    results = c.fetchall()
    conn.close()

    match = get_close_matches(query, [r[0] for r in results], n=1, cutoff=0.5)
    if match:
        for q, a in results:
            if q == match[0]:
                return a
    return "দুঃখিত, আমি এই প্রশ্নের উত্তর খুঁজে পেলাম না।"

def show_emoji_on_oled(emoji):
    # Placeholder: Replace with actual OLED display code
    print(f"Displaying emoji on OLED: {emoji}")

def save_reminder(data):
    with open("reminders.json", "a") as f:
        f.write(json.dumps(data) + "\n")

def save_profile(name):
    with open("profile.txt", "w") as f:
        f.write(name)

def ask_gpt(query):
    # Integrate your GPT model or OpenAI API here
    return "AI response for: " + query

def fetch_weather(location):
    # Integrate weather API here
    return {"location": location, "temperature": "30°C", "condition": "Sunny"}

def chat_with_gpt(msg):
    # ChatGPT integration here
    return "GPT reply for: " + msg

def run_ocr(file):
    img = Image.open(file.stream)
    text = pytesseract.image_to_string(img, lang='ben+eng+hin+tam+guj+kan+mal+mar+ori+pan+tel+urd+ara+chi_sim+fra+deu+spa')
    return text

def toggle_plugin_state(plugin):
    # Save plugin toggle state (dummy example)
    print(f"Plugin toggled: {plugin}")

def get_usage_statistics():
    # Placeholder stats
    return {"uptime_hours": 123, "commands_processed": 456}

def activate_dream_mode():
    print("Dream mode activated")

def save_custom_command(cmd):
    with open("custom_commands.txt", "a") as f:
        f.write(cmd + "\n")
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def sync_memory_to_firebase():
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("SELECT time, question, answer FROM memories")
    rows = c.fetchall()
    conn.close()

    for row in rows:
        data = {
            "time": row[0],
            "question": row[1],
            "answer": row[2]
        }
        db.collection("memories").add(data)

def detect_gesture():
    # Placeholder gesture detection
    return "wave"

def is_call_active():
    return False

def get_latest_camera_frame():
    path = "memory_images/sample.jpg"
    if os.path.exists(path):
        return path
    else:
        return "static/placeholder.jpg"

    
def create_placeholder_image():
    placeholder_path = "static/placeholder.jpg"
    if not os.path.exists(placeholder_path):
            # Create a simple placeholder image (1x1 pixel)
        with open(placeholder_path, "wb") as f:
            # Minimal JPEG header for a 1x1 white pixel
            f.write(bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46]))

create_placeholder_image()

# Routes
@app.route('/api/capture', methods=['POST'])  # ⬅️ এখানে রাখুন
def capture_image():
    file = request.files['image']
    desc = request.form.get('desc', 'no description')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}.jpg"
    path = os.path.join(MEMORY_IMG_FOLDER, filename)
    file.save(path)

    # Save to SQLite
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    c.execute("INSERT INTO image_memory (desc, path) VALUES (?, ?)", (desc, path))
    conn.commit()
    conn.close()

    return jsonify({"saved": True, "filename": filename})

def upload_to_drive(filepath):
    creds = Credentials.from_service_account_file("credentials.json")
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': os.path.basename(filepath)}
    media = MediaFileUpload(filepath, mimetype='application/octet-stream')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file.get('id') 
    
def tts_generate(text, lang="bn"):
    filename = f"tts_{int(time.time())}.mp3"
    filepath = os.path.join("audio", filename)
    os.makedirs("audio", exist_ok=True)
    tts = gTTS(text=text, lang=lang)
    tts.save(filepath)
    # Optional: log
    with open("tts_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}: {filename} | lang={lang} | {text}\n")
    return filepath

def save_memory(question, answer):
    conn = sqlite3.connect("memory.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO memories (time, question, answer) VALUES (?, ?, ?)", (now, question, answer))
    conn.commit()
    conn.close()
    
# ---------------------------
# WiFi Auto Connect & Scan APIs
# ---------------------------

def wifi_scan_networks():
    """
    Scan WiFi networks (Linux example, adjust as per platform)
    Returns a list of dict {ssid, signal}
    """
    try:
        scan_result = subprocess.check_output("nmcli -f SSID,SIGNAL dev wifi list", shell=True, universal_newlines=True)
        networks = []
        for line in scan_result.strip().split("\n")[1:]:
            parts = line.strip().split()
            if len(parts) >= 2:
                ssid = " ".join(parts[:-1]).strip()
                signal = parts[-1]
                if ssid:
                    networks.append({"ssid": ssid, "signal": int(signal)})
        return networks
    except Exception as e:
        return []

def wifi_connect(ssid, password):
    """
    Connect to WiFi using nmcli (Linux example)
    """
    try:
        # Remove old connection if exists
        subprocess.call(f"nmcli connection delete '{ssid}'", shell=True)
    except:
        pass
    try:
        connect_cmd = f"nmcli dev wifi connect '{ssid}' password '{password}'"
        output = subprocess.check_output(connect_cmd, shell=True, universal_newlines=True)
        return True, output
    except Exception as e:
        return False, str(e)

@app.route('/api/wifi_scan', methods=['GET'])
def api_wifi_scan():
    networks = wifi_scan_networks()
    # Sort by signal descending
    networks.sort(key=lambda x: x["signal"], reverse=True)
    return jsonify(networks)

@app.route('/api/wifi_connect', methods=['POST'])
def api_wifi_connect():
    data = request.json
    ssid = data.get("ssid")
    password = data.get("password")
    
    if not ssid or not password:
        return jsonify({"success": False, "message": "SSID and password required"}), 400

    success, msg = wifi_connect(ssid, password)
    
    if success:
        return jsonify({"success": True, "message": f"Connected to {ssid}"})
    else:
        return jsonify({"success": False, "message": msg})

# ----------1.Memory Gallery----------
@app.route('/api/memory', methods=['GET'])
def get_memory():
    # Memory DB থেকে সব মেমরি রিটার্ন করুন
    return jsonify(load_all_memories())
    # ----------  2. Speak to Aura
@app.route('/api/speak', methods=['POST'])
def speak_to_aura():
    data = request.json
    text = data.get("text")
    
    lang = data.get("lang", "ben")
    if not text:
        return jsonify({"error": "No text received"}), 400


    try:
        filepath = tts_generate(text, lang)  # 🔁 রিইউজ ফাংশন
        return send_file(filepath, mimetype='audio/mp3')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
  
    # ---------- 3. Schedule Task
@app.route('/api/schedule', methods=['POST'])
def schedule_task():
    data = request.json
    time = data.get("time")
    task = data.get("task")
    save_schedule(time, task)
    return jsonify({"status": "Scheduled"})
   # ----------  4. Emotion Timeline
@app.route('/api/emotion_timeline', methods=['GET'])
def get_emotion_timeline():
    return jsonify(load_emotion_log())
   # ----------  5. Sensor Monitor
@app.route('/api/sensors', methods=['GET'])
def get_sensor_data():
    return jsonify(read_all_sensors())
   # ----------  6. Command Console
@app.route('/api/command', methods=['POST'])
def command_console():
    cmd = request.json.get("cmd")
    output = execute_shell_command(cmd) 
    return jsonify({"output": f"Command executed: {output}"})

   # ----------  7. Secure Access (PIN)
@app.route('/api/unlock', methods=['POST'])
def unlock():
    pin = request.json.get("pin")
    if pin == get_stored_pin():
        return jsonify({"unlocked": True})
    return jsonify({"unlocked": False})
   # ----------  8. Cloud Backup
@app.route('/api/backup', methods=['GET'])
def backup_data():
    return send_file("memory_backup.json")

def restore_from_file(file):
    data = json.load(file)
    with open("memory_backup.json", "w") as f:
        json.dump(data, f)

@app.route('/api/restore', methods=['POST'])
def restore_data():
    file = request.files['file']
    restore_from_file(file)
    return jsonify({"restored": True})

    
    # ---------- 9. OTA Firmware Upload
@app.route('/api/ota', methods=['POST'])
def ota_update():
    file = request.files['firmware']
    file.save('static/firmware.bin')
    return jsonify({"status": "uploaded"})
    # ----------10. Private Memory
@app.route('/api/private_memory', methods=['GET'])
def private_memory():
    return jsonify(load_private_memories())
    # ---------- 11. Live Camera
@app.route('/api/live_frame', methods=['GET'])
def live_camera():
    return send_file(get_latest_camera_frame(), mimetype='image/jpeg')
   # ----------  12. System Status
@app.route('/api/status', methods=['GET'])
def system_status():
    return jsonify(get_system_status())
   # ----------  13. Emotion Emoji
@app.route('/api/emoji', methods=['POST'])
def set_emoji():
    emoji = request.json.get("emoji")
    show_emoji_on_oled(emoji)
    print(f"Emoji set: {emoji}")
    return jsonify({"status": "ok"})
    
   # ----------  14. Reminder
@app.route('/api/reminder', methods=['POST'])
def set_reminder():
    data = request.json
    save_reminder(data)
    return jsonify({"status": "Reminder set"})
   # ----------  15. Smart Profile
@app.route('/api/profile', methods=['POST'])
def set_profile():
    name = request.json.get("name")
    save_profile(name)
    return jsonify({"saved": True})
    # ----------  16.AI Console
@app.route('/api/ai_console', methods=['POST'])
def ai_console():
    query = request.json.get("query")
    response = ask_gpt(query) 
    return jsonify({"response": response})
   # ----------  17. Weather System
@app.route('/api/weather', methods=['POST'])
def weather():
    location = request.json.get("location")
    data = fetch_weather(location) 
    data = {"location": location, "temperature": "25°C", "condition": "Sunny"} 
    return jsonify(data)
    # ---------- 18. GPT Chat
@app.route('/api/gpt_chat', methods=['POST'])
def gpt_chat():
    msg = request.json.get("msg")
    reply = chat_with_gpt(msg) 
    reply = f"GPT reply for: {msg}"
    return jsonify({"reply": reply})
    # ---------- 19. OCR Upload 
 

@app.route("/ocr_stream", methods=["POST"])
def ocr_api():
    image = Image.open(io.BytesIO(request.data))
    text = pytesseract.image_to_string(image, lang="eng+ben")
    save_to_memory("ocr", text)
    speak(text)  # নিচে ব্যাখ্যা
    return jsonify({"text": text})

    # ---------- 20. Plugin Toggle
@app.route('/api/plugin_toggle', methods=['POST'])
def toggle_plugin():
    plugin = request.json.get("plugin")
    toggle_plugin_state(plugin)
    return jsonify({"toggled": True})
   # ----------  21. Audio Library
@app.route('/api/play_audio', methods=['POST'])
def play_audio():
    audio_file = request.json.get("file")
    return send_file(f"audio/{audio_file}", mimetype='audio/mp3')
    # ---------- 22. Notification
@app.route('/api/notifications', methods=['GET'])
def notifications():
    return jsonify(get_notifications())
   # ----------  23. Usage Stats
@app.route('/api/usage_stats', methods=['GET'])
def usage_stats():
    return jsonify(get_usage_statistics())
   # ----------  24. Dream Mode
@app.route('/api/dream_mode', methods=['POST'])
def dream_mode():
    activate_dream_mode()
    return jsonify({"status": "Started"})
   # ----------  25. Custom Command
@app.route('/api/custom_command', methods=['POST'])
def custom_command():
    cmd = request.json.get("cmd")
    save_custom_command(cmd)
    return jsonify({"saved": True})
   
  # ----------   26. Gesture Control
@app.route('/api/gesture', methods=['POST'])
def gesture():
    result = detect_gesture()
    return jsonify({"gesture": result})
   # ----------  27. WebRTC Video Call
@app.route('/api/webrtc_status', methods=['GET'])
def webrtc_status():
    return jsonify({"call_active": is_call_active()})
    # ---------- 28.Face Detection
@app.route('/api/face_detect', methods=['POST'])
def face_detect():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    img = Image.open(file.stream).convert("RGB")
    img_np = np.array(img)

    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    face_data = []
    for (x, y, w, h) in faces:
        face_data.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
        # Optionally draw rectangles on image (not returned)
        cv2.rectangle(img_np, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return jsonify({"faces_detected": len(faces), "faces": face_data})

# ---------- 29: Face Recognition
@app.route('/face_add', methods=['POST'])
def face_add():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({'error': 'Image and name required'}), 400

    file = request.files['image']
    name = request.form['name']

    img = face_recognition.load_image_file(file.stream)
    encodings = face_recognition.face_encodings(img)

    if len(encodings) == 0:
        return jsonify({'error': 'No face found'}), 400

    # Save encoding with name
    face_db[name] = encodings[0].tolist()
    save_face_db()

    return jsonify({'success': True, 'message': f"Face saved for {name} ✅"})

# //face_check

@app.route('/face_check', methods=['POST'])
def face_check():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    img = face_recognition.load_image_file(file.stream)
    encodings = face_recognition.face_encodings(img)

    if len(encodings) == 0:
        return jsonify({'matched': False, 'name': 'No face detected'})

    unknown_encoding = encodings[0]

    for name, saved_encoding in face_db.items():
        known_encoding = np.array(saved_encoding)
        match = face_recognition.compare_faces([known_encoding], unknown_encoding)[0]
        if match:
            return jsonify({'matched': True, 'name': name})

    return jsonify({'matched': False, 'name': 'Unknown'})

  
# ---------- 30. OCR (base64 image upload) ----------
@app.route("/ocr_base64", methods=["POST"])
def ocr_read():
    data = request.json.get("image_base64", "")
    if not data:
        return jsonify({"error": "No image_base64 found in request"}), 400
    try:
        image_data = base64.b64decode(data.split(",")[1])
        with open("temp_ocr.jpg", "wb") as f:
            f.write(image_data)
        text = pytesseract.image_to_string(Image.open("temp_ocr.jpg"), lang='ben+eng')
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- OCR (direct image file upload) ----------
@app.route("/ocr_image", methods=["POST"])
def ocr_image():
    if 'image' not in request.files:
        return jsonify({'error': 'Image not found'}), 400
    # Simulate OCR
    text = "Sample OCR text extracted from image"
    
    image_file = request.files['image']
    img = Image.open(image_file.stream)

# OCR (বাংলা + ইংরেজি একসাথে)
    text = pytesseract.image_to_string(img, lang='ben+eng')

    return jsonify({'text': text})
    
# ---------- 31. Emotion ----------
@app.route("/emotion", methods=["POST"])
def detect_emotion():
    if 'image' not in request.files:
        return jsonify({'error': 'Image not found'}), 400

    file = request.files['image'].read()
    npimg = np.frombuffer(file, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    try:
        result = DeepFace.analyze(img, actions=['emotion'], enforce_detection=False)
        dominant_emotion = result[0]['dominant_emotion']
        emotions = ["happy", "sad", "angry", "neutral", "surprise"]
        emotion = np.random.choice(emotions)
        global current_emotion
        current_emotion = emotion

    
        emoji_map = {
            "happy": "😊",
            "sad": "😢",
            "angry": "😠",
            "surprise": "😮",
            "neutral": "😐",
            "fear": "😨",
            "disgust": "🤢"
        }
        emoji = emoji_map.get(dominant_emotion, "😐")

        return jsonify({"emotion": dominant_emotion, "emoji": emoji})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------- 32.Send Image to Server
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'image_{timestamp}.jpg'
    save_path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(save_path)
    return jsonify({'message': 'Image saved', 'filename': filename})
  # ---------- . 33. Surveillance Timeline
@app.route('/timeline')
def timeline():
    conn = sqlite3.connect("aura.db")
    c = conn.cursor()
    c.execute("SELECT filename, timestamp FROM surveillance ORDER BY timestamp DESC")
    data = c.fetchall()
    conn.close()

    return jsonify([
        {"filename": row[0], "timestamp": row[1]}
        for row in data
    ])
   # ----------  34.Live Emotion Stream
@app.route("/detect_emotion", methods=["POST"])
def detect_emotion_live():
    if 'image' not in request.files:
        return jsonify({'error': 'Image not found'}), 400

    file = request.files['image']
    try:
        image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
        result = DeepFace.analyze(image, actions=['emotion'], enforce_detection=False)
        emotion = result[0]["dominant_emotion"]
        return jsonify({"emotion": emotion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- 35. Face Add + Recall ----------
@app.route('/add_face', methods=['POST'])
def add_face():
    if 'name' not in request.form or 'image' not in request.files:
        return jsonify({"error": "Name or image missing"}), 400
    
    name = request.form['name']
    file = request.files['image']
    img_bytes = file.read()
    
    img = Image.open(io.BytesIO(img_bytes))
    img.save(f"faces/{name}.jpg")
    
    # আপডেট ফেস ডাটাবেস
    load_face_database()
    
    return jsonify({"status": f"Face for {name} added."})

@app.route('/recognize', methods=['POST'])
def recognize():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['image']
    img_bytes = file.read()
    img = face_recognition.load_image_file(io.BytesIO(img_bytes))
    
    unknown_encodings = face_recognition.face_encodings(img)
    if not unknown_encodings:
        return jsonify({"result": "No face found"})
    
    results = []
    for unknown_encoding in unknown_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, unknown_encoding)
        face_distances = face_recognition.face_distance(known_face_encodings, unknown_encoding)
        
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
            else:
                name = "Unknown"
        else:
            name = "Unknown"
        
        results.append({"name": name})
    
    return jsonify({"results": results})

# ---------- 36. Voice STT ----------
@app.route("/stt", methods=["POST"])
def speech_to_text():
    if 'audio' not in request.files:
        return jsonify({'error': 'Audio file required'}), 400

    r = sr.Recognizer()
    audio_file = request.files['audio']

    try:
        with sr.AudioFile(audio_file) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="bn-BD")
        return jsonify({"text": text})
    except Exception as e:
        # যদি Speech-to-Text fail করে, fallback text পাঠাও
        fallback_text = "Hello, this is sample speech to text output (simulated)"
        return jsonify({"text": fallback_text, "error": str(e)})

# ---------- 37 Image Memory ----------
@app.route("/image_add", methods=["POST"])
def add_image_memory():
    image = request.files["image"]
    desc = request.form["desc"]

    # ফাইল সেভ
    filename = secure_filename(f"{int(time.time())}.jpg")
    path = os.path.join("memory_images", filename)
    os.makedirs("memory_images", exist_ok=True)
    image.save(path)

    # ডেটাবেজে সেভ
    conn = sqlite3.connect("memory.db")
    conn.execute("INSERT INTO image_memory (desc, path) VALUES (?, ?)", (desc, path))
    conn.commit()
    conn.close()

    return jsonify({"status": "Image saved ✅"})

@app.route("/image_search", methods=["GET"])
def search_image_memory():
    q = request.args.get("q", "").lower()

    conn = sqlite3.connect("memory.db")
    rows = conn.execute("SELECT desc, path FROM image_memory").fetchall()
    conn.close()

    for desc, path in rows:
        if q in desc.lower():
            return send_file(path, mimetype='image/jpeg')

    return jsonify({"status": "No match found ❌"})


# ---------- 38. PIN Unlock ----------
@app.route("/unlock", methods=["POST"])
def unlock_memory():
    data = request.json
    pin = data.get("pin")
    if pin == "1234":
        return jsonify({"access": "granted"})
    else:
        return jsonify({"access": "denied"})

# ---------- 39. Timeline Memory ----------
@app.route("/memory", methods=["GET"])
def search_memory():
    q = request.args.get("q", "")
    conn = sqlite3.connect("memory.db")
    rows = conn.execute("SELECT time, question, answer FROM memories").fetchall()
    for time_, question, answer in rows:
        if q in question.lower():
            return jsonify({"answer": answer, "time": time_})
    return jsonify({"status": "not found"})

# ---------- 40. Idle / Greeting ----------
@app.route("/idle", methods=["GET"])
def idle_speech():
    return send_file("audio/idle1.mp3")

@app.route("/greeting", methods=["GET"])
def greeting():
    return send_file("audio/greeting.mp3")

# ---------- 41. Translate + TTS ----------
@app.route("/translate", methods=["POST"])
def translate_text():
    data = request.json
    text = data["text"]
    lang = data["lang"]
    trans = Translator().translate(text, dest=lang)
    return jsonify({"translated": trans.text})

@app.route("/tts", methods=["POST"])
def text_to_speech():
    text = request.json.get("text", "")
    if not text:
        return jsonify({"error": "Text is required"}), 400

    filename = "temp.mp3"
    tts = gTTS(text=text, lang="bn")
    tts.save(filename)

    @after_this_request
    def remove_file(response):
        try:
            os.remove(filename)
        except Exception:
            pass
        return response

    return send_file(filename, mimetype="audio/mpeg")


# appi/tts
@app.route('/api/tts', methods=['POST'])
def api_tts_generate():
    data = request.json
    text = data.get("text", "")
    lang = data.get("lang", "bn")  # 👉 ডিফল্ট বাংলা

    # ✅ সাপোর্টেড ল্যাঙ্গুয়েজ চেক
    supported_langs = ['bn', 'en', 'hi', 'ta', 'gu', 'ml', 'kn', 'mr']
    if lang not in supported_langs:
        return jsonify({"error": f"Unsupported language: {lang}. Supported: {supported_langs}"}), 400

    if not text:
        return jsonify({"error": "Text is required"}), 400

    try:
        audio_path = tts_generate(text, lang)
        return send_file(audio_path, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- 42 Servo ----------
@app.route("/servo", methods=["GET"])
def servo_control():
    cmd = request.args.get("cmd", "")
    with open("/dev/ttyUSB1", "w") as f:
         f.write("left\n")
    return jsonify({"status": f"Command sent: {cmd}"})

# ---------- 43. Play Audio ----------
@app.route("/play", methods=["GET"])
def play_mp3():
    filename = request.args.get("file", "greeting.mp3")
    path = os.path.join("audio", filename)
    return send_file(path, mimetype="audio/mpeg")

# ---------- .44 Web UI ----------
@app.route("/")
def index():
    return render_template("index.html")
# ------ 45. Voice/Command Trigger 
@app.route('/command', methods=['POST'])
def handle_command():
    cmd = request.form.get("cmd")
    if not cmd:
        return "No command!", 400

    print(f"[ESP32] Command received: {cmd}")

    # 🔘 Wake/Greeting
    if cmd == "wake_up":
        return "Robot is now awake!"
    elif cmd == "greet_user":
        return "Hello! Welcome!"

    # 🔘 Face/Camera Features
    elif cmd == "face_save":
        return "Saving new face"
    elif cmd == "face_recognize":
        return "Recognizing face"
    elif cmd == "camera_capture":
        return "Capturing image"
    elif cmd == "detect_emotion":
        return "Detecting emotion"
    elif cmd == "ocr_read":
        return "Reading text from image"
    elif cmd == "live_stream":
        return "Starting camera stream"

    # 🔘 Memory
    elif cmd == "remember_this":
        return "Memory saved"
    elif cmd == "recall_memory":
        return "Recalling old memory"
    elif cmd == "memory_timeline":
        return "Showing memory timeline"

    # 🔘 Audio/TTS
    elif cmd == "speak_text":
        return "Speaking text"
    elif cmd == "play_audio":
        return "Playing audio"
    elif cmd == "stop_audio":
        return "Stopping audio"

    # 🔘 Servo / Movement
    elif cmd == "move_forward":
        return "Moving forward"
    elif cmd == "move_backward":
        return "Moving backward"
    elif cmd == "turn_left":
        return "Turning left"
    elif cmd == "turn_right":
        return "Turning right"
    elif cmd == "nod_yes":
        return "Nodding yes"
    elif cmd == "shake_no":
        return "Shaking no"
    elif cmd == "head_center":
        return "Head centered"

    # 🔘 Web/OTA Features
    elif cmd == "ota_update":
        return "Starting OTA update"
    elif cmd == "open_dashboard":
        return "Opening Web Dashboard"
    elif cmd == "system_restart":
        return "Restarting system"

    # 🔘 Emotion/Emoji
    elif cmd == "show_happy":
        return "😊 Showing happy"
    elif cmd == "show_sad":
        return "😢 Showing sad"
    elif cmd == "show_angry":
        return "😠 Showing angry"
    elif cmd == "show_sleepy":
        return "😴 Showing sleepy"

    # 🔘 Language/Translate
    elif cmd == "translate_bangla":
        return "Switching to Bangla"
    elif cmd == "translate_english":
        return "Switching to English"

    # 🔘 Personalization
    elif cmd == "set_name":
        return "Name set"
    elif cmd == "get_name":
        return "Here is my name"
    elif cmd == "change_voice":
        return "Changing voice"

    # 🔘 Misc
    elif cmd == "battery_status":
        return "Battery status"
    elif cmd == "internet_status":
        return "Internet connection check"
    elif cmd == "wifi_scan":
        return "Scanning WiFi"
    elif cmd == "unlock_memory":
        return "PIN verified"
    elif cmd == "lock_memory":
        return "Memory locked"
    elif cmd == "weather_update":
        return "Getting weather"
    elif cmd == "calendar_check":
        return "Opening calendar"
    elif cmd == "show_time":
        return "Showing time"

    # 🔘 বই / পড়াশোনা (৫০টি বাংলা কমান্ড)
    elif cmd == "বই_পড়া":
        return "বই পড়া হচ্ছে"
    elif cmd == "অধ্যায়_পড়া":
        return "অধ্যায় পড়া হচ্ছে"
    elif cmd == "পৃষ্ঠা_পড়া":
        return "পৃষ্ঠা পড়া হচ্ছে"
    elif cmd == "অনুচ্ছেদ_পড়া":
        return "অনুচ্ছেদ পড়া হচ্ছে"
    elif cmd == "লাইন_পড়া":
        return "লাইন পড়া হচ্ছে"
    elif cmd == "সারাংশ_পড়া":
        return "সারাংশ পড়া হচ্ছে"
    elif cmd == "উচ্চস্বরে_পড়া":
        return "উচ্চস্বরে পড়া হচ্ছে"
    elif cmd == "পড়া_বিরতি":
        return "পড়া বিরতি দেওয়া হচ্ছে"
    elif cmd == "পড়া_চালিয়ে_নেওয়া":
        return "পড়া আবার শুরু হচ্ছে"
    elif cmd == "পড়া_বন্ধ_করা":
        return "পড়া বন্ধ করা হচ্ছে"
    elif cmd == "গল্প_পড়া":
        return "গল্প পড়া হচ্ছে"
    elif cmd == "কবিতা_পড়া":
        return "কবিতা পড়া হচ্ছে"
    elif cmd == "অনুচ্ছেদ_অনুবাদ":
        return "অনুচ্ছেদ অনুবাদ হচ্ছে"
    elif cmd == "পৃষ্ঠা_বুকমার্ক":
        return "পৃষ্ঠা বুকমার্ক করা হচ্ছে"
    elif cmd == "পরবর্তী_পৃষ্ঠা":
        return "পরবর্তী পৃষ্ঠায় যাওয়া হচ্ছে"
    elif cmd == "আগের_পৃষ্ঠা":
        return "আগের পৃষ্ঠায় যাওয়া হচ্ছে"
    elif cmd == "শব্দ_অনুসন্ধান":
        return "শব্দ খোঁজা হচ্ছে"
    elif cmd == "শব্দের_সংজ্ঞা":
        return "শব্দের সংজ্ঞা দেওয়া হচ্ছে"
    elif cmd == "গণিত_পড়া":
        return "গণিত পড়া হচ্ছে"
    elif cmd == "বিজ্ঞান_পড়া":
        return "বিজ্ঞান পড়া হচ্ছে"
    elif cmd == "বাংলা_বই_পড়া":
        return "বাংলা বই পড়া হচ্ছে"
    elif cmd == "ইংরেজি_বই_পড়া":
        return "ইংরেজি বই পড়া হচ্ছে"
    elif cmd == "বই_রেটিং":
        return "বই রেটিং দেওয়া হচ্ছে"
    elif cmd == "বই_সাজেশন":
        return "একটি বই সাজেস্ট করা হচ্ছে"
    elif cmd == "এসডি_কার্ড_থেকে_পড়া":
        return "এসডি কার্ড থেকে বই পড়া হচ্ছে"
    elif cmd == "ইন্টারনেট_থেকে_পড়া":
        return "ইন্টারনেট থেকে বই পড়া হচ্ছে"
    elif cmd == "পিডিএফ_পড়া":
        return "পিডিএফ পড়া হচ্ছে"
    elif cmd == "ছবি_থেকে_লেখা_পড়া":
        return "ছবি থেকে লেখা পড়া হচ্ছে"
    elif cmd == "প্রিয়_বই_পড়া":
        return "আপনার প্রিয় বই পড়া হচ্ছে"
    elif cmd == "বই_তালিকা":
        return "বইয়ের তালিকা দেখানো হচ্ছে"
    elif cmd == "বই_ডাউনলোড":
        return "বই ডাউনলোড করা হচ্ছে"
    elif cmd == "বই_সারাংশ":
        return "বইয়ের সারাংশ পড়া হচ্ছে"
    elif cmd == "শিক্ষা_বই_পড়া":
        return "শিক্ষা বই পড়া হচ্ছে"
    elif cmd == "গল্পের_চরিত্র_বর্ণনা":
        return "গল্পের চরিত্র বর্ণনা করা হচ্ছে"
    elif cmd == "বই_সংরক্ষণ":
        return "বই সংরক্ষণ করা হচ্ছে"
    elif cmd == "বই_বাঁধা":
        return "বই বন্ধ করা হচ্ছে"
    elif cmd == "পাঠ্য_বই_পড়া":
        return "পাঠ্য বই পড়া হচ্ছে"
    elif cmd == "বই_স্ক্যান":
        return "বই স্ক্যান করা হচ্ছে"
    elif cmd == "বই_সংক্ষেপ":
        return "বইয়ের সংক্ষেপ পড়া হচ্ছে"
    elif cmd == "বই_প্রথম_পৃষ্ঠা":
        return "বইয়ের প্রথম পৃষ্ঠা পড়া হচ্ছে"
    elif cmd == "বই_শেষ_পৃষ্ঠা":
        return "বইয়ের শেষ পৃষ্ঠা পড়া হচ্ছে"
    elif cmd == "বই_ফেরত_দেওয়া":
        return "বই ফেরত দেওয়া হচ্ছে"
    elif cmd == "পাঠ্য_পুস্তক_অনুসন্ধান":
        return "পাঠ্য পুস্তক খোঁজা হচ্ছে"
    elif cmd == "নতুন_বই_যোগ":
        return "নতুন বই যোগ করা হচ্ছে"
    elif cmd == "বই_দেখাও":
        return "বই দেখানো হচ্ছে"
    elif cmd == "বই_নাম_সন্ধান":
        return "বইয়ের নাম খোঁজা হচ্ছে"

    # 🔘 লেখা / লেখালেখি (৫০টি বাংলা কমান্ড)
    elif cmd == "লেখা_শুরু":
        return "লেখা শুরু হচ্ছে"
    elif cmd == "লেখা_বন্ধ":
        return "লেখা বন্ধ করা হয়েছে"
    elif cmd == "লেখা_সংরক্ষণ":
        return "লেখা সংরক্ষণ করা হয়েছে"
    elif cmd == "নতুন_দলিল_তৈরি":
        return "নতুন দলিল তৈরি করা হচ্ছে"
    elif cmd == "লেখা_সম্পাদনা":
        return "লেখা সম্পাদনা মোড চালু"
    elif cmd == "লেখা_মুছে_ফেলা":
        return "লেখা মুছে ফেলা হচ্ছে"
    elif cmd == "লেখা_পুনরুদ্ধার":
        return "লেখা পুনরুদ্ধার করা হচ্ছে"
    elif cmd == "বাক্য_লেখা":
        return "বাক্য লেখা হচ্ছে"
    elif cmd == "শিরোনাম_লেখা":
        return "শিরোনাম লেখা হচ্ছে"
    elif cmd == "উপশিরোনাম_লেখা":
        return "উপশিরোনাম লেখা হচ্ছে"
    elif cmd == "বিন্দু_তৈরি":
        return "বিন্দু তৈরি করা হচ্ছে"
    elif cmd == "ছোট_বিষয়_লেখা":
        return "ছোট বিষয় লেখা হচ্ছে"
    elif cmd == "অনুচ্ছেদ_লেখা":
        return "অনুচ্ছেদ লেখা হচ্ছে"
    elif cmd == "লেখার_ফন্ট_পরিবর্তন":
        return "লেখার ফন্ট পরিবর্তন করা হচ্ছে"
    elif cmd == "লেখার_আকার_পরিবর্তন":
        return "লেখার আকার পরিবর্তন করা হচ্ছে"
    elif cmd == "লেখার_রঙ_পরিবর্তন":
        return "লেখার রঙ পরিবর্তন করা হচ্ছে"
    elif cmd == "লেখার_সারি_পরিবর্তন":
        return "লেখার সারি পরিবর্তন করা হচ্ছে"
    elif cmd == "লেখা_কপি_করা":
        return "লেখা কপি করা হচ্ছে"
    elif cmd == "লেখা_কাটা":
        return "লেখা কাটা হচ্ছে"
    elif cmd == "লেখা_পেস্ট_করা":
        return "লেখা পেস্ট করা হচ্ছে"
    elif cmd == "লেখার_স্টাইল_পরিবর্তন":
        return "লেখার স্টাইল পরিবর্তন করা হচ্ছে"
    elif cmd == "লেখার_দিক_পরিবর্তন":
        return "লেখার দিক পরিবর্তন করা হচ্ছে"
    elif cmd == "লেখা_বোল্ড_করুন":
        return "লেখা বোল্ড করা হচ্ছে"
    elif cmd == "লেখা_ইটালিক_করুন":
        return "লেখা ইটালিক করা হচ্ছে"
    elif cmd == "লেখা_আন্ডারলাইন_করুন":
        return "লেখা আন্ডারলাইন করা হচ্ছে"
    elif cmd == "লেখা_সেট_করা":
        return "লেখা সেট করা হচ্ছে"
    elif cmd == "লেখার_সর্বশেষ_সংশোধন":
        return "সর্বশেষ লেখার সংশোধন করা হচ্ছে"
    elif cmd == "লেখা_সংক্ষিপ্ত_করুন":
        return "লেখা সংক্ষিপ্ত করা হচ্ছে"
    elif cmd == "লেখা_বর্ধিত_করুন":
        return "লেখা বর্ধিত করা হচ্ছে"
    elif cmd == "লেখা_সংযোগ_করুন":
        return "লেখা সংযোগ করা হচ্ছে"
    elif cmd == "লেখা_ফাইল_সংরক্ষণ":
        return "লেখার ফাইল সংরক্ষণ করা হচ্ছে"
    elif cmd == "লেখা_ফাইল_খোলা":
        return "লেখার ফাইল খোলা হচ্ছে"
    elif cmd == "লেখা_রপ্তানি":
        return "লেখা রপ্তানি করা হচ্ছে"
    elif cmd == "লেখা_আদান_প্রদান":
        return "লেখা আদান-প্রদান হচ্ছে"
    elif cmd == "লেখার_পরিবর্তন_রিভিউ":
        return "লেখার পরিবর্তন রিভিউ করা হচ্ছে"
    elif cmd == "লেখা_মুদ্রণ":
        return "লেখা মুদ্রণ করা হচ্ছে"
    elif cmd == "লেখা_ফরম্যাট_সেট":
        return "লেখা ফরম্যাট সেট করা হচ্ছে"
    elif cmd == "লেখা_ফাইল_মুছে_ফেলা":
        return "লেখার ফাইল মুছে ফেলা হচ্ছে"
    elif cmd == "লেখা_বর্ণনা_যোগ":
        return "লেখার বর্ণনা যোগ করা হচ্ছে"
    elif cmd == "লেখা_বিষয়_বিস্তার":
        return "লেখার বিষয় বিস্তার করা হচ্ছে"
    elif cmd == "লেখা_ব্যাকআপ":
        return "লেখা ব্যাকআপ নেওয়া হচ্ছে"
    elif cmd == "লেখা_সংশ্লিষ্ট_ফাইল_যোগ":
        return "লেখার সংশ্লিষ্ট ফাইল যোগ করা হচ্ছে"
    elif cmd == "লেখা_সংশোধন_সেভ":
        return "লেখার সংশোধন সেভ করা হচ্ছে"
    elif cmd == "লেখা_বিভাগ_তৈরি":
        return "লেখার বিভাগ তৈরি করা হচ্ছে"
    elif cmd == "লেখা_শেয়ার":
        return "লেখা শেয়ার করা হচ্ছে"
    elif cmd == "লেখা_টেমপ্লেট_নির্বাচন":
        return "লেখার টেমপ্লেট নির্বাচিত হচ্ছে"
    elif cmd == "লেখা_অটোকরেক্ট":
        return "লেখার অটোকরেক্ট চালু করা হচ্ছে"
    # 🔘 বস্তু / জিনিসপত্র (৫০টি বাংলা কমান্ড)
    elif cmd == "বস্তু_খুঁজে_পাও":
        return "বস্তু খুঁজে পাওয়া হচ্ছে"
    elif cmd == "বস্তু_সংরক্ষণ":
        return "বস্তু সংরক্ষণ করা হচ্ছে"
    elif cmd == "বস্তু_তৈরি":
        return "বস্তু তৈরি করা হচ্ছে"
    elif cmd == "বস্তু_পরিবর্তন":
        return "বস্তু পরিবর্তন করা হচ্ছে"
    elif cmd == "বস্তু_মুছে_ফেলা":
        return "বস্তু মুছে ফেলা হচ্ছে"
    elif cmd == "বস্তু_পরিমাপ":
        return "বস্তু পরিমাপ করা হচ্ছে"
    elif cmd == "বস্তু_পরীক্ষা":
        return "বস্তু পরীক্ষা করা হচ্ছে"
    elif cmd == "বস্তু_পরিবহন":
        return "বস্তু পরিবহন করা হচ্ছে"
    elif cmd == "বস্তু_স্থাপন":
        return "বস্তু স্থাপন করা হচ্ছে"
    elif cmd == "বস্তু_স্থানান্তর":
        return "বস্তু স্থানান্তর করা হচ্ছে"
    elif cmd == "বস্তু_নিরীক্ষণ":
        return "বস্তু নিরীক্ষণ করা হচ্ছে"
    elif cmd == "বস্তু_বিন্যাস":
        return "বস্তু বিন্যাস করা হচ্ছে"
    elif cmd == "বস্তু_চিহ্নিত":
        return "বস্তু চিহ্নিত করা হচ্ছে"
    elif cmd == "বস্তু_জমা_দেওয়া":
        return "বস্তু জমা দেওয়া হচ্ছে"
    elif cmd == "বস্তু_গ্রহণ":
        return "বস্তু গ্রহণ করা হচ্ছে"
    elif cmd == "বস্তু_বিক্রয়":
        return "বস্তু বিক্রয় করা হচ্ছে"
    elif cmd == "বস্তু_পুনরুদ্ধার":
        return "বস্তু পুনরুদ্ধার করা হচ্ছে"
    elif cmd == "বস্তু_বিনিময়":
        return "বস্তু বিনিময় করা হচ্ছে"
    elif cmd == "বস্তু_পর্যালোচনা":
        return "বস্তু পর্যালোচনা করা হচ্ছে"
    elif cmd == "বস্তু_সঙ্কলন":
        return "বস্তু সঙ্কলন করা হচ্ছে"
    elif cmd == "বস্তু_সংখ্যা_গণনা":
        return "বস্তু সংখ্যা গণনা করা হচ্ছে"
    elif cmd == "বস্তু_অনুসন্ধান":
        return "বস্তু অনুসন্ধান করা হচ্ছে"
    elif cmd == "বস্তু_দেখাও":
        return "বস্তু দেখানো হচ্ছে"
    elif cmd == "বস্তু_তালিকা":
        return "বস্তু তালিকা দেখানো হচ্ছে"
    elif cmd == "বস্তু_জমা_হিসাব":
        return "বস্তু জমা হিসাব করা হচ্ছে"
    elif cmd == "বস্তু_বিক্রয়_হিসাব":
        return "বস্তু বিক্রয় হিসাব করা হচ্ছে"
    elif cmd == "বস্তু_সরবরাহ":
        return "বস্তু সরবরাহ করা হচ্ছে"
    elif cmd == "বস্তু_জরুরি_তালিকা":
        return "বস্তু জরুরি তালিকা দেখানো হচ্ছে"
    elif cmd == "বস্তু_সম্পাদনা":
        return "বস্তু সম্পাদনা করা হচ্ছে"
    elif cmd == "বস্তু_পুনঃস্থাপন":
        return "বস্তু পুনঃস্থাপন করা হচ্ছে"
    elif cmd == "বস্তু_খোলা":
        return "বস্তু খোলা হচ্ছে"
    elif cmd == "বস্তু_বন্ধ":
        return "বস্তু বন্ধ করা হচ্ছে"
    elif cmd == "বস্তু_স্থান_পরিবর্তন":
        return "বস্তু স্থানের পরিবর্তন করা হচ্ছে"
    elif cmd == "বস্তু_পরিমাণ_বৃদ্ধি":
        return "বস্তু পরিমাণ বৃদ্ধি পাচ্ছে"
    elif cmd == "বস্তু_পরিমাণ_হ্রাস":
        return "বস্তু পরিমাণ হ্রাস পাচ্ছে"
    elif cmd == "বস্তু_সংশ্লিষ্ট_তথ্য":
        return "বস্তু সম্পর্কিত তথ্য দেখানো হচ্ছে"
    elif cmd == "বস্তু_তৈরি_সময়":
        return "বস্তু তৈরি সময় প্রদর্শন"
    elif cmd == "বস্তু_শেষ_তারিখ":
        return "বস্তু শেষ তারিখ প্রদর্শন"
    elif cmd == "বস্তু_মেয়াদ_সংশোধন":
        return "বস্তু মেয়াদ সংশোধন করা হচ্ছে"
    elif cmd == "বস্তু_মূল্য_নির্ধারণ":
        return "বস্তু মূল্য নির্ধারণ করা হচ্ছে"
    elif cmd == "বস্তু_বিবরণ":
        return "বস্তু বিবরণ দেখানো হচ্ছে"
    elif cmd == "বস্তু_নতুন_যোগ":
        return "নতুন বস্তু যোগ করা হচ্ছে"
    elif cmd == "বস্তু_সার্বিক_পর্যালোচনা":
        return "বস্তু সার্বিক পর্যালোচনা করা হচ্ছে"
    elif cmd == "বস্তু_অবস্থা_পরীক্ষা":
        return "বস্তু অবস্থা পরীক্ষা করা হচ্ছে"
    elif cmd == "বস্তু_ব্যবহার_হিসাব":
        return "বস্তু ব্যবহার হিসাব করা হচ্ছে"
    elif cmd == "বস্তু_রিপোর্ট":
        return "বস্তু রিপোর্ট তৈরি হচ্ছে"

    # 🔘 হাঁটা / চলাফেরা (৫০টি বাংলা কমান্ড)
    elif cmd == "হাঁটা_শুরু":
        return "হাঁটা শুরু হচ্ছে"
    elif cmd == "হাঁটা_বন্ধ":
        return "হাঁটা বন্ধ করা হচ্ছে"
    elif cmd == "আগিয়ে_চলুন":
        return "আগিয়ে চলুন"
    elif cmd == "পেছনে_যান":
        return "পেছনে যান"
    elif cmd == "বাঁদিকে_মোরান":
        return "বাঁদিকে মোড় নিন"
    elif cmd == "ডানদিকে_মোরান":
        return "ডানদিকে মোড় নিন"
    elif cmd == "দ্রুত_হাঁটুন":
        return "দ্রুত হাঁটুন"
    elif cmd == "ধীরে_হাঁটুন":
        return "ধীরে হাঁটুন"
    elif cmd == "দাঁড়ান":
        return "দাঁড়ান"
    elif cmd == "বিঘ্নবিহীন_হাঁটা":
        return "বিঘ্নবিহীন হাঁটা"
    elif cmd == "নিরাপদ_হাঁটা":
        return "নিরাপদ হাঁটা"
    elif cmd == "গতি_বৃদ্ধি":
        return "গতি বৃদ্ধি পাচ্ছে"
    elif cmd == "গতি_হ্রাস":
        return "গতি কমানো হচ্ছে"
    elif cmd == "হাঁটার_দিক_পরিবর্তন":
        return "হাঁটার দিক পরিবর্তন"
    elif cmd == "হাঁটার_গতি_নিয়ন্ত্রণ":
        return "হাঁটার গতি নিয়ন্ত্রণ"
    elif cmd == "সোজা_হাঁটুন":
        return "সোজা হাঁটুন"
    elif cmd == "বাঁকুন":
        return "বাঁকুন"
    elif cmd == "ডানদিকে_বাঁকুন":
        return "ডানদিকে বাঁকুন"
    elif cmd == "বাঁদিকে_বাঁকুন":
        return "বাঁদিকে বাঁকুন"
    elif cmd == "হাঁটার_সময়_বৃদ্ধি":
        return "হাঁটার সময় বৃদ্ধি পাচ্ছে"
    elif cmd == "হাঁটার_সময়_হ্রাস":
        return "হাঁটার সময় কমানো হচ্ছে"
    elif cmd == "চলাফেরার_দূরত্ব_বৃদ্ধি":
        return "চলাফেরার দূরত্ব বৃদ্ধি পাচ্ছে"
    elif cmd == "চলাফেরার_দূরত্ব_হ্রাস":
        return "চলাফেরার দূরত্ব কমানো হচ্ছে"
    elif cmd == "গতি_পরিমাপ":
        return "গতি পরিমাপ করা হচ্ছে"
    elif cmd == "পথ_নির্দেশনা":
        return "পথ নির্দেশনা প্রদান"
    elif cmd == "পথ_পরিবর্তন":
        return "পথ পরিবর্তন"
    elif cmd == "চলাফেরা_বন্ধ":
        return "চলাফেরা বন্ধ"
    elif cmd == "হাঁটার_প্রক্রিয়া_শুরু":
        return "হাঁটার প্রক্রিয়া শুরু"
    elif cmd == "হাঁটার_প্রক্রিয়া_শেষ":
        return "হাঁটার প্রক্রিয়া শেষ"
    elif cmd == "পায়ে_হাঁটা":
        return "পায়ে হাঁটা"
    elif cmd == "ধাপ_গোনা":
        return "ধাপ গোনা হচ্ছে"
    elif cmd == "ধাপ_বৃদ্ধি":
        return "ধাপ বৃদ্ধি পাচ্ছে"
    elif cmd == "ধাপ_হ্রাস":
        return "ধাপ কমানো হচ্ছে"
    elif cmd == "স্টেপ_মোড":
        return "স্টেপ মোড চালু"
    elif cmd == "চলাফেরার_গতি_পরিবর্তন":
        return "চলাফেরার গতি পরিবর্তন"
    elif cmd == "পথ_অনুসরণ":
        return "পথ অনুসরণ"
    elif cmd == "অবসর_নেওয়া":
        return "অবসর নেওয়া হচ্ছে"
    elif cmd == "দূরত্ব_অতিক্রম":
        return "দূরত্ব অতিক্রম করা হচ্ছে"
    elif cmd == "গতি_পর্যালোচনা":
        return "গতি পর্যালোচনা"
    elif cmd == "চলাফেরা_ব্যাহত":
        return "চলাফেরা বজায় রাখা হচ্ছে"
    elif cmd == "হাঁটার_প্রশিক্ষণ":
        return "হাঁটার প্রশিক্ষণ চলছে"
    elif cmd == "পথ_বাধা_পরিহার":
        return "পথে বাধা পরিহার করা হচ্ছে"
    elif cmd == "চলাফেরা_নিয়ন্ত্রণ":
        return "চলাফেরা নিয়ন্ত্রণ করা হচ্ছে"
    elif cmd == "পায়ে_চলাফেরা_শুরু":
        return "পায়ে চলাফেরা শুরু"
    elif cmd == "পায়ে_চলাফেরা_বন্ধ":
        return "পায়ে চলাফেরা বন্ধ"
    elif cmd == "সঠিক_দিকনির্দেশ":
        return "সঠিক দিকনির্দেশ প্রদান"

    # 🔘 মাথা / মাথার চলাচল (৫০টি বাংলা কমান্ড)
    elif cmd == "মাথা_উপর_তোলা":
        return "মাথা উপরে তোলা হচ্ছে"
    elif cmd == "মাথা_নিচে_নামানো":
        return "মাথা নিচে নামানো হচ্ছে"
    elif cmd == "মাথা_ডানদিকে_মোড়ানো":
        return "মাথা ডানদিকে মোড়ানো হচ্ছে"
    elif cmd == "মাথা_বাঁদিকে_মোড়ানো":
        return "মাথা বাঁদিকে মোড়ানো হচ্ছে"
    elif cmd == "মাথা_সোজা_রাখা":
        return "মাথা সোজা রাখা হচ্ছে"
    elif cmd == "মাথা_আঁচড়ানো":
        return "মাথা আঁচড়ানো হচ্ছে"
    elif cmd == "মাথা_হেলানো":
        return "মাথা হেলানো হচ্ছে"
    elif cmd == "মাথা_ঘোরানো":
        return "মাথা ঘোরানো হচ্ছে"
    elif cmd == "মাথা_নাড়ানো":
        return "মাথা নাড়ানো হচ্ছে"
    elif cmd == "মাথা_হাঁটানো":
        return "মাথা হাঁটানো হচ্ছে"
    elif cmd == "মাথা_নড়ানো_থামানো":
        return "মাথা নড়ানো থামানো হচ্ছে"
    elif cmd == "মাথা_নিম্ন_করুন":
        return "মাথা নিম্ন করা হচ্ছে"
    elif cmd == "মাথা_উর্ধ্ব_করুন":
        return "মাথা উর্ধ্ব করা হচ্ছে"
    elif cmd == "মাথা_দাঁড়ানো":
        return "মাথা দাঁড়ানো অবস্থায়"
    elif cmd == "মাথা_চলাচল_শুরু":
        return "মাথা চলাচল শুরু"
    elif cmd == "মাথা_চলাচল_বন্ধ":
        return "মাথা চলাচল বন্ধ"
    elif cmd == "মাথা_স্ফুরণ":
        return "মাথা স্ফুরণ ঘটানো হচ্ছে"
    elif cmd == "মাথা_পাল্টানো":
        return "মাথা পাল্টানো হচ্ছে"
    elif cmd == "মাথা_গোলমাল_করা":
        return "মাথা গোলমাল করা হচ্ছে"
    elif cmd == "মাথা_ঝাঁকানো":
        return "মাথা ঝাঁকানো হচ্ছে"
    elif cmd == "মাথা_বাঁকানো":
        return "মাথা বাঁকানো হচ্ছে"
    elif cmd == "মাথা_ডান_হাত_মোড়ানো":
        return "মাথা ডান হাত মোড়ানো"
    elif cmd == "মাথা_বাঁহাত_মোড়ানো":
        return "মাথা বাঁ হাত মোড়ানো"
    elif cmd == "মাথা_নোঙ্গর":
        return "মাথা নোঙ্গর করা হচ্ছে"
    elif cmd == "মাথা_হেলান":
        return "মাথা হেলানো হচ্ছে"
    elif cmd == "মাথা_উঁচু_করা":
        return "মাথা উঁচু করা হচ্ছে"
    elif cmd == "মাথা_নিম্ন_করা":
        return "মাথা নিম্ন করা হচ্ছে"
    elif cmd == "মাথা_নড়াচড়া":
        return "মাথা নড়াচড়া হচ্ছে"
    elif cmd == "মাথা_সীমিত_করা":
        return "মাথার গতি সীমিত করা হচ্ছে"
    elif cmd == "মাথা_সঠিক_রেখায়_রাখুন":
        return "মাথা সঠিক রেখায় রাখা হচ্ছে"
    elif cmd == "মাথা_বাঁকান":
        return "মাথা বাঁকানো হচ্ছে"
    elif cmd == "মাথা_ডান_বাঁকান":
        return "মাথা ডান বাঁকানো হচ্ছে"
    elif cmd == "মাথা_বাঁই_বাঁকান":
        return "মাথা বাঁই বাঁকানো হচ্ছে"
    elif cmd == "মাথা_আবার_সোজা_করুন":
        return "মাথা আবার সোজা করা হচ্ছে"
    elif cmd == "মাথা_গতি_হ্রাস":
        return "মাথার গতি হ্রাস পাচ্ছে"
    elif cmd == "মাথা_গতি_বৃদ্ধি":
        return "মাথার গতি বৃদ্ধি পাচ্ছে"
    elif cmd == "মাথা_স্তব্ধ":
        return "মাথা স্তব্ধ অবস্থায়"
    elif cmd == "মাথা_ঝুঁকি_পরিহার":
        return "মাথা ঝুঁকি পরিহার করছে"
    elif cmd == "মাথা_শান্ত":
        return "মাথা শান্ত অবস্থায়"
    elif cmd == "মাথা_তাড়াতাড়ি_ঘোরানো":
        return "মাথা দ্রুত ঘোরানো হচ্ছে"
    elif cmd == "মাথা_ধীরে_ঘোরানো":
        return "মাথা ধীরে ঘোরানো হচ্ছে"
    elif cmd == "মাথা_পেছনে_ঘোরানো":
        return "মাথা পেছনে ঘোরানো হচ্ছে"
    elif cmd == "মাথা_সামনে_নেওয়া":
        return "মাথা সামনে নেওয়া হচ্ছে"
    elif cmd == "মাথা_দাঁড়ানো_রাখুন":
        return "মাথা দাঁড়ানো অবস্থায় রাখা হচ্ছে"
    elif cmd == "মাথা_সরে_যাও":
        return "মাথা সরানো হচ্ছে"
    elif cmd == "মাথা_স্ফীত_করা":
        return "মাথা স্ফীত করা হচ্ছে"
   
    # 🔘 প্রশ্ন / জিজ্ঞাসা (৫০টি বাংলা কমান্ড)
    elif cmd == "প্রশ্ন_করো":
        return "প্রশ্ন করা হচ্ছে"
    elif cmd == "উত্তর_দাও":
        return "উত্তর দেওয়া হচ্ছে"
    elif cmd == "আবার_বলুন":
        return "আবার বলুন"
    elif cmd == "স্পষ্ট_করে_বলুন":
        return "স্পষ্ট করে বলুন"
    elif cmd == "বিস্তারিত_বলা":
        return "বিস্তারিত বলা হচ্ছে"
    elif cmd == "সংক্ষিপ্ত_উত্তর":
        return "সংক্ষিপ্ত উত্তর দেওয়া হচ্ছে"
    elif cmd == "সঠিক_উত্তর":
        return "সঠিক উত্তর দেওয়া হচ্ছে"
    elif cmd == "ভুল_ঠিক_করুন":
        return "ভুল ঠিক করা হচ্ছে"
    elif cmd == "সহজ_ভাষায়_বলা":
        return "সহজ ভাষায় বলা হচ্ছে"
    elif cmd == "অন্য_প্রশ্ন_করুন":
        return "অন্য প্রশ্ন করা হচ্ছে"
    elif cmd == "প্রশ্ন_বাতিল_করুন":
        return "প্রশ্ন বাতিল করা হয়েছে"
    elif cmd == "অফলাইন_প্রশ্ন":
        return "অফলাইন প্রশ্ন গ্রহণ"
    elif cmd == "অনলাইন_প্রশ্ন":
        return "অনলাইন প্রশ্ন গ্রহণ"
    elif cmd == "উত্তর_অনুসন্ধান":
        return "উত্তর অনুসন্ধান করা হচ্ছে"
    elif cmd == "বিষয়_সম্পর্কিত_প্রশ্ন":
        return "বিষয় সম্পর্কিত প্রশ্ন করা হচ্ছে"
    elif cmd == "সাধারণ_প্রশ্ন":
        return "সাধারণ প্রশ্ন গ্রহণ"
    elif cmd == "বিশেষ_প্রশ্ন":
        return "বিশেষ প্রশ্ন গ্রহণ"
    elif cmd == "প্রশ্ন_সংরক্ষণ":
        return "প্রশ্ন সংরক্ষণ করা হচ্ছে"
    elif cmd == "প্রশ্ন_মুছে_ফেলা":
        return "প্রশ্ন মুছে ফেলা হচ্ছে"
    elif cmd == "প্রশ্ন_আপডেট":
        return "প্রশ্ন আপডেট করা হচ্ছে"
    elif cmd == "উত্তর_পুনরায়_বলুন":
        return "উত্তর পুনরায় বলা হচ্ছে"
    elif cmd == "প্রশ্ন_গোপন":
        return "প্রশ্ন গোপন করা হয়েছে"
    elif cmd == "উত্তর_গোপন":
        return "উত্তর গোপন করা হয়েছে"
    elif cmd == "প্রশ্ন_ফিল্টার_করুন":
        return "প্রশ্ন ফিল্টার করা হচ্ছে"
    elif cmd == "উত্তর_ফিল্টার_করুন":
        return "উত্তর ফিল্টার করা হচ্ছে"
    elif cmd == "প্রশ্ন_অনুবাদ":
        return "প্রশ্ন অনুবাদ করা হচ্ছে"
    elif cmd == "উত্তর_অনুবাদ":
        return "উত্তর অনুবাদ করা হচ্ছে"
    elif cmd == "সংশ্লিষ্ট_প্রশ্ন":
        return "সংশ্লিষ্ট প্রশ্ন দেখানো হচ্ছে"
    elif cmd == "উত্তর_সংশ্লিষ্ট":
        return "সংশ্লিষ্ট উত্তর দেখানো হচ্ছে"
    elif cmd == "প্রশ্ন_প্রদর্শন":
        return "প্রশ্ন প্রদর্শন করা হচ্ছে"
    elif cmd == "উত্তর_প্রদর্শন":
        return "উত্তর প্রদর্শন করা হচ্ছে"
    elif cmd == "প্রশ্ন_সংখ্যা_গণনা":
        return "প্রশ্ন সংখ্যা গণনা করা হচ্ছে"
    elif cmd == "উত্তর_সংখ্যা_গণনা":
        return "উত্তর সংখ্যা গণনা করা হচ্ছে"
    elif cmd == "প্রশ্ন_যোগ":
        return "প্রশ্ন যোগ করা হচ্ছে"
    elif cmd == "উত্তর_যোগ":
        return "উত্তর যোগ করা হচ্ছে"
    elif cmd == "প্রশ্ন_তালিকা":
        return "প্রশ্নের তালিকা দেখানো হচ্ছে"
    elif cmd == "উত্তর_তালিকা":
        return "উত্তরের তালিকা দেখানো হচ্ছে"
    elif cmd == "প্রশ্ন_রিপোর্ট":
        return "প্রশ্নের রিপোর্ট তৈরি হচ্ছে"
    elif cmd == "উত্তর_রিপোর্ট":
        return "উত্তরের রিপোর্ট তৈরি হচ্ছে"
    elif cmd == "প্রশ্ন_মন্তব্য":
        return "প্রশ্নের মন্তব্য দেখানো হচ্ছে"
    elif cmd == "উত্তর_মন্তব্য":
        return "উত্তরের মন্তব্য দেখানো হচ্ছে"
    elif cmd == "প্রশ্ন_আলোচনা":
        return "প্রশ্নের আলোচনা শুরু"
    elif cmd == "উত্তর_আলোচনা":
        return "উত্তরের আলোচনা শুরু"
    elif cmd == "প্রশ্ন_সমাধান":
        return "প্রশ্ন সমাধান করা হচ্ছে"
    elif cmd == "উত্তর_সমাধান":
        return "উত্তর সমাধান করা হচ্ছে"
    elif cmd == "প্রশ্ন_জমা_দেওয়া":
        return "প্রশ্ন জমা দেওয়া হচ্ছে"
    elif cmd == "উত্তর_জমা_দেওয়া":
        return "উত্তর জমা দেওয়া হচ্ছে"

    # 🔘 উত্তর (৫০টি বাংলা কমান্ড)
    elif cmd == "উত্তর_দাও":
        return "উত্তর দেওয়া হচ্ছে"
    elif cmd == "উত্তর_লিখুন":
        return "উত্তর লেখা হচ্ছে"
    elif cmd == "উত্তর_সংরক্ষণ":
        return "উত্তর সংরক্ষণ করা হচ্ছে"
    elif cmd == "উত্তর_পরীক্ষা":
        return "উত্তর পরীক্ষা করা হচ্ছে"
    elif cmd == "উত্তর_সম্পাদনা":
        return "উত্তর সম্পাদনা করা হচ্ছে"
    elif cmd == "উত্তর_মুছে_ফেলা":
        return "উত্তর মুছে ফেলা হচ্ছে"
    elif cmd == "উত্তর_পুনরুদ্ধার":
        return "উত্তর পুনরুদ্ধার করা হচ্ছে"
    elif cmd == "উত্তর_প্রেরণ":
        return "উত্তর প্রেরণ করা হচ্ছে"
    elif cmd == "উত্তর_পাঠান":
        return "উত্তর পাঠানো হচ্ছে"
    elif cmd == "উত্তর_পাঠানো_সফল":
        return "উত্তর সফলভাবে পাঠানো হয়েছে"
    elif cmd == "উত্তর_আলোচনা":
        return "উত্তর আলোচনা শুরু"
    elif cmd == "উত্তর_গোপন":
        return "উত্তর গোপন রাখা হয়েছে"
    elif cmd == "উত্তর_প্রকাশ":
        return "উত্তর প্রকাশ করা হচ্ছে"
    elif cmd == "উত্তর_সংক্ষিপ্ত":
        return "উত্তর সংক্ষিপ্ত করা হচ্ছে"
    elif cmd == "উত্তর_বিস্তারিত":
        return "উত্তর বিস্তারিত বলা হচ্ছে"
    elif cmd == "উত্তর_ফরম্যাট":
        return "উত্তর ফরম্যাট করা হচ্ছে"
    elif cmd == "উত্তর_ফিল্টার":
        return "উত্তর ফিল্টার করা হচ্ছে"
    elif cmd == "উত্তর_অনুমোদন":
        return "উত্তর অনুমোদিত"
    elif cmd == "উত্তর_অস্বীকার":
        return "উত্তর অস্বীকার করা হয়েছে"
    elif cmd == "উত্তর_প্রতিবেদন":
        return "উত্তর প্রতিবেদন তৈরি হচ্ছে"
    elif cmd == "উত্তর_সংখ্যা_গণনা":
        return "উত্তর সংখ্যা গণনা করা হচ্ছে"
    elif cmd == "উত্তর_রিভিউ":
        return "উত্তর রিভিউ করা হচ্ছে"
    elif cmd == "উত্তর_সংশোধন":
        return "উত্তর সংশোধন করা হচ্ছে"
    elif cmd == "উত্তর_প্রতিক্রিয়া":
        return "উত্তর প্রতিক্রিয়া গ্রহণ"
    elif cmd == "উত্তর_মন্তব্য":
        return "উত্তর মন্তব্য দেখানো হচ্ছে"
    elif cmd == "উত্তর_বিনিময়":
        return "উত্তর বিনিময় করা হচ্ছে"
    elif cmd == "উত্তর_রক্ষণাবেক্ষণ":
        return "উত্তর রক্ষণাবেক্ষণ করা হচ্ছে"
    elif cmd == "উত্তর_সংগ্রহ":
        return "উত্তর সংগ্রহ করা হচ্ছে"
    elif cmd == "উত্তর_অনুসন্ধান":
        return "উত্তর অনুসন্ধান করা হচ্ছে"
    elif cmd == "উত্তর_ফাইল_সংরক্ষণ":
        return "উত্তর ফাইল সংরক্ষণ করা হচ্ছে"
    elif cmd == "উত্তর_শেয়ার":
        return "উত্তর শেয়ার করা হচ্ছে"
    elif cmd == "উত্তর_রপ্তানি":
        return "উত্তর রপ্তানি করা হচ্ছে"
    elif cmd == "উত্তর_প্রিন্ট":
        return "উত্তর প্রিন্ট করা হচ্ছে"
    elif cmd == "উত্তর_যোগ":
        return "উত্তর যোগ করা হচ্ছে"
    elif cmd == "উত্তর_সম্পাদনা_সেভ":
        return "উত্তর সম্পাদনা সেভ করা হচ্ছে"
    elif cmd == "উত্তর_ফর্ম_পূরণ":
        return "উত্তর ফর্ম পূরণ করা হচ্ছে"
    elif cmd == "উত্তর_প্রেরণ_প্রক্রিয়া":
        return "উত্তর প্রেরণ প্রক্রিয়া চলছে"
    elif cmd == "উত্তর_ব্যবহার":
        return "উত্তর ব্যবহার করা হচ্ছে"
    elif cmd == "উত্তর_সফল":
        return "উত্তর সফল হয়েছে"
    elif cmd == "উত্তর_ব্যর্থ":
        return "উত্তর ব্যর্থ হয়েছে"
    elif cmd == "উত্তর_প্রতিলিপি":
        return "উত্তর প্রতিলিপি করা হচ্ছে"
    elif cmd == "উত্তর_প্রতিকৃতি":
        return "উত্তর প্রতিকৃতি তৈরি করা হচ্ছে"
    elif cmd == "উত্তর_দেখাও":
        return "উত্তর দেখানো হচ্ছে"
    elif cmd == "উত্তর_গুপ্ত":
        return "উত্তর গোপন রাখা হয়েছে"
    elif cmd == "উত্তর_সংগ্রহস্থল":
        return "উত্তর সংগ্রহস্থল প্রদর্শন"
    elif cmd == "উত্তর_সফটওয়্যার_আপডেট":
        return "উত্তর সফটওয়্যার আপডেট চলছে"
    elif cmd == "উত্তর_সংরক্ষণ_বাতিল":
        return "উত্তর সংরক্ষণ বাতিল করা হয়েছে"

    # 🔘 দিক (৫০টি বাংলা কমান্ড)
    elif cmd == "সোজা_চলুন":
        return "সোজা চলা শুরু"
    elif cmd == "বাঁদিকে_মোড়ান":
        return "বাঁদিকে মোড় নিন"
    elif cmd == "ডানদিকে_মোড়ান":
        return "ডানদিকে মোড় নিন"
    elif cmd == "পেছনে_যান":
        return "পেছনে যাওয়া শুরু"
    elif cmd == "আগের_দিক":
        return "আগের দিকে যাওয়া"
    elif cmd == "পরবর্তী_দিক":
        return "পরবর্তী দিকে যাওয়া"
    elif cmd == "উত্তর_চলুন":
        return "উত্তর দিকে চলা"
    elif cmd == "দক্ষিণ_চলুন":
        return "দক্ষিণ দিকে চলা"
    elif cmd == "পূর্ব_চলুন":
        return "পূর্ব দিকে চলা"
    elif cmd == "পশ্চিম_চলুন":
        return "পশ্চিম দিকে চলা"
    elif cmd == "উত্তর-পূর্ব_চলুন":
        return "উত্তর-পূর্ব দিকে চলা"
    elif cmd == "উত্তর-পশ্চিম_চলুন":
        return "উত্তর-পশ্চিম দিকে চলা"
    elif cmd == "দক্ষিণ-পূর্ব_চলুন":
        return "দক্ষিণ-পূর্ব দিকে চলা"
    elif cmd == "দক্ষিণ-পশ্চিম_চলুন":
        return "দক্ষিণ-পশ্চিম দিকে চলা"
    elif cmd == "মুখ_ঘুরাও_ডানদিকে":
        return "মুখ ডানদিকে ঘুরানো"
    elif cmd == "মুখ_ঘুরাও_বাঁদিকে":
        return "মুখ বাঁদিকে ঘুরানো"
    elif cmd == "মুখ_সোজা_করো":
        return "মুখ সোজা রাখা"
    elif cmd == "দিক_পরিবর্তন_করো":
        return "দিক পরিবর্তন করা"
    elif cmd == "দিক_নির্দেশ_দাও":
        return "দিক নির্দেশ প্রদান"
    elif cmd == "দিক_খুঁজে_পাও":
        return "দিক খুঁজে পাওয়া"
    elif cmd == "বাম_দিক_চলুন":
        return "বাম দিকে চলা"
    elif cmd == "ডান_দিক_চলুন":
        return "ডান দিকে চলা"
    elif cmd == "উপর_দিক_চলুন":
        return "উপর দিকে চলা"
    elif cmd == "নীচে_দিক_চলুন":
        return "নীচে দিকে চলা"
    elif cmd == "সামনে_দিক_চলুন":
        return "সামনে দিকে চলা"
    elif cmd == "পেছনে_দিক_চলুন":
        return "পেছনে দিকে চলা"
    elif cmd == "দিক_সংশোধন_করো":
        return "দিক সংশোধন করা"
    elif cmd == "দিক_স্থির_করো":
        return "দিক স্থির করা"
    elif cmd == "দিক_পর্যবেক্ষণ_করো":
        return "দিক পর্যবেক্ষণ করা"
    elif cmd == "দিক_পরিমাপ_করো":
        return "দিক পরিমাপ করা"
    elif cmd == "দিক_পরিবর্তন_নিয়ন্ত্রণ":
        return "দিক পরিবর্তন নিয়ন্ত্রণ"
    elif cmd == "দিক_ঘুরাও_ধীরে":
        return "দিক ধীরে ঘুরানো"
    elif cmd == "দিক_ঘুরাও_দ্রুত":
        return "দিক দ্রুত ঘুরানো"
    elif cmd == "দিক_চিহ্নিত_করো":
        return "দিক চিহ্নিত করা"
    elif cmd == "দিক_রিপোর্ট_দাও":
        return "দিক রিপোর্ট প্রদান"
    elif cmd == "দিক_মিলাও":
        return "দিক মিলানো"
    elif cmd == "দিক_ছাড়াও":
        return "দিক ছাড়া"
    elif cmd == "দিক_সুন্দর_করো":
        return "দিক সুন্দর করা"
    elif cmd == "দিক_সীমাবদ্ধ_করো":
        return "দিক সীমাবদ্ধ করা"
    elif cmd == "দিক_নির্দেশিকা_দাও":
        return "দিক নির্দেশিকা প্রদান"
    elif cmd == "দিক_সঠিক_করো":
        return "দিক সঠিক করা"
    elif cmd == "দিক_চলাচল_বন্ধ":
        return "দিক চলাচল বন্ধ"
    elif cmd == "দিক_চলাচল_শুরু":
        return "দিক চলাচল শুরু"
    elif cmd == "দিক_নিয়ন্ত্রণ_গ্রহণ":
        return "দিক নিয়ন্ত্রণ গ্রহণ"
    elif cmd == "দিক_রেসেট_করো":
        return "দিক রিসেট করা"
    elif cmd == "দিক_বিন্যাস_করো":
        return "দিক বিন্যাস করা"
    elif cmd == "দিক_স্বরূপ_পরিবর্তন":
        return "দিক স্বরূপ পরিবর্তন"

    # 🔘 ওঠা-বসা / উপরে-নিচে (৫০টি বাংলা কমান্ড)
    elif cmd == "উঠুন":
        return "উঠা হচ্ছে"
    elif cmd == "বসুন":
        return "বসা হচ্ছে"
    elif cmd == "উপরে_যান":
        return "উপরে যাওয়া হচ্ছে"
    elif cmd == "নিচে_যান":
        return "নিচে যাওয়া হচ্ছে"
    elif cmd == "ধীরে_উঠুন":
        return "ধীরে উঠে যাওয়া হচ্ছে"
    elif cmd == "ধীরে_বসুন":
        return "ধীরে বসা হচ্ছে"
    elif cmd == "দ্রুত_উঠুন":
        return "দ্রুত উঠে যাওয়া হচ্ছে"
    elif cmd == "দ্রুত_বসুন":
        return "দ্রুত বসা হচ্ছে"
    elif cmd == "আধা_উঠুন":
        return "আধা উঠে যাওয়া হচ্ছে"
    elif cmd == "আধা_বসুন":
        return "আধা বসা হচ্ছে"
    elif cmd == "পেছনে_উঠুন":
        return "পেছনে উঠে যাওয়া হচ্ছে"
    elif cmd == "পেছনে_বসুন":
        return "পেছনে বসা হচ্ছে"
    elif cmd == "সোজা_উঠুন":
        return "সোজা উঠে যাওয়া হচ্ছে"
    elif cmd == "সোজা_বসুন":
        return "সোজা বসা হচ্ছে"
    elif cmd == "উঠার_প্রক্রিয়া_শুরু":
        return "উঠার প্রক্রিয়া শুরু"
    elif cmd == "বসার_প্রক্রিয়া_শুরু":
        return "বসার প্রক্রিয়া শুরু"
    elif cmd == "উঠার_প্রক্রিয়া_বন্ধ":
        return "উঠার প্রক্রিয়া বন্ধ"
    elif cmd == "বসার_প্রক্রিয়া_বন্ধ":
        return "বসার প্রক্রিয়া বন্ধ"
    elif cmd == "উঠে_পড়া":
        return "উঠে পড়া হচ্ছে"
    elif cmd == "বসে_থাকা":
        return "বসে থাকা"
    elif cmd == "আনুভূমিক_উঠান":
        return "আনুভূমিক উঠে যাওয়া"
    elif cmd == "আনুভূমিক_বসান":
        return "আনুভূমিক বসা"
    elif cmd == "উঠা_নিয়ন্ত্রণ":
        return "উঠা নিয়ন্ত্রণ করা হচ্ছে"
    elif cmd == "বসা_নিয়ন্ত্রণ":
        return "বসা নিয়ন্ত্রণ করা হচ্ছে"
    elif cmd == "উঠে_থাকা":
        return "উঠে থাকা হচ্ছে"
    elif cmd == "বসে_থাকা_নিয়ন্ত্রণ":
        return "বসে থাকা নিয়ন্ত্রণ করা হচ্ছে"
    elif cmd == "উঠতে_সাহায্য_করুন":
        return "উঠতে সাহায্য করা হচ্ছে"
    elif cmd == "বসতে_সাহায্য_করুন":
        return "বসতে সাহায্য করা হচ্ছে"
    elif cmd == "উঠার_গতি_বৃদ্ধি":
        return "উঠার গতি বৃদ্ধি পাচ্ছে"
    elif cmd == "বসার_গতি_বৃদ্ধি":
        return "বসার গতি বৃদ্ধি পাচ্ছে"
    elif cmd == "উঠার_গতি_হ্রাস":
        return "উঠার গতি হ্রাস পাচ্ছে"
    elif cmd == "বসার_গতি_হ্রাস":
        return "বসার গতি হ্রাস পাচ্ছে"
    elif cmd == "উঠার_সময়_পরিমাপ":
        return "উঠার সময় পরিমাপ"
    elif cmd == "বসার_সময়_পরিমাপ":
        return "বসার সময় পরিমাপ"
    elif cmd == "উঠার_দিক_নিয়ন্ত্রণ":
        return "উঠার দিক নিয়ন্ত্রণ"
    elif cmd == "বসার_দিক_নিয়ন্ত্রণ":
        return "বসার দিক নিয়ন্ত্রণ"
    elif cmd == "উঠা_বসা_চক্র":
        return "উঠা-বসা চক্র চলছে"
    elif cmd == "বসা_থাকা_ধারণ":
        return "বসা থাকা ধারণ"
    elif cmd == "উঠা_থাকা_ধারণ":
        return "উঠা থাকা ধারণ"
    elif cmd == "উঠার_পজিশন":
        return "উঠার পজিশন"
    elif cmd == "বসার_পজিশন":
        return "বসার পজিশন"
    elif cmd == "উঠার_ভঙ্গি":
        return "উঠার ভঙ্গি"
    elif cmd == "বসার_ভঙ্গি":
        return "বসার ভঙ্গি"
    elif cmd == "উঠার_নিয়ম":
        return "উঠার নিয়ম"
    elif cmd == "বসার_নিয়ম":
        return "বসার নিয়ম"
    elif cmd == "উঠার_প্রয়াস":
        return "উঠার প্রচেষ্টা"
    elif cmd == "বসার_প্রয়াস":
        return "বসার প্রচেষ্টা"
    elif cmd == "উঠার_অবস্থা":
        return "উঠার অবস্থা"
    elif cmd == "বসার_অবস্থা":
        return "বসার অবস্থা"

    # 🔘 সময় (৫০টি বাংলা কমান্ড)
    elif cmd == "সময়_দেখাও":
        return "বর্তমান সময় দেখানো হচ্ছে"
    elif cmd == "এখন_কত_বাজে":
        return "এখন সময় কত"
    elif cmd == "আজকের_তারিখ":
        return "আজকের তারিখ জানানো হচ্ছে"
    elif cmd == "আজ_কি_দিন":
        return "আজ সপ্তাহের দিন"
    elif cmd == "কাল_কি_দিন":
        return "কাল কী দিন"
    elif cmd == "আগামী_কাল_তারিখ":
        return "আগামী কালের তারিখ"
    elif cmd == "গতকাল_কি_দিন":
        return "গতকালের দিন"
    elif cmd == "মাসের_নাম_বলুন":
        return "বর্তমান মাসের নাম"
    elif cmd == "বছরের_নাম_বলুন":
        return "বর্তমান বছরের নাম"
    elif cmd == "বেলা_কত_বাজে":
        return "বর্তমান বেলার অবস্থা"
    elif cmd == "দিনের_শেষ_সময়":
        return "দিন শেষ হওয়ার সময়"
    elif cmd == "রাতের_সময়":
        return "বর্তমান রাতের সময়"
    elif cmd == "দুপুরের_সময়":
        return "বর্তমান দুপুরের সময়"
    elif cmd == "সকাল_কত_বাজে":
        return "সকাল কত বাজে"
    elif cmd == "দুপুর_কত_বাজে":
        return "দুপুর কত বাজে"
    elif cmd == "বিকেল_কত_বাজে":
        return "বিকেল কত বাজে"
    elif cmd == "রাত_কত_বাজে":
        return "রাত কত বাজে"
    elif cmd == "সময়_সেট_করো":
        return "সময় সেট করা হচ্ছে"
    elif cmd == "ঘড়ি_সেট_করো":
        return "ঘড়ি সেট করা হচ্ছে"
    elif cmd == "টাইম_জোন_দেখাও":
        return "টাইম জোন দেখানো হচ্ছে"
    elif cmd == "সময়_পরিবর্তন_করো":
        return "সময় পরিবর্তন করা হচ্ছে"
    elif cmd == "ঘড়ি_সিঙ্ক্রোনাইজ_করো":
        return "ঘড়ি সিঙ্ক্রোনাইজ করা হচ্ছে"
    elif cmd == "আলার্ম_সেট_করো":
        return "আলার্ম সেট করা হচ্ছে"
    elif cmd == "আলার্ম_বন্ধ_করো":
        return "আলার্ম বন্ধ করা হচ্ছে"
    elif cmd == "টাইমার_চালু_করো":
        return "টাইমার চালু করা হচ্ছে"
    elif cmd == "টাইমার_বন্ধ_করো":
        return "টাইমার বন্ধ করা হচ্ছে"
    elif cmd == "স্টপওয়াচ_শুরু_করো":
        return "স্টপওয়াচ শুরু করা হচ্ছে"
    elif cmd == "স্টপওয়াচ_রুদ্ধ_করো":
        return "স্টপওয়াচ বন্ধ করা হচ্ছে"
    elif cmd == "সময়_মাপো":
        return "সময় মাপা হচ্ছে"
    elif cmd == "ঘড়ির_সময়_দেখাও":
        return "ঘড়ির সময় দেখানো হচ্ছে"
    elif cmd == "ক্যালেন্ডার_খুলো":
        return "ক্যালেন্ডার খোলা হচ্ছে"
    elif cmd == "তারিখ_সেট_করো":
        return "তারিখ সেট করা হচ্ছে"
    elif cmd == "সপ্তাহের_দিন_বলুন":
        return "সপ্তাহের দিন জানানো হচ্ছে"
    elif cmd == "মাসের_শেষ_দিন":
        return "মাসের শেষ দিন জানানো হচ্ছে"
    elif cmd == "বছরের_শেষ_দিন":
        return "বছরের শেষ দিন জানানো হচ্ছে"
    elif cmd == "কয়েক_ঘন্টা_বাকি":
        return "কয়েক ঘণ্টা বাকি"
    elif cmd == "কয়েক_মিনিট_বাকি":
        return "কয়েক মিনিট বাকি"
    elif cmd == "ঘুম_সময়":
        return "ঘুমের সময়"
    elif cmd == "জাগ্রত_সময়":
        return "জাগ্রত থাকার সময়"
    elif cmd == "সময়_স্মরণ করো":
        return "সময় স্মরণ করানো হচ্ছে"
    elif cmd == "সময়_স্মৃতি":
        return "সময় স্মৃতি দেখানো হচ্ছে"
    elif cmd == "বেলুন বাজাও":
        return "বেলুন বাজানো হচ্ছে"
    elif cmd == "সক্রিয়_সময়":
        return "সক্রিয় সময় চলছে"
    elif cmd == "নিষ্ক্রিয়_সময়":
        return "নিষ্ক্রিয় সময় চলছে"
    elif cmd == "আধা_ঘন্টা_পরে":
        return "আধা ঘণ্টা পরে"
    elif cmd == "এক_ঘন্টা_পরে":
        return "এক ঘণ্টা পরে"
    elif cmd == "একদিন_পরে":
        return "এক দিন পরে"
    elif cmd == "সপ্তাহ_শেষ":
        return "সপ্তাহ শেষ"

    # 🔘 আবহাওয়া (৫০টি বাংলা কমান্ড)
    elif cmd == "আবহাওয়া_দেখাও":
        return "বর্তমান আবহাওয়া দেখানো হচ্ছে"
    elif cmd == "আজকের_আবহাওয়া":
        return "আজকের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "কালকের_আবহাওয়া":
        return "কালকের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "বৃষ্টি_হবে_কি":
        return "বৃষ্টি হবে কি না জানা হচ্ছে"
    elif cmd == "তাপমাত্রা_কত":
        return "বর্তমান তাপমাত্রা জানানো হচ্ছে"
    elif cmd == "বাতাসের_গতিবেগ":
        return "বাতাসের গতিবেগ জানানো হচ্ছে"
    elif cmd == "আর্দ্রতা_কত":
        return "আর্দ্রতার পরিমাণ জানানো হচ্ছে"
    elif cmd == "তাপমাত্রা_বাড়বে_কি":
        return "তাপমাত্রা বাড়বে কি না জানা হচ্ছে"
    elif cmd == "তাপমাত্রা_কমবে_কি":
        return "তাপমাত্রা কমবে কি না জানা হচ্ছে"
    elif cmd == "সকালের_আবহাওয়া":
        return "সকালের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "দুপুরের_আবহাওয়া":
        return "দুপুরের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "বিকেলের_আবহাওয়া":
        return "বিকেলের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "রাতের_আবহাওয়া":
        return "রাতের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "তুষারপাত_হবে_কি":
        return "তুষারপাত হবে কি না জানা হচ্ছে"
    elif cmd == "ধোঁয়া_আছে_কি":
        return "ধোঁয়া আছে কি না জানানো হচ্ছে"
    elif cmd == "তূর্নাদু_আছে_কি":
        return "তূর্নাদু আছে কি না জানা হচ্ছে"
    elif cmd == "ঝড়_আসছে_কি":
        return "ঝড় আসছে কি না জানা হচ্ছে"
    elif cmd == "বাতাসের_দিক":
        return "বাতাসের দিক জানানো হচ্ছে"
    elif cmd == "মেঘলা_আছে_কি":
        return "মেঘলা আছে কি না জানা হচ্ছে"
    elif cmd == "সঠিক_আবহাওয়া_দাও":
        return "সঠিক আবহাওয়া তথ্য দেওয়া হচ্ছে"
    elif cmd == "আবহাওয়া_রিপোর্ট":
        return "আবহাওয়া রিপোর্ট তৈরি হচ্ছে"
    elif cmd == "বৃষ্টি_সম্ভাবনা":
        return "বৃষ্টির সম্ভাবনা জানানো হচ্ছে"
    elif cmd == "হিমবাহ_অবস্থা":
        return "হিমবাহের অবস্থা জানানো হচ্ছে"
    elif cmd == "তাপমাত্রা_অনুমান":
        return "তাপমাত্রার অনুমান দেওয়া হচ্ছে"
    elif cmd == "আবহাওয়া_আপডেট":
        return "আবহাওয়া আপডেট দেওয়া হচ্ছে"
    elif cmd == "আবহাওয়া_সতর্কতা":
        return "আবহাওয়া সতর্কতা জারি"
    elif cmd == "বৃষ্টির_আবহাওয়া":
        return "বৃষ্টির আবহাওয়া জানানো হচ্ছে"
    elif cmd == "সুর্য_উদয়_সময়":
        return "সুর্যোদয়ের সময় জানানো হচ্ছে"
    elif cmd == "সুর্যাস্ত_সময়":
        return "সুর্যাস্তের সময় জানানো হচ্ছে"
    elif cmd == "জলবায়ু_পরিবর্তন":
        return "জলবায়ু পরিবর্তন বিষয়ক তথ্য"
    elif cmd == "গ্রীষ্ম_কালীন_আবহাওয়া":
        return "গ্রীষ্মের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "শীত_কালীন_আবহাওয়া":
        return "শীতের আবহাওয়া জানানো হচ্ছে"
    elif cmd == "বর্ষা_কালীন_আবহাওয়া":
        return "বর্ষার আবহাওয়া জানানো হচ্ছে"
    elif cmd == "আবহাওয়া_পরিসংখ্যান":
        return "আবহাওয়া পরিসংখ্যান দেখানো হচ্ছে"
    elif cmd == "আবহাওয়া_ভবিষ্যত":
        return "আবহাওয়ার ভবিষ্যত জানানো হচ্ছে"
    elif cmd == "আবহাওয়া_পরিবর্তন":
        return "আবহাওয়া পরিবর্তনের তথ্য"
    elif cmd == "উষ্ণতা_বৃদ্ধি":
        return "উষ্ণতা বৃদ্ধির তথ্য"
    elif cmd == "ঠান্ডা_আবহাওয়া":
        return "ঠান্ডা আবহাওয়ার তথ্য"
    elif cmd == "আবহাওয়া_সতর্কতা_নিম্নমুখী":
        return "আবহাওয়া সতর্কতা নিম্নমুখী"
    elif cmd == "আবহাওয়া_সতর্কতা_উচ্চমুখী":
        return "আবহাওয়া সতর্কতা উচ্চমুখী"
    elif cmd == "বৃষ্টির_তীব্রতা":
        return "বৃষ্টির তীব্রতা জানানো হচ্ছে"
    elif cmd == "জলবায়ুর_উষ্ণতা":
        return "জলবায়ুর উষ্ণতা তথ্য"
    elif cmd == "আবহাওয়া_সংকেত":
        return "আবহাওয়া সংকেত দেখানো হচ্ছে"
    elif cmd == "মৌসুমী_আবহাওয়া":
        return "মৌসুমী আবহাওয়া তথ্য"
    elif cmd == "বাতাসের_চাপ":
        return "বাতাসের চাপ জানানো হচ্ছে"
    # 🔘 গান / অডিও (৫০টি বাংলা কমান্ড)
    elif cmd == "গান_চালাও":
        return "গান চালু করা হচ্ছে"
    elif cmd == "গান_বন্ধ_করো":
        return "গান বন্ধ করা হচ্ছে"
    elif cmd == "পরবর্তী_গান":
        return "পরবর্তী গান চালু করা হচ্ছে"
    elif cmd == "পূর্ববর্তী_গান":
        return "পূর্ববর্তী গান চালু করা হচ্ছে"
    elif cmd == "গান_পজ_করো":
        return "গান পজ করা হচ্ছে"
    elif cmd == "গান_পুনরায়_চালাও":
        return "গান পুনরায় চালানো হচ্ছে"
    elif cmd == "ভলিউম_বাড়াও":
        return "ভলিউম বাড়ানো হচ্ছে"
    elif cmd == "ভলিউম_কমানো":
        return "ভলিউম কমানো হচ্ছে"
    elif cmd == "মিউট_করো":
        return "মিউট চালু করা হচ্ছে"
    elif cmd == "মিউট_বন্ধ_করো":
        return "মিউট বন্ধ করা হচ্ছে"
    elif cmd == "গান_রিপিট_করো":
        return "গান রিপিট মোড চালু"
    elif cmd == "গান_শাফল_করো":
        return "গান শাফল মোড চালু"
    elif cmd == "গান_লিস্ট_দেখাও":
        return "গানের তালিকা দেখানো হচ্ছে"
    elif cmd == "পছন্দের_গান_চালাও":
        return "পছন্দের গান চালু"
    elif cmd == "গান_বাধা_দাও":
        return "গানের বাধা দেওয়া হচ্ছে"
    elif cmd == "গান_স্টপ_করো":
        return "গান বন্ধ করা হচ্ছে"
    elif cmd == "অডিও_চালাও":
        return "অডিও প্লে করা হচ্ছে"
    elif cmd == "অডিও_বন্ধ_করো":
        return "অডিও বন্ধ করা হচ্ছে"
    elif cmd == "রেকর্ডিং_শুরু":
        return "রেকর্ডিং শুরু করা হয়েছে"
    elif cmd == "রেকর্ডিং_বন্ধ_করো":
        return "রেকর্ডিং বন্ধ করা হয়েছে"
    elif cmd == "অডিও_পজ_করো":
        return "অডিও পজ করা হয়েছে"
    elif cmd == "অডিও_পুনরায়_চালাও":
        return "অডিও পুনরায় চালানো হয়েছে"
    elif cmd == "প্লেলিস্ট_সেভ_করো":
        return "প্লেলিস্ট সংরক্ষণ করা হয়েছে"
    elif cmd == "প্লেলিস্ট_লোড_করো":
        return "প্লেলিস্ট লোড করা হয়েছে"
    elif cmd == "গান_অনুসন্ধান_করো":
        return "গান অনুসন্ধান করা হচ্ছে"
    elif cmd == "গান_ডাউনলোড_করো":
        return "গান ডাউনলোড করা হচ্ছে"
    elif cmd == "অডিও_স্লাইডার_সেট_করো":
        return "অডিও স্লাইডার সেট করা হয়েছে"
    elif cmd == "গান_রেটিং_দাও":
        return "গান রেটিং দেওয়া হয়েছে"
    elif cmd == "গান_রিভিউ_লিখো":
        return "গান রিভিউ লেখা হয়েছে"
    elif cmd == "গান_শেয়ার_করো":
        return "গান শেয়ার করা হয়েছে"
    elif cmd == "গান_ফেভারিট_করো":
        return "গান প্রিয় হিসেবে চিহ্নিত করা হয়েছে"
    elif cmd == "অডিও_প্রোফাইল_সেট_করো":
        return "অডিও প্রোফাইল সেট করা হয়েছে"
    elif cmd == "গান_সার্চ_শুরু":
        return "গান সার্চ শুরু করা হয়েছে"
    elif cmd == "গান_সার্চ_বন্ধ_করো":
        return "গান সার্চ বন্ধ করা হয়েছে"
    elif cmd == "গানের_ধরন_পরিবর্তন":
        return "গানের ধরন পরিবর্তন করা হয়েছে"
    elif cmd == "গান_ফাইল_সেভ_করো":
        return "গানের ফাইল সংরক্ষণ করা হয়েছে"
    elif cmd == "গান_অবস্থান_খুঁজো":
        return "গানের অবস্থান খুঁজে পাওয়া গেছে"
    elif cmd == "গান_শ্রবণ_অবস্থা":
        return "গান শ্রবণ অবস্থা চলছে"
    elif cmd == "গানের_স্বর_সেট_করো":
        return "গানের স্বর সেট করা হয়েছে"
    elif cmd == "গানের_বিট_সেট_করো":
        return "গানের বিট সেট করা হয়েছে"
    elif cmd == "গানের_গতি_সেট_করো":
        return "গানের গতি সেট করা হয়েছে"
    elif cmd == "গানের_রেকর্ড_শুরু":
        return "গানের রেকর্ড শুরু হয়েছে"
    elif cmd == "গানের_রেকর্ড_বন্ধ_করো":
        return "গানের রেকর্ড বন্ধ হয়েছে"
    elif cmd == "অডিও_স্ট্রিম_শুরু":
        return "অডিও স্ট্রিম শুরু হয়েছে"
    elif cmd == "অডিও_স্ট্রিম_বন্ধ_করো":
        return "অডিও স্ট্রিম বন্ধ হয়েছে"

    # 🔘 যন্ত্র/সরঞ্জাম নিয়ন্ত্রণ (৫০টি বাংলা কমান্ড)
    elif cmd == "লাইট_জ্বালাও":
        return "লাইট জ্বালানো হচ্ছে"
    elif cmd == "লাইট_বন্ধ_করো":
        return "লাইট বন্ধ করা হচ্ছে"
    elif cmd == "ফ্যান_চালাও":
        return "ফ্যান চালানো হচ্ছে"
    elif cmd == "ফ্যান_বন্ধ_করো":
        return "ফ্যান বন্ধ করা হচ্ছে"
    elif cmd == "দরজা_খুলো":
        return "দরজা খোলা হচ্ছে"
    elif cmd == "দরজা_বন্ধ_করো":
        return "দরজা বন্ধ করা হচ্ছে"
    elif cmd == "এসি_চালাও":
        return "এসি চালানো হচ্ছে"
    elif cmd == "এসি_বন্ধ_করো":
        return "এসি বন্ধ করা হচ্ছে"
    elif cmd == "টিভি_চালাও":
        return "টিভি চালানো হচ্ছে"
    elif cmd == "টিভি_বন্ধ_করো":
        return "টিভি বন্ধ করা হচ্ছে"
    elif cmd == "রেডিও_চালাও":
        return "রেডিও চালানো হচ্ছে"
    elif cmd == "রেডিও_বন্ধ_করো":
        return "রেডিও বন্ধ করা হচ্ছে"
    elif cmd == "ফ্যানের_গতিবেগ_বাড়াও":
        return "ফ্যানের গতিবেগ বাড়ানো হচ্ছে"
    elif cmd == "ফ্যানের_গতিবেগ_কমানো":
        return "ফ্যানের গতিবেগ কমানো হচ্ছে"
    elif cmd == "লাইটের_উজ্জ্বলতা_বাড়াও":
        return "লাইটের উজ্জ্বলতা বাড়ানো হচ্ছে"
    elif cmd == "লাইটের_উজ্জ্বলতা_কমানো":
        return "লাইটের উজ্জ্বলতা কমানো হচ্ছে"
    elif cmd == "গ্যাস_চুলা_চালাও":
        return "গ্যাস চুলা চালানো হচ্ছে"
    elif cmd == "গ্যাস_চুলা_বন্ধ_করো":
        return "গ্যাস চুলা বন্ধ করা হচ্ছে"
    elif cmd == "পাখা_ঘোরাও":
        return "পাখা ঘোরানো হচ্ছে"
    elif cmd == "পাখা_বন্ধ_করো":
        return "পাখা বন্ধ করা হচ্ছে"
    elif cmd == "জল_পাম্প_চালাও":
        return "জল পাম্প চালানো হচ্ছে"
    elif cmd == "জল_পাম্প_বন্ধ_করো":
        return "জল পাম্প বন্ধ করা হচ্ছে"
    elif cmd == "গরম_পানি_চালাও":
        return "গরম পানি চালানো হচ্ছে"
    elif cmd == "গরম_পানি_বন্ধ_করো":
        return "গরম পানি বন্ধ করা হচ্ছে"
    elif cmd == "বাতি_জ্বালাও":
        return "বাতি জ্বালানো হচ্ছে"
    elif cmd == "বাতি_বন্ধ_করো":
        return "বাতি বন্ধ করা হচ্ছে"
    elif cmd == "ফ্রিজ_চালাও":
        return "ফ্রিজ চালানো হচ্ছে"
    elif cmd == "ফ্রিজ_বন্ধ_করো":
        return "ফ্রিজ বন্ধ করা হচ্ছে"
    elif cmd == "ওভেন_চালাও":
        return "ওভেন চালানো হচ্ছে"
    elif cmd == "ওভেন_বন্ধ_করো":
        return "ওভেন বন্ধ করা হচ্ছে"
    elif cmd == "জেনারেটর_চালাও":
        return "জেনারেটর চালানো হচ্ছে"
    elif cmd == "জেনারেটর_বন্ধ_করো":
        return "জেনারেটর বন্ধ করা হচ্ছে"
    elif cmd == "ভ্যাকুয়াম_চালাও":
        return "ভ্যাকুয়াম চালানো হচ্ছে"
    elif cmd == "ভ্যাকুয়াম_বন্ধ_করো":
        return "ভ্যাকুয়াম বন্ধ করা হচ্ছে"
    elif cmd == "ইনভার্টার_চালাও":
        return "ইনভার্টার চালানো হচ্ছে"
    elif cmd == "ইনভার্টার_বন্ধ_করো":
        return "ইনভার্টার বন্ধ করা হচ্ছে"
    elif cmd == "ওয়াশিং_মেশিন_চালাও":
        return "ওয়াশিং মেশিন চালানো হচ্ছে"
    elif cmd == "ওয়াশিং_মেশিন_বন্ধ_করো":
        return "ওয়াশিং মেশিন বন্ধ করা হচ্ছে"
    elif cmd == "মাইক্রোওয়েভ_চালাও":
        return "মাইক্রোওয়েভ চালানো হচ্ছে"
    elif cmd == "মাইক্রোওয়েভ_বন্ধ_করো":
        return "মাইক্রোওয়েভ বন্ধ করা হচ্ছে"
    elif cmd == "কফি_মেশিন_চালাও":
        return "কফি মেশিন চালানো হচ্ছে"
    elif cmd == "কফি_মেশিন_বন্ধ_করো":
        return "কফি মেশিন বন্ধ করা হচ্ছে"
    elif cmd == "ডিশওয়াশার_চালাও":
        return "ডিশওয়াশার চালানো হচ্ছে"
    elif cmd == "ডিশওয়াশার_বন্ধ_করো":
        return "ডিশওয়াশার বন্ধ করা হচ্ছে"

    # 🔘 স্মৃতি/ডেটা (৫০টি বাংলা কমান্ড)
    elif cmd == "স্মৃতি_সংরক্ষণ":
        return "স্মৃতি সংরক্ষণ করা হচ্ছে"
    elif cmd == "স্মৃতি_পুনরুদ্ধার":
        return "স্মৃতি পুনরুদ্ধার করা হচ্ছে"
    elif cmd == "তথ্য_সংরক্ষণ":
        return "তথ্য সংরক্ষণ করা হচ্ছে"
    elif cmd == "তথ্য_পুনরুদ্ধার":
        return "তথ্য পুনরুদ্ধার করা হচ্ছে"
    elif cmd == "তথ্য_মুছুন":
        return "তথ্য মুছে ফেলা হচ্ছে"
    elif cmd == "স্মৃতি_মুছুন":
        return "স্মৃতি মুছে ফেলা হচ্ছে"
    elif cmd == "তথ্য_হালনাগাদ":
        return "তথ্য হালনাগাদ করা হচ্ছে"
    elif cmd == "স্মৃতি_হালনাগাদ":
        return "স্মৃতি হালনাগাদ করা হচ্ছে"
    elif cmd == "তথ্য_অনুসন্ধান":
        return "তথ্য অনুসন্ধান করা হচ্ছে"
    elif cmd == "স্মৃতি_অনুসন্ধান":
        return "স্মৃতি অনুসন্ধান করা হচ্ছে"
    elif cmd == "ডেটা_আপলোড":
        return "ডেটা আপলোড করা হচ্ছে"
    elif cmd == "ডেটা_ডাউনলোড":
        return "ডেটা ডাউনলোড করা হচ্ছে"
    elif cmd == "স্মৃতি_লক_করুন":
        return "স্মৃতি লক করা হচ্ছে"
    elif cmd == "স্মৃতি_আনলক_করুন":
        return "স্মৃতি আনলক করা হচ্ছে"
    elif cmd == "তথ্য_ব্যাকআপ":
        return "তথ্য ব্যাকআপ নেওয়া হচ্ছে"
    elif cmd == "স্মৃতি_ব্যাকআপ":
        return "স্মৃতি ব্যাকআপ নেওয়া হচ্ছে"
    elif cmd == "তথ্য_মুছে_ফেলা":
        return "তথ্য মুছে ফেলা হচ্ছে"
    elif cmd == "স্মৃতি_রিসেট":
        return "স্মৃতি রিসেট করা হচ্ছে"
    elif cmd == "তথ্য_সিঙ্ক্রোনাইজ":
        return "তথ্য সিঙ্ক্রোনাইজ করা হচ্ছে"
    elif cmd == "স্মৃতি_সিঙ্ক্রোনাইজ":
        return "স্মৃতি সিঙ্ক্রোনাইজ করা হচ্ছে"
    elif cmd == "তথ্য_সংরক্ষণ_করা_হয়েছ":
        return "তথ্য সফলভাবে সংরক্ষিত হয়েছে"
    elif cmd == "স্মৃতি_সংরক্ষণ_করা_হয়েছ":
        return "স্মৃতি সফলভাবে সংরক্ষিত হয়েছে"
    elif cmd == "ডেটা_পরিবর্তন":
        return "ডেটা পরিবর্তন করা হচ্ছে"
    elif cmd == "স্মৃতি_পরিবর্তন":
        return "স্মৃতি পরিবর্তন করা হচ্ছে"
    elif cmd == "তথ্য_রিপোর্ট":
        return "তথ্যের রিপোর্ট তৈরি হচ্ছে"
    elif cmd == "স্মৃতি_রিপোর্ট":
        return "স্মৃতির রিপোর্ট তৈরি হচ্ছে"
    elif cmd == "তথ্য_পর্যালোচনা":
        return "তথ্য পর্যালোচনা করা হচ্ছে"
    elif cmd == "স্মৃতি_পর্যালোচনা":
        return "স্মৃতি পর্যালোচনা করা হচ্ছে"
    elif cmd == "তথ্য_লক_খুলো":
        return "তথ্য লক খোলা হচ্ছে"
    elif cmd == "স্মৃতি_লক_খুলো":
        return "স্মৃতি লক খোলা হচ্ছে"
    elif cmd == "ডেটা_অ্যাক্সেস":
        return "ডেটা অ্যাক্সেস করা হচ্ছে"
    elif cmd == "স্মৃতি_অ্যাক্সেস":
        return "স্মৃতি অ্যাক্সেস করা হচ্ছে"
    elif cmd == "তথ্য_সংরক্ষণ_বাতিল":
        return "তথ্য সংরক্ষণ বাতিল করা হয়েছে"
    elif cmd == "স্মৃতি_সংরক্ষণ_বাতিল":
        return "স্মৃতি সংরক্ষণ বাতিল করা হয়েছে"
    elif cmd == "ডেটা_ফাইল_সেভ":
        return "ডেটা ফাইল সংরক্ষণ করা হয়েছে"
    elif cmd == "স্মৃতি_ফাইল_সেভ":
        return "স্মৃতি ফাইল সংরক্ষণ করা হয়েছে"
    elif cmd == "তথ্য_মেট্রিক_দেখাও":
        return "তথ্যের মেট্রিক দেখানো হচ্ছে"
    elif cmd == "স্মৃতি_মেট্রিক_দেখাও":
        return "স্মৃতির মেট্রিক দেখানো হচ্ছে"
    elif cmd == "তথ্য_তৈরি_করো":
        return "তথ্য তৈরি করা হচ্ছে"
    elif cmd == "স্মৃতি_তৈরি_করো":
        return "স্মৃতি তৈরি করা হচ্ছে"
    elif cmd == "ডেটা_রিসেট":
        return "ডেটা রিসেট করা হচ্ছে"
    elif cmd == "স্মৃতি_ক্লিয়ার":
        return "স্মৃতি ক্লিয়ার করা হচ্ছে"
    elif cmd == "ডেটা_সংশোধন":
        return "ডেটা সংশোধন করা হচ্ছে"
    elif cmd == "স্মৃতি_সংশোধন":
        return "স্মৃতি সংশোধন করা হচ্ছে"
    elif cmd == "তথ্য_ডিলিট":
        return "তথ্য ডিলিট করা হচ্ছে"
    elif cmd == "স্মৃতি_ডিলিট":
        return "স্মৃতি ডিলিট করা হচ্ছে"

    # 🔘 নিরাপত্তা (৫০টি বাংলা কমান্ড)
    elif cmd == "পাসওয়ার্ড_সেট_করো":
        return "পাসওয়ার্ড সেট করা হচ্ছে"
    elif cmd == "পাসওয়ার্ড_পরিবর্তন_করো":
        return "পাসওয়ার্ড পরিবর্তন করা হচ্ছে"
    elif cmd == "সিস্টেম_লক_করো":
        return "সিস্টেম লক করা হচ্ছে"
    elif cmd == "সিস্টেম_আনলক_করো":
        return "সিস্টেম আনলক করা হচ্ছে"
    elif cmd == "নিরাপত্তা_তদন্ত_শুরু":
        return "নিরাপত্তা তদন্ত শুরু হয়েছে"
    elif cmd == "নিরাপত্তা_তদন্ত_বন্ধ_করো":
        return "নিরাপত্তা তদন্ত বন্ধ করা হয়েছে"
    elif cmd == "অ্যাক্সেস_নিরোধ_করো":
        return "অ্যাক্সেস নিষিদ্ধ করা হয়েছে"
    elif cmd == "অ্যাক্সেস_অনুমোদন_করো":
        return "অ্যাক্সেস অনুমোদিত হয়েছে"
    elif cmd == "ফায়ারওয়াল_চালু_করো":
        return "ফায়ারওয়াল চালু করা হয়েছে"
    elif cmd == "ফায়ারওয়াল_বন্ধ_করো":
        return "ফায়ারওয়াল বন্ধ করা হয়েছে"
    elif cmd == "লগইন_করো":
        return "লগইন সম্পন্ন হয়েছে"
    elif cmd == "লগআউট_করো":
        return "লগআউট সম্পন্ন হয়েছে"
    elif cmd == "বিভিন্ন_অ্যাকাউন্ট_নিয়ন্ত্রণ":
        return "বিভিন্ন অ্যাকাউন্ট নিয়ন্ত্রণ করা হচ্ছে"
    elif cmd == "ব্রুট_ফোর্স_আক্রমণ_নিরোধ":
        return "ব্রুট ফোর্স আক্রমণ নিরোধ করা হচ্ছে"
    elif cmd == "দ্বি-স্তরের_প্রমাণীকরণ_চালু_করো":
        return "দ্বি-স্তরের প্রমাণীকরণ চালু করা হয়েছে"
    elif cmd == "দ্বি-স্তরের_প্রমাণীকরণ_বন্ধ_করো":
        return "দ্বি-স্তরের প্রমাণীকরণ বন্ধ করা হয়েছে"
    elif cmd == "সিসিটিভি_সক্রিয়_করো":
        return "সিসিটিভি সক্রিয় করা হয়েছে"
    elif cmd == "সিসিটিভি_বন্ধ_করো":
        return "সিসিটিভি বন্ধ করা হয়েছে"
    elif cmd == "অ্যান্টিভাইরাস_চালু_করো":
        return "অ্যান্টিভাইরাস চালু করা হয়েছে"
    elif cmd == "অ্যান্টিভাইরাস_আপডেট_করো":
        return "অ্যান্টিভাইরাস আপডেট করা হয়েছে"
    elif cmd == "অ্যান্টিভাইরাস_স্ক্যান_করো":
        return "অ্যান্টিভাইরাস স্ক্যান চলছে"
    elif cmd == "ম্যালওয়্যার_নিরসন_করো":
        return "ম্যালওয়্যার নিরসন করা হচ্ছে"
    elif cmd == "ফিঙ্গারপ্রিন্ট_লক_সেট_করো":
        return "ফিঙ্গারপ্রিন্ট লক সেট করা হয়েছে"
    elif cmd == "ফিঙ্গারপ্রিন্ট_লক_খুলো":
        return "ফিঙ্গারপ্রিন্ট লক খোলা হয়েছে"
    elif cmd == "আইপি_অ্যাক্সেস_নিয়ন্ত্রণ":
        return "আইপি অ্যাক্সেস নিয়ন্ত্রণ করা হচ্ছে"
    elif cmd == "ডেটা_এনক্রিপশন_চালু_করো":
        return "ডেটা এনক্রিপশন চালু করা হয়েছে"
    elif cmd == "ডেটা_ডিক্রিপশন_করো":
        return "ডেটা ডিক্রিপশন করা হচ্ছে"
    elif cmd == "নিরাপত্তা_সংক্রান্ত_বার্তা_দেখাও":
        return "নিরাপত্তা সংক্রান্ত বার্তা দেখানো হচ্ছে"
    elif cmd == "সিকিউরিটি_অ্যালার্ম_চালু_করো":
        return "সিকিউরিটি অ্যালার্ম চালু করা হয়েছে"
    elif cmd == "সিকিউরিটি_অ্যালার্ম_বন্ধ_করো":
        return "সিকিউরিটি অ্যালার্ম বন্ধ করা হয়েছে"
    elif cmd == "জাল_লগইন_চেষ্টা_নির্দেশনা":
        return "জাল লগইন চেষ্টা শনাক্ত করা হয়েছে"
    elif cmd == "ব্লক_ইউজার_অ্যাকাউন্ট":
        return "ইউজার অ্যাকাউন্ট ব্লক করা হয়েছে"
    elif cmd == "আনব্লক_ইউজার_অ্যাকাউন্ট":
        return "ইউজার অ্যাকাউন্ট আনব্লক করা হয়েছে"
    elif cmd == "পাসওয়ার্ড_রিসেট_করো":
        return "পাসওয়ার্ড রিসেট করা হয়েছে"
    elif cmd == "সফটওয়্যার_আপডেট_নিরাপত্তা":
        return "সফটওয়্যার আপডেট নিরাপত্তা যাচাই চলছে"
    elif cmd == "নেটওয়ার্ক_সুরক্ষা_পরীক্ষা":
        return "নেটওয়ার্ক সুরক্ষা পরীক্ষা চলছে"
    elif cmd == "বিভিন্ন_সার্ভার_নিরাপত্তা_পরীক্ষা":
        return "সার্ভার নিরাপত্তা পরীক্ষা চলছে"
    elif cmd == "সিকিউরিটি_লগ_দেখাও":
        return "সিকিউরিটি লগ দেখানো হচ্ছে"
    elif cmd == "হ্যাকিং_চেষ্টা_সনাক্ত_করো":
        return "হ্যাকিং চেষ্টা সনাক্ত করা হয়েছে"
    elif cmd == "সেশন_সমাপ্তি":
        return "সেশন সমাপ্ত করা হয়েছে"
    elif cmd == "নিরাপত্তা_পরামর্শ_দাও":
        return "নিরাপত্তা পরামর্শ দেওয়া হচ্ছে"
    elif cmd == "অ্যাকাউন্ট_লক_শুরু":
        return "অ্যাকাউন্ট লক শুরু হয়েছে"
    elif cmd == "অ্যাকাউন্ট_লক_সর্বশেষ_অবস্থা":
        return "অ্যাকাউন্ট লকের সর্বশেষ অবস্থা"
    elif cmd == "নিরাপত্তা_প্রোটোকল_আপডেট":
        return "নিরাপত্তা প্রোটোকল আপডেট করা হচ্ছে"

    # 🔘 নেটওয়ার্ক/ইন্টারনেট (৫০টি বাংলা কমান্ড)
    elif cmd == "নেটওয়ার্ক_সংযোগ_চেক_করো":
        return "নেটওয়ার্ক সংযোগ পরীক্ষা করা হচ্ছে"
    elif cmd == "ইন্টারনেট_চালু_করো":
        return "ইন্টারনেট চালু করা হচ্ছে"
    elif cmd == "ইন্টারনেট_বন্ধ_করো":
        return "ইন্টারনেট বন্ধ করা হচ্ছে"
    elif cmd == "ওয়াইফাই_স্ক্যান_করো":
        return "ওয়াইফাই স্ক্যান শুরু করা হচ্ছে"
    elif cmd == "ওয়াইফাই_যোগাযোগ_স্থাপন":
        return "ওয়াইফাই সংযোগ স্থাপন করা হচ্ছে"
    elif cmd == "ওয়াইফাই_সংযোগ_ছাড়াও":
        return "ওয়াইফাই সংযোগ ছাড়া হচ্ছে"
    elif cmd == "আইপি_ঠিকানা_দেখাও":
        return "আইপি ঠিকানা দেখানো হচ্ছে"
    elif cmd == "ডিএনএস_কনফিগার_করো":
        return "ডিএনএস কনফিগারেশন চলছে"
    elif cmd == "নেটওয়ার্ক_রিস্টার্ট_করো":
        return "নেটওয়ার্ক রিস্টার্ট করা হচ্ছে"
    elif cmd == "পিং_পরীক্ষা_করো":
        return "পিং পরীক্ষা চলছে"
    elif cmd == "ব্যান্ডউইথ_পরিমাপ_করো":
        return "ব্যান্ডউইথ পরিমাপ করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ট্রাফিক_মতিগ্রহণ_করো":
        return "নেটওয়ার্ক ট্রাফিক মনিটর করা হচ্ছে"
    elif cmd == "ওয়াইফাই_পাসওয়ার্ড_পরিবর্তন":
        return "ওয়াইফাই পাসওয়ার্ড পরিবর্তন করা হচ্ছে"
    elif cmd == "ওয়াইফাই_নিরাপত্তা_সেটিংস":
        return "ওয়াইফাই নিরাপত্তা সেটিংস আপডেট হচ্ছে"
    elif cmd == "ম্যাক_ফিল্টারিং_চালু_করো":
        return "ম্যাক ফিল্টারিং চালু করা হয়েছে"
    elif cmd == "ম্যাক_ফিল্টারিং_বন্ধ_করো":
        return "ম্যাক ফিল্টারিং বন্ধ করা হয়েছে"
    elif cmd == "নেটওয়ার্ক_গতি_পরীক্ষা":
        return "নেটওয়ার্ক গতি পরীক্ষা করা হচ্ছে"
    elif cmd == "ইন্টারনেট_ব্যান্ডউইথ_সীমাবদ্ধ_করো":
        return "ইন্টারনেট ব্যান্ডউইথ সীমাবদ্ধ করা হচ্ছে"
    elif cmd == "ওয়াইফাই_নেটওয়ার্ক_নাম_পরিবর্তন":
        return "ওয়াইফাই নেটওয়ার্ক নাম পরিবর্তন করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ডিভাইস_সংযোগ_পরীক্ষা":
        return "নেটওয়ার্ক ডিভাইস সংযোগ পরীক্ষা করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_আইডি_সেট_করো":
        return "নেটওয়ার্ক আইডি সেট করা হচ্ছে"
    elif cmd == "ইন্টারনেট_বিচ্ছিন্ন_করো":
        return "ইন্টারনেট বিচ্ছিন্ন করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_গুরুত্বপূর্ণ_নোটিফিকেশন_দাও":
        return "নেটওয়ার্ক গুরুত্বপূর্ণ নোটিফিকেশন দেখানো হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ডিভাইস_রিবুট_করো":
        return "নেটওয়ার্ক ডিভাইস রিবুট করা হচ্ছে"
    elif cmd == "ওয়াইফাই_অটোমেটিক_কানেক্ট":
        return "ওয়াইফাই অটোমেটিক কানেক্ট চালু করা হয়েছে"
    elif cmd == "নেটওয়ার্ক_ডিএসএল_চালু_করো":
        return "নেটওয়ার্ক ডিএসএল চালু করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ডিএসএল_বন্ধ_করো":
        return "নেটওয়ার্ক ডিএসএল বন্ধ করা হচ্ছে"
    elif cmd == "ইন্টারনেট_প্রক্সি_সেট_করো":
        return "ইন্টারনেট প্রোক্সি সেট করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ট্রাফিক_ব্লক_করো":
        return "নেটওয়ার্ক ট্রাফিক ব্লক করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ট্রাফিক_আনলক_করো":
        return "নেটওয়ার্ক ট্রাফিক আনলক করা হচ্ছে"
    elif cmd == "ওয়াইফাই_সিগন্যাল_শক্তি_পরীক্ষা":
        return "ওয়াইফাই সিগন্যাল শক্তি পরীক্ষা করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_গেটওয়ে_সেট_করো":
        return "নেটওয়ার্ক গেটওয়ে সেট করা হচ্ছে"
    elif cmd == "আইপি_অ্যাসাইন_করো":
        return "আইপি অ্যাসাইন করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_সার্ভার_কানেক্ট_করো":
        return "নেটওয়ার্ক সার্ভারে কানেক্ট করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_সার্ভার_ডিসকানেক্ট_করো":
        return "নেটওয়ার্ক সার্ভার থেকে ডিসকানেক্ট করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_সেটিংস_রিসেট":
        return "নেটওয়ার্ক সেটিংস রিসেট করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ডাটা_মোড_পরিবর্তন":
        return "নেটওয়ার্ক ডাটা মোড পরিবর্তন করা হচ্ছে"
    elif cmd == "ওয়াইফাই_নেটওয়ার্ক_স্ক্যান_তালিকা":
        return "ওয়াইফাই নেটওয়ার্ক স্ক্যান তালিকা দেখানো হচ্ছে"
    elif cmd == "নেটওয়ার্ক_ব্যবহার_পরিসংখ্যান":
        return "নেটওয়ার্ক ব্যবহার পরিসংখ্যান দেখানো হচ্ছে"
    elif cmd == "ইন্টারনেট_ব্রাউজিং_স্টার্ট":
        return "ইন্টারনেট ব্রাউজিং শুরু করা হচ্ছে"
    elif cmd == "নেটওয়ার্ক_সংযোগ_সংক্রান্ত_সাহায্য":
        return "নেটওয়ার্ক সংযোগ সংক্রান্ত সাহায্য দেওয়া হচ্ছে"
    elif cmd == "নেটওয়ার্ক_সংযোগ_বাতিল":
        return "নেটওয়ার্ক সংযোগ বাতিল করা হচ্ছে"
    elif cmd == "ইন্টারনেট_ডাউনলোড_শুরু":
        return "ইন্টারনেট ডাউনলোড শুরু হয়েছে"
    # 🔘 ভাষা/অনুবাদ (৫০টি বাংলা কমান্ড)
    elif cmd == "ভাষা_পরিবর্তন_করো":
        return "ভাষা পরিবর্তন করা হচ্ছে"
    elif cmd == "বাংলা_সেট_করো":
        return "বাংলা ভাষা চালু করা হচ্ছে"
    elif cmd == "ইংরেজি_সেট_করো":
        return "ইংরেজি ভাষা চালু করা হচ্ছে"
    elif cmd == "হিন্দি_সেট_করো":
        return "হিন্দি ভাষা চালু করা হচ্ছে"
    elif cmd == "স্প্যানিশ_সেট_করো":
        return "স্প্যানিশ ভাষা চালু করা হচ্ছে"
    elif cmd == "ফ্রেঞ্চ_সেট_করো":
        return "ফ্রেঞ্চ ভাষা চালু করা হচ্ছে"
    elif cmd == "জার্মান_সেট_করো":
        return "জার্মান ভাষা চালু করা হচ্ছে"
    elif cmd == "অনুবাদ_শুরু_করো":
        return "অনুবাদ শুরু করা হচ্ছে"
    elif cmd == "অনুবাদ_বন্ধ_করো":
        return "অনুবাদ বন্ধ করা হচ্ছে"
    elif cmd == "অনুবাদ_ভাষা_নির্বাচন":
        return "অনুবাদের ভাষা নির্বাচন করা হচ্ছে"
    elif cmd == "টেক্সট_অনুবাদ_করো":
        return "টেক্সট অনুবাদ করা হচ্ছে"
    elif cmd == "বাক্য_অনুবাদ_করো":
        return "বাক্য অনুবাদ করা হচ্ছে"
    elif cmd == "শব্দ_অনুবাদ_করো":
        return "শব্দ অনুবাদ করা হচ্ছে"
    elif cmd == "ভাষা_পরিচয়_দাও":
        return "ভাষার পরিচয় দেওয়া হচ্ছে"
    elif cmd == "বহুভাষী_সক্রিয়_করো":
        return "বহুভাষী মোড চালু করা হচ্ছে"
    elif cmd == "ভাষা_পরিবর্তন_স্বীকার_করো":
        return "ভাষা পরিবর্তন স্বীকার করা হয়েছে"
    elif cmd == "অনুবাদ_ফলাফল_দেখাও":
        return "অনুবাদ ফলাফল দেখানো হচ্ছে"
    elif cmd == "ভাষা_পরীক্ষা_করো":
        return "ভাষা পরীক্ষা করা হচ্ছে"
    elif cmd == "অডিও_অনুবাদ_করো":
        return "অডিও অনুবাদ করা হচ্ছে"
    elif cmd == "ভাষা_স্বর_পরিবর্তন":
        return "ভাষার স্বর পরিবর্তন করা হচ্ছে"
    elif cmd == "ভাষা_সিন্থেসাইজ_করো":
        return "ভাষা সিন্থেসাইজ করা হচ্ছে"
    elif cmd == "বাক্যাংশ_অনুবাদ_করো":
        return "বাক্যাংশ অনুবাদ করা হচ্ছে"
    elif cmd == "ডকুমেন্ট_অনুবাদ_করো":
        return "ডকুমেন্ট অনুবাদ করা হচ্ছে"
    elif cmd == "অনুবাদ_বাতিল_করো":
        return "অনুবাদ বাতিল করা হচ্ছে"
    elif cmd == "ভাষা_মিশ্রণ_চালু_করো":
        return "ভাষা মিশ্রণ মোড চালু করা হচ্ছে"
    elif cmd == "ভাষা_বিকল্প_নির্বাচন":
        return "ভাষার বিকল্প নির্বাচন করা হচ্ছে"
    elif cmd == "অভিধান_খুঁজুন":
        return "অভিধান খোঁজা হচ্ছে"
    elif cmd == "ভাষা_প্যাক_আপডেট_করো":
        return "ভাষা প্যাক আপডেট করা হচ্ছে"
    elif cmd == "ভাষা_পরিচিতি_দেখাও":
        return "ভাষার পরিচিতি দেখানো হচ্ছে"
    elif cmd == "ভাষা_সিন্থেসাইজার_চালু_করো":
        return "ভাষা সিন্থেসাইজার চালু করা হচ্ছে"
    elif cmd == "ভাষা_সিন্থেসাইজার_বন্ধ_করো":
        return "ভাষা সিন্থেসাইজার বন্ধ করা হচ্ছে"
    elif cmd == "শব্দকোষ_আপডেট_করো":
        return "শব্দকোষ আপডেট করা হচ্ছে"
    elif cmd == "অনুবাদক_সেট_করো":
        return "অনুবাদক সেট করা হচ্ছে"
    elif cmd == "ভাষা_স্মৃতি_সংরক্ষণ":
        return "ভাষার স্মৃতি সংরক্ষণ করা হচ্ছে"
    elif cmd == "ভাষা_স্মৃতি_পুনরুদ্ধার":
        return "ভাষার স্মৃতি পুনরুদ্ধার করা হচ্ছে"
    elif cmd == "ভাষা_প্রশিক্ষণ_শুরু":
        return "ভাষা প্রশিক্ষণ শুরু হচ্ছে"
    elif cmd == "ভাষা_প্রশিক্ষণ_বন্ধ":
        return "ভাষা প্রশিক্ষণ বন্ধ হয়েছে"
    elif cmd == "ভাষা_নির্ণায়ক_চালু_করো":
        return "ভাষা নির্ণায়ক চালু করা হয়েছে"
    elif cmd == "ভাষা_নির্ণায়ক_বন্ধ_করো":
        return "ভাষা নির্ণায়ক বন্ধ করা হয়েছে"
    elif cmd == "অডিও_ভাষা_সেট_করো":
        return "অডিও ভাষা সেট করা হচ্ছে"
    elif cmd == "বাক্য_ভাষান্তর_করা":
        return "বাক্য ভাষান্তর করা হচ্ছে"
    elif cmd == "ভাষা_বাতিল_করো":
        return "ভাষা বাতিল করা হচ্ছে"
    elif cmd == "ভাষা_কোড_দেখাও":
        return "ভাষার কোড দেখানো হচ্ছে"
    elif cmd == "অনুবাদ_গুণমান_বর্ধন":
        return "অনুবাদের গুণমান বৃদ্ধি করা হচ্ছে"
    elif cmd == "ভাষা_পরিচিতি_আপডেট_করো":
        return "ভাষার পরিচিতি আপডেট করা হচ্ছে"
    elif cmd == "অনুবাদক_রিসেট_করো":
        return "অনুবাদক রিসেট করা হচ্ছে"
    # 🔘 ক্যামেরা/ফটো (৫০টি বাংলা কমান্ড)
    elif cmd == "ক্যামেরা_চালু_করো":
        return "ক্যামেরা চালু করা হচ্ছে"
    elif cmd == "ক্যামেরা_বন্ধ_করো":
        return "ক্যামেরা বন্ধ করা হচ্ছে"
    elif cmd == "ছবি_তুলো":
        return "ছবি তোলা হচ্ছে"
    elif cmd == "ভিডিও_রেকর্ড_শুরু_করো":
        return "ভিডিও রেকর্ড শুরু করা হচ্ছে"
    elif cmd == "ভিডিও_রেকর্ড_বন্ধ_করো":
        return "ভিডিও রেকর্ড বন্ধ করা হচ্ছে"
    elif cmd == "লাইভ_স্ট্রিম_শুরু_করো":
        return "লাইভ স্ট্রিম শুরু করা হচ্ছে"
    elif cmd == "লাইভ_স্ট্রিম_বন্ধ_করো":
        return "লাইভ স্ট্রিম বন্ধ করা হচ্ছে"
    elif cmd == "ফ্রন্ট_ক্যামেরা_সেট_করো":
        return "ফ্রন্ট ক্যামেরা চালু করা হচ্ছে"
    elif cmd == "ব্যাক_ক্যামেরা_সেট_করো":
        return "ব্যাক ক্যামেরা চালু করা হচ্ছে"
    elif cmd == "ফোকাস_সেট_করো":
        return "ফোকাস সেট করা হচ্ছে"
    elif cmd == "জুম_বাড়াও":
        return "জুম বাড়ানো হচ্ছে"
    elif cmd == "জুম_কমাও":
        return "জুম কমানো হচ্ছে"
    elif cmd == "ব্লুম_সেট_করো":
        return "ব্লুম সেট করা হচ্ছে"
    elif cmd == "কন্ট্রাস্ট_পরিবর্তন_করো":
        return "কন্ট্রাস্ট পরিবর্তন করা হচ্ছে"
    elif cmd == "ব্রাইটনেস_পরিবর্তন_করো":
        return "ব্রাইটনেস পরিবর্তন করা হচ্ছে"
    elif cmd == "ছবির_ফিল্টার_প্রয়োগ_করো":
        return "ছবির ফিল্টার প্রয়োগ করা হচ্ছে"
    elif cmd == "আল্ট্রা_হাই_রেজোলিউশন_সেট_করো":
        return "আল্ট্রা হাই রেজোলিউশন সেট করা হচ্ছে"
    elif cmd == "স্বয়ংক্রিয়_ফোকাস_চালু_করো":
        return "স্বয়ংক্রিয় ফোকাস চালু করা হচ্ছে"
    elif cmd == "মেনু_সেটিংস_খুলো":
        return "মেনু সেটিংস খোলা হচ্ছে"
    elif cmd == "ছবির_আকার_পরিবর্তন_করো":
        return "ছবির আকার পরিবর্তন করা হচ্ছে"
    elif cmd == "রেজোলিউশন_পরিবর্তন_করো":
        return "রেজোলিউশন পরিবর্তন করা হচ্ছে"
    elif cmd == "ছবি_সেভ_করো":
        return "ছবি সংরক্ষণ করা হচ্ছে"
    elif cmd == "ছবি_মুছুন":
        return "ছবি মুছে ফেলা হচ্ছে"
    elif cmd == "ভিডিও_প্লে_করো":
        return "ভিডিও চালানো হচ্ছে"
    elif cmd == "ভিডিও_পজ_করো":
        return "ভিডিও থামানো হয়েছে"
    elif cmd == "ফ্রেম_রেট_সেট_করো":
        return "ফ্রেম রেট সেট করা হচ্ছে"
    elif cmd == "ইমেজ_স্ট্যাবিলাইজেশন_চালু_করো":
        return "ইমেজ স্ট্যাবিলাইজেশন চালু করা হচ্ছে"
    elif cmd == "ইমেজ_স্ট্যাবিলাইজেশন_বন্ধ_করো":
        return "ইমেজ স্ট্যাবিলাইজেশন বন্ধ করা হচ্ছে"
    elif cmd == "ফেস_ডিটেকশন_চালু_করো":
        return "ফেস ডিটেকশন চালু করা হচ্ছে"
    elif cmd == "ফেস_ডিটেকশন_বন্ধ_করো":
        return "ফেস ডিটেকশন বন্ধ করা হচ্ছে"
    elif cmd == "রঙ_সেট_করো":
        return "রঙ সেট করা হচ্ছে"
    elif cmd == "শ্বেতস্বর_সেট_করো":
        return "শ্বেতস্বর সেট করা হচ্ছে"
    elif cmd == "হোয়াইট_ব্যালান্স_পরিবর্তন_করো":
        return "হোয়াইট ব্যালান্স পরিবর্তন করা হচ্ছে"
    elif cmd == "অটো_হোয়াইট_ব্যালান্স_চালু_করো":
        return "অটো হোয়াইট ব্যালান্স চালু করা হচ্ছে"
    elif cmd == "ম্যানুয়াল_হোয়াইট_ব্যালান্স_চালু_করো":
        return "ম্যানুয়াল হোয়াইট ব্যালান্স চালু করা হচ্ছে"
    elif cmd == "লেন্স_ক্লিন_করো":
        return "লেন্স পরিষ্কার করা হচ্ছে"
    elif cmd == "ছবি_প্রিভিউ_দেখাও":
        return "ছবি প্রিভিউ দেখানো হচ্ছে"
    elif cmd == "ভিডিও_প্রিভিউ_দেখাও":
        return "ভিডিও প্রিভিউ দেখানো হচ্ছে"
    elif cmd == "ক্যামেরা_সেটিংস_রিসেট_করো":
        return "ক্যামেরা সেটিংস রিসেট করা হচ্ছে"
    elif cmd == "ক্যামেরা_অটোমেটিক_চালু_করো":
        return "ক্যামেরা অটোমেটিক চালু করা হচ্ছে"
    elif cmd == "ক্যামেরা_ম্যানুয়াল_চালু_করো":
        return "ক্যামেরা ম্যানুয়াল চালু করা হচ্ছে"
    elif cmd == "গ্যালারি_খুলো":
        return "গ্যালারি খোলা হচ্ছে"
    elif cmd == "ছবি_শেয়ার_করো":
        return "ছবি শেয়ার করা হচ্ছে"
    elif cmd == "ভিডিও_শেয়ার_করো":
        return "ভিডিও শেয়ার করা হচ্ছে"
    elif cmd == "ছবি_এডিট_করো":
        return "ছবি এডিট করা হচ্ছে"
    elif cmd == "ভিডিও_এডিট_করো":
        return "ভিডিও এডিট করা হচ্ছে"
    elif cmd == "টাইম_ল্যাপস_রেকর্ড_করো":
        return "টাইম ল্যাপস রেকর্ড শুরু হয়েছে"

    # 🔘 ক্যালেন্ডার/ঘটনা (৫০টি বাংলা কমান্ড)
    elif cmd == "ক্যালেন্ডার_খুলো":
        return "ক্যালেন্ডার খোলা হচ্ছে"
    elif cmd == "নতুন_ঘটনা_যোগ_করো":
        return "নতুন ঘটনা যোগ করা হচ্ছে"
    elif cmd == "ঘটনা_দেখাও":
        return "ঘটনাগুলো দেখানো হচ্ছে"
    elif cmd == "আজকের_ঘটনা_দেখাও":
        return "আজকের ঘটনা দেখানো হচ্ছে"
    elif cmd == "আগামী_ঘটনা_দেখাও":
        return "আগামী ঘটনা দেখানো হচ্ছে"
    elif cmd == "ঘটনা_সম্পাদনা_করো":
        return "ঘটনা সম্পাদনা করা হচ্ছে"
    elif cmd == "ঘটনা_মুছে_ফেলো":
        return "ঘটনা মুছে ফেলা হচ্ছে"
    elif cmd == "ঘটনা_স্মরণ করাও":
        return "ঘটনা স্মরণ করানো হচ্ছে"
    elif cmd == "ক্যালেন্ডার_সিঙ্ক্রোনাইজ_করো":
        return "ক্যালেন্ডার সিঙ্ক্রোনাইজ করা হচ্ছে"
    elif cmd == "ক্যালেন্ডার_আপডেট_করো":
        return "ক্যালেন্ডার আপডেট করা হচ্ছে"
    elif cmd == "আজকের_তারিখ_দেখাও":
        return "আজকের তারিখ দেখানো হচ্ছে"
    elif cmd == "আগামী_সপ্তাহের_ঘটনা_দেখাও":
        return "আগামী সপ্তাহের ঘটনা দেখানো হচ্ছে"
    elif cmd == "মাসিক_ঘটনা_দেখাও":
        return "মাসিক ঘটনা দেখানো হচ্ছে"
    elif cmd == "ঘটনার_বিবরণ_দেখাও":
        return "ঘটনার বিবরণ দেখানো হচ্ছে"
    elif cmd == "ঘটনার_স্থান_দেখাও":
        return "ঘটনার স্থান দেখানো হচ্ছে"
    elif cmd == "ঘটনা_সীমা_নির্ধারণ_করো":
        return "ঘটনার সীমা নির্ধারণ করা হচ্ছে"
    elif cmd == "ঘটনা_সক্রিয়_করো":
        return "ঘটনা সক্রিয় করা হচ্ছে"
    elif cmd == "ঘটনা_নিষ্ক্রিয়_করো":
        return "ঘটনা নিষ্ক্রিয় করা হচ্ছে"
    elif cmd == "বার্ষিকী_যোগ_করো":
        return "বার্ষিকী যোগ করা হচ্ছে"
    elif cmd == "মিটিং_শিডিউল_করো":
        return "মিটিং শিডিউল করা হচ্ছে"
    elif cmd == "ঘটনা_আলোচনা_করো":
        return "ঘটনা আলোচনা করা হচ্ছে"
    elif cmd == "ঘটনা_অনুমোদন_করো":
        return "ঘটনা অনুমোদন করা হচ্ছে"
    elif cmd == "ঘটনা_বাতিল_করো":
        return "ঘটনা বাতিল করা হচ্ছে"
    elif cmd == "ঘটনা_রিমাইন্ডার_সেট_করো":
        return "ঘটনা রিমাইন্ডার সেট করা হচ্ছে"
    elif cmd == "ঘটনা_স্মার্ট_সেট_করো":
        return "ঘটনা স্মার্ট সেট করা হচ্ছে"
    elif cmd == "ঘটনা_লগ_দেখাও":
        return "ঘটনা লগ দেখানো হচ্ছে"
    elif cmd == "সাপ্তাহিক_ঘটনা_সংক্ষিপ্ত_দেখাও":
        return "সাপ্তাহিক ঘটনা সংক্ষিপ্ত দেখানো হচ্ছে"
    elif cmd == "মাসিক_শিডিউল_দেখাও":
        return "মাসিক শিডিউল দেখানো হচ্ছে"
    elif cmd == "ক্যালেন্ডার_এক্সপোর্ট_করো":
        return "ক্যালেন্ডার এক্সপোর্ট করা হচ্ছে"
    elif cmd == "ক্যালেন্ডার_ইমপোর্ট_করো":
        return "ক্যালেন্ডার ইমপোর্ট করা হচ্ছে"
    elif cmd == "ক্যালেন্ডার_সেটিংস_পরিবর্তন_করো":
        return "ক্যালেন্ডার সেটিংস পরিবর্তন করা হচ্ছে"
    elif cmd == "ক্যালেন্ডার_সিঙ্ক_বন্ধ_করো":
        return "ক্যালেন্ডার সিঙ্ক বন্ধ করা হচ্ছে"
    elif cmd == "মিটিং_শুরু_করো":
        return "মিটিং শুরু করা হচ্ছে"
    elif cmd == "মিটিং_শেষ_করো":
        return "মিটিং শেষ করা হচ্ছে"
    elif cmd == "ঘটনা_সংখ্যা_গণনা_করো":
        return "ঘটনার সংখ্যা গণনা করা হচ্ছে"
    elif cmd == "ঘটনা_সারাংশ_দেখাও":
        return "ঘটনার সারাংশ দেখানো হচ্ছে"
    elif cmd == "ঘটনা_ফিল্টার_করো":
        return "ঘটনা ফিল্টার করা হচ্ছে"
    elif cmd == "ঘটনা_বিষয়_সেট_করো":
        return "ঘটনার বিষয় সেট করা হচ্ছে"
    elif cmd == "ঘটনা_কারণ_সেট_করো":
        return "ঘটনার কারণ সেট করা হচ্ছে"
    elif cmd == "ঘটনা_গুরুত্ব_সেট_করো":
        return "ঘটনার গুরুত্ব সেট করা হচ্ছে"
    elif cmd == "ঘটনা_অবস্থান_সেট_করো":
        return "ঘটনার অবস্থান সেট করা হচ্ছে"
    elif cmd == "ঘটনা_ব্যবহারকারী_অ্যাসাইন_করো":
        return "ঘটনা ব্যবহারকারী অ্যাসাইন করা হচ্ছে"
    elif cmd == "ক্যালেন্ডার_রিসেট_করো":
        return "ক্যালেন্ডার রিসেট করা হচ্ছে"
    elif cmd == "ঘটনা_মেমো_যোগ_করো":
        return "ঘটনা মেমো যোগ করা হচ্ছে"

    # 🔘 স্বাস্থ্য/ফিটনেস (৫০টি বাংলা কমান্ড)
    elif cmd == "হৃদস্পন্দন_পরীক্ষা_করো":
        return "হৃদস্পন্দন পরীক্ষা করা হচ্ছে"
    elif cmd == "রক্তচাপ_মাপো":
        return "রক্তচাপ পরিমাপ করা হচ্ছে"
    elif cmd == "শ্বাস_নিও":
        return "শ্বাস নেওয়া হচ্ছে"
    elif cmd == "ক্যালোরি_গণনা_করো":
        return "ক্যালোরি গণনা করা হচ্ছে"
    elif cmd == "ওজন_পরিমাপ_করো":
        return "ওজন পরিমাপ করা হচ্ছে"
    elif cmd == "জিম_শুরু_করো":
        return "জিম শুরু করা হচ্ছে"
    elif cmd == "ব্যায়াম_শুরু_করো":
        return "ব্যায়াম শুরু করা হচ্ছে"
    elif cmd == "ব্যায়াম_থামাও":
        return "ব্যায়াম থামানো হয়েছে"
    elif cmd == "দৈনিক_ধাপ_গণনা_করো":
        return "দৈনিক ধাপ গণনা করা হচ্ছে"
    elif cmd == "ওজন_লক্ষ্য_সেট_করো":
        return "ওজন লক্ষ্য নির্ধারণ করা হচ্ছে"
    elif cmd == "পানি_পানের_স্মরণ_করাও":
        return "পানি পান করার স্মরণ করানো হচ্ছে"
    elif cmd == "ঘুম_ট্র্যাক_করো":
        return "ঘুম ট্র্যাকিং চালু করা হচ্ছে"
    elif cmd == "ক্যালোরি_ব্যবহার_দেখাও":
        return "ক্যালোরি ব্যবহার দেখানো হচ্ছে"
    elif cmd == "সুপারফুড_রেকমেন্ড_করো":
        return "সুপারফুড রেকমেন্ড করা হচ্ছে"
    elif cmd == "দৈনিক_কার্ডিও_পরিকল্পনা_দাও":
        return "দৈনিক কার্ডিও পরিকল্পনা দেওয়া হচ্ছে"
    elif cmd == "স্ট্রেস_পরীক্ষা_করো":
        return "স্ট্রেস পরীক্ষা করা হচ্ছে"
    elif cmd == "স্বাস্থ্য_পরামর্শ_দাও":
        return "স্বাস্থ্য পরামর্শ দেওয়া হচ্ছে"
    elif cmd == "হাঁটা_শুরু_করো":
        return "হাঁটা শুরু করা হচ্ছে"
    elif cmd == "যোগব্যায়াম_শুরু_করো":
        return "যোগব্যায়াম শুরু করা হচ্ছে"
    elif cmd == "ডায়েট_পরিকল্পনা_তৈরি_করো":
        return "ডায়েট পরিকল্পনা তৈরি করা হচ্ছে"
    elif cmd == "ফিটনেস_লক্ষ্য_সেট_করো":
        return "ফিটনেস লক্ষ্য নির্ধারণ করা হচ্ছে"
    elif cmd == "মেডিটেশন_শুরু_করো":
        return "মেডিটেশন শুরু করা হচ্ছে"
    elif cmd == "ফিটনেস_ট্র্যাক_দেখাও":
        return "ফিটনেস ট্র্যাক দেখানো হচ্ছে"
    elif cmd == "ব্যায়ামের_সময়_নির্ধারণ_করো":
        return "ব্যায়ামের সময় নির্ধারণ করা হচ্ছে"
    elif cmd == "হৃদরোগ_সতর্কতা_দাও":
        return "হৃদরোগ সতর্কতা দেওয়া হচ্ছে"
    elif cmd == "ওজন_হ্রাস_পরামর্শ_দাও":
        return "ওজন হ্রাস পরামর্শ দেওয়া হচ্ছে"
    elif cmd == "দৈনিক_ক্যালোরি_লক্ষ্য_সেট_করো":
        return "দৈনিক ক্যালোরি লক্ষ্য নির্ধারণ করা হচ্ছে"
    elif cmd == "পেশী_বর্ধন_পরিকল্পনা_তৈরি_করো":
        return "পেশী বৃদ্ধি পরিকল্পনা তৈরি করা হচ্ছে"
    elif cmd == "জল_পানের_পরিমাণ_নির্ধারণ_করো":
        return "জল পান পরিমাণ নির্ধারণ করা হচ্ছে"
    elif cmd == "ডায়েট_ট্র্যাক_করো":
        return "ডায়েট ট্র্যাকিং চালু করা হচ্ছে"
    elif cmd == "স্বাস্থ্য_রিপোর্ট_তৈরি_করো":
        return "স্বাস্থ্য রিপোর্ট তৈরি করা হচ্ছে"
    elif cmd == "পদক্ষেপ_গণনা_দেখাও":
        return "পদক্ষেপ গণনা দেখানো হচ্ছে"
    elif cmd == "হাঁটা_থামাও":
        return "হাঁটা থামানো হয়েছে"
    elif cmd == "কঠিন_ব্যায়াম_শুরু_করো":
        return "কঠিন ব্যায়াম শুরু করা হচ্ছে"
    elif cmd == "শ্বাস_নিয়ন্ত্রণ_করো":
        return "শ্বাস নিয়ন্ত্রণ করা হচ্ছে"
    elif cmd == "অবসাদ_পরীক্ষা_করো":
        return "অবসাদ পরীক্ষা করা হচ্ছে"
    elif cmd == "সুস্থতা_বিষয়ক_পরামর্শ_দাও":
        return "সুস্থতা বিষয়ক পরামর্শ দেওয়া হচ্ছে"
    elif cmd == "দৈনিক_যোগব্যায়াম_পরিকল্পনা_তৈরি_করো":
        return "দৈনিক যোগব্যায়াম পরিকল্পনা তৈরি করা হচ্ছে"
    elif cmd == "হৃদস্পন্দন_রেকর্ড_করো":
        return "হৃদস্পন্দন রেকর্ড করা হচ্ছে"
    elif cmd == "ফিটনেস_অ্যাপ_চালু_করো":
        return "ফিটনেস অ্যাপ চালু করা হচ্ছে"
    elif cmd == "পুষ্টি_তালিকা_দেখাও":
        return "পুষ্টি তালিকা দেখানো হচ্ছে"
    elif cmd == "হাঁটার_গতি_পরিমাপ_করো":
        return "হাঁটার গতি পরিমাপ করা হচ্ছে"
    elif cmd == "দৈনিক_ক্যালোরি_খরচ_দেখাও":
        return "দৈনিক ক্যালোরি খরচ দেখানো হচ্ছে"
    elif cmd == "ওজন_নিয়ন্ত্রণ_পরামর্শ_দাও":
        return "ওজন নিয়ন্ত্রণ পরামর্শ দেওয়া হচ্ছে"
    elif cmd == "ব্যায়াম_সময়সূচী_তৈরি_করো":
        return "ব্যায়াম সময়সূচী তৈরি করা হচ্ছে"
    elif cmd == "ফিটনেস_পরীক্ষা_শুরু_করো":
        return "ফিটনেস পরীক্ষা শুরু করা হচ্ছে"
    elif cmd == "শরীরের_চর্বি_পরিমাপ_করো":
        return "শরীরের চর্বি পরিমাপ করা হচ্ছে"
    # 🔘 দিন (৫০টি বাংলা কমান্ড)
    elif cmd == "আজকের_দিন_কি":
        return "আজকের দিন জানানো হচ্ছে"
    elif cmd == "কালকের_দিন_কি":
        return "কালকের দিন জানানো হচ্ছে"
    elif cmd == "গতকাল_কি_ছিল":
        return "গতকালের দিন জানানো হচ্ছে"
    elif cmd == "আগামী_দিন_কি":
        return "আগামী দিনের তথ্য দেওয়া হচ্ছে"
    elif cmd == "সপ্তাহের_দিন_কি":
        return "সপ্তাহের দিন জানানো হচ্ছে"
    elif cmd == "সপ্তাহের_কোন_দিন":
        return "সপ্তাহের কোন দিন তা জানানো হচ্ছে"
    elif cmd == "দিনের_তারিখ_কি":
        return "দিনের তারিখ জানানো হচ্ছে"
    elif cmd == "আজকের_তারিখ_কি":
        return "আজকের তারিখ জানানো হচ্ছে"
    elif cmd == "আজ_কি_দিন":
        return "আজ কি দিন তা জানানো হচ্ছে"
    elif cmd == "কাল_কি_দিন":
        return "কাল কি দিন তা জানানো হচ্ছে"
    elif cmd == "সপ্তাহের_প্রথম_দিন":
        return "সপ্তাহের প্রথম দিন জানানো হচ্ছে"
    elif cmd == "সপ্তাহের_শেষ_দিন":
        return "সপ্তাহের শেষ দিন জানানো হচ্ছে"
    elif cmd == "বছরের_দিন_কি":
        return "বছরের দিন জানানো হচ্ছে"
    elif cmd == "আজ_কত_তারিখ":
        return "আজকের তারিখ জানানো হচ্ছে"
    elif cmd == "গত_সপ্তাহ_কি_ছিল":
        return "গত সপ্তাহের তথ্য জানানো হচ্ছে"
    elif cmd == "আগামী_সপ্তাহ_কি_আছে":
        return "আগামী সপ্তাহের তথ্য দেওয়া হচ্ছে"
    elif cmd == "দিনের_নাম_কি":
        return "দিনের নাম জানানো হচ্ছে"
    elif cmd == "দিনের_অবস্থা_কি":
        return "দিনের অবস্থা জানানো হচ্ছে"
    elif cmd == "আজকের_দিনের_পরিকল্পনা":
        return "আজকের দিনের পরিকল্পনা দেখানো হচ্ছে"
    elif cmd == "আজকের_দিনের_ঘটনা":
        return "আজকের দিনের ঘটনা দেখানো হচ্ছে"
    elif cmd == "কালকের_দিনের_পরিকল্পনা":
        return "কালকের দিনের পরিকল্পনা দেখানো হচ্ছে"
    elif cmd == "গতকালকের_দিনের_ঘটনা":
        return "গতকালকের দিনের ঘটনা দেখানো হচ্ছে"
    elif cmd == "দিনের_লিখিত_রিপোর্ট":
        return "দিনের লিখিত রিপোর্ট দেখানো হচ্ছে"
    elif cmd == "দিনের_সারাংশ_দেখাও":
        return "দিনের সারাংশ দেখানো হচ্ছে"
    elif cmd == "দিনের_সংক্ষিপ্ত_সারাংশ":
        return "দিনের সংক্ষিপ্ত সারাংশ দেওয়া হচ্ছে"
    elif cmd == "দিনের_কাজ_তালিকা":
        return "দিনের কাজের তালিকা দেখানো হচ্ছে"
    elif cmd == "দিনের_শিডিউল_দেখাও":
        return "দিনের শিডিউল দেখানো হচ্ছে"
    elif cmd == "দিনের_স্মরণ_করাও":
        return "দিনের স্মরণ করানো হচ্ছে"
    elif cmd == "দিনের_ঘটনা_লিখো":
        return "দিনের ঘটনা লেখা হচ্ছে"
    elif cmd == "দিনের_স্মৃতি_সংরক্ষণ":
        return "দিনের স্মৃতি সংরক্ষণ করা হচ্ছে"
    elif cmd == "দিনের_ব্যবহার_পরীক্ষা":
        return "দিনের ব্যবহার পরীক্ষা করা হচ্ছে"
    elif cmd == "দিনের_পরিসংখ্যান":
        return "দিনের পরিসংখ্যান দেখানো হচ্ছে"
    elif cmd == "দিনের_বাজেট_দেখাও":
        return "দিনের বাজেট দেখানো হচ্ছে"
    elif cmd == "দিনের_বাজেট_সেট_করো":
        return "দিনের বাজেট সেট করা হচ্ছে"
    elif cmd == "দিনের_অগ্রগতি_দেখাও":
        return "দিনের অগ্রগতি দেখানো হচ্ছে"
    elif cmd == "দিনের_নোট_যোগ_করো":
        return "দিনের নোট যোগ করা হচ্ছে"
    elif cmd == "দিনের_নোট_দেখাও":
        return "দিনের নোট দেখানো হচ্ছে"
    elif cmd == "দিনের_টাস্ক_শুরুকরো":
        return "দিনের টাস্ক শুরু করা হচ্ছে"
    elif cmd == "দিনের_টাস্ক_শেষ_করো":
        return "দিনের টাস্ক শেষ করা হচ্ছে"
    elif cmd == "দিনের_টাইমলাইন_দেখাও":
        return "দিনের টাইমলাইন দেখানো হচ্ছে"
    elif cmd == "দিনের_রিপোর্ট_তৈরি_করো":
        return "দিনের রিপোর্ট তৈরি করা হচ্ছে"
    elif cmd == "দিনের_আলোচনা_শুরু_করো":
        return "দিনের আলোচনা শুরু করা হচ্ছে"
    elif cmd == "দিনের_আলোচনা_শেষ_করো":
        return "দিনের আলোচনা শেষ করা হচ্ছে"
    elif cmd == "দিনের_স্মৃতি_পুনরুদ্ধার_করো":
        return "দিনের স্মৃতি পুনরুদ্ধার করা হচ্ছে"
    elif cmd == "দিনের_স্মৃতি_মুছে_ফেলো":
        return "দিনের স্মৃতি মুছে ফেলা হচ্ছে"

        # 🔘 Fallback
    else:
        return f"Unknown command: {cmd}", 400

    # 46. Memory Recall by Question
@app.route('/api/memory_answer', methods=['POST'])
def memory_answer():
    query = request.json.get("query")
    answer = search_memory_by_question(query)
    return jsonify({"answer": answer})
# 47. Google Drive Memory Backup
@app.route('/api/drive_backup', methods=['POST'])
def drive_backup():
    filepath = "memory.db"  # অথবা memory_backup.json
    file_id = upload_to_drive(filepath)
    return jsonify({"uploaded": True, "file_id": file_id})
# 48. Firebase Memory Sync
@app.route('/api/sync_firebase', methods=['GET'])
def sync_firebase():
    sync_memory_to_firebase()
    return jsonify({"status": "Synced to Firebase"})
#49....
@app.route('/latest_emotion')
def latest_emotion():
    return jsonify({"emotion": current_emotion})

# ---------- 50. storage_info ----------
@app.route('/api/storage_info', methods=['GET'])
def get_storage_info():
    sizes = {
        "uploads": get_folder_size(UPLOAD_FOLDER),
        "audio": get_folder_size(AUDIO_FOLDER),
        "memory_images": get_folder_size(MEMORY_IMG_FOLDER),
        "firmware": get_folder_size(FIRMWARE_FOLDER)
    }
    return jsonify({k: f"{v / 1024 / 1024:.2f} MB" for k, v in sizes.items()})
 
# 51 UPLOAD_IMAGE
@app.route('/', methods=['POST'])
def receive_image():
    command = request.data[:12]
    image_data = request.data[12:]

    if command == b'UPLOAD_IMAGE':
        filename = "capture_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        with open("received_images/" + filename, "wb") as f:
            f.write(image_data)
        print(f"✅ Image saved as {filename}")
        return "Image received", 200
    else:
        print("❌ Unknown command")
        return "Unknown", 400
#...52
@app.route('/process_text', methods=['POST'])
def process_text():
    data = request.get_json()
    user_text = data.get("text", "")
    
    # ১. বাংলা থেকে ইংরেজি অনুবাদ
    eng_text = translate_text(user_text, dest_language='en')
    
    # ২. (AI লজিক বা প্রসেস) এখানে যেকোনো লজিক লাগান, উদাহরণ:
    response_eng = "This is a response to: " + eng_text
    
    # ৩. ইংরেজি থেকে আবার বাংলা অনুবাদ
    response_bn = translate_to_bengali(response_eng)
    
    # ৪. TTS এর জন্য mp3 ফাইল তৈরি করুন (Coqui TTS / gTTS / অন্য API)
    # এখানে সরাসরি response_bn পাঠাতে পারেন TTS API তে
    
    return jsonify({"response_text": response_bn})
#..53..
@app.route('/add_memory', methods=['POST'])
def add_memory():
    data = request.get_json()
    text = data.get('text')
    private = data.get('private', 0)  # 0 = public, 1 = private

    if not text:
        return jsonify({"error": "No text provided"}), 400

    timestamp = datetime.datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO memories (timestamp, text, private) VALUES (?, ?, ?)', (timestamp, text, private))
    conn.commit()
    conn.close()

    return jsonify({"status": "Memory added", "timestamp": timestamp})
#...54...
@app.route('/search_memory', methods=['GET'])
def search_memory():
    query = request.args.get('q', '')
    show_private = request.args.get('private', '0')  # যদি private দেখাতে চান

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if show_private == '1':
        cursor.execute('SELECT timestamp, text FROM memories WHERE text LIKE ?', ('%'+query+'%',))
    else:
        cursor.execute('SELECT timestamp, text FROM memories WHERE text LIKE ? AND private=0', ('%'+query+'%',))

    results = cursor.fetchall()
    conn.close()

    memories_list = [{"timestamp": t, "text": txt} for t, txt in results]
    return jsonify({"results": memories_list}) 
    app.route('/api/facelogs')
def api_face_logs():
    return jsonify(face_logs)

@app.route('/api/memorytimeline')
def api_memory_timeline():
    return jsonify(memory_timeline)

@app.route('/api/wifiprofiles', methods=['GET', 'POST'])
def api_wifi_profiles():
    if request.method == 'GET':
        return jsonify(wifi_profiles)
    else:
        data = request.json
        ssid = data.get('ssid')
        password = data.get('password')
        # এখানে নতুন wifi সংরক্ষণ বা কানেক্ট করার লজিক যোগ করুন
        wifi_profiles.append({"ssid": ssid, "status": "Saved"})
        return jsonify({"message": "WiFi profile added", "ssid": ssid})
@app.route('/recognize', methods=['POST'])
def recognize_face():
    data = request.json
    img_b64 = data.get('image')
    if not img_b64:
        return jsonify({"error": "No image provided"}), 400

    # base64 ডিকোড এবং image file তৈরি
    img_data = base64.b64decode(img_b64.split(",")[1])  # "data:image/jpeg;base64,..." ফর্ম্যাটে আসলে
    with open("temp.jpg", "wb") as f:
        f.write(img_data)

    unknown_image = face_recognition.load_image_file("temp.jpg")
    unknown_encodings = face_recognition.face_encodings(unknown_image)

    if not unknown_encodings:
        return jsonify({"result": "no_face_detected"})

    unknown_encoding = unknown_encodings[0]

    # মিল যাচাই
    matches = face_recognition.compare_faces(known_face_encodings, unknown_encoding, tolerance=0.5)
    face_distances = face_recognition.face_distance(known_face_encodings, unknown_encoding)
    best_match_index = np.argmin(face_distances) if face_distances.size > 0 else None

    if best_match_index is not None and matches[best_match_index]:
        name = known_face_names[best_match_index]
        # পরিচিত মুখ, ESP32 কে "Hi, name" পাঠাবে
        return jsonify({"result": "known", "name": name, "message": f"Hi, {name}!"})
    else:
        # নতুন মুখ, ESP32 কে /add_face trigger করার নির্দেশ
        return jsonify({"result": "unknown", "message": "Unknown face. Please add."})

@app.route('/add_face', methods=['POST'])
def add_face():
    data = request.json
    img_b64 = data.get('image')
    name = data.get('name')
    if not img_b64 or not name:
        return jsonify({"error": "Image and name required"}), 400

    img_data = base64.b64decode(img_b64.split(",")[1])
    path = os.path.join(KNOWN_FACES_DIR, f"{name}.jpg")
    with open(path, "wb") as f:
        f.write(img_data)

    load_known_faces()  # নতুন মুখ লোড করুন

    return jsonify({"message": f"Face {name} added successfully."}) 
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    pin = data.get('pin')
    if pin == PRIVATE_PIN:
        session['authenticated'] = True
        return jsonify({"message": "Login successful"})
    else:
        return jsonify({"message": "Invalid PIN"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return jsonify({"message": "Logged out"})

def pin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({"error": "Authentication required"}), 403
        return f(*args, **kwargs)
    return decorated

# প্রাইভেট মেমোরি API - PIN অথেনটিকেশন প্রয়োজন
@app.route('/private_memory', methods=['GET'])
@pin_required
def private_memory():
    # প্রাইভেট মেমোরি ডেটা রিটার্ন করুন
    memories = [
        {"timestamp": "2025-06-27 10:00", "text": "Private memory example"}
    ]
    return jsonify(memories)
@app.route('/search', methods=['GET'])
def search_memory():
    q = request.args.get('q', '').lower()
    if not q:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    memories = query_memories()
    
    # Simple matching using difflib to find closest memory
    best_match = None
    best_ratio = 0.0
    for memory in memories:
        ratio = difflib.SequenceMatcher(None, q, memory.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = memory
    
    if best_match:
        return jsonify({"answer": best_match})
    else:
        return jsonify({"answer": "Sorry, I have no relevant memory."})
@app.route('/backup', methods=['GET'])
def manual_backup():
    try:
        backup_to_drive()
        return "✅ Backup complete", 200
    except Exception as e:
        return f"❌ Backup failed: {e}", 500
# Violation check API
@app.route('/check_violation', methods=['POST'])
def check_violation():
    data = request.json
    event_text = data.get("text", "")

    cur = conn.cursor()
    cur.execute("SELECT text FROM memory WHERE type='rule'")
    rules = [row[0] for row in cur.fetchall()]

    for rule in rules:
        if rule in event_text:
            return jsonify({"violation": True, "rule": rule})

    return jsonify({"violation": False})
# --- Add any additional feature routes similarly here ---

# Run Server
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
