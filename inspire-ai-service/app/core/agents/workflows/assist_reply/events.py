from llama_index.core.workflow import Event
from app.services.ask_ai.constants.ticket import TicketPriority


class ProgressEvent(Event):
    msg: str


class TicketTriageEvent(Event):
    should_reactivate: bool
    should_skip: bool
    skip_reason: str
    priority_level: TicketPriority
    confidence: float
    current_ticket_status: str


class AnswerQuestionEvent(Event):
    triage_info: TicketTriageEvent
