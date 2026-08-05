import json
import logging

logger = logging.getLogger(__name__)


MEMORY_EXTRACTION_PROMPT = """
You are NutriBot's Memory Extraction Engine.

Your job is to extract ONLY long-term information that should be remembered.

Remember things like:
- Name
- Age
- Gender
- Height
- Weight
- Diet
- Allergies
- Medical conditions
- Health goals
- Exercise habits
- Food preferences
- Food dislikes
- Lifestyle habits
- Sleep schedule
- Favourite cuisine

DO NOT remember:
- Greetings
- Temporary questions
- One-time requests
- Casual conversation

Return ONLY valid JSON.

Example:

[
    {
        "category": "diet",
        "key": "type",
        "value": "vegetarian"
    },
    {
        "category": "allergy",
        "key": "peanuts",
        "value": "true"
    }
]

If there is nothing worth remembering return:

[]
"""


class MemoryExtractor:

    @staticmethod
    def build_prompt(message: str):
        return f"""
{MEMORY_EXTRACTION_PROMPT}

Conversation:

{message}
"""

    @staticmethod
    def extract(ai_client, message: str):

        prompt = MemoryExtractor.build_prompt(message)

        try:
            response = ai_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
            )

            text = response.text.strip()

            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()

            return json.loads(text)

        except Exception as e:
            logger.error("Memory extraction failed: %s", e)
            return []