from flask import Flask, session, render_template, request, redirect, jsonify, send_file
from flask_mail import Mail, Message
import sqlite3
import os
import segno
import requests
import random
from datetime import datetime
import schedule
import time
from threading import Thread

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

# TEMPORARY - function to connect to fake DB
def get_fakedb_connection():
    conn = sqlite3.connect("fake.db")
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

    # Create Places Table
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS places (
                placeID INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                building TEXT NOT NULL,
                address TEXT NULL
            )
        ''')

    conn.commit()
    conn.close()

# Ensure database tables exist
create_tables()
@app.route("/")
@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Upcoming events: event start is in the future
    cursor.execute("""
        SELECT * FROM events 
        WHERE eventDate || 'T' || startTime >= ?
        ORDER BY eventDate, startTime
    """, (now,))
    upcoming = cursor.fetchall()

    # Past events: event has already ended
    cursor.execute("""
        SELECT * FROM events 
        WHERE eventDate || 'T' || stopTime < ?
        ORDER BY eventDate DESC, startTime DESC
    """, (now,))
    past = cursor.fetchall()

    conn.close()
    return render_template("dashboard.html", upcoming_events=upcoming, past_events=past)

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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places")
    places = cursor.fetchall()
    conn.close()
    return render_template("places.html", places=places)


# Function to generate (or retrieve) QR code
def get_or_create_qr_code(event_id):
    qr_code_path = os.path.join(QR_CODE_FOLDER, f"event_{event_id}.png")

    if os.path.exists(qr_code_path):
        return qr_code_path  # Return existing QR code

    # Generate new QR code that directs to the student interface
    qr_url = f"http://127.0.0.1:5000/student_checkin/{event_id}" #temp - Boray was using on his laptop
    #qr_url = f"http://192.168.1.100:5000/student_checkin/{event_id}" #temp - Joie was using this IP to test on her local network (address for home network)
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
    firstName = data['firstName']
    lastName = data['lastName']
    email = data['email']
    classForExtraCredit = data['classForExtraCredit']
    professorForExtraCredit = data['professorForExtraCredit']
    scannedEventID = int(data['scannedEventID'])
    studentLocation = str(data['studentLocation'])

    conn = get_db_connection()
    conn.cursor().execute('''
        INSERT INTO student_checkins (firstName, lastName, email, classForExtraCredit, professorForExtraCredit, scannedEventID, studentLocation)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (firstName, lastName, email, classForExtraCredit, professorForExtraCredit, scannedEventID, studentLocation))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

# **Functions for Generating and Sending Emails to Professors Post-Event**
def construct_email_records():
    """
    Collect a list of professors and their students' attendance records
    to be used to generate emails.

    Returns:
    emails - dictionary with professor names as keys and a list of student
    details as values
    """
    conn = get_db_connection()

    #get student information and their attendance status records
    results = conn.cursor().execute('''
        SELECT sc.firstName, sc.lastName, sc.classForExtraCredit, sc.professorForExtraCredit, atd.attendanceStatus
        FROM student_checkins sc
        JOIN attendance_status atd ON sc.checkinID = atd.checkinID
    ''').fetchall()

    #get unique professor names to use as keys in the dictionary
    professors = conn.cursor().execute('''
        SELECT DISTINCT sc.professorForExtraCredit
        FROM student_checkins sc
        JOIN attendance_status atd ON sc.checkinID = atd.checkinID
    ''').fetchall()
    conn.close()

    #create a dictionary with professor names as keys
    #and a list of student details as values
    emails = {}
    for professor in professors:
        records = []
        professor_name = professor[0]
        emails[professor_name] = records

        for result in results:
            if result[3] == professor_name:
                records.append(f'{result[0]} {result[1]} - {result[2]} - {result[4]}')

    return emails

def send_professor_emails():
    """
    Send emails to professors with a summary of student attendance records.
    """
    emails = construct_email_records()
    professors = (emails.keys())

    conn_fakedb = get_fakedb_connection()
    for professor in professors:
        #get the professors' email from fake db
        professor_email = conn_fakedb.cursor().execute('''
            SELECT professor_email FROM Professor WHERE professor_name = ?
        ''', (professor,)).fetchone()

        #format student attendance records as an html body, use plaintext as
        #backup if html within email is unsupported
        plaintext_msg = 'Hello ' + professor + '! The following students recently attended an event for course credit:\n' + '\n'.join(emails[professor])
        html_msg = f'''
        <html>
            <body>
                <p>Hello {professor},</p>
                <p>The following students recently attended an event for course credit:</p>
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <th style="padding: 8px; text-align: left; border: 1px solid black;">Name</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid black;">Class</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid black;">Attendance Status</th>
                    </tr>
                    {''.join(f"<tr><td style='padding: 8px; border: 1px solid black;'>{result.split(' - ')[0]}</td>"
                            f"<td style='padding: 8px; border: 1px solid black;'>{result.split(' - ')[1]}</td>"
                            f"<td style='padding: 8px; border: 1px solid black;'>{result.split(' - ')[2]}</td></tr>"
                            for result in emails[professor])}
                </table>
            </body>
        </html>
        '''
        msg = Message (
            subject='Student Attendance Notification',
            recipients=[professor_email[0]],
            body=plaintext_msg,
            html=html_msg
        )
        mail.send(msg)

    conn_fakedb.close()

#TODO - this occurs immediately upon app startup, need to change
#to a scheduled duration or decide on something else?
with app.app_context():
    pass
    send_professor_emails()

# Route: Handle Event Creation
@app.route("/submit_event", methods=["POST"])
def submit_event():
    event_name = request.form["event_name"]
    event_date = request.form["event_date"]
    start_time = request.form["start_time"]
    stop_time = request.form["stop_time"]
    event_location = request.form["event_location"]
    event_address = request.form.get("event_address", "Unknown Location")
    try:
        lat, lng = map(float, event_location.split(","))
    except ValueError:
        return jsonify({"message": "Invalid location format"}), 400

    # Use the address provided by the frontend
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (eventName, eventDate, startTime, stopTime, latitude, longitude, eventAddress)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (event_name, event_date, start_time, stop_time, lat, lng, event_address))

    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    get_or_create_qr_code(event_id)

    return redirect("/dashboard?success=1")

# Route: API endpoint for event list (returns JSON)
@app.route("/api/events", methods=["GET"])
def get_events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT eventID, eventName, eventDate, startTime, stopTime, latitude, longitude, eventAddress FROM events")
    events = cursor.fetchall()
    conn.close()
    formatted_events = []
    for event in events:
        # Convert to dictionary (assuming events is a list of tuples)
        event_dict = dict(event)

        # Combine date and time for FullCalendar's required format
        start_datetime = f"{event_dict['eventDate']}T{event_dict['startTime']}"
        end_datetime = f"{event_dict['eventDate']}T{event_dict['stopTime']}" if event_dict["stopTime"] else None

        formatted_events.append({
            "id": event_dict["eventID"],
            "title": event_dict["eventName"],
            "start": start_datetime,
            "end": end_datetime,
            "location": event_dict["eventAddress"],
            "latitude": event_dict["latitude"],
            "longitude": event_dict["longitude"]
        })

    return jsonify(formatted_events)

@app.route("/submit_place", methods=["POST"])
def submit_place():
    data = request.json
    name = data.get("name")
    building = data.get("building")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    address = data.get("address", "Unknown Address")

    if not name or not building or not latitude or not longitude:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO places (name, building, latitude, longitude, address) VALUES (?, ?, ?, ?, ?)",
        (name, building, latitude, longitude, address)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Place added successfully"})

# Route: Fetch all places
@app.route("/api/places", methods=["GET"])
def get_places():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places")
    places = cursor.fetchall()
    conn.close()

    places_list = [
        {
            "name": place["name"],
            "building": place["building"],
            "latitude": place["latitude"],
            "longitude": place["longitude"]
        }
        for place in places
    ]
    return jsonify(places_list)

if __name__ == "__main__":
    app.run(debug=True)
