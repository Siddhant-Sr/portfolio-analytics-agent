from pathlib import Path
from src.database.db_connection import get_db_connection
from src.utils.logger import get_logger
import pandas as pd

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]

SCHEMA_PATH = BASE_DIR / "data" / "schema" / "database_schema.sql"
CSV_DIR = BASE_DIR / "data" / "csv_files"

def initialize_database():
    """
    Executes the SQL schema file to create tables.
    """


    try:
        conn = get_db_connection()

        with open(SCHEMA_PATH, "r") as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)

        conn.commit()

        logger.info("Database schema executed successfully")

        conn.close()

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    
def load_csv_to_table(csv_path, table_name, conn):
    """
    Load CSV data into a database table.
    """

    try:
        df = pd.read_csv(csv_path)

        df.to_sql(
            table_name,
            conn,
            if_exists="append",
            index=False
        )

        logger.info(f"Loaded {len(df)} rows into {table_name}")

    except Exception as e:
        logger.error(f"Failed loading {table_name}: {e}")
        raise

def upload_files():
    """
    Load CSV files into database tables.
    """

    conn = get_db_connection()

    tables = {
        "sectors": CSV_DIR / "sectors.csv",
        "securities": CSV_DIR / "securities.csv",
        "benchmarks": CSV_DIR / "benchmarks.csv",
        "portfolios": CSV_DIR / "portfolios.csv",
        "holdings": CSV_DIR / "holdings.csv",
        "transactions": CSV_DIR / "transactions.csv",
        "historical_prices": CSV_DIR / "historical_prices.csv",
        "portfolio_performance": CSV_DIR / "portfolio_performance.csv",
        "risk_metrics": CSV_DIR / "risk_metrics.csv"
    }

    for table, path in tables.items():
        load_csv_to_table(path, table, conn)

    conn.commit()
    conn.close()

    logger.info("All CSV data loaded successfully")
    
if __name__ == "__main__":
    initialize_database()
    upload_files()