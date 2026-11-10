"""HTTP integration tests for the A4 patient-to-queue vertical slice.

All identities, appointments and timestamps are synthetic. The clock is fixed
per test to make boundary behaviour deterministic.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


class VerticalSliceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "test.sqlite3")
        self.now = [datetime(2026, 11, 10, 8, 30, tzinfo=timezone.utc)]
        self.app = create_app(self.db, clock=lambda: self.now[0])
        self.client = TestClient(self.app)
        self.patient = self.login("patient", "PatientDemo!2026")
        self.reception = self.login("reception", "ReceptionDemo!2026")

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def login(self, username, password):
        response = self.client.post("/api/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def create_appointment(self, token=None, start="2026-11-10T09:00:00+00:00", end="2026-11-10T11:00:00+00:00"):
        response = self.client.post("/api/appointments", headers=self.auth(token or self.patient), json={
            "clinic_code": "CLINIC-A", "window_start": start, "window_end": end
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def checkin(self, appointment_id, key="request-001", token=None):
        return self.client.post(
            f"/api/appointments/{appointment_id}/check-in",
            headers={**self.auth(token or self.patient), "Idempotency-Key": key}, json={}
        )

    def create_ticket(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 9, 30, tzinfo=timezone.utc)
        response = self.checkin(appointment["id"])
        self.assertEqual(response.status_code, 200, response.text)
        return appointment, response.json()["ticket"]

    def test_01_health_endpoint(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_02_interface_is_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Clinic Arrival &amp; Queue", response.text.replace("&", "&amp;"))

    def test_03_patient_login_returns_bearer_token(self):
        result = self.client.post("/api/login", json={"username": "patient", "password": "PatientDemo!2026"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["user"]["role"], "patient")
        self.assertEqual(result.json()["token_type"], "bearer")

    def test_04_invalid_password_is_rejected(self):
        result = self.client.post("/api/login", json={"username": "patient", "password": "wrong"})
        self.assertEqual(result.status_code, 401)

    def test_05_appointment_can_be_created(self):
        appointment = self.create_appointment()
        self.assertEqual(appointment["state"], "CONFIRMED")
        self.assertEqual(appointment["clinic_code"], "CLINIC-A")

    def test_06_appointment_creation_requires_authentication(self):
        result = self.client.post("/api/appointments", json={"clinic_code": "CLINIC-A", "window_start": "2026-11-10T09:00:00Z", "window_end": "2026-11-10T11:00:00Z"})
        self.assertEqual(result.status_code, 401)

    def test_07_receptionist_cannot_create_patient_booking(self):
        result = self.client.post("/api/appointments", headers=self.auth(self.reception), json={"clinic_code": "CLINIC-A", "window_start": "2026-11-10T09:00:00Z", "window_end": "2026-11-10T11:00:00Z"})
        self.assertEqual(result.status_code, 403)

    def test_08_owner_can_view_appointment(self):
        appointment = self.create_appointment()
        result = self.client.get(f"/api/appointments/{appointment['id']}", headers=self.auth(self.patient))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["id"], appointment["id"])

    def test_09_other_patient_cannot_view_appointment(self):
        appointment = self.create_appointment()
        # Create a second synthetic patient/token directly in this isolated test database.
        import sqlite3, hashlib, secrets
        salt = secrets.token_bytes(16); digest = hashlib.pbkdf2_hmac("sha256", b"OtherDemo!2026", salt, 260_000)
        db = sqlite3.connect(self.db)
        try:
            db.execute("INSERT INTO users(username,password_salt,password_hash,role) VALUES(?,?,?,?)", ("other_patient",salt.hex(),digest.hex(),"patient"))
            user_id = db.execute("SELECT id FROM users WHERE username='other_patient'").fetchone()[0]
            raw = "other-test-token"
            db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (hashlib.sha256(raw.encode()).hexdigest(),user_id,"2026-11-10T16:30:00+00:00"))
            db.commit()
        finally:
            db.close()
        result = self.client.get(f"/api/appointments/{appointment['id']}", headers=self.auth(raw))
        self.assertEqual(result.status_code, 403)

    def test_10_receptionist_can_view_appointment(self):
        appointment = self.create_appointment()
        result = self.client.get(f"/api/appointments/{appointment['id']}", headers=self.auth(self.reception))
        self.assertEqual(result.status_code, 200)

    def test_11_checkin_creates_one_waiting_ticket(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 9, 20, tzinfo=timezone.utc)
        result = self.checkin(appointment["id"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["appointment"]["state"], "CHECKED_IN")
        self.assertEqual(result.json()["ticket"]["state"], "WAITING")

    def test_12_checkin_before_window_is_rejected(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 8, 59, tzinfo=timezone.utc)
        self.assertEqual(self.checkin(appointment["id"]).status_code, 409)

    def test_13_start_boundary_is_inclusive(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(self.checkin(appointment["id"]).status_code, 200)

    def test_14_end_boundary_is_exclusive(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 11, 0, tzinfo=timezone.utc)
        self.assertEqual(self.checkin(appointment["id"]).status_code, 409)

    def test_15_idempotency_header_is_required(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 9, 30, tzinfo=timezone.utc)
        result = self.client.post(f"/api/appointments/{appointment['id']}/check-in", headers=self.auth(self.patient), json={})
        self.assertEqual(result.status_code, 422)

    def test_16_same_idempotency_key_replays_same_ticket(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 9, 30, tzinfo=timezone.utc)
        first = self.checkin(appointment["id"], "same-key")
        second = self.checkin(appointment["id"], "same-key")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["ticket"]["id"], second.json()["ticket"]["id"])

    def test_17_new_key_cannot_create_second_ticket(self):
        appointment = self.create_appointment()
        self.now[0] = datetime(2026, 11, 10, 9, 30, tzinfo=timezone.utc)
        self.assertEqual(self.checkin(appointment["id"], "first").status_code, 200)
        self.assertEqual(self.checkin(appointment["id"], "second").status_code, 409)

    def test_18_patient_cannot_view_staff_queue(self):
        self.assertEqual(self.client.get("/api/staff/queue?clinic_code=CLINIC-A", headers=self.auth(self.patient)).status_code, 403)

    def test_19_receptionist_can_view_queue_using_china_local_date(self):
        appointment = self.create_appointment(
            start="2026-11-11T08:00:00+08:00", end="2026-11-11T10:00:00+08:00"
        )
        # 00:30 UTC is 08:30 on the same day in Asia/Shanghai.
        self.now[0] = datetime(2026, 11, 11, 0, 30, tzinfo=timezone.utc)
        # Refresh sessions because the test clock has moved beyond the 8-hour expiry.
        self.patient = self.login("patient", "PatientDemo!2026")
        self.reception = self.login("reception", "ReceptionDemo!2026")
        checked = self.checkin(appointment["id"])
        self.assertEqual(checked.status_code, 200, checked.text)
        result = self.client.get("/api/staff/queue?clinic_code=CLINIC-A", headers=self.auth(self.reception))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["service_date"], "2026-11-11")
        self.assertEqual(len(result.json()["tickets"]), 1)

    def test_20_patient_cannot_call_ticket(self):
        _, ticket = self.create_ticket()
        result = self.client.post(f"/api/staff/tickets/{ticket['id']}/call", headers={**self.auth(self.patient), "If-Match": "1"}, json={})
        self.assertEqual(result.status_code, 403)

    def test_21_receptionist_can_call_ticket(self):
        _, ticket = self.create_ticket()
        result = self.client.post(f"/api/staff/tickets/{ticket['id']}/call", headers={**self.auth(self.reception), "If-Match": "1"}, json={})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["state"], "CALLED")
        self.assertEqual(result.json()["version"], 2)

    def test_22_call_requires_if_match(self):
        _, ticket = self.create_ticket()
        result = self.client.post(f"/api/staff/tickets/{ticket['id']}/call", headers=self.auth(self.reception), json={})
        self.assertEqual(result.status_code, 428)

    def test_23_stale_version_is_rejected(self):
        _, ticket = self.create_ticket()
        self.client.post(f"/api/staff/tickets/{ticket['id']}/call", headers={**self.auth(self.reception), "If-Match": "1"}, json={})
        result = self.client.post(f"/api/staff/tickets/{ticket['id']}/call", headers={**self.auth(self.reception), "If-Match": "1"}, json={})
        self.assertEqual(result.status_code, 412)

    def test_24_already_called_ticket_cannot_be_called_again(self):
        _, ticket = self.create_ticket()
        self.client.post(f"/api/staff/tickets/{ticket['id']}/call", headers={**self.auth(self.reception), "If-Match": "1"}, json={})
        result = self.client.post(f"/api/staff/tickets/{ticket['id']}/call", headers={**self.auth(self.reception), "If-Match": "2"}, json={})
        self.assertEqual(result.status_code, 409)


if __name__ == "__main__":
    unittest.main(verbosity=2)
