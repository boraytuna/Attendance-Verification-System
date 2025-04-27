import unittest
from unittest.mock import patch, MagicMock
import json
from app import app, get_db_connection

class AttendanceAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def register_user(self, email="testuser@example.com"):
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
        email = "newtestuser@example.com"
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

    """
    Test student check-in functionality.
    """
    def checkin_student(self):
        return self.app.post('/submit_student_checkin', json={
            'firstName': 'Test',
            'lastName': 'User',
            'email': 'testuser@example.com',
            'scannedEventID': '1',
            'studentLocation': 'Test Location',
            'deviceId': '12345',
            'courses': [
                {
                    'className': 'Test Course',
                    'professorName': 'Test Professor'
                }
            ]
        })
    
    def test_student_checkin(self):
        response = self.checkin_student()
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(data['status'], 'success')

if __name__ == '__main__':
    unittest.main()
