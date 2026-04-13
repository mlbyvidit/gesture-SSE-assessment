import json
import os
import logging

import httpx

logger = logging.getLogger(__name__)

_MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

_SYSTEM_PROMPT = """You are Maya, a warm and friendly intake specialist at Gesture.
Your personality is professional but approachable — like a knowledgeable colleague, not a salesperson.

YOUR ONLY JOB RIGHT NOW is to have a natural conversation to understand the user's needs. Do NOT recommend specific products yet. Do NOT go into pricing details. Just collect their information through genuine conversation.

You need to collect these four things — but ask naturally, one at a time, not like a form:
1. WHO they are trying to reach: customers, employees, partners, or brand audience
2. SCALE: roughly how many people (under 500, hundreds, thousands, 50,000+)
3. GOAL: what outcome they want (reduce churn/retention, reward performance/recognition, drive engagement, run a campaign/acquisition)
4. TIMELINE: how urgently they want to move (immediately/Q1/soon, next quarter, just exploring)

Bonus fields to collect if they come up naturally:
- Whether they have an existing loyalty or rewards program
- Their specific pain point in their own words
- What type of company they are

CONVERSATION RULES:
- Greet warmly on the first message
- Ask only ONE question per message — never two
- Keep your replies SHORT — 2 to 3 sentences maximum during intake
- If the user gives you multiple pieces of information at once, acknowledge all of it and ask about whatever is still missing
- If the user asks what Gesture does, give a ONE sentence answer: "Gesture helps brands create memorable gifting and reward experiences for their customers, employees, and partners." Then continue collecting.
- Do not get sidetracked into long product explanations during intake
- Be genuinely curious and interested in their situation

WHEN YOU HAVE COLLECTED ENOUGH INFORMATION:
CRITICAL RULE: The moment you can answer ALL FOUR of these — audience, scale, goal, timeline — you MUST complete the intake. Do NOT ask any more questions. Do NOT collect bonus fields at the expense of completing. Do not say "one more question". Emit PROFILE_COMPLETE immediately.
You MUST complete by message 5 at the latest even if you are missing some bonus fields.

When you have the four required fields, write your final intake message (warm, 2 sentences max, acknowledging what you've learned and that you're pulling together a recommendation) and then on a NEW LINE write exactly:
PROFILE_COMPLETE
And then on the VERY NEXT LINE write a valid raw JSON object (NO markdown fences, NO ```json, just the raw JSON):
{
  "audience": "customers|employees|partners|brand",
  "scale": "small|medium|large|enterprise",
  "goal": "retention|recognition|engagement|acquisition",
  "timeline": "immediate|planned|exploring",
  "existing_program": true|false|null,
  "pain_point": "their exact words describing their problem or null",
  "company_type": "type of company or null",
  "raw_quotes": ["exact quote 1", "exact quote 2"]
}

IMPORTANT: Write the JSON with NO surrounding text, NO markdown code fences, NO backticks. Just the raw { } object directly after PROFILE_COMPLETE."""


async def run_intake(
    user_message: str,
    conversation_history: list[dict],
    session_id: str,
) -> dict:
    api_key = os.getenv("MISTRAL_API_KEY")

    # After 6 messages in history (3 user turns), push a strong completion hint
    turn_count = sum(1 for m in conversation_history if m.get("role") == "user")
    final_content = user_message
    if turn_count >= 3:
        final_content = (
            user_message
            + "\n\n[You now have enough information. You MUST emit PROFILE_COMPLETE "
            "in this response. Do not ask another question.]"
        )

    messages = (
        [{"role": "system", "content": _SYSTEM_PROMPT}]
        + conversation_history
        + [{"role": "user", "content": final_content}]
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _MISTRAL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mistral-small-latest",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 400,
                },
            )
            response.raise_for_status()
            data = response.json()

        reply: str = data["choices"][0]["message"]["content"]

        if "PROFILE_COMPLETE" in reply:
            parts = reply.split("PROFILE_COMPLETE", 1)
            chat_part = parts[0].strip()
            json_part = parts[1].strip()

            # Strip markdown code fences that some model versions emit
            if json_part.startswith("```"):
                json_part = json_part.split("\n", 1)[-1]
                json_part = json_part.rsplit("```", 1)[0].strip()

            try:
                profile_data = json.loads(json_part)
            except json.JSONDecodeError as exc:
                logger.error(
                    "session=%s failed to parse profile JSON: %s | raw=%r",
                    session_id, exc, json_part,
                )
                return {
                    "chat_message": (
                        "I think I have everything I need — could you just "
                        "confirm one more time what your main goal is and we'll "
                        "get your recommendation ready."
                    ),
                    "profile_complete": False,
                    "profile_data": None,
                }

            return {
                "chat_message": chat_part,
                "profile_complete": True,
                "profile_data": profile_data,
            }

        return {
            "chat_message": reply,
            "profile_complete": False,
            "profile_data": None,
        }

    except httpx.TimeoutException:
        logger.warning("session=%s intake API call timed out", session_id)
        return {
            "chat_message": (
                "Sorry, that took a bit longer than expected on my end. "
                "Could you say that again and I'll pick right back up?"
            ),
            "profile_complete": False,
            "profile_data": None,
        }

    except Exception as exc:
        logger.exception("session=%s unexpected error in run_intake: %s", session_id, exc)
        return {
            "chat_message": (
                "Apologies — something went wrong on my end. "
                "Please try again and I'll be right with you."
            ),
            "profile_complete": False,
            "profile_data": None,
        }
