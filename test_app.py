import unittest
from unittest.mock import patch, MagicMock
import json
import uuid
from app import app, get_db_connection

class AttendanceAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Seed test professor to database for test reliability
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO professors (professor_name, professor_email)
            VALUES (?, ?)
        """, ("Dr. Demo Tester", "your.email@domain.com"))
        conn.commit()
        conn.close()

    def register_user(self, email=None):
        if not email:
            email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        return self.app.post("/submit_signup", json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "password123"
        })

    def login_user(self, email="testuser@example.com"):
        return self.app.post("/submit_login", json={
            "email": email,
            "password": "password123"
        })

    def test_signup_and_login(self):
        email = f"newtestuser_{uuid.uuid4().hex[:8]}@example.com"
        response = self.register_user(email)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])

        login_response = self.login_user(email)
        self.assertEqual(login_response.status_code, 200)
        login_data = json.loads(login_response.data)
        self.assertTrue(login_data['success'])

    def test_protected_dashboard_redirect(self):
        response = self.app.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers['Location'])

    def test_event_api_requires_login(self):
        response = self.app.get("/api/my_events", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_landing_page_loads(self):
        response = self.app.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<!DOCTYPE html", response.data)

    def test_student_checkin(self):
        with self.app as client:
            email = f"student_{uuid.uuid4().hex[:8]}@example.com"
            device_id = uuid.uuid4().hex[:12]  # randomized to avoid conflicts

            response = client.post('/submit_student_checkin', json={
                'firstName': 'Test',
                'lastName': 'User',
                'email': email,
                'scannedEventID': '1',
                'studentLocation': 'Test Location',
                'deviceId': device_id,
                'courses': [
                    {
                        'className': 'Test Course',
                        'professorName': 'Dr. Demo Tester'
                    }
                ]
            })

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIsNotNone(data)
            self.assertEqual(data['status'], 'success')

    def test_demo_professor_exists(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        result = cursor.execute("SELECT * FROM professors WHERE professor_email = ?", ("your.email@domain.com",)).fetchone()
        conn.close()
        self.assertIsNotNone(result)
        self.assertEqual(result["professor_name"], "Dr. Demo Tester")

    def test_search_professors_api(self):
        response = self.app.get('/search_professors?query=Demo')
        self.assertEqual(response.status_code, 200)
        results = response.get_json()
        self.assertTrue(any("Dr. Demo Tester" in r for r in results))

if __name__ == '__main__':
    unittest.main()