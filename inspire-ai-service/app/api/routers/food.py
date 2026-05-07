import json
import unicodedata
from typing import List

from fastapi import APIRouter, HTTPException
from llama_index.core import Settings as LlamaIndexSettings
from pydantic import BaseModel, Field

food_router = router = APIRouter(prefix="/food")


class FoodChatRestaurant(BaseModel):
    id: str
    name: str
    cuisine: str
    priceRange: str
    rating: float
    distance: str
    description: str = ""
    menuItems: List[str] = Field(default_factory=list)


class FoodChatSuggestionRequest(BaseModel):
    message: str = Field(..., description="Freeform user message about what they want to eat.")
    keywords: List[str] = Field(default_factory=list, description="Optional chip keywords from the frontend.")
    restaurants: List[FoodChatRestaurant] = Field(default_factory=list, description="Available restaurant context.")


class FoodChatSuggestionResponse(BaseModel):
    reply: str
    matched_restaurant_ids: List[str] = Field(default_factory=list)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.lower().strip()


def strip_code_fences(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def parse_json_response(value: str) -> dict:
    cleaned = strip_code_fences(value)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM did not return a JSON object")
    return json.loads(cleaned[start : end + 1])


def match_restaurants_from_reply(reply: str, restaurants: List[FoodChatRestaurant]) -> List[str]:
    normalized_reply = normalize_text(reply)
    return [
        restaurant.id
        for restaurant in restaurants
        if normalize_text(restaurant.name) in normalized_reply
    ][:5]


def build_prompt(body: FoodChatSuggestionRequest) -> str:
    restaurant_lines = []
    for restaurant in body.restaurants[:25]:
        menu_preview = ", ".join(restaurant.menuItems[:8]) or "Anything"
        restaurant_lines.append(
            f"- id={restaurant.id} | name={restaurant.name} | cuisine={restaurant.cuisine} | "
            f"price={restaurant.priceRange} | rating={restaurant.rating:.1f} | distance={restaurant.distance} | "
            f"menu={menu_preview} | note={restaurant.description or 'N/A'}"
        )

    keyword_text = ", ".join(body.keywords) if body.keywords else "none"
    restaurant_context = "\n".join(restaurant_lines) if restaurant_lines else "- none"

    return (
        "You are a food recommendation assistant for a lunch app. "
        "Pick 3 to 5 restaurants only from the provided list. "
        "Use a Vietnamese-first lens when it fits the request, but stay grounded in the provided restaurants. "
        "Return strict JSON with this shape only: "
        '{"reply":"markdown reply with bullet points","matched_restaurant_ids":["id-1","id-2"]}.\n\n'
        f"User message: {body.message}\n"
        f"Optional keywords: {keyword_text}\n\n"
        "Available restaurants:\n"
        f"{restaurant_context}\n\n"
        "Rules:\n"
        "1. matched_restaurant_ids must contain only restaurant ids from the list.\n"
        "2. reply must briefly explain the fit, then list bullet points using the restaurant names.\n"
        "3. Keep the reply concise and helpful.\n"
    )


@router.post("/chat-suggestions", response_model=FoodChatSuggestionResponse)
async def chat_suggestions(body: FoodChatSuggestionRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    if not body.restaurants:
        return FoodChatSuggestionResponse(
            reply="I need a restaurant list before I can suggest anything.",
            matched_restaurant_ids=[],
        )

    prompt = build_prompt(body)

    try:
        completion = LlamaIndexSettings.llm.complete(prompt)
        raw_text = getattr(completion, "text", str(completion))
        parsed = parse_json_response(raw_text)
    except Exception as exc:  # pragma: no cover - network/provider failure
        raise HTTPException(status_code=502, detail=f"food_chat_failed: {exc}") from exc

    reply = str(parsed.get("reply", "")).strip()
    available_ids = {restaurant.id for restaurant in body.restaurants}
    matched_restaurant_ids = [
        restaurant_id
        for restaurant_id in parsed.get("matched_restaurant_ids", [])
        if restaurant_id in available_ids
    ][:5]

    if not matched_restaurant_ids and reply:
        matched_restaurant_ids = match_restaurants_from_reply(reply, body.restaurants)

    if not reply:
        raise HTTPException(status_code=502, detail="food_chat_failed: missing reply")

    return FoodChatSuggestionResponse(
        reply=reply,
        matched_restaurant_ids=matched_restaurant_ids,
    )
