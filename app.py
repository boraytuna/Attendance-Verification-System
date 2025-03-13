from flask import Flask, session, render_template, request, redirect, jsonify, send_file
from flask_mail import Mail, Message
import sqlite3
import os
import segno
import requests
import random

app = Flask(__name__)

DATABASE_NAME = "attendance.db"
QR_CODE_FOLDER = "qr_codes"

#session key
app.secret_key = os.urandom(24)

#mail server configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'jrosestangle@gmail.com'
app.config['MAIL_PASSWORD'] = 'pfdbqlrqisxzubmf' #app pw
app.config['MAIL_DEFAULT_SENDER'] = 'jrosestangle@gmail.com'
mail = Mail(app)

if not os.path.exists(QR_CODE_FOLDER):
    os.makedirs(QR_CODE_FOLDER)

GOOGLE_API_KEY = "AIzaSyAzf_3rNo5yi24L3Mu35o5VHaw1PwVmeTs"  # Replace with your actual Google API key

# Function to connect to SQLite
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Enables dictionary-style access
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
    return conn

# Function to create tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Events Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            eventID INTEGER PRIMARY KEY AUTOINCREMENT,
            eventName TEXT NOT NULL,
            eventDate DATE NOT NULL,
            startTime TIME NOT NULL,
            stopTime TIME NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            eventAddress TEXT NOT NULL
        )
    ''')

    # Create Student Check-Ins Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_checkins (
            checkinID INTEGER PRIMARY KEY AUTOINCREMENT,
            studentID TEXT NOT NULL,
            firstName TEXT NOT NULL,
            lastName TEXT NOT NULL,
            email TEXT NOT NULL,
            classForExtraCredit TEXT NOT NULL,
            professorForExtraCredit TEXT NOT NULL,
            scannedEventID INTEGER NOT NULL,
            studentLocation TEXT NOT NULL,
            checkinTime DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scannedEventID) REFERENCES events(eventID)
        )
    ''')

    # Create Attendance Status Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_status (
            statusID INTEGER PRIMARY KEY AUTOINCREMENT,
            checkinID INTEGER NOT NULL,
            attendanceStatus TEXT NOT NULL CHECK (attendanceStatus IN ('Attended', 'Left Early')),
            FOREIGN KEY (checkinID) REFERENCES student_checkins(checkinID)
        )
    ''')

    conn.commit()
    conn.close()

# Ensure database tables exist
create_tables()

# Route: Dashboard
@app.route("/")
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# Route: Events Page
@app.route("/events", methods=["GET"])
def events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    conn.close()
    return render_template("events.html", events=events)

# Route: Calendar Page
@app.route("/calendar")
def calendar():
    return render_template("calendar.html")

# Route: Find Student Page
@app.route("/find_student")
def find_student():
    return render_template("find_student.html")

# Route: Places Page
@app.route("/places")
def places():
    return render_template("places.html")

# Function to generate (or retrieve) QR code
def get_or_create_qr_code(event_id):
    qr_code_path = os.path.join(QR_CODE_FOLDER, f"event_{event_id}.png")

    if os.path.exists(qr_code_path):
        return qr_code_path  # Return existing QR code

    # Generate new QR code that directs to the student interface
    #qr_url = f"http://127.0.0.1:5000/student_interface/{event_id}"
    qr_url = f"http://192.168.1.100:5000/student_checkin/{event_id}" #temp - Joie was using this IP to test on her local network (address for home network)
    #qr_url = f"http://172.20.10.12:5000/student_checkin/{event_id}" #temp - Joie was using this IP to test on her local network (address for phone hotspot)
    qr = segno.make(qr_url)
    qr.save(qr_code_path, scale=10)

    return qr_code_path

# Route: Serve QR Code
@app.route("/qr_code/<int:event_id>")
def serve_qr_code(event_id):
    qr_code_path = get_or_create_qr_code(event_id)
    return send_file(qr_code_path, mimetype="image/png")

# **Route: Student Interface**
@app.route("/student_checkin/<int:event_id>")
#@app.route("/student_checkin/<int:event_id>/<int:page>")
def student_interface(event_id):
    """Serve the student interface pages for a specific event.
    Pass the eventID and eventName to the HTML template."""
    #get the event name associated with the eventID
    conn = get_db_connection()
    event = get_db_connection().cursor().execute("SELECT eventName FROM events WHERE eventID = ?", (event_id,)).fetchone()
    conn.close()
    event_name = event["eventName"]
    return render_template("student_checkin.html", eventID=event_id, eventName=event_name)

# **API Routes for Student Check-In Email Verification**
@app.route('/verify_email', methods=['POST'])
def send_email():
    data = request.get_json()
    email = data.get('email')

    #generate a random 6 digit code
    code = ''
    for i in range(6):
        num = random.randint(0, 9)
        code += str(num)

    #store the code in the session
    session['verification_code'] = code 

    body_msg = 'Your email verification code for student check-in is: ' + code
    msg = Message (
        'Student Check-In Code',
        recipients=[email],
        body=body_msg
    )

    try:
        mail.send(msg)
        return 'Sent', 200
    except Exception as e:
        return str(e), 500

@app.route('/verify_code', methods=['POST'])
def verify_code():
    data = request.get_json()
    code = data.get('code')

    if 'verification_code' not in session:
        return jsonify({'error': 'Session expired'}), 400
    
    if code == session['verification_code']:
        return jsonify({'message': 'Code verified'}), 200
    else:
        return jsonify({'error': 'Invalid code'}), 400

# **API Routes for Course & Professor Search**
@app.route('/search_courses', methods=['GET'])
def search_courses():
    """Search for courses based on user input."""
    #TEMPORARY - connect to fake DB
    conn = sqlite3.connect("fake.db")
    conn.row_factory = sqlite3.Row  # Enables dictionary-style access
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints

    search_term = request.args.get('query', '')
    #conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT course_name FROM Courses WHERE course_name LIKE ?", (f"%{search_term}%",))
    results = cursor.fetchall()
    conn.close()
    return jsonify([row[0] for row in results])

@app.route('/search_professors', methods=['GET'])
def search_professors():
    """Search for professors based on user input."""
    #TEMPORARY - connect to fake DB
    conn = sqlite3.connect("fake.db")
    conn.row_factory = sqlite3.Row  # Enables dictionary-style access
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints

    search_term = request.args.get('query', '')
    #conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT professor_name FROM Professor WHERE professor_name LIKE ?", (f"%{search_term}%",))
    results = cursor.fetchall()
    conn.close()
    return jsonify([row[0] for row in results])

# **API Route for Submitting Student Check-In Form**
@app.route('/submit_student_checkin', methods=['POST'])
def submit_student_checkin():
    data = request.json
    studentID = data['studentID']
    firstName = data['firstName']
    lastName = data['lastName']
    email = data['email']
    classForExtraCredit = data['classForExtraCredit']
    professorForExtraCredit = data['professorForExtraCredit']
    scannedEventID = data['scannedEventID']
    studentLocation = data['studentLocation']

    conn = get_db_connection()
    conn.cursor().execute('''
        INSERT INTO student_checkins (studentID, firstName, lastName, email, classForExtraCredit, professorForExtraCredit, scannedEventID, studentLocation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (studentID, firstName, lastName, email, classForExtraCredit, professorForExtraCredit, scannedEventID, studentLocation))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# Route: Handle Event Creation
@app.route("/submit_event", methods=["POST"])
def submit_event():
    event_name = request.form["event_name"]
    event_date = request.form["event_date"]
    start_time = request.form["start_time"]
    stop_time = request.form["stop_time"]
    event_location = request.form["event_location"]  # Lat,Lng format

    if not event_location:
        return jsonify({"message": "Please select a location"}), 400

    try:
        lat, lng = map(float, event_location.split(","))
    except ValueError:
        return jsonify({"message": "Invalid location format"}), 400

    # Reverse Geocode using Google Maps API
    address = "Unknown Location"
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_API_KEY}"
    response = requests.get(geocode_url).json()

    if response["status"] == "OK" and len(response["results"]) > 0:
        address = response["results"][0]["formatted_address"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (eventName, eventDate, startTime, stopTime, latitude, longitude, eventAddress)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (event_name, event_date, start_time, stop_time, lat, lng, address))

    event_id = cursor.lastrowid  # Get the newly created event ID
    conn.commit()
    conn.close()

    # Generate QR Code for this event
    get_or_create_qr_code(event_id)

    return redirect("/events")

# Route: API endpoint for event list (returns JSON)
@app.route("/api/events", methods=["GET"])
def get_events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT eventID, eventName, eventDate, startTime, stopTime, latitude, longitude, eventAddress FROM events")
    events = cursor.fetchall()
    conn.close()

    events_list = [dict(event) for event in events]
    return jsonify(events_list)

if __name__ == "__main__":
    app.run(debug=True)