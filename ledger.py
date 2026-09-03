"""Small SQLite-backed expense ledger."""
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path.home() / ".config" / "http-server" / "ledger.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER UNIQUE NOT NULL,
        name TEXT,
        created_at TEXT NOT NULL
    )""")
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
    categories = {"1": "식비", "2": "여가", "3": "통신/구독", "4": "경조사", "5": "쇼핑", "6": "주거/생활", "7": "저축/투자", "8": "커피"}
    match = re.match(r"^\s*([1-8])\s+(.+?)\s+(\d+)\s*$", text)
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


def query_expenses(month=None, user=None, category=None, limit=100):
    conn=_connect(); conn.row_factory=sqlite3.Row
    where=[]; args=[]
    if month: where.append("created_at LIKE ?"); args.append(month+'%')
    if user: where.append("telegram_user_id=?"); args.append(int(user))
    if category: where.append("category=?"); args.append(category)
    clause=(' WHERE '+' AND '.join(where)) if where else ''
    rows=conn.execute("SELECT id, CASE telegram_user_id WHEN 8631664727 THEN '지희' WHEN 8806961376 THEN '광래' ELSE CAST(telegram_user_id AS TEXT) END AS name, telegram_user_id, description AS merchant, amount, category, substr(created_at,1,10) AS spent_at FROM expenses"+clause+" ORDER BY id DESC LIMIT ?",(*args,limit)).fetchall(); conn.close(); return [dict(x) for x in rows]

def statistics(month=None):
    conn=_connect(); where=' WHERE created_at LIKE ?' if month else ''; args=(month+'%',) if month else ()
    total=conn.execute('SELECT COALESCE(SUM(amount),0) FROM expenses'+where,args).fetchone()[0]
    cat=[dict(label=r[0],total=r[1]) for r in conn.execute('SELECT category,SUM(amount) FROM expenses'+where+' GROUP BY category ORDER BY 2 DESC',args)]
    monthly=[dict(label=r[0],total=r[1]) for r in conn.execute('SELECT substr(created_at,1,7),SUM(amount) FROM expenses GROUP BY 1 ORDER BY 1 DESC LIMIT 12')]
    conn.close(); return {'total':total,'category':cat,'users':[],'monthly':monthly}

def update_expense(expense_id, content, category, amount, spent_at=None):
    conn=_connect()
    if spent_at:
        conn.execute("UPDATE expenses SET description=?, category=?, amount=?, created_at=substr(?,1,10)||substr(created_at,11) WHERE id=?", (content, category, amount, spent_at, expense_id))
    else:
        conn.execute("UPDATE expenses SET description=?, category=?, amount=? WHERE id=?", (content, category, amount, expense_id))
    conn.commit(); conn.close()

def delete_expense(expense_id):
    conn=_connect(); conn.execute("DELETE FROM expenses WHERE id=?",(expense_id,)); conn.commit(); conn.close()
