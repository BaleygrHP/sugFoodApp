from llama_index.core import Settings

def simplify_words(
    text: str,
) -> str:
    prompt_template = """
**Role:** Plain Language Expert

**Primary Goal:** Enhance the readability of the provided text by simplifying its vocabulary.

**Task:**
1.  Identify words in the text below that are likely unfamiliar, complex, overly technical, or unnecessarily sophisticated for a general audience.
2.  Replace these words with simpler, more common, and widely understood alternatives.
3.  Prioritize directness and clarity in word choice.
4.  If necessary for clarity after vocabulary changes, slightly adjust sentence structure (e.g., break up very long sentences), but the main focus is on word replacement.

**Crucial Constraint:** You MUST preserve the original core meaning, intent, and essential information of the text. Do not add new information or significantly alter the message. Avoid oversimplification that leads to inaccuracy or loss of nuance where that nuance is critical.

**Input Text:**
{text}

**Output:**
Provide only the simplified version of the text.
    """

    prompt = prompt_template.format(text=text)

    llm = Settings.llm

    response = llm.complete(prompt)

    return response.text
