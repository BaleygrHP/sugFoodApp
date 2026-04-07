from enum import Enum


class Channel(str, Enum):
    CHAT = 'Chat'
    EMAIL = 'Email'


class WorkflowMode(str, Enum):
    """Workflow execution mode - shared across workflows"""
    DRAFT = "DRAFT"
    AUTO_RESPONSE = "AUTO_RESPONSE"
    PLAYGROUND = "PLAYGROUND"
