from pydantic import BaseModel, Field


class TriggerRulesExtractionDto(BaseModel):
    """
    Schema for triggering knowledge extraction rules based on tenant ID and current rules.
    """

    tenant_id: str = Field(
        ...,
        description="The ID of the tenant for which the rules extraction are applied.",
    )

    extraction_session_id: str = Field(
        ...,
        description="The ID of the extraction session to which the rules apply.",
    )

    language: str = Field(
        "en",
        description="The language of the rules to be extracted. Default is English.",
    )
