import sqlite3

DB_NAME = "crawler.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS crawl_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seed_url TEXT NOT NULL,
            max_pages INTEGER NOT NULL,
            same_domain INTEGER NOT NULL DEFAULT 1,
            pages_crawled INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            url TEXT NOT NULL,
            title TEXT,
            meta_description TEXT,
            status_code INTEGER,
            content_type TEXT,
            crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(run_id, url),
            FOREIGN KEY (run_id) REFERENCES crawl_runs(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            source_url TEXT NOT NULL,
            target_url TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES crawl_runs(id)
        )
        """
    )

    conn.commit()
    conn.close()


def create_crawl_run(seed_url, max_pages, same_domain):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO crawl_runs (seed_url, max_pages, same_domain)
        VALUES (?, ?, ?)
        """,
        (seed_url, max_pages, 1 if same_domain else 0),
    )
    conn.commit()
    run_id = cur.lastrowid
    conn.close()
    return run_id


def update_crawl_run(run_id, pages_crawled):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE crawl_runs
        SET pages_crawled = ?
        WHERE id = ?
        """,
        (pages_crawled, run_id),
    )
    conn.commit()
    conn.close()