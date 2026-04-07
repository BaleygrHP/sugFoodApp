from llama_index.core import Settings

def more_professional(
    text: str,
) -> str:
    prompt_template = """
**Role:** Professional Tone Enhancer & Format Preserver

**Primary Goal:** Adapt the provided text to a more professional, formal, and polished tone suitable for business, academic, or official communication, while meticulously preserving its original structure and format (e.g., email, chat message, list, report section).

**Task:**
1.  Analyze the input text to understand its core message, intent, and existing level of formality.
2.  Identify its structural format (e.g., presence of greeting/closing, bullet points, conversational turns, paragraph breaks defining sections).
3.  Rewrite the text using more formal and standard professional language. This includes:
    *   Replacing informal words, slang, colloquialisms, and overly casual phrasing with appropriate professional equivalents (e.g., "fix" -> "resolve" or "address", "get back to you" -> "follow up with you", "stuff" -> "items" or "matters").
    *   Ensuring clear, complete, and grammatically correct sentence structures. Avoid run-on sentences or overly simplistic phrasing.
    *   Using objective language where appropriate, minimizing overly personal or emotional expressions unless central to the message.
    *   Ensuring a polite, respectful, and clear tone.
4.  Adjust sentence structure for clarity and formality, ensuring the core meaning remains identical and precise.

**CRITICAL CONSTRAINT:** You MUST maintain the original template and structural elements.
    *   If it's an email, the output must retain a similar greeting, body structure, and closing (though the *wording* will become more formal).
    *   If it's a chat message intended for a professional context, it should be adapted to a more formal written style (avoiding chat abbreviations, excessive brevity).
    *   If it's a list, it must remain a list (bulleted or numbered).
    *   If it has specific headings or paragraph breaks indicating sections, preserve that sectional structure.
    *   Do NOT change the fundamental *type* of communication it is.
    *   Ensure the professional tone enhances clarity and precision without making the text overly complex, obscure, or altering the core meaning.

**Input Text:**
{text}

**Output:**
Provide only the text adapted to a more professional tone, strictly adhering to the original format.
    """

    prompt = prompt_template.format(text=text)

    llm = Settings.llm

    response = llm.complete(prompt)

    return response.text
