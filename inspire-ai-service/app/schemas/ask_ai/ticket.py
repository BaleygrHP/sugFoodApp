from pydantic import BaseModel
from app.services.ask_ai.constants.ticket import TicketStatus, TicketPriority

class Ticket(BaseModel):
    status: TicketStatus
    priority: TicketPriority
    body: str
