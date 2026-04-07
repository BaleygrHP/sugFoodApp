from llama_index.core import Settings

def shorten_response(
    text: str,
) -> str:
    prompt_template = """
**Role:** Expert Condenser & Format Preserver

**Primary Goal:** Significantly shorten the provided text by removing redundancy and non-essential information, while meticulously preserving its original structure and format (e.g., email, chat message, list, report section).

**Task:**
1.  Analyze the input text to identify its core message and essential details.
2.  Identify its structural format (e.g., presence of greeting/closing, bullet points, conversational turns, paragraph breaks defining sections).
3.  Rewrite the text to be much more concise and direct. Eliminate filler words, redundant phrases, and less critical explanations or examples.
4.  Consolidate sentences where possible without losing meaning or clarity.

**CRITICAL CONSTRAINT:** You MUST maintain the original template and structural elements.
    *   If it's an email, the output must retain a similar greeting, body structure, and closing.
    *   If it's a chat message, it must remain brief and conversational in tone and format.
    *   If it's a list, it must remain a list (bulleted or numbered).
    *   If it has specific headings or paragraph breaks indicating sections, preserve that sectional structure.
    *   Do NOT change the fundamental *type* of communication it is.

**Input Text:**
{text}

**Output:**
Provide only the condensed text, strictly adhering to the original format.
    """

    prompt = prompt_template.format(text=text)

    llm = Settings.llm

    response = llm.complete(prompt)

    return response.text
