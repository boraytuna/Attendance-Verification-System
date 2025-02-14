from flask import Flask, render_template, request, redirect, jsonify
import sqlite3

app = Flask(__name__)
DATABASE_NAME = "attendance.db"

# Connect to SQLite
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
    return conn

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

# Route: Handle Event Creation
@app.route("/submit_event", methods=["POST"])
def submit_event():
    event_name = request.form["event_name"]
    event_date = request.form["event_date"]
    start_time = request.form["start_time"]
    stop_time = request.form["stop_time"]
    event_location = request.form["event_location"]  # Will be "lat,lng"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (eventName, eventDate, startTime, stopTime, eventLocation)
        VALUES (?, ?, ?, ?, ?)
    ''', (event_name, event_date, start_time, stop_time, event_location))
    conn.commit()
    conn.close()

    return redirect("/events")

# Route: API endpoint for event list (returns JSON)
@app.route("/api/events", methods=["GET"])
def get_events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT eventID, eventName, eventDate, startTime, stopTime, eventLocation FROM events")
    events = cursor.fetchall()
    conn.close()

    events_list = [dict(event) for event in events]
    return jsonify(events_list)

if __name__ == "__main__":
    app.run(debug=True)

