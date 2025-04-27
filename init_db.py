import sqlite3
import pandas as pd
import os

# DB setup
DATABASE_NAME = "attendance.db"
EXCEL_SOURCE = "CSV-Files/prof_names.xlsx"
COURSE_SOURCE = "CSV-Files/cleaned_course_names.xlsx"

# Helper: Connect to DB
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Step 1: Create all necessary tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            userID INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            eventID INTEGER PRIMARY KEY AUTOINCREMENT,
            eventName TEXT NOT NULL,
            eventDate DATE NOT NULL,
            startTime TIME NOT NULL,
            stopTime TIME NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            professorID INTEGER NOT NULL,
            professor_email_sent INTEGER,
            isRecurring BOOLEAN DEFAULT 0,
            recurrenceType TEXT,
            recurrenceStartDate DATE,
            recurrenceEndDate DATE,
            recurrenceGroup TEXT,
            eventDescription TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_checkins (
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS places (
            placeID INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            building TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professors (
            professor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_name TEXT NOT NULL,
            professor_email TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("[✅ TABLES CREATED] All necessary tables are now set up.")

# Step 2: Optional seeding from spreadsheet
def seed_professors_and_courses():
    if not os.path.exists(EXCEL_SOURCE):
        print("[⚠️ WARNING] Excel file not found. Skipping professor seeding.")
    else:
        df = pd.read_excel(EXCEL_SOURCE)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM professors")
        for _, row in df.iterrows():
            full_name = f"Dr. {row['First Name']} {row['Last Name']}"
            email = row['Email']
            cursor.execute("INSERT INTO professors (professor_name, professor_email) VALUES (?, ?)", (full_name, email))
        conn.commit()
        conn.close()
        print("[📥 SEEDED] Professors have been added to the database.")

    if not os.path.exists(COURSE_SOURCE):
        print("[⚠️ WARNING] Course Excel file not found. Skipping course seeding.")
    else:
        df = pd.read_excel(COURSE_SOURCE)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM courses")
        for course in df["Course Name"]:
            cursor.execute("INSERT INTO courses (course_name) VALUES (?)", (course,))

        conn.commit()
        conn.close()
        print("[📥 SEEDED] Courses have been added to the database.")

# Run setup
if __name__ == "__main__":
    create_tables()
    seed_professors_and_courses()
