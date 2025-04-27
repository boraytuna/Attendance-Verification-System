from flask import Flask, session, render_template, request, redirect, jsonify, send_file, flash, url_for, \
    render_template_string
from flask_mail import Mail, Message
import sqlite3
import os
import segno
import random
import math
import requests
from datetime import datetime, timedelta, date
from geopy.distance import geodesic
import passlib, passlib.hash
from passlib.hash import sha256_crypt
from functools import wraps
from uuid import uuid4
import logging
import pytz

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

DATABASE_NAME = "attendance.db"
QR_CODE_FOLDER = "qr_codes"

# session key
app.secret_key = os.urandom(24)

ENFORCE_DEVICE_ID = True  # Can toggle off for testing or relaxed events

# mail server configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'jrosestangle@gmail.com'
app.config['MAIL_PASSWORD'] = 'pfdbqlrqisxzubmf'  # app pw
app.config['MAIL_DEFAULT_SENDER'] = 'jrosestangle@gmail.com'
mail = Mail(app)

if not os.path.exists(QR_CODE_FOLDER):
    os.makedirs(QR_CODE_FOLDER)

# Function to connect to SQLite
def get_db_connection():
    """
    Establish a connection to the SQLite attendance.db database.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Enables dictionary-style access
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
    return conn

def login_required(f):
    """
    Decorator that restricts access to a route unless the user is logged in.
    If a user is not logged in, they are redirected to the login page.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

def get_eastern_now():
    return datetime.now(pytz.timezone("US/Eastern"))

@app.route("/")
def landing_page():
    """
    Flask route for the landing page.

    Returns:
        the rendered landing page HTML template
    """
    return render_template("landing_page.html")


@app.route("/signup")
def signup():
    """
    Flask route rendering for the signup page.

    Returns:
        the rendered signup page HTML template
    """
    return render_template("signup.html")


@app.route("/submit_signup", methods=["POST"])
def submit_signup():
    """
    API route to handle user signup.
    """
    data = request.json
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = sha256_crypt.encrypt(data.get('password'))

    conn = get_db_connection()
    try:
        # first check if account with email already exists
        user = conn.cursor().execute('''
            SELECT * FROM users WHERE email = ?
        ''', (email,)).fetchone()

        if user is not None:
            return jsonify({
                "success": False,
                "message": "An account with this email already exists."
            })
        else:
            conn.cursor().execute('''
                INSERT INTO users (first_name, last_name, email, password)
                VALUES (?, ?, ?, ?)
            ''', (first_name, last_name, email, password))
            conn.commit()

            return jsonify({
                "success": True,
                "message": "Account creation successful!"
            })
    except sqlite3.Error as e:
        return jsonify({
            "success": False,
            "message": f"Database error: {str(e)}"
        })
    finally:
        conn.close()


@app.route("/submit_login", methods=["POST"])
def submit_login():
    """
    API route to handle user login.
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')

    conn = get_db_connection()
    try:
        user = conn.cursor().execute('''
            SELECT * FROM users WHERE email = ?
        ''', (email,)).fetchone()
    except sqlite3.Error as e:
        return jsonify({
            "success": False,
            "message": f"Database error: {str(e)}"
        })
    finally:
        conn.close()

    if user is None:
        return jsonify({
            "success": False,
            "message": "No account exists with this email."
        })
    elif sha256_crypt.verify(password, user[4]):  # assuming index 4 = password
        session['user_id'] = user[0]
        session['user_email'] = user[3]
        session['first_name'] = user[1]
        session['last_name'] = user[2]
        return jsonify({
            "success": True,
            "message": "Login successful."
        })
    else:
        return jsonify({
            "success": False,
            "message": "Incorrect password."
        })


@app.route("/login")
def login():
    """
    Flask route rendering for the login page.

    Returns:
        the rendered login page HTML template
    """
    return render_template("login.html")


@app.route("/submit_logout", methods=["POST"])
def submit_logout():
    """
    """
    # clear all session storage
    session.clear()

    # redirect to the landing page
    return redirect(url_for("landing_page"))


@app.route("/api/dashboard_data")
@login_required
def get_dashboard_data():
    user_id = session["user_id"]
    now = get_eastern_now().strftime("%Y-%m-%dT%H:%M:%S")

    # Get pagination args
    per_page = 5
    current_page = int(request.args.get("current_page", 1))
    upcoming_page = int(request.args.get("upcoming_page", 1))
    past_page = int(request.args.get("past_page", 1))

    conn = get_db_connection()
    cursor = conn.cursor()

    def paginate(query, args, page):
        offset = (page - 1) * per_page
        results = cursor.execute(query + " LIMIT ? OFFSET ?", args + [per_page, offset]).fetchall()
        total = cursor.execute("SELECT COUNT(*) FROM (" + query + ")", args).fetchone()[0]
        return [dict(r) for r in results], total

    # CURRENT
    query = """SELECT e.*, p.name AS place_name, p.building FROM events e
               LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
               WHERE eventDate || 'T' || startTime <= ? AND eventDate || 'T' || stopTime >= ? AND professorID = ?
               ORDER BY eventDate, startTime"""
    current, current_total = paginate(query, [now, now, user_id], current_page)

    # UPCOMING
    query = """SELECT e.*, p.name AS place_name, p.building FROM events e
               LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
               WHERE eventDate || 'T' || startTime > ? AND professorID = ?
               ORDER BY eventDate, startTime"""
    upcoming, upcoming_total = paginate(query, [now, user_id], upcoming_page)

    # PAST
    query = """SELECT e.*, p.name AS place_name, p.building FROM events e
               LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
               WHERE eventDate || 'T' || stopTime < ? AND professorID = ?
               ORDER BY eventDate DESC, startTime DESC"""
    past, past_total = paginate(query, [now, user_id], past_page)

    conn.close()
    return jsonify({
        "current_events": current, "current_total": current_total,
        "upcoming_events": upcoming, "upcoming_total": upcoming_total,
        "past_events": past, "past_total": past_total,
        "per_page": per_page
    })


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    now = get_eastern_now().strftime("%Y-%m-%dT%H:%M:%S")
    per_page = 5  # how many events per page

    # Get current page numbers from URL
    upcoming_page = int(request.args.get("upcoming_page", 1))
    current_page = int(request.args.get("current_page", 1))
    past_page = int(request.args.get("past_page", 1))

    conn = get_db_connection()
    cursor = conn.cursor()

    # -- UPCOMING --
    cursor.execute("""
        SELECT e.*, p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
        WHERE eventDate || 'T' || startTime > ? AND professorID = ?
        ORDER BY eventDate, startTime
    """, (now, user_id))
    upcoming_all = cursor.fetchall()
    upcoming = upcoming_all[(upcoming_page - 1) * per_page: upcoming_page * per_page]

    # -- CURRENT --
    cursor.execute("""
        SELECT e.*, p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
        WHERE eventDate || 'T' || startTime <= ?
          AND eventDate || 'T' || stopTime >= ?
          AND professorID = ?
        ORDER BY eventDate, startTime
    """, (now, now, user_id))
    current_all = cursor.fetchall()
    current = current_all[(current_page - 1) * per_page: current_page * per_page]

    # -- PAST --
    cursor.execute("""
        SELECT e.*, p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
        WHERE eventDate || 'T' || stopTime < ? AND professorID = ?
        ORDER BY eventDate DESC, startTime DESC
    """, (now, user_id))
    past_all = cursor.fetchall()
    past = past_all[(past_page - 1) * per_page: past_page * per_page]

    conn.close()

    return render_template("dashboard.html",
                           current_events=current,
                           upcoming_events=upcoming,
                           past_events=past,
                           current_total=len(current_all),
                           upcoming_total=len(upcoming_all),
                           past_total=len(past_all),
                           per_page=per_page,
                           current_page=current_page,
                           upcoming_page=upcoming_page,
                           past_page=past_page)


@app.route("/dashboard_partial/current")
@login_required
def dashboard_current_partial():
    return render_partial_events("current")


@app.route("/dashboard_partial/upcoming")
@login_required
def dashboard_upcoming_partial():
    return render_partial_events("upcoming")


@app.route("/dashboard_partial/past")
@login_required
def dashboard_past_partial():
    return render_partial_events("past")


def render_partial_events(section):
    user_id = session["user_id"]
    now = get_eastern_now().strftime("%Y-%m-%dT%H:%M:%S")
    per_page = 5

    try:
        page = int(request.args.get("page", 1))
    except (ValueError, TypeError):
        page = 1

    conn = get_db_connection()
    cursor = conn.cursor()

    query_base = """
        SELECT e.*, p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
        WHERE professorID = ?
    """
    args = [user_id]

    if section == "current":
        query_base += " AND eventDate || 'T' || startTime <= ? AND eventDate || 'T' || stopTime >= ?"
        args = [now, now, user_id]
        order = " ORDER BY eventDate, startTime"
        section_name = "🟡 Events Happening Now"
        page_var = "current_page"
    elif section == "upcoming":
        query_base += " AND eventDate || 'T' || startTime > ?"
        args = [now, user_id]
        order = " ORDER BY eventDate, startTime"
        section_name = "📅 Upcoming Events"
        page_var = "upcoming_page"
    else:
        query_base += " AND eventDate || 'T' || stopTime < ?"
        args = [now, user_id]
        order = " ORDER BY eventDate DESC, startTime DESC"
        section_name = "🕘 Past Events"
        page_var = "past_page"

    full_query = query_base + order
    all_rows = cursor.execute(full_query, args).fetchall()
    paginated = all_rows[(page - 1) * per_page: page * per_page]
    conn.close()

    return render_template_string("""
        {% from 'macros.html' import render_table %}
        {{ render_table(events, section_name, page_var, total, per_page, current_page) }}
    """, events=paginated, section_name=section_name, page_var=page_var,
                                  total=len(all_rows), per_page=per_page, current_page=page)


@app.route("/events")
@login_required
def events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    conn.close()
    return render_template("events.html", events=events)


# Route: Calendar Page
@app.route("/calendar")
@login_required
def calendar():
    conn = get_db_connection()
    events = conn.execute("SELECT * FROM events").fetchall()
    conn.close()

    # Convert to a list of dicts if needed (e.g., for JSON compatibility)
    event_list = []
    for event in events:
        event_list.append({
            'title': event['eventName'],
            'start': f"{event['eventDate']}T{event['startTime']}",
            'end': f"{event['eventDate']}T{event['stopTime']}",
        })

    return render_template("calendar.html", events=event_list)


# Route: Places Page
@app.route("/places")
@login_required
def places():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM places")
    places = cursor.fetchall()
    conn.close()
    return render_template("places.html", places=places)


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get full user info
    cursor.execute("""
        SELECT first_name, last_name, email, password FROM users WHERE email = ?
    """, (session['user_email'],))
    user = cursor.fetchone()

    if request.method == 'POST':
        # 🧠 Grab form data
        new_first = request.form.get('first_name').strip()
        new_last = request.form.get('last_name').strip()
        new_email = request.form.get('email').strip()
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not new_first or not new_last or not new_email:
            flash("❌ First name, last name, and email cannot be empty.")
            return redirect(url_for('account'))

        # 🔐 If password is being changed, validate and hash
        if new_password or confirm_password:
            if new_password != confirm_password:
                flash("❌ Passwords do not match.")
                return redirect(url_for('account'))
            hashed_password = sha256_crypt.hash(new_password)
            cursor.execute("""
                UPDATE users SET first_name = ?, last_name = ?, email = ?, password = ? WHERE email = ?
            """, (new_first, new_last, new_email, hashed_password, session['user_email']))
        else:
            # 📝 Only update name/email
            cursor.execute("""
                UPDATE users SET first_name = ?, last_name = ?, email = ? WHERE email = ?
            """, (new_first, new_last, new_email, session['user_email']))

        conn.commit()
        conn.close()

        # 🧼 Force re-login ONLY if email or password changed
        if new_email != session['user_email'] or new_password:
            flash("✅ Info updated. Please log in again.")
            session.clear()
            return redirect(url_for('login'))

        # 🔁 If only name changed, no logout needed
        flash("✅ Account info updated!")
        session['user_email'] = new_email  # update session if email changed
        return redirect(url_for('account'))

    conn.close()
    return render_template('account.html', user=user)


# # Function to generate (or retrieve) QR code
# def get_or_create_qr_code(event_id):
#     qr_code_path = os.path.join(QR_CODE_FOLDER, f"event_{event_id}.png")
#
#     if os.path.exists(qr_code_path):
#         return qr_code_path  # Return existing QR code
#
#     # Generate new QR code that directs to the student interface
#     qr_url = f"http://127.0.0.1:5000/student_checkin/{event_id}"  # temp - Boray was using on his laptop
#     # qr_url = f"http://192.168.1.100:5000/student_checkin/{event_id}" #temp - Joie was using this IP to test on her local network (address for home network)
#     # qr_url = f"http://172.20.10.12:5000/student_checkin/{event_id}" #temp - Joie was using this IP to test on her local network (address for phone hotspot)
#     qr = segno.make(qr_url)
#     qr.save(qr_code_path, scale=10)
#
#     return qr_code_path
def get_or_create_qr_code(event_id):
    qr_code_path = os.path.join(QR_CODE_FOLDER, f"event_{event_id}.png")

    if os.path.exists(qr_code_path):
        return qr_code_path  # Return existing QR code

    # Use the deployed public URL on Render
    qr_url = f"https://attendance-verification-system.onrender.com/student_checkin/{event_id}"

    qr = segno.make(qr_url)
    qr.save(qr_code_path, scale=10)

    return qr_code_path


# Route: Serve QR Code
@app.route("/qr_code/<int:event_id>")
@login_required
def serve_qr_code(event_id):
    qr_code_path = get_or_create_qr_code(event_id)
    return send_file(qr_code_path, mimetype="image/png")


@app.route("/calendar_event_qr/<int:event_id>")
@login_required
def qr_display(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.eventName, e.eventDate, e.startTime, e.stopTime, 
               e.eventDescription,
               p.name AS placeName, p.building
        FROM events e
        JOIN places p ON ROUND(e.latitude, 6) = ROUND(p.latitude, 6) 
                      AND ROUND(e.longitude, 6) = ROUND(p.longitude, 6)
        WHERE e.eventID = ?
    """, (event_id,))
    event = cursor.fetchone()
    conn.close()

    if not event:
        flash("❌ Event not found.", "error")
        return redirect(url_for("dashboard"))

    return render_template("qr_display.html", event=event, qr_url=url_for("serve_qr_code", event_id=event_id))


# **Route: Student Interface**
@app.route("/student_checkin/<int:event_id>")
def student_interface(event_id):
    """Serve the student interface pages for a specific event.
    Pass the eventID and eventName to the HTML template."""
    # get the event name associated with the eventID
    cursor = get_db_connection().cursor()
    cursor.execute('SELECT eventName, eventDate, stopTime FROM events WHERE eventID = ?', (event_id,))
    result = cursor.fetchone()

    if not result:
        return render_template("student_checkin.html", eventName="Event Not Found", eventEnd="2000-01-01T00:00:00")

    event_name, event_date, stop_time = result

    # 🛠 Normalize stop_time
    if len(stop_time.split(':')) == 2:
        stop_time += ":00"  # Convert HH:MM ➜ HH:MM:SS

    event_end = datetime.strptime(f"{event_date} {stop_time}", "%Y-%m-%d %H:%M:%S").isoformat()

    return render_template("student_checkin.html", eventName=event_name, eventEnd=event_end)

# **API Routes for Student Check-In Email Verification**
@app.route('/verify_email', methods=['POST'])
def send_email():
    data = request.get_json()
    email = data.get('email')

    # generate a random 6 digit code
    code = ''
    for i in range(6):
        num = random.randint(0, 9)
        code += str(num)

    # store the code in the session
    session['verification_code'] = code

    body_msg = 'Your email verification code for student check-in is: ' + code
    msg = Message(
        'Student Check-In Code',
        recipients=[email],
        body=body_msg
    )

    try:
        mail.send(msg)
        return 'Sent', 200
    except Exception as e:
        return str(e), 500


@app.route('/resend_verification_email', methods=['POST'])
def resend_email():
    data = request.get_json()
    email = data.get('email')

    COOLDOWN_SECONDS = 180

    code = session.get('verification_code')
    last_sent = session.get('last_verification_email_sent')

    if not code:
        return jsonify({'error': 'No verification code found. Please restart the process.'}), 400

    # Check cooldown
    if last_sent:
        last_sent_time = pytz.timezone('US/Eastern').localize(datetime.strptime(last_sent, "%Y-%m-%d %H:%M:%S"))
        if get_eastern_now() < last_sent_time + timedelta(seconds=COOLDOWN_SECONDS):
            remaining = (last_sent_time + timedelta(seconds=COOLDOWN_SECONDS)) - get_eastern_now()
            return jsonify({
                'error': f'Please wait {int(remaining.total_seconds())} more seconds before resending.'
            }), 429

    msg = Message(
        'Student Check-In Code (Resend)',
        recipients=[email],
        body=f'Your email verification code is: {code}'
    )

    try:
        mail.send(msg)
        session['last_verification_email_sent'] = get_eastern_now().strftime("%Y-%m-%d %H:%M:%S")
        return jsonify({'message': 'Verification code resent.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = request.args.get('query', '')
    cursor.execute("SELECT course_name FROM courses WHERE course_name LIKE ?", (f"%{search_term}%",))
    results = cursor.fetchall()
    conn.close()
    return jsonify([row[0] for row in results])


@app.route('/search_professors', methods=['GET'])
def search_professors():
    """Search for professors based on user input."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = request.args.get('query', '')
    cursor.execute("SELECT professor_name FROM professors WHERE professor_name LIKE ?", (f"%{search_term}%",))
    results = cursor.fetchall()
    conn.close()
    return jsonify([row[0] for row in results])


@app.route('/submit_student_checkin', methods=['POST'])
def submit_student_checkin():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400

        firstName = data.get('firstName', '').strip()
        lastName = data.get('lastName', '').strip()
        email = data.get('email', '').strip()
        scannedEventID = data.get('scannedEventID')
        studentLocation = data.get('studentLocation', '').strip()
        deviceId = data.get('deviceId')
        course_entries = data.get('courses', [])

        if not all([firstName, lastName, email, scannedEventID, studentLocation]):
            return jsonify({'status': 'error', 'message': 'Missing required student fields'}), 400

        try:
            scannedEventID = int(scannedEventID)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid scannedEventID'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Optional: Prevent multiple check-ins from same device for same event
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
                }), 403

        # Validate that event exists
        cursor.execute('SELECT eventDate, startTime FROM events WHERE eventID = ?', (scannedEventID,))
        event_row = cursor.fetchone()
        if not event_row:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Event not found'}), 404

        event_start = datetime.strptime(f"{event_row['eventDate']} {event_row['startTime']}", "%Y-%m-%d %H:%M")
        late_cutoff = event_start + timedelta(minutes=10)

        responses = []

        for entry in course_entries:
            className = entry.get('className', '').strip()
            professorName = entry.get('professorName', '').strip()

            if not className or not professorName:
                continue

            # Insert new check-in record
            cursor.execute('''
                INSERT INTO student_checkins (
                    firstName, lastName, email, classForExtraCredit,
                    professorForExtraCredit, scannedEventID, studentLocation, deviceId
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                firstName, lastName, email, className,
                professorName, scannedEventID, studentLocation, deviceId
            ))
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'entries': responses})

    except Exception as e:
        import traceback
        print("🔥 Exception in /submit_student_checkin:", traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/submit_end_location', methods=['POST'])
def submit_end_location():
    print("📍 /submit_end_location called")
    data = request.json

    try:
        email = data.get('email', '').strip()
        lastName = data.get('lastName', '').strip()
        scannedEventID = data.get('scannedEventID')
        endLocation = str(data.get('endLocation', '')).strip()
        endTime = get_eastern_now().strftime('%Y-%m-%d %H:%M:%S')

        # Validate input
        if not all([email, lastName, scannedEventID, endLocation]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        try:
            scannedEventID = int(scannedEventID)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid scannedEventID'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Update all matching check-ins without an endLocation
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

def evaluate_student_location(event_lat, event_lon, start_loc, end_loc):
    def parse(loc):
        try:
            lat_str, lon_str = loc.split(",")
            return float(lat_str), float(lon_str)
        except Exception:
            return None, None

    start_lat, start_lon = parse(start_loc)
    end_lat, end_lon = parse(end_loc)

    def in_range(lat, lon):
        if lat is None or lon is None:
            return False
        return haversine_distance(event_lat, event_lon, lat, lon) <= 100

    checkin_in_range = in_range(start_lat, start_lon)
    checkout_in_range = in_range(end_lat, end_lon)

    if checkin_in_range and checkout_in_range:
        return "✅ Both Locations Within 100m"
    elif checkin_in_range:
        return "⚠️ Only Check-In Within Range"
    elif checkout_in_range:
        return "⚠️ Only Check-Out Within Range"
    else:
        return "❌ Neither Location Within Range"


def send_professor_emails(event_id):
    print(f"[🚨 EMAIL JOB STARTED] Event ID: {event_id}")
    emails_by_professor = {}

    # 💥 Prevent duplicate sends
    conn_check = get_db_connection()
    status = conn_check.execute("SELECT professor_email_sent FROM events WHERE eventID = ?", (event_id,)).fetchone()
    conn_check.close()

    if status and status["professor_email_sent"] == 1:
        print(f"[🚫 ABORTED] Email already sent for Event ID {event_id}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch event details
    event = cursor.execute('''
        SELECT eventName, eventDate, startTime, stopTime, latitude, longitude
        FROM events WHERE eventID = ?
    ''', (event_id,)).fetchone()

    if not event:
        print("[❌ ERROR] Event not found.")
        conn.close()
        return

    event_name, event_date, start_time, stop_time, event_lat, event_lon = event

    # Fetch all check-ins for the event
    rows = cursor.execute('''
        SELECT firstName, lastName, email, classForExtraCredit, professorForExtraCredit,
               checkinTime, endTime, studentLocation, endLocation
        FROM student_checkins
        WHERE scannedEventID = ?
    ''', (event_id,)).fetchall()
    conn.close()

    for row in rows:
        first, last, email, class_name, prof_name, checkin_time, end_time, loc_start, loc_end = row

        location_status = evaluate_student_location(event_lat, event_lon, loc_start, loc_end)

        if prof_name not in emails_by_professor:
            emails_by_professor[prof_name] = []

        emails_by_professor[prof_name].append({
            "name": f"{first} {last}",
            "email": email,
            "class": class_name,
            "event_id": event_id,
            "event_date": event_date,
            "official_start": start_time,
            "official_end": stop_time,
            "student_checkin": checkin_time,
            "student_checkout": end_time or "Not Submitted",
            "location_status": location_status
        })

    if not emails_by_professor:
        print(f"[⚠️ NO MATCH] No check-ins found for Event {event_id}")
        return

    # Send email to each professor
    conn_db = get_db_connection()
    for prof, students in emails_by_professor.items():
        prof_email_row = conn_db.execute(
            'SELECT professor_email FROM professors WHERE professor_name = ?',
            (prof,)
        ).fetchone()

        if not prof_email_row:
            print(f"[❌ NO EMAIL] No email found for professor: {prof}")
            continue

        recipient = prof_email_row[0]

        html_table = '''
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
            <tr>
                <th>Name</th><th>Email</th><th>Class</th><th>Event ID</th><th>Date</th>
                <th>Official Start</th><th>Official End</th>
                <th>Check-in</th><th>Check-out</th><th>Location Status</th>
            </tr>
        '''
        for s in students:
            html_table += f'''
                <tr>
                    <td>{s["name"]}</td>
                    <td>{s["email"]}</td>
                    <td>{s["class"]}</td>  <!-- ✅ NEW: class from student dict -->
                    <td>{s["event_id"]}</td>
                    <td>{s["event_date"]}</td>
                    <td>{s["official_start"]}</td>
                    <td>{s["official_end"]}</td>
                    <td>{s["student_checkin"]}</td>
                    <td>{s["student_checkout"]}</td>
                    <td>{s["location_status"]}</td>
                </tr>
            '''
        html_table += '</table>'

        html_msg = f'''
        <p>Hello {prof},</p>
        <p>Below is the attendance summary for <strong>{event_name}</strong> on {event_date}. Each student is tagged with how close they were to the event based on check-in and check-out locations.</p>
        {html_table}
        '''

        plaintext_msg = f"Professor {prof},\nHere are your students for event {event_name} on {event_date}:\n"
        for s in students:
            plaintext_msg += f"{s['name']} | {s['email']} | Check-in: {s['student_checkin']} | Check-out: {s['student_checkout']} | {s['location_status']}\n"

        try:
            msg = Message(
                subject=f"Attendance Summary: {event_name}",
                recipients=[recipient],
                body=plaintext_msg,
                html=html_msg
            )
            mail.send(msg)
            print(f"[✅ EMAIL SENT] To: {prof} ({recipient}) for Event ID {event_id}")
        except Exception as e:
            print(f"[❌ EMAIL FAILED] To: {prof} ({recipient}): {e}")

    conn_db.close()

    # ✅ Mark event as email sent
    conn = get_db_connection()
    conn.execute("UPDATE events SET professor_email_sent = 1 WHERE eventID = ?", (event_id,))
    conn.commit()
    conn.close()
    print(f"[📬 STATUS] Marked Event ID {event_id} as professor_email_sent = 1")

@app.route("/send_email_summary/<int:event_id>")
@login_required
def send_email_summary(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check check-ins
    students = cursor.execute("""
        SELECT firstName, lastName, email, classForExtraCredit, professorForExtraCredit
        FROM student_checkins
        WHERE scannedEventID = ?
    """, (event_id,)).fetchall()

    if not students:
        conn.close()
        return render_template("email_confirmation.html",
                               grouped_by_prof={},
                               event_id=event_id,
                               show_send_button=False,
                               show_resend_button=False)

    grouped = {}
    for s in students:
        prof = s["professorForExtraCredit"]
        grouped.setdefault(prof, []).append({
            "name": f"{s['firstName']} {s['lastName']}",
            "email": s["email"],
            "class": s["classForExtraCredit"]
        })

    # Check status
    status = cursor.execute("SELECT professor_email_sent FROM events WHERE eventID = ?", (event_id,)).fetchone()
    conn.close()

    already_sent = status and status[0] == 1
    show_send_button = not already_sent
    show_resend_button = already_sent

    # ❗️Only send email if not already sent
    if show_send_button:
        send_professor_emails(event_id)

    return render_template("email_confirmation.html",
                           grouped_by_prof=grouped,
                           event_id=event_id,
                           show_send_button=False,
                           show_resend_button=show_resend_button)

@app.route("/force_resend_email/<int:event_id>", methods=["POST"])
@login_required
def force_resend_email(event_id):
    # Optional: log forced sends if needed
    print(f"[🔁 FORCED EMAIL RESEND] for Event {event_id} by user {session.get('user_id')}")
    # Remove the 'sent' flag temporarily
    conn = get_db_connection()
    conn.execute("UPDATE events SET professor_email_sent = 0 WHERE eventID = ?", (event_id,))
    conn.commit()
    conn.close()
    # Call send logic again
    send_professor_emails(event_id)
    return redirect(url_for("send_email_summary", event_id=event_id))

@app.route("/submit_event", methods=["POST"])
@login_required
def submit_event():
    print("📩 HIT THE ROUTE")
    print("FORM:", dict(request.form))

    # Collect and log form data
    event_name = request.form.get("event_name", "").strip()
    event_date = request.form.get("event_date")
    start_time = request.form.get("start_time")
    stop_time = request.form.get("stop_time")
    event_location = request.form.get("event_location")
    is_recurring = request.form.get("is_recurring") == "true"
    event_description = request.form.get("event_info", "").strip()

    try:
        # Parse time fields
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        stop_time_obj = datetime.strptime(stop_time, "%H:%M").time()

        if stop_time_obj <= start_time_obj:
            flash("❌ End time must be after start time.", "error")
            return redirect(url_for("events"))

        # Validate single event date
        if not is_recurring:
            event_date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
            eastern = pytz.timezone("US/Eastern")
            event_datetime_naive = datetime.combine(event_date_obj, start_time_obj)
            event_datetime = eastern.localize(event_datetime_naive)

            now = get_eastern_now()
            if event_datetime < now:
                flash("❌ You cannot create an event in the past.", "error")
                return redirect(url_for("events"))

        # Validate recurring event dates
        else:
            recurrence_start = request.form.get("recurrence_start_date")
            recurrence_end = request.form.get("recurrence_end_date")

            recurrence_start_obj = datetime.strptime(recurrence_start, "%Y-%m-%d").date()
            recurrence_end_obj = datetime.strptime(recurrence_end, "%Y-%m-%d").date()

            if recurrence_start_obj < date.today():
                flash("❌ Recurrence start date cannot be in the past.", "error")
                return redirect(url_for("events"))

            if recurrence_end_obj < recurrence_start_obj:
                flash("❌ Recurrence end date cannot be before the start date.", "error")
                return redirect(url_for("events"))

    except ValueError as ve:
        flash("❌ Invalid date or time format.", "error")
        logging.error(f"[PARSE ERROR] {ve}")
        return redirect(url_for("events"))

    recurrence_type = request.form.get("recurrence", "none")
    # 🔒 Block if recurrence type is 'none' but user selected recurring (unless they confirmed)
    if is_recurring and recurrence_type == "none" and "recurrence_warning_acknowledged" not in request.form:
        logging.warning("❌ Recurring selected but recurrence type is 'none'. Blocking creation.")
        flash(
            "❌ Event was not saved. You selected 'Recurring' but chose 'Does not repeat'. Please select a repeat type and try again.",
            "error")
        return redirect(url_for("events"))
    recurrence_start = request.form.get("recurrence_start_date")
    recurrence_end = request.form.get("recurrence_end_date")
    professor_id = session.get("user_id")

    logging.debug(f"Event Name: {event_name}")
    logging.debug(f"Recurring: {is_recurring}, Type: {recurrence_type}")
    logging.debug(f"Recurrence Range: {recurrence_start} to {recurrence_end}")

    # Validate and parse coordinates
    try:
        lat, lng = map(float, event_location.split(","))
        logging.debug(f"Parsed location: {lat}, {lng}")
    except Exception as e:
        logging.error(f"❌ Invalid location format: {e}")
        flash("❌ Invalid location format.", "error")
        return redirect(url_for("events"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify that this location exists in places table
    cursor.execute("""
        SELECT * FROM places 
        WHERE ROUND(latitude, 6) = ROUND(?, 6) AND ROUND(longitude, 6) = ROUND(?, 6)
    """, (lat, lng))
    place = cursor.fetchone()

    if not place:
        logging.warning("❌ Location does not match any known place.")
        flash("❌ Selected location does not match a saved place.", "error")
        return redirect(url_for("events"))

    # Validate time logic
    if start_time >= stop_time:
        logging.warning("Start time >= stop time")
        flash("❌ End time must be later than start time.", "error")
        return redirect(url_for("events"))

    # Verify the place exists in the DB
    cursor.execute("""
        SELECT * FROM places 
        WHERE ROUND(latitude, 6) = ROUND(?, 6) AND ROUND(longitude, 6) = ROUND(?, 6)
    """, (lat, lng))
    place = cursor.fetchone()

    if not place:
        conn.close()
        logging.error("❌ Location does not match a saved place")
        flash("❌ Selected location does not match any saved place.", "error")
        return redirect(url_for("events"))

    # --- RECURRING EVENT HANDLING ---
    if is_recurring:
        logging.debug("🔄 Processing as RECURRING event")
        try:
            start_date = datetime.strptime(recurrence_start, "%Y-%m-%d")
            end_date = datetime.strptime(recurrence_end, "%Y-%m-%d")
            assert start_date <= end_date
        except Exception as e:
            conn.close()
            logging.error(f"❌ Recurrence date error: {e}")
            flash("❌ Invalid recurrence date range.", "error")
            return redirect(url_for("events"))

        recurrence_group = str(uuid4())
        logging.debug(f"Recurrence Group ID: {recurrence_group}")
        current_date = start_date

        while current_date <= end_date:
            cursor.execute('''
                INSERT INTO events (
                    eventName, eventDate, startTime, stopTime,
                    latitude, longitude, professorID,
                    isRecurring, recurrenceType, recurrenceStartDate,
                    recurrenceEndDate, recurrenceGroup, eventDescription
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_name,
                current_date.strftime("%Y-%m-%d"),
                start_time, stop_time,
                lat, lng, professor_id,
                True, recurrence_type,
                recurrence_start, recurrence_end,
                recurrence_group, event_description
            ))

            event_id = cursor.lastrowid
            logging.debug(f"✅ Inserted recurring event for {current_date.date()} (Event ID: {event_id})")
            get_or_create_qr_code(event_id)

            # Advance to next occurrence
            if recurrence_type == "daily":
                current_date += timedelta(days=1)
            elif recurrence_type == "weekly":
                current_date += timedelta(weeks=1)
            elif recurrence_type == "monthly":
                month = current_date.month + 1
                year = current_date.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                try:
                    current_date = current_date.replace(year=year, month=month)
                except ValueError:
                    current_date = current_date.replace(day=1, year=year, month=month) + timedelta(days=31)

        conn.commit()
        conn.close()
        logging.debug("✅ All recurring events committed successfully")
        return redirect(url_for("dashboard", recurring_created=1))

    # --- SINGLE EVENT HANDLING ---
    else:
        logging.debug("📅 Processing as single event")
        try:
            event_date_obj = datetime.strptime(event_date, "%Y-%m-%d")
        except Exception as e:
            conn.close()
            logging.error(f"❌ Invalid event date: {e}")
            flash("❌ Invalid event date.", "error")
            return redirect(url_for("events"))

        # Check for duplicate event at same time/location
        cursor.execute("""
            SELECT * FROM events 
            WHERE eventDate = ? 
            AND ROUND(latitude, 6) = ROUND(?, 6) 
            AND ROUND(longitude, 6) = ROUND(?, 6)
            AND (
                (? BETWEEN startTime AND stopTime) OR 
                (? BETWEEN startTime AND stopTime) OR 
                (startTime BETWEEN ? AND ?) OR 
                (stopTime BETWEEN ? AND ?)
            )
        """, (
            event_date, lat, lng,
            start_time, stop_time, start_time, stop_time, start_time, stop_time
        ))

        if cursor.fetchone():
            conn.close()
            logging.warning("❌ Duplicate detected at this time and location")
            flash("❌ Another event is already scheduled at this time and location.", "error")
            return redirect(url_for("events"))

        cursor.execute('''
            INSERT INTO events (
                eventName, eventDate, startTime, stopTime,
                latitude, longitude, professorID, eventDescription
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_name, event_date, start_time, stop_time, lat, lng, professor_id, event_description))

        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logging.debug(f"✅ Event {event_id} inserted successfully")

        get_or_create_qr_code(event_id)
        return redirect(url_for("dashboard", created=1))

@app.route("/api/my_events")
@login_required
def my_events():
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT eventID, eventName, eventDate, startTime, stopTime, professor_email_sent
        FROM events
        WHERE professorID = ?
        AND datetime(eventDate || ' ' || stopTime) <= datetime('now')
        ORDER BY datetime(eventDate || ' ' || stopTime) DESC
    """, (session["user_id"],)).fetchall()
    conn.close()

    events = []
    for row in rows:
        events.append({
            "eventID": row["eventID"],
            "eventName": row["eventName"],
            "eventDate": row["eventDate"],
            "startTime": row["startTime"],
            "stopTime": row["stopTime"],
            "emailSent": bool(row["professor_email_sent"])
        })
    return jsonify(events)

# Route: API endpoint for event list (returns JSON)
@app.route("/api/event/information", methods=["GET"])
@login_required
def get_event_information():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.eventID, e.eventName, e.eventDate, e.startTime, e.stopTime,
               e.latitude, e.longitude, e.recurrenceType, e.isRecurring,
               e.eventDescription,
               p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
    """)
    events = cursor.fetchall()
    conn.close()

    formatted_events = []

    for event in events:
        event_dict = dict(event)

        formatted_event = {
            "eventID": event_dict["eventID"],
            "eventName": event_dict["eventName"],
            "eventDate": event_dict["eventDate"],
            "startTime": event_dict["startTime"],
            "stopTime": event_dict["stopTime"],
            "latitude": event_dict["latitude"],
            "longitude": event_dict["longitude"],
            "recurrenceType": event_dict["recurrenceType"] if event_dict["isRecurring"] else None,
            "place_name": event_dict.get("place_name"),
            "building": event_dict.get("building"),
            "eventDescription": event_dict.get("eventDescription", "")
        }

        formatted_events.append(formatted_event)

    return jsonify(formatted_events)


@app.route("/edit_event/<int:event_id>", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        # Get updated form data
        name = request.form.get("event_name")
        description = request.form.get("event_description")
        date = request.form.get("event_date")
        start_time = request.form.get("start_time")
        stop_time = request.form.get("stop_time")
        latlng = request.form.get("event_location")
        lat, lng = map(float, latlng.split(","))

        # Combine datetime
        now = get_eastern_now()
        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        stop_dt = datetime.strptime(f"{date} {stop_time}", "%Y-%m-%d %H:%M")

        # Fetch event again for re-rendering if needed
        event = cursor.execute("""
            SELECT * FROM events WHERE eventID = ? AND professorID = ?
        """, (event_id, session["user_id"])).fetchone()

        error = None
        if start_dt <= now:
            error = "⛔ You cannot schedule an event that starts in the past."
        elif stop_dt <= now:
            error = "⛔ Event end time must be in the future."
        elif stop_dt <= start_dt:
            error = "⛔ End time must be after start time."

        if error:
            conn.close()
            return render_template("edit_event.html", event=event, error_message=error)

        # Otherwise, update the event
        cursor.execute("""
            UPDATE events
            SET eventName = ?, eventDescription = ?, eventDate = ?, startTime = ?, stopTime = ?, latitude = ?, longitude = ?
            WHERE eventID = ? AND professorID = ?
        """, (name, description, date, start_time, stop_time, lat, lng, event_id, session["user_id"]))
        conn.commit()
        conn.close()

        return redirect(url_for("dashboard", edited=1))

    # --- GET method logic ---
    event = cursor.execute("""
        SELECT * FROM events WHERE eventID = ? AND professorID = ?
    """, (event_id, session["user_id"])).fetchone()

    conn.close()

    if not event:
        return "Unauthorized or event not found", 403

    return render_template("edit_event.html", event=event)


@app.route("/delete_event/<int:event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if event has any student check-ins
    cursor.execute("SELECT COUNT(*) FROM student_checkins WHERE scannedEventID = ?", (event_id,))
    checkin_count = cursor.fetchone()[0]

    if checkin_count > 0:
        conn.close()
        flash("❌ Cannot delete this event because students have already checked in.", "error")
        return redirect(url_for("edit_event", event_id=event_id))

    # Proceed with deletion
    cursor.execute("DELETE FROM events WHERE eventID = ? AND professorID = ?", (event_id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard", deleted=1))


@app.route("/submit_place", methods=["POST"])
@login_required
def submit_place():
    data = request.json
    name = data.get("name")
    building = data.get("building")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not name or not building or not latitude or not longitude:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO places (name, building, latitude, longitude) VALUES (?, ?, ?, ?)",
        (name, building, latitude, longitude)
    )
    conn.commit()
    conn.close()

    # ✅ Return URL to redirect client to dashboard
    return jsonify({"success": True, "redirect_url": url_for("dashboard", place_created=1)})


# Route: Fetch all places
@app.route("/api/places", methods=["GET"])
@login_required
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
@login_required
def find_student():
    students = None  # Ensure we differentiate between no search and empty results

    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Adjust query based on the search fields being filled
        if first_name and last_name:
            query = '''
            SELECT sc.*, e.eventName, e.startTime, e.stopTime 
            FROM student_checkins sc
            LEFT JOIN events e ON sc.scannedEventID = e.eventID
            WHERE LOWER(sc.firstName) = LOWER(?) AND LOWER(sc.lastName) = LOWER(?)
            '''
            params = [first_name, last_name]
        elif first_name:
            query = '''
            SELECT sc.*, e.eventName, e.startTime, e.stopTime 
            FROM student_checkins sc
            LEFT JOIN events e ON sc.scannedEventID = e.eventID
            WHERE LOWER(sc.firstName) = LOWER(?)
            '''
            params = [first_name]
        elif last_name:
            query = '''
            SELECT sc.*, e.eventName, e.startTime, e.stopTime 
            FROM student_checkins sc
            LEFT JOIN events e ON sc.scannedEventID = e.eventID
            WHERE LOWER(sc.lastName) = LOWER(?)
            '''
            params = [last_name]
        else:
            query = '''
            SELECT sc.*, e.eventName, e.startTime, e.stopTime 
            FROM student_checkins sc
            LEFT JOIN events e ON sc.scannedEventID = e.eventID
            '''  # Show all students if nothing is filled

        cursor.execute(query, params)
        students = cursor.fetchall()
        conn.close()

    return render_template('find_student.html', students=students)


@app.template_filter('todatetime')
def todatetime_filter(value, format="%Y-%m-%d %H:%M"):
    return datetime.strptime(value, format)


@app.route("/event_info/<int:event_id>")
@login_required
def event_info(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    event = cursor.execute("""
        SELECT e.*, p.name AS place_name, p.building
        FROM events e
        LEFT JOIN places p ON e.latitude = p.latitude AND e.longitude = p.longitude
        WHERE e.eventID = ?
    """, (event_id,)).fetchone()
    conn.close()

    if not event:
        return "Event not found", 404

    # Pass current datetime as a string to match format in Jinja
    return render_template("event_info.html", event=event, now=get_eastern_now().strftime("%Y-%m-%d %H:%M"))

@app.route('/init-db')
def init_db_route():
    from init_db import create_tables, seed_professors_and_courses

    create_tables()
    seed_professors_and_courses()

    return "Database initialized!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
