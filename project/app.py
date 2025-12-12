# app.py
import sqlite3
import uuid
import os
from flask import Flask, g, render_template, request, jsonify, redirect, url_for

DATABASE = 'links.db'
DOMAIN = os.environ.get("DOMAIN", "http://localhost:5000")  # sửa khi deploy 
# setx TELEGRAM_BOT_TOKEN "8279709205:AAH_QDH0IQTMHpcOi6BQldE8nW8Q7tC9cX4"

app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT,
        original_link TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT,
        telegram_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(task_id, telegram_id)
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        telegram_id TEXT PRIMARY KEY,
        points INTEGER DEFAULT 0
    )
    ''')
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ----- Admin: tạo nhiệm vụ nhanh (demo) -----
@app.route('/admin/create_task', methods=['POST'])
def admin_create_task():
    # POST form: title, original_link
    title = request.form.get('title')
    orig = request.form.get('original_link')
    if not (title and orig):
        return "title and original_link required", 400
    task_id = uuid.uuid4().hex[:10]
    db = get_db()
    db.execute('INSERT INTO tasks (id, title, original_link) VALUES (?, ?, ?)', (task_id, title, orig))
    db.commit()
    # link để mở trang task:
    task_url = f"{DOMAIN}/task/{task_id}"
    return jsonify({"task_id": task_id, "task_url": task_url})

# ----- Mini-app page (mở trong Telegram WebApp) -----
@app.route('/app')
def app_index():
    db = get_db()
    cur = db.execute('SELECT id, title FROM tasks ORDER BY created_at DESC')
    tasks = cur.fetchall()
    return render_template('index.html', tasks=tasks, domain=DOMAIN)

# ----- Trang task: hiển thị link gốc sau delay hoặc nút -----
@app.route('/task/<task_id>')
def task_page(task_id):
    db = get_db()
    cur = db.execute('SELECT id, title, original_link FROM tasks WHERE id=?', (task_id,))
    row = cur.fetchone()
    if not row:
        return "Task không tồn tại", 404
    # Không redirect tự động: show page with a timer + nút "Lấy link gốc"
    return render_template('task.html', task=row)

# ----- API: người dùng dán link vào mini-app để xác nhận hoàn thành -----
@app.route('/api/submit_link', methods=['POST'])
def api_submit_link():
    data = request.json or {}
    telegram_id = str(data.get('telegram_id') or "")
    task_id = data.get('task_id')
    pasted = data.get('pasted_link', "").strip()

    if not (telegram_id and task_id and pasted):
        return jsonify({"ok": False, "msg": "thiếu dữ liệu"}), 400

    db = get_db()
    cur = db.execute('SELECT original_link FROM tasks WHERE id=?', (task_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"ok": False, "msg": "Task không tồn tại"}), 404

    orig = row['original_link'].strip()
    # So sánh: có thể làm mạnh hơn (normalize url) — ở đây so sánh đơn giản
    if pasted != orig:
        return jsonify({"ok": False, "msg": "Link không đúng"}), 400

    # Check đã hoàn thành chưa
    try:
        db.execute('INSERT INTO completions (task_id, telegram_id) VALUES (?, ?)', (task_id, telegram_id))
        # cộng điểm cho user
        db.execute('INSERT OR IGNORE INTO users (telegram_id, points) VALUES (?, ?)', (telegram_id, 0))
        db.execute('UPDATE users SET points = points + 1 WHERE telegram_id = ?', (telegram_id,))
        db.commit()
    except sqlite3.IntegrityError:
        # đã hoàn thành trước đó
        return jsonify({"ok": False, "msg": "Bạn đã hoàn thành nhiệm vụ này trước đó"}), 400

    cur2 = db.execute('SELECT points FROM users WHERE telegram_id = ?', (telegram_id,))
    pts = cur2.fetchone()['points']
    return jsonify({"ok": True, "msg": "Hoàn thành", "points": pts})

# ----- API: lấy điểm user -----
@app.route('/api/get_points')
def get_points():
    telegram_id = request.args.get('telegram_id')
    if not telegram_id:
        return jsonify({"ok": False, "msg": "telegram_id required"}), 400
    db = get_db()
    cur = db.execute('SELECT points FROM users WHERE telegram_id = ?', (telegram_id,))
    r = cur.fetchone()
    return jsonify({"ok": True, "points": (r['points'] if r else 0)})

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
