import requests
from rest_framework.views import APIView
from rest_framework.response import Response


schema = {
    "ad_dmt_transaction": {
        "dmt_refrence_id": "unique reference id of transaction",
        "dmt_trn_id": "internal transaction id",
        "dmt_txn_amount": "transaction amount",
        "dmt_txn_status": "transaction status",
        "created_at": "transaction date"
    }
}


def format_schema(schema_dict):
    result = ""
    for table, columns in schema_dict.items():
        cols = ", ".join(columns.keys())
        result += f"{table}({cols})\n"
    return result


def clean_sql(output):
    output = output.strip()
    if "SELECT" in output.upper():
        output = output[output.upper().index("SELECT"):]
    return output


# 🔥 SMART FIX FUNCTION (IMPORTANT)
def fix_sql(query, user_query):
    q = query.upper()
    user_q = user_query.lower()

    # ❌ remove multiple queries
    if ";" in query:
        query = query.split(";")[0]

    # 🔥 Fix wrong table name
    query = query.replace("AD_DMT_TRANSACTION", "DMTTransaction")

    # 🔥 Fix ISO WEEK issue
    query = query.replace("ISO WEEK", "WEEK")

    # 🔥 FIX: last N days logic
    if "last" in user_q and "day" in user_q:
        import re
        match = re.search(r'last (\d+) day', user_q)
        if match:
            n = int(match.group(1))
            days = n - 1

            query = f"""
SELECT 
    dmt_refrence_id,
    SUM(dmt_txn_amount) AS total_amount
FROM ad_dmt_transaction
WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
AND created_at < CURRENT_DATE + INTERVAL '1 day'
GROUP BY dmt_refrence_id;
"""

    # 🔥 FIX: week query
    if "week" in user_q:
        query = f"""
SELECT SUM(dmt_txn_amount)
FROM ad_dmt_transaction
WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)
AND created_at < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '1 week';
"""

    return query.strip()


def validate_sql(query):
    if "SELECT" not in query.upper():
        return False
    if "DROP" in query.upper() or "DELETE" in query.upper():
        return False
    return True


class GenerateSQLAPIView(APIView):

    def post(self, request):
        user_query = request.data.get("query")

        if not user_query:
            return Response({"error": "Query required"}, status=400)

        schema_str = format_schema(schema)

        # 🔥 STRONG PROMPT (TRAINING EFFECT 🔥)
        prompt = f"""
You are a PostgreSQL expert.

STRICT RULES:
- Only return ONE SQL query
- No explanation
- Use PostgreSQL syntax
- NEVER use ISO WEEK
- ALWAYS use DATE_TRUNC for week/month
- For "last N days" use CURRENT_DATE - INTERVAL

MAPPING:
- "unique id" = dmt_refrence_id
- "amount" = dmt_txn_amount

EXAMPLES:

Q: last 5 days transaction amount and id
A:
SELECT dmt_refrence_id, SUM(dmt_txn_amount)
FROM ad_dmt_transaction
WHERE created_at >= CURRENT_DATE - INTERVAL '4 days'
AND created_at < CURRENT_DATE + INTERVAL '1 day'
GROUP BY dmt_refrence_id;

Q: total amount this week
A:
SELECT SUM(dmt_txn_amount)
FROM ad_dmt_transaction
WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)
AND created_at < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '1 week';

Database schema:
{schema_str}

User question:
{user_query}

SQL Query:
"""

        try:
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "my-sql-model",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )

            sql_query = res.json().get("response", "").strip()

            # ✅ Clean
            sql_query = clean_sql(sql_query)

            # 🔥 Smart Fix
            sql_query = fix_sql(sql_query, user_query)

            # ❌ Validate
            if not validate_sql(sql_query):
                return Response({
                    "message": "Samajh nahi aaya, clear query likho"
                })

            return Response({
                "sql_query": sql_query
            })

        except requests.exceptions.ConnectionError:
            return Response({"error": "Ollama not running"}, status=500)

        except requests.exceptions.Timeout:
            return Response({"error": "Model slow, try again"}, status=500)

        except Exception as e:
            return Response({"error": str(e)}, status=500)