from db import ConversionDB


def test_conversion_db_initializes_quality_column(monkeypatch):
    monkeypatch.setattr(ConversionDB, 'DB_PATH', ':memory:')

    db = ConversionDB()
    try:
        columns = db.conn.execute(f"PRAGMA table_info({db.TABLE_NAME})").fetchall()
        column_names = {column[1] for column in columns}

        assert 'quality' in column_names
    finally:
        db.close()