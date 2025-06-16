from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS blog (id INTEGER PRIMARY KEY, title TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY, title TEXT, description TEXT, image TEXT, video TEXT)''')
    conn.commit()
    conn.close()

# Home route
@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    blogs = c.execute('SELECT title, content FROM blog').fetchall()
    portfolio_entries = c.execute('SELECT title, description, image, video FROM portfolio').fetchall()
    conn.close()
    return render_template('index.html', blogs=blogs, portfolio_entries=portfolio_entries)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == "admin@example.com" and password == "admin123":
            session['admin'] = True
            return redirect('/dashboard')
        else:
            return "Invalid credentials"
    return render_template('login.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('dashboard.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)