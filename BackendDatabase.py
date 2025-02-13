import sqlite3

DATABASE_NAME = "attendance.db"

# Function to connect to SQLite
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Enables dictionary-style access
    return conn

# Function to create tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Events Table (Professor Input)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            eventID INTEGER PRIMARY KEY AUTOINCREMENT,
            eventName TEXT NOT NULL,
            eventDate DATE NOT NULL,
            startTime TIME NOT NULL,
            stopTime TIME NOT NULL,
            eventLocation TEXT NOT NULL
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

# Run table creation when script is executed
if __name__ == "__main__":
    create_tables()
    print("Database initialized successfully!")