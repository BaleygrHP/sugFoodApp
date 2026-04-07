import re
import dirtyjson
from llama_index.core import Settings
from .constants.ticket_analyze_constant import (
    TicketAnalyzeInstructions,
    Tone,
    Satisfaction,
    Potential,
    AgentTone,
    Urgency
)
from app.schemas.ask_ai.ticket_analyze import TicketAnalyzeResponse
from app.core.logger import get_logger

logger = get_logger(__name__)

def joinItems(items: list[str], prefix = '-') -> str:
  if prefix == 'asc':
    return '\n'.join([f"{index + 1}. {item}" for index, item in enumerate(items)])
  return '\n'.join([f"\n{prefix} {item}" for item in items])

def format_string_no_underscore_and_capitalize(input_string):
    temp_string = input_string.replace("_", " ")
    formatted_string = temp_string.title()

    return formatted_string

def ticket_analyze(
    conversation: list[str],
    language: str = "English",
) -> str:
    instructions = [instruction.value for instruction in TicketAnalyzeInstructions]
    prompt_template = f"""
    You are an expert customer service analyst specializing in evaluating customer sentiment in support ticket interactions. Your task is to analyze the provided chat history, determining the customer's overall sentiment, satisfaction, purchasing potential, agent tone, urgency level, and provide a reason for the purchasing potential.

    Ensure that your analysis is objective and based on the content of the history. Do not infer beyond the provided text.

    Here is the list of possible tones:
    <tone_list>
    {[tone.value for tone in Tone]}
    </tone_list>

    Here is the list of possible satisfaction levels:
    <satisfaction_list>
    {[satisfaction.value for satisfaction in Satisfaction]}
    </satisfaction_list>

    Here is the list of possible purchasing potential levels, along with their descriptions:
    <purchasing_potential_list>
    {[potential.value for potential in Potential]}
    </purchasing_potential_list>

    Here is the list of possible agent tones:
    <agent_tone_list>
    {[agent_tone.value for agent_tone in AgentTone]}
    </agent_tone_list>

    Here is the list of possible urgency levels:
    <urgency_list>
    {[urgency.value for urgency in Urgency]}
    </urgency_list>

    Conversational History: This section may include exchanges between the user and any agents involved in addressing the ticket in the tag <history>, or it could be empty if no history exists.
    <history>
    {joinItems(conversation)}
    </history>

    Here are the instructions of your task:
    <instructions>
    {joinItems(instructions)}
    Translate the following result into {language} and ensure that the values inside `summary` and `reason` are translated, even if they are common or default terms. The translation rules below must be strictly followed:
    <translateRules>
        - You have to paraphrase sentences and analysis result values (the content inside `summary` and `reason`) to make them natural and use common words in {language}.
        - If a text is already in {language}, return it unchanged.
        - Only translate the content inside the specified tags (`summary` and `reason`), not the tags themselves.
    </translateRules>
    </instructions>

    Ensure all rules and guidelines are adhered to.

    Put your results in the corresponding JSON format, with no additional explanation:
    {{
        'summary': 'The content of the ticket summary',
        "tone": 'The tone of the ticket {[tone.value for tone in Tone]}',
        "satisfaction": 'The satisfaction level of the ticket {[satisfaction.value for satisfaction in Satisfaction]}',
        "purchasing_potential": 'The purchasing potential of the ticket {[format_string_no_underscore_and_capitalize(potential.name) for potential in Potential]}',
        "reason": 'The reason of the purchasing potential',
        "agent_tone": 'The agent tone of the ticket {[format_string_no_underscore_and_capitalize(agent_tone.name) for agent_tone in AgentTone]}',
        "urgency": 'The urgency level of the ticket {[format_string_no_underscore_and_capitalize(urgency.name) for urgency in Urgency]}'
    }}

    Here is the example of the JSON format:
    {{
        'summary': 'The customer sent a brief greeting ("Hello from gmail"). The agent responded with generic greetings and acknowledgments of the customer choosing the company. There's also mention of testing from zendesk.',
        "tone": 'Normal',
        "satisfaction": 'Neutral',
        "purchasing_potential": 'Medium',
        "reason": 'The customer's initial message is a simple greeting, showing no specific interest in a product or service, indicating a low purchasing potential.',
        "agent_tone": 'Friendly',
        "urgency": 'Low'
    }}
    """

    llm = Settings.llm

    response = llm.complete(prompt_template)

    try:
        match = re.search(r'\{[^{}]*\}', response.text)
        if match:
            return dirtyjson.loads(match.group())
    except Exception as e:
        print("Failed to parse:", e)

    return {
       "summary": "Unknown",
        "tone": "Unknown",
        "satisfaction": "Unknown",
        "purchasing_potential": "Unknown",
        "reason": "Unknown",
        "agent_tone": "Unknown",
        "urgency": "Unknown"
    }
