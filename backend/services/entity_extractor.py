"""Entity extraction service using GPT-4o-mini with structured JSON output."""

import json
from openai import AsyncOpenAI
from config import get_settings

_SYSTEM_PROMPT = """\
Extract entities and relationships from the provided text.
Return a JSON object with exactly these keys:
- "entities": list of {name: str, type: str, description: str}
  type must be one of: Person, Organization, Technology, Concept, Location, Other
- "relationships": list of {from: str, to: str, type: str}
  type examples: USES, PART_OF, WORKS_AT, CREATED_BY, RELATED_TO, DEVELOPED_BY

Rules:
- Max 10 entities. Only extract clearly mentioned entities.
- Only include relationships where both entities appear in the entities list.
- If text is empty or has no extractable entities, return {"entities": [], "relationships": []}.
"""


async def extract_entities_from_chunk(text: str) -> dict:
    """Extract entities and relationships from text using GPT-4o-mini.

    Args:
        text: The text chunk to extract entities from.

    Returns:
        A dict with "entities" and "relationships" keys, each containing lists.
        Returns {"entities": [], "relationships": []} on empty input or errors.
    """
    if not text or not text.strip():
        return {"entities": [], "relationships": []}

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_GRADER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Text:\n{text[:2000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
        entities = data.get("entities", [])
        relationships = data.get("relationships", [])

        # Validate entities
        valid_entities = [
            e for e in entities
            if isinstance(e, dict) and "name" in e and "type" in e and "description" in e
        ]

        # Validate relationships
        valid_rels = [
            r for r in relationships
            if isinstance(r, dict) and "from" in r and "to" in r and "type" in r
        ]

        return {"entities": valid_entities, "relationships": valid_rels}
    except Exception:
        return {"entities": [], "relationships": []}
