import os

from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from app.models.incident import Incident


load_dotenv()


class AIService:

    def __init__(self):

        self.model = ChatGroq(

            model="openai/gpt-oss-120b",

            groq_api_key=os.getenv("GROQ_API_KEY"),

            temperature=0,

        )

    def generate_summary(
        self,
        incident: Incident
    ) -> dict:

        prompt = f"""
You are an expert electrical distribution fault analysis assistant.

Analyze the following fault incident and generate a concise report.

Incident ID:
{incident.incident_id}

Fault Type:
{incident.fault_type}

Feeder ID:
{incident.feeder_id}

Transformer ID:
{incident.transformer_id}

Fault Boundary:
{incident.start_pole} -> {incident.end_pole}

Affected Pole Count:
{incident.affected_pole_count}

Affected Pole IDs:
{incident.affected_pole_ids}

Location:
Latitude: {incident.latitude}
Longitude: {incident.longitude}
Pincode: {incident.pincode}

Confidence:
{incident.confidence}%

Generate the response in EXACTLY this format with STRICT character limits:

Fault Summary:
<1-2 sentences, MAX 180 characters>

Probable Root Cause:
<1 sentence, MAX 180 characters>

Recommended Action:
<1-2 sentences, MAX 180 characters>

CRITICAL: Each section must be under 180 characters. No markdown, no bullet points, plain text only.
"""

        response = self.model.invoke(

            [

                HumanMessage(

                    content=prompt

                )

            ]

        )

        return self._parse(response.content)

    def _parse(self, text: str) -> dict:

        summary = None
        root_cause = None
        recommended_action = None

        markers = [
            ("Fault Summary:", "summary"),
            ("Probable Root Cause:", "root_cause"),
            ("Recommended Action:", "recommended_action"),
        ]

        positions = []

        for marker, key in markers:

            idx = text.find(marker)

            if idx != -1:
                positions.append((idx, len(marker), key))

        positions.sort()

        for i, (idx, marker_len, key) in enumerate(positions):

            start = idx + marker_len

            end = positions[i + 1][0] if i + 1 < len(positions) else len(text)

            value = text[start:end].strip()

            if key == "summary":
                summary = value
            elif key == "root_cause":
                root_cause = value
            elif key == "recommended_action":
                recommended_action = value

        return {
            "ai_summary": summary or text.strip(),
            "root_cause": root_cause,
            "recommended_action": recommended_action,
        }