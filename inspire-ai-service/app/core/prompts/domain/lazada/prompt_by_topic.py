from app.schemas.ask_ai.draft_response import DraftModeEnum
from app.core.prompts.domain.lazada.default_topic import DefaultTopic
from app.core.prompts.domain.lazada import (
    LAZADA_HUMAN_SUPPORT_PROMPT,
    LAZADA_ORDER_CANCELLATION_AUTO_RESPONSE_PROMPT,
    LAZADA_ORDER_CANCELLATION_DRAFT_RESPONSE_PROMPT,
    LAZADA_ORDER_INQUIRY_AUTO_RESPONSE_PROMPT,
    LAZADA_ORDER_INQUIRY_DRAFT_RESPONSE_PROMPT,
    LAZADA_PRODUCT_CONSULTATION_AUTO_RESPONSE_PROMPT,
    LAZADA_PRODUCT_CONSULTATION_DRAFT_RESPONSE_PROMPT,
)


def get_prompt_template_by_topic(
    topic_code: str, mode: DraftModeEnum = DraftModeEnum.DRAFT
):
    """
    Get the appropriate prompt template for a given topic and mode.

    Args:
        topic_code: The topic code from DefaultTopic enum
        mode: The draft mode (AUTO_RESPONSE or DRAFT)

    Returns:
        RichPromptTemplate object or None if not found

    Raises:
        ValueError: If topic_code or mode is invalid
    """
    if not topic_code:
        raise ValueError("topic_code cannot be empty")

    if not isinstance(mode, DraftModeEnum):
        raise TypeError(f"mode must be a DraftModeEnum, got {type(mode)}")

    # Define prompt mapping structure
    prompt_mapping = {
        DefaultTopic.LAZADA_PRODUCT_CONSULTATION.value: {
            DraftModeEnum.AUTO_RESPONSE: LAZADA_PRODUCT_CONSULTATION_AUTO_RESPONSE_PROMPT,
            DraftModeEnum.DRAFT: LAZADA_PRODUCT_CONSULTATION_DRAFT_RESPONSE_PROMPT,
        },
        DefaultTopic.LAZADA_ORDER_CANCELLATION.value: {
            DraftModeEnum.AUTO_RESPONSE: LAZADA_ORDER_CANCELLATION_AUTO_RESPONSE_PROMPT,
            DraftModeEnum.DRAFT: LAZADA_ORDER_CANCELLATION_DRAFT_RESPONSE_PROMPT,
        },
        DefaultTopic.LAZADA_ORDER_INFO.value: {
            DraftModeEnum.AUTO_RESPONSE: LAZADA_ORDER_INQUIRY_AUTO_RESPONSE_PROMPT,
            DraftModeEnum.DRAFT: LAZADA_ORDER_INQUIRY_DRAFT_RESPONSE_PROMPT,
        },
        DefaultTopic.LAZADA_HUMAN_SUPPORT.value: {
            DraftModeEnum.AUTO_RESPONSE: LAZADA_HUMAN_SUPPORT_PROMPT,
            DraftModeEnum.DRAFT: LAZADA_HUMAN_SUPPORT_PROMPT,
        },
    }

    topic_prompts = prompt_mapping.get(topic_code)
    if not topic_prompts:
        return None

    return topic_prompts.get(mode)
