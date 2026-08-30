from app.ai.tools import execute_readonly, get_schema


class DatabaseAgent:
    def __init__(self, llm):
        self.llm = llm

    def ask(self, url: str, question: str) -> tuple[str, str]:
        # 1. اقرا شكل الداتا بيز الحقيقية بتاعة اليوزر (اسماء جداول واعمدة)
        schema = get_schema(url)

        # 2. خلي الموديل يولد كويري SQL واحدة بناء على السؤال والاسكيما بس
        sql = self.llm.generate_sql(question, schema)

        # 3. نفذ الكويري فعليا (execute_readonly بتتحقق منها الاول وبترفض اي حاجة خطرة)
        rows = execute_readonly(url, sql)

        # 4. حوّل النتايج الحقيقية لإجابة مفهومة لليوزر
        answer = self.llm.answer(question, schema, rows)
        return answer, sql