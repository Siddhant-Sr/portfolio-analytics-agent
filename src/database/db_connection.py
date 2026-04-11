import sqlite3
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Get project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Database path
DB_PATH = BASE_DIR / "data" / "db" / "portfolio_database.db"


def get_db_connection():
    """
    Create and return a SQLite database connection.
    """

    try:
        conn = sqlite3.connect(DB_PATH)

        logger.info(f"Connected to database: {DB_PATH}")

        return conn

    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    
from pathlib import Path
from langchain_community.utilities import SQLDatabase
from src.utils.logger import get_logger

logger = get_logger(__name__)

_db_instance = None


def find_project_root(start: Path) -> Path:
    """
    Walk up the directory tree until the project root is found.
    Root is identified by the presence of the 'data' directory.
    """
    for p in [start, *start.parents]:
        if (p / "data").exists():
            return p

    raise RuntimeError("Project root not found")


def get_sql_database() -> SQLDatabase:
    """
    Return a reusable SQLDatabase connection.
    """

    global _db_instance

    if _db_instance is not None:
        return _db_instance

    base_dir = find_project_root(Path.cwd())

    db_path = base_dir / "data" / "db" / "portfolio_database.db"

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    uri = f"sqlite:///{db_path}"

    logger.info("Connecting to database at %s", db_path)

    _db_instance = SQLDatabase.from_uri(
        uri,
        sample_rows_in_table_info=3
    )

    logger.info("Database connected")
    logger.info("Dialect: %s", _db_instance.dialect)
    logger.info("Available tables: %s", _db_instance.get_usable_table_names())

    return _db_instance
    
if __name__ == "__main__":
    get_db_connection()