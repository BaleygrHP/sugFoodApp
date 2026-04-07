from llama_index.core import Settings

def more_casual(
    text: str,
) -> str:
    prompt_template = """
**Role:** Casual Tone Adapter & Format Preserver

**Primary Goal:** Adapt the provided text to a more casual, conversational, and informal tone, while meticulously preserving its original structure and format (e.g., email, chat message, list, report section).

**Task:**
1.  Analyze the input text to understand its core message, intent, and existing level of formality.
2.  Identify its structural format (e.g., presence of greeting/closing, bullet points, conversational turns, paragraph breaks defining sections).
3.  Rewrite the text using more informal language. This includes:
    *   Replacing formal words and phrases with common, everyday equivalents (e.g., "utilize" -> "use", "commence" -> "start", "inform" -> "let you know").
    *   Employing contractions where appropriate (e.g., "it is" -> "it's", "you are" -> "you're", "do not" -> "don't").
    *   Simplifying complex sentence structures for a more natural, spoken feel.
    *   Using warmer, more approachable phrasing.
4.  Adjust sentence structure slightly for a more natural, conversational flow, but ensure the core meaning remains identical.

**CRITICAL CONSTRAINT:** You MUST maintain the original template and structural elements.
    *   If it's an email, the output must retain a similar greeting, body structure, and closing (though the *wording* of these can become more casual).
    *   If it's a chat message, it should sound even more like a typical chat exchange.
    *   If it's a list, it must remain a list (bulleted or numbered).
    *   If it has specific headings or paragraph breaks indicating sections, preserve that sectional structure.
    *   Do NOT change the fundamental *type* of communication it is.
    *   Ensure the casual tone does not inadvertently change the core meaning or introduce inappropriate slang unless context strongly suggests it.

**Input Text:**
{text}

**Output:**
Provide only the text adapted to a more casual tone, strictly adhering to the original format.
    """

    prompt = prompt_template.format(text=text)

    llm = Settings.llm

    response = llm.complete(prompt)

    return response.text
