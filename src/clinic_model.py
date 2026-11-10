"""Reference specification for the ISE-A2 clinic appointment workflow.

Uses synthetic/test values only. It is not production clinical software.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from collections import Counter


class AppointmentState(str, Enum):
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    COMPLETED = "COMPLETED"


class TicketState(str, Enum):
    WAITING = "WAITING"
    CALLED = "CALLED"
    IN_CONSULTATION = "IN_CONSULTATION"
    FINISHED = "FINISHED"
    WITHDRAWN = "WITHDRAWN"


class CheckInDecision(str, Enum):
    TOO_EARLY = "TOO_EARLY"
    ACCEPT_CHECK_IN = "ACCEPT_CHECK_IN"
    LATE_REVIEW = "LATE_REVIEW"
    NO_SHOW_ELIGIBLE = "NO_SHOW_ELIGIBLE"
    REJECT_CANCELLED = "REJECT_CANCELLED"
    ALREADY_CHECKED_IN = "ALREADY_CHECKED_IN"
    REJECT_CLOSED = "REJECT_CLOSED"


ACTIVE_TICKET_STATES = {TicketState.WAITING, TicketState.CALLED, TicketState.IN_CONSULTATION}
ALLOWED_NO_SHOW_ROLES = {"receptionist", "queue_supervisor", "clinic_manager"}
GRACE_MINUTES_DEFAULT = 15  # Explicit prototype assumption; clinic must configure/approve.


def is_aware(value: datetime | None) -> bool:
    return value is not None and value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime

    def is_valid(self) -> bool:
        return is_aware(self.start) and is_aware(self.end) and self.start < self.end

    def contains(self, instant: datetime) -> bool:
        if not self.is_valid():
            raise ValueError("Invalid appointment time window")
        if not is_aware(instant):
            raise ValueError("The timestamp must be timezone-aware")
        return self.start <= instant < self.end  # Half-open [start, end).


@dataclass(frozen=True)
class Appointment:
    appointment_id: str
    state: AppointmentState
    window: TimeWindow
    created_at: datetime
    checked_in_at: datetime | None = None
    no_show_recorded_at: datetime | None = None


@dataclass(frozen=True)
class QueueTicket:
    ticket_id: str
    appointment_id: str
    queue_number: str
    state: TicketState
    issued_at: datetime
    session_id: str

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_TICKET_STATES


def appointment_violations(a: Appointment, grace_minutes: int = GRACE_MINUTES_DEFAULT) -> list[str]:
    """Return all detectable violations of appointment state/time coherence."""
    issues: list[str] = []
    if not a.appointment_id.strip():
        issues.append("appointment_id must be non-empty")
    if not a.window.is_valid():
        issues.append("window must have aware timestamps and positive duration")
    if not is_aware(a.created_at):
        issues.append("created_at must be timezone-aware")
    elif is_aware(a.checked_in_at) and a.checked_in_at < a.created_at:
        issues.append("checked_in_at cannot precede created_at")
    if a.state in {AppointmentState.CHECKED_IN, AppointmentState.COMPLETED} and not is_aware(a.checked_in_at):
        issues.append("CHECKED_IN/COMPLETED requires checked_in_at")
    if a.state in {AppointmentState.CONFIRMED, AppointmentState.CANCELLED, AppointmentState.NO_SHOW} and a.checked_in_at is not None:
        issues.append("CONFIRMED/CANCELLED/NO_SHOW cannot have checked_in_at")
    if a.state is AppointmentState.NO_SHOW:
        if not is_aware(a.no_show_recorded_at):
            issues.append("NO_SHOW requires an aware no_show_recorded_at")
        elif a.window.is_valid() and a.no_show_recorded_at < a.window.end + timedelta(minutes=grace_minutes):
            issues.append("NO_SHOW cannot be recorded before window end plus grace")
    if a.state is not AppointmentState.NO_SHOW and a.no_show_recorded_at is not None:
        issues.append("no_show_recorded_at is only valid for NO_SHOW")
    return issues


def duplicate_active_ticket_appointments(tickets: list[QueueTicket]) -> set[str]:
    counts = Counter(t.appointment_id for t in tickets if t.is_active)
    return {appointment_id for appointment_id, count in counts.items() if count > 1}


def ticket_registry_violations(tickets: list[QueueTicket]) -> list[str]:
    issues: list[str] = []
    ticket_ids = [t.ticket_id for t in tickets]
    if len(ticket_ids) != len(set(ticket_ids)):
        issues.append("ticket_id must be unique")
    if any(not t.ticket_id.strip() or not t.appointment_id.strip() for t in tickets):
        issues.append("ticket_id and appointment_id must be non-empty")
    if duplicate_active_ticket_appointments(tickets):
        issues.append("at most one active ticket is permitted per appointment")
    queue_keys = [(t.session_id, t.queue_number) for t in tickets]
    if len(queue_keys) != len(set(queue_keys)):
        issues.append("queue_number must be unique within a session")
    if any(not is_aware(t.issued_at) for t in tickets):
        issues.append("issued_at must be timezone-aware")
    return issues


def can_issue_ticket(a: Appointment, existing: list[QueueTicket]) -> bool:
    """Ticket creation is permitted only after recorded check-in and with no active ticket."""
    return (
        a.state is AppointmentState.CHECKED_IN
        and is_aware(a.checked_in_at)
        and not appointment_violations(a)
        and a.appointment_id not in duplicate_active_ticket_appointments(existing)
        and not any(t.appointment_id == a.appointment_id and t.is_active for t in existing)
    )


def decide_check_in(
    window: TimeWindow,
    state: AppointmentState,
    now: datetime,
    grace_minutes: int = GRACE_MINUTES_DEFAULT,
) -> CheckInDecision:
    """Pure decision function. It does not mutate appointments or issue tickets."""
    if not window.is_valid():
        raise ValueError("Invalid appointment time window")
    if not is_aware(now):
        raise ValueError("Current time must be timezone-aware")
    if grace_minutes < 0:
        raise ValueError("grace_minutes must be >= 0")
    if state is AppointmentState.CANCELLED:
        return CheckInDecision.REJECT_CANCELLED
    if state is AppointmentState.CHECKED_IN:
        return CheckInDecision.ALREADY_CHECKED_IN
    if state in {AppointmentState.NO_SHOW, AppointmentState.COMPLETED}:
        return CheckInDecision.REJECT_CLOSED
    if now < window.start:
        return CheckInDecision.TOO_EARLY
    if now < window.end:
        return CheckInDecision.ACCEPT_CHECK_IN
    if now < window.end + timedelta(minutes=grace_minutes):
        return CheckInDecision.LATE_REVIEW
    return CheckInDecision.NO_SHOW_ELIGIBLE


def can_record_no_show(
    a: Appointment,
    now: datetime,
    actor_role: str,
    grace_minutes: int = GRACE_MINUTES_DEFAULT,
) -> bool:
    """No-show is a staff-authorised reconciliation, never an automatic UI side effect."""
    if not a.window.is_valid() or not is_aware(now) or grace_minutes < 0:
        return False
    return (
        a.state is AppointmentState.CONFIRMED
        and a.checked_in_at is None
        and now >= a.window.end + timedelta(minutes=grace_minutes)
        and actor_role in ALLOWED_NO_SHOW_ROLES
        and not appointment_violations(a, grace_minutes)
    )


_ALLOWED_TICKET_TRANSITIONS = {
    TicketState.WAITING: {TicketState.CALLED, TicketState.WITHDRAWN},
    TicketState.CALLED: {TicketState.IN_CONSULTATION, TicketState.WAITING, TicketState.WITHDRAWN},
    TicketState.IN_CONSULTATION: {TicketState.FINISHED},
    TicketState.FINISHED: set(),
    TicketState.WITHDRAWN: set(),
}


def ticket_transition_allowed(current: TicketState, target: TicketState) -> bool:
    return target in _ALLOWED_TICKET_TRANSITIONS[current]
