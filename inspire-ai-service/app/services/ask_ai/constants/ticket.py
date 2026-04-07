from enum import Enum

class TicketStatus(str, Enum):
    UNASSIGNED = 'UNASSIGNED'
    OPEN = 'OPEN'
    PENDING = 'PENDING'
    SOLVED = 'SOLVED'
    AI_SERVING = 'AI_SERVING'

class TicketPriority(str, Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
