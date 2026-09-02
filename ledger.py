"""Small SQLite-backed expense ledger."""
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path.home() / ".config" / "http-server" / "ledger.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER NOT NULL,
        telegram_chat_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        amount INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )""")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(expenses)")}
    if "category" not in cols: conn.execute("ALTER TABLE expenses ADD COLUMN category TEXT NOT NULL DEFAULT '기타'")
    return conn


def parse_expense(text: str):
    categories = {"1": "식비", "2": "여가", "3": "통신/구독", "4": "경조사", "5": "쇼핑", "6": "주거/생활"}
    match = re.match(r"^\s*([1-6])\s+(.+?)\s+(\d+)\s*$", text)
    if not match: return None
    category = categories[match.group(1)]
    content = match.group(2).strip()
    if not content: return None
    return content, int(match.group(3)), category

def add_expense(user_id: int, chat_id: int, parsed, name=None) -> None:
    content, amount, category = parsed
    with _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO users (telegram_user_id, name, created_at) VALUES (?, ?, ?)", (user_id, name or str(user_id), datetime.now(timezone.utc).isoformat()))
        row = conn.execute("SELECT id FROM users WHERE telegram_user_id=?", (user_id,)).fetchone()
        conn.execute("INSERT INTO expenses (telegram_user_id, telegram_chat_id, description, amount, category, created_at) VALUES (?, ?, ?, ?, ?, ?)", (user_id, chat_id, content, amount, category, datetime.now(timezone.utc).isoformat()))


def query_expenses(month=None, limit=100):
    conn=_connect(); conn.row_factory=sqlite3.Row
    rows=conn.execute("SELECT id, CASE telegram_user_id WHEN 8631664727 THEN '지희' ELSE CAST(telegram_user_id AS TEXT) END AS name, description AS merchant, amount, category, substr(created_at,1,10) AS spent_at FROM expenses ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); conn.close()
    return [dict(x) for x in rows]

def statistics(month=None):
    conn=_connect(); total=conn.execute('SELECT COALESCE(SUM(amount),0) FROM expenses').fetchone()[0]
    cat=[dict(label=r[0],total=r[1]) for r in conn.execute('SELECT category,SUM(amount) FROM expenses GROUP BY category ORDER BY 2 DESC')]; conn.close()
    return {'total':total,'category':cat,'users':[],'monthly':[]}


def update_expense(expense_id, content, category, amount):
    conn=_connect(); conn.execute("UPDATE expenses SET description=?, category=?, amount=? WHERE id=?",(content,category,amount,expense_id)); conn.commit(); conn.close()

def delete_expense(expense_id):
    conn=_connect(); conn.execute("DELETE FROM expenses WHERE id=?",(expense_id,)); conn.commit(); conn.close()
