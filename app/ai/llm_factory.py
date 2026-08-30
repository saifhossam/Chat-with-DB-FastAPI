"""Composition root for the Gemini provider."""
from google import genai

from app.ai.agent import DatabaseAgent
from app.ai.prompts import DATABASE_AGENT_PROMPT, SQL_GENERATION_PROMPT
from app.core.config import settings


class GeminiProvider:
    """Minimal Gemini 2.5 Flash adapter used by the agent."""

    def __init__(self, api_key: str | None, model: str):
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else None

    def generate_sql(self, question: str, schema: str) -> str:
        if not self.client:
            return "SELECT 1 AS example"

        prompt = (
            f"{SQL_GENERATION_PROMPT}\n"
            f"Schema: {schema}\n"
            f"<user_question>\n{question}\n</user_question>"
        )
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return (response.text or "SELECT 1 WHERE 1=0").strip()

    def answer(self, question: str, schema: str, rows: list[dict]) -> str:
        if not self.client:
            return f"Found {len(rows)} row(s) for: {question}"

        prompt = (
            f"{DATABASE_AGENT_PROMPT}\n"
            f"Schema: {schema}\n"
            f"<user_question>\n{question}\n</user_question>\n"
            f"<query_results>\n{rows}\n</query_results>"
        )
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return response.text or "Gemini returned an empty answer."

    def answer_stream(self, question: str, schema: str, rows: list[dict]):
        """نفس answer بس بترجع الاجابة جزء جزء اول ما توصل من Gemini،
        مش كل الرد مرة واحدة في الآخر."""
        if not self.client:
            yield f"Found {len(rows)} row(s) for: {question}"
            return

        prompt = (
            f"{DATABASE_AGENT_PROMPT}\n"
            f"Schema: {schema}\n"
            f"<user_question>\n{question}\n</user_question>\n"
            f"<query_results>\n{rows}\n</query_results>"
        )
        # generate_content_stream بيرجع النتيجة على دفعات بدل ما يستنى الرد كامل
        for chunk in self.client.models.generate_content_stream(model=self.model, contents=prompt):
            if chunk.text:
                yield chunk.text


llm = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
agent = DatabaseAgent(llm)