import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# LOAD ENV FIRST
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a property management maintenance intake assistant.

Rules:
- Be professional and calm
- Ask 2–4 clarifying questions
- Do NOT promise repairs or timelines
- Assume non-emergency unless explicitly stated
- Output JSON only

Format:
{
  "issue_category": "...",
  "severity": "low|medium|high",
  "reply": "email-safe response"
}
"""

def run_ai_agent(subject: str, body: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Subject: {subject}\nMessage: {body}"
            }
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "issue_category": "unknown",
            "severity": "unknown",
            "reply": (
                "Thanks for reaching out. We’ve received your maintenance request "
                "and will follow up shortly."
            )
        }
