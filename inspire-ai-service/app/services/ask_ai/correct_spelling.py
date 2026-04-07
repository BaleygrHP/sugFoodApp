from llama_index.core import Settings

def correct_spelling(
    text: str,
) -> str:
    prompt_template = """
**Role:** Meticulous Proofreader

**Task:** Correct spelling and grammar errors in the provided text below.

**CRITICAL CONSTRAINT:** You MUST NOT change, "correct", or alter any Proper Nouns or unique identifiers. This includes, but is not limited to:
    *   Personal names (e.g., "Anya Sharma", "X Æ A-12")
    *   Place names (e.g., "Zzyzx", "Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch")
    *   Company/Organization/Brand names (e.g., "SynthTech", "QuantuMechanix")
    *   Product names or unique model numbers (e.g., "ChronoLeap Watch", "Model ZX-9000")
    *   Technical terms or specific jargon likely intended by the author (e.g., "flux capacitor", "holophonor")
    *   Acronyms, even if unconventional.

**Instructions:**
1.  Thoroughly check the text for errors in standard spelling, grammar, punctuation, and syntax.
2.  Correct only these standard language errors.
3.  If a word appears misspelled but *could* be a unique name or proper noun you are unfamiliar with, **DO NOT CHANGE IT.** Err on the side of preservation for potential proper nouns.
4.  Maintain the original meaning, tone, and style of the text.
5.  Provide only the corrected text as the output.

**Text to Proofread:**
{text}
    """

    prompt = prompt_template.format(text=text)

    llm = Settings.llm

    response = llm.complete(prompt)

    return response.text
