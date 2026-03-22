#!/usr/bin/env python3
"""
SQL Injection Challenge - Vulnerable Login Page
WARNING: This code is intentionally vulnerable! Do not use in production!
"""

from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Flag from environment variable
FLAG = os.getenv('FLAG', 'FLAG{sql_1nj3ct10n_1s_d4ng3r0us}')

# 資料庫路徑（支援 Docker 和本地環境）
DB_PATH = os.getenv('DB_PATH', '/app/data/database.db')
# 本地開發時使用當前目錄
if not os.path.exists(os.path.dirname(DB_PATH)):
    DB_PATH = 'database.db'

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 創建用戶表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')

    # 插入預設用戶
    try:
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES ('admin', 'P@ssw0rd123', 1)")
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES ('guest', 'guest', 0)")
    except sqlite3.IntegrityError:
        pass  # 用戶已存在

    conn.commit()
    conn.close()

@app.route('/')
def index():
    """首頁"""
    if 'username' in session:
        return render_template('dashboard.html',
                             username=session['username'],
                             flag=FLAG if session.get('is_admin') else None)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登入頁面 - 含有 SQL Injection 漏洞"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        # 危險！直接拼接 SQL 查詢
        # 這是故意的漏洞，請勿在實際應用中使用
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute(query)  # SQL Injection 漏洞在此
            user = cursor.fetchone()

            if user:
                session['username'] = user[1]
                session['is_admin'] = bool(user[3])
                conn.close()
                return redirect(url_for('index'))
            else:
                conn.close()
                return render_template('login.html', error='Invalid credentials')

        except sqlite3.Error as e:
            conn.close()
            # 洩漏 SQL 錯誤訊息（也是漏洞）
            return render_template('login.html', error=f'Database error: {str(e)}')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=False)
