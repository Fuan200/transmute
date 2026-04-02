import sqlite3
import threading
from core import get_settings, validate_sql_identifier, migrate_table_columns, assign_orphaned_rows_to_admin

'''
Anywhere you see # nosec B608, it is marking a Bandit false positive. The table 
name is validated and locked after initialization, and the values are 
parameterized to prevent SQL injection.
'''

class DefaultQualitiesDB:
    """Database class for managing default quality settings per output format.

    Stores user-configured default quality levels for output formats that
    support quality options.  For example, a user can set jpeg -> high so
    that every time a file is converted to JPEG, the quality dropdown
    defaults to 'high' instead of 'medium'.

    Attributes:
        settings: Application settings instance.
        DB_PATH: Path to the SQLite database file.
        _TABLE_NAME: Name of the database table for default qualities.
        conn: Active SQLite database connection.
    """

    settings = get_settings()
    DB_PATH = settings.db_path
    _TABLE_NAME = "DEFAULT_QUALITIES"

    @property
    def TABLE_NAME(self) -> str:
        """str: The validated, immutable table name."""
        return self._table_name

    def __init__(self) -> None:
        """Initialize DefaultQualitiesDB, validate the table name, and create tables."""
        object.__setattr__(self, '_table_name', validate_sql_identifier(self._TABLE_NAME))
        self._local = threading.local()
        self.create_tables()

    @property
    def conn(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection, creating one if needed."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.DB_PATH)
        return self._local.conn

    def create_tables(self) -> None:
        """Create the default qualities table if it does not already exist."""
        with self.conn:
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    user_id        TEXT NOT NULL,
                    output_format  TEXT NOT NULL,
                    quality        TEXT NOT NULL,
                    PRIMARY KEY (user_id, output_format)
                )
            """)  # nosec B608

        migrate_table_columns(self.conn, self.TABLE_NAME, {
            "user_id":        "TEXT",
            "output_format":  "TEXT",
            "quality":        "TEXT",
        })

        # Assign pre-auth orphaned rows to the first admin
        assign_orphaned_rows_to_admin(self.conn, self.TABLE_NAME)

    def get_all(self, user_id: str) -> list[dict]:
        """Return all default quality mappings for a user."""
        cursor = self.conn.cursor()
        cursor.row_factory = sqlite3.Row
        cursor.execute(
            f"SELECT output_format, quality FROM {self.TABLE_NAME} WHERE user_id = ? ORDER BY output_format",  # nosec B608
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get(self, user_id: str, output_format: str) -> dict | None:
        """Return the default quality for a given output format and user."""
        cursor = self.conn.cursor()
        cursor.row_factory = sqlite3.Row
        cursor.execute(
            f"SELECT output_format, quality FROM {self.TABLE_NAME} WHERE user_id = ? AND output_format = ?",  # nosec B608
            (user_id, output_format)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def upsert(self, user_id: str, output_format: str, quality: str) -> dict:
        """Insert or update a default quality mapping for a user."""
        with self.conn:
            self.conn.execute(
                f"INSERT INTO {self.TABLE_NAME} (user_id, output_format, quality) "  # nosec B608
                f"VALUES (?, ?, ?) "
                f"ON CONFLICT(user_id, output_format) DO UPDATE SET quality = excluded.quality",
                (user_id, output_format, quality)
            )
        return {"output_format": output_format, "quality": quality}

    def delete(self, user_id: str, output_format: str) -> bool:
        """Delete a default quality mapping for a user."""
        with self.conn:
            cursor = self.conn.execute(
                f"DELETE FROM {self.TABLE_NAME} WHERE user_id = ? AND output_format = ?",  # nosec B608
                (user_id, output_format)
            )
        return cursor.rowcount > 0

    def delete_all(self, user_id: str) -> int:
        """Delete all default quality mappings for a user."""
        with self.conn:
            cursor = self.conn.execute(
                f"DELETE FROM {self.TABLE_NAME} WHERE user_id = ?",  # nosec B608
                (user_id,)
            )
        return cursor.rowcount

    def close(self) -> None:
        """Close the current thread's database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
