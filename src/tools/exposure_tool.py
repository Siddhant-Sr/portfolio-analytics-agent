from src.utils.logger import get_logger
from src.database.db_connection import get_sql_database
import ast

logger = get_logger(__name__)


def resolve_portfolio_id(identifier: str, db) -> int:
    """
    Resolve portfolio identifier to portfolio_id.
    Accepts either portfolio_id or portfolio_name.
    
    Args:
        identifier (str): Portfolio name or portfolio id.
        db: Database connection object.

    Returns:
        int: Resolved portfolio_id or None if not found.
    """

    if isinstance(identifier, int) or str(identifier).isdigit():
        return int(identifier)

    query = f"""
    SELECT portfolio_id
    FROM portfolios
    WHERE LOWER(portfolio_name) LIKE LOWER('%{identifier}%')
    """

    result = db.run(query)

    if not result:
        return None

    rows = ast.literal_eval(result)

    portfolio_id = rows[0][0]

    logger.info("Resolved portfolio '%s' to id %s", identifier, portfolio_id)

    return portfolio_id


def calculate_sector_exposure(identifier: str):
    """
    Use this tool when the user asks for sector exposure,
    sector allocation, or sector breakdown of a portfolio.

    The portfolio can be identified by portfolio name or portfolio id.
    
    Args:
        identifier (str): Portfolio name or portfolio id.
    """

    logger.info("Calculating sector exposure for identifier=%s", identifier)

    db = get_sql_database()

    portfolio_id = resolve_portfolio_id(identifier, db)

    if portfolio_id is None:
        return {"error": "Portfolio not found"}

    query = f"""
    SELECT
        sec.sector_name,
        SUM(h.current_weight) as exposure
    FROM holdings h
    JOIN securities s
        ON h.security_id = s.security_id
    JOIN sectors sec
        ON s.sector_id = sec.sector_id
    WHERE
        h.portfolio_id = {portfolio_id}
        AND s.asset_type = 'Stock'
    GROUP BY sec.sector_name
    ORDER BY exposure DESC
    """

    try:

        result = db.run(query)

        logger.info("Exposure query executed successfully")
        logger.info("Raw result: %s", result)

        if not result:
            return {
                "portfolio_id": portfolio_id,
                "sector_exposure": {},
            }

        rows = ast.literal_eval(result)

        sector_exposure = {sector: exposure for sector, exposure in rows}

        return {
            "portfolio_id": portfolio_id,
            "sector_exposure": sector_exposure,
        }

    except Exception as e:
        logger.error("Exposure calculation failed: %s", str(e))
        return {"error": str(e)}