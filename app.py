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

# Route: Professor Dashboard
@app.route("/professor_dashboard", methods=["GET"])
def professor_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    conn.close()
    return render_template("professor_dashboard.html", events=events)

# Route: Handle Event Creation
@app.route("/submit_event", methods=["POST"])
def submit_event():
    # Retrieve form data
    event_name = request.form["event_name"]
    event_date = request.form["event_date"]
    start_time = request.form["start_time"]
    stop_time = request.form["stop_time"]
    event_location = request.form["event_location"]

    # Insert event into the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (eventName, eventDate, startTime, stopTime, eventLocation)
        VALUES (?, ?, ?, ?, ?)
    ''', (event_name, event_date, start_time, stop_time, event_location))
    conn.commit()
    conn.close()

    return redirect("/professor_dashboard")

# Route: API endpoint for event list
@app.route("/api/events", methods=["GET"])
def get_events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    conn.close()

    events_list = [dict(event) for event in events]
    return jsonify(events_list)

if __name__ == "__main__":
    app.run(debug=True)