from llama_index.core import Settings
from app.core.logger import logger
from app.core.tools.query_engine import QueryEngine
from llama_index.core.agent.workflow import FunctionAgent

async def lengthen_response(
    text: str,
    query_engine: QueryEngine = None,
) -> str:
    prompt_template = """
**Role:** Content Elaborator (Strict Adherence Mode)

**Primary Goal:** Expand the provided text by adding detail, description, or rephrasing *solely based on the information explicitly present* in the original text. The goal is to make the existing statement longer and potentially more descriptive or slightly more formal/informal, but NOT to add new facts, reasons, or contexts.

**Task:**
1.  Analyze the *exact* meaning and scope of the original text.
2.  Expand on the existing words and concepts ONLY. This might involve:
    *   Using more descriptive adjectives or adverbs already implied.
    *   Rephrasing parts for clarity or emphasis using different words with the same core meaning.
    *   Slightly expanding a sentence structure (e.g., turning a simple sentence into a complex one with related clauses *that don't introduce new factual assumptions*).
3.  Maintain the original core message precisely.

**CRITICAL CONSTRAINTS:**
*   **DO NOT INVENT REASONS OR CAUSES:** If the original text states an outcome (like "cannot return the item"), do not invent *why* that outcome occurred unless the reason is *explicitly* in the original text.
*   **DO NOT ASSUME CONTEXT:** Do not assume the text originates from a specific entity (like a company, a person with a specific role) or situation (like a specific policy, a scientific study) unless clearly stated in the original. Avoid adding details common to assumed contexts (e.g., standard return policy clauses).
*   **DO NOT ADD NEW FACTUAL INFORMATION:** Expansion must come from elaborating on *what is already there*, not from adding external knowledge or common scenarios.
*   **Maintain Original Intent and Tone:** Expand consistently with the source.

**Input Text:**
{text}

**Output:**
Provide only the expanded version of the text, strictly adhering to the constraint of using only explicitly present information and avoiding invented context or reasons.
    """

    prompt = prompt_template.format(text=text)

    llm = Settings.llm

    # TODO: fix query engine json error, then delete this and the next line
    query_engine = None

    if query_engine is not None:
        query_engine_tool = query_engine.create_tool(
            name="query_engine_tool",
            description=(
                "Searches internal documentation to answer questions. "
                "Use this tool to find information related to user queries. "
                "The input should be a clear, concise, and specific question, optimized for retrieval-augmented generation."
                "For example: 'Clarify the return policy for a product' is optimal version of 'What is the return policy?' or 'Provide steps to reset a password' is optimal version of 'How to reset my password?'"
            )
        )

        agent = FunctionAgent(
            tools=[query_engine_tool],
            llm=llm,
        )

        response = await agent.run(prompt)
        response = str(response)

    else:
        response = llm.complete(prompt).text

    return response
