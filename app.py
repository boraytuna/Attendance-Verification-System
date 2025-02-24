from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

def query_db(query, args=(), one=False):
    """Helper function to query the SQLite database."""
    conn = sqlite3.connect('fake.db')  # Ensure this matches your database
    cursor = conn.cursor()
    cursor.execute(query, args)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return (results[0] if results else None) if one else results

@app.route('/search_courses', methods=['GET'])
def search_courses():
    """Search for courses based on user input."""
    search_term = request.args.get('query', '')
    results = query_db("SELECT course_name FROM Courses WHERE course_name LIKE ?", (f"%{search_term}%",))
    return jsonify([row[0] for row in results])

@app.route('/search_professors', methods=['GET'])
def search_professors():
    """Search for professors based on user input."""
    search_term = request.args.get('query', '')
    results = query_db("SELECT professor_name FROM Professor WHERE professor_name LIKE ?", (f"%{search_term}%",))
    return jsonify([row[0] for row in results])

@app.route('/student-interface/<int:page>')
def student_interface(page):
    """Serve the student interface pages."""
    return render_template(f'student{page}.html')

if __name__ == '__main__':
    app.run(debug=True)
