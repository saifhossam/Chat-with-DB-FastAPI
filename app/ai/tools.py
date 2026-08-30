"""Database tools and read-only SQL validation."""
import re

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.exceptions import DatabaseConnectionError, UnsafeSqlError
from app.database.connection import engine


FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "grant", "revoke", "pragma", "attach", "detach", "vacuum",
)

# اقصى عدد صفوف بنرجعه للموديل، عشان منبعتش داتا ضخمة او نستهلك تكن كتير من غير داعي
MAX_ROWS = 10


def _get_engine(url: str):
    """رابط التطبيق نفسه بياخد نفس الـ engine الجاهز (فيه pool_pre_ping من الأول).
    اي رابط تاني بتاع اليوزر بياخد engine جديد بنفس اعدادات اعادة الاتصال."""
    if url == settings.database_url:
        return engine
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


def validate_readonly_sql(sql: str) -> str:
    """يتأكد ان الكويري قراءة بس، جملة واحدة بس، من غير اي كلمات خطرة."""
    # شيل اي code fences لو الموديل رجعها بالغلط زي ```sql ... ```
    cleaned = sql.strip().strip("`")
    cleaned = re.sub(r"^sql\s*", "", cleaned, flags=re.IGNORECASE).strip()

    # امنع اي كومنتات ممكن تتستخدم عشان تهرّب اوامر زيادة جوه الكويري
    if "--" in cleaned or "/*" in cleaned:
        raise UnsafeSqlError("SQL comments are not allowed")

    # امنع اكتر من statement (سماح بسيمي كولون واحدة في الآخر بس)
    statements = [s for s in cleaned.split(";") if s.strip()]
    if len(statements) != 1:
        raise UnsafeSqlError("Only a single SQL statement is allowed")

    normalized = statements[0].strip().lower()

    if not normalized.startswith(("select", "with")):
        raise UnsafeSqlError("Only read-only SELECT statements are allowed")

    # دور على كل كلمة ممنوعة كـ "كلمة كاملة" مش substring
    # عشان عمود اسمه مثلا updated_at ميترفضش غلط بسبب كلمة "update"
    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{word}\b", normalized):
            raise UnsafeSqlError(f"'{word}' is not allowed in a read-only query")

    return statements[0].strip()


def get_schema(url: str) -> str:

    try:
        target_engine = _get_engine(url)
        inspector = inspect(target_engine)
        tables = []
        for table in inspector.get_table_names():
            columns = ", ".join(f'"{column["name"]}"' for column in inspector.get_columns(table))
            tables.append(f'"{table}"({columns})')
        return "; ".join(tables) or "No tables found"
    except SQLAlchemyError as error:
        raise DatabaseConnectionError(f"Could not connect to the database: {error}") from error


def execute_readonly(url: str, sql: str) -> list[dict]:
    """يتحقق من الكويري الاول، ثم ينفذها فعليا على داتا بيز اليوزر الحقيقية."""
    safe_sql = validate_readonly_sql(sql)
    try:
        target_engine = _get_engine(url)
        with target_engine.connect() as connection:
            result = connection.execute(text(safe_sql))
            # fetchmany بدل fetchall عشان منجيبش صفوف اكتر من اللي محتاجينه
            rows = [dict(row._mapping) for row in result.fetchmany(MAX_ROWS)]
            return rows
    except SQLAlchemyError as error:
        raise DatabaseConnectionError(f"Could not run the query: {error}") from error