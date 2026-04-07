import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from llama_index.core import Settings

from app.core.token_tracking import get_token_tracker
from app.lib.utils.string import language_map
from app.services.ai_service import AIService
from app.tasks import celery, logger

MAX_CONVERSATION_LENGTH = 20000
MAX_TOKENS_PER_REQUEST = 128000  # Conservative limit for most models
ESTIMATED_TOKENS_PER_CHAR = 0.25  # Rough estimation for token counting
CONSOLIDATION_BATCH_SIZE = 50  # Rules per batch during consolidation
MAX_CONSOLIDATION_TOKENS = 128000  # Token limit for consolidation prompts
FINAL_CONSOLIDATION_THRESHOLD = 10  # Threshold for final consolidation pass


def _estimate_tokens(text: str) -> int:
    """Estimate token count for a given text"""
    return int(len(text) * ESTIMATED_TOKENS_PER_CHAR)


def _parse_response_to_json(response: str) -> dict:
    """Parse a string response to JSON, handling errors gracefully"""
    try:
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1
        if start_idx == -1 or end_idx == 0:
            return {}
        json_str = response[start_idx:end_idx]
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return {}


def _build_conversation_extract_prompt(conversations_text: str) -> str:
    return f"""You are a Customer Support Rule Analyst AI. Your job is to extract teachable operational rules from customer support conversations between users and agents.
For each conversation:
1. Identify any repeatable agent behavior that led to a successful resolution or improved the customer experience.
2. Convert each behavior into a concise, actionable rule using strong verbs (e.g., "Provide," "Inform," "Acknowledge").
3. If the tone of the agent clearly affects the outcome (e.g., calming angry user), note the tone.

RULES QUALITY CHECK LIST:
- Must be specific, operational, and teachable (e.g., can be added to a system prompt or training guide).
- Exclude customer-specific data (names, emails, etc.).
- Limit to 0-2 rules per conversation. Skip if no meaningful rules are found.

OUTPUT FORMAT:
Must be in clean JSON format, include conversation ID from input and rules extracted.
{{
  "conversations": [
    {{
      "conversation_id": "<conv_id>",
      "rules": [
        "If a customer asks about general knowledge (math, drawing, legal advice, etc.), reply that you're the  AI and recommend using https://chat.jarvis.cx or https://jarvis.cx/download for productivity-related questions.",
        "Include the link to encourage user to download the application, just include 1 time per chat thread not in a message."
      ]
    }},
    ...
  ]
}}

CONVERSATION INPUT:

{conversations_text}"""


def build_consolidate_prompt(
    input_rules: str,
    existing_rules: list[str] | None = None,
    existing_instructions: list[str] | None = None,
    language: str = "en",
) -> str:
    existing_context = ""
    if existing_rules or existing_instructions:
        existing_context = "\n### EXISTING RULES AND INSTRUCTIONS:\n"
        existing_context += "The tenant already has the following rules and instructions. DO NOT duplicate or create very similar rules:\n\n"

        if existing_rules:
            existing_context += "**Current Rules:**\n"
            for i, rule in enumerate(existing_rules, 1):
                existing_context += f"{i}. {rule}\n"
            existing_context += "\n"

        if existing_instructions:
            existing_context += "**Current Instructions:**\n"
            for i, instruction in enumerate(existing_instructions, 1):
                existing_context += f"{i}. {instruction}\n"
            existing_context += "\n"

    translation_instruction = ""
    if language != "en":
        target_lang_name = language_map(language)
        translation_instruction = f"""
### TRANSLATION REQUIREMENT:
- **IMPORTANT**: After consolidating the rules, translate ALL final rules to {target_lang_name}
- Maintain the operational meaning, tone and clarity of each rule
- Return translated rules instead of original
"""

    return f"""You are an AI support rule optimizer.
Your task is to consolidate support rules extracted from many tickets into a short list of under 10 concise, general-purpose rules for a single tenant.
{existing_context}
{translation_instruction}
Each rule must be:
- Clear and actionable
- Suitable as part of a system prompt or operational guideline for an AI support agent
- Should follow: trigger / condition - action - (outcome / tone)
- **NOT duplicate or be very similar to existing rules/instructions above**

### Your tasks:
1. Group semantically similar rules into a single, clean rule but keep the rule simple enough.
2. Eliminate rules that are vague, redundant, too common or too case-specific.
3. **IMPORTANT**: Skip rules that are already covered by existing rules/instructions or are very similar to them.
4. Focus on NEW, unique, and valuable rules that add distinct value.
5. For each final rule, return up to **5 representative ticket IDs** that best reflect that rule — these should be **clear, relevant, and diverse**.

### Output Format:
{{
  "rules": [
    {{
      "rule": "<translated generalized rule>",
      "source_tickets": ["id1", "id2", ...]
    }}
  ]
}}

### Guidelines:
- Rules may not need to appear in many tickets, just need to be highly meaningful and applicable
- Do not chain multiple rules or too many actions into one.
- Think of each rule as a **core capability or protocol** the AI agent should learn.
- Only include representative tickets that best reflect the final rule (no more than 5).

---

### Input:
{input_rules}"""


def _prepare_conversation_text_from_ticket(messages: list[dict]) -> str:
    """Prepare conversation text from a ticket for token estimation"""
    conversation_text = ""
    for msg in messages:
        content = msg.get("content", "")
        role = msg.get("role", "unknown")
        if content:
            conversation_text += f"{role}: {content}\n"

    return conversation_text


def _prepare_ticket_batches(tickets: list[dict]) -> list[list[dict]]:
    """Create batches of tickets based on estimated token count"""
    batches = []
    current_batch = []
    current_tokens = 0

    base_prompt_tokens = _estimate_tokens(_build_conversation_extract_prompt(""))

    for ticket in tickets:
        messages = ticket.get("messages", [])

        conversation_text = _prepare_conversation_text_from_ticket(messages)
        ticket_tokens = _estimate_tokens(conversation_text)

        if (
            current_tokens + base_prompt_tokens + ticket_tokens > MAX_TOKENS_PER_REQUEST
            and current_batch
        ):
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(
            {
                "ticket_id": ticket.get("ticketID"),
                "conversation_text": conversation_text,
                "messages": messages,
            }
        )
        current_tokens += ticket_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def _extract_rules_from_ticket_batch(batch_tickets: list[dict]) -> list[dict]:
    """
    Extract rules from a batch of tickets.
    """
    try:
        if not batch_tickets:
            return []

        conversations_text = ""
        for i, ticket in enumerate(batch_tickets):
            ticket_id = ticket.get("ticket_id")
            conversation_text = ticket.get("conversation_text", "")

            if conversation_text:
                conversations_text += f"CONVERSATION {i+1} (ID: {ticket_id}):\n"
                conversations_text += conversation_text
                conversations_text += "\n" + "-" * 3 + "\n\n"

        if not conversations_text.strip():
            return []

        prompt = _build_conversation_extract_prompt(conversations_text.strip())
        llm = Settings.llm
        response = llm.complete(prompt)

        parsed_response = _parse_response_to_json(response.text.strip())
        if not parsed_response:
            logger.error("Failed to parse response from LLM for rule extraction")
            return []

        ticket_rules = []
        conversation_rules = parsed_response.get("conversations", [])

        for conv in conversation_rules:
            ticket_id = conv.get("conversation_id")
            rules = conv.get("rules", [])

            ticket_data = None
            for t in batch_tickets:
                if t["ticket_id"] == ticket_id:
                    ticket_data = t
                    break

            if not ticket_data:
                continue

            first_message_id = ticket_data.get("messages", [{}])[0].get("id")
            last_message_id = ticket_data.get("messages", [{}])[-1].get("id")

            if rules:
                ticket_rules.append(
                    {
                        "ticket_id": ticket_id,
                        "rules": rules,
                        "first_message_id": first_message_id,
                        "last_message_id": last_message_id,
                    }
                )

        return ticket_rules

    except Exception as e:
        logger.error(f"Error extracting rules from batch: {e}")
        return []


def _process_ticket_batches_parallel(
    batches: list[list[dict]], max_workers: int = 5
) -> list[dict]:
    """
    Process multiple batches in parallel to extract rules.

    Args:
        batches: List of ticket batches
        max_workers: Maximum number of parallel workers

    Returns:
        List of all extracted rules from all batches
    """
    all_ticket_rules = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {
            executor.submit(_extract_rules_from_ticket_batch, batch): (i, batch)
            for i, batch in enumerate(batches)
        }

        for future in as_completed(future_to_batch):
            batch_index, batch = future_to_batch[future]
            try:
                batch_rules = future.result()
                all_ticket_rules.extend(batch_rules)

                logger.info(
                    f"Batch {batch_index + 1} completed: {len(batch)} tickets → {len(batch_rules)} rules"
                )

            except Exception as e:
                logger.error(f"Error processing batch {batch_index + 1}: {e}")

    return all_ticket_rules


def _prepare_rule_batches(
    rule_data: list[dict],
    existing_rules: list[str] | None = None,
    existing_instructions: list[str] | None = None,
) -> list[list[dict]]:
    """Create batches of rules based on token limits"""
    batches = []
    current_batch = []
    current_tokens = 0
    base_prompt_tokens = _estimate_tokens(
        build_consolidate_prompt("", existing_rules, existing_instructions)
    )

    for rule in rule_data:
        rule_json = json.dumps(rule, ensure_ascii=False, indent=2)
        rule_tokens = _estimate_tokens(rule_json)

        if (
            current_tokens + rule_tokens + base_prompt_tokens > MAX_CONSOLIDATION_TOKENS
            and current_batch
        ):
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(rule)
        current_tokens += rule_tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def _consolidate_rules_single_batch(
    rules: list[dict],
    existing_rules: list[str] | None,
    existing_instructions: list[str] | None,
    language: str = "en",
) -> list[dict]:
    """Consolidate rules in a single batch"""
    if not rules:
        return []

    prompt = build_consolidate_prompt(
        json.dumps(rules, ensure_ascii=False, indent=2),
        existing_rules,
        existing_instructions,
        language,
    )
    llm = Settings.llm
    response = llm.complete(prompt)

    parsed_response = _parse_response_to_json(response.text.strip())
    if not parsed_response:
        logger.error("Failed to parse response from LLM for rule consolidation")
        return []

    return parsed_response.get("rules", [])


def _consolidate_rules(
    ticket_rules: list[dict], tenant_id: str, language: str = "en"
) -> list[dict]:
    """Consolidate ticket rules into final general rules using token-aware batching"""
    if not ticket_rules:
        return []

    existing_data = AIService.get_current_rules_instructions(tenant_id)
    existing_rules = existing_data.get("rules", [])
    existing_instructions = existing_data.get("instructions", [])

    rule_batches = _prepare_rule_batches(
        ticket_rules, existing_rules, existing_instructions
    )

    consolidated_rules = []
    for batch in rule_batches:
        batch_results = _consolidate_rules_single_batch(
            batch, existing_rules, existing_instructions, language
        )
        if batch_results:
            consolidated_rules.extend(batch_results)

    if len(consolidated_rules) > FINAL_CONSOLIDATION_THRESHOLD:
        final_prompt = build_consolidate_prompt(
            json.dumps(consolidated_rules, ensure_ascii=False, indent=2),
            existing_rules,
            existing_instructions,
            language,
        )
        llm = Settings.llm
        response = llm.complete(final_prompt)
        parsed_response = _parse_response_to_json(response.text.strip())
        if not parsed_response:
            logger.error("Failed to parse final consolidation response")
            return []

        consolidated_rules = parsed_response.get("rules", [])
    else:
        logger.info(f"Final consolidation completed: {len(consolidated_rules)} rules")

    return consolidated_rules


def _process_tickets_for_extraction(
    tickets: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Process tickets to separate changed tickets and existing rules"""
    changed_tickets = []
    existing_ticket_rules = []

    for ticket in tickets:
        has_changed = bool(ticket.get("hasChanged", True))
        if has_changed:
            changed_tickets.append(ticket)
        else:
            rules = ticket.get("rules", {})
            rules = rules.get("rules", [])
            if rules:
                for rule in rules:
                    existing_ticket_rules.append(
                        {
                            "ticket_id": ticket.get("ticketID"),
                            "rule": rule,
                        }
                    )

    return changed_tickets, existing_ticket_rules


@celery.task(name="extract_rules_from_histories")
def extract_rules_from_histories(
    extraction_session_id: str, tenant_id: str, language: str = "en"
) -> dict:
    """
    Extract rules from histories based on tenant configuration.
    """
    token_tracker = get_token_tracker()
    token_tracker.reset_counts()

    AIService.send_extraction_status(
        extraction_session_id=extraction_session_id,
        status="processing",
    )

    # TODO: Put below logic in a loop to load all tickets in batches
    start_time = datetime.now()
    ticket_response = AIService.get_tickets(tenant_id)
    tickets = ticket_response.get("items", []) if ticket_response else []

    if not tickets:
        AIService.send_extraction_status(
            extraction_session_id=extraction_session_id,
            status="failed",
        )
        return {
            "status": "Not found",
            "tenant_id": tenant_id,
            "message": "No tickets available for rule extraction.",
        }

    changed_tickets, existing_ticket_rules = _process_tickets_for_extraction(tickets)

    logger.info(
        f"Processing {len(tickets)} tickets for tenant {tenant_id}: "
        f"{len(changed_tickets)} need extraction, "
        f"{len(existing_ticket_rules)} existing rules"
    )

    all_extracted_rules = []
    new_ticket_rules = []

    if changed_tickets:
        logger.info(f"🔄 Extracting rules from {len(changed_tickets)} changed tickets")
        batches = _prepare_ticket_batches(changed_tickets)
        all_extracted_rules = _process_ticket_batches_parallel(batches, max_workers=5)

        for rule_data in all_extracted_rules:
            new_ticket_rules.append(rule_data)

        if new_ticket_rules:
            try:
                _ = AIService.create_ticket_rules(
                    extraction_session_id=extraction_session_id,
                    ticket_rules=new_ticket_rules,
                )
                logger.info(
                    f"✅ Sent {len(new_ticket_rules)} new ticket rules to AI service"
                )
            except Exception as e:
                logger.error(f"❌ Failed to send ticket rules to AI service: {e}")
    else:
        logger.info("🔄 No changed tickets found, skipping extraction phase")

    newly_extracted_rules = [
        {"ticket_id": rule["ticket_id"], "rule": r}
        for rule in all_extracted_rules
        for r in rule.get("rules", [])
    ]

    all_rules_for_consolidation = newly_extracted_rules + existing_ticket_rules

    final_consolidated_rules = _consolidate_rules(
        all_rules_for_consolidation, tenant_id, language
    )
    if not final_consolidated_rules:
        AIService.send_extraction_status(
            extraction_session_id=extraction_session_id,
            status="failed",
        )

        return {
            "status": "Failed",
            "tenant_id": tenant_id,
            "message": "Failed to extract rules from tickets.",
        }

    _ = AIService.create_extracted_rules(
        extraction_session_id=extraction_session_id,
        extracted_rules=final_consolidated_rules,
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    token_counts = token_tracker.get_token_counts()

    _ = AIService.send_extraction_status(
        extraction_session_id=extraction_session_id,
        status="completed",
        metadata={
            "tickets_processed": len(tickets),
            "changed_tickets_processed": len(changed_tickets),
            "existing_rules_reused": len(existing_ticket_rules),
            "new_ticket_rules_extracted": len(all_extracted_rules),
            "final_rules_count": len(final_consolidated_rules),
            "token_usage": {
                "prompt_tokens": token_counts["prompt"]["total"],
                "completion_tokens": token_counts["prompt"]["completion"],
                "total_tokens": token_tracker.get_total_token_count(),
            },
            "duration_seconds": duration,
        },
    )

    return {
        "status": "Completed",
        "tenant_id": tenant_id,
        "changed_tickets_processed": len(changed_tickets),
        "existing_rules_reused": len(existing_ticket_rules),
        "new_ticket_rules_extracted": len(all_extracted_rules),
        "final_rules": final_consolidated_rules,
        "token_usage": {
            "prompt_tokens": token_counts["prompt"]["total"],
            "completion_tokens": token_counts["prompt"]["completion"],
            "total_tokens": token_tracker.get_total_token_count(),
        },
        "duration_seconds": duration,
    }
