from enum import Enum

class TicketAnalyzeRules(str, Enum):
  READ_HISTORY_CONTENT = 'You must read the entire content within the <history> tag carefully and analyze it thoroughly before proceeding.',
  DIRECT_ANSWER = 'Answer directly to the point, without unnecessary preambles.',
  NO_HISTORY_OR_ANALYSIS = 'If there is no history provided or the analysis cannot be performed, return the lowest value for each category.',
  ALIGN_ANALYSIS_VALUES = 'The analysis values must align with the lists described below.',

class TicketAnalyzeInstructions(str, Enum):
  READ_HISTORY_CONTENT = 'Carefully read and analyze the entire conversational history provided within the <history> tags.',
  CREATE_SUMMARY = 'Create a summary of the history.',
  ANALYZE_CUSTOMER_TONE = "Analyze the tone of the customer's messages throughout the chat history.",
  DETERMINE_SATISFACTION_LEVEL = "Determine the overall satisfaction level based on the customer's tone and language.",
  USE_PROVIDED_TONE_SATISFACTION_LIST = 'Use the provided tone list and satisfaction list to categorize your findings.',
  PRIORITIZE_RECENT_SENTIMENT = 'If the sentiment is mixed, prioritize the tone and satisfaction level shown in the most recent history.',
  ASSESS_PURCHASING_POTENTIAL = "Assess the customer's purchasing potential based on their interest and intent shown in the history.",
  PROVIDE_PURCHASING_REASON = 'Provide a reason for the purchasing potential level you determined, citing specific evidence from the history.',
  EVALUATE_AGENT_TONE = "Evaluate the agent's tone throughout the history using the provided agent tone list.",
  DETERMINE_URGENCY_LEVEL = "Determine the urgency level of the customer's requests based on the language and context of the history.",

class TicketAnalyzeTags(str, Enum):
  SUMMARY = 'summary',
  TONE = 'tone',
  SATISFACTION = 'satisfaction',
  PURCHASING_POTENTIAL = 'purchasing_potential',
  PURCHASING_POTENTIAL_REASON = 'reason',
  AGENT_TONE = 'agent_tone',
  URGENCY = 'urgency',

class Tone(str, Enum):
  POSITIVE = 'Positive',
  SLIGHTLY_POSITIVE = 'Slightly positive',
  NORMAL = 'Normal',
  SLIGHTLY_NEGATIVE = 'Slightly negative',
  NEGATIVE = 'Negative',

class Satisfaction(str, Enum):
  VERY_SATISFIED = 'Very Satisfied',
  SATISFIED = 'Satisfied',
  NEUTRAL = 'Neutral',
  DISSATISFIED = 'Dissatisfied',
  VERY_DISSATISFIED = 'Very Dissatisfied',

class Potential(str, Enum):
  LOW = 'Low: The customer shows minimal interest and only seeks general information without a clear intention to buy.',
  MEDIUM = 'Medium: The customer is somewhat interested in the product/service and asks more detailed questions but does not have a clear intent to purchase.',
  HIGH = 'High: The customer has a clear intention to buy and shows significant interest in completing the transaction.',

class AgentTone(str, Enum):
  PROFESSIONAL = 'Professional: Responses are formal, concise, and focused on clarity. Ideal for business or corporate settings, where accuracy and neutrality are key.',
  FRIENDLY = 'Friendly: Conversational and approachable, this tone uses casual language to create a warm and engaging experience, perfect for customer support or social interactions.',
  ENTHUSIASTIC = 'Enthusiastic: Upbeat, energetic, and positive. Suitable for engaging audiences, creating excitement, or energizing responses.',
  NOT_RESPONDED = 'Not Responded: The agent has not yet responded to the inquiry.',

class Urgency(str, Enum):
  LOW = 'Low: The task or issue is not time-sensitive and can be addressed at a leisurely pace without immediate attention.',
  NORMAL = 'Normal: The task or issue should be addressed in a timely manner but does not require immediate action.',
  HIGH = 'High: The task or issue is important and should be prioritized, requiring prompt attention and action.',
  URGENT = 'Urgent: The task or issue is critical and demands immediate attention and action to prevent significant consequences.',
