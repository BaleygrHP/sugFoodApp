from llama_index.core.prompts import RichPromptTemplate

TICKET_TRIAGE_ANALYSIS_TEMPLATE = RichPromptTemplate("""
<poml version="2.0">
  <role>Ticket triage system. Decide if AI should handle this ticket.</role>

  <task>
    Analyze and determine:
    - Should AI handle this ticket? (should_reactivate)
    - Should AI skip responding? (should_skip)
    - Does it need human? (requires_human)
    - What's the priority? (priority_level)
  </task>

  <context>
    {% if latest_user_message %}
    <latest-user-message priority="HIGHEST">{{ latest_user_message }}</latest-user_message>
    {% endif %}
    {% if current_ticket_status %}<status>{{ current_ticket_status }}</status>{% endif %}

    {% if customer_context %}
    <customer>
      <name>{{ customer_context.get('name', '') }}</name>
      <email>{{ customer_context.get('email', '') }}</email>
    </customer>
    {% endif %}

    {% if email_metadata %}
    <email>
      {% for key, value in email_metadata.items() %}
      <{{ key }}>{{ value }}</{{ key }}>
      {% endfor %}
    </email>
    {% endif %}

    {% if conversation_context and conversation_context.get('internal_notes') %}
    <notes>
      {% for note in conversation_context.get('internal_notes', []) %}
      <note>{{ note }}</note>
      {% endfor %}
    </notes>
    {% endif %}

    {% if conversation_context and conversation_context.get('resolution_summaries') %}
    <resolution-summaries>
      {% for summary in conversation_context.get('resolution_summaries', []) %}
      <summary>{{ summary }}</summary>
      {% endfor %}
    </resolution-summaries>
    {% endif %}

    <conversation>
      <!-- Recency-first: latest message is highest priority -->
      {% for message in chat_history %}
      {% if loop.last %}
      <msg role="{{ message.role }}" priority="HIGHEST" is_latest="true">{{ message.content }}</msg>
      {% else %}
      <msg role="{{ message.role }}">{{ message.content }}</msg>
      {% endif %}
      {% endfor %}
    </conversation>
  </context>

  <rules>
    <recency-priority>
      - Focus primarily on the latest user message when deciding reactivation/skip.
      - Use earlier turns as context; do not let them override the most recent ask.
      - If the latest turn is assistant, consider the latest preceding user message.
    </recency-priority>
    Skip if:
    - Status = "OPEN" (human handling)
    - Email from noreply@
    - Marketing email (unsubscribe link, no question)
    - Billing notification only

    Reactivate if:
    - Status = SOLVED/PENDING + customer has new question
    - Status = UNASSIGNED or AI_SERVING

    Escalate if:
    - Customer requests human
    - Customer angry/frustrated
    - Complex issue needing judgment
  </rules>

  <output>
    Return JSON only:
```json
{
  "should_reactivate": true,
  "reactivation_reason": "Reason here",
  "should_skip": false,
  "skip_reason": "",
  "requires_human": false,
  "priority_level": "MEDIUM",
  "confidence": 0.85
}
```
    Fields:
    - should_reactivate: bool (AI can handle?)
    - should_skip: bool (AI skip?)
    - skip_reason: str (if should_skip=true)
    - requires_human: bool (needs escalation?)
    - priority_level: LOW|MEDIUM|HIGH|CRITICAL
    - confidence: 0.0-1.0
  </output>
</poml>
""")
