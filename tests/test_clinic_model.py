import unittest
from datetime import datetime, timedelta, timezone
from src.clinic_model import (
    Appointment, AppointmentState, CheckInDecision, QueueTicket, TicketState,
    TimeWindow, appointment_violations, can_issue_ticket, can_record_no_show,
    decide_check_in, duplicate_active_ticket_appointments,
    ticket_registry_violations, ticket_transition_allowed,
)

CN = timezone(timedelta(hours=8))
def at(h, m=0): return datetime(2026, 10, 12, h, m, tzinfo=CN)
def window(): return TimeWindow(at(9), at(11))
def appointment(state=AppointmentState.CONFIRMED, checked=None, no_show=None):
    return Appointment("A-001", state, window(), at(8), checked, no_show)
def ticket(ticket_id="T-1", appointment_id="A-001", state=TicketState.WAITING, number="Q-001", session="S-1"):
    return QueueTicket(ticket_id, appointment_id, number, state, at(9, 10), session)

class TestInvariantI1Window(unittest.TestCase):
    def test_valid_positive_window(self): self.assertTrue(window().is_valid())
    def test_zero_length_window_rejected(self): self.assertFalse(TimeWindow(at(9), at(9)).is_valid())
    def test_reversed_window_rejected(self): self.assertFalse(TimeWindow(at(11), at(9)).is_valid())
    def test_naive_timestamp_rejected(self): self.assertFalse(TimeWindow(datetime(2026,10,12,9), at(11)).is_valid())
    def test_contains_uses_start_inclusive_end_exclusive(self):
        self.assertTrue(window().contains(at(9)))
        self.assertFalse(window().contains(at(11)))

class TestCheckInDecisionTable(unittest.TestCase):
    def test_too_early(self): self.assertEqual(decide_check_in(window(), AppointmentState.CONFIRMED, at(8,59)), CheckInDecision.TOO_EARLY)
    def test_start_boundary_accepted(self): self.assertEqual(decide_check_in(window(), AppointmentState.CONFIRMED, at(9)), CheckInDecision.ACCEPT_CHECK_IN)
    def test_inside_window_accepted(self): self.assertEqual(decide_check_in(window(), AppointmentState.CONFIRMED, at(10,15)), CheckInDecision.ACCEPT_CHECK_IN)
    def test_window_end_routes_to_late_review(self): self.assertEqual(decide_check_in(window(), AppointmentState.CONFIRMED, at(11)), CheckInDecision.LATE_REVIEW)
    def test_pre_grace_end_routes_to_late_review(self): self.assertEqual(decide_check_in(window(), AppointmentState.CONFIRMED, at(11,14,)), CheckInDecision.LATE_REVIEW)
    def test_grace_threshold_makes_no_show_eligible_not_automatic(self): self.assertEqual(decide_check_in(window(), AppointmentState.CONFIRMED, at(11,15)), CheckInDecision.NO_SHOW_ELIGIBLE)
    def test_cancelled_rejected(self): self.assertEqual(decide_check_in(window(), AppointmentState.CANCELLED, at(9,30)), CheckInDecision.REJECT_CANCELLED)
    def test_repeat_checkin_is_idempotent_decision(self): self.assertEqual(decide_check_in(window(), AppointmentState.CHECKED_IN, at(9,30)), CheckInDecision.ALREADY_CHECKED_IN)
    def test_completed_is_closed(self): self.assertEqual(decide_check_in(window(), AppointmentState.COMPLETED, at(9,30)), CheckInDecision.REJECT_CLOSED)
    def test_naive_current_time_raises(self):
        with self.assertRaises(ValueError): decide_check_in(window(), AppointmentState.CONFIRMED, datetime(2026,10,12,9))
    def test_negative_grace_raises(self):
        with self.assertRaises(ValueError): decide_check_in(window(), AppointmentState.CONFIRMED, at(9), -1)

class TestInvariantI2AppointmentCoherence(unittest.TestCase):
    def test_confirmed_without_checkin_is_valid(self): self.assertEqual(appointment_violations(appointment()), [])
    def test_checkedin_without_timestamp_violates(self): self.assertTrue(appointment_violations(appointment(AppointmentState.CHECKED_IN)))
    def test_checkedin_with_timestamp_is_valid(self): self.assertEqual(appointment_violations(appointment(AppointmentState.CHECKED_IN, at(9,30))), [])
    def test_noshow_with_checkin_violates(self): self.assertTrue(appointment_violations(appointment(AppointmentState.NO_SHOW, at(9,30), at(11,20))))
    def test_noshow_before_grace_violates(self): self.assertTrue(appointment_violations(appointment(AppointmentState.NO_SHOW, None, at(11,14))))
    def test_noshow_after_grace_without_checkin_is_coherent(self): self.assertEqual(appointment_violations(appointment(AppointmentState.NO_SHOW, None, at(11,15))), [])

class TestInvariantI3Tickets(unittest.TestCase):
    def test_single_active_ticket_has_no_duplicate_violation(self): self.assertEqual(duplicate_active_ticket_appointments([ticket()]), set())
    def test_two_active_tickets_for_one_booking_violate(self):
        ts = [ticket("T-1", number="Q-001"), ticket("T-2", number="Q-002")]
        self.assertEqual(duplicate_active_ticket_appointments(ts), {"A-001"})
        self.assertTrue(ticket_registry_violations(ts))
    def test_withdrawn_ticket_does_not_count_as_active(self):
        ts = [ticket("T-1", state=TicketState.WITHDRAWN, number="Q-001"), ticket("T-2", number="Q-002")]
        self.assertEqual(duplicate_active_ticket_appointments(ts), set())
    def test_ticket_issuance_requires_accepted_checkin(self): self.assertFalse(can_issue_ticket(appointment(), []))
    def test_ticket_issuance_allowed_once_after_checkin(self):
        a = appointment(AppointmentState.CHECKED_IN, at(9,5))
        self.assertTrue(can_issue_ticket(a, []))
        self.assertFalse(can_issue_ticket(a, [ticket()]))
    def test_queue_number_unique_per_session(self):
        ts = [ticket("T-1", "A-001", number="Q-001"), ticket("T-2", "A-002", number="Q-001")]
        self.assertIn("queue_number must be unique within a session", ticket_registry_violations(ts))

class TestInvariantI4NoShowAuthorization(unittest.TestCase):
    def test_authorized_after_threshold_allowed(self): self.assertTrue(can_record_no_show(appointment(), at(11,15), "receptionist"))
    def test_before_threshold_not_allowed(self): self.assertFalse(can_record_no_show(appointment(), at(11,14), "receptionist"))
    def test_unauthorized_role_not_allowed(self): self.assertFalse(can_record_no_show(appointment(), at(11,15), "patient"))
    def test_checkedin_appointment_cannot_be_noshow(self): self.assertFalse(can_record_no_show(appointment(AppointmentState.CHECKED_IN, at(9,5)), at(11,15), "receptionist"))

class TestInvariantI5TicketTransitions(unittest.TestCase):
    def test_waiting_to_called_allowed(self): self.assertTrue(ticket_transition_allowed(TicketState.WAITING, TicketState.CALLED))
    def test_called_back_to_waiting_allowed_as_recall_correction(self): self.assertTrue(ticket_transition_allowed(TicketState.CALLED, TicketState.WAITING))
    def test_finished_to_waiting_forbidden(self): self.assertFalse(ticket_transition_allowed(TicketState.FINISHED, TicketState.WAITING))
    def test_withdrawn_is_terminal(self): self.assertFalse(ticket_transition_allowed(TicketState.WITHDRAWN, TicketState.CALLED))

if __name__ == "__main__": unittest.main(verbosity=2)
