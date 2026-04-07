from typing import Any
import json

from llama_index.core import Settings
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core import PromptTemplate

from app.models.ask_ai.variable import ApiVariableParseOutput, Variable

def parse_api_variables(
    language: str,
    name: str,
    description: str,
    parameters: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    current_variables: list[Variable] | None = None,
) -> ApiVariableParseOutput:
    if not parameters:
        parameters = {}
    if not body:
        body = {}
    if not current_variables:
        current_variables = []

    prompt = """
You are an AI assistant specialized in processing JSON data to create API call templates. Your task is to create a new JSON from an existing one, replacing all values in `parameters` and `body` with variables in the format "@var_name", and generating a complete list of variables with descriptions. Use the provided input to perform the following:

**Input**:
- `language`: The language to use for descriptions of variables (e.g., Vietnamese).
- `name`: The name of the API (e.g., book_room).
- `description`: A description of the API's functionality (e.g., Create a hotel room booking).
- `parameters`: A JSON object containing the API's parameters (e.g., query parameters or path parameters).
- `body`: A JSON object containing the API's body.
- `variables`: A list of existing variables, each with a `name` (variable name) and `description` (variable description).

**Requirements**:
1. Replace all values in `parameters` and `body` of the original JSON with variables in the format "@var_name", where `var_name` exactly matches the field name (e.g., the value of the `hotelBranch` field becomes `@hotelBranch`).
2. Create a complete list of variables (`variables`):
   - Include only variables that correspond to fields used in the output `parameters` or `body`.
   - For variables present in the input `variables` list:
     - Retain the existing `name` and `description` if the `description` is clear, contextually relevant to the API's `name` and `description`, and includes necessary details (e.g., format like "yyyy-mm-dd" for dates).
     - If the existing `description` is vague, incomplete, or not fully aligned with the API's context, refine it to be clearer and more contextually appropriate while preserving the original intent. For example, refine "Tên của người dùng" to "Họ và tên của khách hàng" for a hotel booking API if appropriate, but avoid changing specific details like "Họ và tên" to "Tên".
   - Create new variables for any fields in `parameters` or `body` that do not have a corresponding variable in the input `variables` list.
   - Descriptions for new variables must:
     - Be contextually relevant based on the API's `name` and `description`.
     - Be concise, clear, and written in the language specified in `language`.
     - Use the "yyyy-mm-dd" format for date-related fields or other appropriate formats based on context.
   - Discard any variables from the input `variables` list that are not used in the output `parameters` or `body`.
3. Ensure the output maintains the exact JSON structure of `parameters` and `body`, only replacing values with variables.
4. Use the language specified in `language` exclusively for writing or refining descriptions in the `variables` list.

**Output**:
- `parameters`: A JSON object with values replaced by variables in the format "@var_name".
- `body`: A JSON object with values replaced by variables in the format "@var_name".
- `variables`: A list of all variables used in the output, each with `name` and `description`.

**Example**:

**Input**:
```
- Language: "Vietnamese"
- API Name: "book_room"
- Description: "Create a hotel room booking"
- Parameters: {
    "hotelBranch": "Hanoi"
  }
- Body: {
    "roomTypeId": 3,
    "checkInDate": "2025-05-20",
    "checkOutDate": "2025-05-21",
    "fullName": "Nguyen Van A"
  }
- Current Variables: [
    {
      "name": "roomTypeId",
      "description": "ID of the room type"
    },
    {
      "name": "unusedVariable",
      "description": "An unused variable"
    }
  ]
```

**Output**:
```
{
  "parameters": {
    "hotelBranch": "@hotelBranch"
  },
  "body": {
    "roomTypeId": "@roomTypeId",
    "checkInDate": "@checkInDate",
    "checkOutDate": "@checkOutDate",
    "fullName": "@fullName"
  },
  "variables": [
    {
      "name": "hotelBranch",
      "description": "Chi nhánh khách sạn"
    },
    {
      "name": "roomTypeId",
      "description": "ID of the room type"
    },
    {
      "name": "checkInDate",
      "description": "Ngày đặt phòng, định dạng yyyy-mm-dd"
    },
    {
      "name": "checkOutDate",
      "description": "Ngày trả phòng, định dạng yyyy-mm-dd"
    },
    {
      "name": "fullName",
      "description": "Họ và tên của người đặt phòng"
    }
  ]
}
```

**Notes**:
- Ensure variable names (`var_name`) exactly match the field names in `parameters` and `body`.
- When refining existing descriptions, preserve specific details (e.g., "Họ và tên" should not be simplified to "Tên") unless the original description is clearly inadequate.
- Descriptions for variables must be natural, contextually appropriate, and written in the language specified in `language`.
- If no specific information is provided about a field's format or meaning, infer a reasonable description based on the field name and API description.
- Only include variables in the output `variables` list that are used in the output `parameters` or `body`. Discard unused variables from the input `variables` list.
- Process both `parameters` and `body` fields consistently, ensuring all values are replaced with corresponding variables.

Process the request based on the provided input and return the result in the specified output format.

**Here is the data need to be processed:**

- Language: "{language}"
- API Name: "{api_name}"
- Description:
    <description>{description}</description>
- Parameters: {parameters}
- Body: {body}
- Current Variables: [
{current_variables}
  ]
<
"""

    qa_template = PromptTemplate(prompt)

    current_variables_str = ""
    for variable in current_variables:
        var_str = (
            "    {\n"
            + f"      \"name\": \"{variable.name}\"\n"
            + f"      \"description\": \"{variable.description}\"\n"
            + "    },\n"
        )

        current_variables_str += var_str

    prompt_template = qa_template.format(
        language=language,
        api_name=name,
        description=description,
        parameters=json.dumps(parameters),
        body=json.dumps(body),
        current_variables=current_variables_str
    )

    llm_program = LLMTextCompletionProgram.from_defaults(
        output_cls=ApiVariableParseOutput,
        prompt_template_str=prompt_template,
        llm=Settings.llm,
    )

    response = llm_program()

    return response
