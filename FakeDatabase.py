import sqlite3

# Create a connection to the database (it will be created if it doesn't exist)
conn = sqlite3.connect('fake.db')
cursor = conn.cursor()

# Create Professor table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Professor (
    professor_id INTEGER PRIMARY KEY,
    professor_name TEXT NOT NULL
)
''')

# Create Courses table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Courses (
    course_id INTEGER PRIMARY KEY,
    course_name TEXT NOT NULL
)
''')

# Insert normal professor values
professors = [
    (1, 'Dr. John Smith'),
    (2, 'Dr. Emily Johnson'),
    (3, 'Dr. Michael Brown'),
    (4, 'Dr. Sarah Lee'),
    (5, 'Dr. David Wilson')
]
cursor.executemany('INSERT INTO Professor (professor_id, professor_name) VALUES (?, ?)', professors)

# Insert normal course values
courses = [
    (1, 'Introduction to Computer Science'),
    (2, 'Calculus I'),
    (3, 'Physics for Engineers'),
    (4, 'Data Structures and Algorithms'),
    (5, 'Linear Algebra')
]
cursor.executemany('INSERT INTO Courses (course_id, course_name) VALUES (?, ?)', courses)

# Commit the changes
conn.commit()

# Fetch and display the inserted data for verification
cursor.execute('SELECT * FROM Professor')
professors_data = cursor.fetchall()
print("Professors:")
for professor in professors_data:
    print(professor)

cursor.execute('SELECT * FROM Courses')
courses_data = cursor.fetchall()
print("\nCourses:")
for course in courses_data:
    print(course)

# Close the connection
conn.close()
