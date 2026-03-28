from django.shortcuts import render

# Create your views here.
import requests
from rest_framework.views import APIView
from rest_framework.response import Response


schema = """
DMTTransaction(
    dmt_refrence_id,
    dmt_trn_id,
    dmt_txn_amount,
    trn_status,
    created_at
)
"""


class GenerateSQLAPIView(APIView):

    def post(self, request):
        user_query = request.data.get("query")

        if not user_query:
            return Response({"error": "Query required"}, status=400)

        prompt = f"""
You are a PostgreSQL expert.

IMPORTANT:
- "unique id" means dmt_refrence_id
- Only return SQL query

Database schema:
{schema}

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
                }
            )

            sql_query = res.json().get("response", "").strip()

            if not sql_query:
                return Response({"message": "Samajh nahi aaya"})

            return Response({
                "sql_query": sql_query
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)