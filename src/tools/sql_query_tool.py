from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from src.database.db_connection import get_sql_database
from src.utils.logger import get_logger
from dotenv import load_dotenv
import os
import ast

load_dotenv()

logger = get_logger(__name__)
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")


def get_schema_info(db: SQLDatabase) -> str:
    """Fetch database schema information."""
    return db.get_table_info()


def validate_sql(query: str) -> bool:
    """
    Ensure only safe read-only SQL queries are executed.
    """

    query_upper = query.upper()

    forbidden_keywords = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
    ]

    if not query_upper.startswith(("SELECT", "WITH")):
        return False

    if any(keyword in query_upper for keyword in forbidden_keywords):
        return False

    return True


def generate_fetch_data(question: str):
    """
    Use this tool to answer questions about portfolios, holdings,
    sectors, performance metrics, or counts by querying the
    portfolio database using SQL.
    
    Args:
        question (str): The user's question about the portfolio data.
    """

    db = get_sql_database()

    template = """
You are an expert financial database analyst.

Generate a correct SQLite SQL query to answer the user's question.

Rules:
1. Use only tables and columns from the schema.
2. Use correct JOIN relationships.
3. Use CTEs for complex queries when needed.
4. Only include securities where asset_type = 'Stock' when counting sector diversification.
5. Diversification metric = number_of_sectors / total_holdings
6. Count sectors using COUNT(DISTINCT sector_id)
7. Return the SQL query in a single line.
8. Do not include explanations.
9. When displaying categorical information such as sectors, portfolios, or securities,
always return the descriptive name (e.g., sector_name, portfolio_name) instead of IDs.

10. If a table contains a foreign key (e.g., sector_id),
join with the corresponding dimension table to retrieve the name.

11. Avoid returning NULL categories unless explicitly requested.
9. When displaying categorical information such as sectors, portfolios, or securities,
always return the descriptive name (e.g., sector_name, portfolio_name) instead of IDs.

10. If a table contains a foreign key (e.g., sector_id),
join with the corresponding dimension table to retrieve the name.

11. Avoid returning NULL categories unless explicitly requested.
9. When displaying categorical information such as sectors, portfolios, or securities,
always return the descriptive name (e.g., sector_name, portfolio_name) instead of IDs.

10. If a table contains a foreign key (e.g., sector_id),
join with the corresponding dimension table to retrieve the name.

11. Avoid returning NULL categories unless explicitly requested.
12. Always join dimension tables when grouping results by category.
13. When grouping by sector or other category, exclude NULL values unless explicitly required.

Database Schema:
{schema}

User Question:
{question}

SQL Query:
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an expert SQL generator for financial portfolio analytics."),
            ("human", template),
        ]
    )

    llm = ChatGroq(
        model=MODEL,
        temperature=0,
    )

    sql_chain = (
        RunnablePassthrough.assign(schema=lambda _: get_schema_info(db))
        | prompt
        | llm
        | StrOutputParser()
    )

    try:

        generated_sql = sql_chain.invoke({"question": question}).strip()

        logger.info("User Question: %s", question)
        logger.info("Generated SQL: %s", generated_sql)

        if not validate_sql(generated_sql):
            logger.warning("Unsafe SQL detected")
            return {"error": "Unsafe SQL query generated"}

        result = db.run(generated_sql)

        try:
            parsed_result = ast.literal_eval(result)
        except Exception:
            parsed_result = result

        logger.info("Query Result: %s", parsed_result)

        return {
            "sql_query": generated_sql,
            "result": parsed_result,
        }

    except Exception as e:
        logger.error("SQL execution failed: %s", str(e))
        return {"error": str(e)}