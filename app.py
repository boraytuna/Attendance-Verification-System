from flask import Flask, session, render_template, request, redirect, jsonify, send_file, flash, url_for
from flask_mail import Mail, Message
import sqlite3
import os
import segno
import random
import math
from datetime import datetime, timedelta
from geopy.distance import geodesic
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

DATABASE_NAME = "attendance.db"
QR_CODE_FOLDER = "qr_codes"

#session key
app.secret_key = os.urandom(24)

#scheduler for scheduling professor attendance emails
scheduler = BackgroundScheduler()
scheduler.start()

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

ENFORCE_DEVICE_ID = False  # You can toggle this off to disable device restriction (false means it doesnt wait)

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
        CREATE TABLE IF NOT EXISTS student_checkins(
            checkinID INTEGER PRIMARY KEY AUTOINCREMENT,
            deviceId TEXT NOT NULL,
            firstName TEXT NOT NULL,
            lastName TEXT NOT NULL,
            email TEXT NOT NULL,
            classForExtraCredit TEXT NOT NULL,
            professorForExtraCredit TEXT NOT NULL,
            scannedEventID INTEGER NOT NULL,
            studentLocation TEXT NOT NULL,
            checkinTime DATETIME DEFAULT CURRENT_TIMESTAMP,
            endLocation TEXT,
            endTime DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scannedEventID) REFERENCES events(eventID)
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

@app.route('/privacy-policy.html')
def privacy_policy():
    return render_template('privacy-policy.html')

@app.route('/user-agreement.html')
def user_agreement():
    return render_template('user-agreement.html')

@app.route("/") #Made by olu
def home():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Upcoming events: event start is in the future
    cursor.execute("""
        SELECT e.*, p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
        WHERE eventDate || 'T' || startTime >= ?
        ORDER BY eventDate, startTime
    """, (now,))
    upcoming = cursor.fetchall()

    # Past events: event has already ended
    cursor.execute("""
        SELECT e.*, p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
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

@app.route('/submit_student_checkin', methods=['POST'])
def submit_student_checkin():
    data = request.json
    firstName = data['firstName']
    lastName = data['lastName']
    email = data['email']
    scannedEventID = int(data['scannedEventID'])
    studentLocation = str(data['studentLocation'])
    deviceId = data.get('deviceId')
    course_entries = data.get('courses', [])  # Expecting list of {className, professorName}

    conn = get_db_connection()
    cursor = conn.cursor()

    # ✅ Optional device restriction
    if ENFORCE_DEVICE_ID:
        cursor.execute('''
            SELECT 1 FROM student_checkins
            WHERE scannedEventID = ? AND deviceId = ?
        ''', (scannedEventID, deviceId))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'status': 'error',
                'message': 'This device has already been used to check in for this event.'
            })

    # Fetch event start time once for timing logic
    cursor.execute('SELECT eventDate, startTime FROM events WHERE eventID = ?', (scannedEventID,))
    event_row = cursor.fetchone()
    if not event_row:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Event not found'}), 404

    event_start = datetime.strptime(f"{event_row['eventDate']} {event_row['startTime']}", "%Y-%m-%d %H:%M")
    grace_period_minutes = 10
    late_cutoff = event_start + timedelta(minutes=grace_period_minutes)

    responses = []

    for entry in course_entries:
        className = entry.get('className')
        professorName = entry.get('professorName')

        if not className or not professorName:
            continue  # skip if data is missing

        # Insert student check-in
        cursor.execute('''
            INSERT INTO student_checkins (
                firstName, lastName, email, classForExtraCredit,
                professorForExtraCredit, scannedEventID, studentLocation, deviceId
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            firstName, lastName, email, className,
            professorName, scannedEventID, studentLocation, deviceId
        ))

        # Fetch latest check-in row to get timestamp
        cursor.execute('''
            SELECT checkinID, checkinTime FROM student_checkins
            WHERE email = ? AND scannedEventID = ? AND lastName = ?
            AND classForExtraCredit = ? AND professorForExtraCredit = ?
            ORDER BY checkinTime DESC LIMIT 1
        ''', (email, scannedEventID, lastName, className, professorName))
        result = cursor.fetchone()

        if result:
            checkin_time = datetime.strptime(result["checkinTime"], "%Y-%m-%d %H:%M:%S")
            status = "Attended Late" if checkin_time > late_cutoff else "Attended"
            responses.append({
                "class": className,
                "professor": professorName,
                "status": status
            })

    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'entries': responses})

@app.route('/submit_end_location', methods=['POST'])
def submit_end_location():
    print("📍 /submit_end_location called")
    data = request.json
    email = data.get('email')
    scannedEventID = int(data.get('scannedEventID'))
    endLocation = str(data.get('endLocation'))
    endTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lastName = data.get('lastName')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 🔁 Update all matching rows that haven't been updated yet
        cursor.execute('''
            UPDATE student_checkins
            SET endLocation = ?, endTime = ?
            WHERE email = ? AND scannedEventID = ? AND lastName = ?
              AND (endLocation IS NULL OR endLocation = '')
        ''', (endLocation, endTime, email, scannedEventID, lastName))

        updated_count = cursor.rowcount
        conn.commit()
        print(f"✅ Updated {updated_count} rows with end location.")

        return jsonify({'status': 'success', 'updated': updated_count})
    except Exception as e:
        print(f"❌ Error updating end location: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

# **Functions for Generating and Sending Emails to Professors Post-Event**
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def parse_location(location_str):
    try:
        lat_str, lon_str = location_str.split(",")
        return float(lat_str.strip()), float(lon_str.strip())
    except Exception:
        return None, None

def construct_email_records(event_id):
    """
    Return a dictionary of professors mapped to students who checked in/out
    within 100 meters of the event location.
    """
    conn = get_db_connection()

    # Fetch event info
    event = conn.execute('''
        SELECT eventName, eventDate, startTime, stopTime, latitude, longitude
        FROM events
        WHERE eventID = ?
    ''', (event_id,)).fetchone()

    if not event:
        conn.close()
        return {}

    event_name, event_date, start_time, stop_time, event_lat, event_lon = event

    # Get student data
    results = conn.execute('''
        SELECT 
            sc.firstName, sc.lastName, sc.email, sc.professorForExtraCredit,
            sc.checkinTime, sc.endTime,
            sc.studentLocation, sc.endLocation
        FROM student_checkins sc
        WHERE sc.scannedEventID = ?
    ''', (event_id,)).fetchall()

    conn.close()

    emails = {}

    for row in results:
        first_name, last_name, email, professor, checkin_time, checkout_time, start_loc, end_loc = row

        start_lat, start_lon = parse_location(start_loc) if start_loc else (None, None)
        end_lat, end_lon = parse_location(end_loc) if end_loc else (None, None)

        if None in [start_lat, start_lon, end_lat, end_lon]:
            continue  # skip if any location is missing or invalid

        dist_checkin = haversine_distance(event_lat, event_lon, start_lat, start_lon)
        dist_checkout = haversine_distance(event_lat, event_lon, end_lat, end_lon)

        if dist_checkin <= 100 and dist_checkout <= 100:
            if professor not in emails:
                emails[professor] = []

            emails[professor].append({
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'event_name': event_name,
                'event_id': event_id,
                'official_start': start_time,
                'official_end': stop_time,
                'checkin_time': checkin_time,
                'checkout_time': checkout_time or "Not Submitted"
            })

    return emails

def send_professor_emails(event_id):
    print(f"[🚨 EMAIL JOB STARTED] Event ID: {event_id}")
    """
    Send emails to professors with a summary of student attendance records.
    """
    emails = construct_email_records(event_id)
    print(f"[🗃 EMAIL DATA] Found {len(emails)} professors for Event ID {event_id}")
    professors = emails.keys()

    # Get event name
    conn = get_db_connection()
    if not conn:
        print("[❌ ERROR] Could not get DB connection")

    event = conn.execute('SELECT eventName FROM events WHERE eventID = ?', (event_id,)).fetchone()
    conn.close()
    event_name = event[0] if event else "Unknown Event"

    conn_fakedb = get_fakedb_connection()
    if not conn:
        print("[❌ ERROR] Could not get DB connection")

    for professor in professors:
        professor_email = conn_fakedb.execute(
            'SELECT professor_email FROM Professor WHERE professor_name = ?',
            (professor,)
        ).fetchone()

        if not professor_email:
            continue

        student_rows = emails[professor]
        print(f"[📨 EMAIL TO] {professor} → {professor_email}")

        # Plaintext fallback
        plaintext_msg = f"Hello {professor},\nHere is the attendance summary for {event_name}:\n"
        for s in student_rows:
            plaintext_msg += f"{s['first_name']} {s['last_name']} | {s['email']} | Check-in: {s['checkin_time']} | Check-out: {s['checkout_time']}\n"

        # HTML Table
        html_msg = f'''
        <html>
            <body>
                <p>Hello {professor},</p>
                <p>Here is the attendance summary for <strong>{event_name}</strong>:</p>
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Event ID</th>
                        <th>Official Start</th>
                        <th>Official End</th>
                        <th>Check-in</th>
                        <th>Check-out</th>
                    </tr>
        '''


        for s in student_rows:
            html_msg += f'''
                <tr>
                    <td>{s['first_name']} {s['last_name']}</td>
                    <td>{s['email']}</td>
                    <td>{s['event_id']}</td>
                    <td>{s['official_start']}</td>
                    <td>{s['official_end']}</td>
                    <td>{s['checkin_time']}</td>
                    <td>{s['checkout_time']}</td>
                </tr>
            '''

        html_msg += '''
                </table>
                <p>Please review the times and assign attendance credit manually based on their duration.</p>
            </body>
        </html>
        '''

        with app.app_context():
            try:
                msg = Message(
                    subject=f'Student Attendance Report - {event_name}',
                    recipients=[professor_email[0]],
                    body=plaintext_msg,
                    html=html_msg
                )
                mail.send(msg)
                print(f"[✅ EMAIL SENT] Event {event_id} → {professor} ({professor_email[0]})")
            except Exception as e:
                print(f"[❌ EMAIL FAILED] Event {event_id} → {professor} ({professor_email[0]}): {e}")

    conn_fakedb.close()

    # Mark this event as "email sent"
    conn = get_db_connection()
    conn.execute("UPDATE events SET professor_email_sent = 1 WHERE eventID = ?", (event_id,))
    conn.commit()
    conn.close()
    print("Updated events table for email sent")

def reschedule_pending_emails():
    """
    On server restart, re-schedule any professor emails that haven't been sent
    and whose stopTime is still in the future (within 5 minutes window).
    """
    conn = get_db_connection()
    now = datetime.now()

    events = conn.execute('''
        SELECT eventID, eventDate, stopTime 
        FROM events 
        WHERE professor_email_sent = 0
    ''').fetchall()

    for event in events:
        event_id, event_date, stop_time = event
        try:
            stop_dt = datetime.strptime(f"{event_date} {stop_time}", "%Y-%m-%d %H:%M")
            execute_dt = stop_dt + timedelta(minutes=5)

            if execute_dt > now:
                # Job still valid, reschedule it
                scheduler.add_job(
                    func=send_professor_emails,
                    trigger='date',
                    run_date=execute_dt,
                    args=[event_id],
                    id=f"professor_email_{event_id}",
                    replace_existing=True
                )
                print(f"Rescheduled professor email for {event_id}.")
        except Exception as e:
            print(f"[RESCHEDULE ERROR] Could not reschedule email for event {event_id}: {e}")

    conn.close()

@app.route("/submit_event", methods=["POST"])
def submit_event():
    event_name = request.form["event_name"]
    event_date = request.form["event_date"]
    start_time = request.form["start_time"]
    stop_time = request.form["stop_time"]
    event_location = request.form["event_location"]
    event_address = request.form.get("event_address", "Unknown Location")

    # NEW: Parse location
    try:
        lat, lng = map(float, event_location.split(","))
    except ValueError:
        flash("❌ Invalid location format.", "error")
        return redirect(url_for("events"))

    # NEW: Validate time logic
    if start_time >= stop_time:
        flash("❌ End time must be later than start time.", "error")
        return redirect(url_for("events"))

    # NEW: Prevent duplicate event at same time/location
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM events 
        WHERE eventDate = ? AND startTime = ? AND stopTime = ? 
        AND ROUND(latitude, 6) = ROUND(?, 6) AND ROUND(longitude, 6) = ROUND(?, 6)
    """, (event_date, start_time, stop_time, lat, lng))
    same_time_place = cursor.fetchone()

    if same_time_place:
        conn.close()
        flash("❌ Another event is already scheduled at this time and location.", "error")
        return redirect(url_for("events"))

    # SAFE TO INSERT
    cursor.execute('''
        INSERT INTO events (eventName, eventDate, startTime, stopTime, latitude, longitude, eventAddress)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (event_name, event_date, start_time, stop_time, lat, lng, event_address))
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    get_or_create_qr_code(event_id)

    # ✅ Schedule email 5 minutes after event ends
    try:
        # Combine date and time from form
        event_end_str = f"{event_date} {stop_time}"
        event_end_dt = datetime.strptime(event_end_str, "%Y-%m-%d %H:%M")
        executetime = event_end_dt + timedelta(minutes=5)

        # Schedule the email with a unique job ID
        scheduler.add_job(
            func=send_professor_emails,
            trigger='date',
            run_date=executetime,
            args=[event_id],
            id=f"professor_email_{event_id}",
            replace_existing=True
        )
        print(f"Scheduled professor email for event {event_id}.")
    except Exception as e:
        print(f"[SCHEDULER ERROR] Could not schedule professor email for event {event_id}: {e}")

    return redirect(url_for("dashboard", success=1))

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

@app.route('/find_student', methods=['GET', 'POST'])
def find_student():
    students = None  # Ensure we differentiate between no search and empty results

    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()

        if first_name or last_name:  # Ensure at least one field is filled
            conn = get_db_connection()
            cursor = conn.cursor()

            query = '''
            SELECT * FROM student_checkins 
            WHERE (firstName LIKE ? OR lastName LIKE ?)
            '''

            params = [f'%{first_name}%', f'%{last_name}%']

            cursor.execute(query, params)
            students = cursor.fetchall()
            conn.close()

    return render_template('find_student.html', students=students)

@app.route("/test_email/<int:event_id>")
def test_send_professor_email(event_id):
    send_professor_emails(event_id)
    return f"Triggered professor email manually for event {event_id}"

@app.route("/test_location_accuracy/<int:event_id>")
def test_location_accuracy(event_id):
    from flask import Response
    output = []

    conn = get_db_connection()

    # Get event location
    event = conn.execute('''
        SELECT eventName, latitude, longitude
        FROM events
        WHERE eventID = ?
    ''', (event_id,)).fetchone()

    if not event:
        return f"No event found with ID {event_id}", 404

    event_name, event_lat, event_lon = event
    output.append(f"🔍 Testing Check-in Distances for Event: {event_name} (ID: {event_id})<br><br>")

    # Get student check-in data
    results = conn.execute('''
        SELECT firstName, lastName, email, startLocation, endLocation
        FROM student_checkins
        WHERE scannedEventID = ?
    ''', (event_id,)).fetchall()

    conn.close()

    for row in results:
        first_name, last_name, email, start_loc, end_loc = row
        start_lat, start_lon = parse_location(start_loc) if start_loc else (None, None)
        end_lat, end_lon = parse_location(end_loc) if end_loc else (None, None)

        result_line = f"<b>{first_name} {last_name}</b> ({email}): "

        if None in [start_lat, start_lon, end_lat, end_lon]:
            result_line += "<span style='color:red;'>❌ Invalid location data</span><br>"
        else:
            dist_checkin = haversine_distance(event_lat, event_lon, start_lat, start_lon)
            dist_checkout = haversine_distance(event_lat, event_lon, end_lat, end_lon)

            checkin_ok = dist_checkin <= 100
            checkout_ok = dist_checkout <= 100

            result_line += f"Check-in: {dist_checkin:.2f}m | Check-out: {dist_checkout:.2f}m → "
            if checkin_ok and checkout_ok:
                result_line += "<span style='color:green;'>✅ Valid</span><br>"
            else:
                result_line += "<span style='color:orange;'>⚠️ Outside 100m</span><br>"

        output.append(result_line)

    return Response("".join(output), mimetype='text/html')

if __name__ == "__main__":
    scheduler.start()
    reschedule_pending_emails()
    app.run(debug=True)
