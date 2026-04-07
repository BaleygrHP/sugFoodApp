from pydantic import BaseModel


class PydanticUtils:
    @staticmethod
    def dump_fields(
        model: BaseModel, exclude_none: bool = False, exclude_fields: list[str] = []
    ) -> dict:
        return {
            field_name: getattr(model, field_name)
            for field_name in model.model_fields
            if (exclude_none and getattr(model, field_name) is not None)
            and field_name not in exclude_fields
        }
